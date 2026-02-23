import matplotlib.pyplot as plt
import numpy as np

plt.style.use('seaborn-v0_8-whitegrid')

# --- Data based on final_paper.md Section 4.c (Extension 1) ---
# (Replace with your actual Top-1 accuracy values)

categories = ['Overall', 'Scale-Confusable Pairs', 'High-Risk: Drug Screens']
baseline_accuracies = [64.47, 77.0, 60.0]  # Example baseline values
scale_token_accuracies = [67.02, 86.0, 70.4] # Example values with scale tokens (e.g., +10.4% for drug screens)

x = np.arange(len(categories))  # the label locations
width = 0.35  # the width of the bars

fig, ax = plt.subplots(figsize=(10, 7))
rects1 = ax.bar(x - width/2, baseline_accuracies, width, label='Baseline (No Scale Tokens)', color='coral')
rects2 = ax.bar(x + width/2, scale_token_accuracies, width, label='With Scale Tokens', color='mediumseagreen')

# Add some text for labels, title and custom x-axis tick labels, etc.
ax.set_ylabel('Top-1 Accuracy (%)', fontsize=12, fontweight='bold')
ax.set_title('Impact of Scale Token Extension on Top-1 Accuracy', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=10)
ax.legend(fontsize=10)
ax.set_ylim(0, 100)
ax.grid(True, linestyle='--', alpha=0.7)

def autolabel(rects, ax_plot):
    """Attach a text label above each bar in *rects*, displaying its height."""
    for rect in rects:
        height = rect.get_height()
        ax_plot.annotate(f'{height:.2f}%',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=8)

autolabel(rects1, ax)
autolabel(rects2, ax)

fig.tight_layout()
plt.savefig('images/scale_token_performance.png', dpi=300)
plt.close()

print("Plot 'scale_token_performance.png' saved to images folder.") 