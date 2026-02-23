#!/usr/bin/env python
"""
Error Analysis for LOINC Standardization Model

This script performs detailed error analysis on the model's predictions by:
1. Identifying incorrectly classified samples
2. Categorizing error types (e.g., semantically similar targets, property mismatches)
3. Calculating confusion between common target LOINC codes
4. Analyzing source text complexity and its impact on performance
"""
import os
import sys
import pandas as pd
import numpy as np
import argparse
from sklearn.metrics import pairwise_distances
from collections import defaultdict
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.t5_encoder import LOINCEncoder
from models.evaluation import load_test_data, load_target_loincs, load_model, compute_embeddings

def identify_errors(test_df, target_df, model, batch_size=16):
    """
    Identify incorrectly classified samples and analyze error patterns
    
    Args:
        test_df: DataFrame with test data
        target_df: DataFrame with LOINC targets
        model: Trained model
        batch_size: Batch size for inference
        
    Returns:
        error_df: DataFrame with error analysis results
    """
    # Get unique target LOINCs
    unique_target_loincs = target_df['LOINC_NUM'].unique()
    
    # Check if test LOINCs exist in target LOINCs
    test_loincs = test_df['LOINC_NUM'].unique()
    matching_loincs = set(test_loincs) & set(unique_target_loincs)
    print(f"Test data has {len(test_loincs)} unique LOINCs, {len(matching_loincs)} match with target LOINCs")
    
    # Get source texts and target LOINCs
    source_texts = test_df['SOURCE'].tolist()
    target_loincs = test_df['LOINC_NUM'].tolist()
    
    # Compute embeddings for target LOINCs
    print("Computing embeddings for target LOINCs...")
    target_texts = []
    target_loinc_list = []
    for loinc in tqdm(unique_target_loincs):
        # Use first matching text if multiple exist for the same LOINC code
        matching_rows = target_df[target_df['LOINC_NUM'] == loinc]
        target_text = matching_rows.iloc[0]['TARGET']
        target_texts.append(target_text)
        target_loinc_list.append(loinc)
    
    target_embeddings = compute_embeddings(target_texts, model, batch_size)
    
    # Compute embeddings for source texts
    print("Computing embeddings for source texts...")
    source_embeddings = compute_embeddings(source_texts, model, batch_size)
    
    # Create dictionary mapping LOINC codes to their indices in the target embeddings
    loinc_to_index = {loinc: i for i, loinc in enumerate(target_loinc_list)}
    
    # Calculate pairwise distances
    print("Calculating similarities...")
    # Using negative cosine distance (higher is better)
    similarities = -pairwise_distances(source_embeddings, target_embeddings, metric='cosine')
    
    # Create error analysis DataFrame
    error_data = []
    for i, (source_text, target_loinc) in enumerate(zip(source_texts, target_loincs)):
        if target_loinc not in loinc_to_index:
            # Skip samples where target LOINC is not in target pool
            continue
        
        # Get the true target index
        true_target_idx = loinc_to_index[target_loinc]
        
        # Get the top predicted targets
        top_k_indices = np.argsort(similarities[i])[::-1][:5]  # Get top 5
        top_k_loincs = [target_loinc_list[idx] for idx in top_k_indices]
        top_k_texts = [target_texts[idx] for idx in top_k_indices]
        top_k_scores = [similarities[i][idx] for idx in top_k_indices]
        
        # Check if the prediction is correct (top-1)
        is_correct = (top_k_indices[0] == true_target_idx)
        
        # Check the rank of the true target
        true_target_rank = np.where(top_k_indices == true_target_idx)[0]
        true_target_rank = true_target_rank[0] + 1 if len(true_target_rank) > 0 else -1
        
        error_data.append({
            'source_text': source_text,
            'true_loinc': target_loinc,
            'true_text': target_texts[true_target_idx],
            'pred_loinc': top_k_loincs[0],
            'pred_text': top_k_texts[0],
            'pred_score': top_k_scores[0],
            'true_target_rank': true_target_rank,
            'is_correct': is_correct,
            'top_5_loincs': ','.join(top_k_loincs),
            'top_5_scores': ','.join([f"{score:.4f}" for score in top_k_scores])
        })
    
    error_df = pd.DataFrame(error_data)
    
    # Calculate overall accuracy
    accuracy = error_df['is_correct'].mean()
    print(f"Overall Top-1 accuracy: {accuracy:.4f}")
    
    # Filter for just the errors
    error_df_filtered = error_df[~error_df['is_correct']]
    print(f"Found {len(error_df_filtered)} errors out of {len(error_df)} samples")
    
    return error_df

