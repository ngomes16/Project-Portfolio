import pandas as pd
import numpy as np
import os
import argparse
import tensorflow as tf
from tqdm import tqdm
from sklearn.metrics import precision_recall_curve, f1_score, confusion_matrix, roc_curve, auc
import matplotlib.pyplot as plt
import sys
import random

# Add parent directory to path to import from other modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import model loading and embedding functions
from models.evaluation import load_model, compute_embeddings

def load_data(mimic_file, loinc_file, d_labitems_file=None, limit_samples=None, seed=42):
    """
    Load data including negative examples from D_LABITEMS
    
    Args:
        mimic_file: Path to MIMIC mapped pairs CSV
        loinc_file: Path to LOINC targets CSV
        d_labitems_file: Path to D_LABITEMS.csv for non-mappable codes
        limit_samples: Limit number of samples to load
        seed: Random seed for reproducibility
        
    Returns:
        positive_df: DataFrame with mappable examples
        negative_df: DataFrame with unmappable examples (or None)
        loinc_df: DataFrame with LOINC targets
    """
    print(f"Loading positive examples from {mimic_file}...")
    positive_df = pd.read_csv(mimic_file)
    
    # Rename columns to standardized format
    if 'source_text' in positive_df.columns and 'target_loinc' in positive_df.columns:
        positive_df = positive_df.rename(columns={
            'source_text': 'SOURCE',
            'target_loinc': 'LOINC_NUM'
        })
    
    if limit_samples:
        positive_df = positive_df.sample(min(limit_samples, len(positive_df)), random_state=seed)
    
    print(f"Loaded {len(positive_df)} positive examples")
    
    print(f"Loading LOINC targets from {loinc_file}...")
    loinc_df = pd.read_csv(loinc_file)
    print(f"Loaded {len(loinc_df)} LOINC targets")
    
    negative_df = None
    if d_labitems_file and os.path.exists(d_labitems_file):
        print(f"Loading negative examples from {d_labitems_file}...")
        try:
            # Load D_LABITEMS.csv
            labitems_df = pd.read_csv(d_labitems_file)
            
            # Extract codes without LOINC mappings (unmappable)
            unmapped_df = labitems_df[labitems_df['LOINC_CODE'].isna()]
            
            # Create negative examples DataFrame
            negative_df = pd.DataFrame({
                'SOURCE': unmapped_df['LABEL'].tolist(),
                'FLUID': unmapped_df['FLUID'].tolist(),
                'CATEGORY': unmapped_df['CATEGORY'].tolist()
            })
            
            # Filter to focus on radiological codes as negatives, if available
            radiology_df = negative_df[negative_df['CATEGORY'] == 'Radiology']
            if len(radiology_df) >= 100:
                print(f"Using {len(radiology_df)} radiology codes as negative examples")
                negative_df = radiology_df
            
            # Limit negative samples if needed
            if limit_samples:
                negative_df = negative_df.sample(min(limit_samples, len(negative_df)), random_state=seed)
            
            print(f"Loaded {len(negative_df)} negative examples")
        except Exception as e:
            print(f"Error loading negative examples: {e}")
            negative_df = None
    
    return positive_df, negative_df, loinc_df

def prepare_evaluation_dataset(positive_df, negative_df, pos_samples=200, neg_samples=200, seed=42):
    """
    Create a balanced evaluation dataset with both positive and negative examples
    
    Args:
        positive_df: DataFrame with mappable examples
        negative_df: DataFrame with unmappable examples
        pos_samples: Number of positive samples to include
        neg_samples: Number of negative samples to include
        seed: Random seed for reproducibility
        
    Returns:
        eval_df: DataFrame with combined positive and negative examples
    """
    # Sample positive examples
    if len(positive_df) > pos_samples:
        pos_sample_df = positive_df.sample(pos_samples, random_state=seed)
    else:
        pos_sample_df = positive_df
    
    # Add mappable flag
    pos_sample_df = pos_sample_df.copy()
    pos_sample_df['is_mappable'] = True
    
    # Sample negative examples
    if len(negative_df) > neg_samples:
        neg_sample_df = negative_df.sample(neg_samples, random_state=seed)
    else:
        neg_sample_df = negative_df
    
    # Create negative examples dataframe
    neg_examples = pd.DataFrame({
        'SOURCE': neg_sample_df['SOURCE'].tolist(),
        'LOINC_NUM': ['UNMAPPABLE'] * len(neg_sample_df),
        'is_mappable': [False] * len(neg_sample_df)
    })
    
    # Combine positive and negative examples
    eval_df = pd.concat([pos_sample_df, neg_examples], ignore_index=True)
    
    print(f"Created evaluation dataset with {len(eval_df)} examples")
    print(f"- Positive examples: {len(pos_sample_df)}")
    print(f"- Negative examples: {len(neg_examples)}")
    
    return eval_df

