# Cybersecurity Data Science PBL - Part 2

This folder contains the solution for Part 2 of the Cybersecurity Data Science PBL. The task is to create a labeled vulnerability dataset from ProjectKB. The main idea is to start from CVE metadata, find the fixing commits, mine the changed Java methods, and save both vulnerable and fixed versions of the methods.

The final dataset is method-level data:

- `vulnerable = true` means the method version before the security fix.
- `vulnerable = false` means the method version after the security fix.

## Folder Structure

The Part 2 folder contains the notebook, the extracted fixing-commit table, the final labeled dataset, and helper scripts used for long mining runs.

```text
Part2/
|-- CDS_project_part2.ipynb
|-- README.md
|-- projectkb_fix_commits.csv
|-- vulnerability_labeled_dataset.jsonl
`-- Scripts/
    |-- task3_batch_runner.py
    |-- task3_pydriller_worker.py
    `-- retry_failed_commits.py
```

During local execution, temporary folders such as `ProjectKB`, `mining_outputs`, and `retry_outputs` may also be present. These folders are needed while running the project, but they are not part of the final GitHub submission because the final outputs are already saved separately.

## Environment Setup

The project was run using a Conda environment.

```powershell
conda create -n ai_env python=3.10
conda activate ai_env
```

The main packages used in this part are:

```powershell
pip install pandas pyyaml pydriller
```

The notebook is meant to be run from inside the `Part2` folder.

```powershell
cd Part2
jupyter notebook CDS_project_part2.ipynb
```

The paths in the notebook are written relative to the `Part2` folder, for example:

```text
ProjectKB/statements
projectkb_fix_commits.csv
mining_outputs/
vulnerability_labeled_dataset.jsonl
```

## Data Source

The data source for this part is SAP ProjectKB:

```text
https://github.com/SAP/project-kb
```

ProjectKB contains YAML files for vulnerabilities. The important folder is:

```text
ProjectKB/statements
```

Each CVE folder can contain a `statement.yaml` file. These YAML files may include:

- CVE ID
- vulnerability notes
- affected package artifacts
- repository URLs
- fixing commit hashes

Not every YAML file contains fixing commits. Files without fixing commits are still useful for understanding the vulnerability, but they cannot be used directly for method-level mining.

## CVE Meaning

CVE means Common Vulnerabilities and Exposures. A CVE is a public identifier for a known security vulnerability, for example:

```text
CVE-2008-1728
```

The CVE ID gives a standard name to a vulnerability so that researchers, developers, and security tools can refer to the same issue.

## Understanding the YAML Files

A `statement.yaml` file can contain sections such as:

```text
vulnerability_id
notes
artifacts
fixes
```

The `artifacts` section lists package versions and whether they are affected. For example, `affected: true` means that package version is vulnerable, and `affected: false` means that package version is not vulnerable.

The `fixes` section is the most important part for this task because it connects a CVE to the source-code repository and the commit that fixed the vulnerability.

The useful mapping is:

```text
CVE -> repository URL -> fixing commit
```

This mapping is created in Task 2 and then used in Task 3.

## Task 1: Inspect ProjectKB

In Task 1, ProjectKB is cloned and the vulnerability statement files are inspected. The useful CVE files are stored under:

```text
ProjectKB/statements
```

The result of Task 1 was understanding where the CVE metadata is stored and how the YAML files are structured.

## Task 2: Extract Fixing Commits

In Task 2, all `statement.yaml` files are scanned and the fixing-commit information is extracted.

For every useful YAML file, the following fields are extracted:

- CVE ID
- repository URL
- fixing commit hash
- YAML file path

The output of Task 2 is:

```text
projectkb_fix_commits.csv
```

The important columns are:

```text
cve_id
fix_commit
yaml_file
repository_url
```

This CSV file is important because it is the bridge between ProjectKB and PyDriller. It tells the mining code exactly which repositories and commits need to be inspected.

Final Task 2 output:

```text
Rows: 1885
Unique CVEs: 1248
Unique fixing commits: 1793
Unique repositories: 621
```

The final labeled vulnerability dataset is not created directly in Task 2. The complete flow is:

```text
Task 2 -> projectkb_fix_commits.csv
Task 3 -> mining_outputs/extracted_method_pairs_*.jsonl
Task 4 -> vulnerability_labeled_dataset.jsonl
```

## Task 3: Mine Vulnerable and Fixed Methods

In Task 3, PyDriller is used to inspect the fixing commits from `projectkb_fix_commits.csv`.

For each fixing commit, the mining step tries to extract:

- the vulnerable method version before the fix
- the fixed method version after the fix

The vulnerable version usually comes from the parent commit, which is the commit immediately before the fix. The fixed version comes from the fixing commit itself.

For each changed Java method, two dataset records are created:

- one record for the before-fix method, labeled `vulnerable = true`
- one record for the after-fix method, labeled `vulnerable = false`

Task 3 processes commits in batches of 20 rows. This made the mining process easier to resume because mining many repositories can take a long time and can fail due to network issues, missing commits, repository problems, or disk-space limitations.

Example intermediate files from Task 3 (batches of 20 for 1885 records):

