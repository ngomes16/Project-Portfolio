import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any
import torch
import logging
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm

logger = logging.getLogger(__name__)

def loinc_retrieval_metrics_fn(
    y_true_loinc: List[str],
    source_embeddings: Union[np.ndarray, torch.Tensor],
    target_embeddings: Union[np.ndarray, torch.Tensor],
    target_loinc_pool: List[str],
    k_values: List[int] = [1, 3, 5, 10],
    batch_size: int = 32,
) -> Dict[str, float]:
    """Calculate retrieval metrics for LOINC mapping task.
    
    This function computes Top-k accuracy metrics for the LOINC mapping task.
    It calculates the cosine similarity between source embeddings and all target
    embeddings, and checks if the true LOINC code is within the top-k most similar targets.
    
    Args:
        y_true_loinc: Ground truth LOINC codes for each source.
        source_embeddings: Embeddings for the source texts (N x EmbDim).
        target_embeddings: Embeddings for all candidate LOINC codes (M x EmbDim).
        target_loinc_pool: LOINC codes corresponding to the target embeddings.
        k_values: Top-k values to calculate accuracy for.
        batch_size: Batch size for similarity calculations (to avoid memory issues).
        
    Returns:
        Dictionary of metrics {name: value} containing top-k accuracy metrics.
        
    Examples:
        >>> source_embeddings = model.encode(["glucose serum", "sodium urine"])
        >>> target_embeddings = model.encode(["Glucose [Mass/volume] in Serum or Plasma", 
        ...                                  "Sodium [Moles/volume] in Urine"])
        >>> metrics = loinc_retrieval_metrics_fn(
        ...     ["2345-7", "2947-0"],
        ...     source_embeddings,
        ...     target_embeddings,
        ...     ["2345-7", "2947-0"],
        ... )
        >>> print(metrics["loinc_top_1_acc"])
    """
    # Convert inputs to numpy arrays if they are torch tensors
    if isinstance(source_embeddings, torch.Tensor):
        source_embeddings = source_embeddings.detach().cpu().numpy()
    if isinstance(target_embeddings, torch.Tensor):
        target_embeddings = target_embeddings.detach().cpu().numpy()
    
    # Validate input shapes
    if len(y_true_loinc) != source_embeddings.shape[0]:
        raise ValueError(f"Number of ground truth labels ({len(y_true_loinc)}) does not match "
                         f"number of source embeddings ({source_embeddings.shape[0]})")
    
    if len(target_loinc_pool) != target_embeddings.shape[0]:
        raise ValueError(f"Number of target LOINC codes ({len(target_loinc_pool)}) does not match "
                         f"number of target embeddings ({target_embeddings.shape[0]})")
    
    # Initialize results
    total_samples = len(y_true_loinc)
    correct_at_k = {k: 0 for k in k_values}
    
    # Process in batches to avoid memory issues with large target pools
    for i in range(0, len(source_embeddings), batch_size):
        # Get batch of source embeddings
        batch_end = min(i + batch_size, len(source_embeddings))
        batch_source_embeddings = source_embeddings[i:batch_end]
        batch_y_true = y_true_loinc[i:batch_end]
        
        # Calculate cosine similarity between batch sources and all targets
        # Shape: (batch_size, num_targets)
        similarities = cosine_similarity(batch_source_embeddings, target_embeddings)
        
        # For each source in the batch
        for j, (sim_scores, true_loinc) in enumerate(zip(similarities, batch_y_true)):
            # Get indices of top-k similar targets
            top_indices = np.argsort(sim_scores)[::-1]  # Sort in descending order
            
            # Check if true LOINC is in top-k for each k
            for k in k_values:
                top_k_indices = top_indices[:k]
                top_k_loincs = [target_loinc_pool[idx] for idx in top_k_indices]
                
                if true_loinc in top_k_loincs:
                    correct_at_k[k] += 1
    
    # Calculate metrics
    metrics = {}
    for k in k_values:
        metrics[f"loinc_top_{k}_acc"] = correct_at_k[k] / total_samples if total_samples > 0 else 0.0
    
    return metrics