def categorize_errors(error_df):
    """
    Categorize error types
    
    Args:
        error_df: DataFrame with error analysis results
        
    Returns:
        error_df: DataFrame with added error category column
    """
    # Filter for just the errors
    errors_only = error_df[~error_df['is_correct']]
    
    print(f"Analyzing {len(errors_only)} errors...")
    
    # Create a copy to add categorization
    categorized_df = errors_only.copy()
    
    # Define error categories
    categories = {
        'SIMILAR_DESCRIPTION': 0,
        'PROPERTY_MISMATCH': 0,  # Property mismatch (e.g., Qual vs Quant)
        'SPECIMEN_MISMATCH': 0,  # Specimen mismatch (e.g., Blood vs Serum)
        'METHODOLOGICAL': 0,     # Methodological difference (e.g., Test strip vs Automated)
        'AMBIGUOUS_SOURCE': 0,   # Source text is ambiguous
        'COMPLETELY_DIFFERENT': 0,
        'OTHER': 0
    }
    
    # Terms that indicate qualitative/quantitative property
    quant_terms = ['#/vol', 'count', 'volume', 'mass', 'concentration', '[#]']
    qual_terms = ['presence', 'qual', 'ql', 'qualitative']
    
    # Terms that indicate specimen types
    specimen_types = {
        'serum': 'sr',
        'plasma': 'pl',
        'blood': 'bld',
        'urine': 'ur',
        'csf': 'csf',
        'fluid': 'fld'
    }
    
    # Method terms
    method_terms = ['test strip', 'automated', 'manual', 'calculated', 'observed']
    
    # Categorize each error
    for idx, row in categorized_df.iterrows():
        true_text = row['true_text'].lower()
        pred_text = row['pred_text'].lower()
        
        # Check for property mismatch (qual vs quant)
        true_is_quant = any(term in true_text for term in quant_terms)
        true_is_qual = any(term in true_text for term in qual_terms)
        pred_is_quant = any(term in pred_text for term in quant_terms)
        pred_is_qual = any(term in pred_text for term in qual_terms)
        
        if (true_is_quant and pred_is_qual) or (true_is_qual and pred_is_quant):
            categorized_df.at[idx, 'error_category'] = 'PROPERTY_MISMATCH'
            categories['PROPERTY_MISMATCH'] += 1
            continue
        
        # Check for specimen mismatch
        true_specimen = None
        pred_specimen = None
        for specimen, abbrev in specimen_types.items():
            if specimen in true_text or abbrev in true_text:
                true_specimen = specimen
            if specimen in pred_text or abbrev in pred_text:
                pred_specimen = specimen
        
        if true_specimen and pred_specimen and true_specimen != pred_specimen:
            categorized_df.at[idx, 'error_category'] = 'SPECIMEN_MISMATCH'
            categories['SPECIMEN_MISMATCH'] += 1
            continue
        
        # Check for methodological difference
        true_method = None
        pred_method = None
        for method in method_terms:
            if method in true_text:
                true_method = method
            if method in pred_text:
                pred_method = method
        
        if true_method and pred_method and true_method != pred_method:
            categorized_df.at[idx, 'error_category'] = 'METHODOLOGICAL'
            categories['METHODOLOGICAL'] += 1
            continue
        
        # Check for similarity in descriptions
        # Simple approach: count overlapping words
        true_words = set(true_text.lower().split())
        pred_words = set(pred_text.lower().split())
        overlap = len(true_words.intersection(pred_words))
        similarity_ratio = overlap / max(len(true_words), len(pred_words))
        
        if similarity_ratio > 0.7:
            categorized_df.at[idx, 'error_category'] = 'SIMILAR_DESCRIPTION'
            categories['SIMILAR_DESCRIPTION'] += 1
        elif similarity_ratio < 0.2:
            categorized_df.at[idx, 'error_category'] = 'COMPLETELY_DIFFERENT'
            categories['COMPLETELY_DIFFERENT'] += 1
        else:
            # Check for ambiguous source
            source_words = set(row['source_text'].lower().split())
            
            # If source has very few words, it might be ambiguous
            if len(source_words) < 3:
                categorized_df.at[idx, 'error_category'] = 'AMBIGUOUS_SOURCE'
                categories['AMBIGUOUS_SOURCE'] += 1
            else:
                categorized_df.at[idx, 'error_category'] = 'OTHER'
                categories['OTHER'] += 1
    
    # Print summary of error categories
    print("\nError Category Summary:")
    for category, count in categories.items():
        print(f"{category}: {count} ({count/len(categorized_df)*100:.1f}%)")
    
    # Merge back with original dataframe
    error_df = error_df.join(categorized_df[['error_category']], how='left')
    
    return error_df

