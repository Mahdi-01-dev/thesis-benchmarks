#!/usr/bin/env python3
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# Publication styling configuration
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 11,
    'xtick.labelsize': 10,
    'ytick.labelsize': 9,
})

csv_pci = 'pci_breakdown_microbenchmarks.csv'
if not os.path.exists(csv_pci):
    print(f"Error: Target file '{csv_pci}' not found.")
    exit(1)

# Load and isolate iterations 1 to 30
df_pci = pd.read_csv(csv_pci)
df_filtered = df_pci[df_pci['iteration'].between(1, 30)]

# Initialize a 1-row, 2-column subplot canvas
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5.5))

# ----------------------------------------------------
# SUBPLOT 1 (LEFT): MSI-X Subsystem Reset Latency
# ----------------------------------------------------
box1 = ax1.boxplot(df_filtered['msix_reset_us'], labels=['MSI-X Reset Latency'], 
                   patch_artist=True, widths=0.4, showmeans=True, meanline=True,
                   medianprops={'color': '#d62728', 'linewidth': 1.5},
                   meanprops={'color': '#1f77b4', 'linewidth': 1.5, 'linestyle': '--'},
                   flierprops={'marker': 'o', 'markerfacecolor': 'gray', 'markersize': 4, 'alpha': 0.5})

box1['boxes'][0].set_facecolor('#f9afae')
box1['boxes'][0].set_alpha(0.7)
box1['boxes'][0].set_edgecolor('#4d4d4d')

ax1.set_ylabel('Latency (microseconds, µs)', fontweight='bold')

# ----------------------------------------------------
# SUBPLOT 2 (RIGHT): PCI Configuration Space Latency
# ----------------------------------------------------
box2 = ax2.boxplot(df_filtered['config_us'], labels=['PCI Config Space latency'], 
                   patch_artist=True, widths=0.4, showmeans=True, meanline=True,
                   medianprops={'color': '#d62728', 'linewidth': 1.5},
                   meanprops={'color': '#1f77b4', 'linewidth': 1.5, 'linestyle': '--'},
                   flierprops={'marker': 'o', 'markerfacecolor': 'gray', 'markersize': 4, 'alpha': 0.5})

box2['boxes'][0].set_facecolor('#aec7e8')
box2['boxes'][0].set_alpha(0.7)
box2['boxes'][0].set_edgecolor('#4d4d4d')

ax2.set_ylabel('Latency Duration (microseconds, µs)', fontweight='bold')

# Shared Legend Setup across the panels
legend_elements = [
    Line2D([0], [0], color='#d62728', lw=1.5, label='Median Duration'),
    Line2D([0], [0], color='#1f77b4', lw=1.5, linestyle='--', label='Mean Duration')
]
ax2.legend(handles=legend_elements, loc='upper right', frameon=True)

plt.tight_layout(rect=[0, 0, 1, 0.92])

output_pdf = 'pci_transport_side_by_side.pdf'
plt.savefig(output_pdf, dpi=300)
print(f"Success: Side-by-side transport breakdown written cleanly to '{output_pdf}'")
