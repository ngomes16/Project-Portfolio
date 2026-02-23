import tensorflow as tf
import numpy as np
import pandas as pd
import os
import argparse
import sys
from tqdm import tqdm
import time

# Add parent directory to path to import from other modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def load_triplets(triplets_file):
    """
    Load triplet examples with negative samples
    
    Args:
        triplets_file: Path to triplets CSV file
        
    Returns:
        triplets_df: DataFrame with triplet examples
    """
    triplets_df = pd.read_csv(triplets_file)
    
    required_columns = ['anchor', 'positive', 'negative']
    missing_columns = [col for col in required_columns if col not in triplets_df.columns]
    
    if missing_columns:
        raise ValueError(f"Triplets file is missing required columns: {missing_columns}")
    
    print(f"Loaded {len(triplets_df)} triplet examples from {triplets_file}")
    
    return triplets_df

class TripletModel(tf.keras.Model):
    """
    Triplet model for training with negative examples
    """
    def __init__(self, encoder_model, margin=0.2):
        super(TripletModel, self).__init__()
        self.encoder = encoder_model
        self.margin = margin
        
    def call(self, inputs):
        anchor_input, positive_input, negative_input = inputs
        
        # Get embeddings
        anchor_embedding = self.encoder(inputs=anchor_input)
        positive_embedding = self.encoder(inputs=positive_input)
        negative_embedding = self.encoder(inputs=negative_input)
        
        # Calculate distances using Keras operations
        pos_dist = tf.reduce_sum(tf.square(tf.subtract(anchor_embedding, positive_embedding)), axis=-1)
        neg_dist = tf.reduce_sum(tf.square(tf.subtract(anchor_embedding, negative_embedding)), axis=-1)
        
        # Calculate triplet loss
        basic_loss = tf.subtract(pos_dist, neg_dist) + self.margin
        loss = tf.maximum(basic_loss, 0.0)
        
        return loss
    
    def train_step(self, data):
        # Unpack the data
        x, y = data
        
        with tf.GradientTape() as tape:
            # Forward pass
            loss = self(x)
            # Calculate loss value
            loss_value = tf.reduce_mean(loss)
        
        # Calculate gradients
        trainable_vars = self.trainable_variables
        gradients = tape.gradient(loss_value, trainable_vars)
        
        # Update weights
        self.optimizer.apply_gradients(zip(gradients, trainable_vars))
        
        return {"loss": loss_value}

def create_triplet_model(encoder_model, margin=0.2):
    """
    Create a model for triplet training
    
    Args:
        encoder_model: Base encoder model
        margin: Margin for triplet loss
        
    Returns:
        triplet_model: Model for triplet training
    """
    # Create triplet model
    triplet_model = TripletModel(encoder_model, margin=margin)
    
    # Compile the model
    triplet_model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=3e-5))
    
    return triplet_model

def train_with_triplets(encoder_model, triplets_df, output_dir, batch_size=16, epochs=10):
    """
    Train encoder with triplet loss using negative examples
    
    Args:
        encoder_model: Base encoder model
        triplets_df: DataFrame with triplet examples
        output_dir: Directory to save model
        batch_size: Batch size for training
        epochs: Number of epochs for training
        
    Returns:
        history: Training history
    """
    # Create triplet model
    triplet_model = create_triplet_model(encoder_model)
    
    # Prepare data
    anchors = triplets_df['anchor'].tolist()
    positives = triplets_df['positive'].tolist()
    negatives = triplets_df['negative'].tolist()
    
    # Dummy labels (not used in loss calculation)
    dummy_labels = np.zeros((len(anchors),), dtype=np.float32)
    
    # Create dataset
    dataset = tf.data.Dataset.from_tensor_slices((
        {
            'anchor_input': anchors,
            'positive_input': positives,
            'negative_input': negatives
        },
        dummy_labels
    ))
    
    dataset = dataset.shuffle(buffer_size=len(anchors)).batch(batch_size)
    
    # Create checkpoint callback
    checkpoint_dir = os.path.join(output_dir, 'checkpoints')
    os.makedirs(checkpoint_dir, exist_ok=True)
    
    checkpoint_path = os.path.join(checkpoint_dir, 'triplet_model.weights.h5')
    checkpoint_callback = tf.keras.callbacks.ModelCheckpoint(
        checkpoint_path,
        save_weights_only=True,
        save_best_only=True,
        monitor='loss',
        mode='min',
        verbose=1
    )
    
    # Train model
    print(f"Training triplet model with {len(anchors)} triplet examples...")
    history = triplet_model.fit(
        dataset,
        epochs=epochs,
        callbacks=[checkpoint_callback]
    )
    
    # Save encoder weights (from the encoder inside the triplet model)
    encoder_path = os.path.join(checkpoint_dir, 'encoder_model.weights.h5')
    triplet_model.encoder.save_weights(encoder_path)
    print(f"Saved encoder model to {encoder_path}")
    
    return history

