#!/usr/bin/env python3
# coding: utf-8

"""
Test script for LOINC mapping implementation.

This script verifies that all components of the LOINC mapping implementation
work correctly together. It tests:
1. Loading the sample dataset
2. Initializing the model
3. Running a short training cycle
4. Making predictions
"""

import os
import sys
import logging
import numpy as np
import torch
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
    online_hard_triplet_mining
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_dataset_loading():
    """Test loading the MIMIC-III LOINC dataset."""
    logger.info("Testing dataset loading...")
    
    data_dir = os.path.join(os.path.dirname(__file__), 'sample_data')
    
    dataset = MIMIC3LOINCMappingDataset(
        root=data_dir,
        d_labitems_path='d_labitems.csv',
        loinc_table_path='mini_loinc_table.csv',
        train_ratio=0.7,
        val_ratio=0.1,
        test_ratio=0.2,
        seed=42
    )
    
    # Get dataset statistics
    dataset.stat()
    
    # Check if we can access train/val/test data
    train_data = dataset.get_train_data()
    val_data = dataset.get_val_data()
    test_data = dataset.get_test_data()
    
    # Check sample structure
    if len(train_data) > 0:
        sample = train_data[0]
        logger.info(f"Sample data structure: {sample.keys()}")
        logger.info(f"Sample source text: {sample['source_text']}")
        logger.info(f"Sample target LOINC: {sample['target_loinc']}")
    
    logger.info(f"Dataset loaded successfully with {len(train_data)} training samples, "
                f"{len(val_data)} validation samples, and {len(test_data)} test samples.")
    
    return dataset

def test_model_initialization():
    """Test initializing the ContrastiveSentenceTransformer model."""
    logger.info("Testing model initialization...")
    
    # Use a small model for quick testing
    model = ContrastiveSentenceTransformer(
        base_model_id='sentence-transformers/all-MiniLM-L6-v2',
        projection_dim=64,
        freeze_backbone=True,
        normalize_embeddings=True
    )
    
    # Test encoding a sample text
    sample_texts = ["glucose blood test", "sodium urine"]
    embeddings = model.encode(sample_texts)
    
    logger.info(f"Model initialized successfully.")
    logger.info(f"Sample encoding shape: {embeddings.shape}")
    
    return model

def test_triplet_mining(dataset, model):
    """Test triplet mining functionality."""
    logger.info("Testing triplet mining...")
    
    # Get training data
    train_data = dataset.get_train_data()
    
    # Limit to a small subset for testing
    subset_size = min(20, len(train_data))
    subset_data = train_data[:subset_size]
    
    # Extract texts and labels
    texts = [sample['source_text'] for sample in subset_data]
    labels = [sample['target_loinc'] for sample in subset_data]
    
    # Generate embeddings
    embeddings = model.encode(texts)
    
    # Mine triplets
    anchors, positives, negatives = online_hard_triplet_mining(
        embeddings, labels, margin=0.2
    )
    
    logger.info(f"Found {len(anchors)} triplets from {subset_size} samples")
    
    # Print a few examples if available
    if len(anchors) > 0:
        logger.info("Example triplets:")
        for i in range(min(3, len(anchors))):
            logger.info(f"  Anchor: {texts[anchors[i]]} (label: {labels[anchors[i]]})")
            logger.info(f"  Positive: {texts[positives[i]]} (label: {labels[positives[i]]})")
            logger.info(f"  Negative: {texts[negatives[i]]} (label: {labels[negatives[i]]})")
    
    return anchors, positives, negatives

def test_training_cycle(dataset, model):
    """Test a short training cycle."""
    logger.info("Testing a training cycle...")
    
    # Get training data
    train_data = dataset.get_train_data()
    val_data = dataset.get_val_data()
    
    # If dataset is too small, skip this test
    if len(train_data) < 5 or len(val_data) < 2:
        logger.warning("Dataset too small for training test, skipping.")
        return
    
    # Extract texts and labels
    train_texts = [sample['source_text'] for sample in train_data]
    train_labels = [sample['target_loinc'] for sample in train_data]
    
    val_texts = [sample['source_text'] for sample in val_data]
    val_labels = [sample['target_loinc'] for sample in val_data]
    
    # Create optimizer
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
    
    # Use triplet loss
    triplet_loss_fn = torch.nn.TripletMarginLoss(margin=0.2)
    
    # Run a single training epoch
    model.train()
    
    # Generate embeddings for mining
    with torch.no_grad():
        train_embeddings = model.encode(train_texts, convert_to_numpy=True)
    
    # Mine triplets
    anchors, positives, negatives = online_hard_triplet_mining(
        train_embeddings, train_labels, margin=0.2
    )
    
    if len(anchors) == 0:
        logger.warning("No triplets found, skipping training step.")
        return
    
    # Get texts for triplets
    anchor_texts = [train_texts[idx] for idx in anchors]
    positive_texts = [train_texts[idx] for idx in positives]
    negative_texts = [train_texts[idx] for idx in negatives]
    
    # Forward pass
    optimizer.zero_grad()
    
    anchor_embeddings = model(anchor_texts)
    positive_embeddings = model(positive_texts)
    negative_embeddings = model(negative_texts)
    
    # Compute loss
    loss = triplet_loss_fn(anchor_embeddings, positive_embeddings, negative_embeddings)
    
    # Backward pass
    loss.backward()
    optimizer.step()
    
    logger.info(f"Training step completed with loss: {loss.item():.4f}")
    
    # Test evaluation
    model.eval()
    
    # If we have validation data, test metrics calculation
    if len(val_data) > 0:
        # Get unique target codes and their texts
        unique_targets = list(set(val_labels))
        
        # Generate source and target embeddings
        val_source_embeddings = model.encode(val_texts)
        
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
        
        logger.info(f"Evaluation metrics: {metrics}")

def test_inference(dataset, model):
    """Test inference with the model."""
    logger.info("Testing inference...")
    
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
    target_embeddings = model.encode(target_texts)
    
    # Example inputs (the real ones from our sample data)
    example_inputs = [
        "glucose blood",
        "sodium blood",
        "potassium blood"
    ]
    
    logger.info("Example predictions:")
    
    for input_text in example_inputs:
        # Generate embedding for the input
        input_embedding = model.encode([input_text])
        
        # Get predictions
        predictions = loinc_retrieval_predictions(
            input_embedding, target_embeddings, all_loinc_targets, k=3
        )[0]
        
        # Print the results
        logger.info(f"Input: {input_text}")
        logger.info("Top 3 LOINC Predictions:")
        for i, (loinc, score) in enumerate(predictions):
            # Get LOINC descriptions if available
            if dataset.target_loinc_texts and loinc in dataset.target_loinc_texts:
                lcn_variants = [v for v in dataset.target_loinc_texts[loinc] if v[0] == 'LCN']
                if lcn_variants:
                    loinc_desc = f"{loinc} ({lcn_variants[0][1]})"
                else:
                    loinc_desc = f"{loinc} ({dataset.target_loinc_texts[loinc][0][1]})"
            else:
                loinc_desc = loinc
            
            logger.info(f"  {i+1}. {loinc_desc} (score: {score:.4f})")

def main():
    """Run all tests."""
    logger.info("Starting implementation tests")
    
    try:
        # Test dataset loading
        dataset = test_dataset_loading()
        
        # Test model initialization
        model = test_model_initialization()
        
        # Test triplet mining
        test_triplet_mining(dataset, model)
        
        # Test training cycle
        test_training_cycle(dataset, model)
        
        # Test inference
        test_inference(dataset, model)
        
        logger.info("All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during tests: {str(e)}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 