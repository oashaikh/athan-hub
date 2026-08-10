#!/usr/bin/env bash
set -Eeuo pipefail

purge=0
[[ "${1:-}" == "--purge" ]] && purge=1
[[ $EUID -eq 0 ]] || { echo "Run with sudo: sudo athan-hub-uninstall" >&2; exit 1; }

service_user="athan"
if [[ -r /etc/athan-hub/installed ]]; then
  configured_user="$(sed -n 's/^service_user=//p' /etc/athan-hub/installed | head -n 1)"
  if [[ "$configured_user" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]]; then
    service_user="$configured_user"
  fi
fi

systemctl disable --now athan-hub-api.service athan-hub-scheduler.service 2>/dev/null || true
rm -f /etc/systemd/system/athan-hub-api.service /etc/systemd/system/athan-hub-scheduler.service
rm -f /etc/nginx/sites-enabled/athan-hub /etc/nginx/sites-available/athan-hub
for tool in athan-pair-speaker athan-hub-doctor athan-hub-update athan-hub-backup athan-hub-uninstall; do
  rm -f "/usr/local/bin/$tool"
done
rm -rf -- /opt/athan-hub
if [[ -e /etc/nginx/sites-available/default ]]; then
  ln -sfn /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default
fi
systemctl daemon-reload
if nginx -t >/dev/null 2>&1; then
  systemctl reload nginx.service || true
fi

if ((purge)); then
  rm -rf -- /var/lib/athan-hub /var/log/athan-hub /etc/athan-hub
  if id "$service_user" >/dev/null 2>&1; then
    loginctl disable-linger "$service_user" 2>/dev/null || true
    userdel "$service_user" 2>/dev/null || true
  fi
  echo "Athan Hub and all data were permanently removed."
else
  echo "Athan Hub was removed. Data and configuration remain in /var/lib/athan-hub and /etc/athan-hub."
  echo "Run with --purge only if you also want to permanently delete timetable, audio, history, and settings."
fi
