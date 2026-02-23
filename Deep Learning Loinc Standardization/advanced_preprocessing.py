import pandas as pd
import numpy as np
from sklearn.model_selection import StratifiedKFold, KFold
from sklearn.utils import shuffle
from collections import Counter
import os
import tensorflow as tf
from process_loinc import process_loinc_data
from process_mimic import process_mimic_data
from data_augmentation import augment_text
import random

# Set random seed for reproducibility
np.random.seed(42)
tf.random.set_seed(42)

def get_full_loinc_dataset(lab_clinical_only=True):
    """
    Process the full LOINC dataset or filter for laboratory and clinical categories.
    
    Args:
        lab_clinical_only (bool): If True, filter for laboratory and clinical categories
    
    Returns:
        pd.DataFrame: Processed LOINC dataset
    """
    print("Processing full LOINC dataset...")
    
    # Load LOINC.csv into a pandas DataFrame
    loinc_df = pd.read_csv('Loinc.csv', quotechar='"', encoding='utf-8', low_memory=False)
    
    # If specified, filter for laboratory and clinical categories
    if lab_clinical_only:
        # The CLASS field contains the category - we need to identify labs and clinical observations
        # Example lab classes: CHEM, HEM/BC, MICRO, etc.
        # Example clinical classes: CLINRISK, PANEL.CV, PANEL.PULM, etc.
        
        # Find lab and clinical classes in CLASS column - this is a simplified approach
        # A more precise approach would use the official LOINC class mappings
        lab_clinical_classes = ['CHEM', 'HEM', 'MICRO', 'SERO', 'PANEL', 'CLIN', 'LAB', 'DRUG']
        
        class_filter = False
        for lab_class in lab_clinical_classes:
            class_filter = class_filter | loinc_df['CLASS'].str.contains(lab_class, na=False)
        
        loinc_df = loinc_df[class_filter]
        print(f"Filtered for laboratory and clinical categories: {loinc_df.shape[0]} records")
    
    # Select the same columns as in process_loinc.py
    columns_to_keep = ['LOINC_NUM', 'LONG_COMMON_NAME', 'SHORTNAME', 'DisplayName', 'RELATEDNAMES2']
    loinc_df = loinc_df[columns_to_keep]
    
    # Handle missing/NaN values in the text columns (replace with empty strings)
    text_columns = ['LONG_COMMON_NAME', 'SHORTNAME', 'DisplayName', 'RELATEDNAMES2']
    loinc_df[text_columns] = loinc_df[text_columns].fillna('')
    
    # Convert all text columns to lowercase as per the paper
    for col in text_columns:
        loinc_df[col] = loinc_df[col].str.lower()
    
    # Save the processed DataFrame
    loinc_df.to_csv('loinc_full_processed.csv', index=False)
    
    print(f"Processed full LOINC data saved to 'loinc_full_processed.csv'")
    print(f"Number of unique LOINC codes: {loinc_df['LOINC_NUM'].nunique()}")
    
    return loinc_df

def get_most_common_loinc_codes(n=2000):
    """
    Get the n most common LOINC codes based on frequency data.
    
    Args:
        n (int): Number of most common LOINC codes to retrieve
    
    Returns:
        list: List of the n most common LOINC codes
    """
    # Since we don't have actual frequency data, we'll simulate it for this example
    # In a real implementation, you would use frequency data from a reliable source
    
    # Load the full LOINC dataset
    loinc_df = pd.read_csv('Loinc.csv', quotechar='"', encoding='utf-8', low_memory=False)
    
    # For simulation: use the order of LOINCs in the file as a proxy for frequency
    # In a real implementation, you would have actual usage statistics
    common_loinc_codes = loinc_df['LOINC_NUM'].iloc[:n].tolist()
    
    print(f"Retrieved {len(common_loinc_codes)} most common LOINC codes")
    return common_loinc_codes

