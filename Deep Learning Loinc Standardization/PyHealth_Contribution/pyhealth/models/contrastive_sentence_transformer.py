import os
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
import logging
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from .base_model import BaseModel

logger = logging.getLogger(__name__)

class ContrastiveSentenceTransformer(BaseModel):
    """Sentence Transformer model for contrastive learning.
    
    This model wraps a pre-trained sentence embedding model (e.g., Sentence-T5, SapBERT)
    and adds an optional projection layer to map embeddings to a lower-dimensional space.
    It's designed for use with contrastive learning objectives like triplet loss to train
    embeddings for medical term standardization tasks, specifically LOINC mapping.
    
    Args:
        base_model_id: HuggingFace model name or path (e.g., "google/sentence-t5-base").
        projection_dim: Dimension of the optional projection layer. If None, uses direct model output.
        freeze_backbone: Whether to freeze the weights of the base model during fine-tuning.
        normalize_embeddings: Whether to L2-normalize embeddings before return.
        dropout: Dropout probability for the projection layer.
        
    Examples:
        >>> from pyhealth.models import ContrastiveSentenceTransformer
        >>> model = ContrastiveSentenceTransformer(
        ...     base_model_id="google/sentence-t5-base",
        ...     projection_dim=128,
        ...     freeze_backbone=True,
        ... )
        >>> texts = ["glucose serum", "sodium urine", "hemoglobin blood"]
        >>> embeddings = model(texts)
    """
    
    def __init__(
        self,
        base_model_id: str = "sentence-transformers/all-MiniLM-L6-v2",
        projection_dim: Optional[int] = None,
        freeze_backbone: bool = True,
        normalize_embeddings: bool = True,
    ):
        super().__init__()
        
        self.base_model_id = base_model_id
        self.projection_dim = projection_dim
        self.freeze_backbone = freeze_backbone
        self.normalize_embeddings = normalize_embeddings
        
        # Load the pre-trained model
        logger.info(f"Loading pre-trained model: {base_model_id}")
        self.encoder = SentenceTransformer(base_model_id)
        
        # Freeze the backbone if specified
        if freeze_backbone:
            logger.info("Freezing base model parameters")
            for param in self.encoder.parameters():
                param.requires_grad = False
        
        # Get the output dimension of the base model
        self.output_dim = self.encoder.get_sentence_embedding_dimension()
        logger.info(f"Base model output dimension: {self.output_dim}")
        
        # Add projection layer if specified
        if projection_dim is not None:
            logger.info(f"Adding projection layer: {self.output_dim} -> {projection_dim}")
            self.fc = nn.Sequential(
                nn.Linear(self.output_dim, projection_dim),
            )
            self.output_dim = projection_dim
        else:
            self.fc = nn.Identity()
            
    def forward(self, texts: List[str]) -> torch.Tensor:
        """Generate embeddings for a batch of texts.
        
        Args:
            texts: List of text strings to encode.
            
        Returns:
            Tensor of shape (batch_size, embedding_dim) containing the embeddings.
        """
        # Get embeddings from the base model
        with torch.inference_mode():
            embeddings = self.encoder.encode(texts, convert_to_tensor=True)
            
        # Ensure FC layer is on the same device as embeddings
        device = embeddings.device
        self.fc = self.fc.to(device)
            
        # Pass through projection layer
        embeddings = self.fc(embeddings)
        
        # L2 normalize if specified
        if self.normalize_embeddings:
            embeddings = F.normalize(embeddings, p=2, dim=1)
            
        return embeddings
    
    def encode(
        self, 
        texts: List[str], 
        batch_size: int = 32, 
        show_progress_bar: bool = False,
        convert_to_numpy: bool = True,
        convert_to_tensor: bool = False,
        device: Optional[str] = None,
    ) -> Union[np.ndarray, torch.Tensor]:
        """Encode the given texts into embeddings.
        
        Args:
            texts: The texts to encode.
            batch_size: Batch size for encoding.
            show_progress_bar: Whether to show a progress bar.
            convert_to_numpy: Whether to convert the output to a numpy array.
            convert_to_tensor: Whether to convert the output to a torch tensor.
            device: The device to use for encoding.
            
        Returns:
            Array of shape (batch_size, output_dim) containing the embeddings.
        """
        self.eval()  # Set to evaluation mode
        
        # If device is provided, move model to device
        if device is not None:
            self.to(device)
        
        all_embeddings = []
        
        # Process in batches
        for i in tqdm(
            range(0, len(texts), batch_size),
            desc="Batches",
            disable=not show_progress_bar,
        ):
            batch_texts = texts[i:i + batch_size]
            
            # Encode batch
            with torch.no_grad():
                batch_embeddings = self(batch_texts)
            
            all_embeddings.append(batch_embeddings)
        
        # Concatenate all embeddings
        all_embeddings = torch.cat(all_embeddings, dim=0)
        
        # Convert to numpy or tensor as requested
        if convert_to_numpy:
            return all_embeddings.cpu().numpy()
        elif convert_to_tensor:
            return all_embeddings
        
        return all_embeddings
    
    def get_config(self) -> dict:
        """Get the model configuration as a dictionary.
        
        Returns:
            Dictionary containing the model configuration.
        """
        return {
            "base_model_id": self.base_model_id,
            "projection_dim": self.projection_dim,
            "normalize_embeddings": self.normalize_embeddings,
            "freeze_backbone": self.freeze_backbone,
        }
    
    def save_pretrained(self, save_dir: str) -> None:
        """Save the model to a directory.
        
        Args:
            save_dir: Directory to save the model to.
        """
        os.makedirs(save_dir, exist_ok=True)
        
        # Save configuration
        torch.save(self.get_config(), os.path.join(save_dir, "config.bin"))
        
        # Save model state dict
        torch.save(self.state_dict(), os.path.join(save_dir, "pytorch_model.bin"))
        
        logger.info(f"Model saved to {save_dir}")
        
    @classmethod
    def from_pretrained(cls, model_dir: str) -> "ContrastiveSentenceTransformer":
        """Load a model from a directory.
        
        Args:
            model_dir: Directory to load the model from.
            
        Returns:
            Loaded model.
        """
        # Load configuration
        config_path = os.path.join(model_dir, "config.bin")
        if not os.path.exists(config_path):
            raise ValueError(f"Config file not found at {config_path}")
        
        config = torch.load(config_path)
        
        # Create model
        model = cls(
            base_model_id=config.get("base_model_id", "sentence-transformers/all-MiniLM-L6-v2"),
            projection_dim=config.get("projection_dim", None),
            freeze_backbone=config.get("freeze_backbone", True),
            normalize_embeddings=config.get("normalize_embeddings", True),
        )
        
        # Load state dict
        model_path = os.path.join(model_dir, "pytorch_model.bin")
        if not os.path.exists(model_path):
            raise ValueError(f"Model file not found at {model_path}")
        
        try:
            state_dict = torch.load(model_path)
            model.load_state_dict(state_dict, strict=False)
            logger.info(f"Loaded model weights from {model_path}")
        except Exception as e:
            logger.warning(f"Error loading model weights: {e}. Using newly initialized model.")
        
        return model 