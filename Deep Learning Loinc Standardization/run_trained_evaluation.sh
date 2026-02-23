#!/bin/bash
# Script to evaluate the trained model with similarity thresholding

# Activate virtual environment if needed
if [ -d "598_env" ]; then
    echo "Activating virtual environment..."
    source 598_env/bin/activate
fi

# Define directories and parameters
OUTPUT_DIR="results/extension2_trained_evaluation"
MODEL_PATH="results/extension2_triplet_training/checkpoints/encoder_model.weights.h5"
MIMIC_FILE="output/mimic_pairs_processed.csv"
LOINC_FILE="output/loinc_full_processed.csv"
D_LABITEMS_FILE="D_LABITEMS.csv"

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

if [ ! -f "$D_LABITEMS_FILE" ]; then
    echo "D_LABITEMS file not found: $D_LABITEMS_FILE"
    exit 1
fi

if [ ! -f "$MODEL_PATH" ]; then
    echo "Trained model weights not found: $MODEL_PATH"
    exit 1
fi

echo "========================================================"
echo "Creating custom loader for the trained model"
echo "========================================================"

# Create a temporary Python script to evaluate the trained model
cat > evaluate_trained_model.py << EOF
import tensorflow as tf
import numpy as np
import pandas as pd
import os
import sys

# Add parent directory to path to import from other modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    # Import required modules
    from models.t5_encoder import LOINCEncoder
    from thresholded_evaluation import evaluate_with_threshold
    
    # Create a new encoder model
    print("Creating a new encoder model...")
    model = LOINCEncoder(embedding_dim=128, dropout_rate=0.0)
    
    # Build the model with a dummy input
    _ = model(inputs=["dummy text"])
    
    # Load the trained weights
    model_path = "$MODEL_PATH"
    print(f"Loading trained weights from {model_path}...")
    model.load_weights(model_path)
    
    # Load test data
    print("Loading test data...")
    test_df = pd.read_csv("$MIMIC_FILE")
    loinc_df = pd.read_csv("$LOINC_FILE")
    
    # Prepare target_df with the required columns
    if 'TARGET' not in loinc_df.columns:
        if 'LONG_COMMON_NAME' in loinc_df.columns:
            loinc_df['TARGET'] = loinc_df['LONG_COMMON_NAME']
        elif 'DisplayName' in loinc_df.columns:
            loinc_df['TARGET'] = loinc_df['DisplayName']
        else:
            raise ValueError("LOINC data does not have TARGET, LONG_COMMON_NAME, or DisplayName column")
    
    # Load non-mappable codes
    print("Loading non-mappable codes...")
    labitems_df = pd.read_csv("$D_LABITEMS_FILE")
    non_mappable_df = labitems_df[labitems_df['LOINC_CODE'].isna()]
    print(f"Loaded {len(non_mappable_df)} non-mappable codes")
    
    # Run evaluation with thresholding
    print("Running thresholded evaluation...")
    results = evaluate_with_threshold(
        test_df=test_df,
        target_df=loinc_df,
        model=model,
        threshold=None,  # Calculate optimal threshold
        output_dir="$OUTPUT_DIR",
        include_non_mappable=True,
        non_mappable_df=non_mappable_df
    )
    
    # Save results
    results_df = pd.DataFrame([results])
    results_df.to_csv(os.path.join("$OUTPUT_DIR", "threshold_results.csv"), index=False)
    print(f"Saved results to {os.path.join('$OUTPUT_DIR', 'threshold_results.csv')}")
    
    # Print summary
    print("\n" + "="*80)
    print("EVALUATION SUMMARY")
    print("="*80)
    
    print(f"Threshold: {results['threshold']:.4f}")
    
    print(f"Mappable Classification:")
    print(f"- Precision: {results['mappable_precision']:.4f}")
    print(f"- Recall: {results['mappable_recall']:.4f}")
    print(f"- F1 Score: {results['mappable_f1']:.4f}")
    print(f"- SME Workload Reduction: {results['sme_workload_reduction']*100:.1f}%")
    print(f"- Hours saved per 1,000 lab codes: {results['sme_hours_saved_per_1000']:.1f}")
    
    print(f"Top-k Accuracy:")
    for k in [1, 3, 5]:
        if f'top{k}_accuracy' in results:
            print(f"- Top-{k}: {results[f'top{k}_accuracy']:.4f}")
    
    if 'mrr' in results:
        print(f"Mean Reciprocal Rank: {results['mrr']:.4f}")

if __name__ == "__main__":
    main()
EOF

echo "========================================================"
echo "Running evaluation with trained model"
echo "========================================================"

# Run the evaluation script
python evaluate_trained_model.py

# Check for successful execution
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to evaluate trained model"
    exit 1
fi

echo "========================================================"
echo "Evaluation completed!"
echo "========================================================"
echo "Results are available in: $OUTPUT_DIR" 