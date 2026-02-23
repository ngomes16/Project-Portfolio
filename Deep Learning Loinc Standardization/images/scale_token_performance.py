import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

# Set the aesthetic style of the plots
sns.set_style('whitegrid')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial']

# Data from Section VIII.D in llm_research_paper.txt
categories = [
    'Overall Performance',
    'Scale-Confusable Pairs',
    'Blood Culture Tests',
    'Drug Screen Tests'
]

# Accuracy with and without scale tokens
baseline = [64.47, 77.0, 68.7, 62.1]  # Without scale tokens
with_scale = [67.02, 86.0, 74.5, 72.5]  # With scale tokens

# Calculate improvement
improvement = [(with_scale[i] - baseline[i]) for i in range(len(baseline))]

# Creating the figure and axis
fig, ax = plt.subplots(figsize=(12, 8))

# Setting the width of the bars and positions
bar_width = 0.35
r1 = np.arange(len(categories))
r2 = [x + bar_width for x in r1]

# Creating the bars
bars1 = ax.bar(r1, baseline, width=bar_width, label='Baseline (Without Scale Tokens)', color='#1f77b4', edgecolor='black', linewidth=1)
bars2 = ax.bar(r2, with_scale, width=bar_width, label='With Scale Tokens', color='#2ca02c', edgecolor='black', linewidth=1)

# Adding the values on top of the bars
def add_labels(bars):
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{height:.1f}%', ha='center', va='bottom', fontsize=10)

add_labels(bars1)
add_labels(bars2)

# Adding improvement percentages above the bars
for i in range(len(categories)):
    x = r1[i] + bar_width / 2
    plt.annotate(f'+{improvement[i]:.1f}%', 
                xy=(x + bar_width/2, with_scale[i] + 2),
                xytext=(0, 10),  # 10 points vertical offset
                textcoords="offset points",
                ha='center', va='bottom',
                bbox=dict(boxstyle="round,pad=0.3", fc='#d9ead3', ec="green", alpha=0.8),
                fontsize=9)

# Setting axis labels and title
ax.set_xlabel('Test Category', fontsize=12, fontweight='bold')
ax.set_ylabel('Top-1 Accuracy (%)', fontsize=12, fontweight='bold')
ax.set_title('Scale Token Extension Performance Impact', fontsize=14, fontweight='bold', pad=20)

# Setting the positions of the x-ticks
ax.set_xticks([r + bar_width / 2 for r in range(len(categories))])
ax.set_xticklabels(categories, fontsize=11)

# Setting the y-axis limits
ax.set_ylim(0, 100)

# Adding a legend
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=2, fontsize=11)

# Adding a grid for the y-axis
ax.yaxis.grid(True, linestyle='--', alpha=0.7)

# Adding a text note about the source of data
plt.figtext(0.5, -0.05, "Data from llm_research_paper.txt Section VIII.D on Scale Token Extension", 
            ha="center", fontsize=10, style='italic')

# Adding an explanatory note
plt.figtext(0.5, -0.08, 
           "Scale tokens (e.g., ##scale=qn##) help distinguish between qualitative and quantitative tests\n"+
           "Scale-confusable pairs: Similar tests differing only in scale type",
           ha="center", fontsize=9, style='italic')

# Adjusting the layout
plt.tight_layout()

# Save the figure
plt.savefig('images/new_visualizations/scale_token_performance.png', dpi=300, bbox_inches='tight')
plt.savefig('images/new_visualizations/scale_token_performance.pdf', bbox_inches='tight')

print("Scale token extension performance visualization created successfully.") 