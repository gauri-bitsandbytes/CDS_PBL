# Cybersecurity Data Science PBL - Part 3

This folder contains the solution for Part 3 of the Cybersecurity Data Science PBL. The task is to train a vulnerability classifier using the labeled method-level dataset created in Part 2, run inference on the challenge dataset, and submit the prediction CSV to the leaderboard.

The Part 3 notebook was executed in Google Colab because generating CodeBERT-family embeddings was too slow on the local CPU. The notebook is written for Google Colab execution, and a T4 GPU was selected from the Colab runtime settings.

## Files

```text
Part3/
|-- CDS_project_part3.ipynb
|-- README.md
|-- cds_challenge.jsonl
|-- part3_challenge_predictions_5.csv
`-- Leaderboard_Upload.pdf
```

## What Was Given

The challenge provides:

- `cds_challenge.jsonl`: unlabeled challenge dataset.
- A leaderboard upload page where the prediction CSV is submitted.

The project also uses the final dataset generated in Part 2:

```text
Part2/vulnerability_labeled_dataset.jsonl
```

This Part 2 dataset contains vulnerable and non-vulnerable Java method examples. It is used as the training data for Part 3.

## Google Colab Link

The runnable notebook was executed in Google Colab.

```text
Colab notebook link: https://colab.research.google.com/drive/1omlb6BhrbpMzujv94tSc8S_ll6aE7v2z?usp=sharing 
```

## Step-by-Step Execution

### Step 1: Open the Notebook in Google Colab

Upload or open `CDS_project_part3.ipynb` in Google Colab.

The first code cell mounts Google Drive:

```python
from google.colab import drive
drive.mount("/content/drive")
```

The next code cell sets the file paths for Colab execution:

```python
dataset_path = "/content/drive/MyDrive/CDS_Part3/vulnerability_labeled_dataset.jsonl"
challenge_path = "/content/drive/MyDrive/CDS_Part3/cds_challenge.jsonl"
submission_path = "/content/drive/MyDrive/CDS_Part3/part3_challenge_predictions_5.csv"
```

### Step 2: Select the T4 GPU Runtime

In Google Colab, select the GPU runtime before running the notebook:

```text
Runtime -> Change runtime type -> Hardware accelerator -> T4 GPU -> Save
```

The T4 GPU was used because the CodeBERT-family embedding step is much faster on GPU than on local CPU.

### Step 3: Upload the Required Files to Google Drive

Create this folder in Google Drive:

```text
MyDrive/CDS_Part3/
```

Place the required files there:

```text
vulnerability_labeled_dataset.jsonl
cds_challenge.jsonl
```

The first file comes from Part 2. The second file is the challenge file.

### Step 4: Install Required Packages

The notebook installs the main packages inside Colab:

```python
!pip install transformers scikit-learn matplotlib
```

Colab was used with a T4 GPU because it handles the transformer embedding model more efficiently than the local CPU environment.

### Step 5: Load the Labeled Dataset

The notebook loads:

```text
vulnerability_labeled_dataset.jsonl
```

The important columns are:

```text
function_code
vulnerable
```

The code text is used as input, and the `vulnerable` column is used as the binary label.

### Step 6: Split the Dataset

The dataset is split into:

```text
Training set
Validation set
Test set
```

The split is stratified so that vulnerable and non-vulnerable examples are represented in each subset.

The best working run used:

```text
Train size: 1000
Validation size: 250
Test size: 250
```

### Step 7: Create Code Embeddings

The implementation uses a CodeBERT-family model:

```text
huggingface/CodeBERTa-small-v1
```

This model converts Java method code into fixed-size numeric vectors. These vectors are then used as input features for the classifier.

The pipeline follows:

```text
source code -> tokens -> embeddings/vectors -> classifier -> vulnerable/non-vulnerable prediction
```

This approach is faster than fine-tuning a full transformer because the transformer is mainly used as a feature extractor.

### Step 8: Train the Classifier

The classifier is an MLP binary classifier trained on the CodeBERT-family embeddings.

The model predicts one output value for each method:

- closer to `1`: vulnerable
- closer to `0`: non-vulnerable

The notebook trains the classifier and plots the training and validation loss over epochs.

### Step 9: Tune the Threshold

The model outputs probabilities. A threshold is needed to convert probabilities into final labels.

The notebook tests multiple thresholds on the validation set and selects the threshold that gives the best F1-score.

The final submission used a threshold selected from validation/testing experiments. The saved prediction file in this folder is:

```text
part3_challenge_predictions_5.csv
```

### Step 10: Run Inference on the Challenge Dataset

The notebook loads:

```text
cds_challenge.jsonl
```

It creates embeddings for the challenge functions, predicts vulnerability labels, and saves the submission CSV.

The submission file contains:

```text
vul_id
is_vul
```

There is one `is_vul` prediction for each `vul_id`.

### Step 11: Upload the Prediction CSV

Upload this file to the leaderboard:

```text
part3_challenge_predictions_5.csv
```

The leaderboard result is saved as:

```text
Leaderboard_Upload.pdf
```

## Model and Method

The selected approach is:

```text
CodeBERT-family embeddings + MLP classifier
```

The embedding model is:

```text
huggingface/CodeBERTa-small-v1
```

The reason for this setup is that source code cannot be directly passed into a normal classifier as raw text. It first needs to be converted into a numeric representation. CodeBERT-family models are pretrained on programming-language data, so they are suitable for converting code functions into vectors.

The MLP classifier then learns to classify those vectors as vulnerable or non-vulnerable.

## Task 3 Model Parameter Experiment

Task 3 also requires changing model parameters after the first working run and comparing the new results with the previous results.

After confirming that the full pipeline worked, the classifier was changed from a smaller/basic MLP setup to a deeper MLP with more neurons and dropout:

```text
Input embedding size -> 256 neurons -> 128 neurons -> 1 output
```

The improved classifier structure is:

```text
Linear(input_size, 256)
ReLU
Dropout(0.4)
Linear(256, 128)
ReLU
Dropout(0.3)
Linear(128, 1)
```

The number of training examples was also increased compared with the first small test run. The first run was mainly used to check that loading, embedding generation, training, evaluation, and prediction saving worked correctly. After that, the larger run used:

```text
Train size: 1000
Validation size: 250
Test size: 250
```

The model was then retrained, the loss curve was regenerated, and the threshold was tuned again on the validation set.

The earlier small run produced a lower F1-score on the test set:

```text
Accuracy: 0.525
Precision: 0.65
Recall: 0.52
F1-score: 0.5777777777777777
```

After increasing the training data and using the improved MLP, the test-set result improved:

```text
Accuracy: 0.536
Precision: 0.5299539170506913
Recall: 0.8914728682170543
F1-score: 0.6647398843930635
```

The main improvement was recall. The improved model found more vulnerable examples, which is important in vulnerability detection because missing a vulnerable function is usually more serious than raising an extra false positive. Precision decreased compared with the smaller first run, but the overall F1-score improved because the balance between precision and recall became better for this task.

The leaderboard score also improved after tuning the model and threshold. The best submitted result is documented in:

```text
Leaderboard_Upload.pdf
```

## Evaluation

The notebook evaluates the model using:

- accuracy
- precision
- recall
- F1-score
- confusion matrix

F1-score is important for this task because the model needs to balance precision and recall. In vulnerability prediction, recall is also important because missed vulnerabilities are risky.

One validation/test run produced:

```text
Accuracy: 0.536
Precision: 0.5299539170506913
Recall: 0.8914728682170543
F1-score: 0.6647398843930635
```

The leaderboard result from the submitted CSV is documented in:

```text
Leaderboard_Upload.pdf
```

## Summary

Part 3 uses the labeled dataset from Part 2 to train a vulnerability classifier. The code functions are converted into embeddings using a CodeBERT-family model, an MLP classifier is trained on those embeddings, the decision threshold is tuned using validation results, and the final model is used to generate predictions for the challenge dataset.
