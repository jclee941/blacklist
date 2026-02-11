# 🛡️ Blacklist Intelligence Platform

[![CI](https://github.com/jclee-homelab/blacklist/actions/workflows/ci.yml/badge.svg)](https://github.com/jclee-homelab/blacklist/actions/workflows/ci.yml)
[![GitHub Release](https://img.shields.io/github/v/release/jclee-homelab/blacklist)](https://github.com/jclee-homelab/blacklist/releases/latest)
[![Docker](https://img.shields.io/badge/Docker-5%20Services-blue)](#architecture)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Wiki](https://img.shields.io/badge/Docs-Wiki-orange)](https://github.com/jclee-homelab/blacklist/wiki)

Threat intelligence platform for collecting, managing, and analyzing IP blacklist data from the **Korean Financial Security Institute (REGTECH)**.

## Features

| Feature | Description |
|---------|-------------|
| **REGTECH Integration** | Automated data collection from Korean Financial Security Institute |
| **Real-time Dashboard** | Next.js 15 frontend with live metrics and FortiGate logs |
| **FortiGate Integration** | Direct push to FortiManager address objects and policies |
| **Air-Gap Deployment** | Self-contained Docker bundles for offline environments |
| **Auto-Deploy (Sandbox)** | Watchtower-based auto-pull from GHCR on `:latest` tag |
| **Secure Credentials** | AES-256-GCM encrypted authentication |

## Quick Start

### Download & Install (Air-Gap)

```bash
# GitHub CLI
gh release download --repo jclee-homelab/blacklist
tar -xzf blacklist-*.tar.gz && ./install.sh

# curl (auto-detect latest)
TAG=$(curl -s "https://api.github.com/repos/jclee-homelab/blacklist/releases/latest" | grep "tag_name" | sed -E 's/.*"([^"]+)".*/\1/')
curl -#L "https://github.com/jclee-homelab/blacklist/releases/download/$TAG/blacklist-$TAG-airgap.tar.gz" -o "blacklist-$TAG-airgap.tar.gz"
```

### Development

```bash
make dev          # Start all services (hot reload)
make test         # Run all tests (backend + frontend)
make logs         # View logs
make down         # Stop services
```

## Architecture

```
blacklist-frontend   (Next.js 15)        :443 (SSL)
blacklist-app        (Flask API)         :2542
blacklist-collector  (REGTECH ETL)       :8545
blacklist-postgres   (PostgreSQL 16)     :5432
blacklist-redis      (Redis 7)           :6379
```

## CI/CD Pipeline

```
Push/PR → ci.yml (lint + test + build + e2e)
Tag v* → release.yml (build → airgap bundle → GitHub Release → GHCR push)
```

### Deployment Targets

| Environment | Method | Trigger |
|-------------|--------|---------|
| **Production** | Air-gap bundle (`docker load`) | Manual (deploy.yml) |
| **Sandbox** | Watchtower auto-pull from GHCR | Automatic on `:latest` push |

### Auto-Deploy Flow (Sandbox)

```
Tag push → release.yml → GHCR :latest → Watchtower (5min poll) → auto pull & restart
```

Watchtower monitors `collector`, `app`, `frontend` images. Postgres and Redis are excluded (label-filtered).

## API

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /api/stats` | Dashboard statistics |
| `GET /api/blacklist/list` | Paginated blacklist data |
| `GET /api/collection/status` | Collector status |

Full documentation: [API Reference](https://github.com/jclee-homelab/blacklist/wiki/API-Reference)

## Documentation

- [Installation Guide](https://github.com/jclee-homelab/blacklist/wiki/Installation)
- [Air-Gap Deployment](https://github.com/jclee-homelab/blacklist/wiki/Air-Gap-Deployment)
- [Development Guide](https://github.com/jclee-homelab/blacklist/wiki/Development)
- [Configuration](https://github.com/jclee-homelab/blacklist/wiki/Configuration)
- [Troubleshooting](https://github.com/jclee-homelab/blacklist/wiki/Troubleshooting)

## Version

**v3.5.57** (February 2026) - Production Stable

[Releases](https://github.com/jclee-homelab/blacklist/releases) · [Changelog](CHANGELOG.md)
