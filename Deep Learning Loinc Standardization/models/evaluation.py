import tensorflow as tf
import numpy as np
import pandas as pd
import os
import argparse
import sys
import time
from sklearn.metrics import pairwise_distances
from tqdm import tqdm

# Add parent directory to path to import from other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.t5_encoder import LOINCEncoder
from preprocessing.data_augmentation import augment_text

def load_test_data(test_file):
    """
    Load test data from CSV file
    
    Args:
        test_file: Path to the test data CSV file
        
    Returns:
        test_df: DataFrame with test data
    """
    test_df = pd.read_csv(test_file)
    print(f"Loaded {len(test_df)} test samples from {test_file}")
    
    # Check if this is an augmented test file (has 'is_augmented' column)
    if 'is_augmented' in test_df.columns:
        print(f"Found augmented test data: {len(test_df[test_df['is_augmented']])} augmented samples, {len(test_df[~test_df['is_augmented']])} original samples")
    
    required_columns = ['SOURCE', 'LOINC_NUM']
    missing_columns = [col for col in required_columns if col not in test_df.columns]
    if missing_columns:
        raise ValueError(f"Test data is missing required columns: {missing_columns}")
    
    return test_df

def load_target_loincs(loinc_file):
    """
    Load LOINC target data
    
    Args:
        loinc_file: Path to the LOINC data CSV file
        
    Returns:
        target_df: DataFrame with LOINC targets
    """
    target_df = pd.read_csv(loinc_file)
    print(f"Loaded {len(target_df)} LOINC targets from {loinc_file}")
    
    required_columns = ['LOINC_NUM']
    missing_columns = [col for col in required_columns if col not in target_df.columns]
    if missing_columns:
        raise ValueError(f"LOINC data is missing required columns: {missing_columns}")
    
    # Handle the target text column which might be named differently
    text_column_candidates = ['TARGET', 'LONG_COMMON_NAME', 'DisplayName', 'SHORTNAME']
    available_text_columns = [col for col in text_column_candidates if col in target_df.columns]
    
    if not available_text_columns:
        raise ValueError(f"LOINC data does not have any suitable text column. Need one of: {text_column_candidates}")
    
    # Use the first available text column as the TARGET
    text_column = available_text_columns[0]
    print(f"Using '{text_column}' as the target text column")
    
    # Create a new dataframe with LOINC_NUM and TARGET columns
    processed_df = pd.DataFrame({
        'LOINC_NUM': target_df['LOINC_NUM'],
        'TARGET': target_df[text_column]
    })
    
    return processed_df

def load_model(checkpoint_dir, fold):
    """
    Load trained model for the specified fold
    
    Args:
        checkpoint_dir: Directory with model checkpoints
        fold: Fold index
        
    Returns:
        model: Loaded model
    """
    model_path = os.path.join(checkpoint_dir, f"stage2_fold{fold+1}_model.weights.h5")
    if not os.path.exists(model_path):
        raise ValueError(f"Model checkpoint not found at {model_path}")
    
    try:
        # Import the model class
        from models.t5_encoder import LOINCEncoder
        
        # Initialize the model
        model = LOINCEncoder(embedding_dim=128, dropout_rate=0.0)
        
        # Create a dummy input to build the model
        _ = model(inputs=["dummy text"])
        
        # Load the weights
        model.load_weights(model_path)
        print(f"Loaded model from {model_path}")
        return model
    except Exception as e:
        print(f"Error loading model: {e}")
        raise