def create_stratified_folds(mimic_pairs_df, n_folds=5):
    """
    Create stratified folds for cross-validation, handling cases where some classes have fewer samples than n_folds.
    
    Args:
        mimic_pairs_df (pd.DataFrame): DataFrame with source-target pairs
        n_folds (int): Number of folds for cross-validation
    
    Returns:
        list: List of (train_indices, val_indices, test_indices) for each fold
    """
    print(f"Creating {n_folds} stratified folds for cross-validation...")
    
    # Check the frequency of each target_loinc
    target_counts = Counter(mimic_pairs_df['target_loinc'])
    print(f"Found {len(target_counts)} unique LOINC targets")
    
    # Check if all classes have at least n_folds samples
    all_sufficient = all(count >= n_folds for count in target_counts.values())
    
    if all_sufficient:
        print("All target classes have sufficient samples for stratified folding")
        # Use stratified k-fold
        skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
        
        # Get y values for stratification (target_loinc)
        y = mimic_pairs_df['target_loinc'].values
        
        folds = []
        for train_val_idx, test_idx in skf.split(np.zeros(len(y)), y):
            # Further split train_val into train and validation
            # Get the stratified split indices for the training and validation sets
            train_val_y = y[train_val_idx]
            train_idx_inner, val_idx_inner = next(StratifiedKFold(n_splits=10, shuffle=True, random_state=42).split(
                np.zeros(len(train_val_y)), train_val_y))
            
            # Convert inner indices to original indices
            train_idx = train_val_idx[train_idx_inner]
            val_idx = train_val_idx[val_idx_inner]
            
            folds.append((train_idx, val_idx, test_idx))
    else:
        print(f"Some target classes have fewer than {n_folds} samples. Using an alternative approach.")
        
        # Alternative approach: Handle rare classes separately
        
        # 1. Identify frequent and rare classes
        frequent_classes = [loinc for loinc, count in target_counts.items() if count >= n_folds]
        rare_classes = [loinc for loinc, count in target_counts.items() if count < n_folds]
        
        print(f"Frequent classes (>= {n_folds} samples): {len(frequent_classes)}")
        print(f"Rare classes (< {n_folds} samples): {len(rare_classes)}")
        
        # 2. Create indices for frequent and rare samples
        frequent_indices = mimic_pairs_df[mimic_pairs_df['target_loinc'].isin(frequent_classes)].index.tolist()
        rare_indices = mimic_pairs_df[mimic_pairs_df['target_loinc'].isin(rare_classes)].index.tolist()
        
        # 3. Apply stratified folding to frequent classes
        frequent_df = mimic_pairs_df.loc[frequent_indices]
        if len(frequent_df) > 0:
            skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
            y_frequent = frequent_df['target_loinc'].values
            frequent_folds = list(skf.split(np.zeros(len(y_frequent)), y_frequent))
        else:
            frequent_folds = [([], []) for _ in range(n_folds)]
        
        # 4. Distribute rare classes randomly but evenly across folds
        np.random.shuffle(rare_indices)
        rare_fold_indices = [[] for _ in range(n_folds)]
        for i, idx in enumerate(rare_indices):
            fold_idx = i % n_folds
            rare_fold_indices[fold_idx].append(idx)
        
        # 5. Combine frequent and rare indices for each fold
        folds = []
        for i in range(n_folds):
            # Get test indices for this fold
            if len(frequent_folds[i][1]) > 0:
                frequent_test_indices = [frequent_indices[idx] for idx in frequent_folds[i][1]]
            else:
                frequent_test_indices = []
            rare_test_indices = rare_fold_indices[i]
            test_idx = np.array(frequent_test_indices + rare_test_indices)
            
            # All other indices go to train/val
            all_indices = set(range(len(mimic_pairs_df)))
            train_val_idx = np.array(list(all_indices - set(test_idx)))
            
            # Split train_val into train and validation (90/10 split)
            np.random.shuffle(train_val_idx)
            val_size = len(train_val_idx) // 10
            val_idx = train_val_idx[:val_size]
            train_idx = train_val_idx[val_size:]
            
            folds.append((train_idx, val_idx, test_idx))
    
    # Print fold information
    for i, (train_idx, val_idx, test_idx) in enumerate(folds):
        print(f"Fold {i+1}: {len(train_idx)} train, {len(val_idx)} validation, {len(test_idx)} test samples")
    
    # Save fold indices to disk
    # np.save('stratified_folds.npy', folds)
    # Save each fold separately to handle potential shape issues
    for i, fold in enumerate(folds):
        fold_dir = 'stratified_folds'
        os.makedirs(fold_dir, exist_ok=True)
        np.save(f'{fold_dir}/fold_{i+1}_train.npy', fold[0])
        np.save(f'{fold_dir}/fold_{i+1}_val.npy', fold[1])
        np.save(f'{fold_dir}/fold_{i+1}_test.npy', fold[2])
    print(f"Stratified folds saved to 'stratified_folds/' directory")
    
    return folds

