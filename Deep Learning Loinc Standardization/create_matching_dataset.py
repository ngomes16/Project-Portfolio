#!/usr/bin/env python
"""
Create matching LOINC target datasets for evaluation

This script creates LOINC target datasets for evaluation that include all the LOINC codes 
from the test data to ensure proper evaluation.
"""
import os
import pandas as pd
import numpy as np
from tqdm import tqdm
import random

def main():
    # Paths
    mimic_file = 'output/mimic_pairs_processed.csv'
    loinc_file = 'output/loinc_targets_processed.csv'
    output_file = 'output/evaluation_loinc_targets.csv'
    expanded_output_file = 'output/expanded_target_pool.csv'
    
    # Create output directory if needed
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Load test data with LOINC codes
    print(f"Loading test data from {mimic_file}...")
    test_df = pd.read_csv(mimic_file)
    test_loinc_codes = test_df['LOINC_NUM'].unique().tolist()
    print(f"Found {len(test_loinc_codes)} unique LOINC codes in test data")
    
    # Load current LOINC target data
    print(f"Loading LOINC target data from {loinc_file}...")
    loinc_df = pd.read_csv(loinc_file)
    
    # Create mapping between test LOINC codes and descriptions
    loinc_descriptions = {}
    for _, row in test_df.iterrows():
        loinc_code = row['LOINC_NUM']
        if loinc_code not in loinc_descriptions:
            loinc_descriptions[loinc_code] = row['TARGET']
    
    # Create new target dataset
    output_data = []
    
    # First, add all the test LOINC codes to ensure they're included
    print("Adding test LOINC codes to target dataset...")
    for loinc_code in test_loinc_codes:
        description = loinc_descriptions.get(loinc_code, f"LOINC code {loinc_code}")
        output_data.append({
            'LOINC_NUM': loinc_code,
            'LONG_COMMON_NAME': description,
            'SHORTNAME': description.split('[')[0].strip() if '[' in description else description,
            'DisplayName': description.split('[')[0].strip() if '[' in description else description,
            'RELATEDNAMES2': ''
        })
    
    # Then, add some from the current LOINC dataset to reach ~100 codes
    # This represents roughly 20% of the 571 unique LOINC codes mentioned in the paper
    target_count = 100
    remain_count = target_count - len(test_loinc_codes)
    
    print(f"Adding {remain_count} more LOINC codes to reach {target_count} total codes...")
    if remain_count > 0 and not loinc_df.empty:
        # Add remaining LOINC codes from the dataset
        additional_codes = min(remain_count, len(loinc_df))
        for i in range(additional_codes):
            row = loinc_df.iloc[i]
            output_data.append({
                'LOINC_NUM': row['LOINC_NUM'],
                'LONG_COMMON_NAME': row.get('LONG_COMMON_NAME', f"LOINC code {row['LOINC_NUM']}"),
                'SHORTNAME': row.get('SHORTNAME', ''),
                'DisplayName': row.get('DisplayName', ''),
                'RELATEDNAMES2': row.get('RELATEDNAMES2', '')
            })
    
    # Save the new target dataset
    output_df = pd.DataFrame(output_data)
    output_df.to_csv(output_file, index=False)
    print(f"Saved {len(output_df)} LOINC codes to {output_file}")
    
    # Create expanded target pool (adds more codes to simulate the expanded pool in the paper)
    # The paper used 2,313 unique LOINC codes (571 + top 2,000 common LOINCs)
    # We'll simulate this by using ~20% of that: ~460 codes
    expanded_target_count = 460
    additional_expanded_count = expanded_target_count - len(output_df)
    
    print(f"Creating expanded target pool with {expanded_target_count} codes...")
    expanded_data = output_data.copy()
    
    # Generate synthetic LOINC codes if needed
    if additional_expanded_count > 0:
        base_codes = [str(10000 + i) for i in range(additional_expanded_count)]
        
        for code in base_codes:
            # Generate a random digit 0-9 for the check digit
            check_digit = random.randint(0, 9)
            synthetic_loinc = f"{code}-{check_digit}"
            
            expanded_data.append({
                'LOINC_NUM': synthetic_loinc,
                'LONG_COMMON_NAME': f"Synthetic LOINC code {synthetic_loinc}",
                'SHORTNAME': f"Synthetic {synthetic_loinc}",
                'DisplayName': f"Synthetic {synthetic_loinc}",
                'RELATEDNAMES2': ''
            })
    
    # Save the expanded target pool
    expanded_df = pd.DataFrame(expanded_data)
    expanded_df.to_csv(expanded_output_file, index=False)
    print(f"Saved {len(expanded_df)} LOINC codes to {expanded_output_file}")
    
    # Also create a simple version with just the LOINC codes for the expanded target pool
    expanded_df[['LOINC_NUM']].to_csv('output/expanded_target_pool.txt', index=False)
    print(f"Saved LOINC code list to output/expanded_target_pool.txt")

if __name__ == "__main__":
    main() 