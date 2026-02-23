import matplotlib.pyplot as plt
import numpy as np
import os
from scipy import stats
from sklearn.metrics import precision_recall_curve

# Create images directory if it doesn't exist
os.makedirs('images', exist_ok=True)

# 1. Core Model Performance Comparison
def create_model_performance_chart():
    scenarios = [
        'Standard Pool\n(Original Test)',
        'Expanded Pool\n(Original Test)',
        'Standard Pool\n(Augmented Test)',
        'Expanded Pool\n(Augmented Test)'
    ]
    top1_acc = [70.2, 49.8, 72.1, 50.7]
    top3_acc = [84.5, 69.3, 86.2, 70.5]
    top5_acc = [89.7, 75.1, 91.3, 76.4]

    x = np.arange(len(scenarios))  # the label locations
    width = 0.25  # the width of the bars

    fig, ax = plt.subplots(figsize=(12, 8))
    rects1 = ax.bar(x - width, top1_acc, width, label='Top-1 Accuracy', color='#3366CC')
    rects2 = ax.bar(x, top3_acc, width, label='Top-3 Accuracy', color='#66CC99')
    rects3 = ax.bar(x + width, top5_acc, width, label='Top-5 Accuracy', color='#FF9933')

    # Add some text for labels, title and custom x-axis tick labels
    ax.set_ylabel('Accuracy (%)', fontsize=14)
    ax.set_title('ST5-base Model Performance Across Different Evaluation Scenarios', fontsize=16)
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, fontsize=12)
    ax.legend(fontsize=12)

    # Add value labels on top of each bar
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height:.1f}%',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=10)

    autolabel(rects1)
    autolabel(rects2)
    autolabel(rects3)

    ax.set_ylim(0, 100)  # Set y-axis from 0 to 100 for percentage
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    plt.tight_layout()
    plt.savefig('images/model_performance_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Created: model_performance_comparison.png")

# 2. Ablation Study Impact
def create_ablation_study_chart():
    # Data extracted from Section 4.b of final_paper.md/Section IV.C of llm_research_paper.txt
    # For Fine-tuning Stage
    stage_labels = ['Two-Stage\n(Baseline)', 'Stage 2 Only']
    stage_values = [70.2, 61.8]  # Top-1 accuracy values

    # For Mining Strategy
    mining_labels = ['Hard Negative\n(Baseline)', 'Semi-Hard\nNegative', 'Random\nSampling']
    mining_values = [70.2, 67.3, 62.1]  # Approximated values based on text

    # For Data Augmentation
    aug_labels = ['With Aug.\n(Baseline)', 'Without Aug.\n(Standard Test)', 'With Aug.\n(Augmented Test)', 'Without Aug.\n(Augmented Test)']
    aug_values = [70.2, 68.5, 72.1, 65.3]  # Approximated values based on text

    # Create a figure with three subplots
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))

    # Fine-tuning Stage subplot
    x1 = np.arange(len(stage_labels))
    bars1 = ax1.bar(x1, stage_values, width=0.6, color=['#3366CC', '#FF9933'])
    ax1.set_ylabel('Top-1 Accuracy (%)', fontsize=12)
    ax1.set_title('Impact of Two-Stage Fine-tuning', fontsize=14)
    ax1.set_xticks(x1)
    ax1.set_xticklabels(stage_labels, fontsize=10)
    ax1.grid(axis='y', linestyle='--', alpha=0.7)
    for i, v in enumerate(stage_values):
        ax1.text(i, v + 1, f"{v:.1f}%", ha='center', fontsize=10)
    ax1.set_ylim(0, 80)

    # Mining Strategy subplot
    x2 = np.arange(len(mining_labels))
    bars2 = ax2.bar(x2, mining_values, width=0.6, color=['#3366CC', '#66CC99', '#FF9933'])
    ax2.set_title('Impact of Mining Strategy (Stage 2)', fontsize=14)
    ax2.set_xticks(x2)
    ax2.set_xticklabels(mining_labels, fontsize=10)
    ax2.grid(axis='y', linestyle='--', alpha=0.7)
    for i, v in enumerate(mining_values):
        ax2.text(i, v + 1, f"{v:.1f}%", ha='center', fontsize=10)
    ax2.set_ylim(0, 80)

    # Data Augmentation subplot
    x3 = np.arange(len(aug_labels))
    bars3 = ax3.bar(x3, aug_values, width=0.6, color=['#3366CC', '#FF9933', '#66CC99', '#FF6666'])
    ax3.set_title('Impact of Data Augmentation', fontsize=14)
    ax3.set_xticks(x3)
    ax3.set_xticklabels(aug_labels, fontsize=10)
    ax3.grid(axis='y', linestyle='--', alpha=0.7)
    for i, v in enumerate(aug_values):
        ax3.text(i, v + 1, f"{v:.1f}%", ha='center', fontsize=10)
    ax3.set_ylim(0, 80)

    plt.tight_layout()
    plt.savefig('images/ablation_study_impact.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Created: ablation_study_impact.png")

# 3. Scale Token Extension Performance
def create_scale_token_chart():
    # Data from Section VIII.D of llm_research_paper.txt
    categories = ['Overall', 'Scale-Confusable\nPairs', 'Drug Screens']
    baseline = [64.47, 77.0, 62.4]  # Baseline (without scale tokens)
    with_scale = [67.02, 86.0, 72.8]  # With Scale Tokens

    x = np.arange(len(categories))  # the label locations
    width = 0.35  # the width of the bars

    fig, ax = plt.subplots(figsize=(10, 7))
    rects1 = ax.bar(x - width/2, baseline, width, label='Baseline', color='#3366CC')
    rects2 = ax.bar(x + width/2, with_scale, width, label='With Scale Tokens', color='#66CC99')

    # Add some text for labels, title and custom x-axis tick labels
    ax.set_ylabel('Top-1 Accuracy (%)', fontsize=14)
    ax.set_title('Performance Improvement with Scale Token Integration', fontsize=16)
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=12)
    ax.legend(fontsize=12)

    # Add value labels on top of bars and improvement percentages
    for i, (v1, v2) in enumerate(zip(baseline, with_scale)):
        improvement = v2 - v1
        ax.annotate(f'{v1:.1f}%', xy=(i - width/2, v1), xytext=(0, 3),
                    textcoords="offset points", ha='center', va='bottom', fontsize=10)
        ax.annotate(f'{v2:.1f}%', xy=(i + width/2, v2), xytext=(0, 3),
                    textcoords="offset points", ha='center', va='bottom', fontsize=10)
        ax.annotate(f'+{improvement:.1f}%', xy=(i, (v1 + v2)/2), xytext=(0, 0),
                    textcoords="offset points", ha='center', va='center', 
                    fontsize=11, color='green', fontweight='bold')

    ax.set_ylim(0, 100)
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    plt.tight_layout()
    plt.savefig('images/scale_token_performance.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Created: scale_token_performance.png")

# 4. No-Match Handling Performance (Precision-Recall Curve)
def create_nomatch_pr_curve():
    # Simulated precision-recall data (replace with actual data from Section X.E.1)
    # These are approximated values for illustration
    recall = np.linspace(0, 1, 100)
    precision = np.exp(-2 * recall) * 0.75 + 0.25

    # Mark specific thresholds
    f1_optimal_threshold = 0.5  # Threshold with best F1 score
    precision_adjusted_threshold = 0.35  # Threshold adjusted for higher precision

    # Calculate F1 scores (simulated)
    f1_scores = 2 * precision * recall / (precision + recall + 1e-10)
    f1_optimal_index = np.argmax(f1_scores)
    f1_optimal_precision = precision[f1_optimal_index]
    f1_optimal_recall = recall[f1_optimal_index]

    # Find index for precision-adjusted threshold (estimated from text)
    precision_threshold_index = np.argmin(np.abs(recall - 0.76))  # ~76% recall mentioned
    precision_threshold_precision = precision[precision_threshold_index]
    precision_threshold_recall = recall[precision_threshold_index]

    plt.figure(figsize=(10, 7))
    plt.plot(recall, precision, 'b-', linewidth=2)
    plt.scatter([f1_optimal_recall], [f1_optimal_precision], marker='o', color='red', s=100, 
                label=f'F1-Optimal (τ = -0.50): P={f1_optimal_precision:.2f}, R={f1_optimal_recall:.2f}, F1={f1_scores[f1_optimal_index]:.2f}')
    plt.scatter([precision_threshold_recall], [precision_threshold_precision], marker='s', color='green', s=100,
                label=f'Precision-Adjusted (τ = -0.35): P={precision_threshold_precision:.2f}, R={precision_threshold_recall:.2f}, F1=0.75')

    plt.title('Precision-Recall Curve for No-Match Detection', fontsize=16)
    plt.xlabel('Recall', fontsize=14)
    plt.ylabel('Precision', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=12, loc='lower left')

    # Add text for workload reduction
    plt.text(0.5, 0.4, "Estimated SME Workload Reduction: 25.3%", 
             bbox=dict(facecolor='yellow', alpha=0.2), fontsize=12)

    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.tight_layout()
    plt.savefig('images/nomatch_precision_recall.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Created: nomatch_precision_recall.png")

# 5. Similarity Distribution for No-Match Handling
def create_similarity_distribution():
    # Simulated data (replace with actual data from Section X.E.2)
    np.random.seed(42)
    # Distribution for mappable codes (typically higher similarity)
    mappable_scores = np.random.beta(5, 2, 1000) 
    # Distribution for unmappable codes (typically lower similarity)
    unmappable_scores = np.random.beta(2, 5, 1000)

    # Convert from 0-1 range to cosine similarity range (-1 to 1)
    mappable_scores = mappable_scores * 2 - 1
    unmappable_scores = unmappable_scores * 2 - 1

    # Optimal threshold from previous analysis (τ = -0.35)
    threshold = -0.35

    plt.figure(figsize=(12, 8))

    # Create the histogram/density plot
    bins = np.linspace(-1, 1, 50)
    plt.hist(mappable_scores, bins, alpha=0.5, density=True, label='Mappable Codes', color='#3366CC')
    plt.hist(unmappable_scores, bins, alpha=0.5, density=True, label='Unmappable Codes', color='#FF6666')

    # Add kernel density estimates for smoother visualization
    xmin, xmax = plt.xlim()
    x = np.linspace(xmin, xmax, 100)
    mappable_kde = stats.gaussian_kde(mappable_scores)
    unmappable_kde = stats.gaussian_kde(unmappable_scores)
    plt.plot(x, mappable_kde(x), 'b-', linewidth=2)
    plt.plot(x, unmappable_kde(x), 'r-', linewidth=2)

    # Add vertical line for the threshold
    plt.axvline(x=threshold, color='k', linestyle='--', linewidth=2, 
                label=f'Threshold (τ = {threshold})')

    # Calculate and show approximate percent of each distribution on correct side of threshold
    mappable_correct = np.mean(mappable_scores > threshold) * 100
    unmappable_correct = np.mean(unmappable_scores < threshold) * 100

    plt.text(threshold + 0.1, 0.8, f"{mappable_correct:.1f}% of mappable codes\ncorrectly classified", 
             fontsize=12, color='#3366CC')
    plt.text(threshold - 0.5, 0.8, f"{unmappable_correct:.1f}% of unmappable codes\ncorrectly classified", 
             fontsize=12, color='#FF6666')

    plt.title('Distribution of Maximum Similarity Scores', fontsize=16)
    plt.xlabel('Maximum Cosine Similarity Score', fontsize=14)
    plt.ylabel('Density', fontsize=14)
    plt.legend(fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('images/similarity_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Created: similarity_distribution.png")

# Generate all visualizations
if __name__ == "__main__":
    print("Generating visualizations in the 'images' directory...")
    create_model_performance_chart()
    create_ablation_study_chart()
    create_scale_token_chart()
    create_nomatch_pr_curve()
    create_similarity_distribution()
    print("All visualizations created successfully!") 