def loinc_retrieval_predictions(
    source_embeddings: Union[np.ndarray, torch.Tensor],
    target_embeddings: Union[np.ndarray, torch.Tensor],
    target_loinc_pool: List[str],
    k: int = 5,
    batch_size: int = 32,
) -> List[List[Tuple[str, float]]]:
    """Get top-k LOINC predictions with similarity scores.
    
    This function computes the k most similar LOINC codes for each source embedding,
    along with their similarity scores.
    
    Args:
        source_embeddings: Embeddings for source texts (N x EmbDim).
        target_embeddings: Embeddings for all candidate LOINC codes (M x EmbDim).
        target_loinc_pool: LOINC codes corresponding to the target embeddings.
        k: Number of top predictions to return.
        batch_size: Batch size for similarity calculations (to avoid memory issues).
        
    Returns:
        List of top-k predictions for each source, where each prediction is a tuple (loinc_code, similarity_score).
        
    Examples:
        >>> source_embeddings = model.encode(["glucose serum"])
        >>> target_embeddings = model.encode([...])  # Embeddings for all LOINC targets
        >>> predictions = loinc_retrieval_predictions(
        ...     source_embeddings,
        ...     target_embeddings,
        ...     target_loinc_pool,
        ...     k=3,
        ... )
        >>> for loinc, score in predictions[0]:
        ...     print(f"{loinc}: {score:.4f}")
    """
    # Convert inputs to numpy arrays if they are torch tensors
    if isinstance(source_embeddings, torch.Tensor):
        source_embeddings = source_embeddings.detach().cpu().numpy()
    if isinstance(target_embeddings, torch.Tensor):
        target_embeddings = target_embeddings.detach().cpu().numpy()
    
    # Initialize results
    all_predictions = []
    
    # Process in batches to avoid memory issues with large target pools
    for i in range(0, len(source_embeddings), batch_size):
        # Get batch of source embeddings
        batch_end = min(i + batch_size, len(source_embeddings))
        batch_source_embeddings = source_embeddings[i:batch_end]
        
        # Calculate cosine similarity between batch sources and all targets
        # Shape: (batch_size, num_targets)
        similarities = cosine_similarity(batch_source_embeddings, target_embeddings)
        
        # For each source in the batch
        for sim_scores in similarities:
            # Get indices of top-k similar targets
            top_k_indices = np.argsort(sim_scores)[::-1][:k]  # Sort in descending order, take top k
            
            # Get corresponding LOINC codes and scores
            top_k_predictions = [(target_loinc_pool[idx], float(sim_scores[idx])) for idx in top_k_indices]
            all_predictions.append(top_k_predictions)
    
    return all_predictions

def online_hard_triplet_mining(
    anchor_embeddings: np.ndarray,
    anchor_labels: List[str],
    margin: float = 0.2,
    batch_size: Optional[int] = None,
) -> Tuple[List[int], List[int], List[int]]:
    """Perform online hard triplet mining.
    
    This function implements online hard triplet mining as described in the paper.
    For each anchor in a batch, it finds the hardest positive (same class, but furthest distance)
    and the hardest negative (different class, but closest distance).
    
    Args:
        anchor_embeddings: Embeddings for anchor samples.
        anchor_labels: Class labels for anchor samples.
        margin: Margin for triplet loss.
        batch_size: Batch size for mining (if None, use all samples).
        
    Returns:
        Tuple of (anchor_indices, positive_indices, negative_indices) for triplet loss.
    """
    # If batch_size is None, use all samples
    if batch_size is None or batch_size >= len(anchor_embeddings):
        batch_indices = list(range(len(anchor_embeddings)))
    else:
        # Randomly sample batch_size indices
        batch_indices = np.random.choice(
            len(anchor_embeddings), size=batch_size, replace=False
        ).tolist()
    
    # Get batch embeddings and labels
    batch_embeddings = anchor_embeddings[batch_indices]
    batch_labels = [anchor_labels[i] for i in batch_indices]
    
    # Calculate pairwise distances within the batch
    # Shape: (batch_size, batch_size)
    distances = np.zeros((len(batch_indices), len(batch_indices)))
    for i in range(len(batch_indices)):
        for j in range(len(batch_indices)):
            distances[i, j] = np.sum((batch_embeddings[i] - batch_embeddings[j]) ** 2)
    
    # Initialize lists for triplets
    anchors = []
    positives = []
    negatives = []
    
    # For each anchor in the batch
    for anchor_idx in range(len(batch_indices)):
        anchor_label = batch_labels[anchor_idx]
        
        # Find indices of positive samples (same class)
        pos_indices = [idx for idx, label in enumerate(batch_labels) 
                      if label == anchor_label and idx != anchor_idx]
        
        # Find indices of negative samples (different class)
        neg_indices = [idx for idx, label in enumerate(batch_labels) 
                      if label != anchor_label]
        
        # Skip if no positives or negatives
        if not pos_indices or not neg_indices:
            continue
        
        # Find hardest positive (same class, max distance)
        hardest_pos_idx = pos_indices[np.argmax([distances[anchor_idx, idx] for idx in pos_indices])]
        
        # Find hardest negative (different class, min distance)
        hardest_neg_idx = neg_indices[np.argmin([distances[anchor_idx, idx] for idx in neg_indices])]
        
        # Check if the triplet satisfies margin constraint
        if distances[anchor_idx, hardest_pos_idx] - distances[anchor_idx, hardest_neg_idx] + margin > 0:
            anchors.append(batch_indices[anchor_idx])
            positives.append(batch_indices[hardest_pos_idx])
            negatives.append(batch_indices[hardest_neg_idx])
    
    return anchors, positives, negatives

