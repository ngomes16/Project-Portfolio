import tensorflow as tf
import numpy as np

def cosine_distance(y_true, y_pred):
    """
    Compute cosine distance between two vectors.
    Cosine distance = 1 - cosine similarity
    
    Args:
        y_true: First vector
        y_pred: Second vector
        
    Returns:
        Cosine distance between the vectors
    """
    # Both vectors should be L2 normalized already, so dot product equals cosine similarity
    cosine_similarity = tf.reduce_sum(y_true * y_pred, axis=-1)
    # Cosine distance = 1 - cosine similarity
    return 1.0 - cosine_similarity

def triplet_loss(anchor, positive, negative, margin=0.8):
    """
    Compute triplet loss using cosine distance.
    
    Args:
        anchor: Embeddings of anchor samples
        positive: Embeddings of positive samples (same class as anchor)
        negative: Embeddings of negative samples (different class from anchor)
        margin: Minimum desired distance between (anchor, negative) and (anchor, positive)
        
    Returns:
        Triplet loss value (scalar)
    """
    # Compute squared cosine distances
    # Using squared distances as in the paper's formula
    pos_dist_squared = tf.square(cosine_distance(anchor, positive))
    neg_dist_squared = tf.square(cosine_distance(anchor, negative))
    
    # Compute triplet loss with margin
    basic_loss = pos_dist_squared - neg_dist_squared + margin
    
    # ReLU to ensure loss is >= 0
    loss = tf.maximum(basic_loss, 0.0)
    
    # Mean over the batch
    return tf.reduce_mean(loss)

def _pairwise_distances(embeddings, squared=False):
    """Compute the 2D matrix of distances between all embeddings.
    
    Args:
        embeddings: tensor of shape [batch_size, embed_dim]
        squared: Boolean. If true, output is the pairwise squared euclidean distance matrix.
                 If false, output is the pairwise euclidean distance matrix.
    Returns:
        pairwise_distances: tensor of shape [batch_size, batch_size]
    """
    # Get the dot product between all embeddings
    # shape (batch_size, batch_size)
    dot_product = tf.matmul(embeddings, tf.transpose(embeddings))

    # Get squared L2 norm for each embedding. We can just take the diagonal of `dot_product`.
    # This also provides more numerical stability (the diagonal of the result will be exactly 0).
    # shape (batch_size,)
    square_norm = tf.linalg.diag_part(dot_product)

    # Compute the pairwise distance matrix as we have:
    # ||a - b||^2 = ||a||^2  - 2 <a, b> + ||b||^2
    # shape (batch_size, batch_size)
    distances = tf.expand_dims(square_norm, 1) - 2.0 * dot_product + tf.expand_dims(square_norm, 0)

    # Because of computation errors, some distances might be negative so we put everything >= 0.0
    distances = tf.maximum(distances, 0.0)

    if not squared:
        # Because the gradient of sqrt is infinite when distances == 0.0 (ex: on the diagonal)
        # we need to add a small epsilon where distances == 0.0
        mask = tf.cast(tf.equal(distances, 0.0), dtype=tf.float32)
        distances = distances + mask * 1e-16

        distances = tf.sqrt(distances)

        # Correct the epsilon added: set the distances on the diagonal to 0.0
        distances = distances * (1.0 - mask)

    return distances

def _get_triplet_mask(labels):
    """Return a 3D mask where mask[a, p, n] is True if the triplet (a, p, n) is valid.
    
    A triplet (i, j, k) is valid if:
        - i, j, k are distinct indices
        - labels[i] == labels[j] and labels[i] != labels[k]
    
    Args:
        labels: tensor of shape [batch_size]
    
    Returns:
        mask: tf.bool tensor of shape [batch_size, batch_size, batch_size]
    """
    # Check that i, j and k are distinct
    indices_equal = tf.cast(tf.eye(tf.shape(labels)[0]), tf.bool)
    indices_not_equal = tf.logical_not(indices_equal)
    i_not_equal_j = tf.expand_dims(indices_not_equal, 2)
    i_not_equal_k = tf.expand_dims(indices_not_equal, 1)
    j_not_equal_k = tf.expand_dims(indices_not_equal, 0)

    distinct_indices = tf.logical_and(tf.logical_and(i_not_equal_j, i_not_equal_k), j_not_equal_k)

    # Check if labels[i] == labels[j] and labels[i] != labels[k]
    # Convert to strings for comparison
    if not isinstance(labels[0], str):
        labels_equal = tf.equal(tf.expand_dims(labels, 0), tf.expand_dims(labels, 1))
    else:
        # For string labels
        labels_equal = tf.reduce_all(tf.equal(
            tf.expand_dims(labels, 0), tf.expand_dims(labels, 1)), axis=-1)
        
    i_equal_j = tf.expand_dims(labels_equal, 2)
    i_equal_k = tf.expand_dims(labels_equal, 1)

    valid_labels = tf.logical_and(i_equal_j, tf.logical_not(i_equal_k))

    # Combine the two masks
    mask = tf.logical_and(distinct_indices, valid_labels)

    return mask

