#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   sudo bash scripts/install_systemd_retry_worker.sh /opt/b2b-growth /opt/b2b-growth/.venv/bin/python

REPO_DIR=${1:-/opt/b2b-growth}
PYTHON_BIN=${2:-$REPO_DIR/.venv/bin/python}
SERVICE_NAME=b2b-retry-worker

SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
TIMER_FILE="/etc/systemd/system/${SERVICE_NAME}.timer"

cat > /tmp/${SERVICE_NAME}.service <<SERVICE
[Unit]
Description=B2B Growth Retry Worker (WeChat publish retries)
After=network.target

[Service]
Type=oneshot
WorkingDirectory=${REPO_DIR}
ExecStart=${PYTHON_BIN} -m app.workers.retry_worker --limit 20 --delay-minutes 10
EnvironmentFile=-${REPO_DIR}/.env
SERVICE

cat > /tmp/${SERVICE_NAME}.timer <<TIMER
[Unit]
Description=Run B2B Growth Retry Worker every 10 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=10min
Unit=${SERVICE_NAME}.service
Persistent=true

[Install]
WantedBy=timers.target
TIMER

sudo cp /tmp/${SERVICE_NAME}.service "${SERVICE_FILE}"
sudo cp /tmp/${SERVICE_NAME}.timer "${TIMER_FILE}"
sudo systemctl daemon-reload
sudo systemctl enable --now ${SERVICE_NAME}.timer

echo "Installed ${SERVICE_NAME}.service and ${SERVICE_NAME}.timer"
sudo systemctl status ${SERVICE_NAME}.timer --no-pager || true