def generate_triplets(df, loinc_field='target_loinc', text_field='source_text', n_triplets=1000):
    """
    Generate triplets for contrastive learning.
    
    Args:
        df (pd.DataFrame): DataFrame with LOINC codes and text representations
        loinc_field (str): Field containing LOINC codes
        text_field (str): Field containing text representations
        n_triplets (int): Number of triplets to generate
    
    Returns:
        list: List of (anchor, positive, negative) triplets
    """
    # Group by LOINC code
    grouped = df.groupby(loinc_field)
    
    # Filter groups with at least 2 samples
    valid_groups = [group for name, group in grouped if len(group) >= 2]
    
    if len(valid_groups) < 2:
        print("Warning: Need at least 2 groups with 2+ samples each to form triplets")
        print(f"Found {len(valid_groups)} valid groups. Generating fewer triplets or augmenting data further.")
        n_triplets = min(n_triplets, len(valid_groups) * 10) if valid_groups else 0
    
    triplets = []
    for _ in range(n_triplets):
        if not valid_groups:
            break
            
        # Randomly select two different LOINC groups
        if len(valid_groups) >= 2:
            # Use manual random selection instead of np.random.choice
            indices = list(range(len(valid_groups)))
            random.shuffle(indices)
            anchor_idx, negative_idx = indices[0], indices[1]
            anchor_group = valid_groups[anchor_idx]
            negative_group = valid_groups[negative_idx]
        else:
            # If only one valid group, duplicate it and create more diverse samples
            anchor_group = valid_groups[0]
            negative_group = valid_groups[0]
            # Skip if we can't create a valid triplet
            if len(anchor_group) < 3:
                continue
        
        # For the anchor group, select two different samples
        anchor_idx = np.random.choice(len(anchor_group), size=1)[0]
        anchor_text = anchor_group.iloc[anchor_idx][text_field]
        
        # Select a different sample for positive
        positive_candidates = list(range(len(anchor_group)))
        if anchor_idx in positive_candidates:
            positive_candidates.remove(anchor_idx)
        
        if not positive_candidates:
            continue
            
        positive_idx = np.random.choice(positive_candidates)
        positive_text = anchor_group.iloc[positive_idx][text_field]
        
        # For the negative group, select one sample
        # If anchor_group and negative_group are the same, ensure the negative is different
        if anchor_group is negative_group:
            negative_candidates = list(range(len(negative_group)))
            if anchor_idx in negative_candidates:
                negative_candidates.remove(anchor_idx)
            if positive_idx in negative_candidates:
                negative_candidates.remove(positive_idx)
            
            if not negative_candidates:
                continue
                
            negative_idx = np.random.choice(negative_candidates)
        else:
            negative_idx = np.random.choice(len(negative_group))
        
        negative_text = negative_group.iloc[negative_idx][text_field]
        
        triplets.append((anchor_text, positive_text, negative_text))
    
    return triplets