def find_optimal_threshold(model, eval_df, loinc_df, output_dir=None, visualize=True):
    """
    Find the optimal similarity threshold for distinguishing mappable vs unmappable
    
    Args:
        model: Trained LOINC embedding model
        eval_df: DataFrame with evaluation data (both mappable and unmappable)
        loinc_df: DataFrame with LOINC targets
        output_dir: Directory to save output files and visualizations
        visualize: Whether to generate and save visualizations
        
    Returns:
        threshold: Optimal similarity threshold
        threshold_metrics: Dict with threshold performance metrics
    """
    # Extract source texts
    source_texts = eval_df['SOURCE'].tolist()
    
    # Extract unique LOINC targets
    unique_loincs = loinc_df['LOINC_NUM'].unique()
    
    # Get LOINC text representations
    target_texts = []
    target_codes = []
    
    print("Preparing target texts...")
    for loinc in tqdm(unique_loincs, desc="Processing LOINC targets"):
        matching_rows = loinc_df[loinc_df['LOINC_NUM'] == loinc]
        if len(matching_rows) > 0:
            target_texts.append(matching_rows.iloc[0]['LONG_COMMON_NAME'])
            target_codes.append(loinc)
    
    # Compute embeddings
    print("Computing source embeddings...")
    source_embeddings = compute_embeddings(source_texts, model)
    
    print("Computing target embeddings...")
    target_embeddings = compute_embeddings(target_texts, model)
    
    # Calculate similarities
    print("Calculating cosine similarities...")
    from sklearn.metrics import pairwise_distances
    similarities = -pairwise_distances(source_embeddings, target_embeddings, metric='cosine')
    
    # Find maximum similarity for each source
    max_similarities = np.max(similarities, axis=1)
    
    # True mappable labels
    true_mappable = eval_df['is_mappable'].values
    
    # Find optimal threshold
    precision, recall, thresholds = precision_recall_curve(true_mappable, max_similarities)
    
    # Calculate F1 scores for different thresholds
    f1_scores = []
    for i in range(len(precision) - 1):
        if precision[i] + recall[i] > 0:
            f1_score_val = 2 * (precision[i] * recall[i]) / (precision[i] + recall[i])
            f1_scores.append((thresholds[i], f1_score_val, precision[i], recall[i]))
    
    # Find threshold with highest F1 score
    f1_scores.sort(key=lambda x: x[1], reverse=True)
    optimal_threshold = f1_scores[0][0]
    best_f1 = f1_scores[0][1]
    best_precision = f1_scores[0][2]
    best_recall = f1_scores[0][3]
    
    print(f"Optimal threshold: {optimal_threshold:.4f} with F1 score: {best_f1:.4f}")
    print(f"Precision: {best_precision:.4f}, Recall: {best_recall:.4f}")
    
    # Apply threshold
    predicted_mappable = max_similarities >= optimal_threshold
    
    # Calculate metrics
    tn, fp, fn, tp = confusion_matrix(true_mappable, predicted_mappable).ravel()
    precision_val = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall_val = tp / (tp + fn) if (tp + fn) > 0 else 0
    
    # Calculate workload reduction (% of samples correctly identified as unmappable)
    workload_reduction = tn / len(eval_df) if len(eval_df) > 0 else 0
    
    # Print results
    print("\nThreshold Results:")
    print(f"- Threshold: {optimal_threshold:.4f}")
    print(f"- Precision: {precision_val:.4f}")
    print(f"- Recall: {recall_val:.4f}")
    print(f"- F1 Score: {best_f1:.4f}")
    print(f"- True Positives: {tp}")
    print(f"- True Negatives: {tn}")
    print(f"- False Positives: {fp}")
    print(f"- False Negatives: {fn}")
    print(f"- Workload Reduction: {workload_reduction*100:.2f}%")
    
    # Create metrics dictionary
    threshold_metrics = {
        'threshold': optimal_threshold,
        'precision': precision_val,
        'recall': recall_val,
        'f1_score': best_f1,
        'true_positives': tp,
        'true_negatives': tn,
        'false_positives': fp,
        'false_negatives': fn,
        'workload_reduction': workload_reduction
    }
    
    if output_dir:
        # Save results
        os.makedirs(output_dir, exist_ok=True)
        
        # Save threshold
        with open(os.path.join(output_dir, 'optimal_threshold.txt'), 'w') as f:
            f.write(f"{optimal_threshold}")
        
        # Save metrics
        metrics_df = pd.DataFrame([threshold_metrics])
        metrics_df.to_csv(os.path.join(output_dir, 'threshold_metrics.csv'), index=False)
        
        # Save similarity data
        similarity_df = pd.DataFrame({
            'source': source_texts,
            'is_mappable': true_mappable,
            'predicted_mappable': predicted_mappable,
            'max_similarity': max_similarities
        })
        similarity_df.to_csv(os.path.join(output_dir, 'similarity_data.csv'), index=False)
        
        # Save threshold vs F1 data
        threshold_df = pd.DataFrame({
            'threshold': [x[0] for x in f1_scores],
            'f1_score': [x[1] for x in f1_scores],
            'precision': [x[2] for x in f1_scores],
            'recall': [x[3] for x in f1_scores]
        })
        threshold_df.to_csv(os.path.join(output_dir, 'threshold_f1_scores.csv'), index=False)
        
        # Generate visualizations
        if visualize:
            # Plot similarity distributions
            plt.figure(figsize=(10, 6))
            plt.hist(max_similarities[true_mappable], bins=30, alpha=0.5, label='Mappable')
            plt.hist(max_similarities[~true_mappable], bins=30, alpha=0.5, label='Unmappable')
            plt.axvline(x=optimal_threshold, color='red', linestyle='--', label=f'Threshold={optimal_threshold:.4f}')
            plt.xlabel('Maximum Cosine Similarity')
            plt.ylabel('Frequency')
            plt.title('Distribution of Maximum Similarities')
            plt.legend()
            plt.savefig(os.path.join(output_dir, 'similarity_distribution.png'))
            plt.close()
            
            # Plot precision-recall curve
            plt.figure(figsize=(10, 6))
            plt.plot(recall, precision, marker='.', label='Precision-Recall curve')
            plt.xlabel('Recall')
            plt.ylabel('Precision')
            plt.axvline(x=best_recall, color='red', linestyle='--', 
                       label=f'Optimal (P={best_precision:.2f}, R={best_recall:.2f}, F1={best_f1:.2f})')
            plt.title('Precision-Recall Curve')
            plt.legend()
            plt.savefig(os.path.join(output_dir, 'precision_recall_curve.png'))
            plt.close()
            
            # Plot threshold vs F1 score
            plt.figure(figsize=(10, 6))
            plt.plot([x[0] for x in f1_scores], [x[1] for x in f1_scores], label='F1 Score')
            plt.axvline(x=optimal_threshold, color='red', linestyle='--', 
                       label=f'Optimal Threshold={optimal_threshold:.4f}')
            plt.xlabel('Threshold')
            plt.ylabel('F1 Score')
            plt.title('Threshold vs F1 Score')
            plt.legend()
            plt.savefig(os.path.join(output_dir, 'threshold_f1_curve.png'))
            plt.close()
    
    return optimal_threshold, threshold_metrics