def compute_embeddings(texts, model, batch_size=16):
    """
    Compute embeddings for texts
    
    Args:
        texts: List of texts to embed
        model: Trained model
        batch_size: Batch size for inference
        
    Returns:
        embeddings: Numpy array of embeddings
    """
    try:
        all_embeddings = []
        # Add tqdm progress bar to show progress during embedding computation
        for i in tqdm(range(0, len(texts), batch_size), desc="Computing embeddings", 
                     total=(len(texts) + batch_size - 1) // batch_size):
            batch_texts = texts[i:i + batch_size]
            # Ensure all texts are strings
            batch_texts = [str(text) if not isinstance(text, str) else text for text in batch_texts]
            # Calculate embeddings for batch
            batch_embeddings = model(inputs=batch_texts, training=False).numpy()
            all_embeddings.append(batch_embeddings)
        
        # Concatenate all batches
        embeddings = np.concatenate(all_embeddings, axis=0)
    return embeddings
    except Exception as e:
        print(f"Error computing embeddings: {e}")
        raise

def evaluate_top_k_accuracy(test_df, target_df, model, k_values=[1, 3, 5], batch_size=16, 
                           augmented_test=False, use_only_original=False, max_samples=None):
    """
    Evaluate Top-k accuracy
    
    Args:
        test_df: DataFrame with test data
        target_df: DataFrame with LOINC targets
        model: Trained model
        k_values: List of k values for Top-k accuracy
        batch_size: Batch size for inference
        augmented_test: Whether this is augmented test data
        use_only_original: If True, only use original samples from augmented test data
        max_samples: Maximum number of samples to use for evaluation (for debugging/performance)
        
    Returns:
        results: Dictionary with Top-k accuracy results
    """
    # Preprocess data if needed
    if augmented_test and use_only_original and 'is_augmented' in test_df.columns:
        print("Using only original samples from augmented test data")
        test_df = test_df[~test_df['is_augmented']]
    
    # Limit number of samples if specified
    if max_samples is not None and max_samples > 0 and max_samples < len(test_df):
        print(f"Limiting evaluation to {max_samples} samples (out of {len(test_df)} total)")
        test_df = test_df.sample(max_samples, random_state=42)
    
    # Get unique target LOINCs
    unique_target_loincs = target_df['LOINC_NUM'].unique()
    unique_target_texts = target_df['TARGET'].unique()
    print(f"Evaluating against {len(unique_target_loincs)} unique LOINC targets")
    
    # Check if test LOINCs exist in target LOINCs
    test_loincs = test_df['LOINC_NUM'].unique()
    matching_loincs = set(test_loincs) & set(unique_target_loincs)
    print(f"Test data has {len(test_loincs)} unique LOINCs, {len(matching_loincs)} match with target LOINCs")
    
    if len(matching_loincs) == 0:
        print("WARNING: No matching LOINCs between test and target data!")
        print(f"Test LOINCs: {test_loincs}")
        print(f"First few target LOINCs: {list(unique_target_loincs)[:10]}")
    
    # Get source texts and target LOINCs
    source_texts = test_df['SOURCE'].tolist()
    target_loincs = test_df['LOINC_NUM'].tolist()
    
    # Compute embeddings for target LOINCs
    print("Computing embeddings for target LOINCs...")
    target_texts = []
    for loinc in tqdm(unique_target_loincs):
        # Use first matching text if multiple exist for the same LOINC code
        matching_rows = target_df[target_df['LOINC_NUM'] == loinc]
        target_text = matching_rows.iloc[0]['TARGET']
        target_texts.append(target_text)
    
    target_embeddings = compute_embeddings(target_texts, model, batch_size)
    
    # Compute embeddings for source texts
    print("Computing embeddings for source texts...")
    source_embeddings = compute_embeddings(source_texts, model, batch_size)
    
    # Create dictionary mapping LOINC codes to their indices in the target embeddings
    loinc_to_index = {loinc: i for i, loinc in enumerate(unique_target_loincs)}
    
    # Calculate pairwise distances
    print("Calculating similarities...")
    # Using negative cosine distance (higher is better)
    similarities = -pairwise_distances(source_embeddings, target_embeddings, metric='cosine')
    
    # Calculate Top-k accuracy
    results = {}
    for k in k_values:
        # Get top k indices for each source
        top_k_indices = np.argsort(similarities, axis=1)[:, -k:]
        
        # Check if correct target is in top k
    correct = 0
        for i, target_loinc in enumerate(target_loincs):
            # Get the target LOINC's index
            if target_loinc in loinc_to_index:
                target_idx = loinc_to_index[target_loinc]
                # Check if target index is in top k
                if target_idx in top_k_indices[i]:
            correct += 1
            else:
                print(f"WARNING: Target LOINC {target_loinc} not in target pool")
    
    # Calculate accuracy
        accuracy = correct / len(source_texts)
        results[f'top{k}_accuracy'] = accuracy
        print(f"Top-{k} accuracy: {accuracy:.4f} ({correct}/{len(source_texts)})")
    
    # Calculate Mean Reciprocal Rank (MRR)
    reciprocal_ranks = []
    for i, target_loinc in enumerate(target_loincs):
        if target_loinc in loinc_to_index:
            target_idx = loinc_to_index[target_loinc]
            # Get rank of correct target (add 1 because indices are 0-based)
            rank = np.where(np.argsort(similarities[i])[::-1] == target_idx)[0][0] + 1
            reciprocal_ranks.append(1.0 / rank)
        else:
            reciprocal_ranks.append(0.0)
    
    mrr = np.mean(reciprocal_ranks)
    results['mrr'] = mrr
    print(f"Mean Reciprocal Rank: {mrr:.4f}")
    
    # Add target pool size to results
    results['target_pool_size'] = len(unique_target_loincs)
    results['matching_loincs'] = len(matching_loincs)
    results['test_samples'] = len(source_texts)
    
    return results

def evaluate_stratified_by_scale(test_df, target_df, model, k_values=[1, 3, 5], batch_size=16, loinc_df=None):
    """
    Evaluate Top-k accuracy stratified by SCALE_TYP
    
    Args:
        test_df: DataFrame with test data
        target_df: DataFrame with LOINC targets
        model: Trained model
        k_values: List of k values for Top-k accuracy
        batch_size: Batch size for inference
        loinc_df: DataFrame containing LOINC data with scale information
        
    Returns:
        results: Dictionary with Top-k accuracy results stratified by scale type
    """
    if loinc_df is None or 'SCALE_TYP' not in loinc_df.columns:
        print("SCALE_TYP information not available in LOINC data, cannot stratify by scale")
        return None
    
    # Create mapping from LOINC code to scale type
    loinc_to_scale = {}
    for _, row in loinc_df.iterrows():
        if pd.notna(row['LOINC_NUM']) and pd.notna(row['SCALE_TYP']):
            loinc_to_scale[row['LOINC_NUM']] = row['SCALE_TYP']
    
    # Add scale type to test_df
    test_df = test_df.copy()
    test_df['SCALE_TYP'] = test_df['LOINC_NUM'].map(loinc_to_scale)
    
    # Fill missing scale types with unknown
    test_df['SCALE_TYP'] = test_df['SCALE_TYP'].fillna('unknown')
    
    # Get unique scale types
    scale_types = test_df['SCALE_TYP'].unique()
    print(f"Found {len(scale_types)} unique scale types: {scale_types}")
    
    # Get unique target LOINCs
    unique_target_loincs = target_df['LOINC_NUM'].unique()
    
    # Compute embeddings for target LOINCs
    print("Computing embeddings for target LOINCs...")
    target_texts = []
    target_loincs = []
    
    for loinc in tqdm(unique_target_loincs):
        # Use first matching text if multiple exist for the same LOINC code
        matching_rows = target_df[target_df['LOINC_NUM'] == loinc]
        target_text = matching_rows.iloc[0]['TARGET']
        
        # Get scale type
        scale_type = loinc_to_scale.get(loinc, 'unknown')
        
        # Append scale sentinel token
        if 'append_scale_token' in globals():
            target_text = append_scale_token(target_text, scale_type)
        else:
            # Import from parent directory if not already available
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from data_augmentation import append_scale_token
            target_text = append_scale_token(target_text, scale_type)
        
        target_texts.append(target_text)
        target_loincs.append(loinc)
    
    target_embeddings = compute_embeddings(target_texts, model, batch_size)
    
    # Create dictionary mapping LOINC codes to their indices in the target embeddings
    loinc_to_index = {loinc: i for i, loinc in enumerate(target_loincs)}
    
    # Dictionary to store results by scale type
    results_by_scale = {}
    
    for scale_type in scale_types:
        print(f"\nEvaluating SCALE_TYP: {scale_type}")
        
        # Filter test data by scale type
        scale_test_df = test_df[test_df['SCALE_TYP'] == scale_type]
        print(f"Found {len(scale_test_df)} test samples with SCALE_TYP = {scale_type}")
        
        if len(scale_test_df) == 0:
            continue
        
        # Get source texts and target LOINCs for this scale type
        source_texts = scale_test_df['SOURCE'].tolist()
        target_loincs = scale_test_df['LOINC_NUM'].tolist()
        
        # Add scale sentinel token to source texts
        source_texts_with_scale = []
        for text in source_texts:
            # Convert to string if needed
            text = str(text) if not isinstance(text, str) else text
            
            # First try with known scale
            source_text = append_scale_token(text.lower(), scale_type)
            source_texts_with_scale.append(source_text)
        
        # Compute embeddings for source texts
        source_embeddings = compute_embeddings(source_texts_with_scale, model, batch_size)
        
        # Calculate pairwise distances
        # Use negative cosine distance (higher is more similar)
        similarities = -pairwise_distances(source_embeddings, target_embeddings, metric='cosine')
        
        # Evaluate Top-k accuracy
        top_k_results = {}
        for k in k_values:
            correct = 0
            for i, loinc in enumerate(target_loincs):
                # Get top-k predictions
                top_k_indices = np.argsort(similarities[i])[::-1][:k]
                top_k_loincs = [target_loincs[idx] for idx in top_k_indices]
                
                # Check if true LOINC is in top-k predictions
                if loinc in top_k_loincs:
                    correct += 1
            
            accuracy = correct / len(target_loincs) if len(target_loincs) > 0 else 0
            top_k_results[f'top_{k}_accuracy'] = accuracy
            print(f"Top-{k} accuracy: {accuracy:.4f}")
        
        # Store results for this scale type
        results_by_scale[scale_type] = top_k_results
    
    # Also run evaluation with scale token set to 'unk'
    print("\nEvaluating with scale token set to 'unk' (ablation)")
    
    # Add 'unk' scale token to source texts
    source_texts = test_df['SOURCE'].tolist()
    source_texts_with_unk = []
    for text in source_texts:
        # Convert to string if needed
        text = str(text) if not isinstance(text, str) else text
        
        # Use 'unk' scale
        source_text = append_scale_token(text.lower(), 'unk')
        source_texts_with_unk.append(source_text)
    
    # Get target LOINCs from test data
    target_loincs_test = test_df['LOINC_NUM'].tolist()
    
    # Compute embeddings for source texts with 'unk' scale
    source_embeddings_unk = compute_embeddings(source_texts_with_unk, model, batch_size)
    
    # Calculate pairwise distances
    # Use negative cosine distance (higher is more similar)
    similarities_unk = -pairwise_distances(source_embeddings_unk, target_embeddings, metric='cosine')
    
    # Evaluate Top-k accuracy for 'unk' scale
    top_k_results_unk = {}
    for k in k_values:
        correct = 0
        for i, loinc in enumerate(target_loincs_test):
            # Get top-k predictions
            top_k_indices = np.argsort(similarities_unk[i])[::-1][:k]
            top_k_loincs = [target_loincs[idx] for idx in top_k_indices]
            
            # Check if true LOINC is in top-k predictions
            if loinc in top_k_loincs:
                correct += 1
        
        accuracy = correct / len(target_loincs_test) if len(target_loincs_test) > 0 else 0
        top_k_results_unk[f'top_{k}_accuracy'] = accuracy
        print(f"Top-{k} accuracy with 'unk' scale: {accuracy:.4f}")
    
    # Store results for 'unk' scale
    results_by_scale['unk'] = top_k_results_unk
    
    # Also compare scale-sensitive pairs (e.g., Qn vs Ql)
    print("\nEvaluating scale-confusable pairs")
    
    # Find pairs of test samples with same COMPONENT but different SCALE_TYP
    if 'COMPONENT' in loinc_df.columns:
        # Create mapping from LOINC code to component
        loinc_to_component = {}
        for _, row in loinc_df.iterrows():
            if pd.notna(row['LOINC_NUM']) and pd.notna(row['COMPONENT']):
                loinc_to_component[row['LOINC_NUM']] = row['COMPONENT']
        
        # Add component to test_df
        test_df['COMPONENT'] = test_df['LOINC_NUM'].map(loinc_to_component)
        
        # Group by component and find components with multiple scale types
        components_with_multiple_scales = []
        for component, group in test_df.groupby('COMPONENT'):
            if len(group['SCALE_TYP'].unique()) > 1:
                components_with_multiple_scales.append(component)
        
        print(f"Found {len(components_with_multiple_scales)} components with multiple scale types")
        
        if len(components_with_multiple_scales) > 0:
            # Filter test data to include only components with multiple scale types
            confusable_test_df = test_df[test_df['COMPONENT'].isin(components_with_multiple_scales)]
            print(f"Found {len(confusable_test_df)} confusable test samples")
            
            # Get source texts and target LOINCs for confusable pairs
            confusable_source_texts = confusable_test_df['SOURCE'].tolist()
            confusable_target_loincs = confusable_test_df['LOINC_NUM'].tolist()
            confusable_scales = confusable_test_df['SCALE_TYP'].tolist()
            
            # Evaluate with correct scale token
            confusable_source_texts_with_scale = []
            for text, scale_type in zip(confusable_source_texts, confusable_scales):
                # Convert to string if needed
                text = str(text) if not isinstance(text, str) else text
                
                # Use correct scale
                source_text = append_scale_token(text.lower(), scale_type)
                confusable_source_texts_with_scale.append(source_text)
            
            # Compute embeddings for confusable source texts with correct scale
            confusable_source_embeddings = compute_embeddings(confusable_source_texts_with_scale, model, batch_size)
            
            # Calculate pairwise distances
            confusable_similarities = -pairwise_distances(confusable_source_embeddings, target_embeddings, metric='cosine')
            
            # Evaluate Top-k accuracy for confusable pairs with correct scale
            confusable_results = {}
            for k in k_values:
                correct = 0
                for i, loinc in enumerate(confusable_target_loincs):
                    # Get top-k predictions
                    top_k_indices = np.argsort(confusable_similarities[i])[::-1][:k]
                    top_k_loincs = [target_loincs[idx] for idx in top_k_indices]
                    
                    # Check if true LOINC is in top-k predictions
                    if loinc in top_k_loincs:
                        correct += 1
                
                accuracy = correct / len(confusable_target_loincs) if len(confusable_target_loincs) > 0 else 0
                confusable_results[f'top_{k}_accuracy'] = accuracy
                print(f"Top-{k} accuracy for confusable pairs with correct scale: {accuracy:.4f}")
            
            # Store results for confusable pairs with correct scale
            results_by_scale['confusable_with_scale'] = confusable_results
            
            # Evaluate with 'unk' scale token
            confusable_source_texts_with_unk = []
            for text in confusable_source_texts:
                # Convert to string if needed
                text = str(text) if not isinstance(text, str) else text
                
                # Use 'unk' scale
                source_text = append_scale_token(text.lower(), 'unk')
                confusable_source_texts_with_unk.append(source_text)
            
            # Compute embeddings for confusable source texts with 'unk' scale
            confusable_source_embeddings_unk = compute_embeddings(confusable_source_texts_with_unk, model, batch_size)
            
            # Calculate pairwise distances
            confusable_similarities_unk = -pairwise_distances(confusable_source_embeddings_unk, target_embeddings, metric='cosine')
            
            # Evaluate Top-k accuracy for confusable pairs with 'unk' scale
            confusable_results_unk = {}
            for k in k_values:
                correct = 0
                for i, loinc in enumerate(confusable_target_loincs):
                    # Get top-k predictions
                    top_k_indices = np.argsort(confusable_similarities_unk[i])[::-1][:k]
                    top_k_loincs = [target_loincs[idx] for idx in top_k_indices]
                    
                    # Check if true LOINC is in top-k predictions
                    if loinc in top_k_loincs:
                        correct += 1
                
                accuracy = correct / len(confusable_target_loincs) if len(confusable_target_loincs) > 0 else 0
                confusable_results_unk[f'top_{k}_accuracy'] = accuracy
                print(f"Top-{k} accuracy for confusable pairs with 'unk' scale: {accuracy:.4f}")
            
            # Store results for confusable pairs with 'unk' scale
            results_by_scale['confusable_with_unk'] = confusable_results_unk
            
            # Manual inspection of 10 high-risk assays if available
            high_risk_assays = ['blood culture', 'drug screen', 'hormone']
            high_risk_test_df = test_df[test_df['SOURCE'].str.lower().str.contains('|'.join(high_risk_assays), na=False)]
            
            if len(high_risk_test_df) > 0:
                print(f"\nFound {len(high_risk_test_df)} high-risk assay samples for manual inspection")
                high_risk_sample = high_risk_test_df.sample(min(10, len(high_risk_test_df)))
                
                print("\nSample of 10 high-risk assays for manual inspection:")
                for _, row in high_risk_sample.iterrows():
                    loinc_code = row['LOINC_NUM']
                    source_text = row['SOURCE']
                    scale_type = row['SCALE_TYP']
                    component = row.get('COMPONENT', 'N/A')
                    
                    print(f"LOINC: {loinc_code}, Scale: {scale_type}, Component: {component}")
                    print(f"Source: {source_text}")
                    print("-" * 80)
    
    return results_by_scale

def main():
    parser = argparse.ArgumentParser(description='Evaluate LOINC standardization model')
    parser.add_argument('--test_file', type=str, required=True, 
                        help='Path to test data CSV')
    parser.add_argument('--loinc_file', type=str, required=True, 
                        help='Path to LOINC data CSV')
    parser.add_argument('--checkpoint_dir', type=str, default='models/checkpoints', 
                        help='Directory containing model checkpoints')
    parser.add_argument('--fold', type=int, default=0, 
                        help='Fold to evaluate (0-indexed)')
    parser.add_argument('--output_dir', type=str, default='results', 
                        help='Directory to save evaluation results')
    parser.add_argument('--batch_size', type=int, default=16, 
                        help='Batch size for inference')
    parser.add_argument('--expanded_pool', action='store_true', 
                        help='Using expanded target pool')
    parser.add_argument('--augmented_test', action='store_true', 
                        help='Using augmented test data')
    parser.add_argument('--ablation_id', type=str, default=None, 
                        help='Ablation study identifier')
    parser.add_argument('--max_samples', type=int, default=None,
                        help='Maximum number of samples to evaluate (for debugging or performance issues)')
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load data
    print(f"Loading test data from {args.test_file}...")
    test_df = load_test_data(args.test_file)
    
    print(f"Loading LOINC targets from {args.loinc_file}...")
    target_df = load_target_loincs(args.loinc_file)
    
    # Load model
    print(f"Loading model for fold {args.fold}...")
    try:
        model = load_model(args.checkpoint_dir, args.fold)
    except Exception as e:
        print(f"Error loading model: {e}")
        print("WARNING: Using default model for evaluation")
        # Use fold 0 as fallback if fold not found
        try:
            model = load_model(args.checkpoint_dir, 0)
        except Exception as e:
            print(f"Error loading fallback model: {e}")
            return
    
    # Evaluate model
    print("Evaluating model...")
    start_time = time.time()
    
    # Create a file prefix for the results
    if args.expanded_pool:
        if args.augmented_test:
            file_prefix = f"fold{args.fold}_augmented_expanded"
        else:
            file_prefix = f"fold{args.fold}_expanded"
    else:
        if args.augmented_test:
            file_prefix = f"fold{args.fold}_augmented"
        else:
            file_prefix = f"fold{args.fold}"
    
    # Add ablation identifier if provided
    if args.ablation_id:
        file_prefix = f"{file_prefix}_ablation_{args.ablation_id}"
    
    # Run evaluation
    results = evaluate_top_k_accuracy(
        test_df=test_df,
        target_df=target_df,
        model=model,
        batch_size=args.batch_size,
        augmented_test=args.augmented_test,
        max_samples=args.max_samples
    )
    
    # Add fold information to results
    results['fold'] = args.fold
    
    # Save results to CSV
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Create output filename
    file_name_parts = [file_prefix]
    results_file = os.path.join(args.output_dir, '_'.join(file_name_parts) + '.csv')
    
    # Save results
    pd.DataFrame([results]).to_csv(results_file, index=False)
    print(f"Results saved to {results_file}")
    
    # End time
    end_time = time.time()
    print(f"Evaluation completed in {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    main() 