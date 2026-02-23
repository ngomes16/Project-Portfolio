import tensorflow as tf
import numpy as np
import pandas as pd
import os
import argparse
import sys
import time
from sklearn.metrics import pairwise_distances, precision_recall_curve, f1_score, roc_curve, auc
import matplotlib.pyplot as plt
from tqdm import tqdm

# Add parent directory to path to import from other modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.evaluation import load_test_data, load_target_loincs, load_model, compute_embeddings

def evaluate_with_threshold(test_df, target_df, model, threshold=None, k_values=[1, 3, 5], batch_size=16, 
                           output_dir="results", include_non_mappable=True, non_mappable_df=None):
    """
    Evaluate model with similarity threshold to detect non-mappable codes
    
    Args:
        test_df: DataFrame with test data
        target_df: DataFrame with LOINC targets
        model: Trained model
        threshold: Cosine similarity threshold (if None, calculate optimal threshold)
        k_values: List of k values for Top-k accuracy
        batch_size: Batch size for inference
        output_dir: Directory to save results
        include_non_mappable: Whether to include non-mappable samples in evaluation
        non_mappable_df: DataFrame with non-mappable samples
        
    Returns:
        results: Dictionary with evaluation results
    """
    # Get unique target LOINCs
    unique_target_loincs = target_df['LOINC_NUM'].unique()
    
    # Add non-mappable samples if requested
    if include_non_mappable and non_mappable_df is not None and len(non_mappable_df) > 0:
        # Create non-mappable test samples
        non_mappable_samples = pd.DataFrame({
            'SOURCE': non_mappable_df['LABEL'].tolist(),
            'LOINC_NUM': ['UNMAPPABLE'] * len(non_mappable_df),
            'is_mappable': [False] * len(non_mappable_df)
        })
        
        # Add is_mappable column to test_df
        test_df = test_df.copy()
        test_df['is_mappable'] = True
        
        # Combine datasets
        combined_test_df = pd.concat([test_df, non_mappable_samples], ignore_index=True)
        print(f"Combined {len(test_df)} mappable and {len(non_mappable_samples)} non-mappable samples")
    else:
        combined_test_df = test_df.copy()
        # All samples are mappable if not including non-mappable
        combined_test_df['is_mappable'] = True
        print(f"Using {len(combined_test_df)} mappable samples")
    
    # Get source texts
    source_texts = combined_test_df['SOURCE'].tolist()
    
    # Get target LOINCs
    target_loincs = combined_test_df['LOINC_NUM'].tolist()
    is_mappable = combined_test_df['is_mappable'].tolist()
    
    # Compute embeddings for target LOINCs
    print("Computing embeddings for target LOINCs...")
    target_texts = []
    target_codes = []
    
    for loinc in tqdm(unique_target_loincs):
        # Use first matching text if multiple exist for the same LOINC code
        matching_rows = target_df[target_df['LOINC_NUM'] == loinc]
        if len(matching_rows) > 0:
            target_text = matching_rows.iloc[0]['TARGET']
            target_texts.append(target_text)
            target_codes.append(loinc)
    
    target_embeddings = compute_embeddings(target_texts, model, batch_size)
    
    # Compute embeddings for source texts
    print("Computing embeddings for source texts...")
    source_embeddings = compute_embeddings(source_texts, model, batch_size)
    
    # Calculate pairwise similarities
    print("Calculating similarities...")
    # Using negative cosine distance (higher is better)
    similarities = -pairwise_distances(source_embeddings, target_embeddings, metric='cosine')
    
    # Create dictionary mapping LOINC codes to their indices in the target embeddings
    loinc_to_index = {loinc: i for i, loinc in enumerate(target_codes)}
    
    # Get maximum similarity for each source
    max_similarities = np.max(similarities, axis=1)
    
    # If threshold is not provided, calculate optimal threshold
    if threshold is None and include_non_mappable:
        # Calculate precision, recall, and thresholds
        precision, recall, thresholds = precision_recall_curve(is_mappable, max_similarities)
        
        # Calculate F1 score at each threshold
        f1_scores = []
        for i in range(len(precision) - 1):
            if precision[i] + recall[i] > 0:
                f1 = 2 * (precision[i] * recall[i]) / (precision[i] + recall[i])
                f1_scores.append((thresholds[i], f1))
        
        # Find threshold with highest F1 score
        f1_scores.sort(key=lambda x: x[1], reverse=True)
        threshold = f1_scores[0][0]
        
        print(f"Calculated optimal threshold: {threshold:.4f} (F1: {f1_scores[0][1]:.4f})")
        
        # Plot precision-recall curve
        plt.figure(figsize=(10, 6))
        plt.plot(recall, precision, marker='.', label=f'Precision-Recall (AUC = {auc(recall, precision):.4f})')
        plt.xlabel('Recall')
        plt.ylabel('Precision')
        plt.title('Precision-Recall Curve for Mappable Detection')
        plt.grid(True)
        plt.legend()
        plt.savefig(os.path.join(output_dir, 'precision_recall_curve.png'))
        print(f"Saved precision-recall curve to {os.path.join(output_dir, 'precision_recall_curve.png')}")
        
        # Plot ROC curve
        fpr, tpr, _ = roc_curve(is_mappable, max_similarities)
        roc_auc = auc(fpr, tpr)
        
        plt.figure(figsize=(10, 6))
        plt.plot(fpr, tpr, marker='.', label=f'ROC (AUC = {roc_auc:.4f})')
        plt.plot([0, 1], [0, 1], 'k--')
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('ROC Curve for Mappable Detection')
        plt.grid(True)
        plt.legend()
        plt.savefig(os.path.join(output_dir, 'roc_curve.png'))
        print(f"Saved ROC curve to {os.path.join(output_dir, 'roc_curve.png')}")
    elif threshold is None:
        # If not including non-mappable, use a default threshold
        threshold = 0.8
        print(f"Using default threshold: {threshold:.4f}")
    else:
        print(f"Using provided threshold: {threshold:.4f}")
    
    # Apply threshold to determine mappable/non-mappable
    predicted_mappable = max_similarities >= threshold
    
    # Calculate accuracy metrics
    results = {}
    
    # Mappable classification metrics
    if include_non_mappable:
        tp = np.sum((np.array(is_mappable)) & (predicted_mappable))
        tn = np.sum((~np.array(is_mappable)) & (~predicted_mappable))
        fp = np.sum((~np.array(is_mappable)) & (predicted_mappable))
        fn = np.sum((np.array(is_mappable)) & (~predicted_mappable))
        
        precision_val = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall_val = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_val = 2 * (precision_val * recall_val) / (precision_val + recall_val) if (precision_val + recall_val) > 0 else 0
        
        results['mappable_precision'] = precision_val
        results['mappable_recall'] = recall_val
        results['mappable_f1'] = f1_val
        
        print(f"Mappable Classification:")
        print(f"- Precision: {precision_val:.4f}")
        print(f"- Recall: {recall_val:.4f}")
        print(f"- F1 Score: {f1_val:.4f}")
        
        print("\nConfusion Matrix:")
        print(f"True Mappable, Predicted Mappable: {tp}")
        print(f"True Mappable, Predicted Non-mappable: {fn}")
        print(f"True Non-mappable, Predicted Mappable: {fp}")
        print(f"True Non-mappable, Predicted Non-mappable: {tn}")
    
    # Calculate Top-k accuracy (only for mappable samples that are predicted as mappable)
    for k in k_values:
        # Get top k indices for each source
        top_k_indices = np.argsort(similarities, axis=1)[:, -k:]
        
        # Check if correct target is in top k
        correct = 0
        total_evaluated = 0
        
        for i, (target_loinc, is_map, pred_map) in enumerate(zip(target_loincs, is_mappable, predicted_mappable)):
            # Only evaluate mappable samples
            if is_map:
                total_evaluated += 1
                
                # For samples predicted as mappable, check if prediction is correct
                if pred_map:
                    # Get the target LOINC's index
                    if target_loinc in loinc_to_index:
                        target_idx = loinc_to_index[target_loinc]
                        # Check if target index is in top k
                        if target_idx in top_k_indices[i]:
                            correct += 1
                    else:
                        print(f"WARNING: Target LOINC {target_loinc} not in target pool")
        
        # Calculate accuracy
        accuracy = correct / total_evaluated if total_evaluated > 0 else 0
        results[f'top{k}_accuracy'] = accuracy
        print(f"Top-{k} accuracy (mappable samples predicted as mappable): {accuracy:.4f} ({correct}/{total_evaluated})")
    
    # Calculate Mean Reciprocal Rank (MRR) for mappable samples
    reciprocal_ranks = []
    for i, (target_loinc, is_map, pred_map) in enumerate(zip(target_loincs, is_mappable, predicted_mappable)):
        if is_map and pred_map and target_loinc in loinc_to_index:
            target_idx = loinc_to_index[target_loinc]
            # Get rank of correct target (add 1 because indices are 0-based)
            rank = np.where(np.argsort(similarities[i])[::-1] == target_idx)[0][0] + 1
            reciprocal_ranks.append(1.0 / rank)
    
    if reciprocal_ranks:
        mrr = np.mean(reciprocal_ranks)
        results['mrr'] = mrr
        print(f"Mean Reciprocal Rank (mappable samples predicted as mappable): {mrr:.4f}")
    
    # Add additional metrics to results
    results['threshold'] = threshold
    results['target_pool_size'] = len(unique_target_loincs)
    results['test_samples'] = len(source_texts)
    results['mappable_samples'] = sum(is_mappable)
    results['non_mappable_samples'] = len(is_mappable) - sum(is_mappable)
    results['predicted_mappable'] = sum(predicted_mappable)
    results['predicted_non_mappable'] = len(predicted_mappable) - sum(predicted_mappable)
    
    # Sample 10 high confidence incorrect predictions for analysis
    if include_non_mappable:
        incorrect_indices = np.where((np.array(is_mappable) != predicted_mappable) & 
                                  (np.abs(max_similarities - threshold) > 0.1))[0]
        
        if len(incorrect_indices) > 0:
            print("\nHigh-confidence incorrect predictions:")
            
            # Sample at most 10 incorrect predictions
            sample_size = min(10, len(incorrect_indices))
            sampled_indices = np.random.choice(incorrect_indices, sample_size, replace=False)
            
            incorrect_samples = []
            for idx in sampled_indices:
                source_text = source_texts[idx]
                true_mappable = is_mappable[idx]
                pred_mappable = predicted_mappable[idx]
                similarity = max_similarities[idx]
                
                incorrect_sample = {
                    'source_text': source_text,
                    'true_mappable': true_mappable,
                    'pred_mappable': pred_mappable,
                    'similarity': similarity
                }
                
                if true_mappable:
                    incorrect_sample['true_loinc'] = target_loincs[idx]
                    
                    # Get top prediction
                    top_idx = np.argmax(similarities[idx])
                    top_loinc = target_codes[top_idx]
                    top_similarity = -similarities[idx][top_idx]
                    
                    incorrect_sample['top_prediction'] = top_loinc
                    incorrect_sample['top_similarity'] = top_similarity
                
                incorrect_samples.append(incorrect_sample)
                
                # Print sample details
                print(f"Source: {source_text}")
                print(f"True: {'Mappable' if true_mappable else 'Non-mappable'}, "
                     f"Predicted: {'Mappable' if pred_mappable else 'Non-mappable'}")
                print(f"Similarity: {similarity:.4f}")
                
                if true_mappable:
                    print(f"True LOINC: {target_loincs[idx]}")
                    print(f"Top Prediction: {top_loinc} (similarity: {-similarities[idx][top_idx]:.4f})")
                
                print("-" * 80)
            
            # Save incorrect samples to file
            incorrect_df = pd.DataFrame(incorrect_samples)
            incorrect_df.to_csv(os.path.join(output_dir, 'incorrect_predictions.csv'), index=False)
            print(f"Saved {len(incorrect_df)} incorrect predictions to {os.path.join(output_dir, 'incorrect_predictions.csv')}")
    
    # Calculate estimated SME workload reduction
    if include_non_mappable:
        total_samples = len(source_texts)
        total_mappable = sum(is_mappable)
        total_non_mappable = total_samples - total_mappable
        
        # True positives: correctly identified as mappable
        true_positives = np.sum((np.array(is_mappable)) & (predicted_mappable))
        
        # True negatives: correctly identified as non-mappable
        true_negatives = np.sum((~np.array(is_mappable)) & (~predicted_mappable))
        
        # Calculate workload reduction
        baseline_workload = total_samples  # SMEs review all samples
        thresholded_workload = total_samples - true_negatives  # SMEs don't need to review true negatives
        
        workload_reduction = (baseline_workload - thresholded_workload) / baseline_workload
        
        results['sme_workload_reduction'] = workload_reduction
        results['sme_hours_saved_per_1000'] = workload_reduction * 1000 * 0.05  # Assuming 3 minutes per review
        
        print(f"\nSME Workload Reduction:")
        print(f"- Baseline (review all): {baseline_workload} samples")
        print(f"- With threshold: {thresholded_workload} samples")
        print(f"- Reduction: {workload_reduction:.4f} ({workload_reduction*100:.1f}%)")
        print(f"- Estimated hours saved per 1,000 lab codes: {results['sme_hours_saved_per_1000']:.1f} hours")
    
    # Save all prediction details to file
    prediction_details = []
    for i, (source, target, is_map, pred_map, sim) in enumerate(zip(
        source_texts, target_loincs, is_mappable, predicted_mappable, max_similarities)):
        
        detail = {
            'source': source,
            'true_loinc': target,
            'is_mappable': is_map,
            'predicted_mappable': pred_map,
            'max_similarity': sim
        }
        
        # Add top 5 predictions
        top5_indices = np.argsort(similarities[i])[::-1][:5]
        for j, idx in enumerate(top5_indices):
            detail[f'pred{j+1}_loinc'] = target_codes[idx]
            detail[f'pred{j+1}_similarity'] = -similarities[i][idx]
        
        prediction_details.append(detail)
    
    # Save prediction details
    details_df = pd.DataFrame(prediction_details)
    details_df.to_csv(os.path.join(output_dir, 'prediction_details.csv'), index=False)
    print(f"Saved prediction details to {os.path.join(output_dir, 'prediction_details.csv')}")
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Evaluate LOINC standardization model with similarity thresholding')
    parser.add_argument('--test_file', type=str, required=True, 
                        help='Path to test data CSV')
    parser.add_argument('--loinc_file', type=str, required=True, 
                        help='Path to LOINC data CSV')
    parser.add_argument('--d_labitems_file', type=str, default='D_LABITEMS.csv', 
                        help='Path to D_LABITEMS.csv for non-mappable codes')
    parser.add_argument('--checkpoint_dir', type=str, default='models/checkpoints', 
                        help='Directory containing model checkpoints')
    parser.add_argument('--fold', type=int, default=0, 
                        help='Fold to evaluate (0-indexed)')
    parser.add_argument('--output_dir', type=str, default='results/thresholded', 
                        help='Directory to save evaluation results')
    parser.add_argument('--batch_size', type=int, default=16, 
                        help='Batch size for inference')
    parser.add_argument('--threshold', type=float, default=None, 
                        help='Similarity threshold (if not provided, calculate optimal)')
    parser.add_argument('--skip_non_mappable', action='store_true', 
                        help='Skip non-mappable samples in evaluation')
    parser.add_argument('--max_samples', type=int, default=None,
                        help='Maximum number of samples to evaluate (for debugging)')
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load data
    print(f"Loading test data from {args.test_file}...")
    test_df = load_test_data(args.test_file)
    
    print(f"Loading LOINC targets from {args.loinc_file}...")
    target_df = load_target_loincs(args.loinc_file)
    
    # Load non-mappable codes
    non_mappable_df = None
    if not args.skip_non_mappable:
        print(f"Loading non-mappable codes from {args.d_labitems_file}...")
        try:
            labitems_df = pd.read_csv(args.d_labitems_file)
            non_mappable_df = labitems_df[labitems_df['LOINC_CODE'].isna()]
            print(f"Loaded {len(non_mappable_df)} non-mappable codes")
            
            # Limit samples if specified
            if args.max_samples is not None:
                max_non_mappable = min(args.max_samples // 2, len(non_mappable_df))
                non_mappable_df = non_mappable_df.sample(max_non_mappable, random_state=42)
                print(f"Using {len(non_mappable_df)} non-mappable samples")
        except Exception as e:
            print(f"Error loading non-mappable codes: {e}")
    
    # Limit test samples if specified
    if args.max_samples is not None:
        test_df = test_df.sample(min(args.max_samples, len(test_df)), random_state=42)
        print(f"Using {len(test_df)} test samples")
    
    # Load model
    print(f"Loading model for fold {args.fold}...")
    model = load_model(args.checkpoint_dir, args.fold)
    
    # Run evaluation with threshold
    print("Evaluating with similarity threshold...")
    start_time = time.time()
    results = evaluate_with_threshold(
        test_df=test_df,
        target_df=target_df,
        model=model,
        threshold=args.threshold,
        batch_size=args.batch_size,
        output_dir=args.output_dir,
        include_non_mappable=not args.skip_non_mappable,
        non_mappable_df=non_mappable_df
    )
    
    # Save results
    results_df = pd.DataFrame([results])
    results_df.to_csv(os.path.join(args.output_dir, 'threshold_results.csv'), index=False)
    print(f"Saved results to {os.path.join(args.output_dir, 'threshold_results.csv')}")
    
    # Print summary
    print("\n" + "="*80)
    print("EVALUATION SUMMARY")
    print("="*80)
    
    print(f"Threshold: {results['threshold']:.4f}")
    
    if not args.skip_non_mappable:
        print(f"Mappable Classification:")
        print(f"- Precision: {results['mappable_precision']:.4f}")
        print(f"- Recall: {results['mappable_recall']:.4f}")
        print(f"- F1 Score: {results['mappable_f1']:.4f}")
        print(f"- SME Workload Reduction: {results['sme_workload_reduction']*100:.1f}%")
        print(f"- Hours saved per 1,000 lab codes: {results['sme_hours_saved_per_1000']:.1f}")
    
    print(f"Top-k Accuracy:")
    for k in [1, 3, 5]:
        if f'top{k}_accuracy' in results:
            print(f"- Top-{k}: {results[f'top{k}_accuracy']:.4f}")
    
    if 'mrr' in results:
        print(f"Mean Reciprocal Rank: {results['mrr']:.4f}")
    
    print(f"Evaluation completed in {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    main() 