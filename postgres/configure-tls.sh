#!/bin/sh
set -eu

cat > "${PGDATA}/pg_hba.conf" <<'EOF'
local all all trust
hostssl all all 0.0.0.0/0 md5
hostssl all all ::/0 md5
hostnossl all all 0.0.0.0/0 reject
hostnossl all all ::/0 reject
EOF
