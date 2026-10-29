#!/usr/bin/env bash
set -Eeuo pipefail

readonly DEFAULT_REPOSITORY="oashaikh/athan-hub"
readonly INSTALL_ROOT="/opt/athan-hub"
readonly DATA_ROOT="/var/lib/athan-hub"
readonly CONFIG_ROOT="/etc/athan-hub"
readonly LOG_ROOT="/var/log/athan-hub"

TEMP_ROOT=""
SOURCE_ROOT=""
SERVICE_USER="athan"
BRANCH="main"
NEW_HOSTNAME=""
TIMEZONE=""
REQUESTED_PIN=""
PIN_MODE="preserve"
INSTALL_SYSTEM_PACKAGES=true
REPOSITORY="${ATHAN_REPOSITORY:-$DEFAULT_REPOSITORY}"

usage() {
  cat <<'EOF'
Usage: sudo ./install.sh [options]

Options:
  --hostname NAME       Set the mDNS hostname (fresh installs default to athan.local)
  --keep-hostname       Do not change the current hostname
  --timezone ZONE       IANA timezone; defaults to the operating system timezone
  --user USER           Service account; defaults to athan
  --pin PIN             Set a dashboard PIN (letters, numbers, dot, underscore, dash)
  --no-pin              Disable dashboard PIN protection
  --source-dir PATH     Install from an existing checkout instead of GitHub
  --branch NAME         GitHub branch to install (default: main)
  --skip-system-packages
                        Reuse installed OS/audio packages during an automatic update
  -h, --help            Show this help

Optional Wi-Fi setup uses environment variables so the password is not placed in
shell history: ATHAN_WIFI_SSID and ATHAN_WIFI_PASSWORD. NetworkManager/nmcli must
already be available. Wi-Fi is otherwise left exactly as configured by Ubuntu.
EOF
}

log() { printf '\n==> %s\n' "$*"; }
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
cleanup() {
  if [[ -n "$TEMP_ROOT" && -d "$TEMP_ROOT" ]]; then
    rm -rf -- "$TEMP_ROOT"
  fi
  return 0
}
trap cleanup EXIT

[[ $EUID -eq 0 ]] || fail "Run as root, for example: sudo ./install.sh"
[[ -r /etc/os-release ]] || fail "Cannot identify the operating system"
# This standard file exists on every supported target.
# shellcheck disable=SC1091
. /etc/os-release
case "${ID:-}" in
  ubuntu|debian|raspbian) ;;
  *) fail "Supported systems are Ubuntu 22.04+, Debian 12+, and Raspberry Pi OS Bookworm; found ${ID:-unknown}" ;;
esac

if [[ -f "$CONFIG_ROOT/installed" ]]; then
  NEW_HOSTNAME=""
else
  NEW_HOSTNAME="athan"
fi

