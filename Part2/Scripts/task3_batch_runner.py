"""Standalone Task 3 runner for mining fixing commits.

The notebook version of Task 3 is correct, but mining many repositories from a
Jupyter notebook can be fragile. It can take hours, the kernel may crash, and
some repositories can fail. This script runs the same mining idea in a safer
standalone way:

1. Read projectkb_fix_commits.csv from Task 2.
2. Process commits in small batches.
3. Start a separate worker process for each commit.
4. Save mined method records to mining_outputs/*.jsonl.
5. Save failures separately so they can be retried later.

The script is a helper for long-running mining. It is not a separate assignment
task; it supports the notebook workflow.
"""

# json is used to write and read status/result files.
import json

# os is used to pass environment variables to child processes.
import os

# shutil is used to remove temporary folders after each worker finishes.
import shutil

# subprocess starts task3_pydriller_worker.py as a child process.
import subprocess

# sys gives us the current Python executable path.
import sys

# tempfile creates temporary folders for PyDriller/Git work.
import tempfile
from pathlib import Path

import pandas as pd


# BASE_DIR is the Part2 folder where this script is stored.
BASE_DIR = Path(__file__).resolve().parent

# Task 2 output: table of CVEs, repositories, and fixing commits.
CSV_FILE = BASE_DIR / "projectkb_fix_commits.csv"

# Folder where this script writes mined method pairs and failures.
OUTPUT_DIR = BASE_DIR / "mining_outputs"

# Worker script that mines exactly one commit.
WORKER_FILE = BASE_DIR / "task3_pydriller_worker.py"

# Lock file prevents accidentally running two mining jobs at the same time.
LOCK_FILE = BASE_DIR / "task3_mining.lock"

# Status file records progress so the user can see what is currently running.
STATUS_FILE = BASE_DIR / "task3_mining_status.json"

# Number of rows from projectkb_fix_commits.csv processed together.
BATCH_SIZE = 20

# Columns used for successfully extracted method records.
METHOD_COLUMNS = [
    "cve_id",
    "repository_url",
    "fix_commit",
    "file_path",
    "method_name",
    "method_long_name",
    "function_code",
    "vulnerable",
]

# Columns used for failed commits.
FAILURE_COLUMNS = [
    "cve_id",
    "fix_commit",
    "repository_url",
    "reason",
]


def update_status(state, **details):
    # Build one dictionary containing the current state and extra details.
    status = {"state": state, **details}

    # Write to a temporary file first to avoid corrupting the status file.
    temporary_file = STATUS_FILE.with_suffix(".json.tmp")
    temporary_file.write_text(json.dumps(status, indent=2), encoding="utf-8")

    # Replace the real status file only after the temporary write succeeds.
    temporary_file.replace(STATUS_FILE)


def is_git_url(repo_url):
    # PyDriller can mine Git repositories but not old SVN URLs.
    return (
        isinstance(repo_url, str)
        and not repo_url.startswith("svn://")
        and "svn." not in repo_url
    )


def mine_commit_safely(repo_url, commit_hash):
    # Create a temporary folder for this one commit.
    # This helps avoid filling the project folder with cloned repositories.
    temp_folder = tempfile.mkdtemp(prefix="pydriller_commit_")

    # The worker writes its result here.
    result_file = Path(temp_folder) / "result.json"

    # Start from the current environment variables.
    environment = os.environ.copy()

    # Force temporary Git/PyDriller files into our temporary folder.
    environment["TEMP"] = temp_folder
    environment["TMP"] = temp_folder

    # Enable long file paths for Git on Windows.
    environment["GIT_CONFIG_COUNT"] = "1"
    environment["GIT_CONFIG_KEY_0"] = "core.longpaths"
    environment["GIT_CONFIG_VALUE_0"] = "true"

    try:
        # Run the worker as a separate process.
        # If PyDriller crashes for one commit, the parent script can continue.
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

        # If the worker did not write a result file, treat it as a failure.
        if not result_file.exists():
            return [], "Mining worker did not create a result file"

        # Read the worker result.
        result = json.loads(result_file.read_text(encoding="utf-8"))

        # The worker stores exceptions as result["error"].
        if result["error"]:
            return [], result["error"]

        # Return extracted method records and no error.
        return result["methods"], None
    finally:
        # Always remove the temporary folder, even if mining failed.
        shutil.rmtree(temp_folder, ignore_errors=True)


