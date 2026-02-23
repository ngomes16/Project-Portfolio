import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Data based on final_paper.md, Table 1 (replace with your actual mean values)
# Scenarios are groups, metrics are bars within groups.
data = {
    'Scenario': [
        'Standard Pool (Original Test)', 'Standard Pool (Original Test)', 'Standard Pool (Original Test)',
        'Expanded Pool (Original Test)', 'Expanded Pool (Original Test)', 'Expanded Pool (Original Test)',
        'Standard Pool (Augmented Test)', 'Standard Pool (Augmented Test)', 'Standard Pool (Augmented Test)',
        'Expanded Pool (Augmented Test)', 'Expanded Pool (Augmented Test)', 'Expanded Pool (Augmented Test)'
    ],
    'Metric': [
        'Top-1 Acc.', 'Top-3 Acc.', 'Top-5 Acc.',
        'Top-1 Acc.', 'Top-3 Acc.', 'Top-5 Acc.',
        'Top-1 Acc.', 'Top-3 Acc.', 'Top-5 Acc.',
        'Top-1 Acc.', 'Top-3 Acc.', 'Top-5 Acc.'
    ],
    'Accuracy (%)': [
        70.2, 84.5, 89.7,  # Standard Pool (Original Test)
        49.8, 69.3, 75.1,  # Expanded Pool (Original Test)
        72.1, 86.2, 91.3,  # Standard Pool (Augmented Test)
        50.7, 70.5, 76.4   # Expanded Pool (Augmented Test)
    ]
}
df = pd.DataFrame(data)

# --- Plotting ---
plt.style.use('seaborn-v0_8-whitegrid') # Using a seaborn style
fig, ax = plt.subplots(figsize=(14, 8))

pivot_df = df.pivot(index='Scenario', columns='Metric', values='Accuracy (%)')
# Reorder columns for logical presentation
pivot_df = pivot_df[['Top-1 Acc.', 'Top-3 Acc.', 'Top-5 Acc.']]

pivot_df.plot(kind='bar', ax=ax, colormap='viridis')

ax.set_title('Reproduced ST5-Base Model Performance Comparison', fontsize=16, fontweight='bold')
ax.set_xlabel('Evaluation Scenario', fontsize=12, fontweight='bold')
ax.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
ax.tick_params(axis='x', rotation=25, labelsize=10)
ax.tick_params(axis='y', labelsize=10)
ax.legend(title='Accuracy Metric', title_fontsize='11', fontsize='10')
ax.grid(True, linestyle='--', alpha=0.7)

# Add percentage labels on top of bars
for p in ax.patches:
    ax.annotate(f"{p.get_height():.1f}%",
                (p.get_x() + p.get_width() / 2., p.get_height()),
                ha='center', va='center',
                xytext=(0, 9),
                textcoords='offset points',
                fontsize=8, color='dimgray')

plt.ylim(0, 105) # Extend y-limit a bit for labels
plt.tight_layout()
plt.savefig('images/model_performance_comparison.png', dpi=300)
plt.close()

print("Plot 'model_performance_comparison.png' saved to images folder.") 