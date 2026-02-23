import pandas as pd
import numpy as np
import os
import argparse
from tqdm import tqdm
from sklearn.metrics import pairwise_distances, precision_recall_curve, f1_score, auc, roc_curve
import matplotlib.pyplot as plt
import tensorflow as tf
import sys

# Add parent directory to path to import from other modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def load_non_mappable_codes(d_labitems_file):
    """
    Load non-mappable codes from D_LABITEMS.csv
    
    Args:
        d_labitems_file: Path to D_LABITEMS.csv
        
    Returns:
        non_mappable_df: DataFrame with non-mappable codes
    """
    try:
        # Load D_LABITEMS.csv
        labitems_df = pd.read_csv(d_labitems_file)
        
        # Extract non-mappable codes (where LOINC_CODE is empty/NaN)
        non_mappable_df = labitems_df[labitems_df['LOINC_CODE'].isna()]
        
        print(f"Loaded {len(non_mappable_df)} non-mappable codes from {d_labitems_file}")
        
        return non_mappable_df
    except Exception as e:
        print(f"Error loading non-mappable codes: {e}")
        return pd.DataFrame()

def generate_hard_negatives(loinc_df, n_hard_negatives=200):
    """
    Generate hard negative examples by finding syntactically similar LOINCs with different specimens
    
    Args:
        loinc_df: DataFrame with LOINC data
        n_hard_negatives: Number of hard negatives to generate
        
    Returns:
        hard_negatives_df: DataFrame with hard negative examples
    """
    # Make sure we have the required columns
    required_columns = ['LOINC_NUM', 'COMPONENT', 'SYSTEM', 'LONG_COMMON_NAME']
    if not all(col in loinc_df.columns for col in required_columns):
        missing_columns = [col for col in required_columns if col not in loinc_df.columns]
        print(f"Missing required columns in LOINC data: {missing_columns}")
        print("Using only available columns")
    
    # Find components that appear with multiple specimens
    if 'COMPONENT' in loinc_df.columns and 'SYSTEM' in loinc_df.columns:
        component_systems = loinc_df.groupby('COMPONENT')['SYSTEM'].nunique()
        components_with_multiple_systems = component_systems[component_systems > 1].index.tolist()
        
        print(f"Found {len(components_with_multiple_systems)} components with multiple specimens")
        
        # Create pairs of LOINCs with same component but different specimens
        hard_negatives = []
        
        for component in tqdm(components_with_multiple_systems[:min(100, len(components_with_multiple_systems))], 
                             desc="Generating hard negatives"):
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
        
        hard_negatives_df = pd.DataFrame(hard_negatives)
        print(f"Generated {len(hard_negatives_df)} hard negative examples")
        
        return hard_negatives_df
    else:
        print("COMPONENT or SYSTEM columns not available in LOINC data")
        return pd.DataFrame()

