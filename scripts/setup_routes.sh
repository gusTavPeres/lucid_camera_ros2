#!/bin/bash
# Fix routing for dual GigE Vision cameras on overlapping 169.254.0.0/16 subnets
# Run this inside the container (network_mode: host, privileged) after startup
# Camera 243901918 is on enx5c5310faf11f (169.254.153.193) but the kernel
# defaults to enxdc3262cf8709 (metric 100) for all 169.254.x.x traffic.
# This explicit host route forces camera 243901918 traffic through the correct interface.

CAM2_IP="169.254.153.193"
CAM2_IFACE="enx5c5310faf11f"
CAM2_SRC="169.254.42.30"

if ip route show | grep -q "169.254.153.193"; then
    echo "[setup_routes] Route for camera 243901918 already exists — skipping"
else
    ip route add "${CAM2_IP}/32" dev "${CAM2_IFACE}" src "${CAM2_SRC}"
    echo "[setup_routes] Added route: ${CAM2_IP}/32 via ${CAM2_IFACE} src ${CAM2_SRC}"
fi
