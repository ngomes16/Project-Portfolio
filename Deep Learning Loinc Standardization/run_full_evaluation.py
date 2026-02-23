#!/usr/bin/env python
"""
Run a full evaluation of the LOINC standardization model.

This script orchestrates the complete evaluation pipeline, including:
1. Data preparation
2. Model evaluation on standard and expanded target pools
3. Evaluation with augmented test data (Type-1 generalization)
4. Error analysis
5. Ablation studies (if requested)
"""
import os
import argparse
import subprocess
import pandas as pd
import shutil
import sys
from pathlib import Path

def ensure_file_exists(file_path, description, create_if_missing=False):
    """
    Check if a file exists and optionally create it if missing
    
    Args:
        file_path: Path to the file
        description: Description of the file for error messages
        create_if_missing: Whether to create a placeholder if the file is missing
        
    Returns:
        bool: True if file exists or was created, False otherwise
    """
    if os.path.exists(file_path):
        print(f"✓ {description} found at {file_path}")
        return True
    
    if create_if_missing:
        print(f"⚠ {description} not found at {file_path}. Creating placeholder...")
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Create an empty file
        with open(file_path, 'w') as f:
            f.write(f"# Placeholder {description} created by run_full_evaluation.py\n")
        
        return True
    
    print(f"✗ {description} not found at {file_path}")
    return False

def prepare_output_directory():
    """
    Prepare the output directory structure
    
    Returns:
        output_dir: Path to the output directory
    """
    output_dir = os.path.join(os.getcwd(), 'results', 'full_evaluation')
    os.makedirs(output_dir, exist_ok=True)
    
    # Create subdirectories
    subdirs = ['standard', 'expanded', 'augmented', 'error_analysis', 'ablation']
    for subdir in subdirs:
        os.makedirs(os.path.join(output_dir, subdir), exist_ok=True)
    
    return output_dir

def check_required_files():
    """
    Check if all required files exist
    
    Returns:
        bool: True if all required files exist, False otherwise
    """
    # Define required files
    required_files = [
        ('output/mimic_pairs_processed.csv', 'Test data file'),
        ('output/loinc_full_processed.csv', 'LOINC target file'),
        ('output/expanded_target_pool.csv', 'Expanded target pool file'),
        ('output/mimic_pairs_augmented.csv', 'Augmented test data file')
    ]
    
    # Check for model checkpoints
    model_dir = 'models/checkpoints'
    if not os.path.exists(model_dir):
        print(f"✗ Model checkpoint directory not found at {model_dir}")
        return False
    
    # Check if at least one model checkpoint exists
    checkpoint_files = [f for f in os.listdir(model_dir) if f.endswith('.h5') or f.endswith('.weights.h5')]
    if not checkpoint_files:
        print(f"✗ No model checkpoints found in {model_dir}")
        return False
    
    # Check all required files
    all_exist = True
    for file_path, description in required_files:
        if not ensure_file_exists(file_path, description, create_if_missing=True):
            all_exist = False
    
    return all_exist