def _get_anchor_positive_triplet_mask(labels):
    """Return a 2D mask where mask[a, p] is True if a and p are distinct and have same label.
    
    Args:
        labels: tensor of shape [batch_size]
    
    Returns:
        mask: tf.bool tensor of shape [batch_size, batch_size]
    """
    # Check that i and j are distinct
    indices_equal = tf.cast(tf.eye(tf.shape(labels)[0]), tf.bool)
    indices_not_equal = tf.logical_not(indices_equal)

    # Check if labels[i] == labels[j]
    # Convert to strings for comparison
    if not isinstance(labels[0], str):
        labels_equal = tf.equal(tf.expand_dims(labels, 0), tf.expand_dims(labels, 1))
    else:
        # For string labels
        labels_equal = tf.reduce_all(tf.equal(
            tf.expand_dims(labels, 0), tf.expand_dims(labels, 1)), axis=-1)

    # Combine the two masks
    mask = tf.logical_and(indices_not_equal, labels_equal)

    return mask

def _get_anchor_negative_triplet_mask(labels):
    """Return a 2D mask where mask[a, n] is True if a and n have different labels.
    
    Args:
        labels: tensor of shape [batch_size]
    
    Returns:
        mask: tf.bool tensor of shape [batch_size, batch_size]
    """
    # Check if labels[i] != labels[k]
    # Convert to strings for comparison
    if not isinstance(labels[0], str):
        labels_equal = tf.equal(tf.expand_dims(labels, 0), tf.expand_dims(labels, 1))
    else:
        # For string labels
        labels_equal = tf.reduce_all(tf.equal(
            tf.expand_dims(labels, 0), tf.expand_dims(labels, 1)), axis=-1)
    
    mask = tf.logical_not(labels_equal)

    return mask

def batch_hard_triplet_loss(labels, embeddings, margin=0.8, squared=False):
    """Build the triplet loss over a batch of embeddings.
    
    For each anchor, we get the hardest positive and hardest negative.
    
    Args:
        labels: labels of the batch, of size (batch_size,)
        embeddings: tensor of shape (batch_size, embed_dim)
        margin: margin for triplet loss
        squared: Boolean. If true, output is the pairwise squared euclidean distance matrix.
                 If false, output is the pairwise euclidean distance matrix.
    
    Returns:
        triplet_loss: scalar tensor containing the triplet loss
    """
    # Convert string labels to numeric for processing
    if isinstance(labels[0], str):
        # Create a mapping from unique labels to integers
        unique_labels = np.unique(labels)
        label_to_index = {label: i for i, label in enumerate(unique_labels)}
        numeric_labels = np.array([label_to_index[label] for label in labels])
        labels = numeric_labels
    
    # Get the pairwise distance matrix
    pairwise_dist = _pairwise_distances(embeddings, squared=squared)

    # For each anchor, get the hardest positive
    # First, we need to get a mask for valid positive pairs
    mask_anchor_positive = _get_anchor_positive_triplet_mask(labels)
    mask_anchor_positive = tf.cast(mask_anchor_positive, tf.float32)

    # We put to 0 any element where (a, p) is not valid (valid if a != p and label(a) == label(p))
    anchor_positive_dist = tf.multiply(mask_anchor_positive, pairwise_dist)

    # shape (batch_size, 1)
    hardest_positive_dist = tf.reduce_max(anchor_positive_dist, axis=1, keepdims=True)

    # For each anchor, get the hardest negative
    # First, we need to get a mask for valid negative pairs
    mask_anchor_negative = _get_anchor_negative_triplet_mask(labels)
    mask_anchor_negative = tf.cast(mask_anchor_negative, tf.float32)

    # We add the maximum value in each row to the invalid negatives (label(a) == label(n))
    max_anchor_negative_dist = tf.reduce_max(pairwise_dist, axis=1, keepdims=True)
    anchor_negative_dist = pairwise_dist + max_anchor_negative_dist * (1.0 - mask_anchor_negative)

    # shape (batch_size,)
    hardest_negative_dist = tf.reduce_min(anchor_negative_dist, axis=1, keepdims=True)

    # Combine biggest d(a, p) and smallest d(a, n) into final triplet loss
    triplet_loss = tf.maximum(hardest_positive_dist - hardest_negative_dist + margin, 0.0)

    # Get final mean triplet loss
    triplet_loss = tf.reduce_mean(triplet_loss)

    return triplet_loss

