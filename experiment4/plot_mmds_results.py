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
    'xtick.labelsize': 10,
    'ytick.labelsize': 9,
})

csv_file = 'mmds_microbenchmarks.csv'
if not os.path.exists(csv_file):
    print(f"Error: {csv_file} missing. Please execute your automated test loop first.")
    exit(1)

df = pd.read_csv(csv_file)

# Drops the warmup row dynamically if still present in the file
means = df[df['iteration'] > 1].mean()

# --- READ EXACT FLOAT VALUES ---
pci_total   = float(means['pci_total_us'])
pci_trans   = float(means['pci_transport_us'])
net_state   = float(means['net_state_us'])

rx_limiter  = float(means['rx_rate_limiter_us'])
tx_limiter  = float(means['tx_rate_limiter_us'])
mmds_core   = float(means['mmds_routing_us'])
b_queues    = float(means['build_queues_us'])
buf_reset   = float(means['buffer_reset_us'])
reapply_act = float(means['reapply_activation_us'])

# Calculate residual setup noise safely
sum_inner_measured = rx_limiter + tx_limiter + mmds_core + b_queues + buf_reset + reapply_act
net_state_residual = max(0.0, net_state - sum_inner_measured)

fig, ax = plt.subplots(figsize=(8.5, 6.5))
x_positions = [0, 0.7]
bar_width = 0.4

# -----------------------------------------------------------------------------
# BAR 1: MACRO PCI DEVICE INFRASTRUCTURE (Cool-Toned Theme)
# -----------------------------------------------------------------------------
# Distinct deep slate blue for transport and muted ice-blue for total net state
ax.bar(x_positions[0], [pci_trans], width=bar_width, label='PCI Transport Layer', color='#1D3557', edgecolor='black', linewidth=0.7)
ax.bar(x_positions[0], [net_state], bottom=[pci_trans], width=bar_width, label='virtio-net backend', color='#A8DADC', edgecolor='black', linewidth=0.7)

ax.annotate(f'Total Device Reset:\n{pci_total:.2f} µs', xy=(x_positions[0], pci_total), 
            xytext=(0, 8), textcoords="offset points", ha='center', fontweight='bold', fontsize=9.5)

# -----------------------------------------------------------------------------
# BAR 2: MICRO COMPONENTS ZOOM-IN (Warm/Vibrant Theme - No Color Collisions)
# -----------------------------------------------------------------------------
micro_components = [rx_limiter, tx_limiter, mmds_core, b_queues, buf_reset, reapply_act, net_state_residual]
micro_labels = [
    'RX Rate Limiter', 
    'TX Rate Limiter', 
    'MMDS Network Stack', 
    'Queue States Rebuild', 
    'Buffer Resets', 
    'Activation State', 
    'Misc'
]

# Fully unique palette ensuring complete visual separation from the Bar 1 blues
micro_colors = [
    '#E63946',  # RX Limiter: Vibrant Red
    '#F4A261',  # TX Limiter: Sandy Orange
    '#E9C46A',  # MMDS Core: Warm Yellow
    '#2A9D8F',  # Queue Rebuild: Teal Green
    '#9B5DE5',  # Kernel Buffer: Deep Purple
    '#F15BB5',  # Activation Framework: Bright Magenta
    '#D3D3D3'   # Setup Remainder: Light Neutral Gray
]

current_bottom = 0.0
for val, lbl, col in zip(micro_components, micro_labels, micro_colors):
    # Plot the structural chunk slice
    ax.bar(x_positions[1], [val], bottom=[current_bottom], width=bar_width, label=lbl, color=col, edgecolor='black', linewidth=0.7)
    
    # Compute the precise vertical center point coordinates of this slice
    slice_center_y = current_bottom + (val / 2.0)
    
    # CONDITIONAL ANNOTATION RULES FOR TEXT OR ARROWS
    if val >= 8.0:
        ax.annotate(f'{val:.2f} µs', xy=(x_positions[1], slice_center_y), 
                    ha='center', va='center', color='black', fontsize=8.5, fontweight='bold')
    else:
        ax.annotate(f'{val:.2f} µs', 
                    xy=(x_positions[1] + (bar_width / 2.0), slice_center_y),  
                    xytext=(x_positions[1] + 0.45, slice_center_y),           
                    arrowprops=dict(
                        arrowstyle="-|>", 
                        connectionstyle="arc3,rad=0", 
                        color='black', 
                        linewidth=0.8,
                        mutation_scale=10
                    ),
                    va='center', ha='left', color='black', fontsize=8.5, fontweight='bold')
        
    current_bottom += val

# Print sub-total above column 2
ax.annotate(f'Net State Zoom:\n{net_state:.2f} µs', xy=(x_positions[1], net_state), 
            xytext=(0, 8), textcoords="offset points", ha='center', fontweight='bold', fontsize=9.5)

# --- GRAPH LAYOUT ADJUSTMENTS ---
ax.set_xticks(x_positions)
ax.set_xticklabels(['Device Level Mapping\n(Macro Log)', 'Net State Components\n(Micro Zoom)'], fontweight='bold')
ax.set_ylabel('Execution Latency (microseconds, µs)', fontweight='bold')
ax.set_title('Average virtio-net latency breakdown for metadata function', fontweight='bold', pad=25)
ax.set_xlim(-0.4, 1.4) 

# Clean deduplicated legends frame mapping
handles, labels = ax.get_legend_handles_labels()
unique_labels = dict(zip(labels, handles))
ax.legend(unique_labels.values(), unique_labels.keys(), bbox_to_anchor=(1.02, 1), loc='upper left', frameon=True)

plt.tight_layout()
output_pdf = 'mmds_hierarchical_micro_breakdown.pdf'
plt.savefig(output_pdf, dpi=300, bbox_inches='tight')
print(f"Success! Generated wide-format chart with completely safe palette mapping at: {output_pdf}")
