#!/usr/bin/env bash

set -euo pipefail

if [[ -f "./init_vars.sh" ]]; then
    source ./init_vars.sh
else
    echo "Error: init_vars.sh missing." >&2
    exit 1
fi

OUTPUT_CSV="memory_dirt_results.csv"
LOG_DIR="$HOME/firecracker_logs"
ITERATIONS=31 # 1 warmup + 5 measured runs

# Scaled memory allocation brackets optimized to safely beat the 2.0s guest timeout
PAYLOAD_SIZES_MB=(1 4 8 16 32 64) 

# Simplified clean schema tracking exactly what you requested
echo "dirty_mb,iteration,reset_total,pci_total_us,guest_function_us" > "$OUTPUT_CSV"

cleanup_env() {
    sudo rm -f /tmp/firecracker.socket /tmp/chameleon-uffd.sock /tmp/chameleon-uffd-handler.pid
    sudo rm -f "$FC_SOCKET" "$UFFD_SOCKET" >/dev/null 2>&1 || true
    sudo killall -9 "my_firecracker_detailed" >/dev/null 2>&1 || true
    sudo killall -9 "resetting-uffd-handler" >/dev/null 2>&1 || true
    sleep 0.2
}

parse_duration_to_us() {
    local raw_val="$1"
    if [[ -z "$raw_val" ]]; then echo "0.000"; return; fi
    if [[ "$raw_val" == *ms ]]; then
        bc <<< "scale=3; ${raw_val%ms} * 1000"
    elif [[ "$raw_val" == *µs ]]; then
        bc <<< "scale=3; ${raw_val%µs} / 1"
    else
        bc <<< "scale=3; $raw_val / 1"
    fi
}

echo "=== Starting Experiment 5: Memory Dirtiness via Network Stream Fetch ==="

# Check health via localhost (127.0.0.1) since server binds to 0.0.0.0
if ! curl -s -f -I --connect-timeout 2 http://127.0.0.1:9000/ > /dev/null; then
    echo "CRITICAL: memory_stream_server.py is not running on port 9000!" >&2
    exit 1
fi

for mb in "${PAYLOAD_SIZES_MB[@]}"; do
    echo "Target Size Bracket -> $mb MB Memory Allocation"

    for ((i=0; i<ITERATIONS; i++)); do
        echo "  Iteration $i/$ITERATIONS..."

        cleanup_env
        sudo -E "$FC_BIN" --api-sock "$FC_SOCKET" --enable-pci > /dev/null 2>&1 &
        for _ in {1..30}; do [[ -S "$FC_SOCKET" ]] && break; sleep 0.1; done
        
        START_UFFD_HANDLER=1 ./restore_vm_uffd.sh "$SNAP_CLEAN" "$MEM_CLEAN" "$UFFD_SOCKET" > /dev/null 2>&1
        LOGFILE=$(ls -t "$LOG_DIR"/firecracker-uffd-restore-*.log 2>/dev/null | head -n 1 || echo "")

        # The guest microVM talks to the host via the bridge gateway IP address
        TARGET_URL="http://172.16.0.1:9000/chunk/$mb"
        
        # Fire request into guest webserver passing the text URL raw in the request body
        GUEST_RESPONSE=$(curl -s -X POST http://172.16.0.2:8080/ \
            -H "Content-Type: text/plain" \
            -d "$TARGET_URL")

        # Pause and execute the in-place snapshot reset pathway
        sudo curl -s -X PATCH --unix-socket "$FC_SOCKET" 'http://localhost/vm' -H 'Content-Type: application/json' -d '{"state": "Paused"}' > /dev/null
        
        sudo curl -s -X PUT --unix-socket "$FC_SOCKET" 'http://localhost/snapshot/reset' \
            -H 'Content-Type: application/json' \
            -d "{\"reset_socket_path\": \"$UFFD_SOCKET\", \"snapshot_path\": \"$SNAP_CLEAN\", \"mem_file_path\": \"$MEM_CLEAN\", \"diff_file_path\": \"$NOOP_DIFF\"}" > /dev/null
        
        sudo ip neigh flush dev tap0 > /dev/null
        sudo curl -s -X PATCH --unix-socket "$FC_SOCKET" 'http://localhost/vm' -H 'Content-Type: application/json' -d '{"state": "Resumed"}' > /dev/null

        # Discard the initial warm-up run to keep data clean
        if (( i == 0 )); then
            continue
        fi

        # Parse metrics directly from the log layout strings
        VMM_ACTION_LINE=$(grep "'reset snapshot' VMM action took" "$LOGFILE" | tail -n 1) || ""
        RESET_TOTAL_US=$(echo "$VMM_ACTION_LINE" | grep -oP "took \K[0-9.]+") || echo "0.000"

        LAST_PCI_LINE=$(grep "Reset PCI net device latency breakdown:" "$LOGFILE" | tail -n 1) || ""
        PCI_TOTAL_RAW=$(echo "$LAST_PCI_LINE" | grep -oP "total=\K[0-9.]+(µs|ms)") || echo "0"
        PCI_TOTAL_US=$(parse_duration_to_us "$PCI_TOTAL_RAW")

        # Safely pluck the high-resolution execution duration out of the guest's response payload
        GUEST_NS=$(echo "$GUEST_RESPONSE" | jq -r '.guest_function_time_ns // 0' 2>/dev/null || echo "0")
        GUEST_FUNC_US=$(bc <<< "scale=3; $GUEST_NS / 1000")

        echo "$mb,$i,$RESET_TOTAL_US,$PCI_TOTAL_US,$GUEST_FUNC_US" >> "$OUTPUT_CSV"
    done
done

cleanup_env
echo "=== Experiment 5 Collection Completed ==="