def mine_range(fix_commits_df, start_index, end_index):
    # Select a slice of the Task 2 fixing-commit table.
    selected_commits = fix_commits_df.iloc[start_index:end_index]

    # Successful extracted methods are stored here.
    method_records = []

    # Failed commits are stored here.
    mining_failures = []

    # Go through each row in the selected batch.
    for row_number, (_, row) in enumerate(selected_commits.iterrows(), start=1):
        # Read the values needed by PyDriller.
        cve_id = row["cve_id"]
        repo_url = row["repository_url"]
        commit_hash = row["fix_commit"]

        print(
            f"[{row_number}/{len(selected_commits)}] "
            f"Processing: {cve_id} {commit_hash}",
            flush=True,
        )
        update_status(
            "running",
            batch=f"{start_index}:{end_index}",
            row=row_number,
            rows_in_batch=len(selected_commits),
            cve_id=cve_id,
            fix_commit=commit_hash,
        )

        if not is_git_url(repo_url):
            # Save non-Git URLs as failures instead of crashing.
            mining_failures.append(
                {
                    "cve_id": cve_id,
                    "fix_commit": commit_hash,
                    "repository_url": repo_url,
                    "reason": "Repository URL is not a Git URL",
                }
            )
            continue

        methods, error = mine_commit_safely(repo_url, commit_hash)
        if error:
            # Save the error message so it can be inspected or retried later.
            print(f"Could not inspect commit: {error}", flush=True)
            mining_failures.append(
                {
                    "cve_id": cve_id,
                    "fix_commit": commit_hash,
                    "repository_url": repo_url,
                    "reason": error,
                }
            )
            continue

        for method in methods:
            # Add CVE/repository/commit metadata to every method record.
            method_records.append(
                {
                    "cve_id": cve_id,
                    "repository_url": repo_url,
                    "fix_commit": commit_hash,
                    **method,
                }
            )

    # Convert records into DataFrames with stable columns.
    methods_df = pd.DataFrame(method_records, columns=METHOD_COLUMNS)
    failures_df = pd.DataFrame(mining_failures, columns=FAILURE_COLUMNS)
    return selected_commits, methods_df, failures_df


def save_batch(methods_df, failures_df, method_file, failure_file):
    # Write to temporary files first.
    # This prevents half-written files from being treated as complete batches.
    method_temp_file = method_file.with_suffix(".jsonl.tmp")
    failure_temp_file = failure_file.with_suffix(".jsonl.tmp")

    # Save successful method records as JSONL.
    methods_df.to_json(
        method_temp_file,
        orient="records",
        lines=True,
        force_ascii=False,
    )
    # Save failed commit records as JSONL.
    failures_df.to_json(
        failure_temp_file,
        orient="records",
        lines=True,
        force_ascii=False,
    )

    # Atomically replace final batch files after writing succeeds.
    method_temp_file.replace(method_file)
    failure_temp_file.replace(failure_file)


def run():
    # Create mining_outputs if it does not exist.
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Load Task 2 output.
    fix_commits_df = pd.read_csv(CSV_FILE)

    # Count how many commit rows need to be processed.
    total_rows = len(fix_commits_df)

    print("Task 3 standalone batch runner", flush=True)
    print("Total fixing-commit rows:", total_rows, flush=True)
    print("Repository mode: temporary PyDriller clones", flush=True)
    print("Crash protection: one child process per commit", flush=True)

    for start_index in range(0, total_rows, BATCH_SIZE):
        # Compute the end index for the current batch.
        end_index = min(start_index + BATCH_SIZE, total_rows)

        # File for successfully mined method versions.
        method_file = (
            OUTPUT_DIR
            / f"extracted_method_pairs_{start_index}_{end_index}.jsonl"
        )
        # File for commits that failed in this batch.
        failure_file = (
            OUTPUT_DIR / f"mining_failures_{start_index}_{end_index}.jsonl"
        )

        if method_file.exists() and failure_file.exists():
            # If both files exist, this batch has already completed.
            # This makes the runner resumable.
            print(
                f"Skipping completed range {start_index}:{end_index}",
                flush=True,
            )
            continue

        # Mine this batch and save the output files.
        print(f"\nProcessing range {start_index}:{end_index}", flush=True)
        selected, methods_df, failures_df = mine_range(
            fix_commits_df,
            start_index,
            end_index,
        )
        save_batch(methods_df, failures_df, method_file, failure_file)

        # Print a short summary for the finished batch.
        print("Selected fixing-commit rows:", len(selected), flush=True)
        print("Extracted method-version rows:", len(methods_df), flush=True)
        print("Failure rows:", len(failures_df), flush=True)

    update_status("complete", total_rows=total_rows)
    print("\nTask 3 batch processing is complete.", flush=True)


try:
    # Create a lock file using exclusive creation mode.
    # If it already exists, another run may still be active.
    lock_handle = open(LOCK_FILE, "x", encoding="utf-8")
except FileExistsError:
    print("Task 3 is already running, or a stale lock file exists.")
    sys.exit(1)

try:
    # Store the process ID in the lock file for debugging.
    lock_handle.write(str(os.getpid()))
    lock_handle.close()
    # Mark the job as starting and then run the full mining process.
    update_status("starting")
    run()
except Exception as error:
    # If the script fails, record the error in the status file.
    update_status("failed", error=str(error))
    raise
finally:
    # Remove the lock file when the script exits.
    LOCK_FILE.unlink(missing_ok=True)
