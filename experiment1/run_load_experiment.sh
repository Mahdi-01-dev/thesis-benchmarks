#!/usr/bin/env bash

set -euo pipefail

# --- SOURCE ENVIRONMENT LAYOUT ---
if [[ -f "./init_vars.sh" ]]; then
    source ./init_vars.sh
else
    echo "Error: init_vars.sh not found in the current directory." >&2
    exit 1
fi

OUTPUT_CSV="load_benchmarks.csv"
LOG_DIR="$HOME/firecracker_logs"
ITERATIONS=31 # 1 warm-up + 30 measured runs

# Target the hash function snapshot artifacts explicitly from init_vars.sh
SNAPSHOT_PATH="$SNAP_CLEAN"
MEM_PATH="$MEM_CLEAN"

echo "iteration,total_load_us,initial_net_restore_us" > "$OUTPUT_CSV"

cleanup_env() {
    sudo pkill -9 -f "$(basename "$FC_BIN")" || true
    sudo pkill -9 -f "resetting-uffd-handler" || true
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

echo "=== Starting Hash Snapshot Load Baseline Loop ==="

for ((i=1; i<=ITERATIONS; i++)); do
    echo "Processing Load Baseline Iteration $i/$ITERATIONS..."
    cleanup_env
    
    # Spawn firecracker detailed process using your exact runtime parameters
    sudo env RUST_BACKTRACE=1 "$FC_BIN" --api-sock "$FC_SOCKET" --enable-pci > /dev/null 2>&1 &
    
    # Wait for the API socket to become available
    for _ in {1..30}; do
        [[ -S "$FC_SOCKET" ]] && break
        sleep 0.1
    done
    
    # Hand off execution to your existing restore shell script
    export API_SOCKET
    START_UFFD_HANDLER=1 ./restore_vm_uffd.sh "$SNAPSHOT_PATH" "$MEM_PATH" "$UFFD_SOCKET" > /dev/null 2>&1
    
    # Force a validation packet down the pipeline to confirm initialization stability
    curl -s -X POST -H "Content-Type: text/plain" -d "http://172.16.0.1:8000/test-file" http://172.16.0.2:8080/ > /dev/null 2>&1 || true
    
    LOGFILE=$(get_latest_logfile)
    if [[ -n "$LOGFILE" && -f "$LOGFILE" ]]; then
        TOTAL_LOAD_US=$(grep "'load snapshot' VMM action took" "$LOGFILE" | tail -n 1 | grep -oP "took \K[0-9]+") || echo "0"
        
        RAW_NET_RESTORE=$(grep "Complete PCI net restore breakdown: total=" "$LOGFILE" | tail -n 1 | grep -oP "total=\K[0-9.]+\w+") || echo ""
        INITIAL_NET_RESTORE_US=$(parse_duration_to_us "$RAW_NET_RESTORE")
        
        echo "$i,$TOTAL_LOAD_US,$INITIAL_NET_RESTORE_US" >> "$OUTPUT_CSV"
    else
        echo "$i,0,0" >> "$OUTPUT_CSV"
    fi
done

cleanup_env
echo "=== Baseline Evaluation Complete. Data written to $OUTPUT_CSV ==="