def generate_hard_negatives(model, positive_df, negative_df, loinc_df, n_hard_negatives=200, 
                           similarity_threshold=0.7, output_dir=None):
    """
    Generate hard negative examples for training
    
    Args:
        model: Trained LOINC embedding model
        positive_df: DataFrame with mappable examples
        negative_df: DataFrame with unmappable examples
        loinc_df: DataFrame with LOINC targets
        n_hard_negatives: Number of hard negative examples to generate
        similarity_threshold: Similarity threshold for selecting hard negatives
        output_dir: Directory to save output files
        
    Returns:
        hard_negatives_df: DataFrame with hard negative examples
    """
    # Extract candidate negative source texts
    negative_texts = negative_df['SOURCE'].tolist()
    
    # Get representative LOINC target texts
    unique_loincs = loinc_df['LOINC_NUM'].unique()
    target_texts = []
    target_codes = []
    
    print("Preparing target texts...")
    for loinc in tqdm(unique_loincs, desc="Processing LOINC targets"):
        matching_rows = loinc_df[loinc_df['LOINC_NUM'] == loinc]
        if len(matching_rows) > 0:
            target_texts.append(matching_rows.iloc[0]['LONG_COMMON_NAME'])
            target_codes.append(loinc)
    
    # Compute embeddings
    print("Computing source embeddings for negative examples...")
    negative_embeddings = compute_embeddings(negative_texts, model)
    
    print("Computing target embeddings...")
    target_embeddings = compute_embeddings(target_texts, model)
    
    # Calculate similarities
    print("Calculating similarities for negative examples...")
    from sklearn.metrics import pairwise_distances
    similarities = -pairwise_distances(negative_embeddings, target_embeddings, metric='cosine')
    
    # Find maximum similarity for each negative source
    max_similarities = np.max(similarities, axis=1)
    max_indices = np.argmax(similarities, axis=1)
    
    # Select hard negatives (high similarity but known to be unmappable)
    hard_negative_indices = np.argsort(max_similarities)[::-1][:min(n_hard_negatives, len(negative_texts))]
    
    hard_negatives = []
    for idx in hard_negative_indices:
        if max_similarities[idx] >= similarity_threshold:
            hard_negatives.append({
                'SOURCE': negative_texts[idx],
                'SIMILARITY': max_similarities[idx],
                'CLOSEST_LOINC': target_codes[max_indices[idx]],
                'CLOSEST_TEXT': target_texts[max_indices[idx]]
            })
    
    print(f"Generated {len(hard_negatives)} hard negative examples")
    
    # Create hard negatives DataFrame
    hard_negatives_df = pd.DataFrame(hard_negatives)
    
    if output_dir:
        # Save hard negatives
        os.makedirs(output_dir, exist_ok=True)
        hard_negatives_df.to_csv(os.path.join(output_dir, 'hard_negatives.csv'), index=False)
    
    return hard_negatives_df

