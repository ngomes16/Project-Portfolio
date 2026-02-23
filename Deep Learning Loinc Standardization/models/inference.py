import tensorflow as tf
import numpy as np
import pandas as pd
import os
import argparse
import sys
import time

# Add parent directory to path to import from other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.t5_encoder import LOINCEncoder

def load_loinc_database(loinc_file):
    """
    Load LOINC database file
    
    Args:
        loinc_file: Path to the LOINC CSV file
        
    Returns:
        loinc_df: DataFrame with LOINC data
    """
    loinc_df = pd.read_csv(loinc_file)
    print(f"Loaded LOINC database: {len(loinc_df)} entries")
    return loinc_df

def predict(model, source_text, loinc_df, top_k=5):
    """
    Predict the most similar LOINC codes for a source text
    
    Args:
        model: Trained LOINCEncoder model
        source_text: Source text to predict for
        loinc_df: DataFrame with LOINC data
        top_k: Number of top predictions to return
        
    Returns:
        top_k_df: DataFrame with top-k predictions
    """
    # Prepare LOINC target texts
    target_texts = []
    loinc_codes = []
    
    for _, row in loinc_df.iterrows():
        # Use LONG_COMMON_NAME as target text
        if pd.notna(row['LONG_COMMON_NAME']):
            target_texts.append(row['LONG_COMMON_NAME'])
            loinc_codes.append(row['LOINC_NUM'])
    
    # Compute embeddings for source text
    with tf.device('/CPU:0'):
        source_embedding = model(inputs=[source_text], training=False).numpy()
    
    # Compute embeddings for target texts in batches
    batch_size = 32
    target_embeddings_list = []
    
    for i in range(0, len(target_texts), batch_size):
        batch_texts = target_texts[i:i+batch_size]
        with tf.device('/CPU:0'):
            batch_embeddings = model(inputs=batch_texts, training=False).numpy()
        target_embeddings_list.append(batch_embeddings)
    
    target_embeddings = np.vstack(target_embeddings_list)
    
    # Compute similarity scores
    similarity = np.matmul(source_embedding, target_embeddings.T)[0]  # Take first (and only) source
    
    # Get top-k predictions
    top_k_indices = np.argsort(similarity)[::-1][:top_k]
    top_k_scores = similarity[top_k_indices]
    top_k_codes = [loinc_codes[i] for i in top_k_indices]
    top_k_texts = [target_texts[i] for i in top_k_indices]
    
    # Create DataFrame with predictions
    top_k_df = pd.DataFrame({
        'LOINC_NUM': top_k_codes,
        'LONG_COMMON_NAME': top_k_texts,
        'Similarity': top_k_scores
    })
    
    return top_k_df

def main():
    parser = argparse.ArgumentParser(description='Make predictions with LOINC standardization model')
    parser.add_argument('source_text', type=str, help='Source text to predict LOINC code for')
    parser.add_argument('--checkpoint_path', type=str, default='models/checkpoints/stage2_fold1_model.weights.h5', 
                        help='Path to model checkpoint')
    parser.add_argument('--loinc_file', type=str, default='output/loinc_targets_processed.csv', 
                        help='Path to LOINC database CSV')
    parser.add_argument('--embedding_dim', type=int, default=128, help='Embedding dimension')
    parser.add_argument('--top_k', type=int, default=5, help='Number of top predictions to return')
    
    args = parser.parse_args()
    
    # Load LOINC database
    loinc_df = load_loinc_database(args.loinc_file)
    
    # Initialize model
    model = LOINCEncoder(embedding_dim=args.embedding_dim, dropout_rate=0.0)  # No dropout during inference
    
    # Call once to build model
    _ = model(inputs=["dummy text"])
    
    # Load model weights
    if os.path.exists(args.checkpoint_path):
        model.load_weights(args.checkpoint_path)
        print(f"Loaded model weights from {args.checkpoint_path}")
    else:
        print(f"Warning: Checkpoint not found at {args.checkpoint_path}")
        print("Using untrained model.")
    
    # Make prediction
    print(f"Predicting LOINC codes for: '{args.source_text}'")
    predictions = predict(model, args.source_text, loinc_df, args.top_k)
    
    # Print predictions
    print("\nTop predictions:")
    for i, (_, row) in enumerate(predictions.iterrows()):
        print(f"{i+1}. {row['LOINC_NUM']} - {row['LONG_COMMON_NAME']} (Similarity: {row['Similarity']:.4f})")

if __name__ == "__main__":
    main() 