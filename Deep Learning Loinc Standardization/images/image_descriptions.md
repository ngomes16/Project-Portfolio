# LOINC Standardization Project Visualizations

This folder contains visualizations for our reproduction of the "Automated LOINC Standardization Using Pre-trained Large Language Models" paper.

## Available Visualizations

### Core Results

1. **Model Performance Comparison** (`model_performance_comparison.png`)
   - A bar chart comparing Top-1, Top-3, and Top-5 accuracies across the four evaluation scenarios:
     - Standard Pool (Original Test Data)
     - Expanded Pool (Original Test Data)
     - Standard Pool (Augmented Test Data)
     - Expanded Pool (Augmented Test Data)

2. **Ablation Study Impact** (`ablation_study_impact.png`)
   - A multi-panel chart showing the impact of different model components on Top-1 accuracy:
     - Two-Stage Fine-Tuning vs. Stage 2 Only
     - Different Triplet Mining Strategies (Hard, Semi-Hard, Random)
     - Impact of Data Augmentation on Standard and Augmented Test Sets

3. **Error Category Distribution** (`error_category_distribution.png` and `error_category_distribution_bar.png`)
   - Pie chart and horizontal bar chart showing the breakdown of error types:
     - Specimen Mismatch (34.8%)
     - Ambiguous Source (26.5%)
     - Property Mismatch (17.2%)
     - Similar Descriptions (14.3%)
     - Methodological Differences (5.2%)
     - Completely Different (1.3%)
     - Other (0.7%)

### Extension Results

4. **Scale Token Performance** (`scale_token_performance.png`)
   - Bar chart showing the improvement in Top-1 accuracy from our Scale Token Extension:
     - Overall performance
     - Performance on Scale-Confusable Pairs
     - Performance on High-Risk assays (e.g., Drug Screens)

5. **No-Match Handling Precision-Recall Curve** (`nomatch_precision_recall.png`)
   - Precision-Recall curve for the No-Match handling extension
   - Shows optimal thresholds based on F1-score and precision-adjusted targets

6. **Similarity Distribution** (`similarity_distribution.png`)
   - Distribution plots showing the similarity scores for Mappable vs. Unmappable codes
   - Indicates threshold cut-offs and their impact on classification

### Methodological Diagrams

7. **Model Architecture Diagram** (`model_architecture_diagram.png`)
   - Illustrates the ST5-base encoder backbone with projection layer
   - Shows the flow from input text to final 128-dimensional embeddings

8. **Two-Stage Fine-tuning Diagram** (`two_stage_finetuning_diagram.png`)
   - Depicts the two-stage fine-tuning strategy:
     - Stage 1: Target-only pre-fine-tuning on LOINC corpus
     - Stage 2: Source-target pairs fine-tuning on MIMIC-III

9. **Data Augmentation Workflow** (`data_augmentation_workflow.png`)
   - Illustrates the data augmentation techniques:
     - Character-level random deletion
     - Word-level random swapping
     - Word-level random insertion
     - Acronym substitution

10. **Triplet Loss Concept** (`triplet_loss_concept.png`)
    - Visualizes the triplet loss mechanism
    - Shows how anchors, positives, and negatives are positioned in embedding space

11. **Scale Token Integration** (`scale_token_integration.png`)
    - Demonstrates how scale type information is integrated into text inputs
    - Shows examples of different scale token prefixes/suffixes

## Python Scripts

This folder includes Python scripts to generate all of these visualizations:

- `plot_core_model_performance.py`: Generates the model performance comparison chart
- `plot_ablation_study_impact.py`: Creates the ablation study impact charts
- `plot_scale_token_performance.py`: Produces the scale token extension performance chart
- `plot_no_match_pr_curve.py`: Generates the precision-recall curve for no-match handling
- `plot_similarity_distribution.py`: Creates the similarity distribution visualization
- `plot_error_category_distribution.py`: Produces the error category distribution charts

To regenerate all images, run the shell script:

```bash
./generate_all_images.sh
```

Note: The scripts use placeholder data that should be replaced with actual experimental results for accurate visualizations. 

## Model Architecture Diagram

```
┌─────────────────┐     ┌───────────────────────┐     ┌───────────────────────┐
│                 │     │                       │     │                       │
│   Input Text    │────►│   ST5-base Encoder    │────►│     768-dim          │
│  (e.g., "creat- │     │     (FROZEN)          │     │    Embedding         │
│  inine blood")  │     │                       │     │                       │
│                 │     │                       │     │                       │
└─────────────────┘     └───────────────────────┘     └───────────┬───────────┘
                                                                  │
                                                                  ▼
┌─────────────────┐     ┌───────────────────────┐     ┌───────────────────────┐
│                 │     │                       │     │                       │
│    128-dim     │◄────│  Fully-Connected Layer │◄────│ 768-dim Embedding    │
│   Embedding    │     │     (TRAINABLE)        │     │                       │
│                 │     │   (768 → 128 dim)     │     │                       │
│                 │     │                       │     │                       │
└─────────┬───────┘     └───────────────────────┘     └───────────────────────┘
          │
          ▼
┌─────────────────┐     ┌───────────────────────┐
│                 │     │                       │
│ Final 128-dim   │◄────│    L2 Normalization   │
│   Embedding     │     │                       │
│                 │     │                       │
│                 │     │                       │
└─────────────────┘     └───────────────────────┘
```

