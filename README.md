# Blacklist Intelligence Platform

[![CI](https://github.com/qws941/blacklist/actions/workflows/ci.yml/badge.svg)](https://github.com/qws941/blacklist/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/qws941/blacklist)](https://github.com/qws941/blacklist/releases/latest)
[![Tests](https://img.shields.io/badge/Tests-992%2B%20passing-brightgreen)](#testing)
[![Docker](https://img.shields.io/badge/Docker-5%20Services-blue)](#architecture)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

Threat intelligence platform for collecting, managing, and analyzing IP blacklist data from **REGTECH** (Korean Financial Security Institute) and **Secudium/ISAP** (SK Shielders).

## Features

| Feature | Description |
|---------|-------------|
| **Multi-Source Collection** | Automated ETL from REGTECH and Secudium/ISAP threat feeds |
| **Real-time Dashboard** | Next.js 15 frontend with live metrics, analytics, and FortiGate logs |
| **FortiGate Integration** | Direct push to FortiManager address objects and policies |
| **Offline Deployment** | Self-contained Docker bundles for offline environments |
| **Secure Credentials** | AES-256-GCM encrypted authentication |
| **992+ Automated Tests** | Backend (pytest), Frontend (vitest), E2E (Playwright) |

## Architecture

| Service | Technology | Port | Storage |
|---------|-----------|------|---------|
| `blacklist-frontend` | Next.js 15 (standalone, SSL embedded) | 443 | — |
| `blacklist-app` | Flask API (Raw SQL, DI) | 2542 | `blacklist-app-data` |
| `blacklist-collector` | Python 3.11 ETL | 8545 | `blacklist-collector-data` |
| `blacklist-postgres` | PostgreSQL 15 | 5432 | `blacklist-pgdata` |
| `blacklist-redis` | Redis 7 Alpine | 6379 | `blacklist-redis-data` |

All services use `network_mode: host` and Docker named volumes for persistent storage.

## Quick Start

### Development

```bash
make dev          # Start all services (hot reload)
make test         # Run all tests (backend + frontend)
make logs         # View logs
make down         # Stop services
```

### Offline Install

```bash
# Download latest release
gh release download --repo qws941/blacklist
tar -xzf blacklist-*.tar.gz && ./install.sh
```

## Project Structure

```
blacklist/
├── app/                    # Flask API (Manual DI, Raw SQL)        :2542
│   ├── core/services/      # 14 services (ServiceFactory DI)
│   ├── core/routes/        # REST API + Web admin (Korean UI)
│   └── core/auth/          # JWT authentication
├── collector/              # ETL Service (independent)             :8545
│   └── core/               # REGTECH + Secudium collectors
├── frontend/               # Next.js 15 Dashboard                  :443
│   ├── app/                # App Router pages
│   ├── lib/api.ts          # Centralized API client
│   └── e2e/                # Playwright E2E tests
├── deploy/
│   ├── docker-compose.yml  # Development compose (named volumes)
│   └── base.yml            # Shared service definitions
├── postgres/migrations/    # Raw SQL migrations (no ORM)
└── tests/                  # Backend tests (pytest)
```

## Testing

| Type | Framework | Files | Tests |
|------|-----------|-------|-------|
| Backend Unit | pytest | 107 | 785+ |
| Frontend Unit | Vitest | 44 | 207+ |
| E2E | Playwright | — | Chromium |
| **Total** | — | **151+** | **992+** |

```bash
make test                   # All tests
make test-backend-unit      # Backend only (pytest)
make test-backend-coverage  # Backend with coverage (≥80% required)
make test-frontend-unit     # Frontend only (vitest)
make test-e2e               # E2E (Playwright)
```

## CI/CD Pipeline

| Workflow | Trigger | Purpose |
|----------|---------|--------|
| `ci.yml` | Push/PR to master | Lint → Test → Build → E2E → Push images |
| `release.yml` | Tag `v*` | Build 5 images → Release bundle → GitHub Release → GHCR |

### Deployment Targets

| Environment | Method | Trigger |
|-------------|--------|--------|
| **Production** | Offline bundle (`docker load`) | Manual |

## API

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /api/stats` | Dashboard statistics |
| `GET /api/blacklist/list` | Paginated blacklist data |
| `GET /api/collection/status` | Collector status |

## Documentation
| Document | Path |
|----------|------|
| **Documentation Hub** | [`docs/README.md`](docs/README.md) |
| Developer Guide | [`AGENTS.md`](AGENTS.md) |
| System Architecture | [`docs/wiki/Architecture.md`](docs/wiki/Architecture.md) |
| API Reference | [`docs/wiki/API-Reference.md`](docs/wiki/API-Reference.md) |
| CI/CD Pipeline | [`docs/CICD_PIPELINE.md`](docs/CICD_PIPELINE.md) |
| Deployment Guide | [`docs/wiki/Deployment-Guide.md`](docs/wiki/Deployment-Guide.md) |

## Version

**v3.6.4** (February 2026) — Production Stable

[Releases](https://github.com/qws941/blacklist/releases) · [Changelog](CHANGELOG.md)
