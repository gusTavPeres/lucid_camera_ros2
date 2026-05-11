#!/bin/bash
# setup_routes_auto.sh — auto version of the dual-GigE route fix-up.
#
# Background: when two GigE cameras live on overlapping 169.254.0.0/16 subnets,
# Linux's default route metric picks ONE iface for all 169.254.* traffic, so
# the second camera is unreachable. Fix: add per-camera /32 host routes.
#
# Behavior:
#   - With no env override, discovers every iface that has a 169.254.x.x IP
#     and pings each known camera serial's last-seen address (skipped here
#     since we don't store ARP). For now, applies a default rule per iface
#     by examining the ARP table for any 169.254.x.x neighbor on each iface.
#   - GIGE_ROUTE_FIX env var lets you pin: "cam_ip:iface:host_src,cam_ip:iface:host_src"
#
# Idempotent.

set -e

log() { echo "[setup_routes_auto] $*"; }

# Manual override path (preserves the legacy hardcoded behavior if needed)
if [ -n "${GIGE_ROUTE_FIX:-}" ]; then
    IFS=',' read -ra _entries <<< "${GIGE_ROUTE_FIX}"
    for _e in "${_entries[@]}"; do
        IFS=':' read -r _ip _if _src <<< "$_e"
        if ip route show | grep -q "$_ip"; then
            log "Route for $_ip exists — skip"
        else
            log "Adding $_ip/32 dev $_if src $_src"
            ip route add "${_ip}/32" dev "$_if" src "$_src"
        fi
    done
    exit 0
fi

# Auto path: discover ifaces with 169.254 addresses and their ARP-known peers
ip -4 -o addr show | awk '$4 ~ /^169\.254\./ { print $2 }' | sort -u | while read -r iface; do
    src_ip=$(ip -4 -o addr show dev "$iface" | awk '{print $4}' | cut -d/ -f1 | head -1)
    # Find every 169.254.x.x peer the kernel has seen on this iface
    ip neigh show dev "$iface" 2>/dev/null \
        | awk '/^169\.254\./ { print $1 }' \
        | while read -r peer_ip; do
        if ip route show | grep -qw "$peer_ip"; then
            log "Route for $peer_ip exists — skip"
        else
            log "Adding $peer_ip/32 dev $iface src $src_ip"
            ip route add "${peer_ip}/32" dev "$iface" src "$src_ip" 2>/dev/null \
                || log "  (could not add $peer_ip — likely already routed)"
        fi
    done
done

log "Done."
