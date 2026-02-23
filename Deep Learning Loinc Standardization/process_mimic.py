import pandas as pd
import numpy as np
import os

def process_mimic_data():
    print("Processing D_LABITEMS.csv file...")
    
    # Load D_LABITEMS.csv into a pandas DataFrame
    # Handle potential quoting issues in CSV
    mimic_df = pd.read_csv('D_LABITEMS.csv', quotechar='"', encoding='utf-8')
    
    print(f"Original MIMIC-III dataframe shape: {mimic_df.shape}")
    
    # Filter rows where 'LOINC_CODE' is present and not empty/null
    loinc_mask = mimic_df['LOINC_CODE'].notna() & (mimic_df['LOINC_CODE'] != '')
    
    # Create a fresh DataFrame copy to avoid the SettingWithCopyWarning
    mimic_df_with_loinc = mimic_df[loinc_mask].copy()
    print(f"MIMIC-III rows with LOINC codes: {mimic_df_with_loinc.shape}")
    
    # Handle potential NaN values in 'LABEL' or 'FLUID' by replacing with empty strings
    mimic_df_with_loinc.loc[:, 'LABEL'] = mimic_df_with_loinc['LABEL'].fillna('')
    mimic_df_with_loinc.loc[:, 'FLUID'] = mimic_df_with_loinc['FLUID'].fillna('')
    
    # Create source_text column by concatenating 'LABEL' and 'FLUID', separated by a space
    mimic_df_with_loinc.loc[:, 'source_text'] = (
        mimic_df_with_loinc['LABEL'] + ' ' + mimic_df_with_loinc['FLUID']
    ).str.strip()
    
    # Convert source_text to lowercase
    mimic_df_with_loinc.loc[:, 'source_text'] = mimic_df_with_loinc['source_text'].str.lower()
    
    # Select the required columns and rename 'LOINC_CODE' to 'target_loinc'
    mimic_pairs_df = mimic_df_with_loinc[['ITEMID', 'source_text', 'LOINC_CODE']].copy()
    mimic_pairs_df = mimic_pairs_df.rename(columns={'LOINC_CODE': 'target_loinc'})
    
    # Save the processed DataFrame
    mimic_pairs_df.to_csv('mimic_pairs_processed.csv', index=False)
    
    print(f"Processed MIMIC-III data saved to 'mimic_pairs_processed.csv'")
    print(f"Number of source-target pairs found: {len(mimic_pairs_df)}")
    print(f"Number of unique LOINC targets in MIMIC: {mimic_pairs_df['target_loinc'].nunique()}")
    
    # Display the first 5 rows of the processed DataFrame
    print("\nFirst 5 rows of the processed MIMIC pairs DataFrame:")
    print(mimic_pairs_df.head())
    
    return mimic_pairs_df

if __name__ == "__main__":
    mimic_pairs_df = process_mimic_data() 