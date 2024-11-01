# S3Fuzzer

S3Fuzzer is a tool for enumerating and verifying permissions on S3 buckets in Amazon AWS. It helps identify if a bucket exists and determines its visibility (public or private) using AWS CLI or HTTP requests. Ideal for penetration testers and system administrators, S3Fuzzer is optimized for fast, parallel enumeration.

## Requirements

- **AWS CLI**: Must be installed and configured, with at least one saved profile (option --profile).
- **Python3** and packages in requirements.txt:

```
tqdm
requests
```

Install packages with:

```
pip install -r requirements.txt
```
## Usage Modes

The tool offers two modes: **CLI** and **HTTP**.


1. Uses AWS CLI to list S3 bucket contents. Can operate in two modes: --string and --s3list.

    String Mode (--string)
    Enables checking by replacing FUZZ in a string with each word from the wordlist.

    Example command:

        $ python3 s3fuzzer.py cli --string com.domain.FUZZ --list ~/Documents/git/SecLists/Discovery/Web-Content/raft-small-directories.txt --profile watcher --region eu-central-1 --threads 30 

        


    List Mode (--s3list)
    Reads a list of S3 buckets from a file and checks each bucket with an `ls` command. The list should contain one bucket per line.

    Example command:

        $ python3 s3fuzzer.py cli --profile watcher --s3list test.txt --region eu-central-1

    
2. HTTP Mode
Checks bucket visibility using HTTP requests, determining if a bucket is public or private.

    Example command:

        $ python3 s3fuzzer.py http --url com.domain.FUZZ --list ./short.txt --region eu-central-1 --threads 30

## Options

- **--profile**: AWS profile to use.
- **--threads**: Number of threads for parallel scanning (max 64).
- **--region**: AWS region, required for HTTP requests.
- **--list**: Wordlist file for `--string` mode or `--url`.
- **--s3list**: File with a list of buckets for CLI mode.
- **--string**: String pattern with "FUZZ" to substitute for enumeration.
- **--url**: URL pattern for HTTP mode, where "FUZZ" is replaced by each word in the wordlist.
- **--acl**: If your IP is blocked by an ACL on the bucket, enabling this option helps identify public buckets. Note this may not work in all cases and is disabled by default.
