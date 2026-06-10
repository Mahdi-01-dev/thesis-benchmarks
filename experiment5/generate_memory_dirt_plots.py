#!/usr/bin/env python3
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg') # Force non-interactive backend to prevent graphics segfaults
import matplotlib.pyplot as plt
import numpy as np

# 1. Load the experiment results CSV
csv_file = "memory_dirt_results.csv"
if not os.path.exists(csv_file):
    print(f"Error: {csv_file} not found. Please run the script in the same directory as the CSV.")
    exit(1)

df = pd.read_csv(csv_file)

# 2. Filter data to strictly ensure we only use measured iterations (2 to 6)
df_filtered = df[df['iteration'].between(2, 6)]

# 3. Aggregate data by payload size (dirty_mb) to calculate means and standard deviations
grouped = df_filtered.groupby('dirty_mb').agg(
    reset_mean=('reset_total', 'mean'),
    reset_std=('reset_total', 'std'),
    pci_mean=('pci_total_us', 'mean'),
    pci_std=('pci_total_us', 'std'),
    guest_mean=('guest_function_us', 'mean'),
    guest_std=('guest_function_us', 'std')
).reset_index()

# Convert metrics to consistent, readable units
# FIXED: Changed grouped['guest_function_us'] to grouped['guest_mean']
grouped['reset_mean_ms'] = grouped['reset_mean'] / 1000
grouped['reset_std_ms'] = grouped['reset_std'] / 1000
grouped['guest_mean_ms'] = grouped['guest_mean'] / 1000
grouped['guest_std_ms'] = grouped['guest_std'] / 1000

# Set up position configurations for categorical grouping
payload_labels = [f"{int(x)} MB" for x in grouped['dirty_mb']]
x_indexes = np.arange(len(payload_labels))


# =============================================================================
# --- GENERATE PDF 1: Macro Focus (VMM Reset Total vs Guest Function) ---
# =============================================================================
fig1, ax1 = plt.subplots(figsize=(10, 5.5))

color_reset = '#1f77b4' # Sharp Royal Blue
ax1.set_xlabel('Guest Dirtied Memory Payload Size', labelpad=12, fontweight='bold')
ax1.set_ylabel('Total Reset Latency (ms)', color=color_reset, fontweight='bold')
line1 = ax1.errorbar(
    x_indexes, grouped['reset_mean_ms'], yerr=grouped['reset_std_ms'],
    fmt='-o', color=color_reset, linewidth=2.5, elinewidth=1.5, capsize=4,
    label='Reset Latency'
)
ax1.tick_params(axis='y', labelcolor=color_reset)
ax1.grid(True, linestyle='--', alpha=0.5)

# Instantiating the second y-axis sharing the same x-axis framework
ax2 = ax1.twinx()
color_guest = '#ff7f0e' # Energetic Safety Orange
ax2.set_ylabel('Guest Execution Latency (ms)', color=color_guest, fontweight='bold')
line2 = ax2.errorbar(
    x_indexes, grouped['guest_mean_ms'], yerr=grouped['guest_std_ms'],
    fmt='-s', color=color_guest, linewidth=2.5, elinewidth=1.5, capsize=4,
    label='Guest Function Benchmark Execution'
)
ax2.tick_params(axis='y', labelcolor=color_guest)

# Combine handles to construct a clear unified legend box layout
lines = [line1, line2]
labels = [l.get_label() for l in lines]

# FIXED: Placed at 'upper center' to clear vertical workspace and prevent whisker masking
ax1.legend(lines, labels, loc='upper center', frameon=True, facecolor='white', edgecolor='none')

plt.xticks(x_indexes, payload_labels)
ax1.set_title('Total Reset Latency and Http-Fetch Execution Duration vs. Payload Size', fontsize=12, pad=12, fontweight='bold')

plt.tight_layout()
output_pdf1 = 'memory_dirt_macro_focus.pdf'
plt.savefig(output_pdf1, dpi=300)
plt.close(fig1)
print(f"Success! Macro graph generated cleanly at: {output_pdf1}")


# =============================================================================
# --- GENERATE PDF 2: Micro Focus (PCI Net Reset Latency) ---
# =============================================================================
fig2, ax3 = plt.subplots(figsize=(10, 5.5))

color_pci = '#2ca02c' # Sharp Emerald Green
ax3.set_xlabel('Payload Size', labelpad=12, fontweight='bold')
ax3.set_ylabel('Latency (µs)', color=color_pci, fontweight='bold')

line3 = ax3.errorbar(
    x_indexes, grouped['pci_mean'], yerr=grouped['pci_std'],
    fmt='-^', color=color_pci, linewidth=2.5, elinewidth=1.5, capsize=4,
    label='PCI Net Reset Latency'
)
ax3.tick_params(axis='y', labelcolor=color_pci)
ax3.grid(True, linestyle='--', alpha=0.5)

# FIXED: Scaled lower boundary multiplier to 0.7 to completely capture the 4MB lower whisker
ax3.set_ylim(min(grouped['pci_mean']) * 0.7, max(grouped['pci_mean']) * 1.2)
ax3.legend(loc='upper left', frameon=True, facecolor='white', edgecolor='none')
ax3.set_title('PCI Net Reset Latency vs. Payload Size', fontsize=12, pad=12, fontweight='bold')

plt.xticks(x_indexes, payload_labels)

plt.tight_layout()
output_pdf2 = 'memory_dirt_micro_focus.pdf'
plt.savefig(output_pdf2, dpi=300)
plt.close(fig2)
print(f"Success! Micro graph generated cleanly at: {output_pdf2}")
