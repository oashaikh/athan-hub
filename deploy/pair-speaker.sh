#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${1:-}" == "--scan" ]]; then
  bluetoothctl power on >/dev/null
  bluetoothctl --timeout 10 scan on || true
  bluetoothctl devices
  exit 0
fi

MAC="${1:-}"
[[ -n "$MAC" ]] || { echo "Usage: sudo athan-pair-speaker MAC" >&2; echo "Discover devices first with: sudo athan-pair-speaker --scan" >&2; exit 2; }
[[ "$MAC" =~ ^([[:xdigit:]]{2}:){5}[[:xdigit:]]{2}$ ]] || { echo "Invalid Bluetooth MAC: $MAC" >&2; exit 2; }

echo "Put the Bluetooth speaker into pairing mode now."
echo "Scanning for $MAC for up to 25 seconds..."
bluetoothctl power on >/dev/null
bluetoothctl pairable on >/dev/null
bluetoothctl --timeout 25 scan on || true
bluetoothctl scan off >/dev/null 2>&1 || true

if ! bluetoothctl info "$MAC" >/dev/null 2>&1; then
  echo "The speaker did not advertise as $MAC. Confirm it is in pairing mode and nearby, then rerun:" >&2
  echo "  sudo /usr/local/bin/athan-pair-speaker $MAC" >&2
  exit 1
fi

if ! bluetoothctl info "$MAC" | grep -q 'Paired: yes'; then
  echo "Pairing $MAC..."
  bluetoothctl --agent NoInputNoOutput --timeout 45 pair "$MAC" || true
fi
if ! bluetoothctl info "$MAC" | grep -q 'Paired: yes'; then
  echo "The speaker was discovered but pairing did not complete. Put it back into pairing mode and rerun this command." >&2
  exit 1
fi
bluetoothctl trust "$MAC"
bluetoothctl connect "$MAC"

echo "Paired, trusted, and connected. Device status:"
bluetoothctl info "$MAC"
