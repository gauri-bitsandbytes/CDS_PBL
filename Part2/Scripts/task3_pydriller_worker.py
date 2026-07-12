"""Mine one fixing commit and write the extracted methods to JSON.

This script exists because mining a repository with PyDriller can sometimes
crash or hang, especially when many external Git repositories are involved.
The main batch runner starts this worker as a separate Python process for each
commit. If one commit crashes, only this worker process fails; the whole batch
runner can continue with the next commit.
"""

# json is used to write the worker result as a small result.json file.
import json

# sys is used to read command-line arguments passed by task3_batch_runner.py.
import sys

# Repository is the PyDriller class that reads Git commits and changed files.
from pydriller import Repository


def extract_method_code(source_code, method):
    """Return only the source-code lines that belong to one method."""

    # Split the full Java file into individual lines.
    lines = source_code.splitlines()

    # PyDriller line numbers start at 1, while Python list indexes start at 0.
    # Therefore, method.start_line - 1 is used as the first Python index.
    return "\n".join(lines[method.start_line - 1:method.end_line])


def mine_commit(repo_url, commit_hash):
    """Extract vulnerable and fixed Java methods from one fixing commit."""

    # This list stores method versions after the fix.
    fixed_records = []

    # This list stores method versions before the fix.
    vulnerable_records = []

    # Ask PyDriller to inspect exactly one commit from the given repository.
    # PyDriller handles cloning the repository temporarily.
    fixing_commit = next(
        Repository(repo_url, single=commit_hash).traverse_commits()
    )

    # A fixing commit can modify one or many files.
    for modified_file in fixing_commit.modified_files:
        # This project focuses on Java methods, so non-Java files are skipped.
        if not modified_file.filename.endswith(".java"):
            continue

        # We need both the file after the fix and the file before the fix.
        # If either side is missing, we cannot create a vulnerable/fixed pair.
        if not modified_file.source_code or not modified_file.source_code_before:
            continue

        # Build a lookup table for methods before the fix.
        # The key is the long method name, which is more specific than just the
        # short method name because Java can overload methods.
        methods_before_by_long_name = {
            method.long_name: method
            for method in modified_file.methods_before
        }

        # changed_methods contains methods that PyDriller detected as changed.
        for fixed_method in modified_file.changed_methods:
            # Find the same method in the before-fix file.
            vulnerable_method = methods_before_by_long_name.get(
                fixed_method.long_name
            )

            # If the method did not exist before the commit, it was newly added.
            # A newly added method has no vulnerable previous version, so skip it.
            if vulnerable_method is None:
                continue

            # Extract the fixed method source code from the file after the fix.
            fixed_code = extract_method_code(
                modified_file.source_code,
                fixed_method
            )

            # Extract the vulnerable method source code from the file before the fix.
            vulnerable_code = extract_method_code(
                modified_file.source_code_before,
                vulnerable_method
            )

            # If the extracted method text is identical, the method did not
            # actually change in a useful way for this dataset.
            if fixed_code == vulnerable_code:
                continue

            # Save the fixed method version with vulnerable=False.
            fixed_records.append({
                "file_path": modified_file.new_path,
                "method_name": fixed_method.name,
                "method_long_name": fixed_method.long_name,
                "function_code": fixed_code,
                "vulnerable": False
            })

            # Save the before-fix method version with vulnerable=True.
            vulnerable_records.append({
                "file_path": modified_file.old_path,
                "method_name": vulnerable_method.name,
                "method_long_name": vulnerable_method.long_name,
                "function_code": vulnerable_code,
                "vulnerable": True
            })

    # Return vulnerable records first and fixed records second.
    return vulnerable_records + fixed_records


# The main runner passes these three command-line arguments:
# 1. repository URL
# 2. fixing commit hash
# 3. output JSON file path
repo_url = sys.argv[1]
commit_hash = sys.argv[2]
output_file = sys.argv[3]

try:
    # Try to mine this commit.
    result = {
        "methods": mine_commit(repo_url, commit_hash),
        "error": None
    }
except Exception as error:
    # If anything fails, return the error message instead of crashing silently.
    result = {
        "methods": [],
        "error": str(error)
    }

# Write the result to the output file so the parent runner can read it.
with open(output_file, "w", encoding="utf-8") as file:
    json.dump(result, file, ensure_ascii=False)
