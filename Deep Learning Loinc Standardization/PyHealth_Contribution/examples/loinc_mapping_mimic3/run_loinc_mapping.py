#!/usr/bin/env python
# coding: utf-8

"""
LOINC Mapping Example Script

This script demonstrates a complete workflow for standardizing local laboratory codes
to LOINC codes using a contrastive learning approach with Sentence-T5 embeddings.
The implementation follows the methodology described in the paper
"Automated LOINC Standardization Using Pre-trained Large Language Models".

The script demonstrates:
1. Loading and processing the MIMIC-III lab items dataset
2. Loading a pre-trained Stage 1 model (or creating one if not available)
3. Stage 2 fine-tuning on source-target pairs
4. Evaluation using top-k accuracy metrics
5. Example predictions on new inputs
"""

import os
import sys
import argparse
import logging
import random
import numpy as np
import pandas as pd
import torch
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sentence_transformers import SentenceTransformer, losses
from tqdm import tqdm

# Add the parent directory to the path to allow importing PyHealth modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# This is the key addition to make sure we import from PyHealth_Contribution
pyhealth_contribution_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, pyhealth_contribution_path)

from pyhealth.datasets.mimic3_loinc import MIMIC3LOINCMappingDataset
from pyhealth.models.contrastive_sentence_transformer import ContrastiveSentenceTransformer
from pyhealth.tasks.loinc_mapping import (
    loinc_retrieval_metrics_fn, 
    loinc_retrieval_predictions,
    online_hard_triplet_mining,
    online_semi_hard_triplet_mining
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Set random seeds for reproducibility
def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

set_seed(42)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='LOINC Mapping Example')
    
    # Data paths
    parser.add_argument('--mimic3_dir', type=str, 
                        default='./sample_data',
                        help='Path to MIMIC-III data directory')
    parser.add_argument('--d_labitems', type=str, 
                        default='d_labitems.csv',
                        help='Path to d_labitems.csv file (relative to mimic3_dir)')
    parser.add_argument('--loinc_table', type=str, 
                        default='mini_loinc_table.csv',
                        help='Path to LOINC table file (relative to mimic3_dir)')
    
    # Model parameters
    parser.add_argument('--base_model_id', type=str, 
                        default='sentence-transformers/all-MiniLM-L6-v2',
                        help='Base model ID for Sentence Transformer (default: all-MiniLM-L6-v2)')
    parser.add_argument('--stage1_weights', type=str, 
                        default='./weights',
                        help='Path to directory containing Stage 1 pre-trained weights')
    parser.add_argument('--projection_dim', type=int, 
                        default=128,
                        help='Projection dimension for output embeddings')
    parser.add_argument('--batch_size', type=int, 
                        default=16,
                        help='Batch size for training')
    parser.add_argument('--epochs', type=int, 
                        default=10,
                        help='Number of epochs for Stage 2 fine-tuning')
    parser.add_argument('--learning_rate', type=float, 
                        default=1e-5,
                        help='Learning rate for Stage 2 fine-tuning')
    parser.add_argument('--margin', type=float, 
                        default=0.2,
                        help='Margin for triplet loss')
    parser.add_argument('--mining_strategy', type=str, 
                        choices=['hard', 'semi-hard'],
                        default='hard',
                        help='Triplet mining strategy (hard or semi-hard)')
    
    # Output parameters
    parser.add_argument('--output_dir', type=str, 
                        default='./output',
                        help='Output directory for saving model and results')
    parser.add_argument('--no_train', action='store_true',
                        help='Skip training and only run evaluation if model exists')
    
    # Device parameters
    parser.add_argument('--device', type=str, 
                        default='',
                        help='Device to use (cpu, cuda, or leave empty for auto-detection)')
    
    args = parser.parse_args()
    return args

def load_dataset(args):
    """Load the MIMIC-III LOINC mapping dataset."""
    logger.info(f"Loading dataset from {args.mimic3_dir}")
    
    dataset = MIMIC3LOINCMappingDataset(
        root=args.mimic3_dir,
        d_labitems_path=args.d_labitems,
        loinc_table_path=args.loinc_table,
        train_ratio=0.7,
        val_ratio=0.1,
        test_ratio=0.2,
        seed=42,
    )
    
    # Print dataset statistics
    dataset.stat()
    
    return dataset

