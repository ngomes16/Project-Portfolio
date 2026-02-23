import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

plt.style.use('seaborn-v0_8-whitegrid')

# --- Data based on final_paper.md Section 4.c (Extension 2) ---
# (Illustrative data. Replace with your actual similarity score distributions)
np.random.seed(42) # for reproducibility

# Simulate similarity scores (cosine similarities are often between -1 and 1, or 0 and 1 if using dot product of normalized vectors)
# Assuming scores are roughly normalized and represent semantic similarity
mappable_scores = np.random.normal(loc=0.6, scale=0.2, size=500) # Higher mean for mappable
unmappable_scores = np.random.normal(loc=0.1, scale=0.25, size=500) # Lower mean for unmappable

# Ensure scores are within a plausible range, e.g., -1 to 1, or 0 to 1
# Here, let's clip to a -0.5 to 1 range for better visualization of example thresholds
mappable_scores = np.clip(mappable_scores, -0.5, 1.0)
unmappable_scores = np.clip(unmappable_scores, -0.5, 1.0)

# Chosen threshold for indication (example value, e.g., F1-optimal from PR curve)
# From llm_research_paper.txt X.E.1: F1-optimal threshold was 0.25
# From llm_research_paper.txt X.E.1: Precision-adjusted threshold was -0.35
chosen_threshold_f1 = 0.25
chosen_threshold_prec_adj = -0.35

fig, ax = plt.subplots(figsize=(10, 6))

sns.kdeplot(mappable_scores, ax=ax, label='Mappable Codes Sim. Scores', fill=True, alpha=0.5, color='dodgerblue')
sns.kdeplot(unmappable_scores, ax=ax, label='Unmappable Codes Sim. Scores', fill=True, alpha=0.5, color='orangered')

# Plot thresholds
ax.axvline(chosen_threshold_f1, color='green', linestyle='--', linewidth=2, label=f'Threshold τ (F1-Opt) = {chosen_threshold_f1:.2f}')
ax.axvline(chosen_threshold_prec_adj, color='purple', linestyle=':', linewidth=2, label=f'Threshold τ (Prec-Adj) = {chosen_threshold_prec_adj:.2f}')

ax.set_xlabel('Maximum Cosine Similarity Score', fontsize=12, fontweight='bold')
ax.set_ylabel('Density', fontsize=12, fontweight='bold')
ax.set_title('Distribution of Max Similarity Scores for No-Match Handling', fontsize=14, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(True, linestyle='--', alpha=0.6)

plt.tight_layout()
plt.savefig('images/similarity_distribution.png', dpi=300)
plt.close()

print("Plot 'similarity_distribution.png' saved to images folder.") 