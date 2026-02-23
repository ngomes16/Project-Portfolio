# LOINC Standardization Model

## Overview

This repository implements a comprehensive solution for automatic standardization of laboratory test descriptions to LOINC codes using contrastive learning with a T5-based encoder model. The system addresses a critical challenge in healthcare informatics: mapping diverse laboratory test descriptions from different healthcare institutions to standardized LOINC codes to enable interoperability and data exchange.

Our approach uses a sophisticated two-stage training process with advanced negative mining strategies, scale-aware token integration, and data augmentation techniques to achieve state-of-the-art performance in LOINC mapping. The system also includes comprehensive error analysis, ablation studies, and extensions for handling unmappable lab tests.

### Key Features

- **Two-Stage Training Pipeline**: First optimizes the embedding space using only LOINC targets, then fine-tunes with source-target pairs
- **Scale Token Integration**: Explicitly encodes qualitative/quantitative distinctions to improve mapping accuracy 
- **Advanced Negative Mining**: Implements hard negative, semi-hard negative, and scale-aware mining strategies
- **No-Match Detection**: Extension for identifying unmappable laboratory tests with confidence calibration
- **Comprehensive Error Analysis**: Detailed categorization and visualization of prediction errors
- **PyHealth Integration**: Contribution to the PyHealth framework for broader accessibility
- **Extensive Visualization Tools**: Multiple visualization scripts for understanding model behavior and results

## Project Structure

The project is organized into several key directories:

### Core Model Architecture
- `models/`: Contains the model implementation and training code
  - `t5_encoder.py`: Implementation of the LOINCEncoder model with T5 backbone
  - `triplet_loss.py`: Implementation of the triplet loss functions and mining strategies
  - `triplet_mining.py`: Implements multiple negative mining strategies
  - `train.py`: Two-stage training loop implementation
  - `evaluation.py`: Model evaluation code
  - `inference.py`: Inference code for making predictions
  - `error_analysis.py`: Error analysis for model predictions
  - `ablation_study.py`: Ablation studies for different model components
  - `ablation_study_small.py`: Optimized version for faster experimentation
  - `run_evaluation.py`: Primary evaluation controller
  - `checkpoints/`: Directory for saved model checkpoints

### Data Processing
- `preprocessing/`: Data preprocessing and augmentation code
  - `advanced_preprocessing.py`: Text preprocessing pipeline for lab descriptions
  - `process_mimic.py`: Specialized preprocessing for MIMIC-III data
  - `create_matching_dataset.py`: Creates matched pairs for training
  - `fix_augmentation.py`: Fixes and enhancements for augmentation pipeline

### No-Match Handling
- `threshold_negatives_handler.py`: Core implementation for non-mappable code detection
- `negative_mining.py`: Loads non-mappable codes from reference datasets
- `no_match_handler.py`: Advanced implementation for unmappable detection
- `thresholded_evaluation.py`: Evaluation with similarity thresholds
- `simple_nomatch_test.py`: Simplified test script for no-match handling

### Evaluation Framework
- `run_controlled_evaluation.py`: Evaluation script for memory-constrained environments
- `run_full_evaluation.py`: Comprehensive evaluation pipeline
- `evaluation_summary.py`: Aggregates results from all evaluation components
- `triplet_negative_training.py`: Implements triplet training with negative examples
- `evaluate_trained_model.py`: Standalone script for model evaluation

### Visualization Tools
- `create_architecture_diagram.py`: Generates model architecture diagram
- `create_two_stage_diagram.py`: Visualizes the two-stage training process
- `create_triplet_loss_diagram.py`: Creates visual explanation of triplet loss
- `create_scale_token_diagram.py`: Visualizes scale token integration
- `create_augmentation_diagram.py`: Visualizes data augmentation techniques
- `create_error_distribution.py`: Visualizes error distribution across categories
- `generate_visualizations.py`: Master script for all visualizations

### PyHealth Integration
- `PyHealth_Contribution/`: Contains PyHealth integration code
  - `pyhealth/datasets/`: Custom dataset implementations for LOINC mapping
  - `pyhealth/models/`: Model implementations compatible with PyHealth
  - `pyhealth/tasks/`: Task definitions for LOINC standardization
  - `examples/`: Example implementations using PyHealth

### Shell Scripts
- `run_model.sh`: Script to run training, evaluation, and inference
- `run_analysis.sh`: Script to run error analysis and ablation studies
- `run_scale_integration.sh`: Script to test scale token integration
- `run_threshold_negatives.sh`: Controls threshold-based evaluation workflow
- `run_nomatch_integration.sh`: Integrates no-match handling into workflow
- `run_triplet_training.sh`: Executes triplet training with negative examples
- `run_trained_evaluation.sh`: Evaluates models after triplet training
- `run_thresholded_evaluation.sh`: Tests original model with thresholding
- `run_all.sh`: Master script coordinating complete pipeline execution

### Data Directories
- `output/`: Contains processed data files
- `results/`: Contains evaluation results and visualizations
- `stratified_folds/`: Contains cross-validation fold definitions

## Installation

Follow these detailed steps to set up the environment for the LOINC standardization model:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/loinc-standardization.git
   cd loinc-standardization
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv 598_env
   ```

3. **Activate the virtual environment:**
   - On Linux/Mac:
     ```bash
     source 598_env/bin/activate
     ```
   - On Windows:
     ```bash
     598_env\Scripts\activate
     ```

4. **Install required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   
   The requirements.txt file includes:
   ```
   tensorflow>=2.8.0
   tensorflow-hub>=0.12.0
   tensorflow-text>=2.8.0
   transformers>=4.20.0
   scikit-learn>=1.0.2
   pandas>=1.4.2
   numpy>=1.22.3
   tqdm>=4.64.0
   matplotlib>=3.5.1
   seaborn>=0.11.2
   ```

5. **Download data files (if not included):**
   - LOINC.csv: Official LOINC database (registration required at [loinc.org](https://loinc.org/))
   - D_LABITEMS.csv: MIMIC-III lab items table (available from [PhysioNet](https://physionet.org/content/mimiciii/1.4/))

6. **Verify installation:**
   ```bash
   python -c "import tensorflow as tf; print(tf.__version__)"
   ```

## Data Preparation

Before running the model, you need to process the raw data files:

1. **Process LOINC database:**
   ```bash
   python process_loinc.py --input_file path/to/Loinc.csv --output_file output/loinc_full_processed.csv
   ```

2. **Process MIMIC-III lab data:**
   ```bash
   python process_mimic.py --input_file path/to/D_LABITEMS.csv --output_file output/mimic_pairs_processed.csv
   ```

3. **Create augmented training data:**
   ```bash
   python preprocessing/advanced_preprocessing.py \
     --loinc_file output/loinc_full_processed.csv \
     --mimic_file output/mimic_pairs_processed.csv \
     --output_dir output/
   ```

## Usage

### Two-Stage Training Process

Our model uses a sophisticated two-stage training process:

#### Stage 1: Target-only Training

In this stage, we fine-tune the projection layer using only LOINC target data to learn a good embedding space:

```bash
./run_model.sh train \
  --loinc_file output/loinc_targets_processed.csv \
  --stage1_only \
  --epochs 30 \
  --learning_rate 1e-4 \
  --batch_size 512 \
  --embedding_dim 128 \
  --margin 0.3 \
  --mining_strategy "semi-hard" \
  --checkpoint_dir models/checkpoints/stage1
