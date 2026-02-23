import matplotlib.pyplot as plt
import numpy as np

plt.style.use('seaborn-v0_8-whitegrid')

# --- Data based on final_paper.md Section 4.b and 4.c ---
# (Replace with your actual Top-1 accuracy values)

# 1. Two-Stage vs. Stage 2 Only
config1_labels = ['Two-Stage (Baseline)', 'Stage 2 Only']
config1_accuracies = [70.2, 61.8] # Example: 70.2% vs 61.8%

# 2. Triplet Mining Strategy (for Stage 2)
config2_labels = ['Hard Negative (Baseline)', 'Semi-Hard Negative', 'Random Negative']
config2_accuracies = [70.2, 67.3, 60.5] # Example: 70.2%, 67.3%, plausible 60.5% for Random

# 3. Data Augmentation (evaluated on Standard Test Data)
config3_labels = ['With Augmentation (Baseline)', 'Without Augmentation']
config3_accuracies_std_test = [70.2, 68.5] # Example: 70.2% vs (70.2-1.7)=68.5%

# 4. Data Augmentation (evaluated on Augmented Test Data)
config4_labels = ['With Augmentation (Baseline)', 'Without Augmentation']
config4_accuracies_aug_test = [72.1, 65.3] # Example: 72.1% vs (72.1-6.8)=65.3%


# --- Plotting Function ---
def plot_ablation_bars(ax, labels, accuracies, title, bar_colors=['skyblue', 'salmon', 'lightgreen']):
    bars = ax.bar(labels, accuracies, color=bar_colors[:len(labels)])
    ax.set_ylabel('Top-1 Accuracy (%)', fontsize=10, fontweight='bold')
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.set_ylim(0, max(accuracies) + 10) # Adjust ylim for labels
    ax.tick_params(axis='x', rotation=15, labelsize=9)
    ax.tick_params(axis='y', labelsize=9)

    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 1.5, f'{yval:.1f}%', ha='center', va='bottom', fontsize=8)

# --- Create Figure with Subplots ---
fig, axs = plt.subplots(2, 2, figsize=(15, 10))
fig.suptitle('Ablation Study: Impact on Top-1 Accuracy', fontsize=16, fontweight='bold')

plot_ablation_bars(axs[0, 0], config1_labels, config1_accuracies, 'Impact of Two-Stage Fine-Tuning')
plot_ablation_bars(axs[0, 1], config2_labels, config2_accuracies, 'Impact of Triplet Mining Strategy (Stage 2)')
plot_ablation_bars(axs[1, 0], config3_labels, config3_accuracies_std_test, 'Impact of Data Augmentation (Standard Test Data)')
plot_ablation_bars(axs[1, 1], config4_labels, config4_accuracies_aug_test, 'Impact of Data Augmentation (Augmented Test Data)')

plt.tight_layout(rect=[0, 0, 1, 0.96]) # Adjust layout to make space for suptitle
plt.savefig('images/ablation_study_impact.png', dpi=300)
plt.close()

print("Plot 'ablation_study_impact.png' saved to images folder.") 