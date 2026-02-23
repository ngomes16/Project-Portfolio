import matplotlib.pyplot as plt
import numpy as np

plt.style.use('seaborn-v0_8-whitegrid')

# Error category data as reported in final_paper.md Section 4.a
categories = [
    'Specimen Mismatch',
    'Ambiguous Source',
    'Property Mismatch',
    'Similar Descriptions',
    'Methodological Diff.',
    'Completely Different',
    'Other'
]

percentages = [34.8, 26.5, 17.2, 14.3, 5.2, 1.3, 0.7]

# Sort by frequency for better visualization
sorted_indices = np.argsort(percentages)[::-1]  # descending order
sorted_categories = [categories[i] for i in sorted_indices]
sorted_percentages = [percentages[i] for i in sorted_indices]

# Set up the plot with a horizontal bar chart
fig, ax = plt.subplots(figsize=(10, 6))

# Create horizontal bars
bars = ax.barh(sorted_categories, sorted_percentages, color='skyblue', edgecolor='navy', alpha=0.8)

# Customize the plot
ax.set_xlabel('Frequency (%)', fontsize=12, fontweight='bold')
ax.set_title('Distribution of Error Categories', fontsize=14, fontweight='bold')
ax.tick_params(axis='y', labelsize=10)
ax.tick_params(axis='x', labelsize=10)
ax.grid(True, linestyle='--', alpha=0.7, axis='x')

# Add percentage labels on the bars
for bar in bars:
    width = bar.get_width()
    label_x_pos = width + 0.5
    ax.text(label_x_pos, bar.get_y() + bar.get_height()/2, f'{width:.1f}%',
            va='center', fontsize=9)

# Adjust layout
plt.tight_layout()
plt.savefig('images/error_category_distribution_bar.png', dpi=300)
plt.close()

# Create a pie chart version as well
fig, ax = plt.subplots(figsize=(9, 7))

# Custom colors for better visibility
colors = plt.cm.tab10(np.arange(len(sorted_categories)))

# Create the pie chart
wedges, texts, autotexts = ax.pie(
    sorted_percentages, 
    labels=sorted_categories,
    autopct='%1.1f%%', 
    startangle=90, 
    colors=colors,
    wedgeprops={'width': 0.5, 'edgecolor': 'w', 'linewidth': 1.5}
)

# Styling
plt.setp(autotexts, size=9, weight='bold')
plt.setp(texts, size=10)
ax.set_title('Distribution of Error Categories', fontsize=14, fontweight='bold')

# Save the pie chart
plt.tight_layout()
plt.savefig('images/error_category_distribution.png', dpi=300)
plt.close()

print("Plots 'error_category_distribution_bar.png' and 'error_category_distribution.png' saved to images folder.") 