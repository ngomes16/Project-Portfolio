#!/bin/bash

# Activate the virtual environment
source 598_env/bin/activate

# Default parameters
MIMIC_FILE="mimic_pairs_processed.csv"
LOINC_FILE="loinc_targets_processed.csv"
D_LABITEMS_FILE="D_LABITEMS.csv"
CHECKPOINT_DIR="models/checkpoints"
FOLD=0
OUTPUT_DIR="results/no_match_handler"
MODE="tune"
THRESHOLD=""
LIMIT_SAMPLES=""

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
    --mode)
      MODE="$2"
      shift 2
      ;;
    --threshold)
      THRESHOLD="--threshold $2"
      shift 2
      ;;
    --limit_samples)
      LIMIT_SAMPLES="--limit_samples $2"
      shift 2
      ;;
    tune)
      MODE="tune"
      shift
      ;;
    evaluate)
      MODE="evaluate"
      shift
      ;;
    generate)
      MODE="generate"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Create output directory
mkdir -p $OUTPUT_DIR

# Define command
CMD="python no_match_handler.py --mimic_file $MIMIC_FILE --loinc_file $LOINC_FILE --d_labitems_file $D_LABITEMS_FILE --checkpoint_dir $CHECKPOINT_DIR --fold $FOLD --output_dir $OUTPUT_DIR --mode $MODE $THRESHOLD $LIMIT_SAMPLES"

# Print command
echo "Running command: $CMD"

# Execute command
eval $CMD

# Check if the command was successful
if [ $? -eq 0 ]; then
  echo "Successfully completed no-match handler in $MODE mode"
  
  # Print summary based on mode
  if [ "$MODE" == "tune" ]; then
    if [ -f "$OUTPUT_DIR/optimal_threshold.txt" ]; then
      OPTIMAL_THRESHOLD=$(cat "$OUTPUT_DIR/optimal_threshold.txt")
      echo "Optimal Threshold: $OPTIMAL_THRESHOLD"
    fi
    
    if [ -f "$OUTPUT_DIR/evaluation_results.csv" ]; then
      echo "Evaluation Results Summary:"
      python -c "import pandas as pd; df=pd.read_csv('$OUTPUT_DIR/evaluation_results.csv'); print(df)"
    fi
  elif [ "$MODE" == "evaluate" ]; then
    if [ -f "$OUTPUT_DIR/evaluation_results.csv" ]; then
      echo "Evaluation Results Summary:"
      python -c "import pandas as pd; df=pd.read_csv('$OUTPUT_DIR/evaluation_results.csv'); print(df)"
    fi
  elif [ "$MODE" == "generate" ]; then
    if [ -f "$OUTPUT_DIR/hard_negatives.csv" ]; then
      NUM_HARD_NEGATIVES=$(wc -l < "$OUTPUT_DIR/hard_negatives.csv")
      echo "Generated $NUM_HARD_NEGATIVES hard negative examples"
    fi
    
    if [ -f "$OUTPUT_DIR/negative_triplets.csv" ]; then
      NUM_TRIPLETS=$(wc -l < "$OUTPUT_DIR/negative_triplets.csv")
      echo "Generated $NUM_TRIPLETS triplet examples with negatives"
    fi
  fi
else
  echo "Error: No-match handler failed"
  exit 1
fi

# Exit successfully
exit 0 