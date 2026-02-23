import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os

# Create images directory if it doesn't exist
os.makedirs('images', exist_ok=True)

def create_scale_token_diagram():
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Set background color
    ax.set_facecolor('#f5f5f5')
    
    # Remove axis ticks and spines
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    # Colors
    text_color = '#333333'
    box_color = '#FFFFFF'
    qn_color = '#3366CC'   # Quantitative
    ql_color = '#66CC99'   # Qualitative
    highlight_color = '#FFDD33'  # Highlight color for tokens
    arrow_color = '#555555'
    
    # Example texts
    similar_examples = [
        {
            "type": "Qn",
            "text": "Erythrocytes [#/volume] in Urine by Test strip",
            "token": "##scale=qn##",
            "color": qn_color
        },
        {
            "type": "Ql",
            "text": "Erythrocytes [Presence] in Urine by Test strip",
            "token": "##scale=ql##",
            "color": ql_color
        }
    ]
    
    # Position
    start_y = 0.8
    spacing = 0.1
    
    # Title
    ax.text(0.5, 0.95, "Scale Token Integration for Qualitative vs. Quantitative Distinction",
           fontsize=16, fontweight='bold', ha='center', va='center')
    
    # Draw the issue box
    issue_box = patches.FancyBboxPatch(
        (0.1, 0.75),
        0.8, 0.15,
        boxstyle=f"round,pad=0.4",
        facecolor="#FFEEEE",
        edgecolor="#FF9999",
        linewidth=2,
        alpha=0.9,
        zorder=1
    )
    ax.add_patch(issue_box)
    
    ax.text(0.5, 0.825, 
           "Issue: Model struggles to distinguish between scale types (Quantitative vs. Qualitative)\n" + 
           "when LOINC descriptions are otherwise similar",
           ha='center', va='center', fontsize=12, color=text_color)
    
    # Draw the similar confusable examples
    for i, example in enumerate(similar_examples):
        y_pos = 0.65 - i * 0.1
        
        # Example box
        box = patches.FancyBboxPatch(
            (0.1, y_pos - 0.04),
            0.8, 0.08,
            boxstyle=f"round,pad=0.3",
            facecolor=box_color,
            edgecolor=example["color"],
            linewidth=2,
            alpha=0.9,
            zorder=1
        )
        ax.add_patch(box)
        
        # Type label
        type_box = patches.FancyBboxPatch(
            (0.11, y_pos - 0.03),
            0.06, 0.06,
            boxstyle=f"round,pad=0.1",
            facecolor=example["color"],
            edgecolor=example["color"],
            linewidth=1,
            alpha=0.9,
            zorder=2
        )
        ax.add_patch(type_box)
        ax.text(0.14, y_pos, example["type"], ha='center', va='center', color='white', fontsize=10, fontweight='bold')
        
        # Example text
        ax.text(0.5, y_pos, example["text"], ha='center', va='center', color=text_color, fontsize=11)
    
    # Solution section title
    ax.text(0.5, 0.45, "Solution: Append Scale Token to Input Text",
           fontsize=14, fontweight='bold', ha='center', va='center')
    
    # Draw the solution with scale tokens
    for i, example in enumerate(similar_examples):
        y_pos = 0.35 - i * 0.1
        
        # Example box
        box = patches.FancyBboxPatch(
            (0.1, y_pos - 0.04),
            0.8, 0.08,
            boxstyle=f"round,pad=0.3",
            facecolor=box_color,
            edgecolor=example["color"],
            linewidth=2,
            alpha=0.9,
            zorder=1
        )
        ax.add_patch(box)
        
        # Full text with token
        text_with_token = example["text"] + " " + example["token"]
        
        # Split text into regular part and token part for different styling
        ax.text(0.2, y_pos, example["text"], ha='left', va='center', color=text_color, fontsize=11)
        ax.text(0.8, y_pos, example["token"], ha='right', va='center', color=example["color"], 
                fontsize=11, fontweight='bold', bbox=dict(facecolor=highlight_color, alpha=0.3, pad=3))
        
        # Type label
        type_box = patches.FancyBboxPatch(
            (0.11, y_pos - 0.03),
            0.06, 0.06,
            boxstyle=f"round,pad=0.1",
            facecolor=example["color"],
            edgecolor=example["color"],
            linewidth=1,
            alpha=0.9,
            zorder=2
        )
        ax.add_patch(type_box)
        ax.text(0.14, y_pos, example["type"], ha='center', va='center', color='white', fontsize=10, fontweight='bold')
    
    # Add arrows from original to solution
    for i in range(len(similar_examples)):
        orig_y = 0.65 - i * 0.1
        solution_y = 0.35 - i * 0.1
        arrow = patches.FancyArrowPatch(
            (0.5, orig_y - 0.05),
            (0.5, solution_y + 0.05),
            arrowstyle='-|>',
            connectionstyle="arc3,rad=0",
            color=arrow_color,
            linewidth=1.5,
            mutation_scale=15,
            zorder=3
        )
        ax.add_patch(arrow)
    
    # Add impact section
    impact_box = patches.FancyBboxPatch(
        (0.1, 0.1),
        0.8, 0.15,
        boxstyle=f"round,pad=0.4",
        facecolor="#EEFFEE",
        edgecolor="#99CC99",
        linewidth=2,
        alpha=0.9,
        zorder=1
    )
    ax.add_patch(impact_box)
    
    ax.text(0.5, 0.175, 
           "Impact: Scale token integration improved performance on scale-confusable pairs\n" + 
           "by +9.0% (77.0% → 86.0%) without requiring model architecture changes",
           ha='center', va='center', fontsize=12, color=text_color)
    
    # Show unknown scale handling
    unknown_box = patches.FancyBboxPatch(
        (0.6, 0.55),
        0.3, 0.1,
        boxstyle=f"round,pad=0.3",
        facecolor="#EEEEEE",
        edgecolor="#999999",
        linewidth=2,
        alpha=0.9,
        zorder=1
    )
    ax.add_patch(unknown_box)
    
    ax.text(0.75, 0.6, 
           "When scale is unknown:\n##scale=unk##",
           ha='center', va='center', fontsize=10, color=text_color)
    
    plt.tight_layout()
    plt.savefig('images/scale_token_integration.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Created: scale_token_integration.png")

if __name__ == "__main__":
    create_scale_token_diagram() 