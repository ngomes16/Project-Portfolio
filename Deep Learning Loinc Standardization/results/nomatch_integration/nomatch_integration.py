import pandas as pd
import numpy as np
import os
import argparse
import sys
import tensorflow as tf
from tqdm import tqdm
from sklearn.metrics import pairwise_distances

# Add parent directory to path to import from other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import model loading and embedding functions
from models.evaluation import load_model, compute_embeddings

def main():
    parser = argparse.ArgumentParser(description='LOINC standardization with no-match handling')
    parser.add_argument('--input_file', type=str, required=True,
                       help='Path to input CSV file with source texts')
    parser.add_argument('--loinc_file', type=str, required=True,
                       help='Path to LOINC targets CSV')
    parser.add_argument('--checkpoint_dir', type=str, default='models/checkpoints',
                       help='Directory containing model checkpoints')
    parser.add_argument('--fold', type=int, default=0,
                       help='Fold to use (0-based)')
    parser.add_argument('--output_dir', type=str, default='results/nomatch_integration',
                       help='Directory to save results')
    parser.add_argument('--threshold', type=float, default=-0.35,
                       help='Similarity threshold for mappable/unmappable decision')
    parser.add_argument('--top_k', type=int, default=5,
                       help='Number of top matches to return')
    parser.add_argument('--batch_size', type=int, default=16,
                       help='Batch size for inference')
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load input data
    print(f"Loading input data from {args.input_file}...")
    try:
        input_df = pd.read_csv(args.input_file)
        print(f"Loaded {len(input_df)} input samples")
    except Exception as e:
        print(f"Error loading input data: {e}")
        sys.exit(1)
    
    # Check for required columns
    required_columns = ['id', 'source_text']
    for col in required_columns:
        if col not in input_df.columns:
            # Try common alternatives
            if col == 'id' and 'ITEMID' in input_df.columns:
                input_df['id'] = input_df['ITEMID']
            elif col == 'source_text' and 'SOURCE' in input_df.columns:
                input_df['source_text'] = input_df['SOURCE']
            else:
                print(f"Error: Required column '{col}' not found in input file")
                sys.exit(1)
    
    # Load LOINC targets
    print(f"Loading LOINC targets from {args.loinc_file}...")
    try:
        loinc_df = pd.read_csv(args.loinc_file)
        print(f"Loaded {len(loinc_df)} LOINC targets")
    except Exception as e:
        print(f"Error loading LOINC targets: {e}")
        sys.exit(1)
    
    # Load model
    print(f"Loading model for fold {args.fold}...")
    try:
        model = load_model(args.checkpoint_dir, args.fold)
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)
    
    # Prepare source texts
    source_texts = input_df['source_text'].tolist()
    
    # Prepare target texts
    unique_loincs = loinc_df['LOINC_NUM'].unique()
    target_texts = []
    target_codes = []
    
    print("Preparing target texts...")
    for loinc in tqdm(unique_loincs, desc="Processing LOINC targets"):
        matching_rows = loinc_df[loinc_df['LOINC_NUM'] == loinc]
        if len(matching_rows) > 0:
            if 'LONG_COMMON_NAME' in matching_rows.columns:
                target_text = matching_rows.iloc[0]['LONG_COMMON_NAME']
            else:
                # Use the first text column available
                for col in ['LONG_COMMON_NAME', 'DisplayName', 'SHORTNAME', 'TARGET']:
                    if col in matching_rows.columns:
                        target_text = matching_rows.iloc[0][col]
                        break
                else:
                    # If no known column found, use the second column
                    target_text = matching_rows.iloc[0][matching_rows.columns[1]]
            
            target_texts.append(target_text)
            target_codes.append(loinc)
    
    # Compute embeddings
    print("Computing source embeddings...")
    source_embeddings = compute_embeddings(source_texts, model, batch_size=args.batch_size)
    
    print("Computing target embeddings...")
    target_embeddings = compute_embeddings(target_texts, model, batch_size=args.batch_size)
    
    # Calculate similarities
    print("Calculating similarities...")
    similarities = -pairwise_distances(source_embeddings, target_embeddings, metric='cosine')
    
    # Process results with threshold-based unmappable detection
    results = []
    
    for i, row in enumerate(input_df.iterrows()):
        source_id = row[1]['id']
        source_text = row[1]['source_text']
        
        # Get similarity scores for this source
        source_similarities = similarities[i]
        
        # Get maximum similarity
        max_similarity = np.max(source_similarities)
        
        # Create result dictionary
        result = {
            'id': source_id,
            'source_text': source_text,
            'max_similarity': max_similarity,
            'is_mappable': max_similarity >= args.threshold,
        }
        
        # If mappable, add top-k matches
        if max_similarity >= args.threshold:
            top_indices = np.argsort(source_similarities)[::-1][:args.top_k]
            
            for rank, idx in enumerate(top_indices):
                result[f'loinc_{rank+1}'] = target_codes[idx]
                result[f'text_{rank+1}'] = target_texts[idx]
                result[f'score_{rank+1}'] = source_similarities[idx]
        else:
            # If unmappable, set to UNMAPPABLE
            result['loinc_1'] = 'UNMAPPABLE'
            result['text_1'] = 'No suitable LOINC match found'
            result['score_1'] = max_similarity
            
            # Empty values for remaining ranks
            for rank in range(2, args.top_k + 1):
                result[f'loinc_{rank}'] = ''
                result[f'text_{rank}'] = ''
                result[f'score_{rank}'] = ''
        
        results.append(result)
    
    # Convert to DataFrame
    results_df = pd.DataFrame(results)
    
    # Save results
    output_file = os.path.join(args.output_dir, 'loinc_mappings_with_nomatch.csv')
    results_df.to_csv(output_file, index=False)
    print(f"Results saved to {output_file}")
    
    # Print summary
    mappable_count = sum(results_df['is_mappable'])
    unmappable_count = len(results_df) - mappable_count
    
    print(f"\nSummary:")
    print(f"- Total examples: {len(results_df)}")
    print(f"- Mappable: {mappable_count} ({mappable_count/len(results_df)*100:.2f}%)")
    print(f"- Unmappable: {unmappable_count} ({unmappable_count/len(results_df)*100:.2f}%)")
    
    # Generate confidence level distribution
    if mappable_count > 0:
        print("\nConfidence distribution for mappable examples:")
        confidence_bins = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0]
        
        for i in range(len(confidence_bins) - 1):
            upper = -confidence_bins[i]
            lower = -confidence_bins[i+1]
            count = sum((results_df['max_similarity'] >= lower) & (results_df['max_similarity'] < upper) & results_df['is_mappable'])
            percent = count / mappable_count * 100 if mappable_count > 0 else 0
            print(f"  {confidence_bins[i]:.1f}-{confidence_bins[i+1]:.1f}: {count} ({percent:.2f}%)")

if __name__ == "__main__":
    main()
