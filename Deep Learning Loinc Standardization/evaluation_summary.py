#!/usr/bin/env python
"""
Generate a summary of the LOINC standardization model evaluation results.
This script collects and summarizes the results from all evaluation runs.
"""
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import glob
import json

def find_results_files(results_dir):
    """
    Find all results files in the given directory
    
    Args:
        results_dir: Directory containing results
        
    Returns:
        dict: Dictionary of result file paths by type
    """
    result_files = {
        'standard': [],
        'expanded': [],
        'augmented': [],
        'augmented_expanded': [],
        'error_analysis': [],
        'ablation': []
    }
    
    # Find all CSV files in the results directory
    for file_path in glob.glob(os.path.join(results_dir, '**', '*.csv'), recursive=True):
        file_name = os.path.basename(file_path)
        
        if 'error_analysis' in file_path:
            result_files['error_analysis'].append(file_path)
        elif 'ablation' in file_path:
            result_files['ablation'].append(file_path)
        elif 'augmented_expanded' in file_name:
            result_files['augmented_expanded'].append(file_path)
        elif 'augmented' in file_name:
            result_files['augmented'].append(file_path)
        elif 'expanded' in file_name:
            result_files['expanded'].append(file_path)
        else:
            result_files['standard'].append(file_path)
    
    return result_files

def load_results(result_files):
    """
    Load results from files
    
    Args:
        result_files: Dictionary of result file paths
        
    Returns:
        dict: Dictionary of results DataFrames
    """
    results = {}
    
    for result_type, file_paths in result_files.items():
        if file_paths:
            try:
                # Try to load and concatenate all result files for this type
                dfs = []
                for file_path in file_paths:
                    try:
                        df = pd.read_csv(file_path)
                        
                        # Add result type and file name as columns
                        df['result_type'] = result_type
                        df['file_name'] = os.path.basename(file_path)
                        
                        # Extract fold from filename if possible
                        try:
                            if 'fold' in os.path.basename(file_path):
                                fold = int(os.path.basename(file_path).split('fold')[1].split('_')[0])
                                df['fold'] = fold
                        except:
                            pass
                        
                        dfs.append(df)
                    except Exception as e:
                        print(f"Error loading {file_path}: {e}")
                
                if dfs:
                    results[result_type] = pd.concat(dfs, ignore_index=True)
                else:
                    print(f"No valid results found for {result_type}")
            except Exception as e:
                print(f"Error processing {result_type} results: {e}")
    
    return results

def analyze_standard_results(results):
    """
    Analyze standard evaluation results
    
    Args:
        results: Dictionary of results DataFrames
        
    Returns:
        str: Summary of standard results
    """
    summary = []
    summary.append("=== STANDARD EVALUATION RESULTS ===")
    
    if 'standard' in results and not results['standard'].empty:
        df = results['standard']
        
        # Calculate mean and std for accuracy metrics
        metrics = ['top1_accuracy', 'top3_accuracy', 'top5_accuracy']
        for metric in metrics:
            if metric in df.columns:
                mean = df[metric].mean()
                std = df[metric].std() if len(df) > 1 else 0
                summary.append(f"{metric.replace('_', ' ').title()}: {mean*100:.2f}% ± {std*100:.2f}%")
        
        summary.append(f"Number of folds: {len(df)}")
        summary.append("")
    else:
        summary.append("No standard evaluation results found.")
        summary.append("")
    
    return "\n".join(summary)

def analyze_expanded_results(results):
    """
    Analyze expanded target pool evaluation results
    
    Args:
        results: Dictionary of results DataFrames
        
    Returns:
        str: Summary of expanded target pool results
    """
    summary = []
    summary.append("=== EXPANDED TARGET POOL RESULTS ===")
    
    if 'expanded' in results and not results['expanded'].empty:
        df = results['expanded']
        
        # Calculate mean and std for accuracy metrics
        metrics = ['top1_accuracy', 'top3_accuracy', 'top5_accuracy']
        for metric in metrics:
            if metric in df.columns:
                mean = df[metric].mean()
                std = df[metric].std() if len(df) > 1 else 0
                summary.append(f"{metric.replace('_', ' ').title()}: {mean*100:.2f}% ± {std*100:.2f}%")
        
        # Compare to standard results
        if 'standard' in results and not results['standard'].empty:
            std_df = results['standard']
            for metric in metrics:
                if metric in df.columns and metric in std_df.columns:
                    std_mean = std_df[metric].mean()
                    mean = df[metric].mean()
                    diff = mean - std_mean
                    summary.append(f"{metric.replace('_', ' ').title()} Change: {diff*100:+.2f}%")
        
        summary.append(f"Number of folds: {len(df)}")
        summary.append("")
    else:
        summary.append("No expanded target pool results found.")
        summary.append("")
    
    return "\n".join(summary)

