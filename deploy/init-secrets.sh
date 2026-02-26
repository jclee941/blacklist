#!/bin/bash
# init-secrets.sh — Auto-generate and persist secrets to shared volume
# Sourced by app and collector entrypoints on container startup
#
# Secrets are persisted to /secrets/.secrets.env (Docker named volume).
# On first startup, generates cryptographic keys. On subsequent startups,
# sources existing keys. Race condition between app and collector handled
# via atomic mkdir lock.

SECRETS_FILE="/secrets/.secrets.env"

if [ ! -f "$SECRETS_FILE" ]; then
    # Atomic lock via mkdir to prevent race between app and collector
    if mkdir /secrets/.secrets.lock 2>/dev/null; then
        if [ ! -f "$SECRETS_FILE" ]; then
            echo "Generating secrets..."
            _mk=$(python3 -c "import secrets; print(secrets.token_hex(32))")
            _sk=$(python3 -c "import secrets; print(secrets.token_hex(32))")
            _ek=$(python3 -c "import base64,os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())")
            printf 'CREDENTIAL_MASTER_KEY=%s\nSECRET_KEY=%s\nCREDENTIAL_ENCRYPTION_KEY=%s\n' \
                "$_mk" "$_sk" "$_ek" > "$SECRETS_FILE"
            chmod 644 "$SECRETS_FILE"
            echo "Secrets persisted to ${SECRETS_FILE}"
        fi
        rmdir /secrets/.secrets.lock 2>/dev/null || true
    else
        echo "Waiting for secrets..."
        for _i in $(seq 1 30); do
            [ -f "$SECRETS_FILE" ] && break
            sleep 1
        done
    fi
fi

if [ -f "$SECRETS_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$SECRETS_FILE"
    set +a
else
    echo "ERROR: Secrets file not available at ${SECRETS_FILE}"
fi

unset _mk _sk _ek _i SECRETS_FILE
