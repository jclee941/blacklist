#!/bin/sh
set -e
SSL_DIR="/app/ssl"
SSL_KEY="${SSL_KEY_PATH:-$SSL_DIR/server.key}"
SSL_CERT="${SSL_CERT_PATH:-$SSL_DIR/server.crt}"
TLS_MODE="${FRONTEND_TLS_MODE:-}"
TLS_SERVER_NAME="${FRONTEND_TLS_SERVER_NAME:-}"

if [ "$TLS_MODE" = "provided" ]; then
  if [ ! -r "$SSL_KEY" ] || [ ! -r "$SSL_CERT" ]; then
    echo "ERROR: FRONTEND_TLS_MODE=provided requires readable server.key and server.crt in $SSL_DIR" >&2
    exit 1
  fi
  if [ -z "$TLS_SERVER_NAME" ]; then
    echo "ERROR: FRONTEND_TLS_SERVER_NAME is required in provided mode" >&2
    exit 1
  fi
  if ! openssl x509 -in "$SSL_CERT" -noout -checkend 0 >/dev/null 2>&1; then
    echo "ERROR: provided frontend TLS certificate is invalid or expired" >&2
    exit 1
  fi
  CERT_PUBLIC_KEY=$(openssl x509 -in "$SSL_CERT" -pubkey -noout | openssl pkey -pubin -outform pem | sha256sum | cut -d' ' -f1)
  KEY_PUBLIC_KEY=$(openssl pkey -in "$SSL_KEY" -pubout -outform pem | sha256sum | cut -d' ' -f1)
  if [ "$CERT_PUBLIC_KEY" != "$KEY_PUBLIC_KEY" ]; then
    echo "ERROR: frontend TLS certificate and private key do not match" >&2
    exit 1
  fi
  case "$TLS_SERVER_NAME" in
    *[!0-9a-fA-F:.]*)
      openssl x509 -in "$SSL_CERT" -noout -checkhost "$TLS_SERVER_NAME" >/dev/null 2>&1 || {
        echo "ERROR: frontend TLS certificate does not cover host $TLS_SERVER_NAME" >&2
        exit 1
      }
      ;;
    *)
      openssl x509 -in "$SSL_CERT" -noout -checkip "$TLS_SERVER_NAME" >/dev/null 2>&1 || {
        echo "ERROR: frontend TLS certificate does not cover IP $TLS_SERVER_NAME" >&2
        exit 1
      }
      ;;
  esac
elif [ "$TLS_MODE" = "self-signed" ]; then
  if { [ -f "$SSL_KEY" ] && [ ! -f "$SSL_CERT" ]; } || { [ ! -f "$SSL_KEY" ] && [ -f "$SSL_CERT" ]; }; then
    echo "ERROR: self-signed frontend TLS requires both server.key and server.crt or neither" >&2
    exit 1
  fi
  if [ -f "$SSL_KEY" ] && ! openssl x509 -in "$SSL_CERT" -noout -ext subjectAltName 2>/dev/null | grep -q "DNS:localhost"; then
    echo "ERROR: refusing to overwrite a non-localhost certificate in self-signed mode" >&2
    exit 1
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
  if ! openssl x509 -in "$SSL_CERT" -noout -checkend 0 >/dev/null 2>&1; then
    echo "ERROR: self-signed frontend TLS certificate is invalid or expired" >&2
    exit 1
  fi
else
  echo "ERROR: FRONTEND_TLS_MODE must be either provided or self-signed" >&2
  exit 1
fi

exec node server.js
