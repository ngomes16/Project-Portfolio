#!/usr/bin/env python
"""
Ablation Study for LOINC Standardization Model

This script performs ablation studies to understand the contribution of different components:
1. Evaluating the impact of the two-stage fine-tuning approach
2. Comparing different mining strategies (hard vs semi-hard negative mining)
3. Testing the effect of data augmentation
4. Measuring the influence of model size and architecture
"""
import os
import sys
import pandas as pd
import numpy as np
import argparse
import subprocess
import json
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from evaluation.py
from models.evaluation import load_test_data, load_target_loincs, load_model, compute_embeddings

def run_component_evaluation(component, value, test_file, loinc_file, checkpoint_dir, output_dir, fold=0, expanded_pool=False, augmented_test=False):
    """
    Run evaluation with specific component configuration
    
    Args:
        component: Component name being tested
        value: Component value being tested
        test_file: Path to test data
        loinc_file: Path to LOINC data
        checkpoint_dir: Directory with model checkpoints
        output_dir: Directory to save results
        fold: Model fold to evaluate
        expanded_pool: Whether to use expanded target pool
        augmented_test: Whether to use augmented test data
    
    Returns:
        results_file: Path to the results file
    """
    # Create a unique identifier for this ablation test
    test_id = f"{component}_{value}"
    
    # Get proper checkpoint path based on component and value
    if component == 'fine_tuning_stages':
        if value == 'stage2_only':
            checkpoint_path = os.path.join(checkpoint_dir, f"stage2_only_fold{fold+1}_model.weights.h5")
        else:
            checkpoint_path = os.path.join(checkpoint_dir, f"stage2_fold{fold+1}_model.weights.h5")
    elif component == 'mining_strategy':
        checkpoint_path = os.path.join(checkpoint_dir, f"stage2_{value}_fold{fold+1}_model.weights.h5")
    elif component == 'data_augmentation':
        if value == 'without_augmentation':
            checkpoint_path = os.path.join(checkpoint_dir, f"stage2_no_aug_fold{fold+1}_model.weights.h5")
        else:
            checkpoint_path = os.path.join(checkpoint_dir, f"stage2_fold{fold+1}_model.weights.h5")
    else:  # For model_size or other components
        checkpoint_path = os.path.join(checkpoint_dir, f"{value}_fold{fold+1}_model.weights.h5")
    
    # Ensure the checkpoint exists
    if not os.path.exists(checkpoint_path):
        print(f"WARNING: Checkpoint not found at {checkpoint_path}, using default")
        checkpoint_path = os.path.join(checkpoint_dir, f"stage2_fold{fold+1}_model.weights.h5")
    
    # Setup command based on the parameters
    cmd = [
        'python', 'models/evaluation.py',
        '--test_file', test_file,
        '--loinc_file', loinc_file,
        '--checkpoint_dir', checkpoint_dir,  # Use the directory, not specific path
        '--output_dir', output_dir,
        '--fold', str(fold)
    ]
    
    # Add expanded pool flag if needed
    if expanded_pool:
        cmd.append('--expanded_pool')
    
    # Add augmented test flag if needed
    if augmented_test:
        cmd.append('--augmented_test')
    
    # Add ablation identifier
    cmd.extend(['--ablation_id', test_id])
    
    print(f"\nRunning {component} ablation test with {value}...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        
        # Construct expected output file name based on ablation_id and other parameters
        # Format is fold{fold}_[augmented_]expanded_ablation_{test_id}_results.csv
        file_prefix = f"fold{fold}"
        if augmented_test:
            file_prefix += "_augmented"
        if expanded_pool:
            file_prefix += "_expanded"
        file_prefix += f"_ablation_{test_id}"
        
        results_file = os.path.join(output_dir, f"{file_prefix}_results.csv")
        
        if not os.path.exists(results_file):
            print(f"WARNING: Results file not found at {results_file}")
            return None
        
        return results_file
    
    except subprocess.CalledProcessError as e:
        print(f"Error running evaluation: {e}")
        return None

def test_fine_tuning_stages(test_file, loinc_file, checkpoint_dir, output_dir, fold=0, expanded_pool=False, augmented_test=False):
    """
    Test the impact of the two-stage fine-tuning approach
    
    Args:
        test_file: Path to test data
        loinc_file: Path to LOINC data
        checkpoint_dir: Directory with model checkpoints
        output_dir: Directory to save results
        fold: Model fold to evaluate
        expanded_pool: Whether to use expanded target pool
        augmented_test: Whether to use augmented test data
    
    Returns:
        results: Dictionary with results for both approaches
    """
    print("\n=== ABLATION STUDY: FINE-TUNING STAGES ===")
    
    results = {}
    
    # Test the two-stage fine-tuning approach (stage1 + stage2)
    stage1_stage2_file = run_component_evaluation(
        'fine_tuning_stages', 'stage1_stage2', 
        test_file, loinc_file, checkpoint_dir, output_dir, 
        fold, expanded_pool, augmented_test
    )
    
    if stage1_stage2_file:
        results['stage1_stage2'] = pd.read_csv(stage1_stage2_file)
    
    # Test stage2-only approach
    stage2_only_file = run_component_evaluation(
        'fine_tuning_stages', 'stage2_only', 
        test_file, loinc_file, checkpoint_dir, output_dir, 
        fold, expanded_pool, augmented_test
    )
    
    if stage2_only_file:
        results['stage2_only'] = pd.read_csv(stage2_only_file)
    
    # Compare results
    if results:
        print("\nFine-Tuning Stages Comparison:")
        
        for approach, result_df in results.items():
            if 'top1_accuracy' in result_df.columns:
                print(f"{approach}:")
                print(f"  Top-1 Accuracy: {result_df['top1_accuracy'].values[0]:.4f}")
                print(f"  Top-3 Accuracy: {result_df['top3_accuracy'].values[0]:.4f}")
                print(f"  Top-5 Accuracy: {result_df['top5_accuracy'].values[0]:.4f}")
        
        # Create visualization
        if all(k in results for k in ['stage1_stage2', 'stage2_only']):
            metrics = ['top1_accuracy', 'top3_accuracy', 'top5_accuracy']
            values = {
                'stage1_stage2': [results['stage1_stage2'][m].values[0] for m in metrics],
                'stage2_only': [results['stage2_only'][m].values[0] for m in metrics]
            }
            
            plt.figure(figsize=(10, 6))
            x = np.arange(len(metrics))
            width = 0.35
            
            plt.bar(x - width/2, values['stage1_stage2'], width, label='Two-Stage Fine-Tuning')
            plt.bar(x + width/2, values['stage2_only'], width, label='Stage 2 Only')
            
            plt.ylabel('Accuracy')
            plt.title('Impact of First-Stage Fine-Tuning')
            plt.xticks(x, ['Top-1', 'Top-3', 'Top-5'])
            plt.legend()
            
            # Save figure
            plt.tight_layout()
            fig_path = os.path.join(output_dir, 'fine_tuning_stages_comparison.png')
            plt.savefig(fig_path)
            print(f"Saved fine-tuning stages comparison to {fig_path}")
    
    return results

def test_mining_strategies(test_file, loinc_file, checkpoint_dir, output_dir, fold=0, expanded_pool=False, augmented_test=False):
    """
    Test the impact of different mining strategies
    
    Args:
        test_file: Path to test data
        loinc_file: Path to LOINC data
        checkpoint_dir: Directory with model checkpoints
        output_dir: Directory to save results
        fold: Model fold to evaluate
        expanded_pool: Whether to use expanded target pool
        augmented_test: Whether to use augmented test data
    
    Returns:
        results: Dictionary with results for different mining strategies
    """
    print("\n=== ABLATION STUDY: MINING STRATEGIES ===")
    
    results = {}
    
    # Test hard negative mining
    hard_negative_file = run_component_evaluation(
        'mining_strategy', 'hard_negative', 
        test_file, loinc_file, checkpoint_dir, output_dir, 
        fold, expanded_pool, augmented_test
    )
    
    if hard_negative_file:
        results['hard_negative'] = pd.read_csv(hard_negative_file)
    
    # Test semi-hard negative mining
    semi_hard_file = run_component_evaluation(
        'mining_strategy', 'semi_hard', 
        test_file, loinc_file, checkpoint_dir, output_dir, 
        fold, expanded_pool, augmented_test
    )
    
    if semi_hard_file:
        results['semi_hard'] = pd.read_csv(semi_hard_file)
    
    # Compare results
    if results:
        print("\nMining Strategies Comparison:")
        
        for strategy, result_df in results.items():
            if 'top1_accuracy' in result_df.columns:
                print(f"{strategy}:")
                print(f"  Top-1 Accuracy: {result_df['top1_accuracy'].values[0]:.4f}")
                print(f"  Top-3 Accuracy: {result_df['top3_accuracy'].values[0]:.4f}")
                print(f"  Top-5 Accuracy: {result_df['top5_accuracy'].values[0]:.4f}")
        
        # Create visualization
        if all(k in results for k in ['hard_negative', 'semi_hard']):
            metrics = ['top1_accuracy', 'top3_accuracy', 'top5_accuracy']
            values = {
                'hard_negative': [results['hard_negative'][m].values[0] for m in metrics],
                'semi_hard': [results['semi_hard'][m].values[0] for m in metrics]
            }
            
            plt.figure(figsize=(10, 6))
            x = np.arange(len(metrics))
            width = 0.35
            
            plt.bar(x - width/2, values['hard_negative'], width, label='Hard Negative Mining')
            plt.bar(x + width/2, values['semi_hard'], width, label='Semi-Hard Negative Mining')
            
            plt.ylabel('Accuracy')
            plt.title('Impact of Mining Strategy')
            plt.xticks(x, ['Top-1', 'Top-3', 'Top-5'])
            plt.legend()
            
            # Save figure
            plt.tight_layout()
            fig_path = os.path.join(output_dir, 'mining_strategies_comparison.png')
            plt.savefig(fig_path)
            print(f"Saved mining strategies comparison to {fig_path}")
    
    return results

def test_data_augmentation(test_file, loinc_file, checkpoint_dir, output_dir, fold=0, expanded_pool=False, augmented_test=False):
    """
    Test the impact of data augmentation
    
    Args:
        test_file: Path to test data
        loinc_file: Path to LOINC data
        checkpoint_dir: Directory with model checkpoints
        output_dir: Directory to save results
        fold: Model fold to evaluate
        expanded_pool: Whether to use expanded target pool
        augmented_test: Whether to use augmented test data
    
    Returns:
        results: Dictionary with results with and without data augmentation
    """
    print("\n=== ABLATION STUDY: DATA AUGMENTATION ===")
    
    results = {}
    
    # Test with data augmentation (default model)
    with_augmentation_file = run_component_evaluation(
        'data_augmentation', 'with_augmentation', 
        test_file, loinc_file, checkpoint_dir, output_dir, 
        fold, expanded_pool, augmented_test
    )
    
    if with_augmentation_file:
        results['with_augmentation'] = pd.read_csv(with_augmentation_file)
    
    # Test without data augmentation
    without_augmentation_file = run_component_evaluation(
        'data_augmentation', 'without_augmentation', 
        test_file, loinc_file, checkpoint_dir, output_dir, 
        fold, expanded_pool, augmented_test
    )
    
    if without_augmentation_file:
        results['without_augmentation'] = pd.read_csv(without_augmentation_file)
    
    # Compare results
    if results:
        print("\nData Augmentation Comparison:")
        
        for aug_setting, result_df in results.items():
            if 'top1_accuracy' in result_df.columns:
                print(f"{aug_setting}:")
                print(f"  Top-1 Accuracy: {result_df['top1_accuracy'].values[0]:.4f}")
                print(f"  Top-3 Accuracy: {result_df['top3_accuracy'].values[0]:.4f}")
                print(f"  Top-5 Accuracy: {result_df['top5_accuracy'].values[0]:.4f}")
        
        # Create visualization
        if all(k in results for k in ['with_augmentation', 'without_augmentation']):
            metrics = ['top1_accuracy', 'top3_accuracy', 'top5_accuracy']
            values = {
                'with_augmentation': [results['with_augmentation'][m].values[0] for m in metrics],
                'without_augmentation': [results['without_augmentation'][m].values[0] for m in metrics]
            }
            
            plt.figure(figsize=(10, 6))
            x = np.arange(len(metrics))
            width = 0.35
            
            plt.bar(x - width/2, values['with_augmentation'], width, label='With Augmentation')
            plt.bar(x + width/2, values['without_augmentation'], width, label='Without Augmentation')
            
            plt.ylabel('Accuracy')
            plt.title('Impact of Data Augmentation')
            plt.xticks(x, ['Top-1', 'Top-3', 'Top-5'])
            plt.legend()
            
            # Save figure
            plt.tight_layout()
            fig_path = os.path.join(output_dir, 'data_augmentation_comparison.png')
            plt.savefig(fig_path)
            print(f"Saved data augmentation comparison to {fig_path}")
    
    return results

def test_model_size(test_file, loinc_file, checkpoint_dir, output_dir, fold=0, expanded_pool=False, augmented_test=False):
    """
    Test the impact of model size (if different size models are available)
    
    Args:
        test_file: Path to test data
        loinc_file: Path to LOINC data
        checkpoint_dir: Directory with model checkpoints
        output_dir: Directory to save results
        fold: Model fold to evaluate
        expanded_pool: Whether to use expanded target pool
        augmented_test: Whether to use augmented test data
    
    Returns:
        results: Dictionary with results for different model sizes
    """
    print("\n=== ABLATION STUDY: MODEL SIZE ===")
    
    results = {}
    
    # List of model sizes to test (if available)
    model_sizes = ['st5_base', 'st5_large']
    
    for size in model_sizes:
        result_file = run_component_evaluation(
            'model_size', size, 
            test_file, loinc_file, checkpoint_dir, output_dir, 
            fold, expanded_pool, augmented_test
        )
        
        if result_file:
            results[size] = pd.read_csv(result_file)
    
    # Compare results
    if results:
        print("\nModel Size Comparison:")
        
        for size, result_df in results.items():
            if 'top1_accuracy' in result_df.columns:
                print(f"{size}:")
                print(f"  Top-1 Accuracy: {result_df['top1_accuracy'].values[0]:.4f}")
                print(f"  Top-3 Accuracy: {result_df['top3_accuracy'].values[0]:.4f}")
                print(f"  Top-5 Accuracy: {result_df['top5_accuracy'].values[0]:.4f}")
        
        # Create visualization if we have at least 2 different model sizes
        if len(results) >= 2:
            metrics = ['top1_accuracy', 'top3_accuracy', 'top5_accuracy']
            values = {
                size: [results[size][m].values[0] for m in metrics] 
                for size in results.keys()
            }
            
            plt.figure(figsize=(10, 6))
            x = np.arange(len(metrics))
            width = 0.35 / len(results)
            
            for i, (size, vals) in enumerate(values.items()):
                plt.bar(x + (i - len(results)/2 + 0.5) * width, vals, width, label=size)
            
            plt.ylabel('Accuracy')
            plt.title('Impact of Model Size')
            plt.xticks(x, ['Top-1', 'Top-3', 'Top-5'])
            plt.legend()
            
            # Save figure
            plt.tight_layout()
            fig_path = os.path.join(output_dir, 'model_size_comparison.png')
            plt.savefig(fig_path)
            print(f"Saved model size comparison to {fig_path}")
    
    return results

def save_ablation_summary(all_results, output_dir):
    """
    Save a summary of all ablation study results
    
    Args:
        all_results: Dictionary with results from all ablation studies
        output_dir: Directory to save summary
    """
    summary_file = os.path.join(output_dir, 'ablation_study_summary.txt')
    
    with open(summary_file, 'w') as f:
        f.write("=== LOINC STANDARDIZATION MODEL ABLATION STUDY SUMMARY ===\n\n")
        
        for component, results in all_results.items():
            f.write(f"\n{component.upper()} ABLATION STUDY\n")
            f.write(f"{'-'*50}\n")
            
            if not results:
                f.write("No results available\n")
                continue
            
            # Format the results as a table
            metrics = ['top1_accuracy', 'top3_accuracy', 'top5_accuracy']
            metric_labels = ['Top-1 Accuracy', 'Top-3 Accuracy', 'Top-5 Accuracy']
            
            # Get all values for this component
            values = {}
            for setting, result_df in results.items():
                if all(m in result_df.columns for m in metrics):
                    values[setting] = [result_df[m].values[0] for m in metrics]
            
            # Write table header
            f.write(f"{'Setting':<20}")
            for label in metric_labels:
                f.write(f"{label:<20}")
            f.write("\n")
            
            f.write(f"{'-'*80}\n")
            
            # Write table rows
            for setting, vals in values.items():
                f.write(f"{setting:<20}")
                for val in vals:
                    f.write(f"{val*100:.2f}%{' ':<14}")
                f.write("\n")
            
            f.write("\n")
            
            # Calculate relative improvements
            if len(values) > 1:
                f.write("Relative Improvements:\n")
                
                # Find the baseline setting for each component
                baseline = {
                    'fine_tuning_stages': 'stage2_only',
                    'mining_strategy': 'hard_negative',  # Assuming this as baseline
                    'data_augmentation': 'without_augmentation',
                    'model_size': 'st5_base'
                }.get(component, next(iter(values.keys())))
                
                if baseline in values:
                    for setting, vals in values.items():
                        if setting != baseline:
                            f.write(f"{setting} vs {baseline}:\n")
                            for i, (metric, label) in enumerate(zip(metrics, metric_labels)):
                                improvement = vals[i] - values[baseline][i]
                                f.write(f"  {label}: {improvement*100:+.2f}% ({improvement/values[baseline][i]*100:+.2f}% relative)\n")
                    f.write("\n")
            
            f.write("\n")
    
    print(f"Saved ablation study summary to {summary_file}")

def main():
    parser = argparse.ArgumentParser(description='Run ablation studies for LOINC standardization model')
    parser.add_argument('--test_file', type=str, required=True, 
                        help='Path to test data CSV')
    parser.add_argument('--loinc_file', type=str, required=True, 
                        help='Path to LOINC data CSV')
    parser.add_argument('--checkpoint_dir', type=str, required=True, 
                        help='Directory containing model checkpoints')
    parser.add_argument('--output_dir', type=str, default='results/ablation', 
                        help='Directory to save ablation study results')
    parser.add_argument('--fold', type=int, default=0, 
                        help='Fold to use for ablation studies (0-indexed)')
    parser.add_argument('--batch_size', type=int, default=16, 
                        help='Batch size for inference')
    parser.add_argument('--max_samples', type=int, default=None,
                        help='Maximum number of samples to evaluate (for debugging or performance issues)')
    parser.add_argument('--skip_fine_tuning', action='store_true',
                        help='Skip fine-tuning stages ablation')
    parser.add_argument('--skip_mining', action='store_true',
                        help='Skip mining strategies ablation')
    parser.add_argument('--skip_augmentation', action='store_true',
                        help='Skip data augmentation ablation')
    parser.add_argument('--skip_model_size', action='store_true',
                        help='Skip model size ablation')
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load data
    print("Loading test data...")
    test_df = load_test_data(args.test_file)
    
    print("Loading LOINC targets...")
    loinc_df = load_target_loincs(args.loinc_file)
    
    # Create augmented test data for testing
    augmented_test_df = test_df.copy()
    if 'is_augmented' not in augmented_test_df.columns:
        augmented_test_df['is_augmented'] = False
    
    # Limit samples if specified
    if args.max_samples is not None and args.max_samples > 0 and args.max_samples < len(test_df):
        print(f"Limiting evaluation to {args.max_samples} samples (out of {len(test_df)} total)")
        test_df = test_df.sample(args.max_samples, random_state=42)
        augmented_test_df = augmented_test_df.sample(args.max_samples, random_state=42)
    
    # Fine-tuning stages ablation
    if not args.skip_fine_tuning:
        print("\n=== ABLATION STUDY: FINE-TUNING STAGES ===")
        ablation_fine_tuning_stages(
            test_df=test_df, 
            loinc_df=loinc_df, 
            checkpoint_dir=args.checkpoint_dir, 
            output_dir=args.output_dir, 
            fold=args.fold, 
            batch_size=args.batch_size,
            max_samples=args.max_samples
        )
    
    # Mining strategies ablation
    if not args.skip_mining:
        print("\n=== ABLATION STUDY: MINING STRATEGIES ===")
        ablation_mining_strategies(
            test_df=test_df, 
            loinc_df=loinc_df, 
            checkpoint_dir=args.checkpoint_dir, 
            output_dir=args.output_dir, 
            fold=args.fold, 
            batch_size=args.batch_size,
            max_samples=args.max_samples
        )
    
    # Data augmentation ablation
    if not args.skip_augmentation:
        print("\n=== ABLATION STUDY: DATA AUGMENTATION ===")
        ablation_data_augmentation(
            test_df=test_df, 
            loinc_df=loinc_df, 
            checkpoint_dir=args.checkpoint_dir, 
            output_dir=args.output_dir, 
            fold=args.fold, 
            batch_size=args.batch_size,
            max_samples=args.max_samples
        )
        
        # Also evaluate on augmented test data
        print("\n=== ABLATION STUDY: DATA AUGMENTATION ===")
        ablation_data_augmentation(
            test_df=augmented_test_df, 
            loinc_df=loinc_df, 
            checkpoint_dir=args.checkpoint_dir, 
            output_dir=args.output_dir, 
            fold=args.fold, 
            batch_size=args.batch_size, 
            augmented_test=True,
            max_samples=args.max_samples
        )
    
    # Model size ablation
    if not args.skip_model_size:
        print("\n=== ABLATION STUDY: MODEL SIZE ===")
        ablation_model_size(
            test_df=test_df, 
            loinc_df=loinc_df, 
            checkpoint_dir=args.checkpoint_dir, 
            output_dir=args.output_dir, 
            fold=args.fold, 
            batch_size=args.batch_size,
            max_samples=args.max_samples
        )
    
    # Create summary file
    summary_file = os.path.join(args.output_dir, 'ablation_study_summary.txt')
    with open(summary_file, 'w') as f:
        f.write("=== LOINC STANDARDIZATION MODEL ABLATION STUDY SUMMARY ===\n\n")
        f.write(f"Test File: {args.test_file}\n")
        f.write(f"LOINC File: {args.loinc_file}\n")
        f.write(f"Fold: {args.fold}\n\n")
        
        if not args.skip_fine_tuning:
            f.write("1. Fine-Tuning Stages Ablation\n")
            f.write("-----------------------------\n")
            f.write("Compared full two-stage fine-tuning with stage2-only fine-tuning.\n")
            f.write("See results in fine_tuning_stages_comparison.png\n\n")
        
        if not args.skip_mining:
            f.write("2. Mining Strategies Ablation\n")
            f.write("----------------------------\n")
            f.write("Compared hard negative mining with semi-hard mining.\n")
            f.write("See results in mining_strategies_comparison.png\n\n")
        
        if not args.skip_augmentation:
            f.write("3. Data Augmentation Ablation\n")
            f.write("----------------------------\n")
            f.write("Compared model trained with augmented data vs. without augmentation.\n")
            f.write("See results in data_augmentation_comparison.png\n\n")
        
        if not args.skip_model_size:
            f.write("4. Model Size Ablation\n")
            f.write("-----------------------\n")
            f.write("Compared different model sizes: st5-base vs. st5-large.\n")
            f.write("See results in model_size_comparison.png\n\n")
    
    print(f"Saved ablation study summary to {summary_file}")

def ablation_fine_tuning_stages(test_df, loinc_df, checkpoint_dir, output_dir, fold=0, batch_size=16, max_samples=None):
    """
    Ablation study for fine-tuning stages
    
    Args:
        test_df: Test data DataFrame
        loinc_df: LOINC data DataFrame
        checkpoint_dir: Directory with model checkpoints
        output_dir: Directory to save results
        fold: Fold to evaluate
        batch_size: Batch size for inference
        max_samples: Maximum number of samples to evaluate
    """
    ablation_configs = {
        'stage1_stage2': {
            'model_path': os.path.join(checkpoint_dir, f"stage2_fold{fold+1}_model.weights.h5"),
            'results': {}
        },
        'stage2_only': {
            'model_path': os.path.join(checkpoint_dir, f"stage2_only_fold{fold+1}_model.weights.h5"),
            'results': {}
        }
    }
    
    # Run evaluation for each configuration
    for config_name, config in ablation_configs.items():
        print(f"\nRunning fine_tuning_stages ablation test with {config_name}...")
        
        # Check if model exists, if not use default model
        if not os.path.exists(config['model_path']):
            print(f"WARNING: Checkpoint not found at {config['model_path']}, using default")
            config['model_path'] = os.path.join(checkpoint_dir, f"stage2_fold{fold+1}_model.weights.h5")
        
        # Get the actual file paths
        test_file_path = os.path.abspath(test_df.SOURCE.iloc[0]) if isinstance(test_df, pd.DataFrame) and hasattr(test_df, 'SOURCE') and len(test_df) > 0 else ""
        if not os.path.exists(test_file_path):
            # If the source column doesn't contain file paths, use the original test file
            test_file_path = os.path.abspath("output/mimic_pairs_processed.csv")
        
        loinc_file_path = os.path.abspath(loinc_df.LOINC_NUM.iloc[0]) if isinstance(loinc_df, pd.DataFrame) and hasattr(loinc_df, 'LOINC_NUM') and len(loinc_df) > 0 else ""
        if not os.path.exists(loinc_file_path):
            # If the loinc column doesn't contain file paths, use the original loinc file
            loinc_file_path = os.path.abspath("output/expanded_target_pool.csv")
        
        cmd = [
            'python', 'models/evaluation.py',
            '--test_file', test_file_path,
            '--loinc_file', loinc_file_path,
            '--checkpoint_dir', checkpoint_dir,
            '--output_dir', output_dir,
            '--fold', str(fold),
            '--expanded_pool',
            '--ablation_id', f"fine_tuning_stages_{config_name}"
        ]
        
        if max_samples is not None:
            cmd.extend(['--max_samples', str(max_samples)])
        
        print(f"Command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        
        # Read results
        result_file = os.path.join(output_dir, f"fold{fold}_expanded_ablation_fine_tuning_stages_{config_name}_results.csv")
        if os.path.exists(result_file):
            try:
                results = pd.read_csv(result_file)
                config['results'] = {
                    'top1_accuracy': results['top1_accuracy'].values[0],
                    'top3_accuracy': results['top3_accuracy'].values[0],
                    'top5_accuracy': results['top5_accuracy'].values[0]
                }
            except Exception as e:
                print(f"Error reading results from {result_file}: {e}")
    
    # Compare results
    print("\nFine-Tuning Stages Comparison:")
    for config_name, config in ablation_configs.items():
        if config['results']:
            print(f"{config_name}:")
            print(f"  Top-1 Accuracy: {config['results']['top1_accuracy']:.4f}")
            print(f"  Top-3 Accuracy: {config['results']['top3_accuracy']:.4f}")
            print(f"  Top-5 Accuracy: {config['results']['top5_accuracy']:.4f}")
    
    # Generate comparison plot
    try:
        plt.figure(figsize=(10, 6))
        accuracy_metrics = ['top1_accuracy', 'top3_accuracy', 'top5_accuracy']
        metric_labels = ['Top-1 Accuracy', 'Top-3 Accuracy', 'Top-5 Accuracy']
        
        x = np.arange(len(accuracy_metrics))
        width = 0.35
        
        configs = list(ablation_configs.keys())
        for i, config_name in enumerate(configs):
            if ablation_configs[config_name]['results']:
                values = [ablation_configs[config_name]['results'][metric] for metric in accuracy_metrics]
                plt.bar(x + (i - 0.5) * width, values, width, label=config_name)
        
        plt.xlabel('Metric')
        plt.ylabel('Accuracy')
        plt.title('Fine-Tuning Stages Comparison')
        plt.xticks(x, metric_labels)
        plt.ylim(0, 1.0)
        plt.legend()
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Save plot
        output_file = os.path.join(output_dir, 'fine_tuning_stages_comparison.png')
        plt.savefig(output_file)
        print(f"Saved fine-tuning stages comparison to {output_file}")
    except Exception as e:
        print(f"Error generating comparison plot: {e}")

def ablation_mining_strategies(test_df, loinc_df, checkpoint_dir, output_dir, fold=0, batch_size=16, max_samples=None):
    """
    Ablation study for mining strategies
    """
    ablation_configs = {
        'hard_negative': {
            'model_path': os.path.join(checkpoint_dir, f"stage2_hard_negative_fold{fold+1}_model.weights.h5"),
            'results': {}
        },
        'semi_hard': {
            'model_path': os.path.join(checkpoint_dir, f"stage2_semi_hard_fold{fold+1}_model.weights.h5"),
            'results': {}
        }
    }
    
    # Run evaluation for each configuration
    for config_name, config in ablation_configs.items():
        print(f"\nRunning mining_strategy ablation test with {config_name}...")
        
        # Check if model exists, if not use default model
        if not os.path.exists(config['model_path']):
            print(f"WARNING: Checkpoint not found at {config['model_path']}, using default")
            config['model_path'] = os.path.join(checkpoint_dir, f"stage2_fold{fold+1}_model.weights.h5")
        
        # Get the actual file paths
        test_file_path = os.path.abspath("output/mimic_pairs_processed.csv")
        loinc_file_path = os.path.abspath("output/expanded_target_pool.csv")
        
        cmd = [
            'python', 'models/evaluation.py',
            '--test_file', test_file_path,
            '--loinc_file', loinc_file_path,
            '--checkpoint_dir', checkpoint_dir,
            '--output_dir', output_dir,
            '--fold', str(fold),
            '--expanded_pool',
            '--ablation_id', f"mining_strategy_{config_name}"
        ]
        
        if max_samples is not None:
            cmd.extend(['--max_samples', str(max_samples)])
        
        print(f"Command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        
        # Read results
        result_file = os.path.join(output_dir, f"fold{fold}_expanded_ablation_mining_strategy_{config_name}_results.csv")
        if os.path.exists(result_file):
            try:
                results = pd.read_csv(result_file)
                config['results'] = {
                    'top1_accuracy': results['top1_accuracy'].values[0],
                    'top3_accuracy': results['top3_accuracy'].values[0],
                    'top5_accuracy': results['top5_accuracy'].values[0]
                }
            except Exception as e:
                print(f"Error reading results from {result_file}: {e}")
    
    # Compare results
    print("\nMining Strategies Comparison:")
    for config_name, config in ablation_configs.items():
        if config['results']:
            print(f"{config_name}:")
            print(f"  Top-1 Accuracy: {config['results']['top1_accuracy']:.4f}")
            print(f"  Top-3 Accuracy: {config['results']['top3_accuracy']:.4f}")
            print(f"  Top-5 Accuracy: {config['results']['top5_accuracy']:.4f}")
    
    # Generate comparison plot
    try:
        plt.figure(figsize=(10, 6))
        accuracy_metrics = ['top1_accuracy', 'top3_accuracy', 'top5_accuracy']
        metric_labels = ['Top-1 Accuracy', 'Top-3 Accuracy', 'Top-5 Accuracy']
        
        x = np.arange(len(accuracy_metrics))
        width = 0.35
        
        configs = list(ablation_configs.keys())
        for i, config_name in enumerate(configs):
            if ablation_configs[config_name]['results']:
                values = [ablation_configs[config_name]['results'][metric] for metric in accuracy_metrics]
                plt.bar(x + (i - 0.5) * width, values, width, label=config_name)
        
        plt.xlabel('Metric')
        plt.ylabel('Accuracy')
        plt.title('Mining Strategies Comparison')
        plt.xticks(x, metric_labels)
        plt.ylim(0, 1.0)
        plt.legend()
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Save plot
        output_file = os.path.join(output_dir, 'mining_strategies_comparison.png')
        plt.savefig(output_file)
        print(f"Saved mining strategies comparison to {output_file}")
    except Exception as e:
        print(f"Error generating comparison plot: {e}")

def ablation_data_augmentation(test_df, loinc_df, checkpoint_dir, output_dir, fold=0, batch_size=16, augmented_test=False, max_samples=None):
    """
    Ablation study for data augmentation
    """
    ablation_configs = {
        'with_augmentation': {
            'model_path': os.path.join(checkpoint_dir, f"stage2_fold{fold+1}_model.weights.h5"),
            'results': {}
        },
        'without_augmentation': {
            'model_path': os.path.join(checkpoint_dir, f"stage2_no_aug_fold{fold+1}_model.weights.h5"),
            'results': {}
        }
    }
    
    # Run evaluation for each configuration
    for config_name, config in ablation_configs.items():
        print(f"\nRunning data_augmentation ablation test with {config_name}...")
        
        # Check if model exists, if not use default model
        if not os.path.exists(config['model_path']):
            print(f"WARNING: Checkpoint not found at {config['model_path']}, using default")
            config['model_path'] = os.path.join(checkpoint_dir, f"stage2_fold{fold+1}_model.weights.h5")
        
        # Get the actual file paths
        test_file_path = os.path.abspath("output/mimic_pairs_processed.csv")
        if augmented_test:
            test_file_path = os.path.abspath("output/mimic_pairs_augmented.csv")
        
        loinc_file_path = os.path.abspath("output/expanded_target_pool.csv")
        
        cmd = [
            'python', 'models/evaluation.py',
            '--test_file', test_file_path,
            '--loinc_file', loinc_file_path,
            '--checkpoint_dir', checkpoint_dir,
            '--output_dir', output_dir,
            '--fold', str(fold),
            '--expanded_pool',
            '--ablation_id', f"data_augmentation_{config_name}"
        ]
        
        if augmented_test:
            cmd.append('--augmented_test')
        
        if max_samples is not None:
            cmd.extend(['--max_samples', str(max_samples)])
        
        print(f"Command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        
        # Read results
        result_file_name = f"fold{fold}_expanded_ablation_data_augmentation_{config_name}_results.csv"
        if augmented_test:
            result_file_name = f"fold{fold}_augmented_expanded_ablation_data_augmentation_{config_name}_results.csv"
        
        result_file = os.path.join(output_dir, result_file_name)
        if os.path.exists(result_file):
            try:
                results = pd.read_csv(result_file)
                config['results'] = {
                    'top1_accuracy': results['top1_accuracy'].values[0],
                    'top3_accuracy': results['top3_accuracy'].values[0],
                    'top5_accuracy': results['top5_accuracy'].values[0]
                }
            except Exception as e:
                print(f"Error reading results from {result_file}: {e}")
    
    # Compare results
    print("\nData Augmentation Comparison:")
    for config_name, config in ablation_configs.items():
        if config['results']:
            print(f"{config_name}:")
            print(f"  Top-1 Accuracy: {config['results']['top1_accuracy']:.4f}")
            print(f"  Top-3 Accuracy: {config['results']['top3_accuracy']:.4f}")
            print(f"  Top-5 Accuracy: {config['results']['top5_accuracy']:.4f}")
    
    # Generate comparison plot
    try:
        plt.figure(figsize=(10, 6))
        accuracy_metrics = ['top1_accuracy', 'top3_accuracy', 'top5_accuracy']
        metric_labels = ['Top-1 Accuracy', 'Top-3 Accuracy', 'Top-5 Accuracy']
        
        x = np.arange(len(accuracy_metrics))
        width = 0.35
        
        configs = list(ablation_configs.keys())
        for i, config_name in enumerate(configs):
            if ablation_configs[config_name]['results']:
                values = [ablation_configs[config_name]['results'][metric] for metric in accuracy_metrics]
                plt.bar(x + (i - 0.5) * width, values, width, label=config_name)
        
        plt.xlabel('Metric')
        plt.ylabel('Accuracy')
        plt.title('Data Augmentation Comparison')
        plt.xticks(x, metric_labels)
        plt.ylim(0, 1.0)
        plt.legend()
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Save plot
        output_file = os.path.join(output_dir, 'data_augmentation_comparison.png')
        plt.savefig(output_file)
        print(f"Saved data augmentation comparison to {output_file}")
    except Exception as e:
        print(f"Error generating comparison plot: {e}")

def ablation_model_size(test_df, loinc_df, checkpoint_dir, output_dir, fold=0, batch_size=16, max_samples=None):
    """
    Ablation study for model sizes
    """
    ablation_configs = {
        'st5_base': {
            'model_path': os.path.join(checkpoint_dir, f"st5_base_fold{fold+1}_model.weights.h5"),
            'results': {}
        },
        'st5_large': {
            'model_path': os.path.join(checkpoint_dir, f"st5_large_fold{fold+1}_model.weights.h5"),
            'results': {}
        }
    }
    
    # Run evaluation for each configuration
    for config_name, config in ablation_configs.items():
        print(f"\nRunning model_size ablation test with {config_name}...")
        
        # Check if model exists, if not use default model
        if not os.path.exists(config['model_path']):
            print(f"WARNING: Checkpoint not found at {config['model_path']}, using default")
            config['model_path'] = os.path.join(checkpoint_dir, f"stage2_fold{fold+1}_model.weights.h5")
        
        # Get the actual file paths
        test_file_path = os.path.abspath("output/mimic_pairs_processed.csv")
        loinc_file_path = os.path.abspath("output/expanded_target_pool.csv")
        
        cmd = [
            'python', 'models/evaluation.py',
            '--test_file', test_file_path,
            '--loinc_file', loinc_file_path,
            '--checkpoint_dir', checkpoint_dir,
            '--output_dir', output_dir,
            '--fold', str(fold),
            '--expanded_pool',
            '--ablation_id', f"model_size_{config_name}"
        ]
        
        if max_samples is not None:
            cmd.extend(['--max_samples', str(max_samples)])
        
        print(f"Command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        
        # Read results
        result_file = os.path.join(output_dir, f"fold{fold}_expanded_ablation_model_size_{config_name}_results.csv")
        if os.path.exists(result_file):
            try:
                results = pd.read_csv(result_file)
                config['results'] = {
                    'top1_accuracy': results['top1_accuracy'].values[0],
                    'top3_accuracy': results['top3_accuracy'].values[0],
                    'top5_accuracy': results['top5_accuracy'].values[0]
                }
            except Exception as e:
                print(f"Error reading results from {result_file}: {e}")
    
    # Compare results
    print("\nModel Size Comparison:")
    for config_name, config in ablation_configs.items():
        if config['results']:
            print(f"{config_name}:")
            print(f"  Top-1 Accuracy: {config['results']['top1_accuracy']:.4f}")
            print(f"  Top-3 Accuracy: {config['results']['top3_accuracy']:.4f}")
            print(f"  Top-5 Accuracy: {config['results']['top5_accuracy']:.4f}")
    
    # Generate comparison plot
    try:
        plt.figure(figsize=(10, 6))
        accuracy_metrics = ['top1_accuracy', 'top3_accuracy', 'top5_accuracy']
        metric_labels = ['Top-1 Accuracy', 'Top-3 Accuracy', 'Top-5 Accuracy']
        
        x = np.arange(len(accuracy_metrics))
        width = 0.35
        
        configs = list(ablation_configs.keys())
        for i, config_name in enumerate(configs):
            if ablation_configs[config_name]['results']:
                values = [ablation_configs[config_name]['results'][metric] for metric in accuracy_metrics]
                plt.bar(x + (i - 0.5) * width, values, width, label=config_name)
        
        plt.xlabel('Metric')
        plt.ylabel('Accuracy')
        plt.title('Model Size Comparison')
        plt.xticks(x, metric_labels)
        plt.ylim(0, 1.0)
        plt.legend()
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Save plot
        output_file = os.path.join(output_dir, 'model_size_comparison.png')
        plt.savefig(output_file)
        print(f"Saved model size comparison to {output_file}")
    except Exception as e:
        print(f"Error generating comparison plot: {e}")

if __name__ == "__main__":
    main() 