while (($#)); do
  case "$1" in
    --hostname) [[ $# -ge 2 ]] || fail "--hostname needs a value"; NEW_HOSTNAME="$2"; shift 2 ;;
    --keep-hostname) NEW_HOSTNAME=""; shift ;;
    --timezone) [[ $# -ge 2 ]] || fail "--timezone needs a value"; TIMEZONE="$2"; shift 2 ;;
    --user) [[ $# -ge 2 ]] || fail "--user needs a value"; SERVICE_USER="$2"; shift 2 ;;
    --pin) [[ $# -ge 2 ]] || fail "--pin needs a value"; REQUESTED_PIN="$2"; PIN_MODE="set"; shift 2 ;;
    --no-pin) REQUESTED_PIN=""; PIN_MODE="disable"; shift ;;
    --source-dir) [[ $# -ge 2 ]] || fail "--source-dir needs a value"; SOURCE_ROOT="$(cd -- "$2" && pwd)"; shift 2 ;;
    --branch) [[ $# -ge 2 ]] || fail "--branch needs a value"; BRANCH="$2"; shift 2 ;;
    --skip-system-packages) INSTALL_SYSTEM_PACKAGES=false; shift ;;
    -h|--help) usage; exit 0 ;;
    *) fail "Unknown option: $1" ;;
  esac
done

[[ "$SERVICE_USER" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]] || fail "Invalid service user"
[[ -z "$NEW_HOSTNAME" || "$NEW_HOSTNAME" =~ ^[a-zA-Z0-9][a-zA-Z0-9-]{0,62}$ ]] || fail "Invalid hostname"
[[ "$BRANCH" =~ ^[A-Za-z0-9._/-]+$ ]] || fail "Invalid branch"
[[ "$PIN_MODE" != "set" || "$REQUESTED_PIN" =~ ^[A-Za-z0-9._-]{4,128}$ ]] || fail "PIN must be 4-128 characters using letters, numbers, dot, underscore, or dash"

if [[ "$INSTALL_SYSTEM_PACKAGES" == true ]]; then
  log "Installing operating-system dependencies"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y --no-install-recommends \
    avahi-daemon bluez ca-certificates curl dbus-user-session gettext-base \
    ffmpeg git mpg123 nginx openssl python3 python3-pip python3-venv pulseaudio-utils rsync tar
fi

python3 - <<'PY' || fail "Python 3.10 or newer is required (Ubuntu 22.04 or newer)"
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY

if dpkg-query -W -f='${Status}' pipewire-pulse 2>/dev/null | grep -q 'install ok installed'; then
  AUDIO_BACKEND="pipewire"
elif [[ "$INSTALL_SYSTEM_PACKAGES" == true ]] && apt-cache show pipewire-pulse wireplumber libspa-0.2-bluetooth >/dev/null 2>&1; then
  apt-get install -y --no-install-recommends pipewire pipewire-pulse wireplumber libspa-0.2-bluetooth pulseaudio-utils
  AUDIO_BACKEND="pipewire"
else
  if [[ "$INSTALL_SYSTEM_PACKAGES" == true ]]; then
    apt-get install -y --no-install-recommends pulseaudio pulseaudio-module-bluetooth pulseaudio-utils
  else
    command -v pulseaudio >/dev/null || fail "No supported audio backend is installed; rerun without --skip-system-packages"
  fi
  AUDIO_BACKEND="pulseaudio"
fi

# Bookworm's PipeWire 0.3.65 always advertises the device as a Bluetooth
# speaker too, so an Echo streams the wrong way and drops the pairing.
# WirePlumber 0.5 from backports can restrict it to the audio source role.
if [[ "$AUDIO_BACKEND" == "pipewire" ]] && [[ "$INSTALL_SYSTEM_PACKAGES" == true ]] \
  && apt-cache policy wireplumber 2>/dev/null | grep -q bookworm-backports \
  && dpkg --compare-versions "$(dpkg-query -W -f='${Version}' wireplumber 2>/dev/null || echo 0)" lt 0.5; then
  log "Upgrading PipeWire from bookworm-backports for Bluetooth speaker support"
  apt-get install -y --no-install-recommends -t bookworm-backports \
    pipewire pipewire-bin pipewire-pulse libspa-0.2-bluetooth wireplumber
fi

# A desktop login screen runs its own audio session with a seat, which claims
# the Bluetooth audio profiles before the service account can register them.
if [[ "$(systemctl get-default 2>/dev/null)" == "graphical.target" ]]; then
  log "Booting to the console so a desktop login screen cannot claim Bluetooth audio"
  systemctl set-default multi-user.target
fi

# The weekly trim has hung SD cards on Rockchip boards and left the root
# filesystem read-only, so it stays off when the system runs from an SD/eMMC.
if [[ "$(findmnt -no SOURCE / 2>/dev/null)" == /dev/mmcblk* ]]; then
  systemctl mask fstrim.timer >/dev/null 2>&1 || true
fi

if [[ -z "$SOURCE_ROOT" ]]; then
  script_source="${BASH_SOURCE[0]:-}"
  if [[ -n "$script_source" ]] && script_directory="$(cd -- "$(dirname -- "$script_source")" 2>/dev/null && pwd)"; then
    :
  else
    script_directory=""
  fi
  if [[ -f "$script_directory/backend/pyproject.toml" ]]; then
    SOURCE_ROOT="$script_directory"
  else
    log "Downloading Athan Hub from GitHub"
    TEMP_ROOT="$(mktemp -d /tmp/athan-hub-install.XXXXXX)"
    curl -fsSL "https://github.com/${REPOSITORY}/archive/refs/heads/${BRANCH}.tar.gz" | tar -xz -C "$TEMP_ROOT"
    SOURCE_ROOT="$(find "$TEMP_ROOT" -mindepth 1 -maxdepth 1 -type d -print -quit)"
  fi
fi

[[ -f "$SOURCE_ROOT/backend/pyproject.toml" ]] || fail "Source tree is missing backend/pyproject.toml"
[[ -f "$SOURCE_ROOT/frontend/dist/index.html" ]] || fail "Prebuilt frontend is missing; run npm ci && npm run build before installing a local checkout"
[[ -f "$SOURCE_ROOT/backend/requirements.lock" ]] || fail "Backend dependency lock file is missing"
[[ -f "$SOURCE_ROOT/resources/quran/quran.sqlite" ]] || fail "Packaged Quran resource database is missing"
[[ -f "$SOURCE_ROOT/resources/quran/manifest.json" ]] || fail "Quran resource manifest is missing"

if [[ -n "$NEW_HOSTNAME" ]]; then
  log "Setting hostname to $NEW_HOSTNAME"
  hostnamectl set-hostname "$NEW_HOSTNAME"
fi

if [[ -n "${ATHAN_WIFI_SSID:-}" || -n "${ATHAN_WIFI_PASSWORD:-}" ]]; then
  [[ -n "${ATHAN_WIFI_SSID:-}" && -n "${ATHAN_WIFI_PASSWORD:-}" ]] || fail "Set both ATHAN_WIFI_SSID and ATHAN_WIFI_PASSWORD"
  command -v nmcli >/dev/null || fail "Optional Wi-Fi setup requires NetworkManager/nmcli; configure Wi-Fi through Ubuntu netplan or cloud-init instead"
  log "Configuring the requested Wi-Fi connection"
  nmcli radio wifi on
  nmcli --wait 30 device wifi connect "$ATHAN_WIFI_SSID" password "$ATHAN_WIFI_PASSWORD"
fi

log "Preparing the dedicated service account"
if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir "$DATA_ROOT" --shell /usr/sbin/nologin "$SERVICE_USER"
fi
SERVICE_UID="$(id -u "$SERVICE_USER")"
for supplemental_group in audio bluetooth; do
  getent group "$supplemental_group" >/dev/null || groupadd --system "$supplemental_group"
  usermod -a -G "$supplemental_group" "$SERVICE_USER"
done
install -d -o "$SERVICE_USER" -g "$SERVICE_USER" -m 0750 \
  "$DATA_ROOT" "$DATA_ROOT/uploads" "$DATA_ROOT/audio" "$DATA_ROOT/backgrounds" "$DATA_ROOT/quran-cache" "$LOG_ROOT"
install -d -o root -g "$SERVICE_USER" -m 0750 "$CONFIG_ROOT"

if [[ -z "$TIMEZONE" ]]; then
  TIMEZONE="$(timedatectl show --property=Timezone --value 2>/dev/null || true)"
  TIMEZONE="${TIMEZONE:-Etc/UTC}"
fi
[[ "$TIMEZONE" =~ ^[A-Za-z0-9_+.-]+(/[A-Za-z0-9_+.-]+)+$ ]] || fail "Invalid IANA timezone: $TIMEZONE"
[[ -e "/usr/share/zoneinfo/$TIMEZONE" ]] || fail "Timezone not installed: $TIMEZONE"

existing_pin=""
existing_secret=""
existing_ha=""
if [[ -r "$CONFIG_ROOT/athan-hub.env" ]]; then
  existing_pin="$(sed -n 's/^ATHAN_PIN=//p' "$CONFIG_ROOT/athan-hub.env" | head -n 1)"
  existing_secret="$(sed -n 's/^ATHAN_PIN_SECRET=//p' "$CONFIG_ROOT/athan-hub.env" | head -n 1)"
  # Home Assistant output settings are added by hand; keep them across updates.
  existing_ha="$(grep -E '^ATHAN_(HA|VERCEL|AUDIO)_' "$CONFIG_ROOT/athan-hub.env" || true)"
fi
generated_pin=""
case "$PIN_MODE" in
  set) dashboard_pin="$REQUESTED_PIN" ;;
  disable) dashboard_pin="" ;;
  preserve)
    if [[ -r "$CONFIG_ROOT/installed" ]]; then
      dashboard_pin="$existing_pin"
    else
      dashboard_pin="$(printf '%06d' "$(( $(od -An -N4 -tu4 /dev/urandom) % 1000000 ))")"
      generated_pin="$dashboard_pin"
    fi
    ;;
