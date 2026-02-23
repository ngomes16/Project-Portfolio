import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle, FancyArrowPatch, FancyBboxPatch
import os

# Create images directory if it doesn't exist
os.makedirs('images', exist_ok=True)

def create_model_architecture_diagram():
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Set background color
    ax.set_facecolor('#f8f8f8')
    
    # Remove axis ticks and spines
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    # Colors
    frozen_color = '#3366CC'
    trainable_color = '#66CC99'
    text_color = '#333333'
    arrow_color = '#555555'
    
    # Positions
    start_x = 0.05
    end_x = 0.95
    center_y = 0.5
    box_height = 0.15
    
    # Create boxes for each component
    components = [
        {"name": "Input Text", "x": start_x, "width": 0.12, "color": 'white', "is_frozen": None},
        {"name": "ST5-base Encoder\n(Frozen)", "x": 0.22, "width": 0.15, "color": frozen_color, "is_frozen": True},
        {"name": "768-dim\nEmbedding", "x": 0.42, "width": 0.12, "color": 'white', "is_frozen": None},
        {"name": "Dense Layer\n(Trainable)", "x": 0.59, "width": 0.15, "color": trainable_color, "is_frozen": False},
        {"name": "128-dim\nEmbedding", "x": 0.79, "width": 0.12, "color": 'white', "is_frozen": None},
    ]
    
    # Draw boxes
    boxes = []
    for comp in components:
        if comp["color"] == 'white':
            # For embeddings, use rounded box with light border
            box = FancyBboxPatch(
                (comp["x"], center_y - box_height/2),
                comp["width"], box_height,
                boxstyle=f"round,pad=0.3",
                facecolor='white',
                edgecolor='gray',
                alpha=0.9,
                zorder=1
            )
        else:
            # For model components, use rectangle with solid color
            box = Rectangle(
                (comp["x"], center_y - box_height/2),
                comp["width"], box_height,
                facecolor=comp["color"],
                edgecolor='gray',
                alpha=0.9,
                zorder=1
            )
        ax.add_patch(box)
        boxes.append(box)
        
        # Add text
        ax.text(
            comp["x"] + comp["width"]/2, 
            center_y, 
            comp["name"],
            ha='center',
            va='center',
            color='black' if comp["color"] == 'white' else 'white',
            fontsize=12,
            fontweight='bold',
            zorder=2
        )
        
        # Add frozen/trainable label if applicable
        if comp["is_frozen"] is not None:
            label = "Frozen" if comp["is_frozen"] else "Trainable"
            ax.text(
                comp["x"] + comp["width"]/2, 
                center_y - box_height/2 - 0.03,
                label,
                ha='center',
                va='top',
                color=text_color,
                fontsize=10,
                fontstyle='italic',
                zorder=2
            )
    
    # Add L2 Normalization step
    norm_x = 0.91
    ax.text(
        norm_x,
        center_y,
        "L2 Normalization",
        ha='center',
        va='center',
        color=text_color,
        fontsize=12,
        fontweight='bold',
        bbox=dict(facecolor='white', edgecolor='gray', boxstyle='round,pad=0.3', alpha=0.9),
        zorder=2
    )
    
    # Draw arrows between components
    for i in range(len(components)-1):
        start = components[i]["x"] + components[i]["width"]
        end = components[i+1]["x"]
        arrow = FancyArrowPatch(
            (start, center_y),
            (end, center_y),
            arrowstyle='-|>',
            color=arrow_color,
            linewidth=1.5,
            mutation_scale=15,
            zorder=0
        )
        ax.add_patch(arrow)
    
    # Add arrow to L2 Normalization
    arrow = FancyArrowPatch(
        (components[-1]["x"] + components[-1]["width"], center_y),
        (norm_x - 0.04, center_y),
        arrowstyle='-|>',
        color=arrow_color,
        linewidth=1.5,
        mutation_scale=15,
        zorder=0
    )
    ax.add_patch(arrow)
    
    # Add Final Embedding
    final_x = 0.91
    final_y = center_y - 0.19
    ax.text(
        final_x,
        final_y,
        "Final 128-dim\nEmbedding",
        ha='center',
        va='center',
        color=text_color,
        fontsize=12,
        fontweight='bold',
        bbox=dict(facecolor='white', edgecolor='gray', boxstyle='round,pad=0.3', alpha=0.9),
        zorder=2
    )
    
    # Arrow from L2 Norm to Final Embedding
    arrow = FancyArrowPatch(
        (norm_x, center_y + box_height/2 + 0.02),
        (final_x, final_y + 0.05),
        arrowstyle='-|>',
        connectionstyle="arc3,rad=-0.3",
        color=arrow_color,
        linewidth=1.5,
        mutation_scale=15,
        zorder=0
    )
    ax.add_patch(arrow)
    
    # Add title
    ax.set_title('LOINC Standardization Model Architecture', fontsize=16, pad=20)
    
    # Set limits
    ax.set_xlim(0, 1)
    ax.set_ylim(0.1, 0.9)
    
    # Add legend for frozen vs trainable
    legend_elements = [
        Rectangle((0, 0), 1, 1, facecolor=frozen_color, edgecolor='gray', alpha=0.9, label='Frozen Component'),
        Rectangle((0, 0), 1, 1, facecolor=trainable_color, edgecolor='gray', alpha=0.9, label='Trainable Component')
    ]
    ax.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, 0.02), ncol=2)
    
    plt.tight_layout()
    plt.savefig('images/model_architecture_diagram.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Created: model_architecture_diagram.png")

if __name__ == "__main__":
    create_model_architecture_diagram() 