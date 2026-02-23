#!/usr/bin/env python
"""
Run evaluation of the LOINC standardization model

This script runs evaluation on the trained model with both standard and augmented test data,
and both standard and expanded target pools.
"""
import os
import argparse
import subprocess
import pandas as pd

def main():
    parser = argparse.ArgumentParser(description='Run evaluation of LOINC standardization model')
    parser.add_argument('--test_file', type=str, default='output/mimic_pairs_processed.csv', 
                        help='Path to test data CSV')
    parser.add_argument('--augmented_test_file', type=str, default='output/mimic_pairs_augmented.csv',
                       help='Path to augmented test data CSV for Type-1 generalization testing')
    parser.add_argument('--loinc_file', type=str, default='output/loinc_full_processed.csv', 
                        help='Path to LOINC data CSV')
    parser.add_argument('--checkpoint_dir', type=str, default='models/checkpoints', 
                        help='Directory containing model checkpoints')
    parser.add_argument('--output_dir', type=str, default='results',
                        help='Directory to save evaluation results')
    parser.add_argument('--expanded_pool', type=str, default='output/expanded_target_pool.csv',
                        help='Path to expanded target pool CSV')
    parser.add_argument('--fold', type=int, default=None,
                        help='Specific fold to evaluate (if not specified, evaluate all folds)')
    parser.add_argument('--skip_augmented_test', action='store_true',
                        help='Skip evaluation on augmented test data')
    parser.add_argument('--max_samples', type=int, default=None,
                        help='Maximum number of samples to evaluate (for debugging or performance issues)')
    parser.add_argument('--timeout', type=int, default=600,
                        help='Timeout in seconds for individual evaluation runs')
    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Check if files exist
    if not os.path.exists(args.test_file):
        print(f"Test file not found: {args.test_file}")
        return

    # Generate augmented test data if needed and not specified to skip
    if not args.skip_augmented_test and (not os.path.exists(args.augmented_test_file)):
        print("Augmented test file not found. Generating augmented test data...")
        try:
            # Try to use our fix_augmentation.py script
            subprocess.run(['python', 'fix_augmentation.py'], check=True)
            print(f"Successfully generated augmented test data: {args.augmented_test_file}")
        except Exception as e:
            print(f"Failed to generate augmented test data: {e}")
            print("Will skip augmented test evaluation.")
            args.skip_augmented_test = True

    # Check if expanded target pool exists
    use_expanded_pool = os.path.exists(args.expanded_pool)
    if not use_expanded_pool:
        print(f"Expanded target pool not found: {args.expanded_pool}")
        print("Will only evaluate on standard target pool.")

    # Check which folds to evaluate
    if args.fold is not None:
        folds = [args.fold]
    else:
        # Find all available folds based on checkpoint files
        model_files = [f for f in os.listdir(args.checkpoint_dir) if f.endswith('.h5') or f.endswith('.weights.h5')]
        folds = []
        for file in model_files:
            if file.startswith('stage2_fold') and 'model.weights.h5' in file:
                # Extract fold number from stage2_fold{N}_model.weights.h5
                try:
                    fold_num = int(file.split('_')[1].replace('fold', '')) - 1  # Convert to 0-indexed
                    folds.append(fold_num)
                except (ValueError, IndexError):
                    continue
        
        folds = sorted(list(set(folds)))
        if not folds:
            print(f"No fold model checkpoints found in {args.checkpoint_dir}")
            return
        print(f"Found {len(folds)} folds to evaluate: {folds}")

    # Run evaluation for each fold
    all_results = []
    
    # Function to run evaluation with timeout
    def run_eval_with_timeout(cmd, result_file, timeout=args.timeout):
        try:
            subprocess.run(cmd, check=True, timeout=timeout)
            
            # Check if result file was generated
            if os.path.exists(result_file):
                return True
            else:
                print(f"Evaluation completed but result file {result_file} was not generated")
                return False
        except subprocess.TimeoutExpired:
            print(f"Evaluation timed out after {timeout} seconds")
            return False
        except subprocess.CalledProcessError as e:
            print(f"Evaluation failed with error: {e}")
            return False
    
    print("\n=== EVALUATING ON STANDARD TARGET POOL ===")
    for fold in folds:
        cmd = [
            'python', 'models/evaluation.py',
            '--test_file', args.test_file,
            '--loinc_file', args.loinc_file,
            '--checkpoint_dir', args.checkpoint_dir,
            '--output_dir', args.output_dir,
            '--fold', str(fold)
        ]
        
        # Add max_samples if specified
        if args.max_samples:
            cmd.extend(['--max_samples', str(args.max_samples)])
        
        print(f"\nRunning evaluation for fold {fold}...")
        print(f"Command: {' '.join(cmd)}")
        
        result_file = os.path.join(args.output_dir, f'fold{fold}_results.csv')
        success = run_eval_with_timeout(cmd, result_file)
        
        # Read and save results if successful
        if success and os.path.exists(result_file):
            results = pd.read_csv(result_file)
            results['fold'] = fold
            results['target_pool'] = 'standard'
            results['test_type'] = 'original'
            all_results.append(results)
    
    # Run evaluation with expanded target pool
    if use_expanded_pool:
        print("\n=== EVALUATING ON EXPANDED TARGET POOL ===")
        for fold in folds:
            cmd = [
                'python', 'models/evaluation.py',
                '--test_file', args.test_file,
                '--loinc_file', args.expanded_pool,
                '--checkpoint_dir', args.checkpoint_dir,
                '--output_dir', args.output_dir,
                '--fold', str(fold),
                '--expanded_pool'
            ]
            
            # Add max_samples if specified
            if args.max_samples:
                cmd.extend(['--max_samples', str(args.max_samples)])
            
            print(f"\nRunning evaluation for fold {fold} with expanded target pool...")
            print(f"Command: {' '.join(cmd)}")
            
            result_file = os.path.join(args.output_dir, f'fold{fold}_expanded_results.csv')
            success = run_eval_with_timeout(cmd, result_file)
            
            # Read and save results if successful
            if success and os.path.exists(result_file):
                results = pd.read_csv(result_file)
                results['fold'] = fold
                results['target_pool'] = 'expanded'
                results['test_type'] = 'original'
                all_results.append(results)
    
    # Run evaluation with augmented test data (Type-1 generalization)
    if not args.skip_augmented_test and os.path.exists(args.augmented_test_file):
        print("\n=== EVALUATING ON AUGMENTED TEST DATA (TYPE-1 GENERALIZATION) ===")
        for fold in folds:
            cmd = [
                'python', 'models/evaluation.py',
                '--test_file', args.augmented_test_file,
                '--loinc_file', args.loinc_file,
                '--checkpoint_dir', args.checkpoint_dir,
                '--output_dir', args.output_dir,
                '--fold', str(fold),
                '--augmented_test'
            ]
            
            # Add max_samples if specified
            if args.max_samples:
                cmd.extend(['--max_samples', str(args.max_samples)])
            
            print(f"\nRunning evaluation for fold {fold} with augmented test data...")
            print(f"Command: {' '.join(cmd)}")
            
            result_file = os.path.join(args.output_dir, f'fold{fold}_augmented_results.csv')
            success = run_eval_with_timeout(cmd, result_file)
            
            # Read and save results if successful
            if success and os.path.exists(result_file):
                results = pd.read_csv(result_file)
                results['fold'] = fold
                results['target_pool'] = 'standard'
                results['test_type'] = 'augmented'
                all_results.append(results)
        
        # Run evaluation with augmented test data and expanded target pool
        if use_expanded_pool:
            print("\n=== EVALUATING ON AUGMENTED TEST DATA WITH EXPANDED TARGET POOL ===")
            for fold in folds:
                cmd = [
                    'python', 'models/evaluation.py',
                    '--test_file', args.augmented_test_file,
                    '--loinc_file', args.expanded_pool,
                    '--checkpoint_dir', args.checkpoint_dir,
                    '--output_dir', args.output_dir,
                    '--fold', str(fold),
                    '--expanded_pool',
                    '--augmented_test'
                ]
                
                # Add max_samples if specified
                if args.max_samples:
                    cmd.extend(['--max_samples', str(args.max_samples)])
                
                print(f"\nRunning evaluation for fold {fold} with augmented test data and expanded target pool...")
                print(f"Command: {' '.join(cmd)}")
                
                result_file = os.path.join(args.output_dir, f'fold{fold}_augmented_expanded_results.csv')
                success = run_eval_with_timeout(cmd, result_file)
                
                # Read and save results if successful
                if success and os.path.exists(result_file):
                    results = pd.read_csv(result_file)
                    results['fold'] = fold
                    results['target_pool'] = 'expanded'
                    results['test_type'] = 'augmented'
                    all_results.append(results)
    
    # Combine all results and compute averages
    if all_results:
        all_results_df = pd.concat(all_results, ignore_index=True)
        summary_file = os.path.join(args.output_dir, 'evaluation_summary.csv')
        all_results_df.to_csv(summary_file, index=False)
        print(f"\nSaved combined results to {summary_file}")
        
        # Calculate average results by group
        grouped = all_results_df.groupby(['target_pool', 'test_type'])
        avg_results = grouped.agg({
            'top1_accuracy': ['mean', 'std'],
            'top3_accuracy': ['mean', 'std'],
            'top5_accuracy': ['mean', 'std']
        })
        
        # Format and print summary
        print("\n=== EVALUATION SUMMARY ===")
        for (target_pool, test_type), group_data in avg_results.iterrows():
            print(f"\nTarget Pool: {target_pool.upper()}, Test Type: {test_type.upper()}")
            print(f"Top-1 Accuracy: {group_data[('top1_accuracy', 'mean')]*100:.1f}% ± {group_data[('top1_accuracy', 'std')]*100:.1f}%")
            print(f"Top-3 Accuracy: {group_data[('top3_accuracy', 'mean')]*100:.1f}% ± {group_data[('top3_accuracy', 'std')]*100:.1f}%")
            print(f"Top-5 Accuracy: {group_data[('top5_accuracy', 'mean')]*100:.1f}% ± {group_data[('top5_accuracy', 'std')]*100:.1f}%")
        
        # Save formatted summary to file
        with open(os.path.join(args.output_dir, 'evaluation_summary.txt'), 'w') as f:
            f.write("=== LOINC STANDARDIZATION MODEL EVALUATION SUMMARY ===\n\n")
            for (target_pool, test_type), group_data in avg_results.iterrows():
                f.write(f"Target Pool: {target_pool.upper()}, Test Type: {test_type.upper()}\n")
                f.write(f"Top-1 Accuracy: {group_data[('top1_accuracy', 'mean')]*100:.1f}% ± {group_data[('top1_accuracy', 'std')]*100:.1f}%\n")
                f.write(f"Top-3 Accuracy: {group_data[('top3_accuracy', 'mean')]*100:.1f}% ± {group_data[('top3_accuracy', 'std')]*100:.1f}%\n")
                f.write(f"Top-5 Accuracy: {group_data[('top5_accuracy', 'mean')]*100:.1f}% ± {group_data[('top5_accuracy', 'std')]*100:.1f}%\n\n")

if __name__ == "__main__":
    main() 