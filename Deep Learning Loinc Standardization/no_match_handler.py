import pandas as pd
import numpy as np
import os
import argparse
import time
from tqdm import tqdm
from sklearn.metrics import precision_recall_curve, f1_score, roc_curve, auc, confusion_matrix
import matplotlib.pyplot as plt
import tensorflow as tf
import sys

# Add parent directory to path to import from other modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def load_data(mimic_file, loinc_file, d_labitems_file=None, limit_samples=None):
    """
    Load the data needed for the "no-match" handler training and evaluation
    
    Args:
        mimic_file: Path to MIMIC mapped pairs CSV
        loinc_file: Path to LOINC targets CSV
        d_labitems_file: Path to D_LABITEMS.csv for non-mappable codes
        limit_samples: Limit the number of samples for testing
        
    Returns:
        positive_df: DataFrame with mappable pairs
        negative_df: DataFrame with unmappable codes
        loinc_df: DataFrame with LOINC targets
    """
    print(f"Loading positive mappable examples from {mimic_file}...")
    positive_df = pd.read_csv(mimic_file)
    
    if limit_samples:
        positive_df = positive_df.sample(min(limit_samples, len(positive_df)), random_state=42)
    
    print(f"Loaded {len(positive_df)} positive examples")
    
    print(f"Loading LOINC targets from {loinc_file}...")
    loinc_df = pd.read_csv(loinc_file)
    print(f"Loaded {len(loinc_df)} LOINC targets")
    
    negative_df = None
    if d_labitems_file:
        print(f"Loading non-mappable codes from {d_labitems_file}...")
        try:
            # Load D_LABITEMS.csv
            labitems_df = pd.read_csv(d_labitems_file)
            
            # Extract non-mappable codes (where LOINC_CODE is empty/NaN)
            negative_df = labitems_df[labitems_df['LOINC_CODE'].isna()]
            
            # For testing with radiology codes, we can filter by category
            radiology_df = labitems_df[labitems_df['CATEGORY'] == 'Radiology']
            
            # If there are at least 100 radiology codes, use those preferentially
            if len(radiology_df) >= 100:
                print(f"Using {len(radiology_df)} radiology codes as negative examples")
                negative_df = radiology_df
            
            # Limit negative samples if needed
            if limit_samples and negative_df is not None:
                negative_df = negative_df.sample(min(limit_samples, len(negative_df)), random_state=42)
            
            if negative_df is not None:
                print(f"Loaded {len(negative_df)} negative (unmappable) examples")
            
        except Exception as e:
            print(f"Error loading non-mappable codes: {e}")
    
    return positive_df, negative_df, loinc_df

def create_evaluation_dataset(positive_df, negative_df=None, n_positives=200, n_negatives=200):
    """
    Create a balanced evaluation dataset with positives and negatives
    
    Args:
        positive_df: DataFrame with mappable pairs
        negative_df: DataFrame with unmappable codes
        n_positives: Number of positive examples to include
        n_negatives: Number of negative examples to include
        
    Returns:
        eval_df: DataFrame with evaluation data
    """
    # Sample positive examples
    if len(positive_df) > n_positives:
        sampled_positives = positive_df.sample(n_positives, random_state=42)
    else:
        sampled_positives = positive_df
    
    sampled_positives = sampled_positives.copy()
    sampled_positives['is_mappable'] = True
    
    # Handle negatives if available
    if negative_df is not None and len(negative_df) > 0:
        if len(negative_df) > n_negatives:
            sampled_negatives = negative_df.sample(n_negatives, random_state=42)
        else:
            sampled_negatives = negative_df
        
        # Create negative examples dataframe
        sampled_negatives = pd.DataFrame({
            'SOURCE': sampled_negatives['LABEL'].tolist(),
            'FLUID': sampled_negatives['FLUID'].tolist(),
            'LOINC_NUM': ['UNMAPPABLE'] * len(sampled_negatives),
            'is_mappable': [False] * len(sampled_negatives)
        })
        
        # Combine positive and negative examples
        eval_df = pd.concat([sampled_positives, sampled_negatives], ignore_index=True)
    else:
        eval_df = sampled_positives
    
    print(f"Created evaluation dataset with {len(eval_df)} examples")
    print(f"- Positives: {sum(eval_df['is_mappable'])}")
    print(f"- Negatives: {len(eval_df) - sum(eval_df['is_mappable'])}")
    
    return eval_df

