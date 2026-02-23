#!/bin/bash
# Script to run triplet training with negative examples

# Activate virtual environment if needed
if [ -d "598_env" ]; then
    echo "Activating virtual environment..."
    source 598_env/bin/activate
fi

# Define directories and parameters
OUTPUT_DIR="results/extension2_triplet_training"
MODELS_DIR="models/checkpoints"
MIMIC_FILE="output/mimic_pairs_processed.csv"
LOINC_FILE="output/loinc_full_processed.csv"
TRIPLETS_FILE="results/extension2_thresholded/negative_mining/negative_triplets.csv"
EPOCHS=5
BATCH_SIZE=16

# Make sure output directory exists
mkdir -p $OUTPUT_DIR

# Check if required files exist
if [ ! -f "$MIMIC_FILE" ]; then
    echo "MIMIC file not found: $MIMIC_FILE"
    exit 1
fi

if [ ! -f "$LOINC_FILE" ]; then
    echo "LOINC file not found: $LOINC_FILE"
    exit 1
fi

if [ ! -f "$TRIPLETS_FILE" ]; then
    echo "Triplets file not found: $TRIPLETS_FILE"
    exit 1
fi

# Check if model checkpoints exist
if [ ! -d "$MODELS_DIR" ] || [ -z "$(ls -A $MODELS_DIR)" ]; then
    echo "Model checkpoints not found in $MODELS_DIR"
    exit 1
fi

echo "========================================================"
echo "Running triplet training with negative examples"
echo "========================================================"

# Run for fold 0 (index 0)
python triplet_negative_training.py \
    --triplets_file $TRIPLETS_FILE \
    --validation_file $MIMIC_FILE \
    --loinc_file $LOINC_FILE \
    --checkpoint_dir $MODELS_DIR \
    --fold 0 \
    --output_dir $OUTPUT_DIR \
    --batch_size $BATCH_SIZE \
    --epochs $EPOCHS

# Check for successful execution
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to run triplet training"
    exit 1
fi

echo "========================================================"
echo "Run thresholded evaluation with the trained model"
echo "========================================================"

# Run thresholded evaluation with the trained model
python thresholded_evaluation.py \
    --test_file $MIMIC_FILE \
    --loinc_file $LOINC_FILE \
    --d_labitems_file "D_LABITEMS.csv" \
    --checkpoint_dir "$OUTPUT_DIR/checkpoints" \
    --fold 0 \
    --output_dir "$OUTPUT_DIR/evaluation" \
    --batch_size $BATCH_SIZE

# Check for successful execution
if [ $? -ne 0 ]; then
    echo "WARNING: Evaluation with trained model failed"
fi

echo "========================================================"
echo "Triplet training completed!"
echo "========================================================"
echo "Results are available in: $OUTPUT_DIR"
echo "Trained model is available in: $OUTPUT_DIR/checkpoints" 