def generate_stage1_triplets(loinc_df, n_triplets=10000):
    """
    Generate triplets for Stage 1 training (target-only).
    
    Args:
        loinc_df (pd.DataFrame): DataFrame with LOINC data
        n_triplets (int): Number of triplets to generate
    
    Returns:
        list: List of (anchor, positive, negative) triplets
    """
    print(f"Generating {n_triplets} triplets for Stage 1 training...")
    
    # Create a DataFrame with augmented examples
    augmented_data = []
    
    # Limit processing to a sample of LOINC codes for demonstration
    sample_size = min(5000, len(loinc_df))
    loinc_sample = loinc_df.sample(sample_size)
    
    print(f"Augmenting {sample_size} LOINC codes...")
    
    # Create augmented examples for each LOINC code
    for idx, (_, row) in enumerate(loinc_sample.iterrows()):
        if idx % 1000 == 0 and idx > 0:
            print(f"Processed {idx} LOINC codes...")
            
        loinc_num = row['LOINC_NUM']
        
        # Create text representations using different fields
        text_representations = []
        
        # Add the original text representations
        if row['LONG_COMMON_NAME']:
            text_representations.append(row['LONG_COMMON_NAME'])
        if row['SHORTNAME']:
            text_representations.append(row['SHORTNAME'])
        if row['DisplayName']:
            text_representations.append(row['DisplayName'])
        
        # Create combined related terms
        related_terms = row['RELATEDNAMES2']
        
        # Generate augmented examples for each text representation
        for text in text_representations:
            # Create 3 augmented versions of each text
            augmented = augment_text(text, related_terms, num_augmentations=3)
            for aug_text in augmented:
                augmented_data.append({
                    'LOINC_NUM': loinc_num,
                    'text_representation': aug_text
                })
    
    # Create DataFrame from augmented data
    aug_df = pd.DataFrame(augmented_data)
    
    # Save the augmented data
    aug_df.to_csv('stage1_augmented_data.csv', index=False)
    print(f"Generated {len(aug_df)} augmented examples for {aug_df['LOINC_NUM'].nunique()} LOINC codes")
    
    # Generate triplets
    triplets = generate_triplets(aug_df, loinc_field='LOINC_NUM', text_field='text_representation', n_triplets=n_triplets)
    
    # Save triplets to disk
    with open('stage1_triplets.txt', 'w') as f:
        for anchor, positive, negative in triplets:
            f.write(f"{anchor}|{positive}|{negative}\n")
    
    print(f"Generated {len(triplets)} triplets for Stage 1 and saved to 'stage1_triplets.txt'")
    
    return triplets

def generate_stage2_triplets(mimic_pairs_df, loinc_df, fold_indices, n_triplets_per_fold=5000):
    """
    Generate triplets for Stage 2 training (source-target pairs) for each fold.
    
    Args:
        mimic_pairs_df (pd.DataFrame): DataFrame with source-target pairs
        loinc_df (pd.DataFrame): DataFrame with LOINC data
        fold_indices (list): List of (train_indices, val_indices, test_indices) for each fold
        n_triplets_per_fold (int): Number of triplets to generate per fold
    
    Returns:
        dict: Dictionary with triplets for each fold
    """
    print(f"Generating triplets for Stage 2 training...")
    
    all_fold_triplets = {}
    
    for fold_idx, (train_idx, val_idx, test_idx) in enumerate(fold_indices):
        print(f"Processing fold {fold_idx+1}/{len(fold_indices)}...")
        
        # Get training data for this fold
        train_df = mimic_pairs_df.iloc[train_idx].copy()
        
        # Augment the training data
        augmented_data = []
        
        for _, row in train_df.iterrows():
            source_text = row['source_text']
            target_loinc = row['target_loinc']
            
            # Get related terms for this LOINC code if available
            related_terms = ""
            loinc_info = loinc_df[loinc_df['LOINC_NUM'] == target_loinc]
            if not loinc_info.empty:
                related_terms = loinc_info.iloc[0]['RELATEDNAMES2']
            
            # Generate augmented examples
            augmented_examples = augment_text(source_text, related_terms, num_augmentations=5)
            
            for aug_text in augmented_examples:
                augmented_data.append({
                    'source_text': aug_text,
                    'target_loinc': target_loinc
                })
        
        # Create DataFrame from augmented data
        aug_train_df = pd.DataFrame(augmented_data)
        
        # Save the augmented training data for this fold
        aug_train_df.to_csv(f'stage2_fold{fold_idx+1}_train_augmented.csv', index=False)
        print(f"Generated {len(aug_train_df)} augmented examples for fold {fold_idx+1}")
        
        # Generate triplets for this fold
        triplets = generate_triplets(aug_train_df, loinc_field='target_loinc', text_field='source_text', 
                                   n_triplets=n_triplets_per_fold)
        
        # Save triplets to disk
        with open(f'stage2_fold{fold_idx+1}_triplets.txt', 'w') as f:
            for anchor, positive, negative in triplets:
                f.write(f"{anchor}|{positive}|{negative}\n")
        
        print(f"Generated {len(triplets)} triplets for fold {fold_idx+1}")
        
        all_fold_triplets[fold_idx] = triplets
    
    return all_fold_triplets

