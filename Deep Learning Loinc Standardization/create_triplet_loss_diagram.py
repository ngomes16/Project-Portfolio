import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patches as patches
from mpl_toolkits.mplot3d import Axes3D
import os

# Create images directory if it doesn't exist
os.makedirs('images', exist_ok=True)

def create_triplet_loss_diagram():
    # Create figure and 3D axis for embedding space visualization
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Colors
    anchor_color = '#3366CC'
    positive_color = '#66CC99'
    negative_color = '#FF6666'
    text_color = '#333333'
    
    # Set axis labels
    ax.set_xlabel('Embedding Dimension 1', fontsize=10, labelpad=10)
    ax.set_ylabel('Embedding Dimension 2', fontsize=10, labelpad=10)
    ax.set_zlabel('Embedding Dimension 3', fontsize=10, labelpad=10)
    
    # Define points in 3D space
    anchor = np.array([0, 0, 0])
    positive = np.array([1, 0.5, 0.2])
    negative_before = np.array([2, 1.5, 0.8])
    
    # Calculate distances
    pos_dist = np.linalg.norm(positive - anchor)
    neg_dist = np.linalg.norm(negative_before - anchor)
    
    # The margin alpha (typically 0.8 as per the paper)
    alpha = 0.8
    
    # Plot points
    ax.scatter(anchor[0], anchor[1], anchor[2], color=anchor_color, s=200, label='Anchor (A)')
    ax.scatter(positive[0], positive[1], positive[2], color=positive_color, s=200, label='Positive (P)')
    ax.scatter(negative_before[0], negative_before[1], negative_before[2], color=negative_color, s=200, label='Negative (N)')
    
    # Draw lines connecting anchor to positive and negative
    ax.plot([anchor[0], positive[0]], [anchor[1], positive[1]], [anchor[2], positive[2]], 
            color='gray', linestyle='-', linewidth=2)
    ax.plot([anchor[0], negative_before[0]], [anchor[1], negative_before[1]], [anchor[2], negative_before[2]], 
            color='gray', linestyle='--', linewidth=2)
    
    # Draw transparent sphere to show margin radius around anchor
    u, v = np.mgrid[0:2*np.pi:20j, 0:np.pi:10j]
    radius = pos_dist + alpha  # Margin distance
    x = radius * np.cos(u) * np.sin(v) + anchor[0]
    y = radius * np.sin(u) * np.sin(v) + anchor[1]
    z = radius * np.cos(v) + anchor[2]
    ax.plot_surface(x, y, z, color=anchor_color, alpha=0.1)
    
    # Arrow indicating positive is pulled closer to anchor
    pull_arrow = ax.quiver(positive[0], positive[1], positive[2],
                          -0.3, -0.15, -0.05,
                          color=positive_color, arrow_length_ratio=0.3, linewidth=2)
    
    # Arrow indicating negative is pushed outside margin
    push_arrow = ax.quiver(negative_before[0], negative_before[1], negative_before[2],
                          0.4, 0.2, 0.1,
                          color=negative_color, arrow_length_ratio=0.3, linewidth=2)
    
    # Add text annotations
    ax.text(anchor[0], anchor[1], anchor[2]+0.4, 'Anchor (A)', color=anchor_color, fontsize=12, ha='center')
    ax.text(positive[0], positive[1], positive[2]+0.4, 'Positive (P)', color=positive_color, fontsize=12, ha='center')
    ax.text(negative_before[0], negative_before[1], negative_before[2]+0.4, 'Negative (N)', color=negative_color, fontsize=12, ha='center')
    
    # Add distance and margin labels
    midpoint_pos = (anchor + positive) / 2
    ax.text(midpoint_pos[0], midpoint_pos[1], midpoint_pos[2]+0.3, 
            f'D(A,P) = {pos_dist:.2f}', color='gray', fontsize=10, ha='center')
    
    midpoint_neg = (anchor + negative_before) / 2
    ax.text(midpoint_neg[0], midpoint_neg[1], midpoint_neg[2]+0.3, 
            f'D(A,N) = {neg_dist:.2f}', color='gray', fontsize=10, ha='center')
    
    # Add margin circle label
    ax.text(anchor[0], anchor[1], anchor[2]+radius, 
            f'Margin (α = {alpha})', color=anchor_color, fontsize=10, ha='center')
    
    # Add triplet loss formula
    triplet_loss = max(0, pos_dist**2 - neg_dist**2 + alpha)
    formula_text = f'Triplet Loss = max(0, D(A,P)² - D(A,N)² + α) = {triplet_loss:.2f}'
    plt.figtext(0.5, 0.02, formula_text, ha='center', fontsize=12, bbox=dict(facecolor='white', alpha=0.8, pad=5))
    
    # Add push-pull explanation
    plt.figtext(0.15, 0.05, 'Pull positive closer to anchor', 
               color=positive_color, fontsize=10, ha='left')
    plt.figtext(0.65, 0.05, 'Push negative beyond margin', 
               color=negative_color, fontsize=10, ha='left')
    
    # Customize view angle
    ax.view_init(elev=20, azim=30)
    
    # Remove axis ticks to reduce clutter
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_zticks([])
    
    # Set equal aspect ratio
    ax.set_box_aspect([1,1,1])
    
    # Set limits to keep all elements visible
    ax.set_xlim([-1, 3])
    ax.set_ylim([-1, 2.5])
    ax.set_zlim([-0.5, 1.5])
    
    # Add title
    plt.title('Triplet Loss Concept in Embedding Space', fontsize=16, y=0.98)
    
    plt.tight_layout()
    plt.savefig('images/triplet_loss_concept.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Created: triplet_loss_concept.png")

if __name__ == "__main__":
    create_triplet_loss_diagram() 