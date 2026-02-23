#!/bin/bash

# Activate virtual environment
source 598_env/bin/activate

# Create output directory
mkdir -p results/no_match_handler

# Run the simple no-match test with limited targets and samples for faster testing
python simple_nomatch_test.py --limit_samples 50 --max_targets 500 