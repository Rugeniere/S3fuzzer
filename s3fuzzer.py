import subprocess
import argparse
import sys
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
import requests
import re
import warnings

warnings.filterwarnings("ignore", message="Unverified HTTPS request")

def print_green(text):
    print(f"\033[92m{text}\033[0m")

def print_red(text):
    print(f"\033[91m{text}\033[0m")

def check_bucket_cli(profile, bucket_name, public_buckets, private_buckets, region=None, check_acl=False):
    try:
        command = ["aws"]
        if region:
            command += ["--region", region]
        command += ["--profile", profile, "s3", "ls", "--recursive", f"s3://{bucket_name}"]

        result = subprocess.run(command, capture_output=True, text=True)

        output = result.stderr.lower() + result.stdout.lower()

        if "the config profile" in output and "could not be found" in output:
            print(f"Error: profile ({profile}) didnt found on aws cli tool")
            sys.exit(1)
        
        if "invalid bucket name" in output:
            return 
        elif "access denied" in output:
            private_buckets.append(bucket_name)
        elif "nosuchbucket" in output:
            return
        elif "could not connect to the endpoint url" in output:
            print(f"Error: Connection issue searching for bucket {bucket_name}.")
            sys.exit(1)
        else:
            if re.search(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', output, re.MULTILINE):
                public_buckets.append((bucket_name, output.strip()))

            if check_acl:
                acl_command = f"curl -s https://{bucket_name}.s3.amazonaws.com"
                acl_result = subprocess.run(acl_command, capture_output=True, text=True, shell=True, verify=False)
                if "NoSuchBucket" in acl_result.stdout:
                    private_buckets.append(bucket_name)
                elif "The bucket you are attempting to access must be addressed using the specified endpoint" in acl_result.stdout:
                    public_buckets.append((bucket_name, "ACL indicates public access"))

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


def check_bucket_http(url_template, region, word, public_buckets, private_buckets):
    url = url_template.replace("FUZZ", word)
    full_url = f"https://{url}.s3-{region}.amazonaws.com/"
    try:
        response = requests.get(full_url, verify=False)
        
        if response.status_code == 403:
            private_buckets.append(full_url)
        elif response.status_code == 404:
            pass
        elif "maxkeys" in response.text.lower():
            public_buckets.append(full_url)

    except requests.exceptions.RequestException:
        pass

def enumerate_buckets_cli(profile, bucket_names, max_threads, region, check_acl):
    public_buckets = []
    private_buckets = []

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        list(tqdm(executor.map(lambda bucket_name: check_bucket_cli(profile, bucket_name, public_buckets, private_buckets, region, check_acl), bucket_names),
                  total=len(bucket_names), desc="Checking bucket"))

    return public_buckets, private_buckets

def enumerate_buckets_fuzz_cli(profile, bucket_template, wordlist, max_threads, region, check_acl):
    public_buckets = []
    private_buckets = []

    with open(wordlist, 'r') as file:
        words = file.read().splitlines()

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        list(tqdm(executor.map(lambda word: check_bucket_cli(profile, bucket_template.replace("FUZZ", word), public_buckets, private_buckets, region, check_acl), words),
                  total=len(words), desc="Checking bucket"))

    return public_buckets, private_buckets

def enumerate_buckets_http(url_template, region, wordlist, max_threads):
    public_buckets = []
    private_buckets = []

    with open(wordlist, 'r') as file:
        words = file.read().splitlines()

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        list(tqdm(executor.map(lambda word: check_bucket_http(url_template, region, word, public_buckets, private_buckets), words),
                  total=len(words), desc="Checking bucket on HTTP"))

    return public_buckets, private_buckets

def main():
    parser = argparse.ArgumentParser(description="Script per verificare i permessi su bucket S3")
    parser.add_argument("mode", choices=["cli", "http"], help="Modalità di esecuzione: cli o http")
    
    cli_group = parser.add_argument_group('CLI options')
    cli_group.add_argument("--s3list", help="File with a list of buckets for CLI mode")
    cli_group.add_argument("--string", help="String pattern with \"FUZZ\" to substitute for enumeration.")
    cli_group.add_argument("--profile", help="AWS profile to use")
    cli_group.add_argument("--region", help="AWS region")
    cli_group.add_argument("--acl", choices=["on", "off"], default="off", help="If your IP is blocked by an ACL on the bucket, enabling this option helps identify public buckets. Note this may not work in all cases.")

    parser.add_argument("--list", help="Wordlist file for `--string` mode or `--url`")
    
    http_group = parser.add_argument_group('HTTP options')
    http_group.add_argument("--url", help="URL pattern for HTTP mode, where \"FUZZ\" is replaced by each word in the wordlist")
    parser.add_argument("--threads", type=int, default=20, help="Number of threads to use (max 50)")

    args = parser.parse_args()

    if args.threads < 1 or args.threads > 50:
        print("Error: The number of threads must be between 1 and 50")
        sys.exit(1)

    check_acl = args.acl == "on"

    if args.mode == "cli":
        if args.profile is None or (args.s3list is None and args.string is None):
            print("Error: Provide --profile and (either --string or --list or just --s3list)")
            sys.exit(1)

        if args.s3list:
            with open(args.s3list, 'r') as file:
                bucket_names = file.read().splitlines()
            public_buckets, private_buckets = enumerate_buckets_cli(args.profile, bucket_names, args.threads, args.region, check_acl)
        elif args.string:
            if args.list is None:
                print("Error: If using --string, also provide --list")
                sys.exit(1)
            public_buckets, private_buckets = enumerate_buckets_fuzz_cli(args.profile, args.string, args.list, args.threads, args.region, check_acl)

    elif args.mode == "http":
        if args.url is None or args.list is None:
            print("Error: Supply --url and --list")
            sys.exit(1)

        public_buckets, private_buckets = enumerate_buckets_http(args.url, args.region, args.list, args.threads)

    print("\nPublic Buckets:")
    for bucket in public_buckets:
        if isinstance(bucket, tuple):
            print_green(bucket[0])
            print(bucket[1])
        else:
            print_green(bucket)

    print("\nPrivate Buckets:")
    for bucket in private_buckets:
        print_red(bucket)

if __name__ == "__main__":
    main()
