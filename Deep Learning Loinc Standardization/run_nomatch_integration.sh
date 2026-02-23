#!/bin/bash

# Activate virtual environment
source 598_env/bin/activate

# Default parameters
MIMIC_FILE="mimic_pairs_processed.csv"
LOINC_FILE="loinc_targets_processed.csv"
D_LABITEMS_FILE="D_LABITEMS.csv"
CHECKPOINT_DIR="models/checkpoints"
FOLD=0
OUTPUT_DIR="results/nomatch_integration"
INPUT_FILE=""
THRESHOLD="-0.35"
TOP_K=5
BATCH_SIZE=16
SEED=42

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --mimic_file)
      MIMIC_FILE="$2"
      shift 2
      ;;
    --loinc_file)
      LOINC_FILE="$2"
      shift 2
      ;;
    --d_labitems_file)
      D_LABITEMS_FILE="$2"
      shift 2
      ;;
    --checkpoint_dir)
      CHECKPOINT_DIR="$2"
      shift 2
      ;;
    --fold)
      FOLD="$2"
      shift 2
      ;;
    --output_dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --threshold)
      THRESHOLD="$2"
      shift 2
      ;;
    --input_file)
      INPUT_FILE="$2"
      shift 2
      ;;
    --top_k)
      TOP_K="$2"
      shift 2
      ;;
    --batch_size)
      BATCH_SIZE="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Create output directory
mkdir -p $OUTPUT_DIR

# Check if input file is provided
if [[ -z "$INPUT_FILE" ]]; then
  echo "Error: Input file is required. Please provide --input_file parameter."
  exit 1
fi

# Create a temporary file with a formatted version of the input
TEMP_MIMIC_FILE="${OUTPUT_DIR}/temp_input.csv"

# Convert input file to the expected format (with SOURCE, LOINC_NUM columns)
python -c "
import pandas as pd
import sys

# Read input file
input_df = pd.read_csv('$INPUT_FILE')

# Check for required columns and convert to standard format
if 'ITEMID' in input_df.columns and 'source_text' in input_df.columns:
    # Create a copy with renamed columns
    output_df = input_df.copy()
    output_df = output_df.rename(columns={
        'source_text': 'SOURCE',
        'ITEMID': 'LOINC_NUM'  # Temporary, will be replaced during processing
    })
    # Use ITEMID also as the LOINC_NUM for now (will be ignored/replaced during processing)
    output_df.to_csv('$TEMP_MIMIC_FILE', index=False)
    print(f'Converted {len(output_df)} records to standard format')
else:
    print('Error: Input file must have ITEMID and source_text columns')
    sys.exit(1)
"

# Check if the conversion was successful
if [ $? -ne 0 ]; then
  echo "Error: Failed to convert input file to standard format."
  exit 1
fi

# Run threshold_negatives_handler.py in evaluate mode
python threshold_negatives_handler.py \
  --mimic_file "$TEMP_MIMIC_FILE" \
  --loinc_file "$LOINC_FILE" \
  --checkpoint_dir "$CHECKPOINT_DIR" \
  --fold "$FOLD" \
  --output_dir "$OUTPUT_DIR" \
  --mode evaluate \
  --threshold "$THRESHOLD" \
  --limit_samples 1000  # Use all samples

# Check if the run was successful
if [ $? -eq 0 ]; then
    # Check if the results file was created
    if [ -f "$OUTPUT_DIR/threshold_inference_results.csv" ]; then
        echo "Successfully completed LOINC standardization with no-match handling"
        
        # Link the results file with a more descriptive name
        cp "$OUTPUT_DIR/threshold_inference_results.csv" "$OUTPUT_DIR/loinc_mappings_with_nomatch.csv"
        
        # Print a summary of the results
        echo "Results saved to $OUTPUT_DIR/loinc_mappings_with_nomatch.csv"
        
        # Calculate statistics
        TOTAL_COUNT=$(wc -l < "$OUTPUT_DIR/loinc_mappings_with_nomatch.csv")
        TOTAL_COUNT=$((TOTAL_COUNT - 1))  # Subtract header
        
        UNMAPPABLE_COUNT=$(grep -c "UNMAPPABLE" "$OUTPUT_DIR/loinc_mappings_with_nomatch.csv")
        MAPPABLE_COUNT=$((TOTAL_COUNT - UNMAPPABLE_COUNT))
        
        UNMAPPABLE_PERCENT=$(echo "scale=2; $UNMAPPABLE_COUNT / $TOTAL_COUNT * 100" | bc)
        MAPPABLE_PERCENT=$(echo "scale=2; $MAPPABLE_COUNT / $TOTAL_COUNT * 100" | bc)
        
        echo "Summary:"
        echo "- Total examples: $TOTAL_COUNT"
        echo "- Mappable: $MAPPABLE_COUNT ($MAPPABLE_PERCENT%)"
        echo "- Unmappable: $UNMAPPABLE_COUNT ($UNMAPPABLE_PERCENT%)"
        
        # Display some example mappings
        echo -e "\nSample mappings (first 3 rows):"
        head -n 4 "$OUTPUT_DIR/loinc_mappings_with_nomatch.csv"
        
        echo -e "\nSample unmappable items:"
        grep "UNMAPPABLE" "$OUTPUT_DIR/loinc_mappings_with_nomatch.csv" | head -n 3
    else
        echo "Error: Results file not found."
        exit 1
    fi
else
    echo "Error: LOINC standardization with no-match handling failed."
    exit 1
fi

# Exit successfully
exit 0 