```text
mining_outputs/extracted_method_pairs_0_20.jsonl 
mining_outputs/mining_failures_0_20.jsonl
```

The `extracted_method_pairs_*.jsonl` files contain mined vulnerable/fixed method versions. The `mining_failures_*.jsonl` files contain commits that could not be mined successfully.

## Notebook and Helper Scripts

The original assignment was provided as a Jupyter notebook, and the notebook contains the main task structure. For Task 3, helper scripts are also included because mining all repositories can take hours and is more stable from the terminal than inside a Jupyter kernel.

The helper scripts are:

```text
Scripts/task3_batch_runner.py
Scripts/task3_pydriller_worker.py
Scripts/retry_failed_commits.py
```

Their roles are:

- `task3_batch_runner.py` reads `projectkb_fix_commits.csv`, processes commits in batches, saves progress, and writes mined outputs.
- `task3_pydriller_worker.py` mines one repository/commit using PyDriller in a separate process.
- `retry_failed_commits.py` retries failed commits and can recover additional method records.

The script workflow is:

```text
CDS_project_part2.ipynb
        |
        | Task 2 creates projectkb_fix_commits.csv
        v
Scripts/task3_batch_runner.py
        |
        | reads projectkb_fix_commits.csv
        | processes fixing commits in batches
        | starts one worker process per commit
        v
Scripts/task3_pydriller_worker.py
        |
        | mines one repository/commit using PyDriller
        | extracts before-fix and after-fix Java methods
        v
mining_outputs/extracted_method_pairs_*.jsonl
mining_outputs/mining_failures_*.jsonl
        |
        | optional retry of failed commits
        v
Scripts/retry_failed_commits.py
        |
        | retries failed commits
        | inserts recovered records back into mining outputs
        v
CDS_project_part2.ipynb
        |
        | Task 4 combines extracted method files
        v
vulnerability_labeled_dataset.jsonl
```

Task 3 can be run either inside the notebook or through the scripts. Both approaches create the same type of output files in `mining_outputs/`. The scripts are useful for the long mining workflow because they are safer for a long run and easier to resume.

## Task 4: Create the Final Dataset

In Task 4, all mined method files are combined into one final labeled dataset.

Task 4 reads files matching:

```text
mining_outputs/extracted_method_pairs_*.jsonl
```

Then it combines the records, removes duplicates, and saves:

```text
vulnerability_labeled_dataset.jsonl
```

JSONL is used instead of CSV for the final method dataset because Java source code can contain commas, quotes, semicolons, and newlines. JSONL stores one complete JSON object per line, which is safer for code text.

## Final Dataset

The final dataset file is:

```text
vulnerability_labeled_dataset.jsonl
```

Final dataset summary:

```text
Total records: 16014
Vulnerable records: 7985
Non-vulnerable records: 8029
Unique CVEs: 659
Unique repositories: 270
Unique fixing commits: 1130
CVE year range: 2008 to 2022
Source batch files combined: 94
```

Each record contains:

```text
function_code
vulnerable
cve_id
repository_url
fix_commit
file_path
method_name
method_long_name
source_file
```

The label meaning is:

- `vulnerable = true`: method code before the fix
- `vulnerable = false`: method code after the fix

## Files Included in the Repository

The Part 2 repository folder contains the files needed to understand and reuse the solution:

```text
CDS_project_part2.ipynb
README.md
projectkb_fix_commits.csv
vulnerability_labeled_dataset.jsonl
Scripts/task3_batch_runner.py
Scripts/task3_pydriller_worker.py
Scripts/retry_failed_commits.py
```

## Local Files Not Included

Some files and folders were used locally while running the project, but they are not included in the repository.

```text
ProjectKB/
mining_outputs/
mining_outputs_retry_backup_*/
retry_outputs/
__pycache__/
.ipynb_checkpoints/
task3_mining.log
task3_mining_error.log
task3_mining_status.json
```

These files are local execution artifacts:

- `ProjectKB/` is the cloned external SAP ProjectKB repository.
- `mining_outputs/` contains intermediate mining batches.
- `retry_outputs/` and `mining_outputs_retry_backup_*/` contain retry and backup files from failed-commit recovery.
- `__pycache__/` is created automatically by Python.
- `.ipynb_checkpoints/` is created automatically by Jupyter.
- `task3_mining.log`, `task3_mining_error.log`, and `task3_mining_status.json` are local progress/debug files.


The final combined dataset is already saved in `vulnerability_labeled_dataset.jsonl`, so the intermediate mining folders are not uploaded in the GitHub repository.

## Main Learning

ProjectKB does not directly provide a ready-made machine-learning dataset. It provides vulnerability metadata. That metadata is used to find fixing commits, and Git history is inspected through PyDriller to create a supervised dataset.

The main transformation is:

```text
ProjectKB CVE metadata
        |
        v
repository URL and fixing commit
        |
        v
before-fix Java method + after-fix Java method
        |
        v
labeled vulnerable/non-vulnerable method dataset
```

In simple words, ProjectKB gives the commit that fixed a CVE. The fixing commit is inspected, the method before the commit is labeled as vulnerable, the method after the commit is labeled as non-vulnerable, and both versions are saved for later machine-learning use.
