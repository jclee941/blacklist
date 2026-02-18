#!/usr/bin/env bash
set -euo pipefail

: "${VERSION:?VERSION is required}"
: "${DEPLOY_BASE:=/opt/blacklist}"
: "${REGISTRY:=ghcr.io}"
: "${REPO:?REPO is required (e.g. qws941/blacklist)}"
: "${GHCR_PAT:=}"
: "${GHCR_USER:=}"

DEPLOY_DIR="${DEPLOY_BASE}/blacklist-v${VERSION}"

echo "=== Deploying Blacklist v${VERSION} (GHCR Pull) ==="

if [ -n "${GHCR_PAT}" ] && [ -n "${GHCR_USER}" ]; then
  echo "${GHCR_PAT}" | sudo docker login "${REGISTRY}" -u "${GHCR_USER}" --password-stdin
fi

echo "📥 Pulling :latest images from GHCR..."
for svc in postgres redis collector app frontend; do
  IMAGE="${REGISTRY}/${REPO}/blacklist-${svc}:latest"
  echo "  Pulling ${IMAGE}..."
  sudo docker pull "${IMAGE}"
done

PREV_DIR=""
if [ -L "${DEPLOY_BASE}/current" ]; then
  RESOLVED=$(readlink -f "${DEPLOY_BASE}/current" 2>/dev/null || echo "")
  if [ -n "${RESOLVED}" ] && [ "${RESOLVED}" != "${DEPLOY_DIR}" ]; then
    PREV_DIR="${RESOLVED}"
  fi
elif [ -d "${DEPLOY_BASE}/current" ]; then
  PREV_DIR="${DEPLOY_BASE}/current"
fi
if [ -z "${PREV_DIR}" ]; then
  PREV_DIR=$(ls -dt "${DEPLOY_BASE}"/blacklist-v*/ 2>/dev/null | grep -v "blacklist-v${VERSION}/" | head -1 | sed 's:/$::')
fi
echo "📂 Previous deployment: ${PREV_DIR:-none}"

if [ -n "${PREV_DIR}" ] && [ "${PREV_DIR}" != "${DEPLOY_DIR}" ] && [ -f "${PREV_DIR}/.env" ]; then
  echo "🔒 Preserving .env from ${PREV_DIR}"
  sudo cp "${PREV_DIR}/.env" "${DEPLOY_DIR}/.env"
elif [ -f "${DEPLOY_BASE}/env-backup-latest.env" ]; then
  echo "🔒 Restoring .env from backup"
  sudo cp "${DEPLOY_BASE}/env-backup-latest.env" "${DEPLOY_DIR}/.env"
fi

if [ ! -f "${DEPLOY_DIR}/.env" ] || [ ! -s "${DEPLOY_DIR}/.env" ]; then
  echo "⚠️  No .env found — generating secrets..."
  sudo bash -c "printf '%s\n' 'FLASK_ENV=production' 'POSTGRES_PASSWORD=blacklist' 'POSTGRES_HOST=localhost' 'REDIS_HOST=localhost' 'REDIS_PORT=6379' > ${DEPLOY_DIR}/.env"
  sudo sh -c "echo \"CREDENTIAL_MASTER_KEY=\$(openssl rand -hex 32)\" >> ${DEPLOY_DIR}/.env"
  sudo sh -c "echo \"SECRET_KEY=\$(openssl rand -hex 32)\" >> ${DEPLOY_DIR}/.env"
  sudo sh -c "echo \"CREDENTIAL_ENCRYPTION_KEY=\$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())' 2>/dev/null || openssl rand -base64 32)\" >> ${DEPLOY_DIR}/.env"
  sudo sh -c "echo \"ENCRYPTION_SALT=\$(openssl rand -hex 16)\" >> ${DEPLOY_DIR}/.env"
  echo "✅ .env generated with fresh secrets"
fi

sudo cp "${DEPLOY_DIR}/.env" "${DEPLOY_BASE}/env-backup-latest.env"

for asset in data ssl; do
  if [ -n "${PREV_DIR}" ] && [ "${PREV_DIR}" != "${DEPLOY_DIR}" ] && [ -d "${PREV_DIR}/${asset}" ]; then
    echo "💾 Preserving ${asset} from ${PREV_DIR}..."
    sudo cp -a "${PREV_DIR}/${asset}" "${DEPLOY_DIR}/${asset}" 2>/dev/null || true
  fi
done

if [ -n "${PREV_DIR}" ] && [ "${PREV_DIR}" != "${DEPLOY_DIR}" ] && [ -f "${PREV_DIR}/docker-compose.yml" ]; then
  echo "⏹️  Stopping existing containers..."
  cd "${PREV_DIR}"
  sudo docker compose down --timeout 30 2>/dev/null || true
fi

for svc in app collector frontend postgres redis; do
  sudo docker rm -f "blacklist-${svc}" 2>/dev/null || true
done

cd "${DEPLOY_DIR}"
sudo touch .env
sudo chown "$(whoami):$(whoami)" .env
if ! grep -q "GITHUB_REPOSITORY" .env 2>/dev/null; then
  echo "" >> .env
  echo "GITHUB_REPOSITORY=${REPO}" >> .env
fi
sed -i '/^VERSION=/d' .env 2>/dev/null || true
sed -i '/^REGISTRY=/d' .env 2>/dev/null || true
echo "REGISTRY=${REGISTRY}" >> .env

echo "🚀 Starting services..."
sudo docker compose up -d

sudo ln -sfn "${DEPLOY_DIR}" "${DEPLOY_BASE}/current"

echo "✅ Containers started"
sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}' | grep blacklist || true
