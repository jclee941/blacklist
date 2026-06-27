# Blacklist Service Management

> 통합 위협 인텔리전스 수집·동기화·블랙리스트 중앙 관리·Fortinet 자동 배포 플랫폼
> Unified threat-intelligence aggregation, centralized blacklist management, and Fortinet deployment platform.

---

## Table of Contents / 목차

- [한국어](#한국어)
  - [개요](#개요)
  - [주요 기능](#주요-기능)
  - [아키텍처](#아키텍처)
  - [빠른 시작](#빠른-시작)
  - [설정](#설정)
  - [명령어 레퍼런스](#명령어-레퍼런스)
  - [로컬 개발](#로컬-개발)
  - [테스트](#테스트)
  - [기여 가이드](#기여-가이드)
  - [라이선스](#라이선스)
- [English](#english)
  - [Overview](#overview)
  - [Features](#features)
  - [Architecture](#architecture)
  - [Quick Start](#quick-start)
  - [Configuration](#configuration)
  - [Commands Reference](#commands-reference)
  - [Local Development](#local-development)
  - [Testing](#testing)
  - [Contributing](#contributing)
  - [License](#license-1)
- [Repository Structure](#repository-structure)

---

## 한국어

### 개요

**Blacklist Service Management**는 다양한 외부 위협 인텔리전스 소스(악성 IP, 도메인, URL 등)에서 데이터를 수집·동기화하고, 중앙 집중식 블랙리스트로 통합 관리한 뒤 Fortinet 방화벽 등 외부 보안 장비로 자동 배포하는 Python 기반 통합 관리 플랫폼입니다. 웹 UI(Jinja2), REST API, WebSocket을 통해 실시간 모니터링과 운영 자동화를 제공합니다.

핵심 사용자:

- **보안 운영팀(SOC)** — 위협 인텔리전스 통합·자동 차단
- **네트워크 엔지니어** — Fortinet 등 외부 장비로의 정책/주소 객체 자동 배포
- **플랫폼 운영자** — 단일 콘솔에서 컬렉션·세션·통합·설정·모니터링 관리

기본 서비스 포트는 `2542`이며(`PORT` 환경 변수로 변경 가능), 기본 실행 환경은 `development`입니다. 진입점은 `app/run_app.py`이며, 컨테이너 환경에서는 `app/entrypoint.sh`가 이를 호출합니다. 배포 전 검증은 `app/deployment_validation.py`로 수행합니다.

### 주요 기능

- **중앙 집중식 블랙리스트 관리** — IP/도메인 블랙리스트 CRUD, 일괄 처리(batch), 외부 컬렉션과 동기화, 변경 이력 추적 (`app/core/routes/api/blacklist/`)
- **컬렉션 동기화** — 여러 위협 인텔리전스 소스에서 주기적/수동 데이터 수집, 히스토리 추적, 트리거 실행 (`app/core/routes/api/collection/`)
- **Fortinet 연동** — Fortinet 장비 등록(`fortinet_register.py`), 블랙리스트 항목의 정책/주소 객체 자동 배포(`fortinet/core.py`)
- **인증/인가** — JWT 기반 세션, 데코레이터·미들웨어 기반 라우트 보호, 역할 기반 접근 제어 (`app/core/auth/`)
- **모니터링/관측** — 캐시/에러/시스템 메트릭 수집, 대시보드, 구조화 로깅, 로그 로테이션 관리 (`app/core/monitoring/`, `app/utils/`)
- **REST API + WebSocket** — 도메인별 모듈화된 API, 실시간 이벤트 스트림 (`app/core/routes/api/`, `app/core/routes/websocket_routes.py`)
- **웹 UI** — Jinja2 기반 대시보드, 컬렉션, 세션, 통합, 설정, 모니터링 화면 (`app/templates/`)
- **마이그레이션/설정** — 데이터베이스 마이그레이션(`migration.py`), IP 관리 헬퍼, 시스템/설정 API
- **컨테이너 친화 배포** — Dockerfile, `deploy/docker-compose.yml` 기반 멀티 서비스 운영

### 아키텍처

```mermaid
flowchart LR
    subgraph Client["Browser / Operator"]
        UI["Web UI<br/>Jinja2 templates"]
    end

    subgraph Edge["Reverse Proxy / Ingress"]
        Proxy["nginx / TLS"]
    end

    subgraph App["Flask Application (app/run_app.py)"]
        Web["Web Routes<br/>web_routes.py"]
        API["REST API<br/>api_routes.py"]
        WS["WebSocket<br/>websocket_routes.py"]
        ProxyRoutes["Proxy Routes<br/>proxy_routes.py"]
        Sys["System Routes<br/>system_routes.py"]
    end

    subgraph Domain["Domain Modules"]
        Auth["auth/<br/>jwt_service, middleware, decorators"]
        Mon["monitoring/<br/>cache_metrics, error_metrics, metrics"]
        BL["blacklist/<br/>core, batch, management, system"]
        Coll["collection/<br/>sources, sync, trigger, history"]
        Forti["fortinet/<br/>core, register"]
        Dash["dashboard.py<br/>dashboard_api.py"]
    end

    subgraph Data["Persistence / State"]
        DB[("Database")]
        Logs[("Structured logs")]
        Cache[("Cache")]
    end

    subgraph Ext["External"]
        TI["Threat Intel Sources"]
        FW["Fortinet Firewalls"]
    end

    UI --&gt; Proxy --&gt; Web
    UI --&gt; Proxy --&gt; API
    UI --&gt; Proxy --&gt; WS
    API --&gt; Auth
    API --&gt; Mon
    API --&gt; BL
    API --&gt; Coll
    API --&gt; Forti
    API --&gt; Dash
    Web --&gt; Dash
    BL --&gt; DB
    Coll --&gt; TI
    Coll --&gt; DB
    Forti --&gt; FW
    Mon --&gt; Logs
    Mon --&gt; Cache
```

### 빠른 시작

요구 사항:

- Docker 및 Docker Compose v2
- Make
- (선택) Python 3.11 이상 — 컨테이너 없이 직접 실행 시

저장소 클론 후 환경 변수 파일을 준비합니다.

```bash
git clone <repository-url> blacklist-service
cd blacklist-service
cp deploy/.env.example deploy/.env   # 실제 환경에 맞게 값 수정
```

개발 환경 기동:

```bash
make dev          # 빌드 후 기동, 핫 리로드 활성화
# 또는
make dev-no-build # 기존 이미지 사용 (빠른 기동)
```

기동 후 접속:

- 웹 UI: `http://localhost:2542`
- API 베이스: `http://localhost:2542/api`
- 헬스 체크: `http://localhost:2542/health`

종료:

```bash
make down
```

### 설정

주요 환경 변수 (`deploy/.env`):

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `ENV` | 실행 환경 (`development` / `production`) | `development` |
| `PORT` | 서비스 포트 | `2542` |
| `JWT_SECRET` | JWT 서명 키 (필수, 운영 환경) | — |
| `DB_*` | 데이터베이스 접속 정보 | — |
| `FORTINET_*` | Fortinet 장비 등록 정보 | — |

인증·역할·라우트 보호 규칙은 `app/core/auth/` 하위 모듈에서 정의되며, 라우트별 권한은 `@require_auth` / `@require_role` 데코레이터로 제어합니다.

### 명령어 레퍼런스

`Makefile`은 다음 타겟을 제공합니다.

| 명령어 | 설명 |
|--------|------|
| `make help` | 사용 가능한 명령어 목록 출력 |
| `make setup-hooks` | Git 훅(pre-commit, commit-msg) 설치 |
| `make dev` | 개발 환경 기동(빌드 포함, 핫 리로드) |
| `make dev-no-build` | 개발 환경 기동(기존 이미지 사용) |
| `make dev-prod` | 프로덕션 유사 환경 기동(핫 리로드 없음) |
| `make dev-app` | app 서비스만 재시작 |
| `make build` | Docker 이미지 빌드 |
| `make up` | 컨테이너 기동 |
| `make down` | 컨테이너 종료 |
| `make restart` | 컨테이너 재시작 |
| `make logs` | 컨테이너 로그 스트림 |
| `make health` | 서비스 헬스 체크 |
| `make clean` | 로컬 캐시·중간 산출물 정리 |
| `make test` | 테스트 실행 |
| `make verify` | 검증 묶음 실행 (lint/type/secret/pre-commit) |
| `make verify-lint` | Ruff 린트 |
| `make verify-types` | mypy 타입 체크 |
| `make verify-secrets` | 시크릿 누출 점검 |
| `make verify-pre-commit` | pre-commit 훅 전체 실행 |
| `make verify-quick` | 빠른 검증 |
| `make verify-all` | 전체 검증 |
| `make deploy` | 배포 |
| `make prod` | 프로덕션 모드 기동 |
| `make release` | 릴리스 절차 실행 |
| `make release-dry` | 릴리스 절차 드라이 런 |

### 로컬 개발

코드 변경 사항은 볼륨 마운트를 통해 자동으로 컨테이너에 반영됩니다(개발 모드). 컨테이너 없이 실행하려면:

```bash
cd app
pip install -r requirements.txt
python run_app.py
```

린팅과 타입 체크는 저장소 루트에서 다음 명령으로 수행합니다.

```bash
ruff check .
mypy .
```

`.pre-commit-config.yaml`이 설치되어 있다면 커밋 시 자동으로 린트·시크릿 점검이 실행됩니다.

### 테스트

`pyproject.toml`의 pytest 설정을 따릅니다(`pythonpath = ["app"]`, `testpaths = ["tests"]`).

사용 가능한 마커:

- `unit` — 외부 의존성 없는 단위 테스트
- `integration` — 외부 서비스가 필요한 통합 테스트
- `security` — 보안 관련 테스트
- `db` — 데이터베이스 테스트
- `api` — API 엔드포인트 테스트

전체 실행:

```bash
make test
# 또는
pytest
```

특정 마커만 실행:

```bash
pytest -m unit
pytest -m "integration and api"
```

### 기여 가이드

- 커밋 메시지는 Conventional Commits 규약을 따릅니다(`commitlint.config.js`).
- PR 전 `make verify` 통과를 권장합니다.
- 라우트/모듈 변경 시 `AGENTS.md`(해당 디렉터리)의 가이드를 우선 검토해 주세요.
- 상세 절차는 `CONTRIBUTING.md`를 참조하세요.

### 라이선스

이 저장소는 저장소 내 `LICENSE` 파일에 명시된 라이선스를 따릅니다.

---

## English

### Overview

**Blacklist Service Management** is a Python-based platform that aggregates threat intelligence from multiple external sources (malicious IPs, domains, URLs), consolidates them into a centrally managed blacklist, and automatically deploys them to external security appliances such as Fortinet firewalls. It exposes a Jinja2 web UI, REST API, and WebSocket channels for real-time monitoring and operational automation.

Primary users:

- **Security Operations (SOC)** — unified threat-intelligence ingestion and automated blocking
- **Network Engineers** — automated policy/address-object deployment to Fortinet and similar appliances
- **Platform Operators** — single console for collections, sessions, integrations, settings, and monitoring

The default service port is `2542` (overridable via `PORT`); the default environment is `development`. The application entry point is `app/run_app.py`; in containers, `app/entrypoint.sh` invokes it. Pre-deployment checks are run via `app/deployment_validation.py`.

### Features

- **Centralized Blacklist Management** — CRUD for IP/domain blacklists, batch operations, synchronization with external collections, full change history (`app/core/routes/api/blacklist/`)
- **Collection Synchronization** — scheduled and on-demand ingestion from multiple threat-intelligence sources with history tracking and trigger execution (`app/core/routes/api/collection/`)
- **Fortinet Integration** — Fortinet device registration (`fortinet_register.py`) and automated policy/address-object deployment from blacklist entries (`fortinet/core.py`)
- **Authentication & Authorization** — JWT-based sessions, route protection via decorators and middleware, role-based access control (`app/core/auth/`)
- **Monitoring & Observability** — cache, error, and system metrics collection, dashboard views, structured logging, log rotation management (`app/core/monitoring/`, `app/utils/`)
- **REST API + WebSocket** — modular, domain-oriented APIs and real-time event streaming (`app/core/routes/api/`, `app/core/routes/websocket_routes.py`)
- **Web UI** — Jinja2-based dashboard, collections, sessions, integrations, settings, and monitoring screens (`app/templates/`)
- **Migrations & Settings** — database migrations (`migration.py`), IP-management helpers, and system/settings APIs
- **Container-friendly Deployment** — Dockerfile and `deploy/docker-compose.yml` for multi-service orchestration

### Architecture

```mermaid
flowchart LR
    subgraph Client["Browser / Operator"]
        UI["Web UI<br/>Jinja2 templates"]
    end

    subgraph Edge["Reverse Proxy / Ingress"]
        Proxy["nginx / TLS"]
    end

    subgraph App["Flask Application (app/run_app.py)"]
        Web["Web Routes<br/>web_routes.py"]
        API["REST API<br/>api_routes.py"]
        WS["WebSocket<br/>websocket_routes.py"]
        ProxyRoutes["Proxy Routes<br/>proxy_routes.py"]
        Sys["System Routes<br/>system_routes.py"]
    end

    subgraph Domain["Domain Modules"]
        Auth["auth/<br/>jwt_service, middleware, decorators"]
        Mon["monitoring/<br/>cache_metrics, error_metrics, metrics"]
        BL["blacklist/<br/>core, batch, management, system"]
        Coll["collection/<br/>sources, sync, trigger, history"]
        Forti["fortinet/<br/>core, register"]
        Dash["dashboard.py<br/>dashboard_api.py"]
    end

    subgraph Data["Persistence / State"]
        DB[("Database")]
        Logs[("Structured logs")]
        Cache[("Cache")]
    end

    subgraph Ext["External"]
        TI["Threat Intel Sources"]
        FW["Fortinet Firewalls"]
    end

    UI --&gt; Proxy --&gt; Web
    UI --&gt; Proxy --&gt; API
    UI --&gt; Proxy --&gt; WS
    API --&gt; Auth
    API --&gt; Mon
    API --&gt; BL
    API --&gt; Coll
    API --&gt; Forti
    API --&gt; Dash
    Web --&gt; Dash
    BL --&gt; DB
    Coll --&gt; TI
    Coll --&gt; DB
    Forti --&gt; FW
    Mon --&gt; Logs
    Mon --&gt; Cache
```

### Quick Start

Prerequisites:

- Docker and Docker Compose v2
- Make
- (Optional) Python 3.11+ for running without containers

After cloning, prepare the environment file:

```bash
git clone <repository-url> blacklist-service
cd blacklist-service
cp deploy/.env.example deploy/.env   # adjust values for your environment
```

Launch the development environment:

```bash
make dev          # build and start with hot reload
# or
make dev-no-build # start with existing images
```

Once running:

- Web UI: `http://localhost:2542`
- API base: `http://localhost:2542/api`
- Health check: `http://localhost:2542/health`

Stop the stack:

```bash
make down
```

### Configuration

Key environment variables (in `deploy/.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| `ENV` | Runtime environment (`development` / `production`) | `development` |
| `PORT` | Service port | `2542` |
| `JWT_SECRET` | JWT signing key (required in production) | — |
| `DB_*` | Database connection parameters | — |
| `FORTINET_*` | Fortinet appliance registration parameters | — |

Authentication, role, and route-protection rules live under `app/core/auth/`. Per-route authorization is enforced via `@require_auth` and `@require_role` decorators.

### Commands Reference

The `Makefile` provides the following targets:

| Command | Description |
|---------|-------------|
| `make help` | List available targets |
| `make setup-hooks` | Install Git hooks (pre-commit, commit-msg) |
| `make dev` | Start development stack (with build, hot reload) |
| `make dev-no-build` | Start development stack using existing images |
| `make dev-prod` | Start production-like stack (no hot reload) |
| `make dev-app` | Restart only the app service |
| `make build` | Build Docker images |
| `make up` | Start containers |
| `make down` | Stop containers |
| `make restart` | Restart containers |
| `make logs` | Stream container logs |
| `make health` | Run service health check |
| `make clean` | Remove local caches and build artifacts |
| `make test` | Run tests |
| `make verify` | Run verification suite (lint/type/secret/pre-commit) |
| `make verify-lint` | Run Ruff lint |
| `make verify-types` | Run mypy type checks |
| `make verify-secrets` | Run secret-leak scan |
| `make verify-pre-commit` | Run full pre-commit suite |
| `make verify-quick` | Run quick verification |
| `make verify-all` | Run complete verification |
| `make deploy` | Deploy |
| `make prod` | Start in production mode |
| `make release` | Execute release procedure |
| `make release-dry` | Dry-run release procedure |

### Local Development

In development mode, source changes are reflected in the running container through volume mounts. To run outside Docker:

```bash
cd app
pip install -r requirements.txt
python run_app.py
```

Run linting and type checks from the repository root:

```bash
ruff check .
mypy .
```

If `.pre-commit-config.yaml` is installed, lint and secret checks run automatically on commit.

### Testing

Tests follow the pytest configuration in `pyproject.toml` (`pythonpath = ["app"]`, `testpaths = ["tests"]`).

Available markers:

- `unit` — unit tests without external dependencies
- `integration` — integration tests requiring services
- `security` — security-related tests
- `db` — database tests
- `api` — API endpoint tests

Run the full suite:

```bash
make test
# or
pytest
```

Run selected markers:

```bash
pytest -m unit
pytest -m "integration and api"
```

### Contributing

- Commit messages follow the Conventional Commits convention (`commitlint.config.js`).
- Run `make verify` before opening a PR.
- When modifying routes or modules, review the relevant `AGENTS.md` first.
- See `CONTRIBUTING.md` for full guidelines.

### License

This repository is distributed under the terms of the license file in the `LICENSE` file.

---

## Repository Structure

```
.
├── AGENTS.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── Makefile
├── OWNERS
├── README.md
├── VERSION
├── commitlint.config.js
├── mypy.ini
├── pyproject.toml
└── app/
    ├── AGENTS.md
    ├── Dockerfile
    ├── __init__.py
    ├── deployment_validation.py
    ├── entrypoint.sh
    ├── requirements.txt
    ├── run_app.py
    ├── utils/
    │   ├── log_rotation_manager.py
    │   └── structured_logging.py
    ├── templates/
    │   ├── collection.html
    │   ├── collection_logs.html
    │   ├── index.html
    │   ├── integrations.html
    │   ├── sessions.html
    │   ├── settings.html
    │   └── monitoring/
    │       └── dashboard.html
    └── core/
        ├── AGENTS.md
        ├── __init__.py
        ├── app.py
        ├── auth_manager.py
        ├── config.py
        ├── dashboard.py
        ├── testing_app.py
        ├── auth/
        │   ├── AGENTS.md
        │   ├── __init__.py
        │   ├── decorators.py
        │   ├── jwt_service.py
        │   └── middleware.py
        ├── monitoring/
        │   ├── AGENTS.md
        │   ├── __init__.py
        │   ├── cache_metrics.py
        │   ├── error_metrics.py
        │   └── metrics.py
        └── routes/
            ├── AGENTS.md
            ├── api_routes.py
            ├── collection_routes_simple.py
            ├── proxy_routes.py
            ├── system_routes.py
            ├── web_routes.py
            ├── websocket_routes.py
            ├── api/
            │   ├── AGENTS.md
            │   ├── __init__.py
            │   ├── analytics.py
            │   ├── auth_routes.py
            │   ├── core_api.py
            │   ├── dashboard_api.py
            │   ├── database_api.py
            │   ├── error_metrics_api.py
            │   ├── fortinet_register.py
            │   ├── ip_management_helpers.py
            │   ├── migration.py
            │   ├── settings_api.py
            │   ├── system_api.py
            │   ├── monitoring/
            │   │   └── __init__.py
            │   ├── blacklist/
            │   │   ├── AGENTS.md
            │   │   ├── __init__.py
            │   │   ├── batch.py
            │   │   ├── collection.py
            │   │   ├── core.py
            │   │   ├── management.py
            │   │   └── system.py
            │   ├── collection/
            │   │   ├── AGENTS.md
            │   │   ├── __init__.py
            │   │   ├── config.py
            │   │   ├── credentials.py
            │   │   ├── history.py
            │   │   ├── sources.py
            │   │   ├── status.py
            │   │   ├── sync.py
            │   │   ├── trigger.py
            │   │   └── utils.py
            │   └── fortinet/
            │       ├── AGENTS.md
            │       ├── __init__.py
            │       └── core.py
```