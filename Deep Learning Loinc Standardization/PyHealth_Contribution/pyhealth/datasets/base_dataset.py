"""
Base Dataset for PyHealth

This module contains the BaseDataset class that serves as the parent class
for all PyHealth dataset classes.
"""

import os
import logging
import pickle
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
import numpy as np

logger = logging.getLogger(__name__)

class BaseDataset:
    """Base class for all PyHealth datasets.
    
    This class provides common functionality for dataset processing, splitting,
    and retrieval that can be inherited by specific dataset implementations.
    
    Args:
        root: The root directory of the dataset files.
        seed: Random seed for reproducibility.
        train_ratio: Ratio of data to use for training.
        val_ratio: Ratio of data to use for validation.
        test_ratio: Ratio of data to use for testing.
    """
    
    def __init__(
        self,
        root: str,
        seed: int = 42,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
    ):
        """Initialize the BaseDataset class."""
        if not os.path.exists(root):
            raise ValueError(f"Root directory {root} does not exist.")
        
        self.root = root
        self.seed = seed
        
        # Check that ratios sum to 1.0
        total_ratio = train_ratio + val_ratio + test_ratio
        if not (0.999 <= total_ratio <= 1.001):  # Allow for floating point errors
            raise ValueError(f"Train, validation, and test ratios must sum to 1.0, got {total_ratio}")
        
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        
        # Placeholders for processed data
        self._all_data = []
        self._train_data = []
        self._val_data = []
        self._test_data = []
        
        # Set random seed for reproducibility
        np.random.seed(seed)
    
    def preprocess(self):
        """Preprocess the dataset.
        
        This method should be implemented by subclasses to load and preprocess
        the dataset files into a format that can be used for training.
        """
        raise NotImplementedError("Subclasses must implement preprocess()")
    
    def split_data(self):
        """Split the dataset into training, validation, and testing sets.
        
        This method randomly shuffles the data and splits it according to the
        ratios specified in the constructor.
        """
        if not self._all_data:
            raise ValueError("Dataset is empty. Call preprocess() first.")
        
        # Shuffle the data
        indices = np.arange(len(self._all_data))
        np.random.shuffle(indices)
        
        # Calculate split sizes
        train_size = int(len(indices) * self.train_ratio)
        val_size = int(len(indices) * self.val_ratio)
        
        # Split indices
        train_indices = indices[:train_size]
        val_indices = indices[train_size:train_size + val_size]
        test_indices = indices[train_size + val_size:]
        
        # Create the splits
        self._train_data = [self._all_data[i] for i in train_indices]
        self._val_data = [self._all_data[i] for i in val_indices]
        self._test_data = [self._all_data[i] for i in test_indices]
        
        logger.info(f"Data split: {len(self._train_data)} training samples, "
                   f"{len(self._val_data)} validation samples, "
                   f"{len(self._test_data)} test samples")
    
    def get_all_data(self) -> List[Dict[str, Any]]:
        """Get all data samples.
        
        Returns:
            List of all data samples.
        """
        return self._all_data
    
    def get_train_data(self) -> List[Dict[str, Any]]:
        """Get training data samples.
        
        Returns:
            List of training data samples.
        """
        return self._train_data
    
    def get_val_data(self) -> List[Dict[str, Any]]:
        """Get validation data samples.
        
        Returns:
            List of validation data samples.
        """
        return self._val_data
    
    def get_test_data(self) -> List[Dict[str, Any]]:
        """Get test data samples.
        
        Returns:
            List of test data samples.
        """
        return self._test_data
    
    def save(self, path: str):
        """Save the processed dataset to disk.
        
        Args:
            path: Path to save the dataset.
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({
                "all_data": self._all_data,
                "train_data": self._train_data,
                "val_data": self._val_data,
                "test_data": self._test_data,
            }, f)
        logger.info(f"Dataset saved to {path}")
    
    def load(self, path: str):
        """Load a processed dataset from disk.
        
        Args:
            path: Path to load the dataset from.
        """
        if not os.path.exists(path):
            raise ValueError(f"Dataset file {path} does not exist.")
        
        with open(path, "rb") as f:
            data = pickle.load(f)
        
        self._all_data = data["all_data"]
        self._train_data = data["train_data"]
        self._val_data = data["val_data"]
        self._test_data = data["test_data"]
        
        logger.info(f"Dataset loaded from {path}")
    
    def stat(self):
        """Print statistics about the dataset."""
        logger.info(f"Dataset Statistics:")
        logger.info(f"  Total samples: {len(self._all_data)}")
        logger.info(f"  Training samples: {len(self._train_data)}")
        logger.info(f"  Validation samples: {len(self._val_data)}")
        logger.info(f"  Test samples: {len(self._test_data)}")
        
        # Subclasses can override this to provide more detailed statistics 