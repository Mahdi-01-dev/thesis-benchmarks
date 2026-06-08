#!/usr/bin/env bash

set -euo pipefail

# --- SOURCE ENVIRONMENT LAYOUT ---
if [[ -f "./init_vars.sh" ]]; then
    source ./init_vars.sh
else
    echo "Error: init_vars.sh not found in the current directory." >&2
    exit 1
fi

OUTPUT_CSV="reset_benchmarks.csv"
LOG_DIR="$HOME/firecracker_logs"
ITERATIONS=31 # 1 warm-up + 30 measured runs

# Target the hash function snapshot artifacts explicitly from init_vars.sh
SNAPSHOT_PATH="$SNAP_CLEAN"
MEM_PATH="$MEM_CLEAN"

echo "iteration,vmm_action_us,chameleon_handler_us,madvise_eviction_us,net_reset_us" > "$OUTPUT_CSV"

cleanup_env() {
    sudo pkill -9 -f "$(basename "$FC_BIN")" >/dev/null 2>&1 || true
    sudo pkill -9 -f "resetting-uffd-handler" >/dev/null 2>&1 || true
    sudo rm -f "$FC_SOCKET" "$UFFD_SOCKET"
    sleep 0.2
}

get_latest_logfile() {
    ls -t "$LOG_DIR"/firecracker-uffd-restore-*.log 2>/dev/null | head -n 1 || echo ""
}

parse_duration_to_us() {
    local raw_line="$1"
    if [[ -z "$raw_line" ]]; then echo "0"; return; fi
    
    if [[ "$raw_line" =~ ([0-9.]+)ms ]]; then
        bc <<< "${BASH_REMATCH[1]} * 1000 / 1"
    elif [[ "$raw_line" =~ ([0-9.]+)µs ]]; then
        bc <<< "${BASH_REMATCH[1]} / 1"
    else
        echo "0"
    fi
}

# Verify bc is installed
if ! command -v bc &> /dev/null; then
    echo "Error: 'bc' utility is missing. Please run: sudo pacman -S bc" >&2
    exit 1
fi

echo "=== Initializing Long-Lived Hash Function Process ==="
cleanup_env

# Start your custom binary with exact debug variables and environment preservation
sudo -E env RUST_BACKTRACE=1 "$FC_BIN" --api-sock "$FC_SOCKET" --enable-pci > /dev/null 2>&1 &
for _ in {1..30}; do [[ -S "$FC_SOCKET" ]] && break; sleep 0.1; done

# Hydrate the guest image
export API_SOCKET
START_UFFD_HANDLER=1 ./restore_vm_uffd.sh "$SNAPSHOT_PATH" "$MEM_PATH" "$UFFD_SOCKET" > /dev/null 2>&1
LOGFILE=$(get_latest_logfile)

echo "=== Starting Post-Workload Hot Reset Loop ==="

for ((i=1; i<=ITERATIONS; i++)); do
    echo "Processing Hot Reset Iteration $i/$ITERATIONS..."
    
    # 1. EXECUTE THE ACTUAL GUEST WORKLOAD
    # Hit the hash service root endpoint with a raw string payload to dirty memory pages
    curl -s -X POST http://172.16.0.2:8080 -d "Hello World" > /dev/null 2>&1 || true

    # 2. Halt the microVM orchestration engine
    sudo curl -s -X PATCH --unix-socket "$FC_SOCKET" 'http://localhost/vm' \
        -H 'Content-Type: application/json' \
        -d '{"state": "Paused"}' > /dev/null
    
    # 3. Fire custom reset mechanism to wipe out the dirty state using the explicit NOOP_DIFF
    sudo curl -s -X PUT --unix-socket "$FC_SOCKET" 'http://localhost/snapshot/reset' \
        -H 'Content-Type: application/json' \
        -d "{\"reset_socket_path\": \"$UFFD_SOCKET\", \"snapshot_path\": \"$SNAPSHOT_PATH\", \"mem_file_path\": \"$MEM_PATH\", \"diff_file_path\": \"$NOOP_DIFF\"}" > /dev/null
        
    # 4. Synchronize hardware networking state tables and wake up
    sudo ip neigh flush dev tap0 > /dev/null
    sudo curl -s -X PATCH --unix-socket "$FC_SOCKET" 'http://localhost/vm' \
        -H 'Content-Type: application/json' \
        -d '{"state": "Resumed"}' > /dev/null

    # 5. Harvest transaction latencies from your telemetry statements
    VMM_TOTAL_US=$(grep "'reset snapshot' VMM action took" "$LOGFILE" | tail -n 1 | grep -oP "took \K[0-9]+") || echo "0"
    
    RAW_HANDLER=$(grep "Time spent in handler:" "$LOGFILE" | tail -n 1 | grep -oP "handler: \K.*") || echo ""
    RAW_MADVISE=$(grep "Memory eviction via io_uring latency:" "$LOGFILE" | tail -n 1 | grep -oP "latency: \K.*") || echo ""
    RAW_NET=$(grep "Reset net devices latency:" "$LOGFILE" | tail -n 1 | grep -oP "latency: \K.*") || echo ""
    
    HANDLER_US=$(parse_duration_to_us "$RAW_HANDLER")
    MADVISE_US=$(parse_duration_to_us "$RAW_MADVISE")
    NET_US=$(parse_duration_to_us "$RAW_NET")

    echo "$i,$VMM_TOTAL_US,$HANDLER_US,$MADVISE_US,$NET_US" >> "$OUTPUT_CSV"
done

cleanup_env
echo "=== Hot Reset Evaluation Complete. Data written to $OUTPUT_CSV ==="
