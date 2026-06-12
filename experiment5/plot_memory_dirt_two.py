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
#df_filtered = df[df['iteration'].between(2, 6)].copy()

# Explicitly ensure dirty_mb is treated as a sorted numeric type for flawless index matching
df['dirty_mb'] = pd.to_numeric(df['dirty_mb'])

# 3. Aggregate data by payload size (dirty_mb) to calculate means and standard deviations
grouped = df.groupby('dirty_mb').agg(
    reset_mean=('reset_total', 'mean'),
    reset_std=('reset_total', 'std'),
    pci_mean=('pci_total_us', 'mean'),
    pci_std=('pci_total_us', 'std'),
    guest_mean=('guest_function_us', 'mean'),
    guest_std=('guest_function_us', 'std')
).sort_index().reset_index() # Force rigid ascending numerical sort order

# Convert metrics to consistent, readable units
grouped['reset_mean_ms'] = grouped['reset_mean'] / 1000
grouped['reset_std_ms'] = grouped['reset_std'] / 1000
grouped['guest_mean_ms'] = grouped['guest_mean'] / 1000
grouped['guest_std_ms'] = grouped['guest_std'] / 1000

# Set up position configurations for categorical grouping
payload_sizes = grouped['dirty_mb'].tolist()
payload_labels = [f"{int(x)} MB" for x in payload_sizes]
x_indexes = np.arange(len(payload_labels))


# =============================================================================
# --- GENERATE PDF 1: Macro Focus (VMM Reset Total vs Guest Function) ---
# =============================================================================
fig1, ax1 = plt.subplots(figsize=(10, 5.5))

color_reset = '#1f77b4' # Sharp Royal Blue
ax1.set_xlabel('Guest Dirtied Memory Payload Size', labelpad=12, fontweight='bold')
ax1.set_ylabel('VMM In-Place Reset Latency (ms)', color=color_reset, fontweight='bold')
line1 = ax1.errorbar(
    x_indexes, grouped['reset_mean_ms'], yerr=grouped['reset_std_ms'],
    fmt='-o', color=color_reset, linewidth=2.5, elinewidth=1.5, capsize=4,
    label='VMM In-Place Reset Total', zorder=2
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
    label='Guest Function Benchmark Execution', zorder=2
)
ax2.tick_params(axis='y', labelcolor=color_guest)

# Combine handles to construct a clear unified legend box layout
lines = [line1, line2]
labels = [l.get_label() for l in lines]
ax1.legend(lines, labels, loc='upper center', frameon=True, facecolor='white', edgecolor='none')

plt.xticks(x_indexes, payload_labels)
ax1.set_title('Macro Focus: Memory Scaling vs. VMM Hot Reset Bounds', fontsize=12, pad=12, fontweight='bold')

plt.tight_layout()
output_pdf1 = 'memory_dirt_macro_focus_two.pdf'
plt.savefig(output_pdf1, dpi=300)
plt.close(fig1)
print(f"Success! Macro graph generated cleanly at: {output_pdf1}")


# =============================================================================
# --- GENERATE PDF 2: Micro Focus (PCI Net Reset Latency + Raw Samples) ---
# =============================================================================
fig2, ax3 = plt.subplots(figsize=(10, 5.5))

color_pci = '#2ca02c' # Sharp Emerald Green
ax3.set_xlabel('Guest Dirtied Memory Payload Size', labelpad=12, fontweight='bold')
ax3.set_ylabel('Latency (µs)', color=color_pci, fontweight='bold')

# Plot the core trend line and standard deviation whiskers
line3 = ax3.errorbar(
    x_indexes, grouped['pci_mean'], yerr=grouped['pci_std'],
    fmt='-^', color=color_pci, linewidth=2.5, elinewidth=1.5, capsize=5,
    label='Mean PCI Net Reset Latency', zorder=3
)

# OVERLAY ALL RAW DATA POINTS: Ensure no sample or outlier is masked or hidden
for idx, size in enumerate(payload_sizes):
    # Fetch all raw values (iterations 2-6) for this specific payload size
    raw_samples = df[df['dirty_mb'] == size]['pci_total_us'].values
    
    # Generate a tight horizontal jitter offset centered around the tick index to prevent overlapping dots
    aligned_x_positions = np.full(shape=len(raw_samples), fill_value=idx)

    # Plot the individual raw dots
    ax3.scatter(aligned_x_positions, raw_samples, color='#d62728', alpha=0.6, edgecolors='black', 
                linewidths=0.5, s=35, label='Raw Iteration Sample' if idx == 0 else "", zorder=4)

ax3.tick_params(axis='y', labelcolor=color_pci)
ax3.grid(True, linestyle='--', alpha=0.5)

# Dynamically set y bounds to cleanly fit the absolute lowest and highest raw data values found across the files
all_pci_values = df['pci_total_us'].values
ax3.set_ylim(min(all_pci_values) * 0.9, max(all_pci_values) * 1.1)

ax3.legend(loc='upper left', frameon=True, facecolor='white', edgecolor='none')
ax3.set_title('Micro Focus: PCI Net Reset Latency Breakdown (With Raw Samples Overlay)', fontsize=12, pad=12, fontweight='bold')

plt.xticks(x_indexes, payload_labels)

plt.tight_layout()
output_pdf2 = 'memory_dirt_micro_focus_two.pdf'
plt.savefig(output_pdf2, dpi=300)
plt.close(fig2)
print(f"Success! Micro graph with individual raw points overlay generated at: {output_pdf2}")
