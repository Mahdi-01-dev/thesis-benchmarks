#!/usr/bin/env python3
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 11,
    'ytick.labelsize': 9,
})

csv_pci = 'pci_breakdown_microbenchmarks.csv'
if not os.path.exists(csv_pci):
    print(f"Error: Target file '{csv_pci}' not found.")
    exit(1)

df_pci = pd.read_csv(csv_pci)
df_filtered = df_pci[df_pci['iteration'].between(1, 30)]

# Isolate columns for MSI-X inner logic paths
msix_data = [
    df_filtered['msix_disable_us'],
    df_filtered['msix_update_us']
]
labels = ['Vector Disabling\n(disable() method call)', 'Vector Table Update']

fig, ax = plt.subplots(figsize=(8, 6))

# Construct specialized vertical boxplots
box = ax.boxplot(msix_data, labels=labels, patch_artist=True, widths=0.4,
                 showmeans=True, meanline=True,
                 medianprops={'color': '#b2182b', 'linewidth': 1.5},
                 meanprops={'color': '#2166ac', 'linewidth': 1.5, 'linestyle': '--'},
                 flierprops={'marker': 'd', 'markerfacecolor': 'gray', 'markersize': 4, 'alpha': 0.5})

# Custom box fill colors
colors = ['#ff9999', '#99ccff']
for patch, color in zip(box['boxes'], colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)
    patch.set_edgecolor('#4d4d4d')

ax.set_ylabel('Latency (microseconds, µs)', fontweight='bold')
ax.set_title('PCI MSI-X Reset Latency Breakdown', fontweight='bold', pad=20)

from matplotlib.lines import Line2D
legend_elements = [
    Line2D([0], [0], color='#b2182b', lw=1.5, label='Median Duration'),
    Line2D([0], [0], color='#2166ac', lw=1.5, linestyle='--', label='Mean Duration')
]
ax.legend(handles=legend_elements, loc='upper right', frameon=True)

plt.tight_layout()
plt.savefig('pci_msix_latency_breakdown.pdf', dpi=300)
print("Success: 'pci_msix_latency_breakdown.pdf' generated cleanly.")
