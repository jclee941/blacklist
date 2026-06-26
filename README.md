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
  - [License](#license)
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
- **REST API + WebSocket** — 도메인별 모듈화된 API, 실시간 이벤트 스트림 (`app/core/routes/api/`, `websocket_routes.py`)
- **프록시 라우트** — 외부 시스템 연동을 위한 중계 엔드포인트 (`proxy_routes.py`)
- **웹 UI** — Jinja2 기반 페이지(인덱스, 컬렉션, 세션, 통합, 설정, 모니터링 대시보드) (`app/templates/`)
- **데이터베이스 마이그레이션** — 내장 스키마 진화 및 검증 도구 (`migration.py`, `app/AGENTS.md`)
- **Docker 기반 배포** — 개발/운영 환경 통합, 핫 리로드, 배포 검증 스크립트 (`app/Dockerfile`, `deploy/`)

### 아키텍처

```mermaid
flowchart TB
    subgraph Client["Client Layer / 클라이언트 계층"]
        UI["Web UI<br/>(Jinja2 Templates)"]
        APIClient["External API Clients"]
        WSClient["WebSocket Clients"]
    end

    subgraph Web["Web Layer / 웹 계층"]
        WebRoutes["web_routes.py"]
        APIRoutes["api_routes.py"]
        WSRoutes["websocket_routes.py"]
        ProxyRoutes["proxy_routes.py"]
        SystemRoutes["system_routes.py"]
    end

    subgraph Core["Core Services / 핵심 서비스"]
        App["app.py (Flask Factory)"]
        AuthMgr["auth_manager.py"]
        JWTSvc["JWT Service<br/>+ decorators/middleware"]
        Dashboard["dashboard.py"]
        Config["config.py"]
    end

    subgraph Domain["Domain Modules / 도메인 모듈"]
        Collection["collection/<br/>sources, sync, trigger,<br/>history, status"]
        Blacklist["blacklist/<br/>batch, management,<br/>collection, core, system"]
        Fortinet["fortinet/<br/>core, register"]
        Analytics["analytics.py"]
        SettingsAPI["settings_api.py"]
        SystemAPI["system_api.py"]
    end

    subgraph Observability["Observability / 관측"]
        Metrics["metrics.py"]
        CacheMetrics["cache_metrics.py"]
        ErrorMetrics["error_metrics.py"]
        Structured["structured_logging.py"]
        LogRotate["log_rotation_manager.py"]
    end

    subgraph Infra["Infrastructure / 인프라"]
        DB[("Database")]
        ExtSources["External Threat<br/>Intel Sources"]
        FortinetFW["Fortinet Devices"]
    end

    Client --&gt; Web
    Web --&gt; Core
    Web --&gt; Domain
    Core --&gt; Domain
    Domain --&gt; Infra
    Observability --&gt; Web
    Observability --&gt; Core
    Observability --&gt; Domain
    App --&gt; AuthMgr
    App --&gt; Dashboard
```

**계층 요약**

| 계층 | 위치 | 책임 |
| --- | --- | --- |
| Client | 브라우저/외부 클라이언트 | Jinja2 페이지, REST 호출, WebSocket 구독 |
| Web | `app/core/routes/` | HTTP 라우팅, 인증 적용, 요청/응답 직렬화 |
| Core | `app/core/` | 앱 부트스트랩, 설정, 인증, 대시보드 집계 |
| Domain | `app/core/routes/api/{collection,blacklist,fortinet,...}` | 도메인 비즈니스 로직 및 API |
| Observability | `app/core/monitoring/`, `app/utils/` | 메트릭, 로그, 회전, 대시보드 데이터 |
| Infrastructure | DB, 외부 인텔 소스, Fortinet 장비 | 영속 저장·외부 시스템 연동 |

### 빠른 시작

사전 요구 사항: Docker / Docker Compose, GNU Make, Python 3.11+(로컬 직접 실행 시).

1. 저장소 클론 및 환경 변수 파일 준비

   ```bash
   git clone <repository-url> blacklist-service
   cd blacklist-service
   cp deploy/.env.example deploy/.env   # 값 편집
   ```

2. 개발 환경 기동 (핫 리로드)

   ```bash
   make dev
   ```

   - 애플리케이션: `http://localhost:2542`
   - 코드 변경 시 볼륨 마운트를 통해 자동 리로드

3. 헬스 체크

   ```bash
   make health
   ```

4. (선택) Git 훅 설치

   ```bash
   make setup-hooks
   ```

### 설정

주요 설정은 `deploy/.env` 및 `app/core/config.py`를 통해 로드됩니다. 일반적인 키:

| 변수 | 설명 | 기본값 |
| --- | --- | --- |
| `ENV` | 실행 환경 (`development` / `production`) | `development` |
| `PORT` | 웹 서비스 포트 | `2542` |
| `DATABASE_URL` | 데이터베이스 접속 문자열 | 환경별 |
| `JWT_SECRET` | JWT 서명 비밀키 | 환경별 |
| `JWT_EXPIRES` | JWT 만료 시간 | 환경별 |
| `LOG_LEVEL` | 로그 레벨 (`DEBUG`/`INFO`/`WARNING`/`ERROR`) | `INFO` |
| `LOG_DIR` | 로그 파일 경로 | 환경별 |
| Fortinet 연동 변수 | 장비 자격 증명, API 엔드포인트 | 환경별 |

민감 정보(시크릿, 토큰, 자격 증명)는 반드시 `deploy/.env`로 주입하고 저장소에 커밋하지 마세요. 시크릿 점검은 `make verify-secrets`로 수행합니다.

### 명령어 레퍼런스

`Makefile`은 모든 일상 운영 명령을 제공합니다. 전체 목록은 `make help`로 확인할 수 있습니다.

| 명령 | 설명 |
| --- | --- |
| `make help` | 사용 가능한 명령과 설명 출력 |
| `make setup-hooks` | pre-commit, commitlint, husky 훅 설치 |
| `make dev` | 개발 환경 기동(빌드 + 핫 리로드) |
| `make dev-no-build` | 기존 이미지로 빠르게 기동 |
| `make dev-prod` | 운영 모드(오버라이드 없음, 핫 리로드 비활성) |
| `make dev-app` | 앱 서비스만 재시작 |
| `make build` | Docker 이미지 빌드 |
| `make up` | Compose 서비스 up |
| `make down` | Compose 서비스 down |
| `make logs` | 로그 스트림 |
| `make restart` | 서비스 재시작 |
| `make health` | 헬스 체크 엔드포인트 호출 |
| `make test` | pytest 실행 |
| `make verify` | 린트·타입·시크릿·pre-commit 종합 검증 |
| `make verify-lint` | Ruff 린트 |
| `make verify-types` | mypy 타입 검사 |
| `make verify-secrets` | 시크릿/자격 증명 점검 |
| `make verify-pre-commit` | pre-commit 훅 실행 |
| `make verify-quick` | 빠른 검증(린트 + 타입) |
| `make verify-all` | 전체 검증 |
| `make release` | 릴리스 절차 수행 |
| `make release-dry` | 릴리스 드라이런 |
| `make clean` | 로컬 산출물 정리 |

### 로컬 개발

**Python 환경(컨테이너 없이 직접 실행)**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
export ENV=development PORT=2542
python app/run_app.py
```

**코드 품질**

- 린트: `ruff check app/` (`pyproject.toml`의 `[tool.ruff]` 설정 사용, Python 3.11, 라인 길이 120)
- 타입: `mypy app/` (`mypy.ini` 참조)
- 포맷: pre-commit 훅이 Ruff/Prettier 적용

**커밋 메시지 규약**

- `commitlint.config.js`에 따라 Conventional Commits 적용
- 예: `feat(collection): add manual trigger endpoint`, `fix(auth): handle expired token`

**디렉토리 컨벤션**

- 도메인 API 모듈은 `app/core/routes/api/<domain>/`에 자체 패키지로 구성
- 각 패키지에 `AGENTS.md`(도메인 운영 메모)와 `__init__.py` 유지
- Jinja2 템플릿은 `app/templates/` 및 `app/templates/monitoring/`

### 테스트

테스트 프레임워크는 pytest이며, `pyproject.toml`의 `[tool.pytest.ini_options]` 섹션 설정을 따릅니다(`pythonpath = ["app"]`, `testpaths = ["tests"]`).

```bash
# 전체 테스트
make test

# 또는 직접 실행
pytest -v

# 마커별 실행
pytest -m unit
pytest -m integration
pytest -m security
pytest -m db
pytest -m api
```

마커 정의:

- `unit` — 외부 의존성 없는 단위 테스트
- `integration` — 외부 서비스가 필요한 통합 테스트
- `security` — 보안 관련 테스트
- `db` — 데이터베이스 테스트
- `api` — API 엔드포인트 테스트

테스트용 애플리케이션 팩토리는 `app/core/testing_app.py`에 정의되어 있습니다.

### 기여 가이드

기여 절차와 규약은 `CONTRIBUTING.md`를 참조하세요. 핵심 원칙:

1. 이슈/브랜치 생성 → 작업 → pre-commit 훅 통과 → PR 제출
2. 커밋 메시지는 Conventional Commits 준수
3. 새 기능은 해당 도메인 패키지(`collection`, `blacklist`, `fortinet`, `auth`, `monitoring` 등)에 모듈화
4. API 라우트 추가 시 적절한 인증 데코레이터와 입력 검증 적용
5. 테스트 추가(최소한 단위 테스트, 가능하면 통합 테스트)
6. PR 리뷰어 지정 — `OWNERS` 참조
7. 변경 이력은 `CHANGELOG.md`에 누적

### 라이선스

본 저장소는 저장소 루트의 `LICENSE` 파일에 명시된 라이선스를 따릅니다.

---

## English

### Overview

**Blacklist Service Management** is a Python-based platform that aggregates threat-intelligence data from multiple external sources, centralizes blacklist management, and automatically deploys entries to external security devices such as Fortinet firewalls. It provides a web UI (Jinja2), REST API, and WebSocket endpoints for real-time monitoring and operational automation.

Primary users:

- **Security Operations (SOC)** — unified threat intelligence and automated blocking
- **Network Engineers** — automated policy/address-object deployment to Fortinet devices
- **Platform Operators** — single console for collection, sessions, integrations, settings, and monitoring

The default service port is `2542` (configurable via `PORT`); the default environment is `development`. The application entry point is `app/run_app.py`; in containerized deployments, `app/entrypoint.sh` invokes it. Pre-deployment validation is handled by `app/deployment_validation.py`.

### Features

- **Centralized Blacklist Management** — CRUD for IP/domain entries, batch operations, synchronization with external collections, change history (`app/core/routes/api/blacklist/`)
- **Collection Sync** — scheduled/manual ingestion from multiple threat-intel sources, history tracking, trigger execution (`app/core/routes/api/collection/`)
- **Fortinet Integration** — device registration (`fortinet_register.py`), automated policy/address-object deployment (`fortinet/core.py`)
- **Authentication & Authorization** — JWT-based sessions, decorator/middleware-based route protection, role-based access control (`app/core/auth/`)
- **Monitoring & Observability** — cache/error/system metrics, dashboard aggregation, structured logging, log rotation (`app/core/monitoring/`, `app/utils/`)
- **REST API + WebSocket** — domain-modular API, real-time event streaming (`app/core/routes/api/`, `websocket_routes.py`)
- **Proxy Routes** — relay endpoints for external system integration (`proxy_routes.py`)
- **Web UI** — Jinja2 pages for index, collections, sessions, integrations, settings, monitoring dashboard (`app/templates/`)
- **Database Migrations** — built-in schema evolution and validation (`migration.py`)
- **Docker-based Deployment** — unified dev/prod environments, hot reload, deployment validation (`app/Dockerfile`, `deploy/`)

### Architecture

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        UI["Web UI<br/>(Jinja2 Templates)"]
        APIClient["External API Clients"]
        WSClient["WebSocket Clients"]
    end

    subgraph Web["Web Layer"]
        WebRoutes["web_routes.py"]
        APIRoutes["api_routes.py"]
        WSRoutes["websocket_routes.py"]
        ProxyRoutes["proxy_routes.py"]
        SystemRoutes["system_routes.py"]
    end

    subgraph Core["Core Services"]
        App["app.py (Flask Factory)"]
        AuthMgr["auth_manager.py"]
        JWTSvc["JWT Service<br/>+ decorators/middleware"]
        Dashboard["dashboard.py"]
        Config["config.py"]
    end

    subgraph Domain["Domain Modules"]
        Collection["collection/<br/>sources, sync, trigger,<br/>history, status"]
        Blacklist["blacklist/<br/>batch, management,<br/>collection, core, system"]
        Fortinet["fortinet/<br/>core, register"]
        Analytics["analytics.py"]
        SettingsAPI["settings_api.py"]
        SystemAPI["system_api.py"]
    end

    subgraph Observability["Observability"]
        Metrics["metrics.py"]
        CacheMetrics["cache_metrics.py"]
        ErrorMetrics["error_metrics.py"]
        Structured["structured_logging.py"]
        LogRotate["log_rotation_manager.py"]
    end

    subgraph Infra["Infrastructure"]
        DB[("Database")]
        ExtSources["External Threat<br/>Intel Sources"]
        FortinetFW["Fortinet Devices"]
    end

    Client --&gt; Web
    Web --&gt; Core
    Web --&gt; Domain
    Core --&gt; Domain
    Domain --&gt; Infra
    Observability --&gt; Web
    Observability --&gt; Core
    Observability --&gt; Domain
    App --&gt; AuthMgr
    App --&gt; Dashboard
```

**Layer Summary**

| Layer | Location | Responsibility |
| --- | --- | --- |
| Client | Browsers / external clients | Jinja2 pages, REST calls, WebSocket subscriptions |
| Web | `app/core/routes/` | HTTP routing, auth enforcement, request/response serialization |
| Core | `app/core/` | App bootstrap, configuration, auth, dashboard aggregation |
| Domain | `app/core/routes/api/{collection,blacklist,fortinet,...}` | Domain business logic and API |
| Observability | `app/core/monitoring/`, `app/utils/` | Metrics, logs, rotation, dashboard data |
| Infrastructure | DB, external intel sources, Fortinet devices | Persistence and external system integration |

### Quick Start

Prerequisites: Docker / Docker Compose, GNU Make, Python 3.11+ (for local non-container runs).

1. Clone and prepare environment

   ```bash
   git clone <repository-url> blacklist-service
   cd blacklist-service
   cp deploy/.env.example deploy/.env   # edit values
   ```

2. Start the development environment (hot reload)

   ```bash
   make dev
   ```

   - Application: `http://localhost:2542`
   - Code changes auto-reload via volume mounts

3. Health check

   ```bash
   make health
   ```

4. (Optional) Install git hooks

   ```bash
   make setup-hooks
   ```

### Configuration

Primary configuration is loaded through `deploy/.env` and `app/core/config.py`. Common keys:

| Variable | Description | Default |
| --- | --- | --- |
| `ENV` | Runtime environment (`development` / `production`) | `development` |
| `PORT` | Web service port | `2542` |
| `DATABASE_URL` | Database connection string | per environment |
| `JWT_SECRET` | JWT signing secret | per environment |
| `JWT_EXPIRES` | JWT expiration window | per environment |
| `LOG_LEVEL` | Log level (`DEBUG`/`INFO`/`WARNING`/`ERROR`) | `INFO` |
| `LOG_DIR` | Log file directory | per environment |
| Fortinet integration vars | device credentials, API endpoint | per environment |

Inject secrets (tokens, credentials) exclusively via `deploy/.env` and never commit them. Use `make verify-secrets` to scan for accidentally committed credentials.

### Commands Reference

`Makefile` provides every routine operational command. Run `make help` for the complete list.

| Command | Description |
| --- | --- |
| `make help` | Print available commands and descriptions |
| `make setup-hooks` | Install pre-commit, commitlint, and husky hooks |
| `make dev` | Start dev environment (build + hot reload) |
| `make dev-no-build` | Start quickly using existing images |
| `make dev-prod` | Production-like (no overrides, no hot reload) |
| `make dev-app` | Restart only the app service |
| `make build` | Build Docker images |
| `make up` | Bring Compose services up |
| `make down` | Bring Compose services down |
| `make logs` | Stream logs |
| `make restart` | Restart services |
| `make health` | Hit the health-check endpoint |
| `make test` | Run pytest |
| `make verify` | Comprehensive verification (lint, types, secrets, pre-commit) |
| `make verify-lint` | Ruff lint |
| `make verify-types` | mypy type checks |
| `make verify-secrets` | Secret/credential scan |
| `make verify-pre-commit` | Run pre-commit hooks |
| `make verify-quick` | Quick verification (lint + types) |
| `make verify-all` | Full verification suite |
| `make release` | Perform release procedure |
| `make release-dry` | Release dry run |
| `make clean` | Clean local build artifacts |

### Local Development

**Python (without containers)**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
export ENV=development PORT=2542
python app/run_app.py
```

**Code quality**

- Lint: `ruff check app/` (see `[tool.ruff]` in `pyproject.toml`; Python 3.11, line length 120)
- Types: `mypy app/` (see `mypy.ini`)
- Formatting: pre-commit hooks apply Ruff/Prettier

**Commit conventions**

- Conventional Commits enforced via `commitlint.config.js`
- Examples: `feat(collection): add manual trigger endpoint`, `fix(auth): handle expired token`

**Directory conventions**

- Domain API modules live in their own package under `app/core/routes/api/<domain>/`
- Each package keeps an `AGENTS.md` (operational notes) and `__init__.py`
- Jinja2 templates live under `app/templates/` and `app/templates/monitoring/`

### Testing

Tests use pytest with configuration from `[tool.pytest.ini_options]` in `pyproject.toml` (`pythonpath = ["app"]`, `testpaths = ["tests"]`).

```bash
# Full suite
make test

# Or directly
pytest -v

# By marker
pytest -m unit
pytest -m integration
pytest -m security
pytest -m db
pytest -m api
```

Markers:

- `unit` — unit tests with no external dependencies
- `integration` — integration tests requiring services
- `security` — security-focused tests
- `db` — database tests
- `api` — API endpoint tests

The testing application factory is provided in `app/core/testing_app.py`.

### Contributing

Refer to `CONTRIBUTING.md` for the full process. Core principles:

1. Open an issue/branch → make changes → pass pre-commit hooks → open PR
2. Follow Conventional Commits
3. Place new features in the appropriate domain package (`collection`, `blacklist`, `fortinet`, `auth`, `monitoring`, etc.)
4. Apply the appropriate auth decorators and input validation to new API routes
5. Add tests (at minimum unit tests, integration tests where possible)
6. Request reviewers per `OWNERS`
7. Accumulate changes in `CHANGELOG.md`

### License

This repository is licensed under the terms described in the `LICENSE` file at the repository root.

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
    ├── core/
    │   ├── AGENTS.md
    │   ├── __init__.py
    │   ├── app.py
    │   ├── auth_manager.py
    │   ├── config.py
    │   ├── dashboard.py
    │   ├── testing_app.py
    │   ├── auth/
    │   │   ├── AGENTS.md
    │   │   ├── __init__.py
    │   │   ├── decorators.py
    │   │   ├── jwt_service.py
    │   │   └── middleware.py
    │   ├── monitoring/
    │   │   ├── AGENTS.md
    │   │   ├── __init__.py
    │   │   ├── cache_metrics.py
    │   │   ├── error_metrics.py
    │   │   └── metrics.py
    │   └── routes/
    │       ├── AGENTS.md
    │       ├── api_routes.py
    │       ├── collection_routes_simple.py
    │       ├── proxy_routes.py
    │       ├── system_routes.py
    │       ├── web_routes.py
    │       ├── websocket_routes.py
    │       └── api/
    │           ├── AGENTS.md
    │           ├── __init__.py
    │           ├── analytics.py
    │           ├── auth_routes.py
    │           ├── core_api.py
    │           ├── dashboard_api.py
    │           ├── database_api.py
    │           ├── error_metrics_api.py
    │           ├── fortinet_register.py
    │           ├── ip_management_helpers.py
    │           ├── migration.py
    │           ├── settings_api.py
    │           ├── system_api.py
    │           ├── monitoring/
    │           │   └── __init__.py
    │           ├── collection/
    │           │   ├── AGENTS.md
    │           │   ├── __init__.py
    │           │   ├── config.py
    │           │   ├── credentials.py
    │           │   ├── history.py
    │           │   ├── sources.py
    │           │   ├── status.py
    │           │   ├── sync.py
    │           │   ├── trigger.py
    │           │   └── utils.py
    │           ├── blacklist/
    │           │   ├── AGENTS.md
    │           │   ├── __init__.py
    │           │   ├── batch.py
    │           │   ├── collection.py
    │           │   ├── core.py
    │           │   ├── management.py
    │           │   └── system.py
    │           └── fortinet/
    │               ├── AGENTS.md
    │               ├── __init__.py
    │               └── core.py
    ├── templates/
    │   ├── collection.html
    │   ├── collection_logs.html
    │   ├── index.html
    │   ├── integrations.html
    │   ├── sessions.html
    │   ├── settings.html
    │   └── monitoring/
    │       └── dashboard.html
    └── utils/
        ├── log_rotation_manager.py
        └── structured_logging.py
```