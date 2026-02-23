#!/bin/bash

# Shell script to run all the visualization Python scripts

echo "Generating all images for the LOINC Standardization project..."

# Run each script in sequence
echo "1. Generating model performance comparison chart..."
python images/plot_core_model_performance.py

echo "2. Generating ablation study impact charts..."
python images/plot_ablation_study_impact.py

echo "3. Generating scale token performance chart..."
python images/plot_scale_token_performance.py

echo "4. Generating no-match precision-recall curve..."
python images/plot_no_match_pr_curve.py

echo "5. Generating similarity distribution chart..."
python images/plot_similarity_distribution.py

echo "6. Generating error category distribution charts..."
python images/plot_error_category_distribution.py

echo "All images generated successfully in the 'images' folder." 