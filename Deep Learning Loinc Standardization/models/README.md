# LOINC Standardization Model

This directory contains the implementation of the LOINC standardization model as described in the paper "Automated LOINC Standardization Using Pre-trained Large Language Models".

## Model Architecture

The model uses a pre-trained Sentence-T5 (ST5-base) encoder as the backbone, with a projection layer to reduce the dimensionality of the embeddings from 768 to 128. The embeddings are L2-normalized before computing the triplet loss. The T5 backbone is kept frozen during training, and only the parameters of the projection layer are updated.

## Implementation Files

- `t5_encoder.py`: Defines the model architecture using ST5-base encoder
- `triplet_loss.py`: Implements the triplet loss function and mining strategies
- `triplet_mining.py`: Implements strategies for mining triplets from datasets
- `train.py`: Implements the two-stage fine-tuning strategy
- `evaluation.py`: Evaluates the model on the test set
- `inference.py`: Runs inference with the trained model

## Training Pipeline

The model is trained in two stages:

1. **Stage 1**: Fine-tuning using only LOINC target codes from the LOINC database
2. **Stage 2**: Fine-tuning using source-target pairs from MIMIC-III

The training uses contrastive learning with triplet loss and online triplet mining (hard or semi-hard negative mining).

## How to Run

Use the `run_model.sh` script in the root directory to run the model:

### Training

```bash
./run_model.sh train [options]
```

Options:
- `--loinc_file`: Path to processed LOINC CSV file (default: output/loinc_full_processed.csv)
- `--mimic_file`: Path to processed MIMIC-III pairs CSV file (default: output/mimic_pairs_processed.csv)
- `--fold_indices`: Path to stratified fold indices (default: output/stratified_folds.npy)
- `--output_dir`: Directory to save model checkpoints (default: models/checkpoints)
- `--stage1_only`: Only perform Stage 1 fine-tuning
- `--stage2_only`: Only perform Stage 2 fine-tuning
- `--mining_strategy`: Triplet mining strategy ('hard' or 'semi-hard', default: semi-hard)
- `--batch_size`: Batch size for training (default: 900)
- `--stage1_lr`: Learning rate for Stage 1 (default: 1e-4)
- `--stage2_lr`: Learning rate for Stage 2 (default: 1e-5)
- `--stage1_epochs`: Number of epochs for Stage 1 (default: 30)
- `--stage2_epochs`: Number of epochs for Stage 2 (default: 30)
- `--num_folds`: Number of folds for cross-validation (default: 5)

### Evaluation

```bash
./run_model.sh evaluate [options]
```

Options:
- `--mimic_file`: Path to processed MIMIC-III pairs CSV file (default: output/mimic_pairs_processed.csv)
- `--fold_indices`: Path to stratified fold indices (default: output/stratified_folds.npy)
- `--expanded_target_pool`: Path to expanded target pool for Type-2 evaluation (default: output/expanded_target_pool.txt)
- `--model_dir`: Directory containing model checkpoints (default: models/checkpoints)
- `--fold_idx`: Fold index to evaluate (default: 0)
- `--augmented`: Evaluate on augmented test set
- `--type2`: Perform Type-2 evaluation (unseen targets)

### Inference

```bash
./run_model.sh predict [source_text] [options]
```

Options:
- `--model_dir`: Directory containing model checkpoints (default: models/checkpoints)
- `--target_file`: Path to file containing target LOINC codes (default: output/expanded_target_pool.txt)
- `--fold_idx`: Fold index to use for loading Stage 2 model (default: 0)
- `--top_k`: Number of top predictions to return (default: 5)

## Examples

1. Train Stage 1 only:
```bash
./run_model.sh train --stage1_only --mining_strategy semi-hard
```

2. Train Stage 2 for fold 0 using the pre-trained Stage 1 model:
```bash
./run_model.sh train --stage2_only --fold_idx 0 --mining_strategy hard
```

3. Evaluate the model on fold 0 with the augmented test set:
```bash
./run_model.sh evaluate --fold_idx 0 --augmented
```

4. Perform Type-2 evaluation (unseen targets):
```bash
./run_model.sh evaluate --fold_idx 0 --type2
```

5. Predict LOINC codes for a source text:
```bash
./run_model.sh predict "hemoglobin blood" --top_k 10
``` 