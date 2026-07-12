## Cybersecurity Data Science PBL - Part 1

This folder contains the solution for Part 1 of the Cybersecurity Data Science PBL. The task is to load a provided validation dataset, run a provided pretrained vulnerability prediction model, and manually evaluate the model performance.

### Files

```text
Part1/
|-- CDS_project_part1.ipynb
|-- LAB-Intro.pdf
|-- model_2023-03-28_20-03.pth
|-- requirements.txt
|-- student_dataset.hdf5
`-- README.md
```

### Environment Setup

Create and activate a Conda environment:

```powershell
conda create -n ai_env python=3.10
conda activate ai_env
```

Install the required packages from inside the `Part1` folder:

```powershell
cd Part1
pip install -r requirements.txt
```

If running in VS Code or Jupyter, select the `ai_env` Python interpreter/kernel before executing the notebook.

### What Was Given

The lab provides:

- `student_dataset.hdf5`: validation dataset in HDF5 format.
- `model_2023-03-28_20-03.pth`: pretrained PyTorch model weights.
- `requirements.txt`: dependency file used to recreate the Python environment for this notebook.
- `LAB-Intro.pdf`: lab description and task instructions.

The dataset contains code samples represented as numeric vectors. Each sample has a binary label:

- `1`: vulnerable
- `0`: non-vulnerable

### What Was Done

The notebook performs the following steps:

1. Loads the HDF5 validation dataset using `h5py`.
2. Reads the feature vectors, labels, and original source-code samples.
3. Converts NumPy arrays into PyTorch tensors.
4. Creates a `TensorDataset` and `DataLoader` for batch prediction.
5. Displays 10 random samples with their labels.
6. Computes dataset statistics.
7. Recreates the provided neural network architecture.
8. Loads pretrained model weights from `model_2023-03-28_20-03.pth`.
9. Runs inference on the validation dataset.
10. Manually calculates TP, TN, FP, FN.
11. Manually calculates accuracy, precision, recall, and F1-score.
12. Answers the theory questions about metric interpretation.

### Technique Used

The solution uses a pretrained PyTorch neural network for binary vulnerability classification.

The model architecture is:

```text
Input vector size: 768
Linear(768, 64)
ReLU
Linear(64, 64)
ReLU
Linear(64, 1)
Sigmoid
```

The model outputs a probability between 0 and 1. A threshold of `0.5` is used:

- probability >= 0.5 means vulnerable
- probability < 0.5 means non-vulnerable

The threshold of `0.5` is the default decision threshold for binary classification. We kept this threshold because the task is to evaluate the provided pretrained model, not to retrain or optimize it. A lower threshold could increase recall, but it would also create more false positives.

Batch processing is done with `DataLoader` using batch size `64`, which allows the model to process multiple samples efficiently during inference.

### Dataset Findings

The validation dataset contains:

```text
Total samples: 1000
Vulnerable samples: 283
Non-vulnerable samples: 717
Vulnerable / non-vulnerable ratio: 0.3947
```

This means the dataset contains more non-vulnerable examples than vulnerable examples.

### Model Results

Using threshold `0.5`, the model produced:

```text
True Positives: 20
True Negatives: 716
False Positives: 1
False Negatives: 263
```

The manually computed metrics were:

```text
Accuracy: 0.736
Precision: 0.952
Recall: 0.071
F1-score: 0.132
```

### Interpretation

The accuracy looks acceptable because the model correctly predicts most non-vulnerable samples. However, accuracy is misleading here because the model misses most vulnerable samples.

The recall is very low:

```text
Recall = 0.071
```

This means the model finds only a small fraction of the actually vulnerable samples.

For vulnerability prediction, recall is very important because missing a real vulnerability can be more harmful than raising a false alarm. F1-score is more informative than accuracy because it combines precision and recall, but recall should still be inspected directly.

The low recall also shows an important limitation of the provided pretrained model at the default threshold. The model is very conservative: when it predicts vulnerable, it is usually correct, but it misses many actual vulnerable examples. In a real security setting, this threshold might be adjusted depending on whether the priority is fewer false alarms or fewer missed vulnerabilities.

### How To Run

From the repository root:

```powershell
cd Part1
jupyter notebook CDS_project_part1.ipynb
```

Or open `CDS_project_part1.ipynb` in VS Code/Jupyter and run all cells from top to bottom.

The notebook expects these files to be in the same `Part1` folder:

```text
student_dataset.hdf5
model_2023-03-28_20-03.pth
```