esac
pin_secret="${existing_secret:-$(openssl rand -hex 32)}"

umask 077
{
  printf 'ATHAN_DATA_DIR=%s\n' "$DATA_ROOT"
  printf 'ATHAN_LOG_DIR=%s\n' "$LOG_ROOT"
  printf 'ATHAN_UPLOAD_DIR=%s\n' "$DATA_ROOT/uploads"
  printf 'ATHAN_AUDIO_DIR=%s\n' "$DATA_ROOT/audio"
  printf 'ATHAN_BACKGROUND_DIR=%s\n' "$DATA_ROOT/backgrounds"
  printf 'ATHAN_QURAN_CACHE_DIR=%s\n' "$DATA_ROOT/quran-cache"
  printf 'ATHAN_QURAN_RESOURCE_DB=%s\n' "$INSTALL_ROOT/resources/quran/quran.sqlite"
  printf 'ATHAN_QURAN_MANIFEST_PATH=%s\n' "$INSTALL_ROOT/resources/quran/manifest.json"
  printf 'ATHAN_PLAYBACK_STATE_PATH=/run/athan-hub/athan-active.json\n'
  printf 'ATHAN_DB_PATH=%s\n' "$DATA_ROOT/athan.db"
  printf 'ATHAN_TIMEZONE=%s\n' "$TIMEZONE"
  printf 'ATHAN_PIN=%s\n' "$dashboard_pin"
  printf 'ATHAN_PIN_SECRET=%s\n' "$pin_secret"
  printf 'ATHAN_LOG_LEVEL=INFO\n'
  [[ -z "$existing_ha" ]] || printf '%s\n' "$existing_ha"
} > "$CONFIG_ROOT/athan-hub.env"
chown root:"$SERVICE_USER" "$CONFIG_ROOT/athan-hub.env"
chmod 0640 "$CONFIG_ROOT/athan-hub.env"
umask 022

