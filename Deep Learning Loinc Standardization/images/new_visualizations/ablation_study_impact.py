import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

# Set the aesthetic style of the plots
sns.set_style('whitegrid')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial']

# Data for ablation studies (Top-1 accuracy percentages)
# Based on Table 2 from the paper and llm_research_paper.txt Section IV.C
categories = [
    'Baseline (Two-Stage)',
    'Stage 2 Only',
    'Hard Negative Mining (Baseline)',
    'Semi-Hard Negative Mining',
    'Random Negative Mining',
    'With Data Augmentation (Baseline)',
    'Without Data Augmentation'
]

# Top-1 accuracy results
accuracy = [70.2, 61.8, 70.2, 67.3, 58.9, 70.2, 68.5]

# For augmented test data (separate values)
accuracy_augmented = [72.1, 65.7, 72.1, 68.9, 60.2, 72.1, 65.3]

# Creating the subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12), sharex=True)

# Colors for different ablation groups
colors = ['#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#d62728', '#2ca02c', '#98df8a']

# Plotting for standard test data
bars1 = ax1.bar(categories, accuracy, color=colors, edgecolor='black', linewidth=1)

# Adding values on top of bars
for bar in bars1:
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
             f'{height:.1f}%', ha='center', va='bottom', fontsize=10)

# Plotting for augmented test data  
bars2 = ax2.bar(categories, accuracy_augmented, color=colors, edgecolor='black', linewidth=1)

# Adding values on top of bars
for bar in bars2:
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height + 1,
             f'{height:.1f}%', ha='center', va='bottom', fontsize=10)

# Setting titles and labels
ax1.set_title('Ablation Study Impact on Top-1 Accuracy (Standard Test Data)', fontsize=14, fontweight='bold', pad=20)
ax2.set_title('Ablation Study Impact on Top-1 Accuracy (Augmented Test Data)', fontsize=14, fontweight='bold', pad=20)

ax1.set_ylabel('Top-1 Accuracy (%)', fontsize=12, fontweight='bold')
ax2.set_ylabel('Top-1 Accuracy (%)', fontsize=12, fontweight='bold')
ax2.set_xlabel('Ablation Configuration', fontsize=12, fontweight='bold')

# Setting y-axis limits
ax1.set_ylim(0, 100)
ax2.set_ylim(0, 100)

# Adding grid for better readability
ax1.yaxis.grid(True, linestyle='--', alpha=0.7)
ax2.yaxis.grid(True, linestyle='--', alpha=0.7)

# Rotating x-tick labels for better readability
plt.xticks(rotation=25, ha='right', fontsize=10)

# Adding a text note about the data source
plt.figtext(0.5, 0.01, "Data from ablation studies in the reproduced model", 
            ha="center", fontsize=10, style='italic')

# Group indicators
# Create colored patches with lines between related components
def add_group_indicators(ax, y_pos, color, start_idx, end_idx, label):
    x_positions = np.arange(len(categories))[start_idx:end_idx+1]
    y_positions = [y_pos] * len(x_positions)
    ax.plot(x_positions, y_positions, color=color, linewidth=3, alpha=0.5)
    ax.text(np.mean(x_positions), y_pos+2, label, ha='center', fontsize=9, fontweight='bold')

# Add group indicators to each subplot
for ax in [ax1, ax2]:
    add_group_indicators(ax, 6, '#1f77b4', 0, 1, 'Training Stage Impact')
    add_group_indicators(ax, 12, '#ff7f0e', 2, 4, 'Mining Strategy Impact')
    add_group_indicators(ax, 18, '#2ca02c', 5, 6, 'Data Augmentation Impact')

# Adjusting layout
plt.tight_layout()
plt.subplots_adjust(hspace=0.3, bottom=0.15)

# Save the figure
plt.savefig('images/new_visualizations/ablation_study_impact.png', dpi=300, bbox_inches='tight')
plt.savefig('images/new_visualizations/ablation_study_impact.pdf', bbox_inches='tight')

print("Ablation study impact visualization created successfully.") 