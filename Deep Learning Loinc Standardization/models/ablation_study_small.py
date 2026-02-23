#!/usr/bin/env python
"""
Simplified ablation study script for LOINC standardization model
using a smaller dataset to prevent performance issues.
"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import argparse
import subprocess

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_test_data(file_path, max_samples=50):
    """
    Load test data from a CSV file
    
    Args:
        file_path: Path to the test data CSV
        max_samples: Maximum number of samples to use
        
    Returns:
        pd.DataFrame: Test data
    """
    try:
        # Load the CSV file
        df = pd.read_csv(file_path)
        print(f"Loaded {len(df)} test samples from {file_path}")
        
        # Limit the number of samples if requested
        if max_samples is not None and max_samples > 0 and max_samples < len(df):
            df = df.sample(max_samples, random_state=42)
            print(f"Limited to {len(df)} samples")
        
        return df
    except Exception as e:
        print(f"Error loading test data: {e}")
        # Return an empty dataframe as a fallback
        return pd.DataFrame()

def load_target_loincs(file_path, max_samples=100):
    """
    Load LOINC targets from a CSV file
    
    Args:
        file_path: Path to the LOINC data CSV
        max_samples: Maximum number of target LOINCs to use
        
    Returns:
        pd.DataFrame: LOINC data
    """
    try:
        # Load the CSV file
        df = pd.read_csv(file_path)
        
        # Determine the target text column (some datasets use different column names)
        if 'LONG_COMMON_NAME' in df.columns:
            df['TARGET'] = df['LONG_COMMON_NAME']
            print("Using 'LONG_COMMON_NAME' as the target text column")
        elif 'DISPLAY_NAME' in df.columns:
            df['TARGET'] = df['DISPLAY_NAME']
            print("Using 'DISPLAY_NAME' as the target text column")
        else:
            print("WARNING: No recognized target text column found")
        
        print(f"Loaded {len(df)} LOINC targets from {file_path}")
        
        # Limit the number of targets if requested
        if max_samples is not None and max_samples > 0 and max_samples < len(df):
            df = df.sample(max_samples, random_state=42)
            print(f"Limited to {len(df)} targets")
        
        return df
    except Exception as e:
        print(f"Error loading LOINC targets: {e}")
        # Return an empty dataframe as a fallback
        return pd.DataFrame()

def run_ablation_comparison(test_file, loinc_file, output_dir, max_samples=50):
    """
    Run a simplified ablation comparison
    
    Args:
        test_file: Path to test data CSV
        loinc_file: Path to LOINC data CSV
        output_dir: Directory to save results
        max_samples: Maximum number of samples to evaluate
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Load data
    test_df = load_test_data(test_file, max_samples)
    loinc_df = load_target_loincs(loinc_file, max_samples)
    
    # Define ablation configurations
    ablation_configs = {
        'standard': {
            'args': ['--test_file', test_file, '--loinc_file', loinc_file, '--max_samples', str(max_samples)],
            'label': 'Standard Configuration',
            'results': {}
        },
        'expanded_pool': {
            'args': ['--test_file', test_file, '--loinc_file', loinc_file, '--expanded_pool', '--max_samples', str(max_samples)],
            'label': 'Expanded Target Pool',
            'results': {}
        },
        'augmented_test': {
            'args': ['--test_file', 'output/mimic_pairs_augmented.csv', '--loinc_file', loinc_file, '--augmented_test', '--max_samples', str(max_samples)],
            'label': 'Augmented Test Data',
            'results': {}
        }
    }
    
    # Run evaluation for each configuration
    print("\n=== RUNNING ABLATION COMPARISONS ===")
    
    for config_name, config in ablation_configs.items():
        print(f"\nRunning comparison for {config_name}...")
        
        # Prepare command
        cmd = ['python', 'models/evaluation.py'] + config['args'] + ['--output_dir', output_dir, '--fold', '0']
        
        print(f"Command: {' '.join(cmd)}")
        
        try:
            # Run the command
            subprocess.run(cmd, check=True)
            
            # Read results
            result_file = None
            for file in os.listdir(output_dir):
                if file.startswith('fold0') and file.endswith('.csv'):
                    result_file = os.path.join(output_dir, file)
                    break
            
            if result_file and os.path.exists(result_file):
                results = pd.read_csv(result_file)
                config['results'] = {
                    'top1_accuracy': results['top1_accuracy'].values[0],
                    'top3_accuracy': results['top3_accuracy'].values[0],
                    'top5_accuracy': results['top5_accuracy'].values[0]
                }
                print(f"Results loaded from {result_file}")
            else:
                print(f"No results file found for {config_name}")
        
        except Exception as e:
            print(f"Error running evaluation for {config_name}: {e}")
    
    # Generate comparison plot
    try:
        plt.figure(figsize=(12, 6))
        
        # Get metrics and config names
        metrics = ['top1_accuracy', 'top3_accuracy', 'top5_accuracy']
        metric_labels = ['Top-1 Accuracy', 'Top-3 Accuracy', 'Top-5 Accuracy']
        configs = list(ablation_configs.keys())
        
        # Set up the bar positions
        x = np.arange(len(metrics))
        width = 0.25
        offset = -width * (len(configs) - 1) / 2
        
        # Plot bars for each configuration
        for i, config_name in enumerate(configs):
            config = ablation_configs[config_name]
            if config['results']:
                values = [config['results'][metric] * 100 for metric in metrics]
                plt.bar(x + offset + i * width, values, width, label=config['label'])
        
        # Set labels and title
        plt.xlabel('Metric')
        plt.ylabel('Accuracy (%)')
        plt.title('LOINC Standardization Model Ablation Study')
        plt.xticks(x, metric_labels)
        plt.ylim(0, 100)
        plt.legend()
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Save the plot
        output_file = os.path.join(output_dir, 'ablation_comparison.png')
        plt.savefig(output_file)
        print(f"\nSaved ablation comparison plot to {output_file}")
        
        # Create a summary file
        summary_file = os.path.join(output_dir, 'ablation_summary.txt')
        with open(summary_file, 'w') as f:
            f.write("=== LOINC STANDARDIZATION MODEL ABLATION STUDY ===\n\n")
            
            for config_name, config in ablation_configs.items():
                f.write(f"{config['label']}:\n")
                if config['results']:
                    for metric in metrics:
                        value = config['results'][metric]
                        f.write(f"  {metric.replace('_', ' ').title()}: {value*100:.2f}%\n")
                else:
                    f.write("  No results available\n")
                f.write("\n")
        
        print(f"Saved ablation summary to {summary_file}")
        
    except Exception as e:
        print(f"Error generating comparison plot: {e}")

def main():
    parser = argparse.ArgumentParser(description='Run simplified ablation studies for LOINC standardization model')
    parser.add_argument('--test_file', type=str, default='output/mimic_pairs_processed.csv',
                      help='Path to test data CSV')
    parser.add_argument('--loinc_file', type=str, default='output/loinc_full_processed.csv',
                      help='Path to LOINC data CSV')
    parser.add_argument('--output_dir', type=str, default='results/ablation_small',
                      help='Directory to save results')
    parser.add_argument('--max_samples', type=int, default=50,
                      help='Maximum number of samples to evaluate')
    args = parser.parse_args()
    
    print("=== SIMPLIFIED ABLATION STUDY FOR LOINC STANDARDIZATION MODEL ===")
    print(f"Test file: {args.test_file}")
    print(f"LOINC file: {args.loinc_file}")
    print(f"Output directory: {args.output_dir}")
    print(f"Max samples: {args.max_samples}")
    
    # Run the ablation comparison
    run_ablation_comparison(args.test_file, args.loinc_file, args.output_dir, args.max_samples)
    
    print("\nSimplified ablation study completed! 🎉")

if __name__ == "__main__":
    main() 