def validate_model(encoder_model, validation_df, target_df, k_values=[1, 3, 5]):
    """
    Validate model on validation data
    
    Args:
        encoder_model: Trained encoder model
        validation_df: DataFrame with validation data
        target_df: DataFrame with target LOINCs
        k_values: List of k values for Top-k accuracy
        
    Returns:
        results: Dictionary with validation results
    """
    from models.evaluation import compute_embeddings
    
    # Get source texts and target LOINCs
    source_texts = validation_df['SOURCE'].tolist()
    target_loincs = validation_df['LOINC_NUM'].tolist()
    
    # Get unique target LOINCs
    unique_target_loincs = target_df['LOINC_NUM'].unique()
    
    # Compute embeddings for target LOINCs
    print("Computing embeddings for target LOINCs...")
    target_texts = []
    for loinc in tqdm(unique_target_loincs):
        matching_rows = target_df[target_df['LOINC_NUM'] == loinc]
        if matching_rows.empty:
            print(f"WARNING: No matching rows for LOINC {loinc}")
            continue
        target_text = matching_rows.iloc[0]['TARGET']
        target_texts.append(target_text)
    
    target_embeddings = compute_embeddings(target_texts, encoder_model)
    
    # Compute embeddings for source texts
    print("Computing embeddings for source texts...")
    source_embeddings = compute_embeddings(source_texts, encoder_model)
    
    # Calculate pairwise distances
    from sklearn.metrics import pairwise_distances
    similarities = -pairwise_distances(source_embeddings, target_embeddings, metric='cosine')
    
    # Create dictionary mapping LOINC codes to indices
    loinc_to_index = {loinc: i for i, loinc in enumerate(unique_target_loincs)}
    
    # Calculate Top-k accuracy
    results = {}
    for k in k_values:
        # Get top k indices for each source
        top_k_indices = np.argsort(similarities, axis=1)[:, -k:]
        
        # Check if correct target is in top k
        correct = 0
        for i, target_loinc in enumerate(target_loincs):
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
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Train LOINC model with triplet negative examples')
    parser.add_argument('--triplets_file', type=str, required=True, 
                        help='Path to triplets CSV with negative examples')
    parser.add_argument('--validation_file', type=str, default='output/mimic_pairs_processed.csv', 
                        help='Path to validation data CSV')
    parser.add_argument('--loinc_file', type=str, default='output/loinc_full_processed.csv', 
                        help='Path to LOINC target CSV')
    parser.add_argument('--checkpoint_dir', type=str, default='models/checkpoints', 
                        help='Directory with base model checkpoints')
    parser.add_argument('--fold', type=int, default=0, 
                        help='Fold to use as base model (0-indexed)')
    parser.add_argument('--output_dir', type=str, default='results/triplet_training', 
                        help='Directory to save trained model and results')
    parser.add_argument('--batch_size', type=int, default=16, 
                        help='Batch size for training')
    parser.add_argument('--epochs', type=int, default=5, 
                        help='Number of epochs for training')
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load triplets
    print(f"Loading triplets from {args.triplets_file}...")
    triplets_df = load_triplets(args.triplets_file)
    
    # Load validation data
    print(f"Loading validation data from {args.validation_file}...")
    validation_df = pd.read_csv(args.validation_file)
    
    # Load LOINC targets
    print(f"Loading LOINC targets from {args.loinc_file}...")
    loinc_df = pd.read_csv(args.loinc_file)
    
    # Make sure TARGET column exists
    if 'TARGET' not in loinc_df.columns:
        if 'LONG_COMMON_NAME' in loinc_df.columns:
            loinc_df['TARGET'] = loinc_df['LONG_COMMON_NAME']
        elif 'DisplayName' in loinc_df.columns:
            loinc_df['TARGET'] = loinc_df['DisplayName']
        else:
            raise ValueError("LOINC data does not have TARGET, LONG_COMMON_NAME, or DisplayName column")
    
    # Load base model
    print(f"Loading base model from fold {args.fold}...")
    
    # Import model class
    try:
        from models.t5_encoder import LOINCEncoder
        from models.evaluation import load_model
        
        # Load the model
        base_model = load_model(args.checkpoint_dir, args.fold)
        print("Base model loaded successfully")
        
        # Validate base model
        print("Validating base model before training...")
        base_results = validate_model(base_model, validation_df, loinc_df)
        
        # Save base results
        base_results_df = pd.DataFrame([base_results])
        base_results_df.to_csv(os.path.join(args.output_dir, 'base_model_results.csv'), index=False)
        
        # Train with triplets
        print("Training model with triplet loss...")
        history = train_with_triplets(
            encoder_model=base_model,
            triplets_df=triplets_df,
            output_dir=args.output_dir,
            batch_size=args.batch_size,
            epochs=args.epochs
        )
        
        # Save training history
        history_df = pd.DataFrame(history.history)
        history_df.to_csv(os.path.join(args.output_dir, 'training_history.csv'), index=False)
        
        # Load trained model
        print("Loading trained model for validation...")
        trained_model = LOINCEncoder(embedding_dim=128, dropout_rate=0.0)
        _ = trained_model(inputs=["dummy text"])  # Build the model
        
        # Load trained weights
        trained_model.load_weights(os.path.join(args.output_dir, 'checkpoints', 'encoder_model.weights.h5'))
        
        # Validate trained model
        print("Validating trained model...")
        trained_results = validate_model(trained_model, validation_df, loinc_df)
        
        # Save trained results
        trained_results_df = pd.DataFrame([trained_results])
        trained_results_df.to_csv(os.path.join(args.output_dir, 'trained_model_results.csv'), index=False)
        
        # Compare results
        print("\n" + "="*80)
        print("COMPARISON OF RESULTS")
        print("="*80)
        print("Metric\t\tBase Model\tTrained Model\tDifference")
        print("-"*80)
        
        for metric in ['top1_accuracy', 'top3_accuracy', 'top5_accuracy', 'mrr']:
            if metric in base_results and metric in trained_results:
                base_value = base_results[metric]
                trained_value = trained_results[metric]
                diff = trained_value - base_value
                diff_pct = diff / base_value * 100 if base_value > 0 else 0
                
                print(f"{metric}\t{base_value:.4f}\t\t{trained_value:.4f}\t\t{diff:.4f} ({diff_pct:+.2f}%)")
        
        print("="*80)
        print(f"Trained model and results saved to {args.output_dir}")
        
    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    main() 