def online_semi_hard_triplet_mining(
    anchor_embeddings: np.ndarray,
    anchor_labels: List[str],
    margin: float = 0.2,
    batch_size: Optional[int] = None,
) -> Tuple[List[int], List[int], List[int]]:
    """Perform online semi-hard triplet mining.
    
    This function implements online semi-hard triplet mining as described in the paper.
    For each anchor, it finds a semi-hard negative: a negative that is further than the 
    positive but still within the margin.
    
    Args:
        anchor_embeddings: Embeddings for anchor samples.
        anchor_labels: Class labels for anchor samples.
        margin: Margin for triplet loss.
        batch_size: Batch size for mining (if None, use all samples).
        
    Returns:
        Tuple of (anchor_indices, positive_indices, negative_indices) for triplet loss.
    """
    # If batch_size is None, use all samples
    if batch_size is None or batch_size >= len(anchor_embeddings):
        batch_indices = list(range(len(anchor_embeddings)))
    else:
        # Randomly sample batch_size indices
        batch_indices = np.random.choice(
            len(anchor_embeddings), size=batch_size, replace=False
        ).tolist()
    
    # Get batch embeddings and labels
    batch_embeddings = anchor_embeddings[batch_indices]
    batch_labels = [anchor_labels[i] for i in batch_indices]
    
    # Calculate pairwise distances within the batch
    # Shape: (batch_size, batch_size)
    distances = np.zeros((len(batch_indices), len(batch_indices)))
    for i in range(len(batch_indices)):
        for j in range(len(batch_indices)):
            distances[i, j] = np.sum((batch_embeddings[i] - batch_embeddings[j]) ** 2)
    
    # Initialize lists for triplets
    anchors = []
    positives = []
    negatives = []
    
    # For each anchor in the batch
    for anchor_idx in range(len(batch_indices)):
        anchor_label = batch_labels[anchor_idx]
        
        # Find indices of positive samples (same class)
        pos_indices = [idx for idx, label in enumerate(batch_labels) 
                      if label == anchor_label and idx != anchor_idx]
        
        # Skip if no positives
        if not pos_indices:
            continue
        
        # Find hardest positive (same class, max distance)
        hardest_pos_idx = pos_indices[np.argmax([distances[anchor_idx, idx] for idx in pos_indices])]
        pos_distance = distances[anchor_idx, hardest_pos_idx]
        
        # Find semi-hard negatives: different class, distance > pos_distance but < pos_distance + margin
        semi_hard_neg_indices = []
        for idx, label in enumerate(batch_labels):
            if label != anchor_label:  # Different class
                neg_distance = distances[anchor_idx, idx]
                if pos_distance < neg_distance < pos_distance + margin:
                    semi_hard_neg_indices.append((idx, neg_distance))
        
        # If no semi-hard negatives found, find closest negative
        if not semi_hard_neg_indices:
            neg_indices = [idx for idx, label in enumerate(batch_labels) if label != anchor_label]
            if not neg_indices:  # Skip if no negatives at all
                continue
            hardest_neg_idx = neg_indices[np.argmin([distances[anchor_idx, idx] for idx in neg_indices])]
        else:
            # Use a random semi-hard negative
            random_neg = np.random.choice(len(semi_hard_neg_indices))
            hardest_neg_idx = semi_hard_neg_indices[random_neg][0]
        
        anchors.append(batch_indices[anchor_idx])
        positives.append(batch_indices[hardest_pos_idx])
        negatives.append(batch_indices[hardest_neg_idx])
    
    return anchors, positives, negatives 