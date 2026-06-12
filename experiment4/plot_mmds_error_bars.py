#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg') # Force non-interactive backend to prevent graphics segfaults
import matplotlib.pyplot as plt

# Publication styling configuration
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 9.5,
    'ytick.labelsize': 9,
})

# 1. Track and load both target files
csv_mmds = 'mmds_microbenchmarks.csv'
csv_hash = 'hash_control_microbenchmarks.csv'

if not os.path.exists(csv_mmds) or not os.path.exists(csv_hash):
    print(f"Error: Missing target metrics. Ensure '{csv_mmds}' and '{csv_hash}' both exist.")
    exit(1)

df_mmds = pd.read_csv(csv_mmds)
df_hash = pd.read_csv(csv_hash)

# Target pre-cleared iterations 1 to 30 as specified
#df_mmds = df_mmds_raw[df_mmds_raw['iteration'].between(1, 30)]
#df_hash = df_hash_raw[df_hash_raw['iteration'].between(1, 30)]

# 2. Define all targeted comparative metrics including rate limiters
metrics = [
    'pci_total_us', 'pci_transport_us', 'net_state_us',
    'rx_rate_limiter_us', 'tx_rate_limiter_us', 'mmds_routing_us',
    'build_queues_us', 'buffer_reset_us', 'reapply_activation_us'
]

labels = [
    'Total PCI Net Reset', 'PCI Transport', 'Net Device State',
    'RX Rate Limiter', 'TX Rate Limiter', 'MMDS Network Stack',
    'Build VirtQueues', 'Buffer Reset', 'Reapply Activation State'
]

# Calculate statistical averages (Means)
values_mmds = [float(df_mmds[m].mean()) for m in metrics]
values_hash = [float(df_hash[m].mean()) for m in metrics]

# Calculate statistical variation (Standard Deviation for the Whiskers)
std_mmds = [float(df_mmds[m].std()) for m in metrics]
std_hash = [float(df_hash[m].std()) for m in metrics]

# 3. Canvas and layout geometry initialization
fig, ax = plt.subplots(figsize=(14, 7))

x = np.arange(len(labels))
width = 0.38  # Bar thickness

# Configure elegant whisker styling props
error_config = dict(ecolor='#333333', lw=1.2, capsize=4, capthick=1.2, zorder=3)

# Render structural mean bars with attached error whiskers directly
rects1 = ax.bar(x - width/2, values_mmds, width, yerr=std_mmds, error_kw=error_config,
                label='metadata function mean ± std', color='#d62728', alpha=0.75, 
                edgecolor='#b2182b', linewidth=1.2)

rects2 = ax.bar(x + width/2, values_hash, width, yerr=std_hash, error_kw=error_config,
                label='hash function (mmds not enabled) mean ± std', color='#1f77b4', alpha=0.75, 
                edgecolor='#2166ac', linewidth=1.2)

# Value annotations centered over bars
def autolabel(rects, std_values):
    for idx, rect in enumerate(rects):
        height = rect.get_height()
        std_val = std_values[idx]
        # Places label slightly higher than the top whisker bracket point to prevent text clipping
        ax.annotate(f'{height:.1f}µs',
                    xy=(rect.get_x() + rect.get_width() / 2, height + std_val),
                    xytext=(0, 4),  
                    textcoords='offset points',
                    ha='center', va='bottom', fontsize=8, fontweight='bold', alpha=0.85)

autolabel(rects1, std_mmds)
autolabel(rects2, std_hash)

# --- GRAPH LAYOUT ADJUSTMENTS ---
ax.set_xticks(x)
# Rotated to 20 degrees with right alignment to cleanly fit all 9 labels
ax.set_xticklabels(labels, rotation=20, ha='right', fontweight='bold')
ax.set_ylabel('Latency (microseconds, µs)', fontweight='bold')

# Standardized legibility legend box configuration
ax.legend(loc='upper right', frameon=True)

# Extend the Y-axis upper limit slightly to leave comfortable space for the value labels above the whiskers
ax.set_ylim(0, max(max(values_mmds) + max(std_mmds), max(values_hash) + max(std_hash)) * 1.15)

plt.tight_layout()
output_pdf = 'experiment4_comprehensive_error_bars.pdf'
plt.savefig(output_pdf, dpi=300)
print(f"Success! Whisker-style vector chart with all 9 metrics written to: {output_pdf}")
