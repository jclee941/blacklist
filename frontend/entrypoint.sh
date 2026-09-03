#!/bin/sh
set -e
SSL_DIR="/app/ssl"
SSL_KEY="${SSL_KEY_PATH:-$SSL_DIR/server.key}"
SSL_CERT="${SSL_CERT_PATH:-$SSL_DIR/server.crt}"
TLS_MODE="${FRONTEND_TLS_MODE:-}"

if [ "$TLS_MODE" = "provided" ]; then
  if [ ! -r "$SSL_KEY" ] || [ ! -r "$SSL_CERT" ]; then
    echo "ERROR: FRONTEND_TLS_MODE=provided requires readable server.key and server.crt in $SSL_DIR" >&2
    exit 1
  fi
elif [ "$TLS_MODE" = "self-signed" ]; then
  if [ -f "$SSL_KEY" ] && [ -f "$SSL_CERT" ] && \
     ! openssl x509 -in "$SSL_CERT" -noout -ext subjectAltName 2>/dev/null | grep -q "DNS:localhost"; then
    rm -f "$SSL_KEY" "$SSL_CERT"
  fi
  if [ ! -f "$SSL_KEY" ] || [ ! -f "$SSL_CERT" ]; then
  echo "> Generating self-signed SSL certificate..."
  mkdir -p "$SSL_DIR"
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$SSL_KEY" \
    -out "$SSL_CERT" \
    -subj "/CN=localhost/O=Blacklist/C=KR" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
  chmod 600 "$SSL_KEY"
  echo "> Persisted self-signed SSL certificate generated"
  fi
else
  echo "ERROR: FRONTEND_TLS_MODE must be either provided or self-signed" >&2
  exit 1
fi

exec node server.js
