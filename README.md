# Cybersecurity Data Science PBL

This repository contains the three parts of the Cybersecurity Data Science PBL project. The project starts with evaluating a provided vulnerability prediction model, then builds a labeled vulnerability dataset from ProjectKB, and finally trains a machine-learning model to predict vulnerable source-code functions.

## Contributors

- Gauri Gajanan Amin (670328)
- Ishan Vyas (679660)
- Rohit Purohit (670203)

## Repository Structure

```text
CDS_PBL/
|-- README.md
|-- .gitignore
|-- Part1/
|   |-- CDS_project_part1.ipynb
|   |-- README.md
|   |-- model_2023-03-28_20-03.pth
|   |-- requirements.txt
|   `-- student_dataset.hdf5
|-- Part2/
|   |-- CDS_project_part2.ipynb
|   |-- README.md
|   |-- projectkb_fix_commits.csv
|   |-- vulnerability_labeled_dataset.jsonl
|   `-- Scripts/
|       |-- retry_failed_commits.py
|       |-- task3_batch_runner.py
|       `-- task3_pydriller_worker.py
`-- Part3/
    |-- CDS_project_part3.ipynb
    |-- README.md
    |-- cds_challenge.jsonl
    |-- part3_challenge_predictions_5.csv
    `-- Leaderboard_Upload.pdf
```

Each part also has its own README with detailed setup, execution steps, methods, and results.

## Part 1: Pretrained Model Evaluation

Part 1 loads a provided validation dataset and evaluates a provided pretrained PyTorch vulnerability prediction model.

Main files:

```text
Part1/CDS_project_part1.ipynb
Part1/student_dataset.hdf5
Part1/model_2023-03-28_20-03.pth
Part1/requirements.txt
```

The notebook:

1. Loads the HDF5 validation dataset.
2. Reads feature vectors, labels, and code samples.
3. Recreates the provided neural network architecture.
4. Loads pretrained model weights.
5. Runs inference.
6. Manually calculates accuracy, precision, recall, and F1-score.
7. Interprets the results.

The provided model uses a default threshold of `0.5` for binary classification.

## Part 2: Building the Vulnerability Dataset

Part 2 creates a labeled method-level dataset from SAP ProjectKB.

Data source:

```text
https://github.com/SAP/project-kb
```

The workflow is:

```text
ProjectKB CVE metadata
        |
        v
repository URL + fixing commit
        |
        v
PyDriller mining of before/after Java methods
        |
        v
vulnerability_labeled_dataset.jsonl
```

Important files:

```text
Part2/projectkb_fix_commits.csv
Part2/vulnerability_labeled_dataset.jsonl
Part2/Scripts/
```

`projectkb_fix_commits.csv` is generated from ProjectKB YAML files and contains the CVE-to-fixing-commit mapping.

Final Task 2 extraction summary:

```text
Rows: 1885
Unique CVEs: 1248
Unique fixing commits: 1793
Unique repositories: 621
```

Task 3 uses PyDriller to mine the vulnerable and fixed method versions from the fixing commits. Task 4 combines the mined method records into the final dataset.

Final labeled dataset:

```text
Part2/vulnerability_labeled_dataset.jsonl
```

Final dataset summary:

```text
Total records: 16014
Vulnerable records: 7985
Non-vulnerable records: 8029
```

JSONL is used because Java source code can contain commas, quotes, semicolons, and newlines.

## Part 3: Vulnerability Prediction Model

Part 3 trains a vulnerability classifier using the labeled dataset from Part 2 and creates predictions for the challenge dataset.

Important files:

```text
Part3/CDS_project_part3.ipynb
Part3/cds_challenge.jsonl
Part3/part3_challenge_predictions_5.csv
Part3/Leaderboard_Upload.pdf
```

The selected method is:

```text
CodeBERT-family embeddings + MLP classifier
```

The notebook uses:

```text
huggingface/CodeBERTa-small-v1
```

The code functions are converted into fixed-size numeric embeddings. These embeddings are then passed into an MLP binary classifier.

Part 3 was executed in Google Colab with a T4 GPU because embedding generation with a transformer model was slow on local CPU.

The challenge prediction file contains:

```text
vul_id
is_vul
```

The submitted prediction file is:

```text
Part3/part3_challenge_predictions_5.csv
```

The leaderboard result is saved as:

```text
Part3/Leaderboard_Upload.pdf
```

## Environment Notes

Part 1 was run with a local Conda environment:

```powershell
conda create -n ai_env python=3.10
conda activate ai_env
```

Part 2 also uses the same environment with packages such as:

```text
pandas
pyyaml
pydriller
```

Part 3 was run in Google Colab with:

```text
Runtime -> Change runtime type -> Hardware accelerator -> T4 GPU
```

## Local Files Not Included

Temporary execution files and large intermediate folders are intentionally excluded through `.gitignore`.

Examples:

```text
Part2/ProjectKB/
Part2/mining_outputs/
Part2/retry_outputs/
Part2/task3_mining.log
Part3/Google Colab/
__pycache__/
.ipynb_checkpoints/
```

These files are not required because the final notebooks, scripts, extracted CSV, final labeled JSONL dataset, challenge prediction CSV, and leaderboard result are included in the repository.

## How To Review

For a quick review, open the README inside each part:

```text
Part1/README.md
Part2/README.md
Part3/README.md
```

Then inspect or run the corresponding notebook:

```text
Part1/CDS_project_part1.ipynb
Part2/CDS_project_part2.ipynb
Part3/CDS_project_part3.ipynb
```

Part 3 is best reviewed through the linked Google Colab notebook mentioned in `Part3/README.md`.

