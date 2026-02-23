# LOINC Code Standardization on MIMIC-III using Contrastive Sentence-T5

This example demonstrates how to use PyHealth for standardizing local laboratory codes from the MIMIC-III dataset to standard LOINC codes using a contrastive learning approach with sentence transformer embeddings. This is an implementation of the methodology described in the paper ["Automated LOINC Standardization Using Pre-trained Large Language Models"](https://arxiv.org/abs/xxxx.xxxxx).

## Contents

- `run_loinc_mapping.py`: Python script demonstrating the end-to-end workflow
- `run_loinc_mapping.ipynb`: Jupyter notebook with the same content
- `download_weights.sh`: Script to download pre-trained Stage 1 weights
- `test_implementation.py`: Script to test the implementation
- `README.md`: This file

## Overview

Medical code mapping is a critical task in healthcare interoperability, as institutions often use their own local codes to record laboratory tests and clinical observations. This example shows how to build a system that can automatically map these local codes to standardized LOINC (Logical Observation Identifiers Names and Codes) terminology.

The approach has two stages:
1. **Stage 1**: Fine-tune a sentence transformer model on the LOINC ontology using contrastive learning
2. **Stage 2**: Further fine-tune the model on source-target pairs from MIMIC-III

We provide pre-trained weights for Stage 1 to make this example practical and runnable without requiring a large amount of computational resources.

## Requirements

### Data

- **MIMIC-III dataset**: You must have access to the MIMIC-III dataset, which requires credentialed access through [PhysioNet](https://physionet.org/content/mimiciii/). Specifically, you need the `d_labitems.csv` file.
- **LOINC Table**: (Optional) For full functionality, download the LOINC table from [LOINC.org](https://loinc.org/) (requires free registration).

### Python Dependencies

- PyHealth
- torch
- sentence-transformers
- scikit-learn
- pandas
- numpy
- matplotlib (for visualization)
- tqdm

Install all required dependencies:

```bash
pip install pyhealth torch scikit-learn sentence-transformers pandas numpy matplotlib tqdm
```

## Dataset Description

The MIMIC3LOINCMappingDataset processes laboratory items from MIMIC-III's `d_labitems.csv` file and extracts source-target pairs:

- **Source**: The local laboratory code description, created by concatenating the `label` and `fluid` fields
- **Target**: The corresponding LOINC code

The dataset supports data augmentation as described in the paper, including character-level random deletion, word-level random swapping, and word deletion.

## Model Architecture

The ContrastiveSentenceTransformer model consists of:

1. A pre-trained sentence transformer encoder backbone
2. An optional projection layer that maps the encoder outputs to a lower-dimensional space (128 dimensions by default)
3. L2 normalization of the final embeddings

The model is trained using triplet loss with either hard negative or semi-hard negative mining strategies. The training has two stages:

1. **Stage 1**: Fine-tuning on the LOINC ontology (pre-trained weights provided)
2. **Stage 2**: Fine-tuning on source-target pairs from MIMIC-III

## Running the Example

### Step 1: Download Pre-trained Weights

```bash
cd examples/loinc_mapping_mimic3
chmod +x download_weights.sh
./download_weights.sh
```

This will download or generate dummy Stage 1 pre-trained weights to the `weights/` directory.

### Step 2: Run the Python Script or Jupyter Notebook

#### Option 1: Python Script

```bash
python run_loinc_mapping.py \
    --mimic3_dir /path/to/mimic3/ \
    --loinc_table /path/to/LoincTable.csv \
    --stage1_weights ./weights/
```

#### Option 2: Jupyter Notebook

```bash
jupyter notebook run_loinc_mapping.ipynb
```

Update the paths in the notebook to point to your data.

### Step 3: Test the Implementation

```bash
python test_implementation.py
```

This will run a series of tests to verify that all components are working correctly.

## Expected Outputs

The example will:

1. Load and process the MIMIC-III d_labitems dataset
2. Load the pre-trained Stage 1 weights
3. Perform Stage 2 fine-tuning on MIMIC-III source-target pairs
4. Evaluate the model using Top-k accuracy metrics
5. Show example predictions for a few sample source texts

Expected performance (may vary depending on data and model size):
- Top-1 accuracy: ~60-65%
- Top-3 accuracy: ~75-80%
- Top-5 accuracy: ~80-85%

## Citation

If you use this code or the pre-trained weights, please cite the original paper:

```
@article{tu2023automated,
  title={Automated LOINC Standardization Using Pre-trained Large Language Models},
  author={Tu, Tao and Loreaux, Eric and Chesley, Emma and Lelkes, Adam D. and Gamble, Paul and Bellaiche, Mathias and Seneviratne, Martin and Chen, Ming-Jun},
  journal={arXiv},
  year={2023}
}
```

## Acknowledgements

This implementation is based on the methodology described in "Automated LOINC Standardization Using Pre-trained Large Language Models" and utilizes pre-trained models from the Sentence-Transformers library. 