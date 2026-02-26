#!/bin/bash
#
# Blacklist Collector Entrypoint
# ================================
# Loads secrets from shared volume, then starts collector
#

set -eo pipefail

echo "========================================="
echo "Blacklist Collector Entrypoint"
echo "========================================="

# --- Load secrets from shared volume ---
if [ -f /app/init-secrets.sh ]; then
    echo "Loading secrets..."
    source /app/init-secrets.sh
fi

echo "Starting collector..."
exec python -m collector.run_collector
