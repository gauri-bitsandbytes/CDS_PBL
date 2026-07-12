## Cybersecurity Data Science PBL - Part 2

This folder contains the solution for Part 2 of the Cybersecurity Data Science PBL. The goal of this part is to create a labeled vulnerability dataset from ProjectKB by identifying fixing commits, mining the changed Java methods, and saving vulnerable/non-vulnerable method versions.

### Files

Recommended final structure:

```text
Part2/
|-- CDS_roject_part2.ipynb
|-- README.md
|-- Part2_steps_and_learnings.md
|-- Part2_steps_and_learnings.pdf
|-- projectkb_fix_commits.csv
|-- vulnerability_labeled_dataset.jsonl
`-- scripts/
    |-- task3_batch_runner.py
    |-- task3_pydriller_worker.py
    `-- retry_failed_commits.py
```

The local working folder may also contain temporary mining folders such as `ProjectKB`, `mining_outputs`, and `retry_outputs`. These are useful while running the project, but they do not need to be pushed as final submission files.

### Environment Setup

Create and activate a Conda environment:

```powershell
conda create -n ai_env python=3.10
conda activate ai_env
```

Install the packages required by the notebook:

```powershell
pip install pandas pyyaml pydriller
```

If your environment already has a `requirements.txt` for the full project, you can install from that instead:

```powershell
pip install -r requirements.txt
```

Open the notebook from inside the `Part2` folder:

```powershell
cd Part2
jupyter notebook CDS_roject_part2.ipynb
```

The notebook paths are written relative to the `Part2` folder, for example:

```text
ProjectKB/statements
projectkb_fix_commits.csv
mining_outputs/
vulnerability_labeled_dataset.jsonl
```

### What Was Given

The assignment points to ProjectKB:

```text
https://github.com/SAP/project-kb
```

ProjectKB contains YAML statements for vulnerabilities. These statements include CVE IDs, affected artifacts, and in many cases the repository URL and fixing commit hash.

### What Was Done

The notebook solves the project in four main tasks.

#### Task 1: Clone and inspect ProjectKB

ProjectKB was cloned locally. The relevant files are under:

```text
ProjectKB/statements
```

Each CVE folder may contain a `statement.yaml` file. The YAML files were inspected to find fixing commits.

#### Task 2: Extract fixing commits

The notebook scans all `statement.yaml` files and extracts:

- CVE ID
- fixing commit hash
- repository URL
- source YAML file path

The extracted table is saved as:

```text
projectkb_fix_commits.csv
```

Final Task 2 output:

```text
Rows: 1885
Unique CVEs: 1248
Unique fixing commits: 1793
Unique repositories: 621
```

This CSV is small and useful, so it should be kept in the repository.

#### Task 3: Mine vulnerable and fixed methods

PyDriller is used to inspect each fixing commit. For each changed Java file, the code tries to extract:

- the fixed method version after the commit
- the vulnerable method version before the commit

Only Java methods with both a before and after version are kept. Method pairs with identical before/after code are skipped.

The mining code processes commits in batches of 20 rows:

```text
BATCH_SIZE = 20
```

Batching is used because mining repositories can take a long time and can fail due to network issues, missing commits, repository format problems, or temporary disk limitations. The batch output files make it possible to resume work instead of restarting everything.

PyDriller is used directly with repository URLs, so repositories are cloned temporarily during mining instead of being permanently stored inside the project folder.

Task 3 writes intermediate files to:

```text
mining_outputs/
```

Example batch files:

```text
extracted_method_pairs_0_20.jsonl
mining_failures_0_20.jsonl
```

These intermediate files are useful locally, but they do not need to be pushed if the final dataset is already included.

#### Task 4: Create the labeled dataset

All extracted method JSONL files are combined into one final labeled dataset.

The final dataset is saved as:

```text
vulnerability_labeled_dataset.jsonl
```

JSONL was chosen instead of CSV because Java code can contain commas, quotes, semicolons, and newlines. JSONL stores one complete JSON object per line, which is safer for source-code text.

### Final Dataset

The final labeled dataset contains:

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

- `vulnerable = true`: method version before the fix
- `vulnerable = false`: method version after the fix

### Important Path Notes

The notebook should be run from inside the `Part2` folder. The paths are correct for this folder layout:

```text
Part2/
|-- CDS_roject_part2.ipynb
|-- ProjectKB/
|-- mining_outputs/
|-- projectkb_fix_commits.csv
`-- vulnerability_labeled_dataset.jsonl
```

If the notebook is run from the repository root instead, paths like `ProjectKB/statements` will not be found. In that case, either open the notebook from `Part2`, or change paths to include the `Part2/` prefix.

### Files To Push

Push these files:

```text
CDS_roject_part2.ipynb
README.md
Part2_steps_and_learnings.md
Part2_steps_and_learnings.pdf
projectkb_fix_commits.csv
vulnerability_labeled_dataset.jsonl
scripts/task3_batch_runner.py
scripts/task3_pydriller_worker.py
scripts/retry_failed_commits.py
```

Do not push these temporary/local files:

```text
ProjectKB/
mining_outputs/
mining_outputs_retry_backup_*/
retry_outputs/
__pycache__/
task3_mining.log
task3_mining_error.log
task3_mining_status.json
```

### Main Takeaways

- ProjectKB is used to identify CVEs and fixing commits.
- PyDriller is used to mine method-level changes from Git repositories.
- Vulnerable examples come from the method version before the fix.
- Non-vulnerable examples come from the method version after the fix.
- JSONL is better than CSV for this dataset because source code contains syntax characters and newlines.
- The final dataset is nearly balanced, with 7985 vulnerable and 8029 non-vulnerable method records.