def inference_with_threshold(model, source_texts, target_df, threshold, top_k=5):
    """
    Perform inference with threshold-based "unmappable" detection
    
    Args:
        model: Trained LOINC embedding model
        source_texts: List of source texts to map
        target_df: DataFrame with LOINC targets
        threshold: Similarity threshold for mappable/unmappable decision
        top_k: Number of top matches to return
        
    Returns:
        results: List of dictionaries with mapping results
    """
    # Get unique LOINC targets
    unique_loincs = target_df['LOINC_NUM'].unique()
    
    # Get LOINC text representations
    target_texts = []
    target_codes = []
    
    print("Preparing target texts...")
    for loinc in tqdm(unique_loincs, desc="Processing LOINC targets"):
        matching_rows = target_df[target_df['LOINC_NUM'] == loinc]
        if len(matching_rows) > 0:
            target_texts.append(matching_rows.iloc[0]['LONG_COMMON_NAME'])
            target_codes.append(loinc)
    
    # Compute embeddings
    print("Computing source embeddings...")
    source_embeddings = compute_embeddings(source_texts, model)
    
    print("Computing target embeddings...")
    target_embeddings = compute_embeddings(target_texts, model)
    
    # Calculate similarities
    print("Calculating similarities...")
    from sklearn.metrics import pairwise_distances
    similarities = -pairwise_distances(source_embeddings, target_embeddings, metric='cosine')
    
    # Get top-k matches for each source
    results = []
    
    for i, source_text in enumerate(source_texts):
        # Get similarity scores for this source
        source_similarities = similarities[i]
        
        # Get maximum similarity
        max_similarity = np.max(source_similarities)
        
        # Create result dictionary
        result = {
            'SOURCE': source_text,
            'MAX_SIMILARITY': max_similarity,
            'MAPPABLE': max_similarity >= threshold,
        }
        
        # If mappable, add top-k matches
        if max_similarity >= threshold:
            top_indices = np.argsort(source_similarities)[::-1][:top_k]
            
            for rank, idx in enumerate(top_indices):
                result[f'LOINC_{rank+1}'] = target_codes[idx]
                result[f'TEXT_{rank+1}'] = target_texts[idx]
                result[f'SCORE_{rank+1}'] = source_similarities[idx]
        else:
            # If unmappable, set to UNMAPPABLE
            result['LOINC_1'] = 'UNMAPPABLE'
            result['TEXT_1'] = 'No suitable LOINC match found'
            result['SCORE_1'] = max_similarity
        
        results.append(result)
    
    return results

