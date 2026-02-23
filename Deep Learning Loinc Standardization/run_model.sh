#!/bin/bash

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "Activating virtual environment..."
    source 598_env/bin/activate
fi

# Parse command-line arguments
COMMAND=$1
shift

if [[ "$COMMAND" == "train" ]]; then
    # Run training
    echo "Running training with arguments: $@"
    python models/train.py "$@"
elif [[ "$COMMAND" == "evaluate" ]]; then
    # Run evaluation
    echo "Running evaluation with arguments: $@"
    python models/evaluation.py "$@"
elif [[ "$COMMAND" == "predict" ]]; then
    # Run inference
    echo "Running prediction with arguments: $@"
    python models/inference.py "$@"
elif [[ "$COMMAND" == "test" ]]; then
    # Run a quick test with a small dataset
    echo "Running test with a small dataset..."
    python models/train.py --loinc_file output/loinc_targets_processed.csv --test_mode --checkpoint_dir models/checkpoints
else
    # Display help
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  train      Train the LOINC standardization model"
    echo "  evaluate   Evaluate the model on test data"
    echo "  predict    Make predictions with the model"
    echo "  test       Run a quick test with a small dataset"
    echo ""
    echo "Examples:"
    echo "  $0 train --loinc_file output/loinc_targets_processed.csv --stage1_only"
    echo "  $0 train --loinc_file output/loinc_targets_processed.csv --mimic_file output/mimic_pairs_processed.csv"
    echo "  $0 evaluate --fold_idx 0"
    echo "  $0 predict \"hemoglobin blood\""
    echo ""
fi 