def run_evaluation():
    """
    Run the main evaluation script
    """
    cmd = [
        'python', 'models/run_evaluation.py',
        '--test_file', 'output/mimic_pairs_processed.csv',
        '--augmented_test_file', 'output/mimic_pairs_augmented.csv',
        '--loinc_file', 'output/loinc_full_processed.csv',
        '--checkpoint_dir', 'models/checkpoints',
        '--output_dir', 'results/full_evaluation/standard',
        '--expanded_pool', 'output/expanded_target_pool.csv'
    ]
    
    print("\n=== RUNNING FULL MODEL EVALUATION ===")
    print(f"Command: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        print("✓ Evaluation completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Evaluation failed with error: {e}")
        return False

def run_error_analysis():
    """
    Run error analysis on evaluation results
    """
    # Find the model checkpoints
    checkpoint_dir = 'models/checkpoints'
    if not os.path.exists(checkpoint_dir):
        print("✗ Model checkpoint directory not found. Skipping error analysis.")
        return False
    
    # Get the list of folds from the model checkpoints
    checkpoint_files = [f for f in os.listdir(checkpoint_dir) if f.endswith('.h5') or f.endswith('.weights.h5')]
    folds = []
    for file in checkpoint_files:
        if file.startswith('stage2_fold') and 'model.weights.h5' in file:
            try:
                fold_num = int(file.split('_')[1].replace('fold', '')) - 1  # Convert to 0-indexed
                folds.append(fold_num)
            except (ValueError, IndexError):
                continue
    
    folds = sorted(list(set(folds)))
    if not folds:
        print("✗ No fold model checkpoints found. Skipping error analysis.")
        return False
    
    # Run error analysis for each fold
    print("\n=== RUNNING ERROR ANALYSIS ===")
    success = True
    
    for fold in folds:
        cmd = [
            'python', 'models/error_analysis.py',
            '--test_file', 'output/mimic_pairs_processed.csv',
            '--loinc_file', 'output/loinc_full_processed.csv',
            '--checkpoint_dir', 'models/checkpoints',
            '--output_dir', 'results/full_evaluation/error_analysis',
            '--fold', str(fold)
        ]
        
        print(f"\nRunning error analysis for fold {fold}...")
        print(f"Command: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"✗ Error analysis for fold {fold} failed with error: {e}")
            success = False
    
    if success:
        print("✓ Error analysis completed successfully")
    
    return success

def run_ablation_studies(skip_ablation=False):
    """
    Run ablation studies
    
    Args:
        skip_ablation: Whether to skip ablation studies
    """
    if skip_ablation:
        print("\n=== SKIPPING ABLATION STUDIES ===")
        return True
    
    print("\n=== RUNNING ABLATION STUDIES ===")
    cmd = [
        'python', 'models/ablation_study.py',
        '--test_file', 'output/mimic_pairs_processed.csv',
        '--loinc_file', 'output/loinc_full_processed.csv',
        '--checkpoint_dir', 'models/checkpoints',
        '--output_dir', 'results/full_evaluation/ablation'
    ]
    
    print(f"Command: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        print("✓ Ablation studies completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Ablation studies failed with error: {e}")
        return False

def generate_summary_report(output_dir):
    """
    Generate a summary report of all evaluation results
    
    Args:
        output_dir: Path to the output directory
    """
    print("\n=== GENERATING SUMMARY REPORT ===")
    
    # Find all evaluation summary files
    summary_files = []
    for root, _, files in os.walk(output_dir):
        summary_files.extend([os.path.join(root, f) for f in files if f == 'evaluation_summary.csv' or f == 'evaluation_summary.txt'])
    
    if not summary_files:
        print("✗ No evaluation summary files found.")
        return
    
    # Combine all summaries into a single report
    report_path = os.path.join(output_dir, 'full_evaluation_report.txt')
    with open(report_path, 'w') as report_file:
        report_file.write("===============================================\n")
        report_file.write("LOINC STANDARDIZATION MODEL - FULL EVALUATION REPORT\n")
        report_file.write("===============================================\n\n")
        
        for summary_file in summary_files:
            report_file.write(f"Results from {os.path.relpath(summary_file, output_dir)}:\n")
            report_file.write("-----------------------------------------------\n")
            
            with open(summary_file, 'r') as f:
                report_file.write(f.read())
            
            report_file.write("\n\n")
    
    print(f"✓ Summary report generated at {report_path}")

def main():
    parser = argparse.ArgumentParser(description='Run full evaluation of LOINC standardization model')
    parser.add_argument('--skip_ablation', action='store_true', help='Skip ablation studies')
    args = parser.parse_args()
    
    print("======================================================")
    print("LOINC STANDARDIZATION MODEL - FULL EVALUATION PIPELINE")
    print("======================================================\n")
    
    # Prepare output directory
    output_dir = prepare_output_directory()
    print(f"Results will be saved to: {output_dir}\n")
    
    # Check if all required files exist
    if not check_required_files():
        print("\n⚠ Some required files are missing, but placeholders were created.")
        print("The evaluation will proceed, but results may not be meaningful.")
    
    # Run evaluation
    eval_success = run_evaluation()
    
    # Run error analysis if evaluation was successful
    if eval_success:
        error_analysis_success = run_error_analysis()
    else:
        error_analysis_success = False
        print("Skipping error analysis due to failed evaluation.")
    
    # Run ablation studies
    ablation_success = run_ablation_studies(args.skip_ablation)
    
    # Generate summary report
    if eval_success or error_analysis_success or ablation_success:
        generate_summary_report(output_dir)
    
    # Print final status
    print("\n======================================================")
    print("EVALUATION PIPELINE COMPLETION STATUS:")
    print(f"Main Evaluation:  {'✓' if eval_success else '✗'}")
    print(f"Error Analysis:   {'✓' if error_analysis_success else '✗'}")
    print(f"Ablation Studies: {'✓' if ablation_success else '✗' if not args.skip_ablation else 'SKIPPED'}")
    print("======================================================\n")
    
    if eval_success and error_analysis_success and (ablation_success or args.skip_ablation):
        print("Full evaluation completed successfully! 🎉")
        return 0
    else:
        print("Evaluation completed with some failures. Check logs for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 