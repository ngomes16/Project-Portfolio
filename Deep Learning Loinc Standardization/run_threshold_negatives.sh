#!/bin/bash

# Activate virtual environment
source 598_env/bin/activate

# Default parameters
MIMIC_FILE="mimic_pairs_processed.csv"
LOINC_FILE="loinc_targets_processed.csv"
D_LABITEMS_FILE="D_LABITEMS.csv"
CHECKPOINT_DIR="models/checkpoints"
FOLD=0
OUTPUT_DIR="results/threshold_negatives"
MODE="tune"
THRESHOLD=""
VISUALIZE=""
LIMIT_SAMPLES=""
POS_SAMPLES=200
NEG_SAMPLES=200
HARD_NEGATIVES=200
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
    --pos_samples)
      POS_SAMPLES="$2"
      shift 2
      ;;
    --neg_samples)
      NEG_SAMPLES="$2"
      shift 2
      ;;
    --hard_negatives)
      HARD_NEGATIVES="$2"
      shift 2
      ;;
    --seed)
      SEED="$2"
      shift 2
      ;;
    --visualize)
      VISUALIZE="--visualize"
      shift
      ;;
    tune)
      MODE="tune"
      shift
      ;;
    generate)
      MODE="generate"
      shift
      ;;
    evaluate)
      MODE="evaluate"
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
CMD="python threshold_negatives_handler.py --mimic_file $MIMIC_FILE --loinc_file $LOINC_FILE --d_labitems_file $D_LABITEMS_FILE --checkpoint_dir $CHECKPOINT_DIR --fold $FOLD --output_dir $OUTPUT_DIR --mode $MODE --pos_samples $POS_SAMPLES --neg_samples $NEG_SAMPLES --hard_negatives $HARD_NEGATIVES --seed $SEED $THRESHOLD $VISUALIZE $LIMIT_SAMPLES"

# Print command
echo "Running command: $CMD"

# Execute command
eval $CMD

# Check if the command was successful
if [ $? -eq 0 ]; then
  echo "Successfully completed no-match handling in $MODE mode"
  
  # Print summary based on mode
  if [ "$MODE" == "tune" ]; then
    if [ -f "$OUTPUT_DIR/optimal_threshold.txt" ]; then
      OPTIMAL_THRESHOLD=$(cat "$OUTPUT_DIR/optimal_threshold.txt")
      echo "Optimal Threshold: $OPTIMAL_THRESHOLD"
    fi
    
    if [ -f "$OUTPUT_DIR/threshold_metrics.csv" ]; then
      echo "Threshold Metrics Summary:"
      python -c "import pandas as pd; df=pd.read_csv('$OUTPUT_DIR/threshold_metrics.csv'); print(df)"
    fi
  elif [ "$MODE" == "generate" ]; then
    if [ -f "$OUTPUT_DIR/hard_negatives.csv" ]; then
      NUM_HARD_NEGATIVES=$(wc -l < "$OUTPUT_DIR/hard_negatives.csv")
      NUM_HARD_NEGATIVES=$((NUM_HARD_NEGATIVES - 1))  # Subtract 1 for header
      echo "Generated $NUM_HARD_NEGATIVES hard negative examples"
    fi
  elif [ "$MODE" == "evaluate" ]; then
    if [ -f "$OUTPUT_DIR/threshold_inference_results.csv" ]; then
      echo "Inference Results Summary:"
      python -c "import pandas as pd; df=pd.read_csv('$OUTPUT_DIR/threshold_inference_results.csv'); print(f'Total examples: {len(df)}'); print(f'Mappable: {sum(df[\"MAPPABLE\"])} ({sum(df[\"MAPPABLE\"])/len(df)*100:.2f}%)'); print(f'Unmappable: {sum(~df[\"MAPPABLE\"])} ({sum(~df[\"MAPPABLE\"])/len(df)*100:.2f}%)')"
    fi
  fi
else
  echo "Error: No-match handler failed"
  exit 1
fi

# Exit successfully
exit 0 