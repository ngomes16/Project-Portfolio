import pandas as pd
import numpy as np
import os
from process_loinc import process_loinc_data
from process_mimic import process_mimic_data
from data_augmentation import augment_text

def main():
    # Activate virtual environment
    print("Make sure to run 'source 598_env/bin/activate' before executing this script")
    
    print("\n" + "="*80)
    print("STEP 1: Process LOINC.csv to create target-only dataset (loinc_targets_df)")
    print("="*80)
    loinc_targets_df = process_loinc_data()
    
    print("\n" + "="*80)
    print("STEP 2: Process D_LABITEMS.csv to create source-target pairs (mimic_pairs_df)")
    print("="*80)
    mimic_pairs_df = process_mimic_data()
    
    print("\n" + "="*80)
    print("STEP 3: Apply Data Augmentation")
    print("="*80)
    
    # Example of augmenting LOINC targets
    print("Augmenting LOINC targets example:")
    
    # Select a random LOINC target
    if not loinc_targets_df.empty:
        sample_loinc = loinc_targets_df.sample(1).iloc[0]
        loinc_num = sample_loinc['LOINC_NUM']
        
        # Get the text representations
        long_name = sample_loinc['LONG_COMMON_NAME']
        short_name = sample_loinc['SHORTNAME']
        display_name = sample_loinc['DisplayName']
        related_names = sample_loinc['RELATEDNAMES2']
        
        # Combine all names for the related terms
        combined_related = '; '.join([short_name, display_name, related_names])
        
        print(f"\nLOINC Code: {loinc_num}")
        print(f"Long Common Name: {long_name}")
        print(f"Related Names: {combined_related}")
        
        # Generate augmented examples
        augmented_examples = augment_text(long_name, combined_related, num_augmentations=5)
        
        print("\nAugmented LOINC Target Examples:")
        for i, example in enumerate(augmented_examples, 1):
            print(f"{i}. {example}")
    
    # Example of augmenting MIMIC source-target pairs
    print("\nAugmenting MIMIC source-target pairs example:")
    
    # Select a random MIMIC source-target pair
    if not mimic_pairs_df.empty:
        sample_mimic = mimic_pairs_df.sample(1).iloc[0]
        source_text = sample_mimic['source_text']
        target_loinc = sample_mimic['target_loinc']
        
        # Get the corresponding LOINC target details if available
        target_details = loinc_targets_df[loinc_targets_df['LOINC_NUM'] == target_loinc]
        if not target_details.empty:
            target_details = target_details.iloc[0]
            related_names = target_details['RELATEDNAMES2']
        else:
            related_names = ""
        
        print(f"\nSource Text: {source_text}")
        print(f"Target LOINC: {target_loinc}")
        
        # Generate augmented examples for the source text
        augmented_source_examples = augment_text(source_text, related_names, num_augmentations=5)
        
        print("\nAugmented Source Text Examples:")
        for i, example in enumerate(augmented_source_examples, 1):
            print(f"{i}. {example}")
    
    print("\n" + "="*80)
    print("STEP 4: Create Stage 1 and Stage 2 Training Examples")
    print("="*80)
    
    # For Stage 1 (target-only training):
    # We create a dataset with multiple text representations of each LOINC code
    print("Stage 1 Training Data (Target-only):")
    stage1_data = []
    
    # Take a small subset for demonstration
    loinc_subset = loinc_targets_df.sample(min(5, len(loinc_targets_df)))
    
    for _, row in loinc_subset.iterrows():
        loinc_num = row['LOINC_NUM']
        long_name = row['LONG_COMMON_NAME']
        short_name = row['SHORTNAME']
        display_name = row['DisplayName']
        related_names = row['RELATEDNAMES2']
        
        # Create combined related terms
        combined_related = '; '.join([short_name, display_name, related_names])
        
        # Generate a few augmented examples
        augmented_examples = augment_text(long_name, combined_related, num_augmentations=3)
        
        # Add each augmented example with the LOINC code
        for example in augmented_examples:
            stage1_data.append({
                'LOINC_NUM': loinc_num,
                'text_representation': example
            })
    
    # Convert to DataFrame and save
    stage1_df = pd.DataFrame(stage1_data)
    stage1_df.to_csv('stage1_training_examples.csv', index=False)
    
    print(f"Created {len(stage1_df)} Stage 1 training examples from {len(loinc_subset)} LOINC codes")
    print("First few Stage 1 examples:")
    print(stage1_df.head())
    
    # For Stage 2 (source-target pairs):
    # We create a dataset with source-target pairs, where the source is augmented
    print("\nStage 2 Training Data (Source-Target pairs):")
    stage2_data = []
    
    # Take a small subset for demonstration
    mimic_subset = mimic_pairs_df.sample(min(5, len(mimic_pairs_df)))
    
    for _, row in mimic_subset.iterrows():
        source_text = row['source_text']
        target_loinc = row['target_loinc']
        
        # Try to find related names for this LOINC code
        target_details = loinc_targets_df[loinc_targets_df['LOINC_NUM'] == target_loinc]
        if not target_details.empty:
            related_names = target_details.iloc[0]['RELATEDNAMES2']
        else:
            related_names = ""
        
        # Generate augmented examples
        augmented_examples = augment_text(source_text, related_names, num_augmentations=3)
        
        # Add each augmented example with the target LOINC
        for example in augmented_examples:
            stage2_data.append({
                'source_text': example,
                'target_loinc': target_loinc
            })
    
    # Convert to DataFrame and save
    stage2_df = pd.DataFrame(stage2_data)
    stage2_df.to_csv('stage2_training_examples.csv', index=False)
    
    print(f"Created {len(stage2_df)} Stage 2 training examples from {len(mimic_subset)} source-target pairs")
    print("First few Stage 2 examples:")
    print(stage2_df.head())
    
    print("\n" + "="*80)
    print("Summary")
    print("="*80)
    print("1. Processed LOINC data with 10% random sampling")
    print("2. Processed MIMIC-III data for source-target pairs")
    print("3. Demonstrated data augmentation techniques")
    print("4. Created example training datasets for both stages")
    print("The data is now ready for model training as described in the paper.")

if __name__ == "__main__":
    main() 