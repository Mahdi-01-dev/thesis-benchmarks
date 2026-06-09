#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 9,
})

# 1. Track and load both target files
csv_mmds = 'mmds_microbenchmarks.csv'
csv_hash = 'hash_control_microbenchmarks.csv'

if not os.path.exists(csv_mmds) or not os.path.exists(csv_hash):
    print(f"Error: Missing target metrics. Ensure '{csv_mmds}' and '{csv_hash}' both exist.")
    exit(1)

df_mmds_raw = pd.read_csv(csv_mmds)
df_hash_raw = pd.read_csv(csv_hash)

# Filter iterations to measured runs only (>1)
df_mmds = df_mmds_raw[df_mmds_raw['iteration'] > 1]
df_hash = df_hash_raw[df_hash_raw['iteration'] > 1]

# Calculate averages
means_mmds = df_mmds.mean()
means_hash = df_hash.mean()

# 2. Define targeted comparative metrics & clean labels
metrics = [
    'pci_total_us', 'pci_transport_us', 'net_state_us',
    'mmds_routing_us', 'build_queues_us', 'buffer_reset_us', 'reapply_activation_us'
]

labels = [
    'Total PCI Net Reset', 'PCI Transport', 'Net Device State',
    'MMDS Routing', 'Build VirtQueues', 'Buffer Reset', 'Reapply Activation State'
]

values_mmds = [float(means_mmds[m]) for m in metrics]
values_hash = [float(means_hash[m]) for m in metrics]

# 3. Canvas and layout geometry initialization
fig, ax = plt.subplots(figsize=(12, 6.5))

x = np.arange(len(labels))
width = 0.38  # Bar thickness

# Render baseline aggregate mean bars
rects1 = ax.bar(x - width/2, values_mmds, width, label='metadata function mean', 
                color='#d62728', alpha=0.4, edgecolor='#d62728', linewidth=1.2)
rects2 = ax.bar(x + width/2, values_hash, width, label='hash function (mmds not enabled) mean', 
                color='#1f77b4', alpha=0.4, edgecolor='#1f77b4', linewidth=1.2)

# --- HIGHLIGHT: Overlaying Raw Iteration Scatter Plots ---
# Seed the random generator for consistent horizontal distribution spacing (jitter)
np.random.seed(42)

for idx, metric in enumerate(metrics):
    # Extract data series matching the current metric column
    y_data_mmds = df_mmds[metric].values
    y_data_hash = df_hash[metric].values
    
    # Generate horizontal offsets centered precisely over the respective bar midpoint
    # Using small random variance spreads (jitter) so overlapping values remain legible
    x_mmds_jitter = np.random.normal(idx - width/2, 0.03, size=len(y_data_mmds))
    x_hash_jitter = np.random.normal(idx + width/2, 0.03, size=len(y_data_hash))
    
    # Plot individual iteration marks over the transparent bars
    ax.scatter(x_mmds_jitter, y_data_mmds, color='#b2182b', s=12, alpha=0.7, zorder=3, marker='o')
    ax.scatter(x_hash_jitter, y_data_hash, color='#2166ac', s=12, alpha=0.7, zorder=3, marker='^')

# Value labels over bars (aligned dynamically onto means)
def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height:.1f}µs',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 4),  
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=8.5, fontweight='bold', alpha=0.85)

autolabel(rects1)
autolabel(rects2)

# --- GRAPH LAYOUT ADJUSTMENTS ---
ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=15, ha='right', fontweight='bold')
ax.set_ylabel('Latency (microseconds, µs)', fontweight='bold')
ax.set_title('Network Reset Latency Comparison: Active MMDS Subsystem vs. Hash Control Baseline', fontweight='bold', pad=25)

# Add custom dummy elements to legend to explicitly denote scatter distribution meanings
handles, plot_labels = ax.get_legend_handles_labels()
from matplotlib.lines import Line2D
custom_legend_elements = [
    handles[0],
    Line2D([0], [0], marker='o', color='w', markerfacecolor='#b2182b', markersize=6, label='MMDS Sample Iterations'),
    handles[1],
    Line2D([0], [0], marker='^', color='w', markerfacecolor='#2166ac', markersize=6, label='Hash Sample Iterations')
]

ax.legend(handles=custom_legend_elements, loc='upper right', frameon=True)

plt.tight_layout()
output_pdf = 'experiment4_control_comparison.pdf'
plt.savefig(output_pdf, dpi=300)
print(f"Success! Comparative chart with overlaid iteration points written to: {output_pdf}")