def compute_embeddings(texts, model, batch_size=16):
    """
    Compute embeddings for a list of text strings
    
    Args:
        texts: List of text strings
        model: Trained model
        batch_size: Batch size for inference
        
    Returns:
        embeddings: Numpy array of embeddings
    """
    # Handle case where texts is empty
    if not texts:
        return np.array([])
    
    embeddings = []
    for i in tqdm(range(0, len(texts), batch_size), desc="Computing embeddings", 
                 total=(len(texts) + batch_size - 1) // batch_size):
        batch_texts = texts[i:i+batch_size]
        # Ensure all texts are strings
        batch_texts = [str(text) if not isinstance(text, str) else text for text in batch_texts]
        # Calculate embeddings for batch
        batch_embeddings = model(inputs=batch_texts, training=False).numpy()
        embeddings.append(batch_embeddings)
    
    return np.vstack(embeddings)

def find_optimal_threshold(model, eval_df, target_df, output_dir):
    """
    Find the optimal similarity threshold for distinguishing mappable vs non-mappable
    
    Args:
        model: Trained model
        eval_df: DataFrame with evaluation data
        target_df: DataFrame with LOINC targets
        output_dir: Directory to save outputs
        
    Returns:
        optimal_threshold: Optimal similarity threshold
    """
    # Check if we have both mappable and non-mappable examples
    if 'is_mappable' not in eval_df.columns or eval_df['is_mappable'].nunique() < 2:
        print("Need both mappable and non-mappable examples to find optimal threshold")
        return 0.5
    
    # Get source texts
    source_texts = eval_df['SOURCE'].tolist()
    
    # Get unique target LOINCs
    unique_loincs = target_df['LOINC_NUM'].unique()
    
    # Get target texts
    target_texts = []
    for loinc in tqdm(unique_loincs, desc="Preparing target texts"):
        matching_rows = target_df[target_df['LOINC_NUM'] == loinc]
        if len(matching_rows) > 0:
            target_text = matching_rows.iloc[0]['LONG_COMMON_NAME']
            target_texts.append(target_text)
    
    # Compute embeddings
    print("Computing embeddings for source texts...")
    source_embeddings = compute_embeddings(source_texts, model)
    
    print("Computing embeddings for target texts...")
    target_embeddings = compute_embeddings(target_texts, model)
    
    # Compute similarity scores
    print("Computing similarity scores...")
    
    # Using negative of pairwise cosine distance (higher is better)
    from sklearn.metrics import pairwise_distances
    similarities = -pairwise_distances(source_embeddings, target_embeddings, metric='cosine')
    
    # Get maximum similarity for each source
    max_similarities = np.max(similarities, axis=1)
    
    # Get true labels
    true_mappable = eval_df['is_mappable'].values
    
    # Calculate precision, recall, and thresholds
    precision, recall, thresholds = precision_recall_curve(true_mappable, max_similarities)
    
    # Calculate F1 score for each threshold
    f1_scores = []
    for i in range(len(precision) - 1):  # -1 because last element of precision has no threshold
        if precision[i] + recall[i] > 0:
            f1 = 2 * (precision[i] * recall[i]) / (precision[i] + recall[i])
            f1_scores.append((thresholds[i], f1))
    
    # Find threshold with highest F1 score
    f1_scores.sort(key=lambda x: x[1], reverse=True)
    optimal_threshold = f1_scores[0][0]
    best_f1 = f1_scores[0][1]
    
    print(f"Optimal threshold: {optimal_threshold:.4f} with F1 score: {best_f1:.4f}")
    
    # Save threshold and F1 scores
    threshold_df = pd.DataFrame({
        'threshold': [x[0] for x in f1_scores],
        'f1_score': [x[1] for x in f1_scores]
    })
    threshold_df.to_csv(os.path.join(output_dir, 'threshold_f1_scores.csv'), index=False)
    
    # Plot precision-recall curve
    plt.figure(figsize=(10, 6))
    plt.plot(recall, precision, marker='.', label=f'Precision-Recall (AUC = {auc(recall, precision):.4f})')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title('Precision-Recall Curve for Mappable Detection')
    plt.axvline(x=recall[np.argmax([p * r for p, r in zip(precision, recall)])], 
                color='r', linestyle='--', alpha=0.3, label=f'Best threshold = {optimal_threshold:.4f}')
    plt.grid(True)
    plt.legend()
    plt.savefig(os.path.join(output_dir, 'precision_recall_curve.png'))
    
    # Plot ROC curve
    fpr, tpr, _ = roc_curve(true_mappable, max_similarities)
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
    
    # Plot F1 scores at different thresholds
    plt.figure(figsize=(10, 6))
    plt.plot([x[0] for x in f1_scores], [x[1] for x in f1_scores], marker='.')
    plt.axvline(x=optimal_threshold, color='r', linestyle='--', alpha=0.3, 
                label=f'Optimal threshold = {optimal_threshold:.4f}')
    plt.xlabel('Threshold')
    plt.ylabel('F1 Score')
    plt.title('F1 Score vs Similarity Threshold')
    plt.grid(True)
    plt.legend()
    plt.savefig(os.path.join(output_dir, 'f1_vs_threshold.png'))
    
    return optimal_threshold

def generate_hard_negatives(model, positive_df, negative_df, loinc_df, n_hard_negatives=200):
    """
    Generate hard negative examples for training with negative mining
    
    Args:
        model: Trained model
        positive_df: DataFrame with mappable pairs
        negative_df: DataFrame with unmappable codes
        loinc_df: DataFrame with LOINC targets
        n_hard_negatives: Number of hard negatives to generate
        
    Returns:
        hard_negatives_df: DataFrame with hard negative examples
    """
    hard_negatives = []
    
    # 1. Create hard negatives from different specimen types (same analyte)
    if 'COMPONENT' in loinc_df.columns and 'SYSTEM' in loinc_df.columns:
        print("Generating hard negatives from different specimen types...")
        
        # Find components that appear with multiple specimens
        component_systems = loinc_df.groupby('COMPONENT')['SYSTEM'].nunique()
        components_with_multiple_systems = component_systems[component_systems > 1].index.tolist()
        
        print(f"Found {len(components_with_multiple_systems)} components with multiple specimens")
        
        # Create pairs of LOINCs with same component but different specimens
        for component in tqdm(components_with_multiple_systems[:min(100, len(components_with_multiple_systems))], 
                             desc="Processing components"):
            # Get all LOINCs for this component
            component_loincs = loinc_df[loinc_df['COMPONENT'] == component]
            
            # Group by system
            systems = component_loincs['SYSTEM'].unique()
            
            if len(systems) < 2:
                continue
                
            # Create pairs across different systems
            for i, system1 in enumerate(systems):
                for system2 in systems[i+1:]:
                    loincs_system1 = component_loincs[component_loincs['SYSTEM'] == system1]
                    loincs_system2 = component_loincs[component_loincs['SYSTEM'] == system2]
                    
                    if len(loincs_system1) > 0 and len(loincs_system2) > 0:
                        # Take first LOINC from each system
                        loinc1 = loincs_system1.iloc[0]
                        loinc2 = loincs_system2.iloc[0]
                        
                        # Create a hard negative pair
                        hard_negatives.append({
                            'anchor_loinc': loinc1['LOINC_NUM'],
                            'hard_negative_loinc': loinc2['LOINC_NUM'],
                            'component': component,
                            'anchor_system': system1,
                            'negative_system': system2,
                            'anchor_name': loinc1.get('LONG_COMMON_NAME', ''),
                            'negative_name': loinc2.get('LONG_COMMON_NAME', '')
                        })
                        
                        if len(hard_negatives) >= n_hard_negatives:
                            break
                            
                if len(hard_negatives) >= n_hard_negatives:
                    break
                    
            if len(hard_negatives) >= n_hard_negatives:
                break
    
    # 2. Add hard negatives from non-mappable radiology codes (if available)
    if negative_df is not None and len(negative_df) > 0:
        print("Adding hard negatives from unmappable codes...")
        
        # Get source texts from negative examples
        negative_texts = negative_df['LABEL'].tolist()
        
        # Get a sample of positive texts
        positive_texts = positive_df['SOURCE'].sample(min(100, len(positive_df)), random_state=42).tolist()
        
        # Compute embeddings
        print("Computing embeddings for similarity analysis...")
        negative_embeddings = compute_embeddings(negative_texts, model)
        positive_embeddings = compute_embeddings(positive_texts, model)
        
        # Find most similar positive-negative pairs
        from sklearn.metrics import pairwise_distances
        similarities = -pairwise_distances(negative_embeddings, positive_embeddings, metric='cosine')
        
        # For each negative, find most similar positive
        for i in range(min(100, len(negative_texts))):
            most_similar_idx = np.argmax(similarities[i])
            similarity = -similarities[i][most_similar_idx]
            
            # Only include if similarity is above a threshold (e.g., 0.7)
            if similarity > 0.7:
                hard_negatives.append({
                    'anchor_loinc': positive_df.iloc[most_similar_idx]['LOINC_NUM'] if most_similar_idx < len(positive_df) else 'unknown',
                    'hard_negative_loinc': 'UNMAPPABLE',
                    'component': 'N/A',
                    'anchor_system': 'N/A',
                    'negative_system': 'N/A',
                    'anchor_name': positive_texts[most_similar_idx],
                    'negative_name': negative_texts[i],
                    'similarity': similarity
                })
    
    hard_negatives_df = pd.DataFrame(hard_negatives)
    print(f"Generated {len(hard_negatives_df)} hard negative examples")
    
    return hard_negatives_df

def generate_triplets_with_negatives(positive_df, negative_df, hard_negatives_df, loinc_df, n_triplets=5000):
    """
    Generate triplet examples for training with negative mining
    
    Args:
        positive_df: DataFrame with mappable pairs
        negative_df: DataFrame with unmappable codes
        hard_negatives_df: DataFrame with hard negative examples
        loinc_df: DataFrame with LOINC targets
        n_triplets: Number of triplets to generate
        
    Returns:
        triplets_df: DataFrame with triplet examples
    """
    triplets = []
    
    # 1. Create triplets from hard negatives
    print("Generating triplets from hard negatives...")
    
    for _, row in hard_negatives_df.iterrows():
        anchor_loinc = row['anchor_loinc']
        hard_negative_loinc = row['hard_negative_loinc']
        
        # Skip if any LOINC is unknown
        if anchor_loinc == 'unknown' or hard_negative_loinc == 'unknown':
            continue
        
        # For unmappable negatives, use the text directly
        if hard_negative_loinc == 'UNMAPPABLE':
            negative_text = row['negative_name']
        else:
            # Get texts for LOINCs
            matching_anchor = loinc_df[loinc_df['LOINC_NUM'] == anchor_loinc]
            matching_negative = loinc_df[loinc_df['LOINC_NUM'] == hard_negative_loinc]
            
            if len(matching_anchor) == 0 or len(matching_negative) == 0:
                continue
            
            anchor_text = matching_anchor.iloc[0]['LONG_COMMON_NAME'] 
            negative_text = matching_negative.iloc[0]['LONG_COMMON_NAME']
        
        # Create a triplet with the anchor as both anchor and positive
        triplets.append({
            'anchor': anchor_text,
            'positive': anchor_text,  # Same as anchor
            'negative': negative_text,
            'anchor_loinc': anchor_loinc,
            'positive_loinc': anchor_loinc,  # Same as anchor
            'negative_loinc': hard_negative_loinc
        })
    
    # 2. Create triplets from unmappable codes
    if negative_df is not None and len(negative_df) > 0:
        print("Generating triplets with unmappable codes...")
        
        for _, row in negative_df.sample(min(100, len(negative_df)), random_state=42).iterrows():
            non_mappable_text = row['LABEL']
            
            # Randomly select a mappable LOINC
            random_loinc_row = loinc_df.sample(1, random_state=np.random.randint(0, 1000)).iloc[0]
            loinc_text = random_loinc_row['LONG_COMMON_NAME']
            loinc_code = random_loinc_row['LOINC_NUM']
            
            # Create a triplet with the LOINC as anchor/positive and non-mappable as negative
            triplets.append({
                'anchor': loinc_text,
                'positive': loinc_text,  # Same as anchor
                'negative': non_mappable_text,
                'anchor_loinc': loinc_code,
                'positive_loinc': loinc_code,  # Same as anchor
                'negative_loinc': 'UNMAPPABLE'
            })
    
    # 3. Fill remaining triplets with regular negative examples
    remaining = n_triplets - len(triplets)
    
    if remaining > 0 and len(positive_df) > 1:
        print(f"Generating {remaining} additional regular triplets...")
        
        # Get all unique LOINCs in the positive set
        unique_loincs = positive_df['LOINC_NUM'].unique()
        
        # For each unique LOINC, create triplets
        triplets_per_loinc = max(1, remaining // len(unique_loincs))
        
        for loinc in unique_loincs:
            # Get samples with this LOINC
            same_loinc_samples = positive_df[positive_df['LOINC_NUM'] == loinc]
            
            if len(same_loinc_samples) < 1:
                continue
            
            # Get samples with different LOINCs
            different_loinc_samples = positive_df[positive_df['LOINC_NUM'] != loinc]
            
            if len(different_loinc_samples) < 1:
                continue
            
            # For each sample, create triplets
            for i, row in same_loinc_samples.head(triplets_per_loinc).iterrows():
                anchor_text = row['SOURCE']
                
                # Randomly select a negative example
                negative_row = different_loinc_samples.sample(1, random_state=np.random.randint(0, 1000)).iloc[0]
                negative_text = negative_row['SOURCE']
                
                # Create triplet
                triplets.append({
                    'anchor': anchor_text,
                    'positive': anchor_text,  # Same as anchor
                    'negative': negative_text,
                    'anchor_loinc': loinc,
                    'positive_loinc': loinc,  # Same as anchor
                    'negative_loinc': negative_row['LOINC_NUM']
                })
                
                if len(triplets) >= n_triplets:
                    break
            
            if len(triplets) >= n_triplets:
                break
    
    triplets_df = pd.DataFrame(triplets)
    print(f"Generated {len(triplets_df)} triplet examples")
    
    return triplets_df

def evaluate_with_threshold(model, test_df, target_df, threshold):
    """
    Evaluate the model with the similarity threshold
    
    Args:
        model: Trained model
        test_df: DataFrame with test data
        target_df: DataFrame with LOINC targets
        threshold: Similarity threshold
        
    Returns:
        results: Dictionary with evaluation results
    """
    # Ensure test_df has is_mappable column
    if 'is_mappable' not in test_df.columns:
        test_df = test_df.copy()
        test_df['is_mappable'] = True
    
    # Get source texts
    source_texts = test_df['SOURCE'].tolist()
    
    # Get unique target LOINCs
    unique_loincs = target_df['LOINC_NUM'].unique()
    target_texts = []
    target_codes = []
    
    for loinc in tqdm(unique_loincs, desc="Preparing target texts"):
        matching_rows = target_df[target_df['LOINC_NUM'] == loinc]
        if len(matching_rows) > 0:
            target_text = matching_rows.iloc[0]['LONG_COMMON_NAME']
            target_texts.append(target_text)
            target_codes.append(loinc)
    
    # Compute embeddings
    print("Computing embeddings for source texts...")
    source_embeddings = compute_embeddings(source_texts, model)
    
    print("Computing embeddings for target texts...")
    target_embeddings = compute_embeddings(target_texts, model)
    
    # Compute similarity scores
    print("Computing similarity scores...")
    from sklearn.metrics import pairwise_distances
    similarities = -pairwise_distances(source_embeddings, target_embeddings, metric='cosine')
    
    # Get maximum similarity for each source
    max_similarities = np.max(similarities, axis=1)
    
    # Apply threshold to determine mappable/non-mappable
    predicted_mappable = max_similarities >= threshold
    
    # Get true labels
    true_mappable = test_df['is_mappable'].values
    
    # Calculate classification metrics
    tn, fp, fn, tp = confusion_matrix(true_mappable, predicted_mappable).ravel()
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    # Calculate top-k accuracy for mappable samples
    k_values = [1, 3, 5]
    top_k_results = {}
    
    # Create mapping from LOINC code to index
    loinc_to_idx = {code: i for i, code in enumerate(target_codes)}
    
    for k in k_values:
        top_k_indices = np.argsort(similarities, axis=1)[:, -k:]
        
        correct = 0
        total_evaluated = 0
        
        for i, (is_map, target_loinc) in enumerate(zip(true_mappable, test_df['LOINC_NUM'])):
            # Only evaluate true mappable samples
            if is_map and target_loinc != 'UNMAPPABLE':
                total_evaluated += 1
                
                # If predicted as mappable, check if correct target in top k
                if predicted_mappable[i]:
                    if target_loinc in loinc_to_idx:
                        target_idx = loinc_to_idx[target_loinc]
                        if target_idx in top_k_indices[i]:
                            correct += 1
        
        accuracy = correct / total_evaluated if total_evaluated > 0 else 0
        top_k_results[f'top{k}_accuracy'] = accuracy
    
    # Calculate MRR for mappable samples
    mrr_values = []
    
    for i, (is_map, target_loinc) in enumerate(zip(true_mappable, test_df['LOINC_NUM'])):
        if is_map and predicted_mappable[i] and target_loinc != 'UNMAPPABLE' and target_loinc in loinc_to_idx:
            target_idx = loinc_to_idx[target_loinc]
            # Get rank of correct target (add 1 because ranks start at 1)
            rank = np.where(np.argsort(similarities[i])[::-1] == target_idx)[0][0] + 1
            mrr_values.append(1.0 / rank)
    
    mrr = np.mean(mrr_values) if mrr_values else 0
    
    # Prepare results
    results = {
        'threshold': threshold,
        'mappable_precision': precision,
        'mappable_recall': recall,
        'mappable_f1': f1,
        'mrr': mrr,
        'true_positives': tp,
        'true_negatives': tn,
        'false_positives': fp,
        'false_negatives': fn,
        'workload_reduction': tn / len(test_df) if len(test_df) > 0 else 0
    }
    
    # Add top-k results
    results.update(top_k_results)
    
    return results, max_similarities, predicted_mappable

def main():
    parser = argparse.ArgumentParser(description='LOINC No-Match Handler with Thresholding and Negative Mining')
    parser.add_argument('--mimic_file', type=str, default='mimic_pairs_processed.csv',
                        help='Path to MIMIC mapped pairs CSV')
    parser.add_argument('--loinc_file', type=str, default='loinc_targets_processed.csv',
                        help='Path to LOINC targets CSV')
    parser.add_argument('--d_labitems_file', type=str, default='D_LABITEMS.csv',
                        help='Path to D_LABITEMS.csv for non-mappable codes')
    parser.add_argument('--checkpoint_dir', type=str, default='models/checkpoints',
                        help='Directory containing model checkpoints')
    parser.add_argument('--fold', type=int, default=0,
                        help='Fold to use for evaluation')
    parser.add_argument('--output_dir', type=str, default='results/no_match_handler',
                        help='Directory to save results')
    parser.add_argument('--mode', type=str, choices=['tune', 'evaluate', 'generate'],
                        default='tune', help='Mode of operation')
    parser.add_argument('--threshold', type=float, default=None,
                        help='Similarity threshold (if None, calculate optimal)')
    parser.add_argument('--limit_samples', type=int, default=None,
                        help='Limit number of samples for testing')
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Import modules only when needed to avoid circular imports
    from models.evaluation import load_model
    
    # Load data
    positive_df, negative_df, loinc_df = load_data(
        args.mimic_file, args.loinc_file, args.d_labitems_file, args.limit_samples)
    
    # Load model
    print(f"Loading model for fold {args.fold}...")
    model = load_model(args.checkpoint_dir, args.fold)
    
    # Execute based on mode
    if args.mode == 'tune':
        # Create evaluation dataset for threshold tuning
        eval_df = create_evaluation_dataset(positive_df, negative_df)
        
        # Find optimal threshold
        optimal_threshold = find_optimal_threshold(model, eval_df, loinc_df, args.output_dir)
        
        # Save the optimal threshold
        with open(os.path.join(args.output_dir, 'optimal_threshold.txt'), 'w') as f:
            f.write(f"{optimal_threshold}")
        
        print(f"Saved optimal threshold ({optimal_threshold:.4f}) to {os.path.join(args.output_dir, 'optimal_threshold.txt')}")
        
        # Evaluate with the optimal threshold
        results, _, _ = evaluate_with_threshold(model, eval_df, loinc_df, optimal_threshold)
        
        # Print evaluation results
        print("\nEvaluation Results:")
        print(f"Threshold: {results['threshold']:.4f}")
        print(f"Mappable Classification:")
        print(f"- Precision: {results['mappable_precision']:.4f}")
        print(f"- Recall: {results['mappable_recall']:.4f}")
        print(f"- F1 Score: {results['mappable_f1']:.4f}")
        print(f"Top-k Accuracy:")
        for k in [1, 3, 5]:
            if f'top{k}_accuracy' in results:
                print(f"- Top-{k}: {results[f'top{k}_accuracy']:.4f}")
        print(f"Mean Reciprocal Rank: {results['mrr']:.4f}")
        print(f"Workload Reduction: {results['workload_reduction']*100:.2f}%")
        
        # Save evaluation results
        results_df = pd.DataFrame([results])
        results_df.to_csv(os.path.join(args.output_dir, 'evaluation_results.csv'), index=False)
        
    elif args.mode == 'evaluate':
        # Load threshold if not provided
        if args.threshold is None:
            try:
                with open(os.path.join(args.output_dir, 'optimal_threshold.txt'), 'r') as f:
                    args.threshold = float(f.read().strip())
                print(f"Loaded threshold: {args.threshold:.4f}")
            except:
                print("No threshold provided or found, using default of 0.8")
                args.threshold = 0.8
        
        # Evaluate on the test data
        print(f"Evaluating with threshold {args.threshold:.4f}...")
        
        # Create a combined test set with both mappable and non-mappable
        test_df = create_evaluation_dataset(positive_df, negative_df, 
                                            n_positives=len(positive_df), 
                                            n_negatives=len(negative_df) if negative_df is not None else 0)
        
        results, max_similarities, predicted_mappable = evaluate_with_threshold(
            model, test_df, loinc_df, args.threshold)
        
        # Add predictions to test_df
        test_df = test_df.copy()
        test_df['max_similarity'] = max_similarities
        test_df['predicted_mappable'] = predicted_mappable
        
        # Save detailed prediction results
        test_df.to_csv(os.path.join(args.output_dir, 'detailed_predictions.csv'), index=False)
        
        # Save summary results
        results_df = pd.DataFrame([results])
        results_df.to_csv(os.path.join(args.output_dir, 'evaluation_results.csv'), index=False)
        
        # Print evaluation results
        print("\nEvaluation Results:")
        print(f"Threshold: {results['threshold']:.4f}")
        print(f"Mappable Classification:")
        print(f"- Precision: {results['mappable_precision']:.4f}")
        print(f"- Recall: {results['mappable_recall']:.4f}")
        print(f"- F1 Score: {results['mappable_f1']:.4f}")
        print(f"Top-k Accuracy:")
        for k in [1, 3, 5]:
            if f'top{k}_accuracy' in results:
                print(f"- Top-{k}: {results[f'top{k}_accuracy']:.4f}")
        print(f"Mean Reciprocal Rank: {results['mrr']:.4f}")
        print(f"Confusion Matrix:")
        print(f"- True Positives: {results['true_positives']}")
        print(f"- True Negatives: {results['true_negatives']}")
        print(f"- False Positives: {results['false_positives']}")
        print(f"- False Negatives: {results['false_negatives']}")
        print(f"Workload Reduction: {results['workload_reduction']*100:.2f}%")
        
    elif args.mode == 'generate':
        # Generate hard negatives
        hard_negatives_df = generate_hard_negatives(model, positive_df, negative_df, loinc_df)
        
        # Save hard negatives
        hard_negatives_path = os.path.join(args.output_dir, 'hard_negatives.csv')
        hard_negatives_df.to_csv(hard_negatives_path, index=False)
        print(f"Saved {len(hard_negatives_df)} hard negative examples to {hard_negatives_path}")
        
        # Generate triplets with negatives
        triplets_df = generate_triplets_with_negatives(positive_df, negative_df, hard_negatives_df, loinc_df)
        
        # Save triplets
        triplets_path = os.path.join(args.output_dir, 'negative_triplets.csv')
        triplets_df.to_csv(triplets_path, index=False)
        print(f"Saved {len(triplets_df)} triplet examples to {triplets_path}")

if __name__ == "__main__":
    main() 