log "Installing application files"
install -d -o "$SERVICE_USER" -g "$SERVICE_USER" -m 0755 "$INSTALL_ROOT"
rsync -a --delete \
  --exclude '.git' --exclude '.github' --exclude '.DS_Store' --exclude '._*' \
  --exclude 'backend/venv' --exclude 'frontend/node_modules' \
  "$SOURCE_ROOT/" "$INSTALL_ROOT/"
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_ROOT"
rsync -a --ignore-existing "$SOURCE_ROOT/backgrounds/" "$DATA_ROOT/backgrounds/"
chown -R "$SERVICE_USER:$SERVICE_USER" "$DATA_ROOT/backgrounds"

log "Installing locked Python dependencies"
if [[ ! -x "$INSTALL_ROOT/backend/venv/bin/python" ]]; then
  runuser -u "$SERVICE_USER" -- python3 -m venv "$INSTALL_ROOT/backend/venv"
fi
runuser -u "$SERVICE_USER" -- "$INSTALL_ROOT/backend/venv/bin/pip" install --disable-pip-version-check --upgrade pip setuptools wheel
runuser -u "$SERVICE_USER" -- "$INSTALL_ROOT/backend/venv/bin/pip" install --disable-pip-version-check -r "$INSTALL_ROOT/backend/requirements.lock"
runuser -u "$SERVICE_USER" -- "$INSTALL_ROOT/backend/venv/bin/pip" install --disable-pip-version-check --no-deps "$INSTALL_ROOT/backend"
runuser -u "$SERVICE_USER" -- "$INSTALL_ROOT/backend/venv/bin/python" -c \
  "from pathlib import Path; from athan_hub.core.quran_resources import QuranResources; QuranResources(Path('$INSTALL_ROOT/resources/quran/quran.sqlite'), Path('$INSTALL_ROOT/resources/quran/manifest.json'))"

# Packaged Quran resources are immutable application data. The service can read
# them, but only root can replace them during a verified upgrade.
chown -R root:"$SERVICE_USER" "$INSTALL_ROOT/resources/quran"
find "$INSTALL_ROOT/resources/quran" -type d -exec chmod 0550 {} +
find "$INSTALL_ROOT/resources/quran" -type f -exec chmod 0440 {} +

