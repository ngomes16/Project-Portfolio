import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patches as patches
import os

# Create images directory if it doesn't exist
os.makedirs('images', exist_ok=True)

def create_two_stage_diagram():
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Set background color
    ax.set_facecolor('#f5f5f5')
    
    # Remove axis ticks and spines
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    # Colors
    stage1_color = '#3366CC'
    stage2_color = '#66CC99'
    box_color = '#FFFFFF'
    text_color = '#333333'
    arrow_color = '#555555'
    
    # Position parameters
    stage_height = 0.3
    stage_width = 0.9
    stage_gap = 0.1
    component_height = 0.12
    component_width = 0.18
    
    # Draw Stage 1 container
    stage1_rect = patches.Rectangle(
        (0.05, 0.6), 
        stage_width, 
        stage_height, 
        linewidth=2, 
        edgecolor=stage1_color, 
        facecolor=stage1_color,
        alpha=0.2,
        zorder=0
    )
    ax.add_patch(stage1_rect)
    
    # Stage 1 title
    ax.text(
        0.08, 
        0.88, 
        "STAGE 1: Target-Only Pre-fine-tuning", 
        fontsize=14, 
        fontweight='bold', 
        color=stage1_color,
        ha='left',
        va='center'
    )
    
    # Stage 1 components
    stage1_components = [
        {"name": "LOINC Target Codes\n+ Augmentation", "x": 0.1, "y": 0.72, "is_input": True},
        {"name": "Frozen ST5-base\n+ Trainable Projection", "x": 0.32, "y": 0.72, "is_input": False},
        {"name": "Triplet Loss\nSemi-Hard Mining", "x": 0.54, "y": 0.72, "is_input": False},
        {"name": "LOINC Ontology\nEmbeddings", "x": 0.76, "y": 0.72, "is_input": True}
    ]
    
    # Draw Stage 1 components
    for comp in stage1_components:
        box = patches.FancyBboxPatch(
            (comp["x"], comp["y"] - component_height/2),
            component_width, 
            component_height,
            boxstyle=f"round,pad=0.3",
            facecolor='white',
            edgecolor=stage1_color,
            linewidth=2,
            alpha=0.9,
            zorder=1
        )
        ax.add_patch(box)
        ax.text(
            comp["x"] + component_width/2, 
            comp["y"], 
            comp["name"],
            ha='center',
            va='center',
            color=text_color,
            fontsize=10,
            fontweight='bold',
            zorder=2
        )
    
    # Stage 1 arrows
    for i in range(len(stage1_components)-1):
        arrow = patches.FancyArrowPatch(
            (stage1_components[i]["x"] + component_width, stage1_components[i]["y"]),
            (stage1_components[i+1]["x"], stage1_components[i+1]["y"]),
            arrowstyle='-|>',
            color=arrow_color,
            linewidth=1.5,
            mutation_scale=15,
            zorder=3
        )
        ax.add_patch(arrow)
    
    # Draw Stage 2 container
    stage2_rect = patches.Rectangle(
        (0.05, 0.1), 
        stage_width, 
        stage_height, 
        linewidth=2, 
        edgecolor=stage2_color, 
        facecolor=stage2_color,
        alpha=0.2,
        zorder=0
    )
    ax.add_patch(stage2_rect)
    
    # Stage 2 title
    ax.text(
        0.08, 
        0.38, 
        "STAGE 2: Source-Target Fine-tuning", 
        fontsize=14, 
        fontweight='bold', 
        color=stage2_color,
        ha='left',
        va='center'
    )
    
    # Stage 2 components
    stage2_components = [
        {"name": "MIMIC-III Source-Target\nPairs + Augmentation", "x": 0.1, "y": 0.22, "is_input": True},
        {"name": "Pre-trained Model\nfrom Stage 1", "x": 0.32, "y": 0.22, "is_input": False},
        {"name": "Triplet Loss\nHard Mining", "x": 0.54, "y": 0.22, "is_input": False},
        {"name": "Joint Source-Target\nEmbeddings", "x": 0.76, "y": 0.22, "is_input": True}
    ]
    
    # Draw Stage 2 components
    for comp in stage2_components:
        box = patches.FancyBboxPatch(
            (comp["x"], comp["y"] - component_height/2),
            component_width, 
            component_height,
            boxstyle=f"round,pad=0.3",
            facecolor='white',
            edgecolor=stage2_color,
            linewidth=2,
            alpha=0.9,
            zorder=1
        )
        ax.add_patch(box)
        ax.text(
            comp["x"] + component_width/2, 
            comp["y"], 
            comp["name"],
            ha='center',
            va='center',
            color=text_color,
            fontsize=10,
            fontweight='bold',
            zorder=2
        )
    
    # Stage 2 arrows
    for i in range(len(stage2_components)-1):
        arrow = patches.FancyArrowPatch(
            (stage2_components[i]["x"] + component_width, stage2_components[i]["y"]),
            (stage2_components[i+1]["x"], stage2_components[i+1]["y"]),
            arrowstyle='-|>',
            color=arrow_color,
            linewidth=1.5,
            mutation_scale=15,
            zorder=3
        )
        ax.add_patch(arrow)
    
    # Add connection between stages
    transfer_arrow = patches.FancyArrowPatch(
        (stage1_components[1]["x"] + component_width/2, stage1_components[1]["y"] - component_height/2 - 0.02),
        (stage2_components[1]["x"] + component_width/2, stage2_components[1]["y"] + component_height/2 + 0.02),
        arrowstyle='-|>',
        connectionstyle="arc3,rad=-0.2",
        color=arrow_color,
        linewidth=2,
        linestyle='--',
        mutation_scale=15,
        zorder=3
    )
    ax.add_patch(transfer_arrow)
    
    # Add transfer label
    ax.text(
        stage1_components[1]["x"] + component_width/2 - 0.08, 
        0.5,
        "Transfer Trained\nProjection Layer",
        ha='center',
        va='center',
        color=text_color,
        fontsize=10,
        fontstyle='italic',
        bbox=dict(facecolor='white', alpha=0.7, pad=3),
        zorder=3
    )
    
    # Add title
    ax.set_title('Two-Stage Fine-Tuning Process for LOINC Standardization', fontsize=16, pad=20)
    
    # Set limits
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    
    plt.tight_layout()
    plt.savefig('images/two_stage_finetuning_diagram.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Created: two_stage_finetuning_diagram.png")

if __name__ == "__main__":
    create_two_stage_diagram() 