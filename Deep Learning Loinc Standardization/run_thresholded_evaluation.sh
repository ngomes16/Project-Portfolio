#!/bin/bash
# Script to run the thresholded evaluation for non-mappable LOINC codes

# Activate virtual environment if needed
if [ -d "598_env" ]; then
    echo "Activating virtual environment..."
    source 598_env/bin/activate
fi

# Define directories and parameters
OUTPUT_DIR="results/extension2_thresholded"
MODELS_DIR="models/checkpoints"
TEST_FILE="output/mimic_pairs_processed.csv"
LOINC_FILE="output/loinc_full_processed.csv"
D_LABITEMS_FILE="D_LABITEMS.csv"

# Make sure output directory exists
mkdir -p $OUTPUT_DIR

# Check if required files exist
if [ ! -f "$TEST_FILE" ]; then
    echo "Test file not found: $TEST_FILE"
    exit 1
fi

if [ ! -f "$LOINC_FILE" ]; then
    echo "LOINC file not found: $LOINC_FILE"
    exit 1
fi

if [ ! -f "$D_LABITEMS_FILE" ]; then
    echo "D_LABITEMS file not found: $D_LABITEMS_FILE"
    exit 1
fi

# Check if model checkpoints exist
if [ ! -d "$MODELS_DIR" ] || [ -z "$(ls -A $MODELS_DIR)" ]; then
    echo "Model checkpoints not found in $MODELS_DIR"
    exit 1
fi

echo "========================================================"
echo "STEP 1: Generate and analyze negative mining dataset"
echo "========================================================"
python negative_mining.py \
    --test_file $TEST_FILE \
    --loinc_file $LOINC_FILE \
    --d_labitems_file $D_LABITEMS_FILE \
    --output_dir "$OUTPUT_DIR/negative_mining" \
    --generate_triplets

# Check for successful execution
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to generate negative mining dataset"
    echo "Continuing with next steps..."
fi

echo "========================================================"
echo "STEP 2: Run evaluation with similarity thresholding"
echo "========================================================"

# Run for all available folds
echo "Looking for available model folds..."
FOLDS=$(ls $MODELS_DIR/stage2_fold*_model.weights.h5 2>/dev/null | sed 's/.*fold\([0-9]\)_model.*/\1/' | sort -u)

if [ -z "$FOLDS" ]; then
    echo "No model folds found in $MODELS_DIR"
    exit 1
fi

echo "Found folds: $FOLDS"

for FOLD in $FOLDS; do
    FOLD_IDX=$((FOLD - 1))  # Convert to 0-indexed
    echo "========================================================"
    echo "Running evaluation for fold $FOLD (index $FOLD_IDX)"
    echo "========================================================"
    
    # Run thresholded evaluation
    python thresholded_evaluation.py \
        --test_file $TEST_FILE \
        --loinc_file $LOINC_FILE \
        --d_labitems_file $D_LABITEMS_FILE \
        --checkpoint_dir $MODELS_DIR \
        --fold $FOLD_IDX \
        --output_dir "$OUTPUT_DIR/fold$FOLD_IDX" \
        --batch_size 16
    
    # Check for successful execution
    if [ $? -ne 0 ]; then
        echo "WARNING: Evaluation for fold $FOLD failed"
    fi
done

echo "========================================================"
echo "STEP 3: Run evaluation with pre-specified threshold (0.8)"
echo "========================================================"

# Use a fixed threshold for comparison
THRESHOLD=0.8

echo "Running evaluation with fixed threshold: $THRESHOLD"
python thresholded_evaluation.py \
    --test_file $TEST_FILE \
    --loinc_file $LOINC_FILE \
    --d_labitems_file $D_LABITEMS_FILE \
    --checkpoint_dir $MODELS_DIR \
    --fold 0 \
    --output_dir "$OUTPUT_DIR/fixed_threshold" \
    --batch_size 16 \
    --threshold $THRESHOLD

# Check for successful execution
if [ $? -ne 0 ]; then
    echo "WARNING: Evaluation with fixed threshold failed"
fi

echo "========================================================"
echo "STEP 4: Combine and compare results"
echo "========================================================"

# Combine results from all folds and calculate averages
echo "Aggregating results from all evaluations..."
python - << EOF
import pandas as pd
import os
import glob

# Find all results files
results_files = glob.glob("$OUTPUT_DIR/**/threshold_results.csv", recursive=True)
print(f"Found {len(results_files)} result files")

if results_files:
    # Read and combine all results
    all_results = []
    for file in results_files:
        try:
            df = pd.read_csv(file)
            folder = os.path.basename(os.path.dirname(file))
            df['fold'] = folder
            all_results.append(df)
        except Exception as e:
            print(f"Error reading {file}: {e}")
    
    if all_results:
        # Combine results
        combined_df = pd.concat(all_results, ignore_index=True)
        
        # Calculate averages
        avg_results = combined_df.groupby('fold').mean().reset_index()
        overall_avg = combined_df.mean(numeric_only=True).to_frame().T
        overall_avg['fold'] = 'average'
        avg_results = pd.concat([avg_results, overall_avg], ignore_index=True)
        
        # Save combined results
        combined_df.to_csv("$OUTPUT_DIR/all_results.csv", index=False)
        avg_results.to_csv("$OUTPUT_DIR/average_results.csv", index=False)
        
        # Print summary
        print("\nSUMMARY OF RESULTS:")
        print(f"Evaluation runs: {len(all_results)}")
        print("\nAverage Metrics:")
        for metric in ['threshold', 'mappable_precision', 'mappable_recall', 'mappable_f1', 
                      'top1_accuracy', 'top3_accuracy', 'top5_accuracy', 'sme_workload_reduction']:
            if metric in overall_avg.columns:
                print(f"- {metric}: {overall_avg[metric].iloc[0]:.4f}")
        
        print("\nDetailed results saved to:")
        print(f"- $OUTPUT_DIR/all_results.csv")
        print(f"- $OUTPUT_DIR/average_results.csv")
    else:
        print("No valid results found")
else:
    print("No result files found")
EOF

echo "========================================================"
echo "Thresholded evaluation completed!"
echo "========================================================"
echo "Results are available in: $OUTPUT_DIR"
echo "Check the average_results.csv file for a summary of the evaluation metrics" 