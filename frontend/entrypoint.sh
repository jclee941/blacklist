#!/bin/sh
set -e
# Generate self-signed SSL certificate at runtime if none exists.
# This avoids baking private keys into Docker image layers.

SSL_DIR="/app/ssl"
SSL_KEY="${SSL_KEY_PATH:-$SSL_DIR/server.key}"
SSL_CERT="${SSL_CERT_PATH:-$SSL_DIR/server.crt}"

if [ ! -f "$SSL_KEY" ] || [ ! -f "$SSL_CERT" ]; then
  echo "> Generating self-signed SSL certificate..."
  mkdir -p "$SSL_DIR"
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$SSL_KEY" \
    -out "$SSL_CERT" \
    -subj "/CN=blacklist/O=Blacklist/C=KR"
  chmod 600 "$SSL_KEY"
  echo "> SSL certificate generated: $SSL_KEY, $SSL_CERT"
fi

exec node server.js