def expand_target_pool_for_type2_testing(mimic_pairs_df, n_common_loinc=2000):
    """
    Expand the target pool with the most common LOINC codes for Type-2 generalization testing.
    
    Args:
        mimic_pairs_df (pd.DataFrame): DataFrame with source-target pairs
        n_common_loinc (int): Number of most common LOINC codes to add
    
    Returns:
        set: Set of expanded target LOINCs
    """
    print(f"Expanding target pool for Type-2 generalization testing...")
    
    # Get existing target LOINCs
    existing_loincs = set(mimic_pairs_df['target_loinc'].unique())
    print(f"Original target pool size: {len(existing_loincs)} LOINC codes")
    
    # Get most common LOINC codes
    common_loincs = get_most_common_loinc_codes(n=n_common_loinc)
    
    # Add to existing LOINCs
    expanded_loincs = existing_loincs.union(common_loincs)
    print(f"Expanded target pool size: {len(expanded_loincs)} LOINC codes")
    
    # Save expanded target pool
    with open('expanded_target_pool.txt', 'w') as f:
        for loinc in expanded_loincs:
            f.write(f"{loinc}\n")
    
    print(f"Expanded target pool saved to 'expanded_target_pool.txt'")
    
    return expanded_loincs

def l2_normalize_embeddings(embeddings):
    """
    Apply L2 normalization to embeddings.
    
    Args:
        embeddings (np.ndarray): Embeddings to normalize
    
    Returns:
        np.ndarray: L2-normalized embeddings
    """
    # This is a placeholder showing how to implement L2 normalization
    # In actual implementation, this would be part of the TensorFlow model
    norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
    return embeddings / norm

def main():
    # Activate virtual environment
    print("Make sure to run 'source 598_env/bin/activate' before executing this script")
    
    print("\n" + "="*80)
    print("STEP 1: Process full LOINC dataset for first-stage fine-tuning")
    print("="*80)
    # Get full LOINC dataset for first-stage fine-tuning
    loinc_full_df = get_full_loinc_dataset(lab_clinical_only=True)
    
    print("\n" + "="*80)
    print("STEP 2: Process MIMIC-III dataset for second-stage fine-tuning")
    print("="*80)
    # Process MIMIC-III data
    mimic_pairs_df = process_mimic_data()
    
    print("\n" + "="*80)
    print("STEP 3: Create stratified folds for cross-validation")
    print("="*80)
    # Create stratified folds for cross-validation
    fold_indices = create_stratified_folds(mimic_pairs_df, n_folds=5)
    
    print("\n" + "="*80)
    print("STEP 4: Generate triplets for Stage 1 training (target-only)")
    print("="*80)
    # Generate triplets for Stage 1 training
    stage1_triplets = generate_stage1_triplets(loinc_full_df, n_triplets=10000)
    
    print("\n" + "="*80)
    print("STEP 5: Generate triplets for Stage 2 training (source-target pairs)")
    print("="*80)
    # Generate triplets for Stage 2 training
    stage2_triplets = generate_stage2_triplets(mimic_pairs_df, loinc_full_df, fold_indices, n_triplets_per_fold=5000)
    
    print("\n" + "="*80)
    print("STEP 6: Expand target pool for Type-2 generalization testing")
    print("="*80)
    # Expand target pool for Type-2 generalization testing
    expanded_loincs = expand_target_pool_for_type2_testing(mimic_pairs_df, n_common_loinc=2000)
    
    print("\n" + "="*80)
    print("Summary of Advanced Preprocessing")
    print("="*80)
    print("1. Processed full LOINC dataset for first-stage fine-tuning")
    print("2. Created 5-fold stratified cross-validation splits")
    print("3. Generated triplets for contrastive learning:")
    print(f"   - Stage 1: {len(stage1_triplets)} triplets for target-only fine-tuning")
    print(f"   - Stage 2: {sum(len(triplets) for triplets in stage2_triplets.values())} triplets across 5 folds")
    print(f"4. Expanded target pool from {len(mimic_pairs_df['target_loinc'].unique())} to {len(expanded_loincs)} LOINC codes")
    print("5. L2 normalization function prepared for embedding normalization")
    print("\nAll preprocessing steps completed successfully. The data is now ready for model implementation.")

if __name__ == "__main__":
    main() 