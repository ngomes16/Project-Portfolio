import matplotlib.pyplot as plt
import numpy as np

plt.style.use('seaborn-v0_8-whitegrid')

# --- Data based on final_paper.md Section 4.c (Extension 2) ---
# (Illustrative PR curve points. Replace with your actual PR data)
# You would typically get precision and recall arrays from sklearn.metrics.precision_recall_curve
# For illustration, we define some points.
recall_points = np.array([0.0, 0.2, 0.4, 0.6, 0.76, 0.78, 0.85, 0.9, 1.0])
precision_points = np.array([1.0, 0.95, 0.9, 0.85, 0.75, 0.82, 0.65, 0.5, 0.2]) # Example values

# Sort by recall for a proper PR curve
sorted_indices = np.argsort(recall_points)
recall_points = recall_points[sorted_indices]
precision_points = precision_points[sorted_indices]


# Points for annotation (from llm_research_paper.txt X.E.1)
f1_optimal_recall = 0.78
f1_optimal_precision = 0.82
f1_optimal_threshold_text = "F1-Optimal (Sim: 0.25)" # Example similarity threshold

precision_adjusted_recall = 0.76
precision_adjusted_precision = 0.75
precision_adjusted_threshold_text = "Precision-Adj. (Sim: -0.35)" # Example similarity threshold

fig, ax = plt.subplots(figsize=(8, 6))
ax.plot(recall_points, precision_points, marker='o', linestyle='-', color='royalblue', label='PR Curve')

# Annotate specific points
ax.plot(f1_optimal_recall, f1_optimal_precision, 'ro', markersize=8, label=f1_optimal_threshold_text)
ax.annotate(f1_optimal_threshold_text + f'\nP:{f1_optimal_precision*100:.0f}%, R:{f1_optimal_recall*100:.0f}%',
            (f1_optimal_recall, f1_optimal_precision),
            textcoords="offset points", xytext=(10,-15), ha='left', fontsize=9,
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2"))

ax.plot(precision_adjusted_recall, precision_adjusted_precision, 'gs', markersize=8, label=precision_adjusted_threshold_text)
ax.annotate(precision_adjusted_threshold_text + f'\nP:{precision_adjusted_precision*100:.0f}%, R:{precision_adjusted_recall*100:.0f}%',
            (precision_adjusted_recall, precision_adjusted_precision),
            textcoords="offset points", xytext=(10,10), ha='left', fontsize=9,
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-.2"))


ax.set_xlabel('Recall', fontsize=12, fontweight='bold')
ax.set_ylabel('Precision', fontsize=12, fontweight='bold')
ax.set_title('Precision-Recall Curve for No-Match Handling', fontsize=14, fontweight='bold')
ax.legend(fontsize=10, loc='lower left')
ax.set_xlim([-0.05, 1.05])
ax.set_ylim([-0.05, 1.05])
ax.grid(True, linestyle='--', alpha=0.7)

plt.tight_layout()
plt.savefig('images/nomatch_precision_recall.png', dpi=300)
plt.close()

print("Plot 'nomatch_precision_recall.png' saved to images folder.") 