if [[ "$INSTALL_SYSTEM_PACKAGES" == true ]]; then
  log "Starting the headless audio session"
  loginctl enable-linger "$SERVICE_USER" || true
  systemctl start "user@${SERVICE_UID}.service"
  user_bus="unix:path=/run/user/${SERVICE_UID}/bus"
  if [[ "$AUDIO_BACKEND" == "pipewire" ]]; then
    runuser -u "$SERVICE_USER" -- env XDG_RUNTIME_DIR="/run/user/${SERVICE_UID}" DBUS_SESSION_BUS_ADDRESS="$user_bus" \
      systemctl --user enable --now pipewire.service pipewire-pulse.service wireplumber.service
  else
    runuser -u "$SERVICE_USER" -- env XDG_RUNTIME_DIR="/run/user/${SERVICE_UID}" pulseaudio --start || true
  fi
else
  log "Reusing the existing headless audio session"
fi

if [[ "$AUDIO_BACKEND" == "pipewire" ]]; then
  # WirePlumber only runs its Bluetooth audio monitor for a user with an
  # active logind seat. The service account is a lingering, seatless user, so
  # without this override the speaker connects at the Bluetooth link level but
  # its A2DP sink never appears or is torn down again. Applied on every install
  # and update because updates skip the audio bootstrap above.
  log "Enabling Bluetooth audio for the headless audio session"
  wp_changed=false
  wp_write() {
    local target="$1" content="$2"
    install -d -m 0755 "$(dirname "$target")"
    if [[ ! -f "$target" ]] || [[ "$(cat "$target")" != "$content" ]]; then
      printf '%s\n' "$content" > "$target"
      chmod 0644 "$target"
      wp_changed=true
    fi
  }
  # WirePlumber 0.5 and newer (Debian trixie and later).
  wp_write /etc/wireplumber/wireplumber.conf.d/80-athan-hub-headless-bluetooth.conf \
'wireplumber.profiles = {
  main = {
    monitor.bluez.seat-monitoring = disabled
  }
}
# Only ever an audio source, never a speaker or headset, and report PLAYING
# over AVRCP while streaming, as a phone does.
monitor.bluez.properties = {
  bluez5.roles = [ a2dp_source ]
  bluez5.dummy-avrcp-player = true
  bluez5.enable-hw-volume = false
}'
  # WirePlumber 0.4 (Debian/Raspberry Pi OS bookworm).
  wp_write /etc/wireplumber/bluetooth.lua.d/80-athan-hub-headless-bluetooth.lua \
'bluez_monitor.properties["with-logind"] = false
bluez_monitor.properties["bluez5.dummy-avrcp-player"] = true
bluez_monitor.properties["bluez5.enable-hw-volume"] = false'
  if [[ "$wp_changed" == true ]] && [[ -S "/run/user/${SERVICE_UID}/bus" ]]; then
    runuser -u "$SERVICE_USER" -- env XDG_RUNTIME_DIR="/run/user/${SERVICE_UID}" \
      DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/${SERVICE_UID}/bus" \
      systemctl --user restart wireplumber.service || true
  fi
fi

log "Installing system services and web server"
install -m 0755 "$INSTALL_ROOT/deploy/pair-speaker.sh" /usr/local/bin/athan-pair-speaker
install -m 0755 "$INSTALL_ROOT/deploy/doctor.sh" /usr/local/bin/athan-hub-doctor
install -m 0755 "$INSTALL_ROOT/deploy/update.sh" /usr/local/bin/athan-hub-update
install -m 0755 "$INSTALL_ROOT/deploy/backup.sh" /usr/local/bin/athan-hub-backup
install -m 0755 "$INSTALL_ROOT/uninstall.sh" /usr/local/bin/athan-hub-uninstall
for service in athan-hub-api athan-hub-scheduler; do
  sed -e "s/@ATHAN_USER@/$SERVICE_USER/g" -e "s/@ATHAN_UID@/$SERVICE_UID/g" \
    "$INSTALL_ROOT/deploy/systemd/$service.service.in" > "/etc/systemd/system/$service.service"