def main():
    parser = argparse.ArgumentParser(description='No-match handler with thresholding and negative mining')
    parser.add_argument('--mimic_file', type=str, default='mimic_pairs_processed.csv',
                       help='Path to MIMIC mapped pairs CSV')
    parser.add_argument('--loinc_file', type=str, default='loinc_targets_processed.csv',
                       help='Path to LOINC targets CSV')
    parser.add_argument('--d_labitems_file', type=str, default='D_LABITEMS.csv',
                       help='Path to D_LABITEMS.csv for non-mappable codes')
    parser.add_argument('--checkpoint_dir', type=str, default='models/checkpoints',
                       help='Directory containing model checkpoints')
    parser.add_argument('--fold', type=int, default=0,
                       help='Fold to use (0-based)')
    parser.add_argument('--output_dir', type=str, default='results/no_match_handler',
                       help='Directory to save results')
    parser.add_argument('--mode', type=str, choices=['tune', 'generate', 'evaluate'], default='tune',
                       help='Mode: tune threshold, generate hard negatives, or evaluate with threshold')
    parser.add_argument('--threshold', type=float, default=None,
                       help='Similarity threshold (if not provided, optimal will be found)')
    parser.add_argument('--pos_samples', type=int, default=200,
                       help='Number of positive samples for threshold tuning')
    parser.add_argument('--neg_samples', type=int, default=200,
                       help='Number of negative samples for threshold tuning')
    parser.add_argument('--hard_negatives', type=int, default=200,
                       help='Number of hard negative examples to generate')
    parser.add_argument('--limit_samples', type=int, default=None,
                       help='Limit number of samples for testing')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed for reproducibility')
    parser.add_argument('--visualize', action='store_true',
                       help='Generate visualizations')
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load data
    positive_df, negative_df, loinc_df = load_data(
        args.mimic_file, args.loinc_file, args.d_labitems_file, args.limit_samples, args.seed
    )
    
    # Check if we have negative examples
    if negative_df is None or len(negative_df) == 0:
        print("Error: No negative examples found. Cannot proceed with no-match handling.")
        sys.exit(1)
    
    # Load model
    print(f"Loading model for fold {args.fold}...")
    model = load_model(args.checkpoint_dir, args.fold)
    
    # Process based on mode
    if args.mode == 'tune':
        # Create evaluation dataset
        eval_df = prepare_evaluation_dataset(
            positive_df, negative_df, args.pos_samples, args.neg_samples, args.seed
        )
        
        # Find optimal threshold
        threshold, metrics = find_optimal_threshold(
            model, eval_df, loinc_df, args.output_dir, args.visualize
        )
        
        print(f"Optimal threshold: {threshold:.4f}")
        print(f"Workload reduction: {metrics['workload_reduction']*100:.2f}%")
        
    elif args.mode == 'generate':
        # Generate hard negative examples
        similarity_threshold = args.threshold if args.threshold is not None else 0.7
        hard_negatives_df = generate_hard_negatives(
            model, positive_df, negative_df, loinc_df, 
            args.hard_negatives, similarity_threshold, args.output_dir
        )
        
        print(f"Generated {len(hard_negatives_df)} hard negative examples")
        
    elif args.mode == 'evaluate':
        # Check if threshold is provided
        if args.threshold is None:
            # Try to load threshold from file
            threshold_file = os.path.join(args.output_dir, 'optimal_threshold.txt')
            if os.path.exists(threshold_file):
                with open(threshold_file, 'r') as f:
                    threshold = float(f.read().strip())
                print(f"Loaded threshold {threshold:.4f} from {threshold_file}")
            else:
                print("No threshold provided and no optimal_threshold.txt found. Using default 0.5")
                threshold = 0.5
        else:
            threshold = args.threshold
        
        # Create test examples
        test_size = min(args.limit_samples if args.limit_samples else 100, len(positive_df))
        test_examples = positive_df.sample(test_size, random_state=args.seed)
        test_texts = test_examples['SOURCE'].tolist()
        
        # Add some negative examples
        neg_size = min(test_size // 2, len(negative_df))
        neg_examples = negative_df.sample(neg_size, random_state=args.seed)
        neg_texts = neg_examples['SOURCE'].tolist()
        
        # Combine test texts
        all_test_texts = test_texts + neg_texts
        
        # Run inference with threshold
        results = inference_with_threshold(model, all_test_texts, loinc_df, threshold)
        
        # Save results
        results_df = pd.DataFrame(results)
        results_df.to_csv(os.path.join(args.output_dir, 'threshold_inference_results.csv'), index=False)
        
        # Print summary
        mappable_count = sum(1 for r in results if r['MAPPABLE'])
        unmappable_count = len(results) - mappable_count
        
        print(f"Inference results:")
        print(f"- Total examples: {len(results)}")
        print(f"- Mappable: {mappable_count} ({mappable_count/len(results)*100:.2f}%)")
        print(f"- Unmappable: {unmappable_count} ({unmappable_count/len(results)*100:.2f}%)")
        
        # Calculate expected unmappable rate
        expected_unmappable = len(neg_texts)
        print(f"- Expected unmappable: {expected_unmappable} ({expected_unmappable/len(all_test_texts)*100:.2f}%)")

if __name__ == "__main__":
    main() 