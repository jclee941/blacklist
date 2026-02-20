#!/bin/bash
#
# Blacklist Application Entrypoint
# =================================
# Waits for dependencies (PostgreSQL, Redis) then starts Flask app
#
# Version: 3.6.4
# Date: 2026-02-20

set -eo pipefail

# Color codes
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
NC=$'\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Blacklist Application Entrypoint${NC}"
echo -e "${BLUE}========================================${NC}"

# --- Wait for PostgreSQL ---
echo -e "${BLUE}Waiting for PostgreSQL (${POSTGRES_HOST:-localhost}:${POSTGRES_PORT:-5432})...${NC}"
for i in $(seq 1 30); do
    if python -c "
import socket, os, sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    s.connect((os.environ.get('POSTGRES_HOST', 'localhost'), int(os.environ.get('POSTGRES_PORT', '5432'))))
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; then
        echo -e "${GREEN}\u2705 PostgreSQL is ready${NC}"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo -e "${RED}\u274c PostgreSQL not ready after 60s${NC}"
        exit 1
    fi
    sleep 2
done

# --- Wait for Redis ---
echo -e "${BLUE}Waiting for Redis (${REDIS_HOST:-localhost}:${REDIS_PORT:-6379})...${NC}"
for i in $(seq 1 15); do
    if python -c "
import socket, os, sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    s.connect((os.environ.get('REDIS_HOST', 'localhost'), int(os.environ.get('REDIS_PORT', '6379'))))
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; then
        echo -e "${GREEN}\u2705 Redis is ready${NC}"
        break
    fi
    if [ "$i" -eq 15 ]; then
        echo -e "${YELLOW}\u26a0\ufe0f  Redis not ready after 30s, continuing anyway...${NC}"
        break
    fi
    sleep 2
done

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}\U0001f680 Starting Flask application...${NC}"
echo -e "${BLUE}========================================${NC}"

# Start Flask application
exec python run_app.py