def analyze_augmented_results(results):
    """
    Analyze augmented test data evaluation results
    
    Args:
        results: Dictionary of results DataFrames
        
    Returns:
        str: Summary of augmented test data results
    """
    summary = []
    summary.append("=== AUGMENTED TEST DATA RESULTS ===")
    
    if 'augmented' in results and not results['augmented'].empty:
        df = results['augmented']
        
        # Calculate mean and std for accuracy metrics
        metrics = ['top1_accuracy', 'top3_accuracy', 'top5_accuracy']
        for metric in metrics:
            if metric in df.columns:
                mean = df[metric].mean()
                std = df[metric].std() if len(df) > 1 else 0
                summary.append(f"{metric.replace('_', ' ').title()}: {mean*100:.2f}% ± {std*100:.2f}%")
        
        # Compare to standard results
        if 'standard' in results and not results['standard'].empty:
            std_df = results['standard']
            for metric in metrics:
                if metric in df.columns and metric in std_df.columns:
                    std_mean = std_df[metric].mean()
                    mean = df[metric].mean()
                    diff = mean - std_mean
                    summary.append(f"{metric.replace('_', ' ').title()} Change: {diff*100:+.2f}%")
        
        summary.append(f"Number of folds: {len(df)}")
        summary.append("")
    else:
        summary.append("No augmented test data results found.")
        summary.append("")
    
    return "\n".join(summary)

def analyze_error_analysis(results):
    """
    Analyze error analysis results
    
    Args:
        results: Dictionary of results DataFrames
        
    Returns:
        str: Summary of error analysis
    """
    summary = []
    summary.append("=== ERROR ANALYSIS SUMMARY ===")
    
    if 'error_analysis' in results and not results['error_analysis'].empty:
        df = results['error_analysis']
        
        # Get unique error categories and their counts
        if 'error_category' in df.columns:
            error_categories = df['error_category'].value_counts()
            total_errors = len(df)
            
            summary.append(f"Total Errors Analyzed: {total_errors}")
            summary.append("Error Categories:")
            
            for category, count in error_categories.items():
                percentage = count / total_errors * 100
                summary.append(f"  {category}: {count} ({percentage:.1f}%)")
            
            # Get confusion pairs
            if 'true_loinc' in df.columns and 'pred_loinc' in df.columns:
                confusion_pairs = df.groupby(['true_loinc', 'pred_loinc']).size().sort_values(ascending=False).head(5)
                
                summary.append("\nTop Confusion Pairs:")
                for (true_loinc, pred_loinc), count in confusion_pairs.items():
                    true_name = df[df['true_loinc'] == true_loinc]['true_name'].iloc[0] if 'true_name' in df.columns else ''
                    pred_name = df[df['pred_loinc'] == pred_loinc]['pred_name'].iloc[0] if 'pred_name' in df.columns else ''
                    summary.append(f"  {true_loinc} ({true_name}) → {pred_loinc} ({pred_name}): {count}")
        
        summary.append("")
    else:
        summary.append("No error analysis results found.")
        summary.append("")
    
    return "\n".join(summary)

