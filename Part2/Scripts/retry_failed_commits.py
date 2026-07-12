"""Retry failed Task 3 mining commits and optionally apply recovered methods.

During repository mining, some commits can fail because of network problems,
temporary GitHub issues, missing commits, or PyDriller/Git checkout errors.
The main runner saves those failures in mining_outputs/mining_failures_*.jsonl.

This script reads those failure files, retries the failed commits, and writes
the retry result into retry_outputs/. If --apply is used, successful retry
records are inserted back into the original mining_outputs batch files.
"""

# argparse reads command-line flags such as --apply.
import argparse

# json reads and writes JSONL files.
import json

# os is used to pass environment variables to child worker processes.
import os

# re extracts batch numbers from filenames.
import re

# shutil copies backups and removes temporary folders.
import shutil

# subprocess starts task3_pydriller_worker.py for each retry.
import subprocess

# sys gives the current Python executable path.
import sys

# tempfile creates temporary folders for retry mining.
import tempfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd


# BASE_DIR is the Part2 folder where this script is stored.
BASE_DIR = Path(__file__).resolve().parent

# Original Task 3 mining output folder.
OUTPUT_DIR = BASE_DIR / "mining_outputs"

# Worker script that mines one commit.
WORKER_FILE = BASE_DIR / "task3_pydriller_worker.py"

# Folder where retry results are written.
RETRY_DIR = BASE_DIR / "retry_outputs"


def read_jsonl(path):
    # Read a JSONL file into a list of dictionaries.
    records = []

    # If the file does not exist, return an empty list.
    if not path.exists():
        return records

    # Read one JSON object per non-empty line.
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))

    return records


def write_jsonl(path, records):
    # Write a list of dictionaries as one JSON object per line.
    with open(path, "w", encoding="utf-8") as file:
        for record in records:
            json.dump(record, file, ensure_ascii=False)
            file.write("\n")


def batch_from_failure_file(path):
    # Failure files are named like mining_failures_0_20.jsonl.
    # This extracts the start and end indexes from that filename.
    match = re.search(r"mining_failures_(\d+)_(\d+)\.jsonl$", path.name)
    if not match:
        raise ValueError(f"Unexpected failure filename: {path.name}")

    return int(match.group(1)), int(match.group(2))


def normalized_repo_url(repo_url):
    # Normalize repository URLs so the same URL with/without trailing slash matches.
    return str(repo_url).strip().rstrip("/")


def is_retryable_git_url(repo_url):
    # Skip old SVN URLs because this retry script uses Git/PyDriller.
    url = normalized_repo_url(repo_url).lower()
    if "svn." in url or "/repos/asf/" in url or url.startswith("svn://"):
        return False

    return url.startswith(("http://", "https://", "git://", "git@"))


def record_key(record):
    # Create a unique identity for a mined method record.
    # This prevents adding the same method twice during retry application.
    return (
        record.get("cve_id"),
        record.get("repository_url"),
        record.get("fix_commit"),
        record.get("file_path"),
        record.get("method_long_name"),
        record.get("vulnerable"),
        record.get("function_code"),
    )


def failure_key(record):
    # Create a unique identity for a failed commit.
    return (
        record.get("cve_id"),
        record.get("fix_commit"),
        normalized_repo_url(record.get("repository_url")),
    )


