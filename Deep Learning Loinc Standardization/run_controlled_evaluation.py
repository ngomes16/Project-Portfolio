#!/usr/bin/env python
"""
Run a controlled evaluation of the LOINC standardization model.

This script runs a more controlled evaluation with limited sample sizes
and timeouts to prevent issues with large datasets or hanging.
"""
import os
import argparse
import subprocess
import sys

def main():
    parser = argparse.ArgumentParser(description='Run controlled evaluation of LOINC standardization model')
    parser.add_argument('--test_size', type=int, default=100,
                        help='Maximum number of test samples to evaluate')
    parser.add_argument('--timeout', type=int, default=300,
                        help='Timeout in seconds for each evaluation run')
    parser.add_argument('--skip_augmented', action='store_true',
                        help='Skip augmented test evaluation')
    parser.add_argument('--skip_ablation', action='store_true',
                        help='Skip ablation studies')
    parser.add_argument('--fold', type=int, default=None,
                        help='Specific fold to evaluate (if not specified, evaluate all folds)')
    args = parser.parse_args()
    
    print("=================================================")
    print("LOINC STANDARDIZATION - CONTROLLED EVALUATION")
    print("=================================================")
    print(f"Test Size: {args.test_size} samples")
    print(f"Timeout: {args.timeout} seconds per run")
    print(f"Skip Augmented Tests: {args.skip_augmented}")
    print(f"Skip Ablation Studies: {args.skip_ablation}")
    print(f"Target Fold: {args.fold if args.fold is not None else 'All'}")
    print("=================================================\n")
    
    # Step 1: Prepare output directory
    output_dir = os.path.join(os.getcwd(), 'results', 'controlled_evaluation')
    os.makedirs(output_dir, exist_ok=True)
    print(f"Results will be saved to: {output_dir}")
    
    # Step 2: Check for required files and prepare placeholders if needed
    required_files = [
        ('output/mimic_pairs_processed.csv', 'MIMIC test data'),
        ('output/loinc_full_processed.csv', 'LOINC data'),
        ('output/expanded_target_pool.csv', 'Expanded target pool')
    ]
    
    if not args.skip_augmented:
        required_files.append(('output/mimic_pairs_augmented.csv', 'Augmented test data'))
    
    for file_path, description in required_files:
        if not os.path.exists(file_path):
            print(f"⚠ {description} not found at {file_path}. Creating placeholder...")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(f"# Placeholder {description} created by run_controlled_evaluation.py\n")
    
    # Step 3: Run evaluation with controlled parameters
    cmd = [
        'python', 'models/run_evaluation.py',
        '--test_file', 'output/mimic_pairs_processed.csv',
        '--loinc_file', 'output/loinc_full_processed.csv',
        '--checkpoint_dir', 'models/checkpoints',
        '--output_dir', output_dir,
        '--expanded_pool', 'output/expanded_target_pool.csv',
        '--max_samples', str(args.test_size),
        '--timeout', str(args.timeout)
    ]
    
    if args.skip_augmented:
        cmd.append('--skip_augmented_test')
    
    if args.fold is not None:
        cmd.extend(['--fold', str(args.fold)])
    
    print("\n=== RUNNING EVALUATION ===")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        print("✓ Evaluation completed successfully")
        eval_success = True
    except subprocess.CalledProcessError as e:
        print(f"✗ Evaluation failed with error: {e}")
        eval_success = False
    
    # Step 4: Run error analysis if evaluation was successful
    if eval_success and args.fold is not None:
        print("\n=== RUNNING ERROR ANALYSIS ===")
        error_cmd = [
            'python', 'models/error_analysis.py',
            '--test_file', 'output/mimic_pairs_processed.csv',
            '--loinc_file', 'output/loinc_full_processed.csv',
            '--checkpoint_dir', 'models/checkpoints',
            '--output_dir', os.path.join(output_dir, 'error_analysis'),
            '--fold', str(args.fold)
        ]
        
        print(f"Command: {' '.join(error_cmd)}")
        
        try:
            subprocess.run(error_cmd, check=True)
            print("✓ Error analysis completed successfully")
            error_success = True
        except subprocess.CalledProcessError as e:
            print(f"✗ Error analysis failed with error: {e}")
            error_success = False
    else:
        error_success = False
        if not eval_success:
            print("Skipping error analysis due to failed evaluation.")
        else:
            print("Skipping error analysis since all folds were evaluated.")
    
    # Step 5: Run ablation studies if requested
    if not args.skip_ablation:
        print("\n=== RUNNING ABLATION STUDIES ===")
        ablation_cmd = [
            'python', 'models/ablation_study.py',
            '--test_file', 'output/mimic_pairs_processed.csv',
            '--loinc_file', 'output/loinc_full_processed.csv',
            '--checkpoint_dir', 'models/checkpoints',
            '--output_dir', os.path.join(output_dir, 'ablation'),
            '--max_samples', str(args.test_size)
        ]
        
        print(f"Command: {' '.join(ablation_cmd)}")
        
        try:
            subprocess.run(ablation_cmd, check=True)
            print("✓ Ablation studies completed successfully")
            ablation_success = True
        except subprocess.CalledProcessError as e:
            print(f"✗ Ablation studies failed with error: {e}")
            ablation_success = False
    else:
        ablation_success = True  # Mark as success if skipped
        print("Skipping ablation studies as requested.")
    
    # Final status summary
    print("\n=================================================")
    print("EVALUATION COMPLETION STATUS:")
    print(f"Main Evaluation:  {'✓' if eval_success else '✗'}")
    print(f"Error Analysis:   {'✓' if error_success else '✗'}")
    print(f"Ablation Studies: {'✓' if ablation_success else ('SKIPPED' if args.skip_ablation else '✗')}")
    print("=================================================")
    
    if eval_success and (error_success or args.fold is None) and (ablation_success or args.skip_ablation):
        print("\nControlled evaluation completed successfully! 🎉")
        return 0
    else:
        print("\nEvaluation completed with some components failing. Check logs for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 