def analyze_error_patterns(error_df):
    """
    Analyze patterns in errors
    
    Args:
        error_df: DataFrame with error analysis results
    """
    # Check which LOINCs are most commonly confused
    errors_only = error_df[~error_df['is_correct']]
    
    # Find the most common true LOINCs with errors
    true_loinc_counts = errors_only['true_loinc'].value_counts().head(10)
    print("\nMost Common True LOINCs with Errors:")
    for loinc, count in true_loinc_counts.items():
        print(f"LOINC: {loinc}, Error Count: {count}")
    
    # Find the most common predicted LOINCs (when wrong)
    pred_loinc_counts = errors_only['pred_loinc'].value_counts().head(10)
    print("\nMost Common Incorrectly Predicted LOINCs:")
    for loinc, count in pred_loinc_counts.items():
        print(f"LOINC: {loinc}, Error Count: {count}")
    
    # Analyze confusion between specific pairs
    confusion_pairs = errors_only.groupby(['true_loinc', 'pred_loinc']).size().reset_index(name='count')
    confusion_pairs = confusion_pairs.sort_values('count', ascending=False).head(10)
    print("\nMost Common Confusion Pairs:")
    for _, row in confusion_pairs.iterrows():
        # Find examples of these texts
        true_text = error_df[error_df['true_loinc'] == row['true_loinc']]['true_text'].iloc[0]
        pred_text = error_df[error_df['pred_loinc'] == row['pred_loinc']]['pred_text'].iloc[0]
        print(f"True LOINC: {row['true_loinc']} ({true_text})")
        print(f"Pred LOINC: {row['pred_loinc']} ({pred_text})")
        print(f"Confusion Count: {row['count']}\n")
    
    # Analyze error categories
    if 'error_category' in error_df.columns:
        category_counts = errors_only['error_category'].value_counts()
        print("\nError Categories:")
        for category, count in category_counts.items():
            print(f"{category}: {count} ({count/len(errors_only)*100:.1f}%)")
        
        # Create a horizontal bar chart of error categories
        plt.figure(figsize=(12, 6))
        sns.barplot(x=category_counts.values, y=category_counts.index)
        plt.title('Distribution of Error Categories')
        plt.xlabel('Count')
        plt.tight_layout()
        plt.savefig('error_categories.png')
        print(f"Saved error categories chart to error_categories.png")

def analyze_source_complexity(error_df):
    """
    Analyze the impact of source text complexity on model performance
    
    Args:
        error_df: DataFrame with error analysis results
    """
    # Add source text length and word count columns
    error_df['source_length'] = error_df['source_text'].apply(len)
    error_df['source_word_count'] = error_df['source_text'].apply(lambda x: len(x.split()))
    
    # Compare distributions for correct vs incorrect predictions
    correct_df = error_df[error_df['is_correct']]
    incorrect_df = error_df[~error_df['is_correct']]
    
    print("\nSource Text Complexity Analysis:")
    print(f"Average source text length (correct): {correct_df['source_length'].mean():.2f}")
    print(f"Average source text length (incorrect): {incorrect_df['source_length'].mean():.2f}")
    
    print(f"Average source word count (correct): {correct_df['source_word_count'].mean():.2f}")
    print(f"Average source word count (incorrect): {incorrect_df['source_word_count'].mean():.2f}")
    
    # Create histograms comparing text length and word count
    plt.figure(figsize=(15, 6))
    
    plt.subplot(1, 2, 1)
    sns.histplot(data=error_df, x='source_length', hue='is_correct', bins=15, element='step')
    plt.title('Source Text Length vs. Prediction Correctness')
    plt.xlabel('Source Text Length (characters)')
    
    plt.subplot(1, 2, 2)
    sns.histplot(data=error_df, x='source_word_count', hue='is_correct', bins=10, element='step')
    plt.title('Source Word Count vs. Prediction Correctness')
    plt.xlabel('Source Text Word Count')
    
    plt.tight_layout()
    plt.savefig('source_complexity.png')
    print(f"Saved source complexity analysis to source_complexity.png")

