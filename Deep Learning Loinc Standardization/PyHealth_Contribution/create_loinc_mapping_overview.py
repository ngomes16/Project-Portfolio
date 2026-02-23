import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

def create_loinc_mapping_overview():
    # Set the style to a clean, modern look
    plt.style.use('seaborn-v0_8-whitegrid')
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Custom colors
    pyhealth_blue = '#3873B3'
    loinc_green = '#1D9A78'
    highlight_orange = '#F7941D'
    light_blue = '#D6E4F0'
    light_green = '#D6F0E4'
    
    # Create custom colormaps
    blue_cmap = LinearSegmentedColormap.from_list('blue_cmap', ['white', light_blue, pyhealth_blue])
    green_cmap = LinearSegmentedColormap.from_list('green_cmap', ['white', light_green, loinc_green])
    
    # Main boxes
    # Source data box
    source_rect = patches.Rectangle((0.1, 0.7), 0.25, 0.2, linewidth=2, edgecolor=pyhealth_blue, 
                                   facecolor=light_blue, alpha=0.7)
    ax.add_patch(source_rect)
    ax.text(0.225, 0.8, 'Local Lab Tests\n(MIMIC-III)', ha='center', va='center', fontsize=12, fontweight='bold')
    
    # Target data box
    target_rect = patches.Rectangle((0.65, 0.7), 0.25, 0.2, linewidth=2, edgecolor=loinc_green, 
                                   facecolor=light_green, alpha=0.7)
    ax.add_patch(target_rect)
    ax.text(0.775, 0.8, 'LOINC Reference\nTerminology', ha='center', va='center', fontsize=12, fontweight='bold')
    
    # Model box
    model_rect = patches.Rectangle((0.25, 0.35), 0.5, 0.25, linewidth=2, edgecolor=highlight_orange, 
                                  facecolor='#FFEDD9', alpha=0.9)
    ax.add_patch(model_rect)
    
    # Model title
    ax.text(0.5, 0.52, 'LOINC Standardization Model', ha='center', va='center', fontsize=14, fontweight='bold')
    
    # Model components
    ax.text(0.35, 0.44, '• Sentence-T5 Encoder', ha='left', va='center', fontsize=10)
    ax.text(0.35, 0.40, '• Projection Layer', ha='left', va='center', fontsize=10)
    ax.text(0.35, 0.36, '• Contrastive Learning', ha='left', va='center', fontsize=10)
    
    # Result box
    result_rect = patches.Rectangle((0.25, 0.1), 0.5, 0.15, linewidth=2, edgecolor='#666666', 
                                   facecolor='#EEEEEE', alpha=0.7)
    ax.add_patch(result_rect)
    ax.text(0.5, 0.175, 'Standardized LOINC Mappings', ha='center', va='center', fontsize=12, fontweight='bold')
    ax.text(0.5, 0.13, 'Top-1 Accuracy: 83.7% | MRR: 0.874', ha='center', va='center', fontsize=10)
    
    # Arrows
    arrow_props = dict(arrowstyle='->',
                      connectionstyle='arc3,rad=0.1',
                      linewidth=2)
    
    # Source to model
    ax.annotate('', xy=(0.4, 0.35), xytext=(0.225, 0.7),
               arrowprops=arrow_props)
    
    # Target to model
    ax.annotate('', xy=(0.6, 0.35), xytext=(0.775, 0.7),
               arrowprops=arrow_props)
    
    # Model to result
    ax.annotate('', xy=(0.5, 0.1), xytext=(0.5, 0.35),
               arrowprops=arrow_props)
    
    # Stage labels
    ax.text(0.25, 0.62, 'Stage 1: Target-only Training', ha='center', va='center', 
           fontsize=10, fontweight='bold', bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.3'))
    ax.text(0.75, 0.62, 'Stage 2: Source-Target Training', ha='center', va='center', 
           fontsize=10, fontweight='bold', bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.3'))
    
    # PyHealth Logo/Text
    ax.text(0.05, 0.95, 'PyHealth Contribution:', ha='left', va='center', fontsize=16, fontweight='bold')
    ax.text(0.4, 0.95, 'LOINC Standardization Framework', ha='left', va='center', fontsize=16, color=pyhealth_blue)
    
    # Remove axes
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    
    # Save the figure
    plt.tight_layout()
    plt.savefig('PyHealth_Contribution/images/loinc_mapping_overview.png', dpi=300, bbox_inches='tight')
    plt.close()

if __name__ == "__main__":
    create_loinc_mapping_overview()
    print("LOINC mapping overview diagram created and saved to PyHealth_Contribution/images/loinc_mapping_overview.png") 