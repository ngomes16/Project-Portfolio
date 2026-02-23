import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os

# Create images directory if it doesn't exist
os.makedirs('images', exist_ok=True)

def create_augmentation_workflow():
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Set background color
    ax.set_facecolor('#f5f5f5')
    
    # Remove axis ticks and spines
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    # Example texts (from LOINC_Standardization_paper.txt Figure 1A)
    source_text = "tricyclic antidepressant screen blood"
    target_text = "Tricyclic antidepressants [Presence] in Serum or Plasma"
    
    # Augmented examples
    char_deletion_examples = [
        "tricyclc antdepressant scrn blood",
        "trcyclic antidepressnt screen bld"
    ]
    
    word_swap_examples = [
        "tricyclic blood screen antidepressant",
        "screen tricyclic antidepressant blood"
    ]
    
    word_insertion_examples = [
        "tricyclic antidepressant assay screen blood",
        "tricyclic antidepressant screen in blood"
    ]
    
    acronym_examples = [
        "tcas screen blood",
        "tricyclics precu cm or plasma"
    ]
    
    # Colors
    source_color = '#3366CC'
    target_color = '#66CC99'
    aug_color = '#FF9933'
    text_color = '#333333'
    box_color = '#FFFFFF'
    
    # Draw the source and target boxes at the top
    def create_text_box(x, y, width, height, text, title, color):
        # Box
        box = patches.FancyBboxPatch(
            (x, y),
            width, height,
            boxstyle=f"round,pad=0.3",
            facecolor=box_color,
            edgecolor=color,
            linewidth=2,
            alpha=0.9,
            zorder=1
        )
        ax.add_patch(box)
        
        # Title
        ax.text(
            x + width/2, 
            y + height - 0.05, 
            title,
            ha='center',
            va='top',
            color=color,
            fontsize=12,
            fontweight='bold',
            zorder=2
        )
        
        # Content
        ax.text(
            x + width/2, 
            y + height/2 - 0.05, 
            text,
            ha='center',
            va='center',
            color=text_color,
            fontsize=11,
            zorder=2
        )
        
        return box
    
    # Source and target boxes
    source_box = create_text_box(0.1, 0.75, 0.35, 0.15, source_text, "Source Text", source_color)
    target_box = create_text_box(0.55, 0.75, 0.35, 0.15, target_text, "LOINC Target Text", target_color)
    
    # Add arrow connecting source and target
    mapping_arrow = patches.FancyArrowPatch(
        (0.45, 0.825),
        (0.55, 0.825),
        arrowstyle='-|>',
        connectionstyle="arc3,rad=0",
        color=text_color,
        linewidth=1.5,
        mutation_scale=15,
        zorder=3
    )
    ax.add_patch(mapping_arrow)
    ax.text(0.5, 0.84, "Mapping", ha='center', va='bottom', color=text_color, fontsize=10)
    
    # Data augmentation box
    aug_box = patches.Rectangle(
        (0.2, 0.52), 
        0.6, 
        0.12, 
        linewidth=2, 
        edgecolor=aug_color, 
        facecolor=aug_color,
        alpha=0.2,
        zorder=0
    )
    ax.add_patch(aug_box)
    ax.text(
        0.5, 
        0.58, 
        "Data Augmentation Techniques",
        ha='center',
        va='center',
        color=text_color,
        fontsize=14,
        fontweight='bold',
        zorder=2
    )
    
    # Arrows from source and target to augmentation
    source_aug_arrow = patches.FancyArrowPatch(
        (0.3, 0.75),
        (0.3, 0.64),
        arrowstyle='-|>',
        color=text_color,
        linewidth=1.5,
        mutation_scale=15,
        zorder=3
    )
    ax.add_patch(source_aug_arrow)
    
    target_aug_arrow = patches.FancyArrowPatch(
        (0.7, 0.75),
        (0.7, 0.64),
        arrowstyle='-|>',
        color=text_color,
        linewidth=1.5,
        mutation_scale=15,
        zorder=3
    )
    ax.add_patch(target_aug_arrow)
    
    # Augmentation technique boxes
    techniques = [
        {"name": "Character Deletion", "examples": char_deletion_examples, "x": 0.1, "y": 0.4},
        {"name": "Word Swapping", "examples": word_swap_examples, "x": 0.35, "y": 0.4},
        {"name": "Word Insertion", "examples": word_insertion_examples, "x": 0.6, "y": 0.4},
        {"name": "Acronym Substitution", "examples": acronym_examples, "x": 0.85, "y": 0.4}
    ]
    
    # Draw arrows from augmentation box to techniques
    for tech in techniques:
        arrow = patches.FancyArrowPatch(
            (tech["x"], 0.52),
            (tech["x"], 0.45),
            arrowstyle='-|>',
            color=text_color,
            linewidth=1.5,
            mutation_scale=15,
            zorder=3
        )
        ax.add_patch(arrow)
    
    # Create technique boxes
    for tech in techniques:
        # Technique box
        box = patches.FancyBboxPatch(
            (tech["x"] - 0.12, tech["y"] - 0.05),
            0.24, 0.1,
            boxstyle=f"round,pad=0.3",
            facecolor=box_color,
            edgecolor=aug_color,
            linewidth=2,
            alpha=0.9,
            zorder=1
        )
        ax.add_patch(box)
        
        # Technique name
        ax.text(
            tech["x"], 
            tech["y"], 
            tech["name"],
            ha='center',
            va='center',
            color=text_color,
            fontsize=11,
            fontweight='bold',
            zorder=2
        )
        
        # Example boxes
        for i, example in enumerate(tech["examples"]):
            # Calculate y position
            example_y = tech["y"] - 0.15 - i * 0.1
            
            # Example box
            example_box = patches.FancyBboxPatch(
                (tech["x"] - 0.12, example_y - 0.04),
                0.24, 0.08,
                boxstyle=f"round,pad=0.3",
                facecolor=box_color,
                edgecolor='gray',
                linewidth=1,
                alpha=0.9,
                zorder=1
            )
            ax.add_patch(example_box)
            
            # Example text
            ax.text(
                tech["x"], 
                example_y, 
                example,
                ha='center',
                va='center',
                color=text_color,
                fontsize=9,
                zorder=2
            )
            
            # Arrow from technique to example
            if i == 0:
                example_arrow = patches.FancyArrowPatch(
                    (tech["x"], tech["y"] - 0.05),
                    (tech["x"], example_y + 0.04),
                    arrowstyle='-|>',
                    color=text_color,
                    linewidth=1,
                    mutation_scale=10,
                    zorder=3
                )
                ax.add_patch(example_arrow)
    
    # Add title
    ax.set_title('Data Augmentation Workflow for LOINC Standardization', fontsize=16, pad=20)
    
    # Set limits
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    
    plt.tight_layout()
    plt.savefig('images/data_augmentation_workflow.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Created: data_augmentation_workflow.png")

if __name__ == "__main__":
    create_augmentation_workflow() 