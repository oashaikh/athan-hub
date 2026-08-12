#!/usr/bin/env bash
set -Eeuo pipefail

destination="${1:-$PWD}"
install -d -m 0755 "$destination"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
archive="$destination/athan-hub-backup-$stamp.tar.gz"
tar -C / --exclude='var/lib/athan-hub/quran-cache' -czf "$archive" var/lib/athan-hub etc/athan-hub
chmod 0600 "$archive"
printf 'Backup created: %s\n' "$archive"