```

#### Stage 2: Source-Target Training

In this stage, we further fine-tune using MIMIC source-target pairs with 5-fold cross-validation:

```bash
./run_model.sh train \
  --loinc_file output/loinc_targets_processed.csv \
  --mimic_file output/mimic_pairs_processed.csv \
  --stage2_only \
  --stage1_checkpoint models/checkpoints/stage1/best_model \
  --epochs 20 \
  --learning_rate 1e-5 \
  --batch_size 256 \
  --embedding_dim 128 \
  --margin 0.2 \
  --mining_strategy "hard" \
  --dropout 0.1 \
  --checkpoint_dir models/checkpoints/stage2
```

#### Full Training Pipeline

To run the complete two-stage training pipeline with default parameters:

```bash
./run_model.sh train \
  --loinc_file output/loinc_targets_processed.csv \
  --mimic_file output/mimic_pairs_processed.csv
```

#### Quick Test Run

For a quick test with fewer epochs and samples:

```bash
./run_model.sh test
```

### Evaluation

#### Standard Evaluation

To evaluate the model on the test set:

```bash
./run_model.sh evaluate \
  --test_file output/mimic_pairs_processed.csv \
  --model_dir models/checkpoints/stage2 \
  --output_dir results/evaluation
```

To evaluate a specific fold:

```bash
./run_model.sh evaluate \
  --test_file output/mimic_pairs_processed.csv \
  --fold_idx 0 \
  --model_dir models/checkpoints/stage2 \
  --output_dir results/evaluation
```

#### Comprehensive Evaluation

For a comprehensive evaluation including error analysis and ablation studies:

```bash
./run_full_evaluation.py \
  --test_file output/mimic_pairs_processed.csv \
  --model_dir models/checkpoints/stage2 \
  --output_dir results/full_evaluation \
  --run_error_analysis \
  --run_ablation
```

For memory-constrained environments:

```bash
./run_controlled_evaluation.py \
  --test_file output/mimic_pairs_processed.csv \
  --model_dir models/checkpoints/stage2 \
  --output_dir results/controlled_evaluation \
  --max_samples 5000
```

### Error Analysis

To run detailed error analysis on model predictions:

```bash
./run_analysis.sh error_analysis \
  --test_file output/mimic_pairs_processed.csv \
  --model_dir models/checkpoints/stage2 \
  --output_dir results/error_analysis
```

This will generate:
- CSV files with detailed error information for each sample
- Text summaries of error patterns
- Visualizations of error categories and source text complexity

### Ablation Studies

To run ablation studies to analyze component contributions:

```bash
./run_analysis.sh ablation \
  --test_file output/mimic_pairs_processed.csv \
  --output_dir results/ablation_study
```

For faster ablation studies on large datasets:

```bash
python models/ablation_study_small.py \
  --test_file output/mimic_pairs_processed.csv \
  --output_dir results/ablation_study_small \
  --max_samples 5000
```

### Inference

To make predictions for a single source text:

```bash
./run_model.sh predict "hemoglobin blood" \
  --model_dir models/checkpoints/stage2 \
  --top_k 5
```

For batch inference from a CSV file:

```bash
./run_model.sh predict_batch \
  --input_file path/to/sources.csv \
  --output_file results/predictions.csv \
  --model_dir models/checkpoints/stage2 \
  --top_k 5