def calculate_similarity_threshold(model, validation_df, target_df, mappable_labels=None):
    """
    Calculate optimal similarity threshold using validation data
    
    Args:
        model: Trained model for embedding
        validation_df: DataFrame with validation data
        target_df: DataFrame with LOINC targets
        mappable_labels: Boolean array indicating whether each validation sample is mappable
        
    Returns:
        threshold: Optimal similarity threshold
        f1_scores: F1 scores at different thresholds
        thresholds: Thresholds used for evaluation
    """
    from models.evaluation import compute_embeddings
    
    # If mappable_labels is not provided, assume all validation samples are mappable
    if mappable_labels is None:
        mappable_labels = np.ones(len(validation_df), dtype=bool)
    
    # Get source texts
    source_texts = validation_df['SOURCE'].tolist()
    
    # Get unique target LOINCs and their texts
    unique_target_loincs = target_df['LOINC_NUM'].unique()
    target_texts = []
    
    for loinc in tqdm(unique_target_loincs, desc="Preparing target texts"):
        matching_rows = target_df[target_df['LOINC_NUM'] == loinc]
        if len(matching_rows) > 0:
            target_text = matching_rows.iloc[0]['TARGET']
            target_texts.append(target_text)
    
    # Compute embeddings
    print("Computing embeddings for validation sources...")
    source_embeddings = compute_embeddings(source_texts, model)
    
    print("Computing embeddings for target LOINCs...")
    target_embeddings = compute_embeddings(target_texts, model)
    
    # Calculate pairwise similarities
    print("Calculating similarities...")
    similarities = -pairwise_distances(source_embeddings, target_embeddings, metric='cosine')
    
    # Get maximum similarity for each source
    max_similarities = np.max(similarities, axis=1)
    
    # Calculate precision, recall, and thresholds for mappable vs non-mappable
    precision, recall, thresholds = precision_recall_curve(mappable_labels, max_similarities)
    
    # Calculate F1 score at each threshold
    f1_scores = []
    for p, r, t in zip(precision[:-1], recall[:-1], thresholds):
        f1 = 2 * (p * r) / (p + r) if (p + r) > 0 else 0
        f1_scores.append((t, f1))
    
    # Sort by F1 score to find optimal threshold
    f1_scores.sort(key=lambda x: x[1], reverse=True)
    optimal_threshold = f1_scores[0][0]
    
    print(f"Optimal similarity threshold: {optimal_threshold:.4f} (F1: {f1_scores[0][1]:.4f})")
    
    # Calculate ROC AUC
    fpr, tpr, _ = roc_curve(mappable_labels, max_similarities)
    roc_auc = auc(fpr, tpr)
    print(f"ROC AUC: {roc_auc:.4f}")
    
    # Plot precision-recall curve
    plt.figure(figsize=(10, 6))
    plt.plot(recall, precision, marker='.', label=f'Precision-Recall (AUC = {auc(recall, precision):.4f})')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title('Precision-Recall Curve for Mappable Detection')
    plt.grid(True)
    plt.savefig('results/precision_recall_curve.png')
    
    # Plot ROC curve
    plt.figure(figsize=(10, 6))
    plt.plot(fpr, tpr, marker='.', label=f'ROC (AUC = {roc_auc:.4f})')
    plt.plot([0, 1], [0, 1], 'k--')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('ROC Curve for Mappable Detection')
    plt.grid(True)
    plt.savefig('results/roc_curve.png')
    
    # Return optimal threshold and F1 scores
    return optimal_threshold, [f[1] for f in f1_scores], [f[0] for f in f1_scores]