## Two-Stage Fine-Tuning Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: Target-Only Pre-Fine-Tuning                                            │
├─────────────────┬───────────────────────┬───────────────────┬──────────────────┤
│                 │                       │                   │                  │
│  LOINC Target   │   Data Augmentation   │    ST5 Model      │    Contrastive   │
│   Codes Only    │  • Character deletion │  • Frozen Encoder │    Triplet Loss  │
│ (~7,800 codes,  │  • Word swapping      │  • Trainable      │  • Semi-Hard     │
│  10% sample)    │  • Word insertion     │    Projection     │    Negative      │
│                 │  • Acronym subst.     │    Layer          │    Mining        │
│                 │                       │                   │  • Margin α=0.8  │
└────────┬────────┴─────────┬─────────────┴─────────┬─────────┴────────┬─────────┘
         │                  │                       │                  │
         ▼                  ▼                       ▼                  ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│            Contextualized LOINC Embeddings in 128-dimensional Space            │
└────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ Initialize projection layer weights
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 2: Source-Target Fine-Tuning                                              │
├─────────────────┬───────────────────────┬───────────────────┬──────────────────┤
│                 │                       │                   │                  │
│  MIMIC-III      │   Data Augmentation   │    ST5 Model      │    Contrastive   │
│  Source-Target  │  • Character deletion │  • Frozen Encoder │    Triplet Loss  │
│  Pairs          │  • Word swapping      │  • Trainable      │  • Hard Negative │
│  (579 pairs)    │  • Word insertion     │    Projection     │    Mining        │
│                 │  • Acronym subst.     │    Layer          │  • Margin α=0.8  │
│                 │                       │  • Dropout (0.2)  │  • 5-fold CV     │
│                 │                       │                   │                  │
└────────┬────────┴─────────┬─────────────┴─────────┬─────────┴────────┬─────────┘
         │                  │                       │                  │
         ▼                  ▼                       ▼                  ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│            Joint Source-Target Embeddings in 128-dimensional Space             │
└────────────────────────────────────────────────────────────────────────────────┘
```

## Data Augmentation Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ Original Source Text                                                │
│ "tricyclic antidepressant screen blood"                             │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Original Target (LOINC)                                             │
│ LONG_COMMON_NAME: "Tricyclic antidepressants [Presence] in Serum or │
│                   Plasma"                                           │
│ SHORTNAME: "Tricyclics SerPl Ql"                                    │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       DATA AUGMENTATION                             │
└───────────┬───────────────┬─────────────────┬───────────────────────┘
            │               │                 │
            ▼               ▼                 ▼                       ▼
┌───────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ 1. Character      │ │ 2. Word         │ │ 3. Word         │ │ 4. Acronym      │
│    Deletion       │ │    Swapping     │ │    Insertion    │ │    Substitution │
├───────────────────┤ ├─────────────────┤ ├─────────────────┤ ├─────────────────┤
│ "tricyclc         │ │ "tricyclic      │ │ "tricyclic      │ │ "tcas screen    │
│ antdepressant     │ │ blood screen    │ │ antidepressant  │ │ blood"          │
│ screen blood"     │ │ antidepressant" │ │ screen level    │ │                 │
│                   │ │                 │ │ blood"          │ │                 │
└───────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ Augmented Target Examples:                                          │
│ • "tricyclics ql"                                                   │
│ • "tcas in precu cm or plasma"                                      │
│ • "plasma antidepressants [presence] in serum or tricyclics ql"     │
└─────────────────────────────────────────────────────────────────────┘
```

## Triplet Loss Concept Diagram

```
         Embedding Space
         
                           │
                           │
                           │
                           │                    N (Negative)
                           │                     ●
                           │                    /
                           │                   /
         Push Away         │                  /
         ───────────►      │                 /
                           │                /   
                           │               /
                           │              /
                           │             /         Margin α
                           │            /◄───────────────►
                           │           /
        A (Anchor)         │          /
           ●───────────────┼─────────/───────────● P (Positive)
         Pull Closer       │        /            
         ◄───────────      │       /             
                           │      /             
                           │     /              
                           │    /               
                           │   /                
                           │  /                 
                           │ /                  
                           │/                   
──────────────────────────┬┴┬────────────────────────────
                         /   \
                        /     \
                                         

Triplet Loss: max(0, D(A,P)² - D(A,N)² + α)

Goal: D(A,P)² + α < D(A,N)²

Where:
- A: Anchor (e.g., source text "creatinine blood")
- P: Positive (e.g., augmented version or true LOINC target)
- N: Negative (e.g., incorrect LOINC target)
- D: Cosine distance
- α: Margin (0.8)
```

## Scale Token Integration Diagram

```
┌──────────────────────────────────────────────────────────────┐
│ Original LOINC Description (Without Scale Token)             │
│                                                              │
│ "Erythrocytes [Presence] in Urine"                           │
│                                                              │
│ ◄─── Can be confused with ───► "Erythrocytes [#/volume] in   │
│                                 Urine"                       │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ LOINC Description with Scale Token                           │
│                                                              │
│ "Erythrocytes [Presence] in Urine ##scale=ql##"              │
│                                                              │
│ "Erythrocytes [#/volume] in Urine ##scale=qn##"              │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ Impact on Triplet Mining                                     │
│                                                              │
│ A (Anchor):                                                  │
│ "Erythrocytes [Presence] in Urine ##scale=ql##"              │
│                                                              │
│ P (Positive):                                                │
│ "Erythro [Presence] in Urine ##scale=ql##"                   │
│                                                              │
│ N (Hard Negative):                                           │
│ "Erythrocytes [#/volume] in Urine ##scale=qn##"              │
│                                                              │
│ - Scale tokens help distinguish between otherwise similarly  │
│   worded LOINC codes that differ primarily in their scale type│
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ During Inference                                             │
│                                                              │
│ Source (with known scale): "urinary erythrocytes ##scale=ql##"│
│                                                              │
│ Source (unknown scale): "urinary erythrocytes ##scale=unk##" │
└──────────────────────────────────────────────────────────────┘
```

These diagram specifications can be implemented in any diagramming tool to create clean, professional visualizations for your project report. 





