#!/usr/bin/env bash
# Install the CAM720 two-way talk service on the Hub: the go2rtc-cam720 fork
# running beside Home Assistant's own go2rtc. Idempotent; safe to re-run.
#
# The Hub is arm64 (Radxa ROCK 4SE), so this downloads the linux/arm64 release
# binary. For a different architecture, build the fork from source instead
# (see github.com/OJ-Labs-Ltd/go2rtc-cam720 CAM720.md, "Building for your
# architecture") and point BIN at it.
set -Eeuo pipefail

readonly REPO="OJ-Labs-Ltd/go2rtc-cam720"
readonly RELEASE="v1.9.15-cam720.1"
readonly ASSET="go2rtc-cam720-linux-arm64"
readonly BIN="/usr/local/bin/go2rtc-cam720"
readonly CONF="/etc/athan-hub/go2rtc-cam720.yaml"
readonly ENVFILE="/etc/athan-hub/athan-hub.env"
readonly UNIT="/etc/systemd/system/cam720-talk.service"
here="$(cd "$(dirname "$0")" && pwd)"

[ "$(id -u)" -eq 0 ] || { echo "run as root"; exit 1; }
[ -f "$ENVFILE" ] || { echo "missing $ENVFILE"; exit 1; }

# The camera UID is not secret; discover it once from the camera's setup port
# and record it in the env file if absent, so the config stays generic.
if ! grep -q '^ATHAN_HA_CAMERA_UID=.' "$ENVFILE"; then
  ip="$(sed -n 's/^ATHAN_HA_CAMERA_IP=//p' "$ENVFILE" | head -n1)"
  uid="$(curl -s -m6 "http://${ip}:9898/get?singleCMD=get_deviceFeatures" \
    | sed -n 's/.*"device_id":"\([^"]*\)".*/\1/p')"
  [ -n "$uid" ] || { echo "could not read camera UID from ${ip}:9898"; exit 1; }
  printf 'ATHAN_HA_CAMERA_UID=%s\n' "$uid" >> "$ENVFILE"
fi

curl -fSL -o "$BIN" \
  "https://github.com/${REPO}/releases/download/${RELEASE}/${ASSET}"
chmod 0755 "$BIN"

install -m 0644 "$here/go2rtc-cam720.yaml" "$CONF"
install -m 0644 "$here/systemd/cam720-talk.service" "$UNIT"

systemctl daemon-reload
systemctl enable --now cam720-talk.service
systemctl --no-pager --lines=0 status cam720-talk.service || true
echo "cam720-talk installed; API on 127.0.0.1:1985, stream 'cam720'."
