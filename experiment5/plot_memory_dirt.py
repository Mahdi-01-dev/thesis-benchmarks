import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# 1. Load the experiment results CSV
csv_file = "memory_dirt_results.csv"
try:
    df = pd.read_csv(csv_file)
except FileNotFoundError:
    print(f"Error: {csv_file} not found. Please run the script in the same directory as the CSV.")
    exit(1)

# 2. Filter data to strictly ensure we only use measured iterations (2 to 6)
#df_filtered = df[df['iteration'].between(2, 6)]

# 3. Aggregate data by payload size (dirty_mb) to calculate means and standard deviations
grouped = df.groupby('dirty_mb').agg(
    reset_mean=('reset_total', 'mean'),
    reset_std=('reset_total', 'std'),
    pci_mean=('pci_total_us', 'mean'),
    pci_std=('pci_total_us', 'std'),
    guest_mean=('guest_function_us', 'mean'),
    guest_std=('guest_function_us', 'std')
).reset_index()

# Convert metrics to consistent, readable units
# reset_total and guest_function are in microseconds in our raw parse, mapping to milliseconds
grouped['reset_mean_ms'] = grouped['reset_mean'] / 1000
grouped['reset_std_ms'] = grouped['reset_std'] / 1000
grouped['guest_mean_ms'] = grouped['guest_mean'] / 1000
grouped['guest_std_ms'] = grouped['guest_std'] / 1000

# pci_total_us is already in microseconds, keep it in microseconds for microscopic resolution
grouped['pci_mean_us'] = grouped['pci_mean']
grouped['pci_std_us'] = grouped['pci_std']

# 4. Initialize a multi-panel subplot layout (2 Rows, 1 Column)
fig, (ax1, ax3) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
plt.rcParams.update({'font.size': 11, 'font.family': 'sans-serif'})

# Setup X-axis discrete categorical layout
x_indexes = np.arange(len(grouped['dirty_mb']))
payload_labels = [f"{int(mb)} MB" for mb in grouped['dirty_mb']]

# ----------------------------------------------------
# PANEL 1 (TOP): Global Macro VMM and Guest Performance
# ----------------------------------------------------
color_reset = '#1f77b4' # Clean Blue
ax1.set_ylabel('Reset Latency (ms)', color=color_reset, fontweight='bold')
line1 = ax1.errorbar(
    x_indexes, grouped['reset_mean_ms'], yerr=grouped['reset_std_ms'],
    fmt='-o', color=color_reset, linewidth=2, elinewidth=1.5, capsize=4,
    label='Total API Reset Latency'
)
ax1.tick_params(axis='y', labelcolor=color_reset)
ax1.grid(True, linestyle='--', alpha=0.3)
ax1.set_ylim(0, max(grouped['reset_mean_ms']) * 1.4)

# Overlay Guest Function Duration using a secondary right Y-axis on the top panel
ax2 = ax1.twinx()
color_guest = '#d62728' # Crimson Red
ax2.set_ylabel('Guest Execution (ms)', color=color_guest, fontweight='bold')
line2 = ax2.errorbar(
    x_indexes, grouped['guest_mean_ms'], yerr=grouped['guest_std_ms'],
    fmt='--s', color=color_guest, linewidth=2, elinewidth=1.5, capsize=4,
    label='Guest Active Execution'
)
ax2.tick_params(axis='y', labelcolor=color_guest)

# Build a unified legend box for the macro panel
lines_top = [line1, line2]
labels_top = [l.get_label() for l in lines_top]
ax1.legend(lines_top, labels_top, loc='upper left', frameon=True, facecolor='white', edgecolor='none')
ax1.set_title('Macro System Profiles (VMM Snapshot Reset vs. Active Guest Execution)', fontsize=11, pad=8, style='italic')

# ----------------------------------------------------
# PANEL 2 (BOTTOM): Micro Focus - Total Net PCI Reset Latency
# ----------------------------------------------------
color_pci = '#2ca02c' # Sharp Emerald Green
ax3.set_xlabel('Guest Dirtied Memory Payload Size', labelpad=12, fontweight='bold')
ax3.set_ylabel('Latency (µs)', color=color_pci, fontweight='bold')
line3 = ax3.errorbar(
    x_indexes, grouped['pci_mean_us'], yerr=grouped['pci_std_us'],
    fmt='-^', color=color_pci, linewidth=2.5, elinewidth=1.5, capsize=4,
)
ax3.tick_params(axis='y', labelcolor=color_pci)
ax3.grid(True, linestyle='--', alpha=0.5)

# Keep bounds focused closely on the microsecond variance boundaries
ax3.set_ylim(min(grouped['pci_mean_us']) * 0.8, max(grouped['pci_mean_us']) * 1.2)
ax3.legend(loc='upper left', frameon=True, facecolor='white', edgecolor='none')
ax3.set_title('Micro Focus: PCI Net Reset Latency', fontsize=11, pad=8, style='italic')

# Assign explicit categorical tick strings to the shared X axis
plt.xticks(x_indexes, payload_labels)

# Title & Structural formatting
plt.suptitle('Chameleon Performance Breakdown: Memory Scaling vs. Internal Latency Paths\nProving Decoupled Micro-Device State Management via Userfaultfd', 
             fontsize=13, fontweight='bold', alpha=0.9, y=0.96)

fig.tight_layout(rect=[0, 0, 1, 0.93])

# 5. Export and render
output_img = "experiment5_pci_focus_chart.png"
plt.savefig(output_img, dpi=300)
print(f"Success: Analysis visualization focusing on PCI latency saved cleanly to '{output_img}'")
plt.show()
