#!/usr/bin/env python3
import os
import pandas as pd

# FIX THE SEGFAULT: Force Matplotlib to use the 'Agg' headless backend.
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import seaborn as sns

# Set academic plotting style matching the template strictly
sns.set_theme(style="whitegrid")
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'figure.titlesize': 15
})

# 1. Load Data
load_csv = 'load_benchmarks.csv'
reset_csv = 'reset_benchmarks.csv'

if not os.path.exists(load_csv) or not os.path.exists(reset_csv):
    print("Error: Ensure both 'load_benchmarks.csv' and 'reset_benchmarks.csv' exist.")
    exit(1)

df_load = pd.read_csv(load_csv)
df_reset = pd.read_csv(reset_csv)

# 2. Filter out the warm-up iteration (Iteration 1)
df_load_filtered = df_load[df_load['iteration'] > 1]
df_reset_filtered = df_reset[df_reset['iteration'] > 1]

# 3. Compute Averages (Normalized to Milliseconds)
mean_total_load_ms = df_load_filtered['total_load_us'].mean() / 1000.0
mean_initial_net_ms = df_load_filtered['initial_net_restore_us'].mean() / 1000.0
mean_vmm_core_load_ms = mean_total_load_ms - mean_initial_net_ms

mean_total_reset_ms = df_reset_filtered['vmm_action_us'].mean() / 1000.0
mean_handler_ms = df_reset_filtered['chameleon_handler_us'].mean() / 1000.0
mean_madvise_ms = df_reset_filtered['madvise_eviction_us'].mean() / 1000.0
mean_net_reset_ms = df_reset_filtered['net_reset_us'].mean() / 1000.0

# Calculate Residual VMM Overhead for Reset
mean_residual_ms = mean_total_reset_ms - (mean_handler_ms + mean_madvise_ms + mean_net_reset_ms)
if mean_residual_ms < 0:
    mean_residual_ms = 0.0

# Reset Core/Memory Base represents everything except the Net Device Reset layer
mean_vmm_core_reset_ms = mean_total_reset_ms - mean_net_reset_ms


# =============================================================================
# --- GENERATE PDF 1: Load vs. Reset Comparison ---
# =============================================================================
fig1, ax1 = plt.subplots(figsize=(6.5, 5.5)) # Custom independent bounding block size
bar_width = 0.55

# Bar 1: Full Load Split
ax1.bar(['Average Snapshot Load'], [mean_vmm_core_load_ms], 
        color='#4A90E2', label='Non-net latency', width=bar_width, edgecolor='black', linewidth=0.7)
ax1.bar(['Average Snapshot Load'], [mean_initial_net_ms], 
        bottom=[mean_vmm_core_load_ms], color='#1F4E79', label='PCI Net Construction', width=bar_width, edgecolor='black', linewidth=0.7)

# Bar 2: Custom Reset Split 
ax1.bar(['Average Snapshot Reset'], [mean_vmm_core_reset_ms], 
        color='#E2844A', label='Non-net latency', width=bar_width, edgecolor='black', linewidth=0.7)
ax1.bar(['Average Snapshot Reset'], [mean_net_reset_ms], 
        bottom=[mean_vmm_core_reset_ms], color='#FFD166', label='Reset PCI Net Latency', width=bar_width, edgecolor='black', linewidth=0.7)

ax1.set_ylabel('Latency (milliseconds)', fontweight='bold')

ax1.legend(bbox_to_anchor=(1.02, 1), loc='upper left', frameon=True)

# Floating metadata annotations over the macro columns
ax1.annotate(f'Total:\n{mean_total_load_ms:.2f} ms', xy=(0, mean_total_load_ms), xytext=(0, 6), textcoords="offset points", ha='center', fontweight='bold', fontsize=10)
ax1.annotate(f'Total:\n{mean_total_reset_ms:.2f} ms', xy=(1, mean_total_reset_ms), xytext=(0, 6), textcoords="offset points", ha='center', fontweight='bold', fontsize=10)

# Inner vertical slice text annotation
ax1.annotate(f'{mean_initial_net_ms:.2f} ms', 
             xy=(0, mean_vmm_core_load_ms + (mean_initial_net_ms / 2.0)), 
             ha='center', va='center', color='white', fontweight='bold', fontsize=9.5)

plt.tight_layout()
output_macro = 'load_vs_reset_comparison.pdf'
plt.savefig(output_macro, dpi=300, bbox_inches='tight')
plt.close(fig1)
print(f"Success! Macro comparison plot generated cleanly at: {output_macro}")


# =============================================================================
# --- GENERATE PDF 2: Reset Path Latency Breakdown ---
# =============================================================================
fig2, ax2 = plt.subplots(figsize=(6.5, 5.5))

components = ['Chameleon UFFD Handler', 'Memory Eviction (madvise)', 'PCI Net Reset', 'Remaining Latency']
data_stack = [mean_handler_ms, mean_madvise_ms, mean_net_reset_ms, mean_residual_ms]
colors2 = ['#50C878', '#FF6B6B', '#FFD166', '#9B5DE5']

bottom_offset = 0.0
for comp, val, col in zip(components, data_stack, colors2):
    ax2.bar(['Reset Breakdown'], [val], bottom=[bottom_offset], color=col, label=comp, width=0.45, edgecolor='black', linewidth=0.7)
    
    # Internal text annotation configuration 
    if val > (mean_total_reset_ms * 0.08):
        ax2.annotate(f'{val*1000:.0f} µs',
                     xy=('Reset Breakdown', bottom_offset + (val / 2.0)),
                     ha='center', va='center', color='black', fontsize=9, fontweight='bold')
    else:
        # Crisp black arrow pointer callout for microsecond slices
        ax2.annotate(f'{comp}: {val*1000:.0f} µs',
                     xy=('Reset Breakdown', bottom_offset + (val / 2.0)),
                     xytext=(0.35, bottom_offset + (val / 2.0) + 0.3),
                     arrowprops=dict(facecolor='black', edgecolor='black', arrowstyle='->', connectionstyle='arc3,rad=0.08'),
                     va='center', fontsize=9.5, fontweight='bold')
                     
    bottom_offset += val

ax2.set_ylabel('Latency (milliseconds)', fontweight='bold')

# Shadowless layout alignment logic
ax2.legend(bbox_to_anchor=(1.02, 1), loc='upper left', frameon=True, shadow=False)

plt.tight_layout()
output_breakdown = 'reset_path_latency_breakdown.pdf'
plt.savefig(output_breakdown, dpi=300, bbox_inches='tight')
plt.close(fig2)
print(f"Success! Micro breakdown plot generated cleanly at: {output_breakdown}")
