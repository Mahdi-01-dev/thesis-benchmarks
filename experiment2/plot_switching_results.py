#!/usr/bin/env python3
import os
import pandas as pd

# Headless backend prevents interactive window engine core dumps on Arch Linux
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import seaborn as sns

# Set academic plotting style
sns.set_theme(style="whitegrid")
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'xtick.labelsize': 11,
    'ytick.labelsize': 10,
})

csv_file = 'switching_benchmarks.csv'
if not os.path.exists(csv_file):
    print(f"Error: {csv_file} missing.")
    exit(1)

df = pd.read_csv(csv_file)
# Filter out the 1st warm-up run pair (Leaves exactly 15 measured runs)
df_filtered = df[df['iteration'] > 1]

# Compute category averages and convert from microseconds to milliseconds
means = df_filtered.groupby('transition_type').mean() / 1000.0

# Wide aspect ratio canvas setup
fig, ax = plt.subplots(figsize=(11, 6.5))

labels = ['Hash ──> JSON Workload', 'JSON ──> Hash Workload']
transitions = ['hash_to_json', 'json_to_hash']

# Extract individual component arrays
handlers = [means.loc['hash_to_json', 'chameleon_handler_us'], means.loc['json_to_hash', 'chameleon_handler_us']]
madvises = [means.loc['hash_to_json', 'madvise_eviction_us'], means.loc['json_to_hash', 'madvise_eviction_us']]
nets = [means.loc['hash_to_json', 'net_reset_us'], means.loc['json_to_hash', 'net_reset_us']]

# Calculate Residual VMM Overhead dynamically
residuals = []
for trans in transitions:
    tot = means.loc[trans, 'vmm_action_us']
    sub = means.loc[trans, 'chameleon_handler_us'] + means.loc[trans, 'madvise_eviction_us'] + means.loc[trans, 'net_reset_us']
    residuals.append(max(0.0, tot - sub))

total_latencies = [means.loc['hash_to_json', 'vmm_action_us'], means.loc['json_to_hash', 'vmm_action_us']]

# Render Stacked Columns
bar_width = 0.45
ax.bar(labels, handlers, label='Chameleon Handler', color='#50C878', width=bar_width, edgecolor='black', linewidth=0.7)
ax.bar(labels, madvises, bottom=handlers, label='Memory Eviction (madvise)', color='#FF6B6B', width=bar_width, edgecolor='black', linewidth=0.7)

stack_base_3 = [h + m for h, m in zip(handlers, madvises)]
ax.bar(labels, nets, bottom=stack_base_3, label='Net Device Reset', color='#FFD166', width=bar_width, edgecolor='black', linewidth=0.7)

stack_base_4 = [b + n for b, n in zip(stack_base_3, nets)]
ax.bar(labels, residuals, bottom=stack_base_4, label='Residual reset Overhead', color='#9B5DE5', width=bar_width, edgecolor='black', linewidth=0.7)

# --- PROFESSIONAL INTERNAL BAR & ARROW ANNOTATIONS ---
# Loop through both bars (0 = Hash->JSON, 1 = JSON->Hash)
for idx, trans in enumerate(transitions):
    components_ms = [handlers[idx], madvises[idx], nets[idx], residuals[idx]]
    component_names = ['Handler', 'madvise', 'Net Reset', 'Residual']
    
    # Track the cumulative bottom point matching the layout logic
    current_bottom = 0.0
    
    # Vertical offset tracking specifically to stack arrows cleanly if multiple thin layers exist
    arrow_y_offset = 0.0
    
    for val, name in zip(components_ms, component_names):
        # Convert value back to microseconds for clean, non-fractional sub-millisecond string representation
        val_us = val * 1000.0
        center_y = current_bottom + (val / 2.0)
        
        # Professional Threshold Rule:
        # If the segment takes up more than 8% of total height, print the microsecond summary inside the slice.
        if val > (total_latencies[idx] * 0.08):
            ax.annotate(f'{val_us:.0f} µs',
                         xy=(idx, center_y),
                         ha='center', va='center', color='black', fontsize=9.5, fontweight='bold')
        else:
            # Thin Slice Callout System: Throws a clean arrow pointing at the microsecond layout boundary
            # Dynamic text positioning pushes markers out smoothly
            text_x_pos = idx + 0.32
            text_y_pos = center_y + arrow_y_offset
            
            ax.annotate(f'{name}: {val_us:.0f} µs',
                         xy=(idx, center_y),
                         xytext=(text_x_pos, text_y_pos),
                         arrowprops=dict(facecolor='black', edgecolor='black', arrowstyle='->', connectionstyle='arc3,rad=0.05'),
                         va='center', ha='left', fontsize=9.5, fontweight='bold')
            # Increment the offset pointer slightly to prevent stacked labels from clipping each other
            arrow_y_offset += 0.4 
            
        current_bottom += val

# Append Macro Totals clearly on top of the columns
for idx, total in enumerate(total_latencies):
    ax.annotate(f'Total:\n{total:.2f} ms', xy=(idx, total), xytext=(0, 8), textcoords="offset points", ha='center', fontweight='bold', fontsize=11)

ax.set_ylabel('Latency (milliseconds)', fontweight='bold')
ax.set_title('Cross-Workload State Transition Reset Latencies', fontweight='bold', pad=20)

# Expand the right side limits slightly so pointer arrow text doesn't run into the legend bounding box
ax.set_xlim(-0.5, 1.8)

# Align legend safely to the exterior right window edge
ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', frameon=True)

plt.tight_layout()

output_pdf = 'switching_evaluation_breakdown.pdf'
plt.savefig(output_pdf, dpi=300, bbox_inches='tight')
print(f"Success! Generated wide-format switching vector chart at: {output_pdf}")