def generate_comparison_plots(results, output_dir):
    """
    Generate comparison plots for different evaluation settings
    
    Args:
        results: Dictionary of results DataFrames
        output_dir: Directory to save plots
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Prepare data for plots
    plot_data = []
    labels = []
    
    for result_type in ['standard', 'expanded', 'augmented', 'augmented_expanded']:
        if result_type in results and not results[result_type].empty:
            df = results[result_type]
            
            metrics = ['top1_accuracy', 'top3_accuracy', 'top5_accuracy']
            for metric in metrics:
                if metric in df.columns:
                    mean = df[metric].mean()
                    label = f"{result_type.replace('_', ' ').title()} - {metric.replace('_', ' ').title()}"
                    plot_data.append(mean)
                    labels.append(label)
    
    if plot_data:
        # Create bar chart
        fig, ax = plt.figure(figsize=(12, 8)), plt.subplot(111)
        pos = np.arange(len(plot_data))
        ax.bar(pos, [d * 100 for d in plot_data], align='center', alpha=0.5)
        ax.set_xticks(pos)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.set_ylabel('Accuracy (%)')
        ax.set_title('LOINC Standardization Model Evaluation Results')
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Add values on bars
        for i, val in enumerate(plot_data):
            ax.text(i, val * 100 + 1, f"{val*100:.1f}%", ha='center')
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'evaluation_comparison.png'))
        plt.close()
        
        # Create grouped bar chart for metrics
        metrics = ['top1_accuracy', 'top3_accuracy', 'top5_accuracy']
        result_types = ['standard', 'expanded', 'augmented', 'augmented_expanded']
        
        data = {}
        for result_type in result_types:
            if result_type in results and not results[result_type].empty:
                df = results[result_type]
                data[result_type] = [df[metric].mean() * 100 if metric in df.columns else 0 for metric in metrics]
        
        if data:
            fig, ax = plt.figure(figsize=(10, 6)), plt.subplot(111)
            x = np.arange(len(metrics))
            width = 0.2
            offset = -width * (len(data) - 1) / 2
            
            for i, (result_type, values) in enumerate(data.items()):
                pos = x + offset + i * width
                ax.bar(pos, values, width, label=result_type.replace('_', ' ').title())
            
            ax.set_ylabel('Accuracy (%)')
            ax.set_title('Comparison of Accuracy Metrics Across Evaluation Settings')
            ax.set_xticks(x)
            ax.set_xticklabels([m.replace('_', ' ').title() for m in metrics])
            ax.legend()
            ax.grid(axis='y', linestyle='--', alpha=0.7)
            
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'metrics_comparison.png'))
            plt.close()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate summary of evaluation results')
    parser.add_argument('--results_dir', type=str, default='results/controlled_evaluation',
                        help='Directory containing evaluation results')
    parser.add_argument('--output_dir', type=str, default='results/summary',
                        help='Directory to save summary')
    args = parser.parse_args()
    
    print(f"Analyzing evaluation results in {args.results_dir}...")
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Find result files
    result_files = find_results_files(args.results_dir)
    
    # Load results
    results = load_results(result_files)
    
    # Generate summary
    summary_parts = []
    summary_parts.append("=" * 80)
    summary_parts.append("LOINC STANDARDIZATION MODEL EVALUATION SUMMARY")
    summary_parts.append("=" * 80)
    summary_parts.append("")
    
    # Add specific analysis for each result type
    summary_parts.append(analyze_standard_results(results))
    summary_parts.append(analyze_expanded_results(results))
    summary_parts.append(analyze_augmented_results(results))
    summary_parts.append(analyze_error_analysis(results))
    
    # Generate comparison plots
    generate_comparison_plots(results, args.output_dir)
    
    # Save summary to file
    summary_text = "\n".join(summary_parts)
    summary_file = os.path.join(args.output_dir, 'evaluation_summary.txt')
    with open(summary_file, 'w') as f:
        f.write(summary_text)
    
    # Save results as JSON
    results_json = {}
    for result_type, df in results.items():
        if not df.empty:
            results_json[result_type] = json.loads(df.to_json(orient='records'))
    
    json_file = os.path.join(args.output_dir, 'evaluation_results.json')
    with open(json_file, 'w') as f:
        json.dump(results_json, f, indent=2)
    
    print(f"Saved summary to {summary_file}")
    print(f"Saved results JSON to {json_file}")
    print("Generated comparison plots:")
    print(f"  - {os.path.join(args.output_dir, 'evaluation_comparison.png')}")
    print(f"  - {os.path.join(args.output_dir, 'metrics_comparison.png')}")
    
    # Print a brief summary to the console
    print("\nBrief Summary:")
    for result_type in ['standard', 'expanded', 'augmented']:
        if result_type in results and not results[result_type].empty:
            df = results[result_type]
            if 'top1_accuracy' in df.columns:
                mean = df['top1_accuracy'].mean()
                print(f"{result_type.replace('_', ' ').title()} Top-1 Accuracy: {mean*100:.2f}%")

if __name__ == "__main__":
    main() 