import numpy as np
import tensorflow as tf
import random

def generate_stage1_triplets(loinc_texts, loinc_codes, num_triplets=10000, loinc_scales=None):
    """
    Generate triplets for Stage 1 fine-tuning (target-only).
    
    Each LOINC code has multiple text representations. We create triplets by:
    - Anchor: One text representation of a LOINC code
    - Positive: Different text representation of the same LOINC code
    - Negative: Text representation of a different LOINC code
    
    Args:
        loinc_texts: List of text representations
        loinc_codes: List of corresponding LOINC codes
        num_triplets: Number of triplets to generate
        loinc_scales: List of scale types (optional)
        
    Returns:
        List of triplets (anchor, positive, negative)
    """
    # Convert to numpy arrays for easier manipulation
    loinc_texts = np.array(loinc_texts)
    loinc_codes = np.array(loinc_codes)
    
    # Handle scale information if provided
    has_scales = loinc_scales is not None
    if has_scales:
        loinc_scales = np.array(loinc_scales)
    
    # Get unique LOINC codes
    unique_codes = np.unique(loinc_codes)
    
    # Create a mapping from LOINC codes to indices
    code_to_indices = {}
    for i, code in enumerate(unique_codes):
        code_to_indices[code] = np.where(loinc_codes == code)[0]
    
    triplets = []
    
    # Keep track of codes with multiple representations
    valid_codes = [code for code in unique_codes if len(code_to_indices[code]) > 1]
    
    if len(valid_codes) == 0:
        raise ValueError("No LOINC codes with multiple text representations found")
    
    # Import append_scale_token for appending scale sentinel token to text
    # This import is placed here to avoid circular imports
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from data_augmentation import append_scale_token
    
    for _ in range(num_triplets):
        # Select a random LOINC code with multiple representations
        anchor_code = random.choice(valid_codes)
        
        # Get indices of all text representations for this code
        indices = code_to_indices[anchor_code]
        
        # Select two different indices for anchor and positive
        anchor_idx, positive_idx = random.sample(list(indices), 2)
        
        # Select a different LOINC code for the negative
        negative_code = random.choice([c for c in unique_codes if c != anchor_code])
        negative_idx = random.choice(code_to_indices[negative_code])
        
        # Get texts
        anchor_text = loinc_texts[anchor_idx]
        positive_text = loinc_texts[positive_idx]
        negative_text = loinc_texts[negative_idx]
        
        # Append scale sentinel tokens if scale information is provided
        if has_scales:
            anchor_scale = loinc_scales[anchor_idx]
            positive_scale = loinc_scales[positive_idx]
            negative_scale = loinc_scales[negative_idx]
            
            anchor_text = append_scale_token(anchor_text, anchor_scale)
            positive_text = append_scale_token(positive_text, positive_scale)
            negative_text = append_scale_token(negative_text, negative_scale)
        
        triplets.append((
            anchor_text,
            positive_text,
            negative_text
        ))
    
    return triplets