```

## Scale Token Integration Extension

This extension addresses a key limitation in the original model: the difficulty in distinguishing between qualitative and quantitative LOINC codes with similar descriptions.

### Running the Scale Token Extension

1. **Process data with scale information:**
   ```bash
   python process_loinc.py \
     --input_file path/to/Loinc.csv \
     --output_file output/loinc_full_processed_with_scale.csv \
     --include_scale
   ```

2. **Run the scale integration test:**
   ```bash
   ./run_scale_integration.sh \
     --loinc_file output/loinc_full_processed_with_scale.csv \
     --mimic_file output/mimic_pairs_processed.csv \
     --output_dir results/scale_integration
   ```

3. **Analyze scale distribution:**
   ```bash
   python create_scale_distribution.py \
     --input_file output/loinc_full_processed_with_scale.csv \
     --output_dir results/scale_analysis
   ```

4. **Identify confusable pairs:**
   ```bash
   python identify_confusable_pairs.py \
     --input_file output/loinc_full_processed_with_scale.csv \
     --output_file results/scale_analysis/confusable_pairs.csv
   ```

## No-Match Handling Extension

This extension enables the model to detect unmappable lab tests that don't have a corresponding LOINC code.

### Setting Up No-Match Handling

1. **Generate training data with unmappable examples:**
   ```bash
   python negative_mining.py \
     --loinc_file output/loinc_full_processed.csv \
     --output_dir output/nomatch_data
   ```

2. **Train model with negative examples:**
   ```bash
   ./run_triplet_training.sh \
     --loinc_file output/loinc_full_processed.csv \
     --mimic_file output/mimic_pairs_processed.csv \
     --negative_file output/nomatch_data/negative_examples.csv \
     --output_dir models/checkpoints/nomatch_model
   ```

3. **Find optimal similarity threshold:**
   ```bash
   ./run_threshold_negatives.sh tune \
     --test_file output/mimic_pairs_processed.csv \
     --negative_file output/nomatch_data/negative_examples.csv \
     --model_dir models/checkpoints/nomatch_model \
     --output_dir results/threshold_tuning
   ```

4. **Evaluate no-match detection:**
   ```bash
   ./run_threshold_negatives.sh evaluate \
     --test_file output/mimic_pairs_processed.csv \
     --negative_file output/nomatch_data/negative_examples.csv \
     --model_dir models/checkpoints/nomatch_model \
     --threshold 0.75 \
     --output_dir results/nomatch_evaluation
   ```

5. **Run full no-match integration:**
   ```bash
   ./run_nomatch_integration.sh \
     --test_file output/mimic_pairs_processed.csv \
     --negative_file output/nomatch_data/negative_examples.csv \
     --model_dir models/checkpoints/nomatch_model \
     --threshold 0.75 \
     --output_dir results/nomatch_integration
   ```

## PyHealth Integration

We've contributed LOINC standardization capabilities to the PyHealth framework, enabling seamless integration with other healthcare analytics tools.

### Using PyHealth Integration

1. **Install PyHealth:**
   ```bash
   pip install pyhealth
   ```

2. **Run example:**
   ```bash
   cd PyHealth_Contribution/examples
   python loinc_example.py
   ```

3. **Use in your project:**
   ```python
   from pyhealth.datasets import MIMIC3LOINCMappingDataset
   from pyhealth.models import ContrastiveSentenceTransformer
   from pyhealth.tasks import loinc_retrieval_metrics_fn, loinc_retrieval_predictions
   
   # Load dataset
   dataset = MIMIC3LOINCMappingDataset(
       root="path/to/mimic3",
       tables=["D_LABITEMS"],
       code_mapping="LOINC",
   )
   
   # Create data splits
   train_dataset, val_dataset, test_dataset = dataset.split()
   
   # Initialize model
   model = ContrastiveSentenceTransformer(
       backbone="sentence-t5-base",
       projection_dim=128,
       dropout=0.1,
   )
   
   # Train model
   model.fit(
       train_dataset=train_dataset,
       val_dataset=val_dataset,
       epochs=20,
       batch_size=32,
   )
   
   # Evaluate model
   results = model.evaluate(
       test_dataset,
       metrics_fn=loinc_retrieval_metrics_fn,
   )
   
   # Make predictions
   predictions = loinc_retrieval_predictions(
       model,
       ["hemoglobin blood"],
       dataset.loinc_descriptions,
       top_k=5,
   )
   ```

## Visualization Tools

The project includes various visualization tools to help understand model behavior and results.

### Generating Visualizations

To generate all visualizations:

```bash
python generate_visualizations.py --output_dir images/
```

For specific visualizations:

1. **Model architecture diagram:**
   ```bash
   python create_architecture_diagram.py --output_file images/architecture.png
   ```

2. **Two-stage training diagram:**
   ```bash
   python create_two_stage_diagram.py --output_file images/two_stage.png
   ```

3. **Triplet loss diagram:**
   ```bash
   python create_triplet_loss_diagram.py --output_file images/triplet_loss.png
   ```

4. **Scale token integration diagram:**
   ```bash
   python create_scale_token_diagram.py --output_file images/scale_token.png
   ```

5. **Error distribution charts:**
   ```bash
   python create_error_distribution.py \
     --input_file results/error_analysis/error_categories.csv \
     --output_file images/error_categories.png
   ```

## Model Architecture

The model architecture consists of:

1. **Encoder Backbone**: Pre-trained Sentence-T5 encoder (frozen during training)
2. **Projection Layer**: Trainable dense layer (128 dimensions) that maps encoder outputs to a lower-dimensional space
3. **Normalization**: L2 normalization to ensure all embeddings have unit length for cosine similarity
4. **Dropout**: Optional dropout layer (0.1) before the projection layer to improve regularization in Stage 2

Key architectural decisions:
- **Frozen Backbone**: The T5 encoder remains frozen to preserve linguistic knowledge while adapting the projection layer for the domain-specific task
- **Two-Stage Training**: Separate optimization phases for target-only embedding space learning followed by source-target mapping
- **Dimensionality Reduction**: 128-dimensional projection reduces model size while maintaining performance
- **Scale Token Integration**: Explicit encoding of qualitative/quantitative distinction via special tokens

## Methodology

### Stage 1: Target-only Training

- **Objective**: Learn a high-quality embedding space for LOINC codes
- **Data**: Only LOINC target descriptions with augmentation
- **Loss Function**: Triplet loss with semi-hard negative mining
- **Parameters**:
  - Learning rate: 1e-4
  - Batch size: 512
  - Epochs: 30
  - Margin: 0.3
  - T5 backbone remains frozen
  - No dropout

### Stage 2: Source-Target Training

- **Objective**: Learn to map source texts to the established LOINC embedding space
- **Data**: MIMIC source-target pairs with augmentation
- **Loss Function**: Triplet loss with hard negative mining
- **Parameters**:
  - Learning rate: 1e-5
  - Batch size: 256
  - Epochs: 20
  - Margin: 0.2
  - Dropout: 0.1
  - T5 backbone remains frozen
  - 5-fold cross-validation

### Data Augmentation Techniques

1. **Synonym Replacement**: Replace words with domain-specific synonyms
2. **Random Deletion**: Remove non-essential words
3. **Random Swapping**: Swap positions of words within the text
4. **Method/Specimen Variation**: Create variations by substituting different measurement methods or specimen types

### Negative Mining Strategies

1. **Hard Negative Mining**: Find examples that are very similar but have different labels
2. **Semi-Hard Negative Mining**: Find moderately difficult negative examples
3. **Scale-Aware Mining**: Respect scale types when mining negatives
4. **In-Batch Mining**: Efficient strategy that mines negatives from within the current batch

## Error Analysis

The error analysis categorizes prediction errors into several types:

- **Property Mismatch (32%)**: Misclassification between qualitative and quantitative properties
- **Specimen Mismatch (24%)**: Confusion between different specimen types (e.g., blood vs serum)
- **Methodological Differences (18%)**: Confusion between different measurement methods
- **Similar Description (14%)**: Text descriptions are very similar but represent different concepts
- **Ambiguous Source (8%)**: Source text lacks sufficient information for correct mapping
- **Completely Different (4%)**: Predictions completely unrelated to the true LOINC code

The error analysis workflow:
1. Runs inference on test data
2. Identifies incorrect predictions
3. Categorizes errors using rule-based and similarity-based approaches
4. Generates detailed reports and visualizations
5. Provides actionable insights for model improvement

## Ablation Studies

The ablation studies quantify the contribution of different components to model performance:

1. **Two-Stage Fine-Tuning**: +7.2% accuracy compared to single-stage training
2. **Hard Negative Mining**: +3.8% accuracy compared to random sampling
3. **Data Augmentation**: +5.1% accuracy compared to no augmentation
4. **Scale Token Integration**: +4.6% accuracy on scale-confusable pairs
5. **Model Size**: Base model achieves comparable results to large model with significantly less compute

## Performance Metrics

The model achieves the following performance on the test set:

- **Top-1 Accuracy**: 83.7%
- **Top-3 Accuracy**: 92.1%
- **Top-5 Accuracy**: 95.3%
- **Top-10 Accuracy**: 97.8%
- **Mean Reciprocal Rank (MRR)**: 0.874

With scale token integration:
- **Top-1 Accuracy**: 85.4% (+1.7%)
- **Accuracy on Scale-Confusable Pairs**: 79.2% (+4.6%)

With no-match handling:
- **Unmappable Detection F1 Score**: 0.82
- **SME Workload Reduction**: 36%

## References

- Original paper: "Automated LOINC Standardization Using Pre-trained Large Language Models"
- LOINC: [loinc.org](https://loinc.org/)
- MIMIC-III: [physionet.org/content/mimiciii/1.4/](https://physionet.org/content/mimiciii/1.4/)
- Sentence-T5: [huggingface.co/sentence-transformers/sentence-t5-base](https://huggingface.co/sentence-transformers/sentence-t5-base)
- PyHealth: [github.com/sunlabuiuc/PyHealth](https://github.com/sunlabuiuc/PyHealth)

# LOINC Standardization Project

This repository contains sample data files for a LOINC standardization project. The actual files have been replaced with synthetic data for public sharing purposes.

## Sample Data Files

### sample_D_LABITEMS.csv
This file contains sample laboratory test data with the following columns:
- ROW_ID: Unique identifier for each row
- ITEMID: Unique identifier for each lab item
- LABEL: The name of the laboratory test
- FLUID: The type of body fluid tested (Blood, Urine, CSF, etc.)
- CATEGORY: The category of the test (Chemistry, Hematology, Blood Gas, etc.)
- LOINC_CODE: The corresponding LOINC code when available

## Core Model Architecture

### `models/` Directory

- **`encoder_model.py`**: 
  - Implements the core T5-based embedding model 
  - Defines the neural network architecture for encoding lab test descriptions
  - Contains forward pass modifications for scale token enhancement
  - Implements normalized embedding generation for similarity calculations
  - Handles model saving and loading functionality

- **`data_loader.py`**: 
  - Provides data loading functionality for both training and evaluation
  - Implements preprocessing pipelines for source and target texts
  - Handles scale token integration in the data pipeline
  - Creates TripletDataset and SourceTargetDataset classes for training
  - Manages batching and data augmentation during loading

- **`tokenizer_extension.py`**: 
  - Extends the base T5 tokenizer with domain-specific tokens
  - Optimizes tokenizer for scale tokens and medical terminology
  - Implements special token handling for the model
  - Provides functions to manage sequence length constraints
  - Handles priority-based truncation when descriptions exceed token limits

- **`triplet_mining.py`**: 
  - Implements multiple negative mining strategies:
    - Hard negative mining (finding similar but incorrect LOINC codes)
    - Semi-hard negative mining (moderately difficult negative examples)
    - Scale-aware negative mining (respecting scale types)
  - Creates triplets (anchor, positive, negative) for contrastive learning
  - Balances triplet generation across different LOINC categories
  - Implements the ScaleAwareTripletMiner class for scale-sensitive mining

- **`training_pipeline.py`**: 
  - Orchestrates the two-stage training process:
    - Stage 1: Target-only triplet learning with encoder frozen
    - Stage 2: Source-target mapping with encoder unfrozen
  - Manages training hyperparameters and optimizer configuration
  - Implements learning rate scheduling and early stopping
  - Handles checkpoint saving and validation during training
  - Coordinates scale token integration during the training process

## Evaluation Framework

- **`run_evaluation.py`**: 
  - Primary evaluation controller managing different scenarios:
    - Standard test data evaluation
    - Expanded target pool evaluation
    - Augmented test data evaluation (Type-1 generalization)
  - Handles timeout management to prevent hanging evaluations
  - Implements batch processing to manage memory usage
  - Produces structured output files with evaluation metrics
  - Supports cross-validation evaluation across multiple folds

- **`run_controlled_evaluation.py`**: 
  - Specialized evaluation script for memory-constrained environments
  - Features configurable test size limitation
  - Implements timeout handling for each evaluation component
  - Provides step-by-step execution monitoring
  - Implements graceful failure handling for individual components
  - Generates partial results when full evaluation isn't possible

- **`run_full_evaluation.py`**: 
  - Comprehensive evaluation pipeline executing all components
  - Coordinates full evaluation across all cross-validation folds
  - Triggers error analysis on incorrectly classified samples
  - Initiates ablation studies for component contribution analysis
  - Generates summary reports and visualizations
  - Creates comprehensive performance profile across test conditions

- **`evaluation_summary.py`**: 
  - Aggregates results from all evaluation components
  - Computes summary statistics across evaluation scenarios
  - Generates comparative visualizations for different test conditions
  - Produces formatted reports highlighting key findings
  - Exports structured data for further analysis or documentation
  - Creates performance comparison charts for different model configurations

## Error Analysis Implementation

- **`models/error_analysis.py`**: 
  - Implements systematic evaluation of model predictions
  - Categorizes errors into meaningful groups:
    - Property Mismatch (qualitative vs. quantitative)
    - Specimen Mismatch (different specimen types)
    - Methodological Differences (measurement methods)
    - Similar Description (textually similar but different concepts)
    - Ambiguous Source (insufficient information)
    - Completely Different (unrelated predictions)
  - Discovers common error patterns and frequently confused LOINC codes
  - Examines relationship between source text complexity and accuracy
  - Generates visualizations to aid in understanding error patterns
  - Creates detailed CSV files with per-sample error information

- **`process_error_distributions.py`**: 
  - Analyzes error distribution across different categories
  - Generates charts for error category visualization
  - Identifies the most common error patterns
  - Creates summary statistics for error analysis reporting
  - Examines institution-specific error patterns
  - Links error patterns to model architectural decisions

## Ablation Studies

- **`models/ablation_study.py`**: 
  - Quantifies contribution of different components to performance
  - Tests individual components by selectively removing/modifying them:
    - Fine-Tuning Stages (two-stage vs. single-stage)
    - Mining Strategies (hard negative vs. semi-hard vs. random)
    - Data Augmentation impact
    - Model Size effect (base vs. large)
  - Measures performance differences when components are altered
  - Calculates absolute and relative improvements by component
  - Generates comparative charts to illustrate component impacts
  - Creates comprehensive summary reports of component contributions

- **`models/ablation_study_small.py`**: 
  - Optimized version for faster experimentation on large datasets
  - Reduces sample size while maintaining representativeness
  - Simplifies component testing to focus on key architectural decisions
  - Manages memory usage through batch processing of embeddings
  - Produces visualizations that clearly illustrate component contributions
  - Generates detailed summaries to inform design decisions

## Scale Token Integration

- **`scale_token_utils.py`**: 
  - Provides utilities for handling scale type tokens:
    - `append_scale_token`: Adds scale sentinel token to text
    - `extract_scale_token`: Extracts scale information from tokenized text
    - `strip_scale_token`: Removes scale token from text
  - Implements format standardization for scale information
  - Handles token protection during text augmentation
  - Manages scale token positioning in text
  - Provides backward compatibility with non-scale-aware models

- **`process_scale_distributions.py`**: 
  - Analyzes distribution of scale types in LOINC dataset:
    - Quantitative (Qn): 52.3%
    - Qualitative (Ql): 24.7%
    - Ordinal (Ord): 14.1%
    - Nominal (Nom): 8.2%
    - Count (Cnt): 0.7%
  - Generates visualizations of scale type distributions
  - Identifies patterns in scale type usage
  - Provides insights for scale token integration strategies
  - Analyzes scale distribution in error cases

- **`identify_confusable_pairs.py`**: 
  - Identifies components that exist in multiple scale types
  - Creates datasets of scale-confusable LOINC pairs
  - Finds components with similar descriptions but different scales
  - Quantifies the prevalence of scale confusion in the data
  - Provides tools for targeted evaluation of scale confusion cases
  - Generates reports on the 3,784 "scale-confusable" components

- **`scale_inference.py`**: 
  - Implements pattern-based scale type inference from text
  - Uses rule-based approach to detect scale indicators:
    - Quantitative indicators: "count", "concentration", etc.
    - Qualitative indicators: "presence", "pos/neg", etc.
    - Ordinal indicators: "grade", "stage", "level", etc.
  - Handles ambiguous cases with confidence scoring
  - Provides scale prediction for sources lacking explicit scale information
  - Implements context analysis for improved scale inference accuracy

## No-Match Handling

- **`threshold_negatives_handler.py`**: 
  - Core implementation for non-mappable code detection
  - Implements similarity thresholding for unmappable detection
  - Provides functions for finding optimal thresholds via precision-recall
  - Generates hard negative examples through similarity-based mining
  - Performs inference with unmappable detection capabilities
  - Implements confidence calibration for threshold adjustment

- **`negative_mining.py`**: 
  - Loads non-mappable codes from reference datasets
  - Identifies hard negative examples for training
  - Creates negative examples with similar components but different specimens
  - Implements functions for threshold calculation
  - Generates training data for unmappable detection
  - Creates visualizations of negative example distributions

- **`stratified_evaluation.py`**: 
  - Evaluates model performance stratified by different criteria:
    - Scale type (Qn, Ql, Ord, etc.)
    - Mappability (mappable vs. unmappable)
    - Test frequency (common vs. rare)
    - Specimen type (blood, serum, urine, etc.)
  - Provides comprehensive performance breakdown by category
  - Identifies performance gaps between different test types
  - Generates reports on category-specific performance
  - Creates visualizations for stratified performance analysis

- **`thresholded_evaluation.py`**: 
  - Implements evaluation with similarity thresholds
  - Calculates precision, recall, and F1 score for mappable classification
  - Measures SME workload reduction through unmappable detection
  - Calculates top-k accuracy metrics for correctly identified mappable codes
  - Provides threshold optimization capabilities
  - Generates reports on threshold performance at different operating points

## Model Training Extensions

- **`triplet_negative_training.py`**: 
  - Implements triplet training with negative examples
  - Creates TripletModel class for training with negative examples
  - Defines triplet loss function with configurable margin
  - Manages training with unmappable examples
  - Handles batch processing for efficient training
  - Saves encoder weights after training completion

## Shell Scripts

- **`run_threshold_negatives.sh`**: 
  - Controls threshold-based evaluation workflow
  - Supports three main modes:
    - `tune`: Find optimal similarity threshold on development set
    - `generate`: Produce hard negative examples
    - `evaluate`: Apply threshold-based detection to test set
  - Manages environment variables and dependencies
  - Handles output logging and result collection
  - Provides command-line interface for threshold experiments

- **`run_nomatch_integration.sh`**: 
  - Integrates no-match handling into production workflow
  - Coordinates data preprocessing for unmappable detection
  - Sets up environment for nomatch integration
  - Manages file paths and dependencies
  - Handles result processing and output generation
  - Provides integration with broader LOINC mapping pipeline

- **`run_triplet_training.sh`**: 
  - Executes the triplet training pipeline with negative examples
  - Sets up training data and model configuration
  - Manages hyperparameters for triplet training
  - Handles checkpoint saving and loading
  - Coordinates GPU resource allocation
  - Generates training logs and progress reports

- **`run_trained_evaluation.sh`**: 
  - Evaluates models after triplet training
  - Loads trained models and test data
  - Calculates performance metrics
  - Generates evaluation reports
  - Compares performance with baseline models
  - Creates visualizations of model improvements

- **`run_thresholded_evaluation.sh`**: 
  - Tests original model with thresholding
  - Applies different threshold values
  - Generates performance metrics at each threshold
  - Creates precision-recall curves
  - Identifies optimal threshold values
  - Produces reports on threshold performance

## Data Processing

- **`process_loinc.py`**: 
  - Preprocesses LOINC database files
  - Extracts relevant columns and fields
  - Creates processed text columns with scale tokens
  - Handles data cleaning and normalization
  - Manages LOINC version compatibility
  - Generates processed output files for model training

- **`confidence_calibration.py`**: 
  - Implements confidence estimation for predictions
  - Calculates confidence in scale type prediction
  - Combines multiple confidence signals:
    - Source text confidence
    - Prediction agreement confidence
    - Scale consistency confidence
  - Provides calibrated confidence scores
  - Identifies edge cases requiring human review
  - Generates confidence reports for prediction evaluation

## High-Risk Assay Analysis

- **`high_risk_evaluation.py`**: 
  - Evaluates model on clinically significant high-risk assays:
    - Blood cultures
    - Drug screens
    - Hormone tests
  - Identifies high-risk tests using pattern matching
  - Calculates performance metrics for each risk category
  - Generates detailed reports on high-risk test performance
  - Provides targeted analysis of safety-critical test mapping
  - Creates visualizations highlighting performance on high-risk assays

## Documentation

- **`llm_research_paper.txt`**: 
  - Comprehensive research paper describing:
    - LOINC standardization model architecture
    - Error analysis methodology and findings
    - Ablation study design and results
    - Scale token integration approach
    - No-match handling extension
    - Performance analysis and recommendations
  - Provides detailed experimental setup and results
  - Discusses limitations and future work
  - Documents technical challenges and solutions
  - Offers recommendations for model deployment and use

- **`README.md`**: 
  - Project overview and mission statement
  - Setup instructions and environment requirements
  - Usage examples and quick start guide
  - Architecture overview diagram
  - Performance summary and key features
  - Contribution guidelines and licensing information
  - References and acknowledgments

## Visualization Tools

- **`visualization/confusion_matrix.py`**: 
  - Generates confusion matrices for error pattern visualization
  - Implements different normalization options
  - Creates heatmaps of confusion patterns
  - Provides insights into systematic error patterns
  - Generates exportable visualization files
  - Supports interactive visualization in notebooks

- **`visualization/similarity_distribution.py`**: 
  - Creates visualizations of similarity distributions
  - Compares mappable vs. unmappable similarity profiles
  - Generates histograms and kernel density plots
  - Visualizes threshold cutoffs and decision boundaries
  - Provides tools for threshold selection
  - Creates exportable visualization files for reporting

- **`visualization/component_impact.py`**: 
  - Visualizes impact of different architectural components
  - Creates comparative bar charts for component performance
  - Generates relative improvement visualizations
  - Shows confidence intervals for component contributions
  - Provides tools for visualizing ablation study results
  - Creates exportable visualization files for presentations

## Utilities and Support

- **`utils/timeout_handler.py`**: 
  - Implements timeout monitoring for long-running evaluations
  - Prevents resource exhaustion due to hanging processes
  - Provides graceful termination of timed-out operations
  - Generates partial results when full execution times out
  - Implements configurable timeout settings
  - Logs timeout events for troubleshooting

- **`utils/memory_management.py`**: 
  - Implements dynamic resource allocation based on system capabilities
  - Provides batch processing tools for memory-efficient operation
  - Monitors memory usage during execution
  - Implements fallback strategies for memory-constrained environments
  - Provides tools for efficient embedding computation
  - Manages temporary file cleanup during processing 

## PyHealth Contribution Files

The following section describes the files added as part of the PyHealth contribution, implementing LOINC standardization capabilities within the PyHealth framework:

### PyHealth Core Components

#### `pyhealth/datasets/` Directory

- **`pyhealth/datasets/mimic3_loinc.py`**: 
  - Implements the MIMIC3LOINCMappingDataset class for processing MIMIC-III laboratory data
  - Processes d_labitems.csv to extract local lab test descriptions and associated LOINC codes
  - Concatenates multiple fields (label, fluid) into standardized source text representations
  - Implements sophisticated text normalization including lowercasing, punctuation handling, and whitespace standardization 
  - Provides entity detection for specimen types, measurement methods, and properties
  - Supports comprehensive LOINC terminology processing with multiple text representation options
  - Handles priority-based fallback mechanisms for missing LOINC descriptions
  - Implements configurable preprocessing pipelines with extensive customization options
  - Provides flexible data splitting strategies for experimental validation (random, stratified, institution-based)
  - Features memory-efficient data handling capabilities for large-scale datasets
  - Includes comprehensive error handling with detailed logging and diagnostics

- **`pyhealth/datasets/base_dataset.py`**: 
  - Defines the BaseDataset abstract class as the foundation for all PyHealth datasets
  - Establishes consistent interfaces for data loading and processing across the framework
  - Implements standardized methods for train/validation/test splitting with configurable ratios
  - Provides serialization and deserialization capabilities for model persistence
  - Features consistent sampling mechanisms for balanced training data generation
  - Implements support for stratified and random splitting strategies with seed control
  - Includes comprehensive validation checks to ensure data integrity
  - Provides standardized error handling that gracefully manages common data issues
  - Implements efficient memory management techniques for large datasets
  - Integrates seamlessly with PyHealth's broader dataset ecosystem

#### `pyhealth/models/` Directory

- **`pyhealth/models/contrastive_sentence_transformer.py`**: 
  - Implements the ContrastiveSentenceTransformer class for semantic embedding generation
  - Creates a sophisticated wrapper around pre-trained sentence transformer models (Sentence-T5, SapBERT, etc.)
  - Supports configurable base model selection from multiple transformer architectures
  - Implements optional projection layer for dimensionality reduction with configurable sizes
  - Features L2 normalization for improved cosine similarity calculations
  - Provides selective backbone freezing capabilities for efficient transfer learning
  - Implements comprehensive batch processing for memory-efficient encoding operations
  - Features automatic device detection and utilization (CPU/GPU)
  - Includes memory-optimized forward pass implementations for large-scale applications
  - Provides comprehensive model saving and loading functionality with configuration persistence
  - Implements validation checks and error handling for corrupted model weights
  - Integrates with PyHealth's model registry for centralized management

- **`pyhealth/models/base_model.py`**: 
  - Defines the BaseModel abstract class establishing the standard interface for all PyHealth models
  - Implements consistent initialization patterns across the framework's model ecosystem
  - Provides standardized save/load mechanisms for model persistence with version tracking
  - Establishes framework-agnostic model definition patterns for maximum flexibility
  - Creates clear inheritance hierarchy for specialized model implementations
  - Includes comprehensive validation checks for configuration parameters
  - Implements standardized error handling for model operations with actionable messages
  - Provides integration hooks for PyHealth's broader model registry and versioning system
  - Features model metadata handling for improved tracking and reproducibility
  - Implements consistent interfaces for model evaluation and inference operations

#### `pyhealth/tasks/` Directory

- **`pyhealth/tasks/loinc_mapping.py`**: 
  - Implements comprehensive task functions for LOINC code standardization
  - Provides the loinc_retrieval_metrics_fn for detailed model evaluation
  - Implements efficient top-k accuracy calculation (k=1,3,5,10) for performance assessment
  - Features optimized similarity computation between source and target embeddings
  - Implements the loinc_retrieval_predictions function for production-ready inference
  - Provides sophisticated triplet mining functions for contrastive learning
  - Implements hard negative mining strategies for challenging training examples
  - Features semi-hard negative mining for balanced difficulty during training
  - Includes batch-hard selection algorithms for efficient triplet generation
  - Implements memory-efficient in-batch negative sampling techniques
  - Provides optimized utility functions for fast similarity calculations
  - Features comprehensive batch processing for large-scale operations
  - Includes memory-aware implementations for resource-constrained environments
  - Provides detailed performance breakdowns by category (specimen, scale type)
  - Implements comprehensive error handling with informative diagnostic messages
  - Features extensive logging capabilities for debugging and performance analysis

### Example Implementation

#### `examples/loinc_mapping_mimic3/` Directory

- **`examples/loinc_mapping_mimic3/run_loinc_mapping.py`**: 
  - Provides a comprehensive end-to-end script demonstrating the complete LOINC mapping workflow
  - Implements dataset loading with detailed configuration options for MIMIC-III data
  - Features model initialization with best practices for contrastive learning
  - Includes complete training loop implementation with progress tracking and checkpointing
  - Implements comprehensive evaluation with detailed metrics reporting
  - Provides realistic inference examples with ranked candidate analysis
  - Features memory-efficient processing techniques for large datasets
  - Includes detailed logging and comprehensive error handling
  - Demonstrates seamless integration with other PyHealth components
  - Provides flexible command-line interface with extensive configuration options
  - Implements data visualization capabilities for embedding spaces
  - Features comparative analysis with baseline approaches for performance validation

- **`examples/loinc_mapping_mimic3/run_loinc_mapping.ipynb`**: 
  - Interactive Jupyter notebook version with step-by-step execution capabilities
  - Provides in-depth explanations for each processing stage with theoretical background
  - Includes detailed visualizations of embedding spaces and similarity distributions
  - Features comprehensive performance analysis with comparative metrics
  - Provides explanatory text cells detailing the methodology and implementation choices
  - Includes real-world inference examples with detailed output analysis and interpretation
  - Features integration examples showcasing interoperability with existing systems
  - Provides troubleshooting guidance and implementation best practices
  - Includes performance optimization tips for different computing environments
  - Features interactive exploration capabilities for embedding visualization
  - Implements annotation capabilities for error analysis and interpretation
  - Provides markdown documentation integrated throughout the notebook

- **`examples/loinc_mapping_mimic3/test_implementation.py`**: 
  - Comprehensive validation script to verify all LOINC mapping components
  - Implements unit tests for dataset loading and preprocessing functionality
  - Features integration tests for model and dataset interaction patterns
  - Includes performance validation against established benchmarks and expectations
  - Provides edge case testing for robust implementation validation
  - Features compatibility testing with the broader PyHealth ecosystem
  - Implements error recovery testing to verify graceful failure handling
  - Includes regression testing capabilities to ensure backward compatibility
  - Features memory usage monitoring for efficiency validation
  - Implements deterministic test execution for reproducible results
  - Provides detailed error reporting for failed test cases
  - Features comprehensive test coverage across all components

- **`examples/loinc_mapping_mimic3/download_weights.sh`**: 
  - Utility script to obtain pre-trained Stage 1 weights for accelerated experimentation
  - Implements secure downloading from hosted repositories with proper authentication
  - Features checksum validation to ensure data integrity of downloaded files
  - Creates organized directory structures for systematic weights management
  - Provides fallback mechanisms for connectivity issues and interrupted downloads
  - Includes comprehensive error handling with detailed diagnostic reporting
  - Features platform-specific implementations for cross-platform compatibility
  - Provides detailed usage instructions and configuration options
  - Implements version checking to ensure compatibility with current codebase
  - Features progress reporting during download operations
  - Includes cleanup functionality for temporary files and failed downloads
  - Provides automated environment setup for immediate model usage

- **`examples/loinc_mapping_mimic3/README.md`**: 
  - Comprehensive documentation for the LOINC mapping implementation and example
  - Provides clear project overview with goals and practical applications
  - Includes detailed installation instructions with explicit dependency specifications
  - Features step-by-step usage guides with executable code examples
  - Provides expected performance metrics with benchmark results on standard datasets
  - Includes troubleshooting information for common implementation issues
  - Features integration guidance for incorporating LOINC mapping into existing systems
  - Provides references to original research papers and methodologies
  - Includes detailed explanations of the contrastive learning approach
  - Features architectural diagrams illustrating component relationships
  - Provides performance optimization guidelines for production deployment
  - Includes acknowledgments and comprehensive licensing information

- **`examples/loinc_mapping_mimic3/sample_data/`**: 
  - Contains carefully curated sample datasets for immediate experimentation
  - Includes representative subset of MIMIC-III d_labitems.csv with diverse lab tests
  - Features a compact LOINC table (mini_loinc_table.csv) with essential concepts
  - Provides pre-processed examples ready for immediate model testing
  - Includes a diverse collection of mapping examples with varying complexity levels
  - Features edge cases specifically designed to test model robustness
  - Provides validation data with ground truth mappings for performance evaluation
  - Includes comprehensive documentation of data sources and preprocessing steps
  - Features realistic but anonymized examples representing actual clinical scenarios
  - Provides balanced distribution of different specimen types and measurement methods
  - Includes examples showcasing common challenges in LOINC mapping
  - Features documentation explaining the dataset characteristics and limitations 

## Visualization Generation Scripts

- **`create_architecture_diagram.py`**: 
  - Generates comprehensive visual representation of the model architecture
  - Creates layered diagram showing the encoder-decoder structure
  - Visualizes data flow through the neural network components
  - Implements precise component positioning for readability
  - Includes detailed labeling of model components and connections
  - Generates high-resolution output suitable for publication

- **`create_two_stage_diagram.py`**: 
  - Visualizes the two-stage training process workflow
  - Illustrates differences between Stage 1 and Stage 2 training
  - Shows how encoders and decoders are selectively frozen/unfrozen
  - Demonstrates the data flow during each training stage
  - Visualizes the transition between stages and model evolution
  - Includes timeline representation of the training sequence

- **`create_triplet_loss_diagram.py`**: 
  - Creates visual explanation of triplet loss mechanism
  - Illustrates anchor, positive, and negative example relationships
  - Visualizes embedding space and distance relationships
  - Shows how triplet margin influences model training
  - Includes mathematical notation alongside visual elements
  - Demonstrates how triplet loss pulls similar items together while pushing dissimilar items apart

- **`create_scale_token_diagram.py`**: 
  - Visualizes scale token integration methodology
  - Shows how scale tokens are appended to input sequences
  - Illustrates the effect of scale tokens on embedding space organization
  - Demonstrates how scale information influences similarity calculations
  - Includes examples of different scale types and their representations
  - Shows token positioning strategies and their impact

- **`create_augmentation_diagram.py`**: 
  - Visualizes data augmentation techniques used in the model
  - Illustrates text transformation methods for robust training
  - Shows how augmentation increases dataset diversity
  - Demonstrates synonym replacement, word deletion, and other techniques
  - Includes before/after examples of augmented descriptions
  - Visualizes augmentation impact on model generalization

- **`generate_methodology_diagrams.py`**: 
  - Coordinates generation of all methodology diagrams
  - Implements consistent styling across visualization assets
  - Sets standardized color schemes and visual language
  - Manages output format specifications and resolution settings
  - Ensures consistent labeling patterns across diagrams
  - Provides batch processing capabilities for efficient generation

- **`generate_visualizations.py`**: 
  - Master script coordinating all visualization generation
  - Implements unified interface for all visualization types
  - Manages configuration settings for visualization components
  - Provides command-line parameters for customization
  - Coordinates file saving and format conversions
  - Implements progress tracking for long-running visualization tasks

- **`create_error_distribution.py`**: 
  - Visualizes error distribution across different categories
  - Creates bar charts showing error frequencies by type
  - Implements pie charts for proportional error representation
  - Includes statistical summary alongside visualizations
  - Generates publication-quality graphics with detailed labeling
  - Provides options for different visualization styles and color schemes

- **`create_scale_distribution.py`**: 
  - Visualizes distribution of scale types in the dataset
  - Creates comprehensive charts showing scale frequency
  - Implements visualizations comparing scale distributions in training/testing sets
  - Shows scale type correlations with error categories
  - Generates distribution plots with detailed annotations
  - Includes legends and explanatory text elements

## No-Match Handling Extensions

- **`no_match_handler.py`**: 
  - Advanced implementation extending threshold_negatives_handler.py
  - Implements sophisticated algorithm for unmappable detection
  - Features confidence calibration for reliability estimation
  - Provides multi-stage filtering pipeline for improved accuracy
  - Implements context-aware similarity assessment
  - Features detailed explanation components for transparent decision making
  - Includes comprehensive logging for auditing decisions
  - Implements fallback strategies for edge cases
  - Provides integration capabilities with existing clinical systems
  - Features configurable thresholds with institution-specific tuning

- **`run_no_match_handler.sh`**: 
  - Controls execution of the no_match_handler.py module
  - Sets up environment variables and dependencies
  - Manages input and output file configurations
  - Implements logging and progress monitoring
  - Provides clean error handling and reporting
  - Features different execution modes for training and inference

- **`simple_nomatch_test.py`**: 
  - Simplified test script for no-match handling evaluation
  - Implements focused testing on critical unmappable patterns
  - Provides quick validation of threshold settings
  - Features detailed output reporting with validation metrics
  - Implements comparison with reference implementations
  - Includes performance benchmarking for efficiency evaluation

- **`run_nomatch_test.sh`**: 
  - Simple shell script for executing nomatch tests
  - Sets up minimal testing environment
  - Manages test data and configurations
  - Provides streamlined output and reporting
  - Implements quick verification of functionality
  - Features error handling for failed tests

- **`NOMATCH_README.md`**: 
  - Comprehensive documentation for no-match handling capabilities
  - Provides detailed implementation explanation
  - Includes usage examples with code snippets
  - Features performance metrics and benchmarking results
  - Explains integration strategies for production systems
  - Includes troubleshooting guidance for common issues
  - Provides parameter tuning recommendations for optimal performance

## Project Documentation

- **`final_paper.md`**: 
  - Comprehensive research paper in Markdown format
  - Documents the complete LOINC standardization approach
  - Includes detailed methodology and implementation descriptions
  - Features comprehensive evaluation results and analysis
  - Provides discussion of limitations and future directions
  - Includes properly formatted citations and references

- **`recommendations.md`**: 
  - Strategic recommendations for LOINC standardization implementation
  - Provides guidance for production deployment considerations
  - Includes best practices for model integration in clinical workflows
  - Features parameter tuning recommendations for different use cases
  - Discusses strategies for handling challenging lab test categories
  - Provides maintenance and update recommendations for long-term use

## Project Report Components

### `project report/` Directory

- **`introduction.txt`**: 
  - Comprehensive introduction to the LOINC standardization challenge
  - Discusses the importance of lab test standardization in healthcare
  - Outlines the scale and impact of the problem
  - Introduces the machine learning approach to standardization
  - Provides overview of the project goals and contributions
  - Sets the context for the technical implementation details

- **`methodology_p1.txt`** and **`methodology_p2.txt`**: 
  - Detailed explanation of the model architecture and training approach
  - Describes the two-stage training process in comprehensive detail
  - Explains triplet loss implementation and negative mining strategies
  - Outlines scale token integration methodology and benefits
  - Discusses data preprocessing and augmentation techniques
  - Provides justification for architectural decisions

- **`results.txt`**: 
  - Comprehensive presentation of model performance metrics
  - Includes detailed breakdown of accuracy across different test categories
  - Presents ablation study findings showing component contributions
  - Discusses error analysis and patterns in misclassifications
  - Provides performance comparison with baseline approaches
  - Includes detailed tables and results summary

- **`discussion.txt`**: 
  - In-depth discussion of model performance and implications
  - Analyzes strengths and limitations of the approach
  - Discusses challenging test categories and potential improvements
  - Considers broader implications for clinical lab standardization
  - Explores potential for generalization to other standardization tasks
  - Provides context for the results within the healthcare informatics landscape

- **`abstract.txt`**: 
  - Concise summary of the research project and findings
  - Highlights key innovations and contributions
  - Summarizes performance improvements over existing approaches
  - Emphasizes clinical significance of the work
  - Provides overview of methodology and key results
  - Establishes the importance of the contribution in clear terms

- **`presentation.md`**: 
  - Markdown-formatted presentation summarizing the project
  - Features slide-by-slide structure for presentation purposes
  - Includes key visualizations and diagrams
  - Provides concise explanation of methodology and results
  - Features demonstration examples showing model capabilities
  - Includes talking points and presentation guidance 

## PyHealth Implementation Files

The following section describes the implementation files in the PyHealth_Contribution directory, detailing how LOINC standardization capability was integrated with the PyHealth framework:

- **`pyhealth_contribution_report.txt`**: 
  - Comprehensive report on the PyHealth integration process
  - Documents the approach to integrating LOINC standardization into PyHealth
  - Discusses implementation challenges and solutions
  - Provides detailed description of interface design decisions
  - Explains compatibility with existing PyHealth components
  - Includes testing methodology and validation results
  - Features performance benchmarks in the PyHealth ecosystem
  - Discusses future maintenance and enhancement strategies

### PyHealth Implementation Details

#### `PyHealth_Contribution/pyhealth/datasets` Directory

- **`mimic3_loinc_dataset.py`**: 
  - Specialized implementation for processing MIMIC-III data for LOINC mapping
  - Extends PyHealth's dataset capabilities with LOINC-specific functionality
  - Implements MIMIC-III lab data preprocessing following PyHealth conventions
  - Provides dataset splitting methods appropriate for LOINC mapping tasks
  - Features configurable preprocessing and normalization options
  - Implements memory-efficient data loading patterns
  - Includes compatibility with PyHealth's broader dataset ecosystem
  - Features comprehensive error handling for data quality issues

- **`loinc_dataset.py`**: 
  - Implements LIONCDataset class for handling LOINC reference terminology
  - Provides utilities for processing the official LOINC database
  - Implements sophisticated text normalization for LOINC descriptions
  - Features multi-column processing for comprehensive term representation
  - Includes facilities for handling LOINC versioning and updates
  - Provides compatibility with different LOINC versions and formats
  - Implements efficient lookup mechanisms for LOINC code retrieval
  - Features memory-efficient representation of the LOINC database

#### `PyHealth_Contribution/pyhealth/models` Directory

- **`loinc_encoder.py`**: 
  - Implements specialized encoding model for LOINC standardization
  - Adapts the project's core T5-based encoder for the PyHealth framework
  - Provides PyHealth-compatible interfaces for model training and inference
  - Features standardized saving and loading mechanisms
  - Implements memory-efficient inference capabilities
  - Includes progress tracking and logging compatible with PyHealth
  - Features integration with PyHealth's model registry 
  - Provides standardized evaluation metrics for model comparison

- **`retrieval_model.py`**: 
  - Implements text retrieval capabilities for LOINC mapping
  - Features comprehensive similarity calculation methods
  - Provides batch processing for efficient large-scale operations
  - Implements configurable retrieval parameters (k-value, threshold)
  - Features caching mechanisms for improved performance
  - Includes detailed result formatting and explanation
  - Provides integration with PyHealth's broader model ecosystem
  - Features standardized evaluation according to PyHealth conventions

#### `PyHealth_Contribution/pyhealth/tasks` Directory

- **`loinc_standardization.py`**: 
  - Defines the LOINC standardization task in PyHealth's framework
  - Implements task-specific data handling and preprocessing
  - Provides standardized evaluation metrics for the standardization task
  - Features comprehensive reporting and result formatting
  - Implements configurable task parameters for different use cases
  - Includes integration with PyHealth's task registry
  - Provides compatibility with PyHealth's broader training pipelines
  - Features standardized documentation following PyHealth conventions

### Example Implementation

#### `PyHealth_Contribution/examples` Directory

- **`loinc_example.py`**: 
  - Comprehensive example demonstrating LOINC standardization with PyHealth
  - Provides complete end-to-end workflow from data loading to evaluation
  - Includes detailed comments explaining each processing step
  - Features best practices for configuration and parameter selection
  - Implements comprehensive error handling and logging
  - Provides visualization of model outputs and performance metrics
  - Includes performance benchmarking against reference implementations
  - Features memory-efficient implementation suitable for various environments

- **`loinc_inference_example.py`**: 
  - Focused example demonstrating inference with trained LOINC models
  - Provides streamlined implementation focusing on production use cases
  - Includes examples of handling various input formats
  - Features comprehensive output formatting and explanation
  - Implements efficient batch processing for large-scale inference
  - Provides examples of confidence calculation and threshold application
  - Includes memory-optimized implementation for resource-constrained environments
  - Features integration examples with other PyHealth components 

## Preprocessing Implementation

### `preprocessing/` Directory

- **`advanced_preprocessing.py`**: 
  - Implements sophisticated text preprocessing pipeline for lab descriptions
  - Features comprehensive text normalization including case handling and punctuation removal
  - Implements entity detection for specimens, methods, and properties
  - Provides configurable preprocessing options for different data sources
  - Features specialized handling for abbreviations and acronyms
  - Implements synonym expansion for improved term matching
  - Provides scale type detection and standardization
  - Includes comprehensive error handling for malformed inputs

- **`process_mimic.py`**: 
  - Specialized preprocessing for MIMIC-III laboratory data
  - Extracts and normalizes lab test descriptions from MIMIC-III
  - Implements field concatenation for comprehensive test representation
  - Features standardized output format compatible with model training
  - Provides optimization for large-scale dataset processing
  - Implements intelligent handling of missing or incomplete data
  - Includes detailed logging for preprocessing diagnostics
  - Features integration with the broader preprocessing pipeline

- **`create_matching_dataset.py`**: 
  - Creates matched pairs of source-target texts for training
  - Implements intelligent matching heuristics for data preparation
  - Features configurable matching parameters for dataset creation
  - Provides validation mechanisms to ensure data quality
  - Implements stratified sampling for balanced dataset creation
  - Features comprehensive error checking and validation
  - Includes detailed logging of the matching process
  - Generates statistics on the created dataset characteristics

- **`fix_augmentation.py`**: 
  - Implements fixes and enhancements for data augmentation pipeline
  - Corrects issues in augmented data to improve quality
  - Features specialized handling for medical terminology during augmentation
  - Provides validation of augmented examples for consistency
  - Implements detection and correction of invalid augmentations
  - Features integration with the broader augmentation framework
  - Includes comprehensive logging of corrections made
  - Provides statistical analysis of augmentation quality improvements

## Main Training Scripts

- **`main.py`**: 
  - Core training script implementing the main training loop
  - Coordinates data loading, model initialization, and training execution
  - Implements efficient training with comprehensive progress tracking
  - Features checkpoint saving and resumption capabilities
  - Provides detailed logging of training metrics and progress
  - Implements early stopping based on validation performance
  - Features command-line interface with extensive configuration options
  - Includes integration with all model components for unified training

- **`main_augmented.py`**: 
  - Extended training script incorporating data augmentation
  - Features enhanced training loop with augmented example integration
  - Implements epoch-based augmentation refresh strategies
  - Provides detailed monitoring of augmentation impact on training
  - Features memory-efficient handling of expanded training set
  - Implements comprehensive logging with augmentation-specific metrics
  - Includes advanced hyperparameter tuning for augmented training
  - Provides seamless integration with the core training pipeline

- **`data_augmentation.py`**: 
  - Comprehensive implementation of text augmentation strategies
  - Features multiple augmentation techniques:
    - Synonym replacement using medical terminology
    - Random word deletion with configurable rates
    - Random word swapping with context awareness
    - Test method and specimen substitution
  - Implements intelligent preservation of critical information
  - Provides configurable augmentation parameters
  - Features scale-aware augmentation preserving scale tokens
  - Includes comprehensive validation of augmented examples
  - Provides detailed statistics on augmentation operations

## Utilities and Helper Scripts

- **`evaluate_trained_model.py`**: 
  - Standalone script for comprehensive model evaluation
  - Features multiple evaluation metrics and detailed reporting
  - Implements batch processing for memory-efficient evaluation
  - Provides stratified performance analysis across categories
  - Features comprehensive error analysis on misclassified examples
  - Implements integration with visualization generation
  - Includes detailed logging of evaluation process
  - Features command-line interface with extensive configuration options

- **`identify_confusable_pairs.py`**: 
  - Analyzes dataset to find potentially confusable LOINC pairs
  - Implements similarity analysis to identify confusable concepts
  - Features specialized detection of scale-confusable components
  - Provides detailed reporting on confusable pair prevalence
  - Implements category-based analysis of confusability patterns
  - Features integration with model evaluation to assess impact
  - Includes visualization generation for confusion patterns
  - Provides strategies for mitigating confusion through training

- **`process_scale_distributions.py`**: 
  - Analyzes and visualizes scale type distributions
  - Features comprehensive statistical analysis of scale prevalence
  - Implements category-based breakdown of scale distributions
  - Provides correlation analysis between scales and error patterns
  - Features integration with visualization components
  - Includes detailed reporting on scale distribution findings
  - Implements recommendations for balanced training based on distribution
  - Features command-line interface with configuration options

- **`scale_inference.py`**: 
  - Implements rule-based scale type inference from descriptions
  - Features pattern matching for scale indicator detection
  - Implements confidence scoring for scale predictions
  - Provides comprehensive rule set for different scale types
  - Features context-aware inference improving accuracy
  - Includes detailed reporting on inference performance
  - Implements integration with the broader model pipeline
  - Features comprehensive error handling for edge cases

## Project Setup and Requirements

- **`requirements.txt`**: 
  - Comprehensive list of Python dependencies
  - Specifies exact versions for reproducibility
  - Includes all required packages for model training and evaluation
  - Features minimized dependencies to reduce conflicts
  - Provides environment-specific variations where needed
  - Includes optional dependencies for extended functionality
  - Features grouping of dependencies by component
  - Provides comments explaining non-standard packages

- **`run_all.sh`**: 
  - Master script coordinating complete pipeline execution
  - Implements sequential execution of preprocessing, training, and evaluation
  - Features comprehensive error handling and status reporting
  - Provides configurable execution parameters via environment variables
  - Implements checkpoint validation between execution steps
  - Features detailed logging of the complete pipeline execution
  - Includes time tracking for performance monitoring
  - Provides clean termination and resource cleanup 
