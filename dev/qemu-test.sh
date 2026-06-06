#!/usr/bin/env bash
# Boot the pi-frame SD image in QEMU and verify services start correctly.
# Requires: qemu-system-aarch64, the built SD image in ../result/
#
# Usage:
#   nix build .#pi-sd-image       # build SD image first
#   bash dev/qemu-test.sh

set -euo pipefail

IMG="$(ls ../result/sd-image/pi-frame*.img 2>/dev/null | head -1)"
if [ -z "$IMG" ]; then
  echo "ERROR: No SD image found. Run 'nix build .#pi-sd-image' first."
  exit 1
fi

# Extract kernel and DTB from the image's boot partition (offset 1 MiB, size 256 MiB)
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

echo "Mounting boot partition from $IMG …"
OFFSET=$((1 * 1024 * 1024))
sudo mount -o loop,offset="$OFFSET",ro "$IMG" "$WORKDIR/boot" 2>/dev/null || {
  # Non-root fallback using udiskctl
  LOOPDEV="$(sudo losetup --find --show -o "$OFFSET" "$IMG")"
  sudo mount -o ro "$LOOPDEV" "$WORKDIR/boot"
  trap "sudo umount '$WORKDIR/boot'; sudo losetup -d '$LOOPDEV'; rm -rf '$WORKDIR'" EXIT
}

KERNEL="$(ls "$WORKDIR/boot"/kernel*.img 2>/dev/null | head -1)"
DTB="$(ls "$WORKDIR/boot"/bcm2837-rpi-zero-2*.dtb 2>/dev/null | head -1)"

if [ -z "$KERNEL" ] || [ -z "$DTB" ]; then
  echo "ERROR: Could not find kernel or DTB in boot partition."
  ls "$WORKDIR/boot/" || true
  exit 1
fi

echo "Kernel: $KERNEL"
echo "DTB:    $DTB"

LOG="$WORKDIR/serial.log"
echo "Starting QEMU (output → $LOG) …"

timeout 120 qemu-system-aarch64 \
  -machine raspi3b \
  -cpu cortex-a53 \
  -m 512M \
  -kernel "$KERNEL" \
  -dtb "$DTB" \
  -drive "file=$IMG,format=raw,if=sd" \
  -serial "file:$LOG" \
  -display none \
  -append "console=ttyAMA0,115200 root=/dev/mmcblk0p2 rootfstype=ext4 rw" \
  & QEMU_PID=$!

# Wait for systemd to reach multi-user.target (or timeout)
echo "Waiting for boot …"
TIMEOUT=120
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
  if grep -q "Reached target.*Multi-User" "$LOG" 2>/dev/null; then
    break
  fi
  sleep 2
  ELAPSED=$((ELAPSED + 2))
done

kill "$QEMU_PID" 2>/dev/null || true
wait "$QEMU_PID" 2>/dev/null || true

echo ""
echo "=== Serial output ==="
cat "$LOG"
echo ""

# Assertions
PASS=true

check() {
  local pattern="$1"
  local label="$2"
  if grep -q "$pattern" "$LOG"; then
    echo "  PASS: $label"
  else
    echo "  FAIL: $label (pattern: $pattern)"
    PASS=false
  fi
}

check "Reached target.*Multi-User\|systemd.*Finished" "System booted"
check "piframe-wifi" "WiFi manager service started"
check "piframe-listener\|piframe\.service" "pi-frame service present"

# Fail if any pi-frame service failed
if grep -E "FAILED.*piframe|piframe.*FAILED" "$LOG"; then
  echo "  FAIL: A piframe service reported failure"
  PASS=false
fi

if $PASS; then
  echo "All QEMU boot checks passed."
  exit 0
else
  echo "Some checks failed."
  exit 1
fi
