#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash scripts/setup_cron.sh /path/to/repo /path/to/python /path/to/logfile
# Example:
#   bash scripts/setup_cron.sh /opt/b2b-growth /opt/b2b-growth/.venv/bin/python /var/log/b2b_retry.log

REPO_DIR=${1:-$(pwd)}
PYTHON_BIN=${2:-python}
LOG_FILE=${3:-/tmp/b2b_retry_worker.log}

CRON_LINE="*/10 * * * * cd ${REPO_DIR} && ${PYTHON_BIN} -m app.workers.retry_worker --limit 20 --delay-minutes 10 >> ${LOG_FILE} 2>&1"

( crontab -l 2>/dev/null | grep -v 'app.workers.retry_worker' ; echo "$CRON_LINE" ) | crontab -

echo "Installed cron job:"
echo "$CRON_LINE"
