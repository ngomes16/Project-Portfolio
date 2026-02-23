import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from scipy import stats

# Set the aesthetic style of the plots
sns.set_style('whitegrid')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial']

# Create the figure
fig, ax = plt.subplots(figsize=(12, 8))

# Generate simulated distribution data based on the paper's description
# For mappable codes - higher similarity scores (around 0.5-0.9)
np.random.seed(42)  # For reproducibility
mappable_similarity = np.concatenate([
    np.random.normal(0.75, 0.1, 700),  # Main distribution for mappable
    np.random.normal(0.5, 0.12, 300)    # Tail for harder mappable cases
])
mappable_similarity = np.clip(mappable_similarity, 0, 1)  # Clip to valid range

# For unmappable codes - lower similarity scores (around 0.1-0.5)
unmappable_similarity = np.concatenate([
    np.random.normal(0.3, 0.08, 600),   # Main distribution for unmappable
    np.random.normal(0.5, 0.1, 400)     # Tail for confusable unmappable cases
])
unmappable_similarity = np.clip(unmappable_similarity, 0, 1)  # Clip to valid range

# Plot the distributions using kernel density estimation
sns.histplot(mappable_similarity, bins=30, alpha=0.6, label='Mappable Codes', 
            kde=True, color='#1f77b4', ax=ax, stat='density')
sns.histplot(unmappable_similarity, bins=30, alpha=0.6, label='Unmappable Codes', 
            kde=True, color='#d62728', ax=ax, stat='density')

# Add a vertical line for the threshold value
threshold = 0.35  # F1-optimal threshold from the previous visualization
ax.axvline(x=threshold, color='k', linestyle='--', linewidth=2)
ax.text(threshold+0.01, 3, f'Threshold τ = {threshold}', rotation=90, verticalalignment='center', fontsize=10)

# Calculate the overlap area
x = np.linspace(0, 1, 1000)
kde_mappable = stats.gaussian_kde(mappable_similarity)
kde_unmappable = stats.gaussian_kde(unmappable_similarity)
y_mappable = kde_mappable(x)
y_unmappable = kde_unmappable(x)

# Shade the confusion regions
# False negatives (mappable classified as unmappable)
idx_fn = np.where(x < threshold)[0]
ax.fill_between(x[idx_fn], 0, y_mappable[idx_fn], color='#1f77b4', alpha=0.3)
# False positives (unmappable classified as mappable)
idx_fp = np.where(x >= threshold)[0]
ax.fill_between(x[idx_fp], 0, y_unmappable[idx_fp], color='#d62728', alpha=0.3)

# Add annotations for confusion regions
ax.annotate('False Negatives\n(Mappable misclassified)', 
           xy=(0.2, 0.5), xytext=(0.1, 1.5),
           arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=.2', color='#1f77b4'),
           fontsize=10, color='#1f77b4')

ax.annotate('False Positives\n(Unmappable misclassified)', 
           xy=(0.5, 0.8), xytext=(0.7, 1.5),
           arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=.2', color='#d62728'),
           fontsize=10, color='#d62728')

# Setting axis labels and title
ax.set_xlabel('Maximum Similarity Score', fontsize=12, fontweight='bold')
ax.set_ylabel('Density', fontsize=12, fontweight='bold')
ax.set_title('Distribution of Maximum Similarity Scores for Mappable vs. Unmappable Codes', 
             fontsize=14, fontweight='bold', pad=20)

# Adding a legend
ax.legend(fontsize=11)

# Adding a text note about the data source
plt.figtext(0.5, 0.01, 
           "Simulated data based on description in llm_research_paper.txt Section X.E.2.\n"+
           "The threshold τ determines whether a source code is considered mappable (≥τ) or unmappable (<τ).",
           ha="center", fontsize=10, style='italic')

# Setting the axis limits
ax.set_xlim(0, 1)
ax.set_ylim(0, 4)

# Adjusting the layout
plt.tight_layout()

# Save the figure
plt.savefig('images/new_visualizations/similarity_distribution.png', dpi=300, bbox_inches='tight')
plt.savefig('images/new_visualizations/similarity_distribution.pdf', bbox_inches='tight')

print("Similarity distribution visualization created successfully.") 