#!/usr/bin/env bash

set -euo pipefail

# --- SOURCE ENVIRONMENT LAYOUT ---
if [[ -f "./init_vars.sh" ]]; then
    source ./init_vars.sh
else
    echo "Error: init_vars.sh not found in the current directory." >&2
    exit 1
fi

OUTPUT_CSV="mmio_breakdown_microbenchmarks.csv"
LOG_DIR="$HOME/firecracker_logs"
ITERATIONS=31 # 1 warmup + 15 measured runs

SNAPSHOT_PATH="$SNAP_CLEAN"
MEM_PATH="$MEM_CLEAN"
DIFF_PATH="$NOOP_DIFF"

echo "iteration,reset_total_us,mmio_total_us,mmio_transport_us,mmio_net_state_us" > "$OUTPUT_CSV"

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
    
    # Check for nanosecond markers and scale to microseconds accordingly
    if [[ "$raw_val" == *ns ]]; then
        bc <<< "scale=3; ${raw_val%ns} / 1000"
    elif [[ "$raw_val" == *ms ]]; then
        bc <<< "scale=3; ${raw_val%ms} * 1000"
    elif [[ "$raw_val" == *µs ]]; then
        bc <<< "scale=3; ${raw_val%µs} / 1"
    else
        bc <<< "scale=3; $raw_val / 1"
    fi
}

echo "=== Starting MMIO Core Architecture Breakdown Experiment ==="
cleanup_env

# Start Firecracker headlessly
sudo -E env RUST_BACKTRACE=1 "$FC_BIN" --api-sock "$FC_SOCKET" > /dev/null 2>&1 &
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
    LAST_MMIO_LINE=$(grep "Reset MMIO net device breakdown:" "$LOGFILE" | tail -n 1) || ""

    RESET_TOTAL_RAW=$(echo "$VMM_ACTION_LINE" | grep -oP "took \K[0-9.]+(?= us)") || echo "0"
    RESET_TOTAL_US=$(parse_duration_to_us "${RESET_TOTAL_RAW}")

    MMIO_TOTAL=$(echo "$LAST_MMIO_LINE" | grep -oP "total=\K[0-9.]+(µs|ms|ns)") || echo "0"
    MMIO_TOTAL_US=$(parse_duration_to_us "$MMIO_TOTAL")

    MMIO_TRANS=$(echo "$LAST_MMIO_LINE" | grep -oP "transport=\K[0-9.]+(µs|ms|ns)") || echo "0"
    MMIO_TRANS_US=$(parse_duration_to_us "$MMIO_TRANS")

    MMIO_NET_STATE=$(echo "$LAST_MMIO_LINE" | grep -oP "net state=\K[0-9.]+(µs|ms|ns)") || echo "0"
    MMIO_NET_STATE_US=$(parse_duration_to_us "$MMIO_NET_STATE")

    echo "$i,$RESET_TOTAL_US,$MMIO_TOTAL_US,$MMIO_TRANS_US,$MMIO_NET_STATE_US" >> "$OUTPUT_CSV"
done

cleanup_env
echo "=== MMIO Experiment Complete. Performance data logged to $OUTPUT_CSV ==="