def mine_commit_safely(repo_url, commit_hash):
    # Create a temporary folder for this retry attempt.
    temp_folder = tempfile.mkdtemp(prefix="pydriller_retry_")

    # The child worker writes its result here.
    result_file = Path(temp_folder) / "result.json"

    # Copy current environment variables.
    environment = os.environ.copy()

    # Force temp files into the retry temp folder.
    environment["TEMP"] = temp_folder
    environment["TMP"] = temp_folder
    environment["GIT_CONFIG_COUNT"] = "1"
    environment["GIT_CONFIG_KEY_0"] = "core.longpaths"
    environment["GIT_CONFIG_VALUE_0"] = "true"

    try:
        # Run the same one-commit worker used by the batch runner.
        process = subprocess.run(
            [
                sys.executable,
                str(WORKER_FILE),
                repo_url,
                commit_hash,
                str(result_file),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=environment,
        )

        if process.returncode != 0:
            return [], f"Mining worker crashed with exit code {process.returncode}"

        # If no result file is produced, the retry failed.
        if not result_file.exists():
            return [], "Mining worker did not create a result file"

        # Load worker result.
        result = json.loads(result_file.read_text(encoding="utf-8"))
        if result["error"]:
            return [], result["error"]

        return result["methods"], None
    finally:
        # Clean up temporary clone/files after every retry.
        shutil.rmtree(temp_folder, ignore_errors=True)


def collect_failures():
    # Collect unique failures from all mining_failures_*.jsonl files.
    failures = []
    seen = set()

    # Go through each original failure file.
    for failure_file in sorted(OUTPUT_DIR.glob("mining_failures_*.jsonl")):
        # Remember which original batch this failure came from.
        start, end = batch_from_failure_file(failure_file)

        for record in read_jsonl(failure_file):
            key = failure_key(record)
            if key in seen:
                continue

            seen.add(key)
            retry_record = dict(record)
            retry_record["repository_url"] = normalized_repo_url(
                retry_record["repository_url"]
            )
            retry_record["batch_start"] = start
            retry_record["batch_end"] = end
            retry_record["failure_file"] = failure_file.name
            retry_record["method_file"] = (
                f"extracted_method_pairs_{start}_{end}.jsonl"
            )
            failures.append(retry_record)

    return failures


def existing_method_keys():
    # Build a set of all method records that already exist.
    # This avoids adding duplicate method records after a retry.
    keys = set()

    for method_file in sorted(OUTPUT_DIR.glob("extracted_method_pairs_*.jsonl")):
        for record in read_jsonl(method_file):
            keys.add(record_key(record))

    return keys


def backup_files(paths):
    # Before modifying original mining output files, make a timestamped backup.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BASE_DIR / f"mining_outputs_retry_backup_{timestamp}"
    backup_dir.mkdir()

    for path in sorted(set(paths)):
        if path.exists():
            shutil.copy2(path, backup_dir / path.name)

    return backup_dir


def batch_commit_order(start, end):
    # Re-read the original Task 2 commit table to recover the original order
    # of commits inside a batch.
    fix_commits_df = pd.read_csv(BASE_DIR / "projectkb_fix_commits.csv")
    selected = fix_commits_df.iloc[start:end]
    order = {}

    for position, (_, row) in enumerate(selected.iterrows()):
        key = (
            row["cve_id"],
            row["fix_commit"],
            normalized_repo_url(row["repository_url"]),
        )
        order[key] = position

    return order


def method_batch_position(record, batch_order):
    # Return the original position of this commit inside its batch.
    key = (
        record.get("cve_id"),
        record.get("fix_commit"),
        normalized_repo_url(record.get("repository_url")),
    )
    return batch_order.get(key, 10**9)


def method_version_position(record):
    # Keep vulnerable versions before fixed versions, matching the worker output.
    return 0 if record.get("vulnerable") is True else 1


def apply_successes(success_records):
    # Insert successful retry results back into original mining_outputs files.
    affected_failure_files = set()
    affected_method_files = set()

    for record in success_records:
        affected_failure_files.add(OUTPUT_DIR / record["failure_file"])
        affected_method_files.add(OUTPUT_DIR / record["method_file"])

    # Back up all files that will be modified.
    backup_dir = backup_files(affected_failure_files | affected_method_files)

    additions_by_method_file = defaultdict(list)
    successful_failure_keys = set()

    for success in success_records:
        # Track which failure rows should be removed after successful recovery.
        successful_failure_keys.add(
            (
                success["cve_id"],
                success["fix_commit"],
                normalized_repo_url(success["repository_url"]),
                success["failure_file"],
            )
        )
        additions_by_method_file[success["method_file"]].extend(
            success["methods"]
        )

    for method_name, additions in additions_by_method_file.items():
        # Load the original method output file for this batch.
        method_path = OUTPUT_DIR / method_name
        start, end = batch_from_failure_file(
            Path(method_name.replace("extracted_method_pairs", "mining_failures"))
        )
        batch_order = batch_commit_order(start, end)
        records = read_jsonl(method_path)
        keys = {record_key(record) for record in records}

        for addition in additions:
            # Add recovered method records only if they are not duplicates.
            key = record_key(addition)
            if key not in keys:
                records.append(addition)
                keys.add(key)

        records = [
            (index, record)
            for index, record in enumerate(records)
        ]
        # Sort so recovered records are placed near their original batch position.
        records.sort(
            key=lambda item: (
                method_batch_position(item[1], batch_order),
                method_version_position(item[1]),
                item[0],
            )
        )
        records = [record for _, record in records]

        write_jsonl(method_path, records)

    for failure_path in affected_failure_files:
        # Remove failure rows for commits that are now successfully recovered.
        records = read_jsonl(failure_path)
        kept = []

        for record in records:
            key = (
                record.get("cve_id"),
                record.get("fix_commit"),
                normalized_repo_url(record.get("repository_url")),
                failure_path.name,
            )
            if key not in successful_failure_keys:
                kept.append(record)

        write_jsonl(failure_path, kept)

    return backup_dir


def main():
    # Build the command-line interface.
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Insert successful retries into the original batch files.",
    )
    args = parser.parse_args()

    # Create retry_outputs if it does not exist.
    RETRY_DIR.mkdir(exist_ok=True)

    # Read all original failures.
    failures = collect_failures()

    # Read already existing mined method keys to avoid duplicates.
    existing_keys = existing_method_keys()
    successes = []
    remaining_failures = []
    skipped = []

    print("Failed commits to retry:", len(failures), flush=True)

    # Retry each failed commit one by one.
    for index, failure in enumerate(failures, start=1):
        cve_id = failure["cve_id"]
        repo_url = failure["repository_url"]
        commit_hash = failure["fix_commit"]

        print(
            f"[{index}/{len(failures)}] Retrying {cve_id} {commit_hash}",
            flush=True,
        )

        if not is_retryable_git_url(repo_url):
            # Some failures are not retryable because they are not Git URLs.
            retry_failure = dict(failure)
            retry_failure["retry_reason"] = "Skipped non-Git/SVN URL"
            skipped.append(retry_failure)
            continue

        methods, error = mine_commit_safely(repo_url, commit_hash)

        if error:
            # Store retry failure reason for later inspection.
            retry_failure = dict(failure)
            retry_failure["retry_reason"] = error
            remaining_failures.append(retry_failure)
            continue

        enriched_methods = []
        for method in methods:
            # Add the CVE/repo/commit metadata back to worker method records.
            record = {
                "cve_id": cve_id,
                "repository_url": repo_url,
                "fix_commit": commit_hash,
                **method,
            }
            if record_key(record) not in existing_keys:
                enriched_methods.append(record)
                existing_keys.add(record_key(record))

        if not enriched_methods:
            # Retry may succeed technically but produce no usable method pairs.
            retry_failure = dict(failure)
            retry_failure["retry_reason"] = (
                "Retry succeeded but produced no new method records"
            )
            remaining_failures.append(retry_failure)
            continue

        success_record = dict(failure)
        success_record["methods"] = enriched_methods
        success_record["new_method_records"] = len(enriched_methods)
        successes.append(success_record)

    # Save retry results as separate files.
    retry_success_file = RETRY_DIR / "retry_successes.jsonl"
    retry_failure_file = RETRY_DIR / "retry_failures_remaining.jsonl"
    retry_skipped_file = RETRY_DIR / "retry_skipped.jsonl"

    write_jsonl(retry_success_file, successes)
    write_jsonl(retry_failure_file, remaining_failures)
    write_jsonl(retry_skipped_file, skipped)

    backup_dir = None
    if args.apply and successes:
        # Apply recovered methods to original mining_outputs files only when requested.
        backup_dir = apply_successes(successes)

    # Write a small summary JSON for the retry run.
    summary = {
        "retried": len(failures),
        "successfully_recovered_commits": len(successes),
        "new_method_records": sum(
            success["new_method_records"] for success in successes
        ),
        "remaining_failures": len(remaining_failures),
        "skipped": len(skipped),
        "applied_to_original_files": bool(args.apply),
        "backup_dir": str(backup_dir) if backup_dir else None,
        "retry_success_file": str(retry_success_file),
        "retry_failure_file": str(retry_failure_file),
        "retry_skipped_file": str(retry_skipped_file),
    }

    summary_file = RETRY_DIR / "retry_summary.json"
    summary_file.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
