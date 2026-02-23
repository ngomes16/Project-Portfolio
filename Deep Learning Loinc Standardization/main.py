import pandas as pd
import numpy as np
import os
from process_loinc import process_loinc_data
from process_mimic import process_mimic_data

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
    print("STEP 3: Analysis of Processed Data")
    print("="*80)
    
    # Check overlap between MIMIC LOINC codes and sampled LOINC codes
    mimic_loinc_codes = set(mimic_pairs_df['target_loinc'].unique())
    sampled_loinc_codes = set(loinc_targets_df['LOINC_NUM'].unique())
    common_loinc_codes = mimic_loinc_codes.intersection(sampled_loinc_codes)
    
    print(f"Total unique LOINC codes in MIMIC: {len(mimic_loinc_codes)}")
    print(f"Total unique LOINC codes in our 10% sample: {len(sampled_loinc_codes)}")
    print(f"LOINC codes present in both datasets: {len(common_loinc_codes)}")
    print(f"Percentage of MIMIC LOINC codes covered by our sample: {len(common_loinc_codes)/len(mimic_loinc_codes)*100:.2f}%")
    
    # Example of a source-target pair from MIMIC
    if not mimic_pairs_df.empty:
        print("\nExample of a source-target pair from MIMIC:")
        example_pair = mimic_pairs_df.iloc[0]
        print(f"Source text: '{example_pair['source_text']}'")
        print(f"Target LOINC: '{example_pair['target_loinc']}'")
        
        # If the target LOINC is in our sample, show its text representations
        if example_pair['target_loinc'] in sampled_loinc_codes:
            example_loinc = loinc_targets_df[loinc_targets_df['LOINC_NUM'] == example_pair['target_loinc']].iloc[0]
            print("\nCorresponding LOINC text representations:")
            print(f"LONG_COMMON_NAME: '{example_loinc['LONG_COMMON_NAME']}'")
            print(f"SHORTNAME: '{example_loinc['SHORTNAME']}'")
            print(f"DisplayName: '{example_loinc['DisplayName']}'")
            print(f"RELATEDNAMES2: '{example_loinc['RELATEDNAMES2']}'")
    
    print("\n" + "="*80)
    print("STEP 4: Data Ready for Modeling")
    print("="*80)
    print("The processed datasets can now be used for:")
    print("1. First-stage fine-tuning using only the target codes (loinc_targets_df)")
    print("2. Second-stage fine-tuning using source-target pairs (mimic_pairs_df)")
    print("As described in the LOINC standardization paper's methodology")

if __name__ == "__main__":
    main() 