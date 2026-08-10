#!/usr/bin/env bash
set -euo pipefail

sudo systemctl restart athan-hub-api.service athan-hub-scheduler.service nginx.service
sudo systemctl --no-pager --full status athan-hub-api.service athan-hub-scheduler.service nginx.service
