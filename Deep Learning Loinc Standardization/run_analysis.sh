#!/bin/bash
# Run error analysis and ablation studies for LOINC standardization model

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Activate virtual environment if it exists
if [ -d "598_env" ]; then
    source 598_env/bin/activate
    echo "Activated virtual environment"
fi

# Create output directories
mkdir -p results/error_analysis
mkdir -p results/ablation_study

# Define common paths
TEST_FILE="output/mimic_pairs_processed.csv"
AUGMENTED_TEST_FILE="output/mimic_pairs_augmented.csv"
LOINC_FILE="output/loinc_full_processed.csv"
EXPANDED_POOL="output/expanded_target_pool.csv"
CHECKPOINT_DIR="models/checkpoints"

echo "============================================================="
echo "RUNNING ERROR ANALYSIS"
echo "============================================================="

# Run error analysis for each fold
for FOLD in {0..4}; do
    echo "Running error analysis for fold $FOLD"
    python models/error_analysis.py \
        --test_file "$TEST_FILE" \
        --loinc_file "$LOINC_FILE" \
        --checkpoint_dir "$CHECKPOINT_DIR" \
        --fold "$FOLD" \
        --output_dir "results/error_analysis"
    
    # If augmented test file exists, run error analysis on it too
    if [ -f "$AUGMENTED_TEST_FILE" ]; then
        echo "Running error analysis on augmented test data for fold $FOLD"
        python models/error_analysis.py \
            --test_file "$AUGMENTED_TEST_FILE" \
            --loinc_file "$LOINC_FILE" \
            --checkpoint_dir "$CHECKPOINT_DIR" \
            --fold "$FOLD" \
            --output_dir "results/error_analysis/augmented"
    fi
    
    # If expanded pool exists, run error analysis with it too
    if [ -f "$EXPANDED_POOL" ]; then
        echo "Running error analysis with expanded target pool for fold $FOLD"
        python models/error_analysis.py \
            --test_file "$TEST_FILE" \
            --loinc_file "$EXPANDED_POOL" \
            --checkpoint_dir "$CHECKPOINT_DIR" \
            --fold "$FOLD" \
            --output_dir "results/error_analysis/expanded"
    fi
done

echo "============================================================="
echo "RUNNING ABLATION STUDIES"
echo "============================================================="

# Run ablation studies for each fold
for FOLD in {0..4}; do
    echo "Running ablation studies for fold $FOLD"
    python models/ablation_study.py \
        --test_file "$TEST_FILE" \
        --augmented_test_file "$AUGMENTED_TEST_FILE" \
        --loinc_file "$LOINC_FILE" \
        --expanded_pool "$EXPANDED_POOL" \
        --checkpoint_dir "$CHECKPOINT_DIR" \
        --fold "$FOLD" \
        --output_dir "results/ablation_study/fold$FOLD"
done

# Generate combined summary of all folds
echo "Generating combined summary of error analysis and ablation studies"
python -c "
import pandas as pd
import os
import glob

# Combine error analysis results
error_files = glob.glob('results/error_analysis/*_error_summary.txt')
with open('results/error_analysis_combined_summary.txt', 'w') as outfile:
    outfile.write('COMBINED ERROR ANALYSIS SUMMARY\n')
    outfile.write('=' * 80 + '\n\n')
    for file in error_files:
        fold = os.path.basename(file).split('_')[0]
        outfile.write(f'FOLD {fold}\n')
        outfile.write('-' * 40 + '\n')
        with open(file, 'r') as infile:
            outfile.write(infile.read())
        outfile.write('\n\n')

# Combine ablation study results
ablation_files = glob.glob('results/ablation_study/fold*/ablation_study_summary.txt')
with open('results/ablation_study_combined_summary.txt', 'w') as outfile:
    outfile.write('COMBINED ABLATION STUDY SUMMARY\n')
    outfile.write('=' * 80 + '\n\n')
    for file in ablation_files:
        fold = os.path.basename(os.path.dirname(file))
        outfile.write(f'{fold.upper()}\n')
        outfile.write('-' * 40 + '\n')
        with open(file, 'r') as infile:
            outfile.write(infile.read())
        outfile.write('\n\n')

print('Combined summaries generated!')
"

echo "============================================================="
echo "ANALYSIS COMPLETE"
echo "============================================================="
echo "Error analysis results: results/error_analysis_combined_summary.txt"
echo "Ablation study results: results/ablation_study_combined_summary.txt" 