def main():
    parser = argparse.ArgumentParser(description='Error analysis for LOINC standardization model')
    parser.add_argument('--test_file', type=str, required=True, 
                        help='Path to test data CSV')
    parser.add_argument('--loinc_file', type=str, required=True, 
                        help='Path to LOINC data CSV')
    parser.add_argument('--checkpoint_dir', type=str, default='models/checkpoints', 
                        help='Directory containing model checkpoints')
    parser.add_argument('--fold', type=int, default=0, 
                        help='Fold to analyze (0-indexed)')
    parser.add_argument('--output_dir', type=str, default='results/error_analysis', 
                        help='Directory to save error analysis results')
    parser.add_argument('--batch_size', type=int, default=16, 
                        help='Batch size for embedding computation')
    parser.add_argument('--no_plots', action='store_true',
                        help='Do not generate plots')
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load data
    print("Loading test data...")
    test_df = load_test_data(args.test_file)
    
    print("Loading LOINC targets...")
    target_df = load_target_loincs(args.loinc_file)
    
    # Load model
    print(f"Loading model for fold {args.fold}...")
    model = load_model(args.checkpoint_dir, args.fold)
    
    # Identify errors
    print("Identifying errors...")
    error_df = identify_errors(test_df, target_df, model, args.batch_size)
    
    # Categorize errors
    print("Categorizing errors...")
    error_df = categorize_errors(error_df)
    
    # Analyze error patterns
    print("Analyzing error patterns...")
    analyze_error_patterns(error_df)
    
    # Analyze source complexity
    print("Analyzing source text complexity...")
    analyze_source_complexity(error_df)
    
    # Save error analysis results
    output_file = os.path.join(args.output_dir, f'fold{args.fold}_error_analysis.csv')
    error_df.to_csv(output_file, index=False)
    print(f"Saved error analysis results to {output_file}")
    
    # Create summary file with key findings
    summary_file = os.path.join(args.output_dir, f'fold{args.fold}_error_summary.txt')
    with open(summary_file, 'w') as f:
        f.write("=== LOINC STANDARDIZATION MODEL ERROR ANALYSIS ===\n\n")
        f.write(f"Test File: {args.test_file}\n")
        f.write(f"LOINC File: {args.loinc_file}\n")
        f.write(f"Fold: {args.fold}\n\n")
        
        f.write(f"Total samples analyzed: {len(error_df)}\n")
        f.write(f"Correct predictions: {len(error_df[error_df['is_correct']])} ({len(error_df[error_df['is_correct']])/len(error_df)*100:.1f}%)\n")
        f.write(f"Incorrect predictions: {len(error_df[~error_df['is_correct']])} ({len(error_df[~error_df['is_correct']])/len(error_df)*100:.1f}%)\n\n")
        
        # Error categories
        if 'error_category' in error_df.columns:
            f.write("Error Categories:\n")
            category_counts = error_df[~error_df['is_correct']]['error_category'].value_counts()
            for category, count in category_counts.items():
                f.write(f"- {category}: {count} ({count/len(error_df[~error_df['is_correct']])*100:.1f}%)\n")
            f.write("\n")
        
        # Most confused LOINCs
        f.write("Most Commonly Confused LOINC Pairs:\n")
        confusion_pairs = error_df[~error_df['is_correct']].groupby(['true_loinc', 'pred_loinc']).size().reset_index(name='count')
        confusion_pairs = confusion_pairs.sort_values('count', ascending=False).head(5)
        for _, row in confusion_pairs.iterrows():
            true_text = error_df[error_df['true_loinc'] == row['true_loinc']]['true_text'].iloc[0]
            pred_text = error_df[error_df['pred_loinc'] == row['pred_loinc']]['pred_text'].iloc[0]
            f.write(f"- True: {row['true_loinc']} ({true_text})\n")
            f.write(f"  Pred: {row['pred_loinc']} ({pred_text})\n")
            f.write(f"  Count: {row['count']}\n\n")
        
        # Source complexity
        f.write("Source Text Complexity:\n")
        f.write(f"- Average source text length (correct): {error_df[error_df['is_correct']]['source_length'].mean():.2f}\n")
        f.write(f"- Average source text length (incorrect): {error_df[~error_df['is_correct']]['source_length'].mean():.2f}\n")
        f.write(f"- Average source word count (correct): {error_df[error_df['is_correct']]['source_word_count'].mean():.2f}\n")
        f.write(f"- Average source word count (incorrect): {error_df[~error_df['is_correct']]['source_word_count'].mean():.2f}\n")
    
    print(f"Saved error analysis summary to {summary_file}")

if __name__ == "__main__":
    main() 