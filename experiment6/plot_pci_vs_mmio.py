#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Publication styling configuration
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 9,
})

csv_pci = 'pci_breakdown_microbenchmarks.csv'
csv_mmio = 'mmio_breakdown_microbenchmarks.csv'

if not os.path.exists(csv_pci) or not os.path.exists(csv_mmio):
    print(f"Error: Required source files ('{csv_pci}' and '{csv_mmio}') must exist in the same directory.")
    exit(1)

# Load and isolate measured iterations (1 to 30)
df_pci = pd.read_csv(csv_pci)
df_mmio = pd.read_csv(csv_mmio)
df_pci_filtered = df_pci[df_pci['iteration'].between(1, 30)]
df_mmio_filtered = df_mmio[df_mmio['iteration'].between(1, 30)]

# Compute averages
means_pci = df_pci_filtered.mean()
means_mmio = df_mmio_filtered.mean()

# Align side-by-side metric tracking arrays
labels = ['Total Reset Time', 'Total Net Reset', 'Transport Reset Latency', 'Net State Reset']
pci_vals = [means_pci['reset_total_us'], means_pci['pci_total_us'], means_pci['pci_transport_us'], means_pci['net_state_us']]
mmio_vals = [means_mmio['reset_total_us'], means_mmio['mmio_total_us'], means_mmio['mmio_transport_us'], means_mmio['mmio_net_state_us']]

fig, ax = plt.subplots(figsize=(11, 6.5))
x = np.arange(len(labels))
width = 0.35

# Render clean baseline structural means without scatter overlays
rects_pci = ax.bar(x - width/2, pci_vals, width, label='PCI', color='#d62728', alpha=0.8, edgecolor='#d62728', linewidth=1.2)
rects_mmio = ax.bar(x + width/2, mmio_vals, width, label='MMIO', color='#1f77b4', alpha=0.8, edgecolor='#1f77b4', linewidth=1.2)

# Value annotations over bar charts
def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height:.1f}µs',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 4), textcoords="offset points",
                    ha='center', va='bottom', fontsize=8.5, fontweight='bold', alpha=0.85)

autolabel(rects_pci)
autolabel(rects_mmio)

# Axis framing
ax.set_xticks(x)
ax.set_xticklabels(labels, fontweight='bold')
ax.set_ylabel('Latency (microseconds, µs)', fontweight='bold')
ax.legend(loc='upper right', frameon=True)

plt.tight_layout()
plt.savefig('pci_vs_mmio_comparison.pdf', dpi=300)
print("Success: 'pci_vs_mmio_comparison.pdf' generated cleanly without scatter overlays.")
