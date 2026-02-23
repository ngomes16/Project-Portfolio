import matplotlib.pyplot as plt
import numpy as np
import os

# Create images directory if it doesn't exist
os.makedirs('images', exist_ok=True)

def create_error_distribution():
    # Data for error categories (example data, replace with actual distribution)
    categories = [
        'Specimen Mismatch',
        'Property Mismatch',
        'Ambiguous Source',
        'Token Range Error',
        'Scale Type Error',
        'Other Errors'
    ]
    
    percentages = [28, 23, 19, 14, 11, 5]  # Example percentages
    
    # Create figure for pie chart
    plt.figure(figsize=(10, 8))
    
    # Colors
    colors = ['#FF6666', '#FFCC33', '#66CC99', '#3366CC', '#CC6699', '#999999']
    
    # Create pie chart
    patches, texts, autotexts = plt.pie(
        percentages, 
        labels=categories,
        colors=colors,
        autopct='%1.1f%%',
        startangle=90,
        wedgeprops={'edgecolor': 'white', 'linewidth': 1.5},
        textprops={'fontsize': 11}
    )
    
    # Adjust text properties for better display of long category names
    for text in texts:
        text.set_horizontalalignment('center')
    
    # Equal aspect ratio ensures that pie is drawn as a circle
    plt.axis('equal')
    
    # Add title
    plt.title('Distribution of Error Categories', fontsize=16, pad=20)
    
    # Add legend
    plt.legend(patches, categories, loc='best', fontsize=11)
    
    # Save figure
    plt.tight_layout()
    plt.savefig('images/error_category_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Created: error_category_distribution.png")
    
    # Also create a horizontal bar chart version for better readability of categories
    plt.figure(figsize=(10, 7))
    
    # Sort for better visualization
    sorted_indices = np.argsort(percentages)
    sorted_categories = [categories[i] for i in sorted_indices]
    sorted_percentages = [percentages[i] for i in sorted_indices]
    sorted_colors = [colors[i] for i in sorted_indices]
    
    # Create horizontal bar chart
    bars = plt.barh(sorted_categories, sorted_percentages, color=sorted_colors, 
                   edgecolor='white', linewidth=1.5, height=0.6)
    
    # Add value labels on bars
    for bar in bars:
        width = bar.get_width()
        plt.text(
            width + 1,
            bar.get_y() + bar.get_height()/2,
            f'{width:.1f}%',
            ha='left', 
            va='center', 
            fontsize=11,
            fontweight='bold'
        )
    
    # Add labels and title
    plt.xlabel('Percentage (%)', fontsize=12)
    plt.title('Distribution of Error Categories', fontsize=16)
    plt.xlim(0, max(percentages) * 1.15)  # Add some headroom for labels
    
    # Add grid lines for better readability
    plt.grid(axis='x', linestyle='--', alpha=0.7)
    
    # Save figure
    plt.tight_layout()
    plt.savefig('images/error_category_distribution_bar.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Created: error_category_distribution_bar.png")

if __name__ == "__main__":
    create_error_distribution() 