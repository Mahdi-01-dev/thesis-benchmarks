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
    print(f"Error: {csv_file} missing. Please execute the updated shell test loop.")
    exit(1)

df = pd.read_csv(csv_file)
# Filter out the initial warm-up execution run cleanly
means = df[df['iteration'] > 1].mean()

# --- FLOAT VALUES PARSED NATIVELY BY PANDAS ---
pci_total   = float(means['pci_total_us'])
pci_trans   = float(means['pci_transport_us'])
net_state   = float(means['net_state_us'])

rx_limiter  = float(means['rx_rate_limiter_us'])
tx_limiter  = float(means['tx_rate_limiter_us'])
mmds_core   = float(means['mmds_routing_us'])
b_queues    = float(means['build_queues_us'])
buf_reset   = float(means['buffer_reset_us'])
reapply_act = float(means['reapply_activation_us'])

# Calculate any residual setup or teardown noise safely as a floating-point delta
sum_inner_measured = rx_limiter + tx_limiter + mmds_core + b_queues + buf_reset + reapply_act
net_state_residual = max(0.0, net_state - sum_inner_measured)

fig, ax = plt.subplots(figsize=(7.8, 6.5))
x_positions = [0, 0.7]
bar_width = 0.4

# -----------------------------------------------------------------------------
# BAR 1: MACRO PCI DEVICE INFRASTRUCTURE
# -----------------------------------------------------------------------------
ax.bar(x_positions[0], [pci_trans], width=bar_width, label='PCI Transport Layer', color='#4EA8DE', edgecolor='black', linewidth=0.7)
ax.bar(x_positions[0], [net_state], bottom=[pci_trans], width=bar_width, label='VirtIO Net State Scope (Total)', color='#B5E2FA', edgecolor='black', linewidth=0.7)

# Print high-res float above column 1
ax.annotate(f'Total Device Sync:\n{pci_total:.2f} µs', xy=(x_positions[0], pci_total), 
            xytext=(0, 8), textcoords="offset points", ha='center', fontweight='bold', fontsize=9.5)

# -----------------------------------------------------------------------------
# BAR 2: MICRO VIRTIO COMPONENTS HIERARCHICAL ZOOM
# -----------------------------------------------------------------------------
micro_components = [rx_limiter, tx_limiter, mmds_core, b_queues, buf_reset, reapply_act, net_state_residual]
micro_labels = ['RX Rate Limiter', 'TX Rate Limiter', 'MMDS Core Binding', 'Queue Descriptor Rebuild', 'Kernel Buffer Reset (TAP)', 'Activation Framework', 'Setup/Cloning Remainder']
micro_colors = ['#4EA8DE', '#56CFE1', '#70E000', '#FFD166', '#FF9F1C', '#FF6B6B', '#CCCCCC']

current_bottom = 0.0
for val, lbl, col in zip(micro_components, micro_labels, micro_colors):
    ax.bar(x_positions[1], [val], bottom=[current_bottom], width=bar_width, label=lbl, color=col, edgecolor='black', linewidth=0.7)
    
    # Internal numeric string prints (formatted to 2 decimal points)
    if val > 5.0:
        ax.annotate(f'{val:.2f} µs', xy=(x_positions[1], current_bottom + (val / 2.0)), 
                    ha='center', va='center', color='black', fontsize=8.5, fontweight='bold')
    current_bottom += val

# Print high-res float sub-total above column 2
ax.annotate(f'Net State Zoom:\n{net_state:.2f} µs', xy=(x_positions[1], net_state), 
            xytext=(0, 8), textcoords="offset points", ha='center', fontweight='bold', fontsize=9.5)

# --- GRAPH LAYOUT ADJUSTMENTS ---
ax.set_xticks(x_positions)
ax.set_xticklabels(['Device Level Mapping\n(Macro Log)', 'Net State Components\n(Micro Zoom)'], fontweight='bold')
ax.set_ylabel('Execution Latency (microseconds, µs)', fontweight='bold')
ax.set_title('Hierarchical Network Infrastructure Reconciliation Performance', fontweight='bold', pad=25)
ax.set_xlim(-0.4, 1.1)

handles, labels = ax.get_legend_handles_labels()
unique_labels = dict(zip(labels, handles))
ax.legend(unique_labels.values(), unique_labels.keys(), bbox_to_anchor=(1.02, 1), loc='upper left', frameon=True)

plt.tight_layout()
output_pdf = 'mmds_hierarchical_micro_breakdown.pdf'
plt.savefig(output_pdf, dpi=300, bbox_inches='tight')
print(f"Success! Generated wide-format hierarchical vector chart with decimal points at: {output_pdf}")
