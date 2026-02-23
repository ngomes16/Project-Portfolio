#!/usr/bin/env python
"""
Fix augmentation for LOINC standardization evaluation

This script creates properly augmented test data for Type-1 generalization testing.
It applies various augmentation techniques to the test data while maintaining the
ground truth LOINC codes.
"""
import pandas as pd
import numpy as np
import os
import sys
import argparse
import random
from tqdm import tqdm

# Add parent directory to path to import from other modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Character-level random deletion
def char_random_deletion(text, p=0.1):
    """Randomly remove characters from the text with probability p"""
    if not text or not isinstance(text, str):
        return text
        
    chars = list(text)
    # Don't delete too many characters
    i = 0
    while i < len(chars):
        if random.random() < p:
            chars.pop(i)
        else:
            i += 1
            
    # Don't return empty string
    if not chars:
        return text
        
    return ''.join(chars)

# Word-level random swapping
def word_random_swapping(text, max_swaps=2):
    """Randomly swap adjacent words in the text"""
    if not text or not isinstance(text, str):
        return text
        
    words = text.split()
    if len(words) <= 1:
        return text
        
    num_swaps = min(max_swaps, len(words) // 2)
    for _ in range(num_swaps):
        i = random.randint(0, len(words) - 2)
        words[i], words[i+1] = words[i+1], words[i]
        
    return ' '.join(words)

# Word-level random insertion
def word_random_insertion(text, related_terms=None, max_inserts=2):
    """Randomly insert words from related terms into the text"""
    if not text or not isinstance(text, str) or not related_terms:
        return text
        
    words = text.split()
    
    # Parse related terms into a list
    related_words = []
    if isinstance(related_terms, str):
        related_words = related_terms.split()
    elif isinstance(related_terms, list):
        for term in related_terms:
            if term and isinstance(term, str):
                related_words.extend(term.split())
    
    if not related_words:
        return text
        
    num_inserts = min(max_inserts, len(words))
    for _ in range(num_inserts):
        insert_pos = random.randint(0, len(words))
        insert_word = random.choice(related_words)
        words.insert(insert_pos, insert_word)
        
    return ' '.join(words)

# Dictionary of common medical acronyms
MEDICAL_ACRONYMS = {
    'hemoglobin': 'hgb',
    'hgb': 'hemoglobin',
    'white blood cell': 'wbc',
    'wbc': 'white blood cell',
    'platelet': 'plt',
    'plt': 'platelet',
    'sodium': 'na',
    'na': 'sodium',
    'potassium': 'k',
    'k': 'potassium',
    'carbon dioxide': 'co2',
    'co2': 'carbon dioxide',
    'calcium': 'ca',
    'ca': 'calcium',
    'chloride': 'cl',
    'cl': 'chloride',
    'glucose': 'gluc',
    'gluc': 'glucose',
    'blood urea nitrogen': 'bun',
    'bun': 'blood urea nitrogen',
    'creatinine': 'crea',
    'crea': 'creatinine',
    'alanine aminotransferase': 'alt',
    'alt': 'alanine aminotransferase',
    'aspartate aminotransferase': 'ast',
    'ast': 'aspartate aminotransferase',
    'alkaline phosphatase': 'alp',
    'alp': 'alkaline phosphatase',
    'total bilirubin': 'tbil',
    'tbil': 'total bilirubin',
    # Add more acronyms as needed
}

# Acronym substitution
def acronym_substitution(text):
    """Substitute words/phrases with their acronyms or vice versa"""
    if not text or not isinstance(text, str):
        return text
        
    # Check each key in the acronym dictionary
    result = text.lower()
    for phrase, acronym in MEDICAL_ACRONYMS.items():
        # Randomly decide whether to replace
        if random.random() < 0.5:
            # Use word boundaries to avoid partial replacements
            if phrase in result:
                result = result.replace(phrase, acronym)
            
    return result

def augment_text(text, num_augmentations=5):
    """
    Apply multiple augmentation techniques to create variations of the input text
    
    Args:
        text: Text string to augment
        num_augmentations: Number of augmented variants to create
        
    Returns:
        List of augmented texts
    """
    if not text or not isinstance(text, str):
        return [text] * num_augmentations
        
    augmented_texts = []
    
    # Add the original text
    augmented_texts.append(text)
    
    # Create additional variants
    for _ in range(num_augmentations - 1):
        # Apply a random sequence of augmentations
        augmented_text = text
        
        # Randomly apply each augmentation with 50% probability
        if random.random() < 0.5:
            augmented_text = char_random_deletion(augmented_text)
            
        if random.random() < 0.5:
            augmented_text = word_random_swapping(augmented_text)
            
        if random.random() < 0.5:
            # For word insertion, use the original text as related terms
            augmented_text = word_random_insertion(augmented_text, [text])
            
        if random.random() < 0.5:
            augmented_text = acronym_substitution(augmented_text)
            
        augmented_texts.append(augmented_text)
    
    # Ensure we return exactly num_augmentations texts
    while len(augmented_texts) < num_augmentations:
        # If we don't have enough, duplicate some
        augmented_texts.append(random.choice(augmented_texts))
    
    return augmented_texts[:num_augmentations]

def main():
    parser = argparse.ArgumentParser(description='Generate augmented test data for LOINC standardization evaluation')
    parser.add_argument('--test_file', type=str, default='output/mimic_pairs_processed.csv', 
                        help='Path to the test data CSV file')
    parser.add_argument('--output_file', type=str, default='output/mimic_pairs_augmented.csv',
                       help='Path to save the augmented test data')
    parser.add_argument('--num_augmentations', type=int, default=5,
                       help='Number of augmented samples to generate for each original sample')
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(args.output_file), exist_ok=True)
    
    # Load test data
    print(f"Loading test data from {args.test_file}...")
    try:
        test_df = pd.read_csv(args.test_file)
        print(f"Loaded {len(test_df)} test samples")
    except Exception as e:
        print(f"Error loading test data: {e}")
        return
    
    # Validate required columns
    required_columns = ['SOURCE', 'LOINC_NUM']
    missing_columns = [col for col in required_columns if col not in test_df.columns]
    if missing_columns:
        print(f"Test data is missing required columns: {missing_columns}")
        return
    
    # Create augmented samples
    print(f"Generating {args.num_augmentations} augmented samples for each test sample...")
    
    # Initialize lists for the augmented dataframe
    sources = []
    loinc_nums = []
    is_augmented = []
    
    # First, add all original samples
    for _, row in test_df.iterrows():
        sources.append(row['SOURCE'])
        loinc_nums.append(row['LOINC_NUM'])
        is_augmented.append(False)
    
    # Then, add augmented samples
    for i, row in tqdm(test_df.iterrows(), total=len(test_df), desc="Augmenting samples"):
        # Get augmented texts for this sample
        original_text = row['SOURCE']
        augmented_texts = augment_text(original_text, args.num_augmentations)
        
        # Skip the first one (it's the original) and add the rest
        for aug_text in augmented_texts[1:]:
            sources.append(aug_text)
            loinc_nums.append(row['LOINC_NUM'])
            is_augmented.append(True)
    
    # Create a new dataframe with augmented samples
    augmented_df = pd.DataFrame({
        'SOURCE': sources,
        'LOINC_NUM': loinc_nums,
        'is_augmented': is_augmented
    })
    
    # Add any other columns from the original dataframe
    for col in test_df.columns:
        if col not in ['SOURCE', 'LOINC_NUM']:
            # For original samples, copy the values
            values = []
            for i, is_aug in enumerate(is_augmented):
                if not is_aug:
                    # This is an original sample, copy the value
                    orig_idx = i % len(test_df)
                    values.append(test_df.iloc[orig_idx][col])
                else:
                    # This is an augmented sample, use NA or empty string
                    if pd.api.types.is_numeric_dtype(test_df[col]):
                        values.append(np.nan)
                    else:
                        values.append('')
            
            augmented_df[col] = values
    
    # Save augmented data
    print(f"Saving {len(augmented_df)} samples (including {len(test_df)} original samples) to {args.output_file}...")
    augmented_df.to_csv(args.output_file, index=False)
    print("Done!")

if __name__ == "__main__":
    main() 