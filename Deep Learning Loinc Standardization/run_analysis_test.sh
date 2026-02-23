#!/bin/bash
# Run error analysis and ablation studies for LOINC standardization model (test version)

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Create output directories
mkdir -p results/error_analysis/test_run
mkdir -p results/ablation_study/test_run

# Define common paths
TEST_FILE="output/mimic_pairs_processed.csv"
LOINC_FILE="output/loinc_full_processed.csv"
EXPANDED_POOL="output/expanded_target_pool.csv"
CHECKPOINT_DIR="models/checkpoints"

echo "============================================================="
echo "RUNNING ERROR ANALYSIS"
echo "============================================================="

# Run error analysis for one fold
FOLD=0
echo "Running error analysis for fold $FOLD"
python models/error_analysis.py \
    --test_file "$TEST_FILE" \
    --loinc_file "$LOINC_FILE" \
    --checkpoint_dir "$CHECKPOINT_DIR" \
    --fold "$FOLD" \
    --output_dir "results/error_analysis/test_run"

echo "============================================================="
echo "RUNNING ABLATION STUDIES"
echo "============================================================="

# Run ablation studies for one fold
FOLD=0
echo "Running ablation studies for fold $FOLD"
python models/ablation_study.py \
    --test_file "$TEST_FILE" \
    --loinc_file "$LOINC_FILE" \
    --checkpoint_dir "$CHECKPOINT_DIR" \
    --fold "$FOLD" \
    --output_dir "results/ablation_study/test_run" \
    --components fine_tuning_stages data_augmentation

echo "============================================================="
echo "ANALYSIS COMPLETE"
echo "============================================================="
echo "Error analysis results: results/error_analysis/test_run/fold${FOLD}_error_summary.txt"
echo "Ablation study results: results/ablation_study/test_run/ablation_study_summary.txt" 