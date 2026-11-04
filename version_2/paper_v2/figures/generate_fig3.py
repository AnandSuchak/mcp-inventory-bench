#!/usr/bin/env python3
"""
Generates Figure 3: Task Cluster Token Workload Comparison: Break-Even Boundary
Project: LASR-MCP / version_2
Output: version_2/paper_v2/figures/fig3_cluster_breakdown.pdf
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Publication typography standards
plt.rcParams.update({
    'font.size': 9,
    'font.family': 'serif',
    'axes.labelsize': 9,
    'axes.titlesize': 10,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 8,
    'figure.titlesize': 10,
    'pdf.fonttype': 42,
    'ps.fonttype': 42
})

clusters = ['C1: Routine\nReplenish', 'C2: Expedited\nEmergency', 'C3: Bulk\nProcurement', 'C4: Depot\nRebalance']
full_tok = [979.8, 1274.2, 1008.1, 1205.0]
k0_tok = [1675.2, 2231.9, 2228.9, 2094.6]
lasr_tok = [847.6, 1557.5, 1610.9, 1609.9]

fig, ax = plt.subplots(figsize=(7.16, 2.9), dpi=300)

x = np.arange(len(clusters))
width = 0.25

b1 = ax.bar(x - width, full_tok, width, label='Full Control Baseline', color='#0072B2', edgecolor='black', linewidth=0.8, alpha=0.85, hatch='//')
b2 = ax.bar(x, k0_tok, width, label='Zero-Constraint (CI k=0)', color='#D55E00', edgecolor='black', linewidth=0.8, alpha=0.85, hatch='\\\\')
b3 = ax.bar(x + width, lasr_tok, width, label='Proposed LASR (k=2 Reactive)', color='#009E73', edgecolor='black', linewidth=0.8, alpha=0.85, hatch='..')

ax.set_ylabel('Mean Recorded P+C Tokens / Trial', fontweight='bold', fontsize=9)
ax.set_ylim(0, 3050)
ax.set_xticks(x)
ax.set_xticklabels(clusters, fontsize=8)
ax.grid(axis='y', linestyle=':', alpha=0.6)

# Horizontal legend at the top to ensure zero collision with any annotation or bars
ax.legend(ncol=3, loc='lower center', bbox_to_anchor=(0.5, 1.02), frameon=True, edgecolor='#cccccc', framealpha=0.95, fontsize=8)

# C1 savings annotation: placed at y=2200, with arrow pointing down to green bar at 847.6
ax.annotate('+13.5% Net Savings\n(847.6 vs 979.8)',
            xy=(x[0] + width, lasr_tok[0]),
            xytext=(x[0] + width, 2200),
            ha='center', fontsize=7.2, fontweight='bold', color='#009E73',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor='#009E73', linewidth=0.9, alpha=0.95),
            arrowprops=dict(arrowstyle='->', color='#009E73', lw=1.0, shrinkB=4))

# C2, C3, C4 workload labels: placed cleanly ABOVE all bars at y=2650 with subtle arrows pointing down to the green bars
for idx, pct, val in [(1, '+22.2%', lasr_tok[1]), (2, '+59.8%', lasr_tok[2]), (3, '+33.6%', lasr_tok[3])]:
    ax.annotate(f'{pct} LASR\nWorkload',
                xy=(x[idx] + width, val),
                xytext=(x[idx] + width, 2650),
                ha='center', fontsize=7.0, fontweight='bold', color='#333333',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor='#888888', linewidth=0.7, alpha=0.95),
                arrowprops=dict(arrowstyle='->', color='#666666', lw=0.8, shrinkB=4))

plt.tight_layout()

out_dir = Path(__file__).resolve().parent
fig.savefig(out_dir / 'fig3_cluster_breakdown.pdf', format='pdf', bbox_inches='tight')
fig.savefig(out_dir / 'fig3_cluster_breakdown.png', format='png', dpi=300, bbox_inches='tight')
plt.close(fig)
print('Figure 3 generated successfully: PDF and PNG created.')