def evaluate_with_threshold(model, test_df, target_df, threshold, non_mappable_df=None):
    """
    Evaluate model with similarity threshold to detect non-mappable codes
    
    Args:
        model: Trained model for embedding
        test_df: DataFrame with test data
        target_df: DataFrame with LOINC targets
        threshold: Similarity threshold
        non_mappable_df: DataFrame with non-mappable codes for evaluation
        
    Returns:
        results: Dictionary with evaluation results
    """
    from models.evaluation import compute_embeddings
    
    # Combine mappable and non-mappable codes for evaluation
    combined_test = test_df.copy()
    combined_test['is_mappable'] = True
    
    if non_mappable_df is not None and len(non_mappable_df) > 0:
        # Prepare non-mappable data
        non_mappable_test = pd.DataFrame({
            'SOURCE': non_mappable_df['LABEL'].tolist(),
            'LOINC_NUM': ['UNMAPPABLE'] * len(non_mappable_df),
            'is_mappable': [False] * len(non_mappable_df)
        })
        
        # Combine with test data
        combined_test = pd.concat([combined_test, non_mappable_test], ignore_index=True)
        
    print(f"Evaluating {len(combined_test)} samples with threshold {threshold:.4f}")
    print(f"- Mappable: {combined_test['is_mappable'].sum()}")
    print(f"- Non-mappable: {(~combined_test['is_mappable']).sum()}")
    
    # Get source texts
    source_texts = combined_test['SOURCE'].tolist()
    
    # Get unique target LOINCs and their texts
    unique_target_loincs = target_df['LOINC_NUM'].unique()
    target_texts = []
    
    for loinc in tqdm(unique_target_loincs, desc="Preparing target texts"):
        matching_rows = target_df[target_df['LOINC_NUM'] == loinc]
        if len(matching_rows) > 0:
            target_text = matching_rows.iloc[0]['TARGET']
            target_texts.append(target_text)
    
    # Compute embeddings
    print("Computing embeddings for test sources...")
    source_embeddings = compute_embeddings(source_texts, model)
    
    print("Computing embeddings for target LOINCs...")
    target_embeddings = compute_embeddings(target_texts, model)
    
    # Calculate pairwise similarities
    print("Calculating similarities...")
    similarities = -pairwise_distances(source_embeddings, target_embeddings, metric='cosine')
    
    # Get maximum similarity for each source
    max_similarities = np.max(similarities, axis=1)
    
    # Apply threshold to determine mappable/non-mappable
    predicted_mappable = max_similarities >= threshold
    
    # Get top-k predictions and confidence scores
    k_values = [1, 3, 5]
    results = {}
    
    # Calculate top-k accuracy for mappable samples only
    for k in k_values:
        # Top-k indices for each source
        top_k_indices = np.argsort(similarities, axis=1)[:, -k:]
        
        # Count correct predictions for mappable samples
        correct = 0
        total_mappable = 0
        
        for i, (is_mappable, target_loinc) in enumerate(zip(combined_test['is_mappable'], combined_test['LOINC_NUM'])):
            if is_mappable:
                total_mappable += 1
                
                # Only check if predicted as mappable
                if predicted_mappable[i]:
                    # Get true LOINC index in target pool
                    target_idx = np.where(unique_target_loincs == target_loinc)[0]
                    
                    if len(target_idx) > 0 and target_idx[0] in top_k_indices[i]:
                        correct += 1
        
        accuracy = correct / total_mappable if total_mappable > 0 else 0
        results[f'top{k}_accuracy'] = accuracy
        print(f"Top-{k} accuracy for mappable samples: {accuracy:.4f}")
    
    # Calculate mappable/non-mappable classification metrics
    true_labels = combined_test['is_mappable'].values
    
    tp = np.sum((true_labels) & (predicted_mappable))
    tn = np.sum((~true_labels) & (~predicted_mappable))
    fp = np.sum((~true_labels) & (predicted_mappable))
    fn = np.sum((true_labels) & (~predicted_mappable))
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    results['mappable_precision'] = precision
    results['mappable_recall'] = recall
    results['mappable_f1'] = f1
    results['threshold'] = threshold
    
    print(f"Mappable Classification:")
    print(f"- Precision: {precision:.4f}")
    print(f"- Recall: {recall:.4f}")
    print(f"- F1 Score: {f1:.4f}")
    
    # Create confusion matrix
    print("\nConfusion Matrix:")
    print(f"True Mappable, Predicted Mappable: {tp}")
    print(f"True Mappable, Predicted Non-mappable: {fn}")
    print(f"True Non-mappable, Predicted Mappable: {fp}")
    print(f"True Non-mappable, Predicted Non-mappable: {tn}")
    
    # Sample 10 cases with high-confidence incorrect predictions
    incorrect_indices = np.where((true_labels != predicted_mappable) & 
                               (np.abs(max_similarities - threshold) > 0.1))[0]
    
    if len(incorrect_indices) > 0:
        print("\nSample of high-confidence incorrect predictions:")
        sample_size = min(10, len(incorrect_indices))
        sampled_indices = np.random.choice(incorrect_indices, sample_size, replace=False)
        
        for idx in sampled_indices:
            source_text = source_texts[idx]
            true_mappable = true_labels[idx]
            pred_mappable = predicted_mappable[idx]
            confidence = max_similarities[idx]
            
            print(f"Source: {source_text}")
            print(f"True: {'Mappable' if true_mappable else 'Non-mappable'}, "
                 f"Predicted: {'Mappable' if pred_mappable else 'Non-mappable'}")
            print(f"Confidence: {confidence:.4f}")
            
            if true_mappable:
                # Show true LOINC code and top prediction
                true_loinc = combined_test.iloc[idx]['LOINC_NUM']
                top_idx = np.argmax(similarities[idx])
                top_loinc = unique_target_loincs[top_idx]
                top_confidence = similarities[idx][top_idx]
                
                print(f"True LOINC: {true_loinc}")
                print(f"Top Prediction: {top_loinc} (confidence: {-top_confidence:.4f})")
            
            print("-" * 80)
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Implement and evaluate negative mining for non-mappable codes')
    parser.add_argument('--test_file', type=str, default='output/mimic_pairs_processed.csv', 
                        help='Path to test data CSV')
    parser.add_argument('--loinc_file', type=str, default='output/loinc_full_processed.csv', 
                        help='Path to LOINC data CSV')
    parser.add_argument('--d_labitems_file', type=str, default='D_LABITEMS.csv', 
                        help='Path to D_LABITEMS.csv for non-mappable codes')
    parser.add_argument('--checkpoint_dir', type=str, default='models/checkpoints', 
                        help='Directory containing model checkpoints')
    parser.add_argument('--fold', type=int, default=0, 
                        help='Fold to evaluate (0-indexed)')
    parser.add_argument('--output_dir', type=str, default='results/negative_mining', 
                        help='Directory to save results')
    parser.add_argument('--generate_triplets', action='store_true',
                        help='Generate triplet examples for training with negatives')
    parser.add_argument('--threshold', type=float, default=None,
                        help='Use specific similarity threshold (if not specified, calculate optimal)')
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Import modules only when needed to avoid circular imports
    print("Loading necessary modules and data...")
    try:
        from models.evaluation import compute_embeddings, load_model
        
        # Load data
        print(f"Loading test data from {args.test_file}...")
        test_df = pd.read_csv(args.test_file)
        
        print(f"Loading LOINC targets from {args.loinc_file}...")
        loinc_df = pd.read_csv(args.loinc_file)
        
        # Prepare target df with required columns
        if 'TARGET' not in loinc_df.columns:
            if 'LONG_COMMON_NAME' in loinc_df.columns:
                loinc_df['TARGET'] = loinc_df['LONG_COMMON_NAME']
            elif 'DisplayName' in loinc_df.columns:
                loinc_df['TARGET'] = loinc_df['DisplayName']
            else:
                raise ValueError("LOINC data does not have TARGET, LONG_COMMON_NAME, or DisplayName column")
        
        # Load non-mappable codes
        print(f"Loading non-mappable codes from {args.d_labitems_file}...")
        non_mappable_df = load_non_mappable_codes(args.d_labitems_file)
        
        # Load model
        print(f"Loading model for fold {args.fold}...")
        model = load_model(args.checkpoint_dir, args.fold)
        
        # Generate hard negatives
        print("Generating hard negative examples...")
        hard_negatives_df = generate_hard_negatives(loinc_df)
        
        if len(hard_negatives_df) > 0:
            hard_negatives_path = os.path.join(args.output_dir, 'hard_negatives.csv')
            hard_negatives_df.to_csv(hard_negatives_path, index=False)
            print(f"Saved {len(hard_negatives_df)} hard negative examples to {hard_negatives_path}")
        
        # Split test data into validation and test sets
        validation_size = int(0.3 * len(test_df))
        validation_df = test_df.sample(validation_size, random_state=42)
        test_df = test_df.drop(validation_df.index)
        
        print(f"Split data into {len(validation_df)} validation and {len(test_df)} test samples")
        
        # Calculate or use specified similarity threshold
        if args.threshold is None:
            print("Calculating optimal similarity threshold...")
            optimal_threshold, f1_scores, thresholds = calculate_similarity_threshold(
                model, validation_df, loinc_df)
            
            # Save threshold information
            threshold_df = pd.DataFrame({
                'threshold': thresholds,
                'f1_score': f1_scores
            })
            threshold_df.to_csv(os.path.join(args.output_dir, 'thresholds.csv'), index=False)
        else:
            optimal_threshold = args.threshold
            print(f"Using specified similarity threshold: {optimal_threshold}")
        
        # Evaluate with similarity threshold
        print("Evaluating with similarity threshold...")
        results = evaluate_with_threshold(model, test_df, loinc_df, optimal_threshold, non_mappable_df)
        
        # Save results
        results_df = pd.DataFrame([results])
        results_df.to_csv(os.path.join(args.output_dir, 'threshold_results.csv'), index=False)
        print(f"Saved results to {os.path.join(args.output_dir, 'threshold_results.csv')}")
        
        # Generate triplet examples for training with negatives if requested
        if args.generate_triplets:
            print("Generating triplet examples with negatives...")
            
            triplets = []
            
            # Create triplets from hard negatives
            for _, row in hard_negatives_df.iterrows():
                anchor_loinc = row['anchor_loinc']
                hard_negative_loinc = row['hard_negative_loinc']
                
                # Get texts
                anchor_text = loinc_df[loinc_df['LOINC_NUM'] == anchor_loinc].iloc[0]['TARGET']
                negative_text = loinc_df[loinc_df['LOINC_NUM'] == hard_negative_loinc].iloc[0]['TARGET']
                
                # Create a triplet with the anchor as both anchor and positive
                triplets.append({
                    'anchor': anchor_text,
                    'positive': anchor_text,  # Same as anchor
                    'negative': negative_text,
                    'anchor_loinc': anchor_loinc,
                    'positive_loinc': anchor_loinc,  # Same as anchor
                    'negative_loinc': hard_negative_loinc
                })
            
            # Create triplets with non-mappable codes
            if len(non_mappable_df) > 0:
                for _, row in non_mappable_df.sample(min(100, len(non_mappable_df))).iterrows():
                    non_mappable_text = row['LABEL']
                    
                    # Randomly select a mappable LOINC
                    random_loinc_row = loinc_df.sample(1).iloc[0]
                    loinc_text = random_loinc_row['TARGET']
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
            
            # Save triplets
            triplets_df = pd.DataFrame(triplets)
            triplets_path = os.path.join(args.output_dir, 'negative_triplets.csv')
            triplets_df.to_csv(triplets_path, index=False)
            print(f"Saved {len(triplets_df)} triplet examples to {triplets_path}")
        
        print("Done!")
        
    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    main() 