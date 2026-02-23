#!/bin/bash

# Activate virtual environment
echo "Activating virtual environment..."
source 598_env/bin/activate

# Run the basic preprocessing
echo "Running basic preprocessing..."
python main.py

# Run the enhanced preprocessing with data augmentation
echo "Running enhanced preprocessing with data augmentation..."
python main_augmented.py

# Run the advanced preprocessing for model training
echo "Running advanced preprocessing for model training..."
python advanced_preprocessing.py

# Print summary
echo ""
echo "All processing complete. The following files have been generated:"
echo ""
echo "Basic Preprocessing Files:"
echo "  - loinc_targets_processed.csv: Processed LOINC targets (10% sample)"
echo "  - mimic_pairs_processed.csv: Processed MIMIC-III source-target pairs"
echo "  - stage1_training_examples.csv: Examples for Stage 1 training (target-only)"
echo "  - stage2_training_examples.csv: Examples for Stage 2 training (source-target pairs)"
echo ""
echo "Advanced Preprocessing Files:"
echo "  - loinc_full_processed.csv: Full LOINC dataset for laboratory and clinical categories"
echo "  - stratified_folds.npy: 5-fold cross-validation splits"
echo "  - stage1_triplets.txt: Triplets for Stage 1 contrastive learning"
echo "  - stage2_fold*_triplets.txt: Triplets for Stage 2 contrastive learning by fold"
echo "  - expanded_target_pool.txt: Expanded target LOINC codes for Type-2 testing"
echo ""
echo "The data is now ready for model training as described in the paper."
echo "See README.md for more details on the methodology and next steps." 