def create_model(args, device=None):
    """Create or load ContrastiveSentenceTransformer model."""
    # Detect device if not specified
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Check if Stage 1 pre-trained weights exist
    stage1_weights_path = args.stage1_weights
    if os.path.exists(os.path.join(stage1_weights_path, "pytorch_model.bin")):
        logger.info(f"Loading Stage 1 pre-trained weights from {stage1_weights_path}")
        model = ContrastiveSentenceTransformer.from_pretrained(stage1_weights_path)
    else:
        logger.info(f"No Stage 1 weights found. Creating model from {args.base_model_id}")
        model = ContrastiveSentenceTransformer(
            base_model_id=args.base_model_id,
            projection_dim=args.projection_dim,
            freeze_backbone=True,
            normalize_embeddings=True,
        )
    
    model = model.to(device)
    logger.info(f"Model loaded on {device}")
    
    return model

def train_model(model, dataset, args, device=None):
    """Train the model using triplet loss and hard negative mining."""
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Get training data
    train_data = dataset.get_train_data()
    val_data = dataset.get_val_data()
    
    # Convert to format needed for training
    train_texts = [sample['source_text'] for sample in train_data]
    train_labels = [sample['target_loinc'] for sample in train_data]
    
    val_texts = [sample['source_text'] for sample in val_data]
    val_labels = [sample['target_loinc'] for sample in val_data]
    
    # Create optimizer
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
    
    # Set up mining strategy
    if args.mining_strategy == 'hard':
        mining_func = online_hard_triplet_mining
        logger.info("Using hard negative mining strategy")
    else:
        mining_func = online_semi_hard_triplet_mining
        logger.info("Using semi-hard negative mining strategy")
    
    # Training loop
    logger.info(f"Starting Stage 2 training for {args.epochs} epochs")
    best_val_acc = 0
    best_model_state = None
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Lists for tracking metrics
    train_losses = []
    val_top1_accs = []
    val_top3_accs = []
    val_top5_accs = []
    
    for epoch in range(args.epochs):
        model.train()
        total_loss = 0
        
        # Process in batches to avoid memory issues
        batch_size = args.batch_size
        for i in range(0, len(train_texts), batch_size):
            batch_end = min(i + batch_size, len(train_texts))
            batch_texts = train_texts[i:batch_end]
            batch_labels = train_labels[i:batch_end]
            
            # Generate embeddings for batch
            with torch.no_grad():
                embeddings = model.encode(batch_texts, convert_to_numpy=True)
            
            # Mine triplets
            anchors, positives, negatives = mining_func(
                embeddings, batch_labels, margin=args.margin
            )
            
            # Skip if no triplets found
            if len(anchors) == 0:
                continue
            
            # Get texts for triplets
            anchor_texts = [batch_texts[idx] for idx in anchors]
            positive_texts = [batch_texts[idx] for idx in positives]
            negative_texts = [batch_texts[idx] for idx in negatives]
            
            # Train on triplets
            optimizer.zero_grad()
            
            # Get embeddings
            anchor_embeddings = model(anchor_texts)
            positive_embeddings = model(positive_texts)
            negative_embeddings = model(negative_texts)
            
            # Compute triplet loss
            triplet_loss = torch.nn.TripletMarginLoss(margin=args.margin)(
                anchor_embeddings, positive_embeddings, negative_embeddings
            )
            
            triplet_loss.backward()
            optimizer.step()
            
            total_loss += triplet_loss.item()
        
        avg_loss = total_loss / (len(train_texts) // batch_size + 1)
        train_losses.append(avg_loss)
        
        # Evaluate on validation set
        model.eval()
        val_source_embeddings = model.encode(val_texts)
        
        # Get unique target codes and their texts
        unique_targets = list(set(val_labels))
        
        # Use the LOINC table to get text representations for targets if available
        if dataset.target_loinc_texts:
            target_texts = []
            for loinc in unique_targets:
                if loinc in dataset.target_loinc_texts and dataset.target_loinc_texts[loinc]:
                    # Use the LCN (Long Common Name) if available
                    lcn_variants = [v for v in dataset.target_loinc_texts[loinc] if v[0] == 'LCN']
                    if lcn_variants:
                        target_texts.append(lcn_variants[0][1])
                    else:
                        # Otherwise use the first available variant
                        target_texts.append(dataset.target_loinc_texts[loinc][0][1])
                else:
                    # If no text representation is available, use the code itself
                    target_texts.append(loinc)
        else:
            # If LOINC table not loaded, use the code itself
            target_texts = unique_targets
        
        # Generate target embeddings
        val_target_embeddings = model.encode(target_texts)
        
        # Calculate metrics
        metrics = loinc_retrieval_metrics_fn(
            val_labels, val_source_embeddings, val_target_embeddings, unique_targets,
            k_values=[1, 3, 5]
        )
        
        val_top1_acc = metrics['loinc_top_1_acc']
        val_top3_acc = metrics['loinc_top_3_acc']
        val_top5_acc = metrics['loinc_top_5_acc']
        
        val_top1_accs.append(val_top1_acc)
        val_top3_accs.append(val_top3_acc)
        val_top5_accs.append(val_top5_acc)
        
        logger.info(f"Epoch {epoch+1}/{args.epochs} - "
                   f"Loss: {avg_loss:.4f} - "
                   f"Val Top-1: {val_top1_acc:.4f} - "
                   f"Val Top-3: {val_top3_acc:.4f} - "
                   f"Val Top-5: {val_top5_acc:.4f}")
        
        # Save best model
        if val_top1_acc > best_val_acc:
            best_val_acc = val_top1_acc
            best_model_state = model.state_dict()
            model.save_pretrained(os.path.join(args.output_dir, "best_model"))
            logger.info(f"Saved best model with Val Top-1 Acc: {best_val_acc:.4f}")
    
    # Plot training metrics
    plt.figure(figsize=(12, 4))
    
    # Plot loss
    plt.subplot(1, 2, 1)
    plt.plot(range(1, args.epochs + 1), train_losses)
    plt.title('Training Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.grid(True)
    
    # Plot accuracy
    plt.subplot(1, 2, 2)
    plt.plot(range(1, args.epochs + 1), val_top1_accs, label='Top-1')
    plt.plot(range(1, args.epochs + 1), val_top3_accs, label='Top-3')
    plt.plot(range(1, args.epochs + 1), val_top5_accs, label='Top-5')
    plt.title('Validation Accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig(os.path.join(args.output_dir, "training_metrics.png"))
    
    # Load best model for evaluation
    if best_model_state is not None:
        model.load_state_dict(best_model_state)
    
    return model

def evaluate_model(model, dataset, args, device=None):
    """Evaluate the model on the test set."""
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Set model to evaluation mode
    model.eval()
    
    # Get test data
    test_data = dataset.get_test_data()
    
    # Convert to format needed for evaluation
    test_texts = [sample['source_text'] for sample in test_data]
    test_labels = [sample['target_loinc'] for sample in test_data]
    
    # Get unique target codes and their texts
    unique_targets = list(set(test_labels))
    
    # Use the LOINC table to get text representations for targets if available
    if dataset.target_loinc_texts:
        target_texts = []
        for loinc in unique_targets:
            if loinc in dataset.target_loinc_texts and dataset.target_loinc_texts[loinc]:
                # Use the LCN (Long Common Name) if available
                lcn_variants = [v for v in dataset.target_loinc_texts[loinc] if v[0] == 'LCN']
                if lcn_variants:
                    target_texts.append(lcn_variants[0][1])
                else:
                    # Otherwise use the first available variant
                    target_texts.append(dataset.target_loinc_texts[loinc][0][1])
            else:
                # If no text representation is available, use the code itself
                target_texts.append(loinc)
    else:
        # If LOINC table not loaded, use the code itself
        target_texts = unique_targets
    
    # Generate source and target embeddings
    logger.info("Generating embeddings for test set")
    test_source_embeddings = model.encode(test_texts)
    test_target_embeddings = model.encode(target_texts)
    
    # Calculate metrics
    logger.info("Calculating evaluation metrics")
    metrics = loinc_retrieval_metrics_fn(
        test_labels, test_source_embeddings, test_target_embeddings, unique_targets,
        k_values=[1, 3, 5, 10]
    )
    
    # Print metrics
    logger.info("Test Set Evaluation:")
    logger.info(f"Top-1 Accuracy: {metrics['loinc_top_1_acc']:.4f}")
    logger.info(f"Top-3 Accuracy: {metrics['loinc_top_3_acc']:.4f}")
    logger.info(f"Top-5 Accuracy: {metrics['loinc_top_5_acc']:.4f}")
    logger.info(f"Top-10 Accuracy: {metrics['loinc_top_10_acc']:.4f}")
    
    # Save metrics to file
    with open(os.path.join(args.output_dir, "test_metrics.txt"), "w") as f:
        for k, v in metrics.items():
            f.write(f"{k}: {v:.4f}\n")
    
    # Analyze some example predictions
    logger.info("\nExample Predictions:")
    
    # Choose 5 random test samples for analysis
    sample_indices = random.sample(range(len(test_texts)), min(5, len(test_texts)))
    
    for idx in sample_indices:
        source_text = test_texts[idx]
        true_loinc = test_labels[idx]
        
        # Get predictions for this sample
        source_embedding = test_source_embeddings[idx].reshape(1, -1)
        predictions = loinc_retrieval_predictions(
            source_embedding, test_target_embeddings, unique_targets, k=3
        )[0]
        
        # Get text representations for predicted LOINCs
        pred_texts = []
        for loinc, score in predictions:
            if dataset.target_loinc_texts and loinc in dataset.target_loinc_texts:
                lcn_variants = [v for v in dataset.target_loinc_texts[loinc] if v[0] == 'LCN']
                if lcn_variants:
                    pred_texts.append(f"{loinc} ({lcn_variants[0][1]})")
                else:
                    pred_texts.append(f"{loinc} ({dataset.target_loinc_texts[loinc][0][1]})")
            else:
                pred_texts.append(loinc)
        
        # Get text representation for true LOINC
        if dataset.target_loinc_texts and true_loinc in dataset.target_loinc_texts:
            lcn_variants = [v for v in dataset.target_loinc_texts[true_loinc] if v[0] == 'LCN']
            if lcn_variants:
                true_loinc_text = f"{true_loinc} ({lcn_variants[0][1]})"
            else:
                true_loinc_text = f"{true_loinc} ({dataset.target_loinc_texts[true_loinc][0][1]})"
        else:
            true_loinc_text = true_loinc
        
        # Print the results
        logger.info(f"\nSource: {source_text}")
        logger.info(f"True LOINC: {true_loinc_text}")
        logger.info("Top 3 Predictions:")
        for i, (loinc, score) in enumerate(predictions):
            logger.info(f"  {i+1}. {pred_texts[i]} (score: {score:.4f})")
    
    return metrics

def demonstrate_inference(model, dataset, args, device=None):
    """Demonstrate how to use the model for inference on new inputs."""
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Set model to evaluation mode
    model.eval()
    
    # Create a list of all unique LOINC targets
    all_data = dataset.get_all_data()
    all_loinc_targets = list(set(sample['target_loinc'] for sample in all_data))
    
    # Get text representations for all targets
    target_texts = []
    for loinc in all_loinc_targets:
        if dataset.target_loinc_texts and loinc in dataset.target_loinc_texts:
            lcn_variants = [v for v in dataset.target_loinc_texts[loinc] if v[0] == 'LCN']
            if lcn_variants:
                target_texts.append(lcn_variants[0][1])
            else:
                target_texts.append(dataset.target_loinc_texts[loinc][0][1])
        else:
            target_texts.append(loinc)
    
    # Generate embeddings for all targets
    logger.info("Generating embeddings for all LOINC targets")
    target_embeddings = model.encode(target_texts)
    
    # Example input texts
    example_inputs = [
        "glucose blood",
        "sodium plasma",
        "potassium serum",
        "hemoglobin",
        "white blood cell count",
    ]
    
    logger.info("\nDemonstrating inference on new inputs:")
    
    for input_text in example_inputs:
        # Generate embedding for the input
        input_embedding = model.encode([input_text])
        
        # Get predictions
        predictions = loinc_retrieval_predictions(
            input_embedding, target_embeddings, all_loinc_targets, k=3
        )[0]
        
        # Get text representations for predicted LOINCs
        pred_texts = []
        for loinc, score in predictions:
            if dataset.target_loinc_texts and loinc in dataset.target_loinc_texts:
                lcn_variants = [v for v in dataset.target_loinc_texts[loinc] if v[0] == 'LCN']
                if lcn_variants:
                    pred_texts.append(f"{loinc} ({lcn_variants[0][1]})")
                else:
                    pred_texts.append(f"{loinc} ({dataset.target_loinc_texts[loinc][0][1]})")
            else:
                pred_texts.append(loinc)
        
        # Print the results
        logger.info(f"\nInput: {input_text}")
        logger.info("Top 3 LOINC Predictions:")
        for i, (loinc, score) in enumerate(predictions):
            logger.info(f"  {i+1}. {pred_texts[i]} (score: {score:.4f})")

def main():
    """Main function to run the LOINC mapping example."""
    # Parse command line arguments
    args = parse_args()
    
    # Set device
    if args.device:
        device = torch.device(args.device)
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load dataset
    dataset = load_dataset(args)
    
    # Create or load model
    model = create_model(args, device)
    
    # Train model (unless --no_train flag is set)
    if not args.no_train:
        model = train_model(model, dataset, args, device)
    else:
        logger.info("Skipping training as --no_train flag is set")
        # Try to load trained model if available
        best_model_path = os.path.join(args.output_dir, "best_model")
        if os.path.exists(best_model_path):
            logger.info(f"Loading best model from {best_model_path}")
            model = ContrastiveSentenceTransformer.from_pretrained(best_model_path)
            model = model.to(device)
    
    # Evaluate model
    evaluate_model(model, dataset, args, device)
    
    # Demonstrate inference
    demonstrate_inference(model, dataset, args, device)
    
    logger.info("LOINC mapping example completed successfully!")

if __name__ == "__main__":
    main() 