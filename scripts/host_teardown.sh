#!/bin/bash
# host_teardown.sh — reverses host_setup.sh.
# Restores MTU 1500, removes the Ouster IP alias.
# Does NOT remove the sysctl drop-in (cheap to leave; comment line below if
# you want it removed).

set -e

if [ "$(id -u)" -ne 0 ]; then
    exec sudo -E "$0" "$@"
fi

log()  { echo "[host_teardown] $*"; }

if [ -z "${SENSOR_IFACE:-}" ]; then
    SENSOR_IFACE=$(ip -4 -o addr show | awk '$4 ~ /^169\.254\./ { print $2; exit }')
fi
if [ -z "${OUSTER_IFACE:-}" ]; then
    OUSTER_IFACE=$(ip -4 -o addr show | awk '$4 ~ /^192\.168\.1\./ { print $2; exit }')
fi
OUSTER_HOST_IP="${OUSTER_HOST_IP:-192.168.1.1/24}"

for iface in "${SENSOR_IFACE:-}" "${OUSTER_IFACE:-}"; do
    [ -z "$iface" ] && continue
    if ip link show "$iface" >/dev/null 2>&1; then
        cur=$(cat "/sys/class/net/$iface/mtu" 2>/dev/null || echo 0)
        if [ "$cur" != "1500" ]; then
            log "Restoring MTU on $iface: $cur -> 1500"
            ip link set "$iface" mtu 1500
        fi
    fi
done

if [ -n "${OUSTER_IFACE:-}" ] && ip link show "$OUSTER_IFACE" >/dev/null 2>&1; then
    if ip -4 addr show dev "$OUSTER_IFACE" | grep -qw "${OUSTER_HOST_IP%/*}"; then
        log "Removing $OUSTER_HOST_IP from $OUSTER_IFACE"
        ip addr del "$OUSTER_HOST_IP" dev "$OUSTER_IFACE" || true
    fi
fi

# Uncomment if you also want sysctls reverted:
# rm -f /etc/sysctl.d/99-sensor-stack.conf
# sysctl --system >/dev/null

log "Done."
