import pandas as pd
import numpy as np
import os

# Set random seed for reproducibility
np.random.seed(42)

def process_loinc_data():
    print("Processing LOINC.csv file...")
    
    # Load LOINC.csv into a pandas DataFrame
    # Handle potential quoting issues in CSV
    loinc_df = pd.read_csv('Loinc.csv', quotechar='"', encoding='utf-8', low_memory=False)
    
    print(f"Original LOINC dataframe shape: {loinc_df.shape}")
    
    # Identify unique LOINC_NUM values
    unique_loinc_codes = loinc_df['LOINC_NUM'].unique()
    print(f"Number of unique LOINC codes: {len(unique_loinc_codes)}")
    
    # Randomly sample 10% of these unique LOINC_NUM values
    sample_size = int(len(unique_loinc_codes) * 0.1)
    sampled_loinc_codes = np.random.choice(unique_loinc_codes, size=sample_size, replace=False)
    print(f"Randomly sampled {len(sampled_loinc_codes)} LOINC codes (10%)")
    
    # Filter the original DataFrame to keep only rows with the sampled LOINC_NUM values
    loinc_targets_df = loinc_df[loinc_df['LOINC_NUM'].isin(sampled_loinc_codes)]
    print(f"Sampled LOINC dataframe shape: {loinc_targets_df.shape}")
    
    # Select the specified columns from the paper, now including SCALE_TYP
    columns_to_keep = ['LOINC_NUM', 'LONG_COMMON_NAME', 'SHORTNAME', 'DisplayName', 'RELATEDNAMES2', 'SCALE_TYP']
    loinc_targets_df = loinc_targets_df[columns_to_keep]
    
    # Handle missing/NaN values in the text columns (replace with empty strings)
    text_columns = ['LONG_COMMON_NAME', 'SHORTNAME', 'DisplayName', 'RELATEDNAMES2']
    loinc_targets_df[text_columns] = loinc_targets_df[text_columns].fillna('')
    
    # Convert all text columns to lowercase as per the paper
    for col in text_columns:
        loinc_targets_df[col] = loinc_targets_df[col].str.lower()
    
    # Save the processed DataFrame
    loinc_targets_df.to_csv('loinc_targets_processed.csv', index=False)
    
    print(f"Processed LOINC data saved to 'loinc_targets_processed.csv'")
    print(f"Number of unique LOINC codes in sample: {loinc_targets_df['LOINC_NUM'].nunique()}")
    
    # Display the first 5 rows of the processed DataFrame
    print("\nFirst 5 rows of the processed LOINC targets DataFrame:")
    print(loinc_targets_df.head())
    
    return loinc_targets_df

if __name__ == "__main__":
    loinc_targets_df = process_loinc_data() 