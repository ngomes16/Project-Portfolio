import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

# Set the aesthetic style of the plots
sns.set_style('whitegrid')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial']

# Data from Table 1 in the paper
categories = ['Top-1 Accuracy', 'Top-3 Accuracy', 'Top-5 Accuracy']

# Model performance data (in percentages)
standard_orig = [70.2, 84.5, 89.7]  # Standard Target Pool (Original Test Data)
expanded_orig = [49.8, 69.3, 75.1]  # Expanded Target Pool (Original Test Data)
standard_aug = [72.1, 86.2, 91.3]   # Standard Target Pool (Augmented Test Data)
expanded_aug = [50.7, 70.5, 76.4]   # Expanded Target Pool (Augmented Test Data)

# Creating the figure and axis
fig, ax = plt.subplots(figsize=(12, 8))

# Setting the width of the bars and positions
bar_width = 0.2
r1 = np.arange(len(categories))
r2 = [x + bar_width for x in r1]
r3 = [x + bar_width for x in r2]
r4 = [x + bar_width for x in r3]

# Creating the bars
bars1 = ax.bar(r1, standard_orig, width=bar_width, label='Standard Target Pool (Original Test Data)', color='#1f77b4', edgecolor='black', linewidth=1)
bars2 = ax.bar(r2, expanded_orig, width=bar_width, label='Expanded Target Pool (Original Test Data)', color='#ff7f0e', edgecolor='black', linewidth=1)
bars3 = ax.bar(r3, standard_aug, width=bar_width, label='Standard Target Pool (Augmented Test Data)', color='#2ca02c', edgecolor='black', linewidth=1)
bars4 = ax.bar(r4, expanded_aug, width=bar_width, label='Expanded Target Pool (Augmented Test Data)', color='#d62728', edgecolor='black', linewidth=1)

# Adding the values on top of the bars
def add_labels(bars):
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{height:.1f}%', ha='center', va='bottom', fontsize=9)

add_labels(bars1)
add_labels(bars2)
add_labels(bars3)
add_labels(bars4)

# Setting axis labels and title
ax.set_xlabel('Evaluation Metric', fontsize=12, fontweight='bold')
ax.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
ax.set_title('ST5-base Model Performance Across Different Evaluation Scenarios', fontsize=14, fontweight='bold', pad=20)

# Setting the positions of the x-ticks
ax.set_xticks([r + bar_width * 1.5 for r in range(len(categories))])
ax.set_xticklabels(categories, fontsize=11)

# Setting the y-axis limits
ax.set_ylim(0, 100)

# Adding a legend
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=2, fontsize=10)

# Adding a grid for the y-axis
ax.yaxis.grid(True, linestyle='--', alpha=0.7)

# Adding a text note about the source of data
plt.figtext(0.5, -0.05, "Data from reproduced ST5-base model (5-fold cross-validation mean)", 
            ha="center", fontsize=10, style='italic')

# Adjusting the layout
plt.tight_layout()

# Save the figure
plt.savefig('images/new_visualizations/core_model_performance.png', dpi=300, bbox_inches='tight')
plt.savefig('images/new_visualizations/core_model_performance.pdf', bbox_inches='tight')

print("Core model performance visualization created successfully.") 