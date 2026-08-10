#!/usr/bin/env bash
set -u

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

check "API service" systemctl is-active --quiet athan-hub-api.service
check "Scheduler service" systemctl is-active --quiet athan-hub-scheduler.service
check "Nginx service" systemctl is-active --quiet nginx.service
check "Bluetooth service" systemctl is-active --quiet bluetooth.service
check "mDNS service" systemctl is-active --quiet avahi-daemon.service
check "Local API health" curl -fsS http://127.0.0.1:9000/api/health
check "Web dashboard" curl -fsS http://127.0.0.1/
check "Bluetooth adapter" bluetoothctl show

if [[ -r /etc/athan-hub/athan-hub.env ]]; then
  service_user="$(stat -c '%U' /opt/athan-hub 2>/dev/null || printf athan)"
  service_uid="$(id -u "$service_user" 2>/dev/null || true)"
  if [[ -n "$service_uid" ]]; then
    check "User audio server" runuser -u "$service_user" -- env XDG_RUNTIME_DIR="/run/user/$service_uid" PULSE_SERVER="unix:/run/user/$service_uid/pulse/native" pactl info
  fi
fi

printf '\nDashboard: http://%s.local\n' "$(hostname)"
if ((failures)); then
  printf '%d check(s) failed. Inspect logs with: journalctl -u athan-hub-api -u athan-hub-scheduler -n 100\n' "$failures" >&2
  exit 1
fi
printf 'Athan Hub is healthy.\n'
