#!/usr/bin/env bash

set -euo pipefail

# --- SOURCE ENVIRONMENT LAYOUT ---
if [[ -f "./init_vars.sh" ]]; then
    source ./init_vars.sh
else
    echo "Error: init_vars.sh not found in the current directory." >&2
    exit 1
fi

OUTPUT_CSV="pci_breakdown_microbenchmarks.csv"
LOG_DIR="$HOME/firecracker_logs"
ITERATIONS=31 # 1 warmup + 15 measured runs

SNAPSHOT_PATH="$SNAP_CLEAN"
MEM_PATH="$MEM_CLEAN"
DIFF_PATH="$NOOP_DIFF"

echo "iteration,reset_total_us,pci_total_us,pci_transport_us,net_state_us,msix_reset_us,config_us,msix_disable_us,msix_update_us" > "$OUTPUT_CSV"

cleanup_env() {
    echo "Performing precise environment sanitation..."
    
    # Force remove physical socket files first
    sudo rm -f /tmp/firecracker.socket /tmp/chameleon-uffd.sock /tmp/chameleon-uffd-handler.pid
    sudo rm -f "$FC_SOCKET" "$UFFD_SOCKET" >/dev/null 2>&1 || true

    # Safe process elimination (kills by exact binary name, never matches this script)
    sudo killall -9 "my_firecracker_detailed" >/dev/null 2>&1 || true
    sudo killall -9 "resetting-uffd-handler" >/dev/null 2>&1 || true
    
    sleep 0.3
    return 0
}

get_latest_logfile() {
    ls -t "$LOG_DIR"/firecracker-uffd-restore-*.log 2>/dev/null | head -n 1 || echo ""
}

parse_duration_to_us() {
    local raw_val="$1"
    if [[ -z "$raw_val" ]]; then echo "0.000"; return; fi
    
    # Clean brackets and generic text strings if wrapped
    raw_val=$(echo "$raw_val" | tr -d '[:space:]')
    
    if [[ "$raw_val" == *ms ]]; then
        bc <<< "scale=3; ${raw_val%ms} * 1000"
    elif [[ "$raw_val" == *µs ]]; then
        bc <<< "scale=3; ${raw_val%µs} / 1"
    else
        bc <<< "scale=3; $raw_val / 1"
    fi
}

echo "=== Starting Experiment 4: MMDS In-Place State Mutation Loop ==="
cleanup_env

# Start Firecracker headlessly
sudo -E env RUST_BACKTRACE=1 "$FC_BIN" --api-sock "$FC_SOCKET" --enable-pci > /dev/null 2>&1 &
for _ in {1..30}; do [[ -S "$FC_SOCKET" ]] && break; sleep 0.1; done

# Hydrate using original restore script since MMDS configuration is frozen inside snapshot
START_UFFD_HANDLER=1 ./restore_vm_uffd.sh "$SNAPSHOT_PATH" "$MEM_PATH" "$UFFD_SOCKET" > /dev/null 2>&1
LOGFILE=$(get_latest_logfile)

for ((i=0; i<ITERATIONS; i++)); do 
    echo "Processing Step $i/$ITERATIONS..."

    curl -s -X POST http://172.16.0.2:8080/ -H "Content-Type: text/plain" -d "control_group_baseline_string" > /dev/null

    # 3. Halt microVM engine
    sudo curl -s -X PATCH --unix-socket "$FC_SOCKET" 'http://localhost/vm' \
        -H 'Content-Type: application/json' \
        -d '{"state": "Paused"}' > /dev/null
    
    # 4. Apply Chameleon In-Place Memory Reset
    sudo curl -s -X PUT --unix-socket "$FC_SOCKET" 'http://localhost/snapshot/reset' \
        -H 'Content-Type: application/json' \
        -d "{\"reset_socket_path\": \"$UFFD_SOCKET\", \"snapshot_path\": \"$SNAPSHOT_PATH\", \"mem_file_path\": \"$MEM_PATH\", \"diff_file_path\": \"$DIFF_PATH\"}" > /dev/null
        
    # 6. Sync hardware device layers and resume execution
    sudo ip neigh flush dev tap0 > /dev/null
    sudo curl -s -X PATCH --unix-socket "$FC_SOCKET" 'http://localhost/vm' \
        -H 'Content-Type: application/json' \
        -d '{"state": "Resumed"}' > /dev/null

    if (( i == 0 )); then
        continue
    fi

    # 8. Harvest data metrics
    VMM_ACTION_LINE=$(grep "'reset snapshot' VMM action took" "$LOGFILE" | tail -n 1) || ""
    LAST_PCI_LINE=$(grep "Reset PCI net device latency breakdown:" "$LOGFILE" | tail -n 1) || ""
    LAST_TRANS_LINE=$(grep "Reset PCI transport state latency breakdown:" "$LOGFILE" | tail -n 1) || ""
    LAST_MSIX_LINE=$(grep "Reset MSI-X breakdown:" "$LOGFILE" | tail -n 1) || ""

    RESET_TOTAL_RAW=$(echo "$VMM_ACTION_LINE" | grep -oP "took \K[0-9.]+(?= us)") || echo "0"
    RESET_TOTAL_US=$(parse_duration_to_us "${RESET_TOTAL_RAW}")

    PCI_TOTAL=$(echo "$LAST_PCI_LINE" | grep -oP "total=\K[0-9.]+(µs|ms)") || echo "0"
    PCI_TOTAL_US=$(parse_duration_to_us "$PCI_TOTAL")

    PCI_TRANS=$(echo "$LAST_PCI_LINE" | grep -oP "transport=\K[0-9.]+(µs|ms)") || echo "0"
    PCI_TRANS_US=$(parse_duration_to_us "$PCI_TRANS")

    NET_STATE=$(echo "$LAST_PCI_LINE" | grep -oP "net state=\K[0-9.]+(µs|ms)") || echo "0"
    NET_STATE_US=$(parse_duration_to_us "$NET_STATE")

    MSIX_RESET=$(echo "$LAST_TRANS_LINE" | grep -oP "msix_reset_latency=\K[0-9.]+(µs|ms)") || echo "0"
    MSIX_RESET_US=$(parse_duration_to_us "$MSIX_RESET")

    CONFIG_LAT=$(echo "$LAST_TRANS_LINE" | grep -oP "config_latency=\K[0-9.]+(µs|ms)") || echo "0"
    CONFIG_LAT_US=$(parse_duration_to_us "$CONFIG_LAT")

    MSIX_DISABLE=$(echo "$LAST_MSIX_LINE" | grep -oP "disable=\K[0-9.]+(µs|ms)") || echo "0"
    MSIX_DISABLE_US=$(parse_duration_to_us "$MSIX_DISABLE")

    MSIX_UPDATE=$(echo "$LAST_MSIX_LINE" | grep -oP "update=\K[0-9.]+(µs|ms)") || echo "0"
    MSIX_UPDATE_US=$(parse_duration_to_us "$MSIX_UPDATE")

    echo "$i,$RESET_TOTAL_US,$PCI_TOTAL_US,$PCI_TRANS_US,$NET_STATE_US,$MSIX_RESET_US,$CONFIG_LAT_US,$MSIX_DISABLE_US,$MSIX_UPDATE_US" >> "$OUTPUT_CSV"
done

cleanup_env
echo "=== Experiment 4 Complete. Performance data logged to $OUTPUT_CSV ==="