def batch_semi_hard_triplet_loss(labels, embeddings, margin=0.8, squared=False):
    """Build the triplet loss over a batch of embeddings using semi-hard triplets.
    
    A triplet (a, p, n) is semi-hard if:
        - d(a, p) < d(a, n)
        - d(a, n) < d(a, p) + margin
    
    Args:
        labels: labels of the batch, of size (batch_size,)
        embeddings: tensor of shape (batch_size, embed_dim)
        margin: margin for triplet loss
        squared: Boolean. If true, output is the pairwise squared euclidean distance matrix.
                 If false, output is the pairwise euclidean distance matrix.
    
    Returns:
        triplet_loss: scalar tensor containing the triplet loss
    """
    # Convert string labels to numeric for processing
    if isinstance(labels[0], str):
        # Create a mapping from unique labels to integers
        unique_labels = np.unique(labels)
        label_to_index = {label: i for i, label in enumerate(unique_labels)}
        numeric_labels = np.array([label_to_index[label] for label in labels])
        labels = numeric_labels
    
    # Get the pairwise distance matrix
    pairwise_dist = _pairwise_distances(embeddings, squared=squared)

    # For each anchor-positive pair, get all the triplets
    # First, we need to get a mask for valid anchor-positive pairs
    mask_anchor_positive = _get_anchor_positive_triplet_mask(labels)
    mask_anchor_positive = tf.cast(mask_anchor_positive, tf.float32)

    # We put to 0 any element where (a, p) is not valid (valid if a != p and label(a) == label(p))
    anchor_positive_dist = tf.multiply(mask_anchor_positive, pairwise_dist)

    # Get the mean of the positive distances for each anchor
    # shape (batch_size, 1)
    mean_anchor_positive_dist = tf.reduce_sum(anchor_positive_dist, axis=1, keepdims=True) / (tf.reduce_sum(mask_anchor_positive, axis=1, keepdims=True) + 1e-16)

    # For each anchor-positive pair, get all the triplets
    # Get a 3D mask where mask[a, p, n] is True if the triplet (a, p, n) is valid
    mask_anchor_negative = _get_anchor_negative_triplet_mask(labels)
    mask_anchor_negative = tf.expand_dims(tf.cast(mask_anchor_negative, tf.float32), 1)

    # shape (batch_size, 1, batch_size)
    anchor_negative_dist = tf.expand_dims(pairwise_dist, 1)

    # semihard negative: distance(anchor, negative) > distance(anchor, positive)
    #                     and distance(anchor, negative) < distance(anchor, positive) + margin
    mask_semihard = tf.cast(tf.greater(anchor_negative_dist, tf.expand_dims(mean_anchor_positive_dist, 2)), tf.float32)
    mask_semihard = tf.multiply(mask_semihard, tf.cast(tf.less(anchor_negative_dist, tf.expand_dims(mean_anchor_positive_dist + margin, 2)), tf.float32))

    # Combine masks to get valid semi-hard triplets
    mask_final = tf.multiply(mask_anchor_negative, mask_semihard)

    # Get triplet loss for each anchor-positive-negative triplet
    triplet_loss = tf.expand_dims(mean_anchor_positive_dist, 2) - anchor_negative_dist + margin
    
    # Apply final mask and get mean over all valid triplets
    triplet_loss = tf.multiply(mask_final, triplet_loss)
    
    # Count number of valid triplets (where loss > 0)
    valid_triplets = tf.cast(tf.greater(triplet_loss, 0.0), tf.float32)
    num_positive_triplets = tf.reduce_sum(valid_triplets)
    
    # Get final mean triplet loss over positive triplets only
    triplet_loss = tf.multiply(triplet_loss, valid_triplets)
    triplet_loss = tf.reduce_sum(triplet_loss) / (num_positive_triplets + 1e-16)
    
    return triplet_loss 