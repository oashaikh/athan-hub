#!/usr/bin/env bash
set -Eeuo pipefail

readonly CONFIG_FILE="/etc/athan-hub/athan-hub.env"
readonly INSTALL_STATE="/etc/athan-hub/installed"
failures=0

check() {
  local label="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    printf 'PASS  %s\n' "$label"
  else
    printf 'FAIL  %s\n' "$label"
    failures=$((failures + 1))
  fi
}

value_from_file() {
  local file="$1" key="$2" fallback="$3" value
  value="$(sed -n "s/^${key}=//p" "$file" 2>/dev/null | head -n 1)"
  printf '%s' "${value:-$fallback}"
}

service_user="$(value_from_file "$INSTALL_STATE" service_user athan)"
data_root="$(value_from_file "$CONFIG_FILE" ATHAN_DATA_DIR /var/lib/athan-hub)"
database_path="$(value_from_file "$CONFIG_FILE" ATHAN_DB_PATH "$data_root/athan.db")"
cache_path="$(value_from_file "$CONFIG_FILE" ATHAN_QURAN_CACHE_DIR "$data_root/quran-cache")"
resource_db="$(value_from_file "$CONFIG_FILE" ATHAN_QURAN_RESOURCE_DB /opt/athan-hub/resources/quran/quran.sqlite)"
resource_manifest="$(value_from_file "$CONFIG_FILE" ATHAN_QURAN_MANIFEST_PATH /opt/athan-hub/resources/quran/manifest.json)"
service_uid="$(id -u "$service_user" 2>/dev/null || true)"
python_path="/opt/athan-hub/backend/venv/bin/python"

check_quran_resources() {
  runuser -u "$service_user" -- "$python_path" - "$resource_db" "$resource_manifest" <<'PY'
import sys
from pathlib import Path
from athan_hub.core.quran_resources import QuranResources

resources = QuranResources(Path(sys.argv[1]), Path(sys.argv[2]))
surahs = resources.list_surahs()
if len(surahs) != 114 or sum(row["ayah_count"] for row in surahs) != 6236:
    raise SystemExit(1)
if not resources.list_recitations():
    raise SystemExit(1)
PY
}

check_audio_durations() {
  "$python_path" - "$database_path" <<'PY'
import sqlite3
import sys

with sqlite3.connect(sys.argv[1]) as connection:
    missing = connection.execute(
        "SELECT COUNT(*) FROM audio_profiles WHERE enabled = 1 AND "
        "(duration_seconds IS NULL OR duration_seconds <= 0)"
    ).fetchone()[0]
raise SystemExit(1 if missing else 0)
PY
}

check_cache_headroom() {
  "$python_path" - "$database_path" "$cache_path" <<'PY'
import shutil
import sqlite3
import sys
from pathlib import Path

database, cache = sys.argv[1], Path(sys.argv[2])
with sqlite3.connect(database) as connection:
    row = connection.execute(
        "SELECT value FROM settings WHERE key = 'quran_cache_limit_bytes'"
    ).fetchone()
    limit = int(row[0]) if row else 5 * 1024 * 1024 * 1024
    used = connection.execute(
        "SELECT COALESCE(SUM(byte_count), 0) FROM quran_audio_cache"
    ).fetchone()[0]
free = shutil.disk_usage(cache).free
minimum_free = min(256 * 1024 * 1024, max(32 * 1024 * 1024, limit // 20))
raise SystemExit(0 if used <= limit and free >= minimum_free else 1)
PY
}

check "Configuration file" test -r "$CONFIG_FILE"
check "Service account" id "$service_user"
check "API service" systemctl is-active --quiet athan-hub-api.service
check "Scheduler service" systemctl is-active --quiet athan-hub-scheduler.service
check "Nginx service" systemctl is-active --quiet nginx.service
check "Bluetooth service" systemctl is-active --quiet bluetooth.service
check "mDNS service" systemctl is-active --quiet avahi-daemon.service
check "Local API health" curl --max-time 10 -fsS http://127.0.0.1:9000/api/health
check "Web dashboard" curl --max-time 10 -fsS http://127.0.0.1/
check "Quran resources API" curl --max-time 10 -fsS http://127.0.0.1:9000/api/quran/surahs
check "Quran reciter catalogue" curl --max-time 10 -fsS http://127.0.0.1:9000/api/quran/recitations
check "Quran resource checksum and counts" check_quran_resources
check "Quran cache writable" runuser -u "$service_user" -- test -w "$cache_path"
check "Runtime state writable" runuser -u "$service_user" -- test -w /run/athan-hub
check "Enabled Athan audio durations" check_audio_durations
check "Quran cache and disk headroom" check_cache_headroom
check "Bluetooth adapter" timeout 10s bluetoothctl show

if [[ -n "$service_uid" ]]; then
  check "User audio server" timeout 10s runuser -u "$service_user" -- env \
    XDG_RUNTIME_DIR="/run/user/$service_uid" \
    PULSE_SERVER="unix:/run/user/$service_uid/pulse/native" pactl info
fi

printf '\nDashboard: http://%s.local\n' "$(hostname)"
if ((failures)); then
  printf '%d check(s) failed. Inspect logs with: journalctl -u athan-hub-api -u athan-hub-scheduler -n 100\n' "$failures" >&2
  exit 1
fi
printf 'Athan Hub is healthy.\n'
