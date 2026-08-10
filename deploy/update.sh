#!/usr/bin/env bash
set -Eeuo pipefail

REPOSITORY="${ATHAN_REPOSITORY:-oashaikh/athan-hub}"
BRANCH="${ATHAN_BRANCH:-main}"
INSTALLER_URL="https://raw.githubusercontent.com/${REPOSITORY}/${BRANCH}/install.sh"

[[ $EUID -eq 0 ]] || { echo "Run with sudo: sudo athan-hub-update" >&2; exit 1; }
curl -fsSL "$INSTALLER_URL" | bash -s -- --branch "$BRANCH" --keep-hostname