done
install -m 0644 "$INSTALL_ROOT/deploy/systemd/athan-hub-update.service" /etc/systemd/system/athan-hub-update.service
install -m 0644 "$INSTALL_ROOT/deploy/systemd/athan-hub-update.timer" /etc/systemd/system/athan-hub-update.timer
install -m 0755 "$INSTALL_ROOT/deploy/athan-audio-sync.py" /usr/local/bin/athan-audio-sync
install -m 0644 "$INSTALL_ROOT/deploy/systemd/athan-audio-sync.service" /etc/systemd/system/athan-audio-sync.service
install -m 0644 "$INSTALL_ROOT/deploy/systemd/athan-audio-sync.path" /etc/systemd/system/athan-audio-sync.path
if [[ ! -e "$CONFIG_ROOT/updater.env" ]]; then
  cat > "$CONFIG_ROOT/updater.env" <<EOF
ATHAN_UPDATE_REPOSITORY=https://github.com/${REPOSITORY}.git
ATHAN_UPDATE_BRANCH=${BRANCH}
EOF
  chown root:root "$CONFIG_ROOT/updater.env"
  chmod 0644 "$CONFIG_ROOT/updater.env"
fi
# With ATHAN_HA_FRONT_DOOR=1 Home Assistant answers on port 80 (http://athan.local)
# and the Athan Hub dashboard moves to port 8080.
web_port=80
if grep -q '^ATHAN_HA_FRONT_DOOR=1$' "$CONFIG_ROOT/athan-hub.env"; then
  web_port=8080
  install -m 0644 "$INSTALL_ROOT/deploy/nginx/home-assistant.nginx" /etc/nginx/sites-available/home-assistant
  ln -sfn /etc/nginx/sites-available/home-assistant /etc/nginx/sites-enabled/home-assistant
else
  rm -f /etc/nginx/sites-enabled/home-assistant
fi
sed -e "s/listen \(\[::\]:\)\{0,1\}80 default_server;/listen \1$web_port default_server;/" \
  "$INSTALL_ROOT/deploy/nginx/athan-hub.nginx" > /etc/nginx/sites-available/athan-hub
chmod 0644 /etc/nginx/sites-available/athan-hub
ln -sfn /etc/nginx/sites-available/athan-hub /etc/nginx/sites-enabled/athan-hub
rm -f /etc/nginx/sites-enabled/default
nginx -t

if command -v ufw >/dev/null && ufw status | grep -q '^Status: active'; then
  ufw allow "$web_port/tcp" comment 'Athan Hub dashboard'
  ufw allow 80/tcp comment 'Dashboard'
  ufw allow 5353/udp comment 'mDNS discovery'
fi

systemctl daemon-reload
systemctl enable --now bluetooth.service avahi-daemon.service nginx.service athan-hub-api.service athan-hub-scheduler.service athan-hub-update.timer athan-audio-sync.path
systemctl restart athan-hub-api.service athan-hub-scheduler.service nginx.service

log "Waiting for the application health check"
for _ in {1..45}; do
  curl -fsS http://127.0.0.1:9000/api/health >/dev/null 2>&1 && break
  sleep 1
done
if ! curl -fsS http://127.0.0.1:9000/api/health >/dev/null; then
  systemctl --no-pager --full status athan-hub-api.service || true
  journalctl -u athan-hub-api.service -n 100 --no-pager || true
  fail "Athan Hub did not become healthy"
fi

printf 'version=2.0.0\nrepository=%s\nbranch=%s\nservice_user=%s\ninstalled_at=%s\n' \
  "$REPOSITORY" "$BRANCH" "$SERVICE_USER" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$CONFIG_ROOT/installed"
chmod 0644 "$CONFIG_ROOT/installed"

host_now="$(hostname)"
log "Athan Hub installation complete"
printf 'Dashboard: http://%s.local\n' "$host_now"
if [[ -n "$generated_pin" ]]; then
  printf 'Dashboard PIN: %s (save this now; it is stored root-only in %s/athan-hub.env)\n' "$generated_pin" "$CONFIG_ROOT"
elif [[ -z "$dashboard_pin" ]]; then
  printf 'Dashboard PIN protection: disabled\n'
else
  printf 'Dashboard PIN protection: enabled\n'
fi
printf 'Next: open Admin to upload a timetable and MP3, pair a Bluetooth speaker, and create child profiles.\n'
printf 'Diagnostics: sudo athan-hub-doctor\n'
