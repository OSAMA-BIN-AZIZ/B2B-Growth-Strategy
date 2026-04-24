#!/usr/bin/env bash
set -euo pipefail
python -m app.workers.retry_worker --limit 20 --delay-minutes 10