def generate_stage2_triplets(source_texts, target_codes, num_triplets=5000, source_scales=None, target_scales=None):
    """
    Generate triplets for Stage 2 fine-tuning (source-target pairs).
    
    We create triplets by:
    - Anchor: Source text mapping to a target LOINC
    - Positive: Different source text mapping to the same target LOINC
    - Negative: Source text mapping to a different target LOINC
    
    Args:
        source_texts: List of source text descriptions
        target_codes: List of corresponding target LOINC codes
        num_triplets: Number of triplets to generate
        source_scales: List of scale types for source texts (optional)
        target_scales: Dictionary mapping target codes to scale types (optional)
        
    Returns:
        List of triplets (anchor, positive, negative)
    """
    # Convert to numpy arrays for easier manipulation
    source_texts = np.array(source_texts)
    target_codes = np.array(target_codes)
    
    # Handle scale information if provided
    has_source_scales = source_scales is not None
    if has_source_scales:
        source_scales = np.array(source_scales)
        
    # Get unique target codes
    unique_codes = np.unique(target_codes)
    
    # Create a mapping from target codes to source indices
    code_to_indices = {}
    for i, code in enumerate(unique_codes):
        code_to_indices[code] = np.where(target_codes == code)[0]
    
    triplets = []
    
    # Keep track of codes with multiple source texts
    valid_codes = [code for code in unique_codes if len(code_to_indices[code]) > 1]
    
    if len(valid_codes) == 0:
        print("Warning: No target codes with multiple source texts found.")
        print("Using data augmentation to create variations.")
        # Fall back to using all codes, assuming data augmentation created variations
        valid_codes = unique_codes
    
    # Import append_scale_token for appending scale sentinel token to text
    # This import is placed here to avoid circular imports
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from data_augmentation import append_scale_token
    
    for _ in range(num_triplets):
        # Select a random target code with multiple sources
        anchor_code = random.choice(valid_codes)
        
        # Get indices of all source texts for this code
        indices = code_to_indices[anchor_code]
        
        if len(indices) > 1:
            # Select two different indices for anchor and positive
            anchor_idx, positive_idx = random.sample(list(indices), 2)
        else:
            # If only one source text, use the same index for anchor and positive
            # This makes sense only if source_texts contains augmented variations
            anchor_idx = positive_idx = indices[0]
        
        # Select a different target code for the negative
        negative_code = random.choice([c for c in unique_codes if c != anchor_code])
        negative_idx = random.choice(code_to_indices[negative_code])
        
        # Get texts
        anchor_text = source_texts[anchor_idx]
        positive_text = source_texts[positive_idx]
        negative_text = source_texts[negative_idx]
        
        # Append scale sentinel tokens if scale information is provided
        if has_source_scales:
            anchor_scale = source_scales[anchor_idx]
            positive_scale = source_scales[positive_idx]
            negative_scale = source_scales[negative_idx]
            
            anchor_text = append_scale_token(anchor_text, anchor_scale)
            positive_text = append_scale_token(positive_text, positive_scale)
            negative_text = append_scale_token(negative_text, negative_scale)
        elif target_scales is not None:
            # If we have target scales dictionary but not source scales,
            # use the target scale for the corresponding LOINC code
            anchor_scale = target_scales.get(anchor_code, 'unk')
            positive_scale = target_scales.get(anchor_code, 'unk')  # Same code as anchor
            negative_scale = target_scales.get(negative_code, 'unk')
            
            anchor_text = append_scale_token(anchor_text, anchor_scale)
            positive_text = append_scale_token(positive_text, positive_scale)
            negative_text = append_scale_token(negative_text, negative_scale)
        
        triplets.append((
            anchor_text,
            positive_text,
            negative_text
        ))
    
    return triplets

class TripletBatchGenerator(tf.keras.utils.Sequence):
    """
    Batch generator for triplet-based training.
    Provides batches of (anchor, positive, negative) triplets.
    """
    
    def __init__(self, triplets, batch_size=32, shuffle=True):
        """
        Initialize the batch generator.
        
        Args:
            triplets: List of triplets (anchor, positive, negative)
            batch_size: Batch size
            shuffle: Whether to shuffle the triplets after each epoch
        """
        self.triplets = triplets
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.indices = np.arange(len(self.triplets))
        if self.shuffle:
            np.random.shuffle(self.indices)
    
    def __len__(self):
        """Number of batches per epoch"""
        return int(np.ceil(len(self.triplets) / self.batch_size))
    
    def __getitem__(self, idx):
        """Get batch at position idx"""
        batch_indices = self.indices[idx * self.batch_size:(idx + 1) * self.batch_size]
        batch_triplets = [self.triplets[i] for i in batch_indices]
        
        anchors = [t[0] for t in batch_triplets]
        positives = [t[1] for t in batch_triplets]
        negatives = [t[2] for t in batch_triplets]
        
        # Convert to tensors
        anchors = tf.constant(anchors)
        positives = tf.constant(positives)
        negatives = tf.constant(negatives)
        
        # For triplet loss, we return inputs and a dummy target (not used by loss function)
        # The actual triplet loss is computed from the model outputs directly
        dummy_y = tf.zeros((len(batch_indices),))
        
        return [anchors, positives, negatives], dummy_y
    
    def on_epoch_end(self):
        """Called at the end of each epoch"""
        if self.shuffle:
            np.random.shuffle(self.indices) 