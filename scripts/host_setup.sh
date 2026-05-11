#!/bin/bash
# host_setup.sh — host-side network prep for the sensor_stack container.
#
# Run on the host BEFORE `docker compose up`. A container in network_mode:host
# cannot reconfigure host NICs by itself.
#
# What it does (idempotent):
#   1. Sets MTU 9000 (jumbo frames) on the Lucid GigE iface.
#   2. Sets MTU 9000 on the Ouster iface.
#   3. Disables NIC offloading on both ifaces (GigE Vision dislikes it).
#   4. Adds an IP alias on the Ouster iface so the host has 192.168.1.1/24
#      -> reachable by the sensor at 192.168.1.200.
#   5. Raises kernel socket buffer sizes.
#
# Auto-detection (any of these can be overridden by exporting the env var):
#   SENSOR_IFACE    — Lucid GigE iface. Default: first iface with a 169.254.x.x IP.
#   OUSTER_IFACE    — Ouster iface.     Default: error if not exported.
#   OUSTER_HOST_IP  — Host IP alias for the lidar subnet. Default: 192.168.1.1/24.
#   LIDAR_HOSTNAME  — Sensor IP (used for the reachability check). Default: 192.168.1.200.
#
# Usage:
#   sudo ./scripts/host_setup.sh
#   SENSOR_IFACE=enp45s0 OUSTER_IFACE=enp46s0 sudo -E ./scripts/host_setup.sh

set -e

# --- Privilege check --------------------------------------------------------
if [ "$(id -u)" -ne 0 ]; then
    echo "[host_setup] Re-running under sudo..."
    exec sudo -E "$0" "$@"
fi

# --- Helpers ----------------------------------------------------------------
log()  { echo "[host_setup] $*"; }
warn() { echo "[host_setup] WARN: $*" >&2; }
die()  { echo "[host_setup] ERROR: $*" >&2; exit 1; }

# Returns 0 if $1 names an existing iface
iface_exists() { ip link show "$1" >/dev/null 2>&1; }

# Print the current MTU of $1
iface_mtu() { cat "/sys/class/net/$1/mtu" 2>/dev/null || echo 0; }

# Find first iface that has an IPv4 in $1 (regex)
find_iface_by_cidr() {
    local cidr="$1"
    ip -4 -o addr show | awk -v c="$cidr" '$4 ~ c { print $2; exit }'
}

# Set MTU only if not already at the target value
set_mtu() {
    local iface="$1" target="$2"
    local cur
    cur=$(iface_mtu "$iface")
    if [ "$cur" = "$target" ]; then
        log "MTU on $iface already $target — skip"
    else
        log "Setting MTU on $iface: $cur -> $target"
        ip link set "$iface" mtu "$target"
    fi
}

# Disable offloading
disable_offload() {
    local iface="$1"
    ethtool -K "$iface" tx off rx off gso off gro off tso off 2>/dev/null \
        || warn "ethtool offload toggles unavailable on $iface (may already be off)"
}

# Add IP alias only if missing
add_addr_if_absent() {
    local iface="$1" addr="$2"
    if ip -4 addr show dev "$iface" | grep -qw "${addr%/*}"; then
        log "IP $addr already on $iface — skip"
    else
        log "Adding IP $addr to $iface"
        ip addr add "$addr" dev "$iface"
    fi
}

# --- 1. Resolve SENSOR_IFACE (Lucid GigE) -----------------------------------
if [ -z "${SENSOR_IFACE:-}" ]; then
    SENSOR_IFACE=$(find_iface_by_cidr '^169\.254\.')
    [ -z "$SENSOR_IFACE" ] && warn "No iface with 169.254.x.x found — set SENSOR_IFACE explicitly."
fi

# --- 2. Resolve OUSTER_IFACE ------------------------------------------------
OUSTER_HOST_IP="${OUSTER_HOST_IP:-192.168.1.1/24}"
LIDAR_HOSTNAME="${LIDAR_HOSTNAME:-192.168.1.200}"

if [ -z "${OUSTER_IFACE:-}" ]; then
    # Try: is there already an iface in 192.168.1.0/24?
    OUSTER_IFACE=$(find_iface_by_cidr '^192\.168\.1\.')
fi
if [ -z "${OUSTER_IFACE:-}" ]; then
    warn "OUSTER_IFACE not set and no iface has a 192.168.1.x IP yet."
    warn "Export OUSTER_IFACE=<name> and re-run, or skip lidar config."
fi

# --- 3. Apply per-iface settings --------------------------------------------
for iface_var in SENSOR_IFACE OUSTER_IFACE; do
    iface="${!iface_var:-}"
    [ -z "$iface" ] && continue
    if ! iface_exists "$iface"; then
        warn "$iface_var=$iface does not exist on this host — skip"
        continue
    fi
    log "Configuring $iface_var -> $iface"
    set_mtu "$iface" 9000
    disable_offload "$iface"
done

# --- 4. Ouster subnet IP alias + reachability ------------------------------
if [ -n "${OUSTER_IFACE:-}" ] && iface_exists "$OUSTER_IFACE"; then
    add_addr_if_absent "$OUSTER_IFACE" "$OUSTER_HOST_IP"
    log "Pinging $LIDAR_HOSTNAME via $OUSTER_IFACE..."
    if ping -c 1 -W 2 -I "$OUSTER_IFACE" "$LIDAR_HOSTNAME" >/dev/null 2>&1; then
        log "  Sensor reachable at $LIDAR_HOSTNAME"
    else
        warn "  Sensor at $LIDAR_HOSTNAME did not respond (expected if no hw yet)."
    fi
fi

# --- 5. Kernel buffers ------------------------------------------------------
log "Raising kernel socket buffers..."
sysctl -w net.core.rmem_default=33554432 >/dev/null
sysctl -w net.core.rmem_max=134217728    >/dev/null
sysctl -w net.core.wmem_default=33554432 >/dev/null
sysctl -w net.core.wmem_max=134217728    >/dev/null

# Persist (idempotent overwrite)
cat > /etc/sysctl.d/99-sensor-stack.conf << 'EOF'
# Managed by sensor_stack host_setup.sh
net.core.rmem_default=33554432
net.core.rmem_max=134217728
net.core.wmem_default=33554432
net.core.wmem_max=134217728
EOF

log "Done."
log "  SENSOR_IFACE=${SENSOR_IFACE:-<unset>}  MTU=$(iface_mtu "${SENSOR_IFACE:-lo}")"
log "  OUSTER_IFACE=${OUSTER_IFACE:-<unset>}  MTU=$(iface_mtu "${OUSTER_IFACE:-lo}")"
log "  Now run: docker compose up -d sensor_stack"
