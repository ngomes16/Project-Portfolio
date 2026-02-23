"""
MIMIC-III LOINC Mapping Dataset

This module contains the MIMIC3LOINCMappingDataset class for loading and processing
MIMIC-III lab data for LOINC mapping tasks.
"""

import os
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
import re
from itertools import groupby
from collections import defaultdict

from .base_dataset import BaseDataset

logger = logging.getLogger(__name__)

class MIMIC3LOINCMappingDataset(BaseDataset):
    """MIMIC-III LOINC mapping dataset for standardization tasks.
    
    This dataset loads and processes MIMIC-III lab test data for LOINC code
    standardization tasks. It creates source-target pairs from MIMIC-III
    lab test descriptions and their corresponding LOINC codes.
    
    Args:
        root: The root directory of MIMIC-III files.
        d_labitems_path: Path to the d_labitems.csv file relative to root.
        loinc_table_path: Path to the LOINC table file relative to root.
        train_ratio: Ratio of data to use for training.
        val_ratio: Ratio of data to use for validation.
        test_ratio: Ratio of data to use for testing.
        seed: Random seed for reproducibility.
        sample_mode: How to create source-target pairs.
        min_count: Minimum number of instances required for a lab item.
        cache_path: Path to save or load the preprocessed dataset.
    """
    
    def __init__(
        self,
        root: str,
        d_labitems_path: str = "d_labitems.csv",
        loinc_table_path: Optional[str] = None,
        train_ratio: float = 0.7,
        val_ratio: float = 0.1,
        test_ratio: float = 0.2,
        seed: int = 42,
        sample_mode: str = "one_per_itemid",
        min_count: int = 1,
        cache_path: Optional[str] = None,
    ):
        """Initialize the MIMIC-III LOINC mapping dataset."""
        super().__init__(
            root=root,
            seed=seed,
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
        )
        
        self.d_labitems_path = os.path.join(root, d_labitems_path)
        if not os.path.exists(self.d_labitems_path):
            raise ValueError(f"d_labitems file not found at {self.d_labitems_path}")
        
        self.loinc_table_path = os.path.join(root, loinc_table_path) if loinc_table_path else None
        if self.loinc_table_path and not os.path.exists(self.loinc_table_path):
            logger.warning(f"LOINC table file not found at {self.loinc_table_path}. "
                           f"Will proceed without LOINC descriptions.")
            self.loinc_table_path = None
        
        self.sample_mode = sample_mode
        self.min_count = min_count
        self.cache_path = cache_path
        
        # LOINC code text representations
        self.target_loinc_texts = {}
        
        # Try to load from cache if provided
        if cache_path and os.path.exists(cache_path):
            logger.info(f"Loading cached dataset from {cache_path}")
            self.load(cache_path)
        else:
            # Otherwise preprocess from scratch
            self.preprocess()
            self.split_data()
            
            # Save to cache if path provided
            if cache_path:
                logger.info(f"Saving preprocessed dataset to {cache_path}")
                self.save(cache_path)
    
    def _load_loinc_table(self):
        """Load and process the LOINC table to get text representations."""
        if not self.loinc_table_path:
            logger.info("No LOINC table provided, skipping LOINC text processing.")
            return
        
        logger.info(f"Loading LOINC table from {self.loinc_table_path}")
        
        try:
            loinc_df = pd.read_csv(self.loinc_table_path)
            
            # Extract key columns for text representations
            required_columns = ['LOINC_NUM']
            text_columns = [
                'LONG_COMMON_NAME',  # LCN
                'SHORTNAME',         # SN
                'DISPLAY_NAME',      # DN
                'COMPONENT',         # COMP
            ]
            
            # Check if required columns exist
            missing_columns = [col for col in required_columns if col not in loinc_df.columns]
            if missing_columns:
                logger.warning(f"Missing required LOINC columns: {missing_columns}")
                return
            
            # Check which text columns are available
            available_text_columns = [col for col in text_columns if col in loinc_df.columns]
            if not available_text_columns:
                logger.warning("No text representation columns found in LOINC table.")
                return
            
            # Create a dictionary of LOINC codes to text representations
            self.target_loinc_texts = {}
            
            for _, row in loinc_df.iterrows():
                loinc_code = row['LOINC_NUM']
                text_variants = []
                
                # Add each available text representation with its type
                if 'LONG_COMMON_NAME' in available_text_columns and pd.notna(row['LONG_COMMON_NAME']):
                    text_variants.append(('LCN', row['LONG_COMMON_NAME']))
                
                if 'SHORTNAME' in available_text_columns and pd.notna(row['SHORTNAME']):
                    text_variants.append(('SN', row['SHORTNAME']))
                
                if 'DISPLAY_NAME' in available_text_columns and pd.notna(row['DISPLAY_NAME']):
                    text_variants.append(('DN', row['DISPLAY_NAME']))
                
                # Create a component+system representation if available
                if 'COMPONENT' in available_text_columns and pd.notna(row['COMPONENT']):
                    component = row['COMPONENT']
                    system = row['SYSTEM'] if 'SYSTEM' in loinc_df.columns and pd.notna(row['SYSTEM']) else ""
                    if component and system:
                        text_variants.append(('COMP+SYS', f"{component} in {system}"))
                    elif component:
                        text_variants.append(('COMP', component))
                
                if text_variants:
                    self.target_loinc_texts[loinc_code] = text_variants
            
            logger.info(f"Processed {len(self.target_loinc_texts)} LOINC codes with text representations.")
            
        except Exception as e:
            logger.error(f"Error loading LOINC table: {str(e)}")
            self.target_loinc_texts = {}
    
    def _normalize_text(self, text):
        """Normalize text by removing special characters and extra spaces."""
        if pd.isna(text):
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Replace special characters with spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Replace multiple spaces with a single space
        text = re.sub(r'\s+', ' ', text)
        
        # Strip leading and trailing spaces
        text = text.strip()
        
        return text
    
    def _create_source_text(self, label, fluid, category=None, additional_info=None):
        """Create a standardized source text from lab test attributes."""
        parts = []
        
        # Add the primary components
        if label and not pd.isna(label):
            parts.append(self._normalize_text(label))
        
        if fluid and not pd.isna(fluid):
            parts.append(self._normalize_text(fluid))
        
        # Add category if provided
        if category and not pd.isna(category):
            category = self._normalize_text(category)
            # Only add if it's not already part of the label
            if category not in parts[0]:
                parts.append(category)
        
        # Add any additional info
        if additional_info and not pd.isna(additional_info):
            parts.append(self._normalize_text(additional_info))
        
        # Join with spaces
        source_text = " ".join(parts)
        
        return source_text
    
    def preprocess(self):
        """Preprocess the MIMIC-III lab data to create source-target pairs."""
        logger.info("Preprocessing MIMIC-III lab data...")
        
        # Load LOINC table if available
        self._load_loinc_table()
        
        # Load the d_labitems file
        try:
            d_labitems_df = pd.read_csv(self.d_labitems_path)
            
            # Check required columns
            required_columns = ['ITEMID', 'LABEL', 'FLUID', 'LOINC_CODE']
            missing_columns = [col for col in required_columns if col not in d_labitems_df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns in d_labitems.csv: {missing_columns}")
            
            # Filter out rows without LOINC codes
            d_labitems_df = d_labitems_df.dropna(subset=['LOINC_CODE'])
            logger.info(f"Found {len(d_labitems_df)} lab items with LOINC codes.")
            
            # Group by itemid
            grouped_by_itemid = d_labitems_df.groupby('ITEMID')
            
            # Create data samples based on the specified mode
            self._all_data = []
            
            if self.sample_mode == "one_per_itemid":
                # One sample per unique itemid
                for itemid, group in grouped_by_itemid:
                    # Use first row for each itemid
                    row = group.iloc[0]
                    
                    # Create source text from label and fluid
                    source_text = self._create_source_text(
                        row['LABEL'], 
                        row['FLUID'],
                        row['CATEGORY'] if 'CATEGORY' in row else None
                    )
                    
                    # Use LOINC code as target
                    target_loinc = row['LOINC_CODE']
                    
                    # Add to dataset
                    self._all_data.append({
                        'itemid': itemid,
                        'source_text': source_text,
                        'target_loinc': target_loinc,
                    })
            
            elif self.sample_mode == "all_combinations":
                # Create all possible label + fluid combinations for each LOINC code
                for target_loinc, group in d_labitems_df.groupby('LOINC_CODE'):
                    # Get unique labels and fluids
                    unique_labels = group['LABEL'].unique()
                    unique_fluids = group['FLUID'].unique()
                    
                    # Create combinations
                    for label in unique_labels:
                        for fluid in unique_fluids:
                            # Check if this combination exists
                            matching_rows = group[(group['LABEL'] == label) & (group['FLUID'] == fluid)]
                            if len(matching_rows) > 0:
                                source_text = self._create_source_text(label, fluid)
                                
                                # Add to dataset
                                self._all_data.append({
                                    'itemid': matching_rows.iloc[0]['ITEMID'],
                                    'source_text': source_text,
                                    'target_loinc': target_loinc,
                                })
            
            else:
                raise ValueError(f"Unknown sample mode: {self.sample_mode}")
            
            # Remove duplicates (based on source_text and target_loinc)
            seen = set()
            unique_data = []
            
            for item in self._all_data:
                key = (item['source_text'], item['target_loinc'])
                if key not in seen:
                    seen.add(key)
                    unique_data.append(item)
            
            self._all_data = unique_data
            
            logger.info(f"Created {len(self._all_data)} unique source-target pairs.")
            
        except Exception as e:
            logger.error(f"Error preprocessing MIMIC-III lab data: {str(e)}")
            raise e
    
    def stat(self):
        """Print statistics about the dataset."""
        super().stat()
        
        if not self._all_data:
            return
        
        # Count unique LOINC codes
        unique_loinc_codes = set(item['target_loinc'] for item in self._all_data)
        logger.info(f"  Unique LOINC codes: {len(unique_loinc_codes)}")
        
        # Count distribution of LOINC codes
        loinc_counts = {}
        for item in self._all_data:
            loinc = item['target_loinc']
            loinc_counts[loinc] = loinc_counts.get(loinc, 0) + 1
        
        # Print top 5 most frequent LOINC codes
        top_loinc = sorted(loinc_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        logger.info(f"  Top 5 most frequent LOINC codes:")
        for loinc, count in top_loinc:
            loinc_name = ""
            if self.target_loinc_texts and loinc in self.target_loinc_texts:
                lcn_variants = [v for v in self.target_loinc_texts[loinc] if v[0] == 'LCN']
                if lcn_variants:
                    loinc_name = f" ({lcn_variants[0][1]})"
            
            logger.info(f"    {loinc}{loinc_name}: {count} samples")
    
    def get_loinc_text_representation(self, loinc_code: str, text_type: str = 'LCN') -> Optional[str]:
        """Get a text representation for a LOINC code.
        
        Args:
            loinc_code: The LOINC code to get a text representation for.
            text_type: The type of text representation to retrieve (LCN, SN, DN, COMP, etc.).
            
        Returns:
            The text representation or None if not available.
        """
        if not self.target_loinc_texts or loinc_code not in self.target_loinc_texts:
            return None
        
        # Find the first matching text representation
        matching_variants = [v for v in self.target_loinc_texts[loinc_code] if v[0] == text_type]
        if matching_variants:
            return matching_variants[0][1]
        
        # If no matching variant, return the first available
        return self.target_loinc_texts[loinc_code][0][1] 