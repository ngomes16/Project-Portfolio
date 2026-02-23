"""
Base Model for PyHealth

This module contains the BaseModel class that serves as the parent class
for all PyHealth model classes.
"""

import torch
import torch.nn as nn
import logging
from typing import Dict, List, Optional, Tuple, Union, Any, Callable

logger = logging.getLogger(__name__)

class BaseModel(nn.Module):
    """Base class for all PyHealth models.
    
    This class provides common functionality for model saving, loading,
    and other utilities that can be inherited by specific model implementations.
    
    All PyHealth models should inherit from this class.
    """
    
    def __init__(self):
        """Initialize the BaseModel class."""
        super(BaseModel, self).__init__()
    
    def forward(self, *args, **kwargs):
        """Forward pass through the model.
        
        This method should be implemented by subclasses to define the model's
        forward computation.
        """
        raise NotImplementedError("Subclasses must implement forward()")
    
    def save_pretrained(self, output_dir: str):
        """Save the model to a directory.
        
        Args:
            output_dir: Directory where model should be saved.
        """
        raise NotImplementedError("Subclasses must implement save_pretrained()")
    
    @classmethod
    def from_pretrained(cls, model_dir: str):
        """Load a pretrained model from a directory.
        
        Args:
            model_dir: Directory containing the saved model.
            
        Returns:
            Loaded model.
        """
        raise NotImplementedError("Subclasses must implement from_pretrained()")
    
    def get_config(self) -> Dict[str, Any]:
        """Get the model configuration.
        
        Returns:
            Dictionary containing the model configuration.
        """
        return {"model_type": self.__class__.__name__} 