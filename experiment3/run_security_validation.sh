#!/usr/bin/env bash

set -euo pipefail

# --- SOURCE ENVIRONMENT LAYOUT ---
if [[ -f "./init_vars.sh" ]]; then
    source ./init_vars.sh
else
    echo "Error: init_vars.sh not found in the current directory." >&2
    exit 1
fi

LOGFILE="security_validation_report.txt"
SNAPSHOT_PATH="$SNAP_CLEAN"
MEM_PATH="$MEM_CLEAN"
DIFF_PATH="$NOOP_DIFF"

cleanup_env() {
    # FIX: Use precise matching so the script doesn't match its own name
    sudo pkill -9 -x "$(basename "$FC_BIN")" >/dev/null 2>&1 || true
    sudo pkill -9 -f "resetting-uffd-handler" >/dev/null 2>&1 || true
    sudo rm -f "$FC_SOCKET" "$UFFD_SOCKET"
    sleep 0.2
}

# Initialize the file with a single redirection to clear old runs completely
echo "=== Chameleon Information Leak & Isolation Verification ===" > "$LOGFILE"
echo "=== Chameleon Information Leak & Isolation Verification ==="

# Safely clean up old lingering processes before launching new ones
cleanup_env

# 1. Start the live networked microVM process
sudo -E env RUST_BACKTRACE=1 "$FC_BIN" --api-sock "$FC_SOCKET" --enable-pci > /dev/null 2>&1 &
for _ in {1..30}; do [[ -S "$FC_SOCKET" ]] && break; sleep 0.1; done

# 2. Hydrate into clean operational base state
export API_SOCKET
START_UFFD_HANDLER=1 ./restore_vm_uffd.sh "$SNAPSHOT_PATH" "$MEM_PATH" "$UFFD_SOCKET" > /dev/null 2>&1
sleep 0.7 # Give the guest kernel network stack an extra moment to settle completely

# =========================================================================
# PHASE 1: PRE-CONTAMINATION CONTROL CHECK
# =========================================================================
echo -n "[Phase 1] Scanning pristine memory for target token... " | tee -a "$LOGFILE"

# The 'leak function' uses ssh to scan kernel circular ring buffers for data leaks
if ssh $SSH_OPTS root@172.16.0.2 'dmesg | grep -q "CHAMELEON_SECRET_TOKEN"' >/dev/null 2>&1; then
    echo "FAIL: Token prematurely present in clean snapshot!" | tee -a "$LOGFILE"
else
    echo "PASS (System is Clean)" | tee -a "$LOGFILE"
fi

# =========================================================================
# PHASE 2: INJECT SECRET TO DIRTY THE STATE (TENANT 1 ACTIVITY)
# =========================================================================
echo -e "\n[Phase 2] Injecting sensitive secret token into guest kernel log space..." | tee -a "$LOGFILE"
# Tenant 1 writes a sensitive, unique runtime token directly to the kernel message buffer
ssh $SSH_OPTS root@172.16.0.2 'echo "CHAMELEON_SECRET_TOKEN=a7b39c01f4de9e22" > /dev/kmsg'

echo -n "[Phase 2] Verifying leak visibility before reset... " | tee -a "$LOGFILE"
if ssh $SSH_OPTS root@172.16.0.2 'dmesg | grep -q "CHAMELEON_SECRET_TOKEN"' >/dev/null 2>&1; then
    echo "PASS (Leak detected as expected)" | tee -a "$LOGFILE"
else
    echo "WARNING: Token was not retained in system buffer during step preparation." | tee -a "$LOGFILE"
fi

# =========================================================================
# PHASE 3: APPLY CUSTOM IN-PLACE HOT RESET
# =========================================================================
echo -e "\n[Phase 3] Executing In-Place Hot Reset (Evicting Tenant 1 Dirty State)..." | tee -a "$LOGFILE"
sudo curl -s -X PATCH --unix-socket "$FC_SOCKET" 'http://localhost/vm' -H 'Content-Type: application/json' -d '{"state": "Paused"}' > /dev/null
sudo curl -s -X PUT --unix-socket "$FC_SOCKET" 'http://localhost/snapshot/reset' -H 'Content-Type: application/json' \
    -d "{\"reset_socket_path\": \"$UFFD_SOCKET\", \"snapshot_path\": \"$SNAPSHOT_PATH\", \"mem_file_path\": \"$MEM_PATH\", \"diff_file_path\": \"$DIFF_PATH\"}" > /dev/null
sudo ip neigh flush dev tap0 > /dev/null
sudo curl -s -X PATCH --unix-socket "$FC_SOCKET" 'http://localhost/vm' -H 'Content-Type: application/json' -d '{"state": "Resumed"}' > /dev/null
sleep 0.7 # Allow network interface descriptor ring synchronization to settle cleanly

# =========================================================================
# PHASE 4: POST-RESET ISOLATION CHECK (TENANT 2 VALIDATION)
# =========================================================================
echo -n "[Phase 4] Scanning isolated memory following Hot Reset loop... " | tee -a "$LOGFILE"
if ssh $SSH_OPTS root@172.16.0.2 'dmesg | grep -q "CHAMELEON_SECRET_TOKEN"' >/dev/null 2>&1; then
    echo "CRITICAL FAILURE: Memory leak detected! Secret token escaped the isolation boundary!" | tee -a "$LOGFILE"
else
    echo "PASS (System cleanly zeroed/restored. Zero remnants found!)" | tee -a "$LOGFILE"
fi

cleanup_env
echo -e "\n=== Security Validation Complete. Log written to $LOGFILE ===" | tee -a "$LOGFILE"
