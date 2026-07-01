# Blacklist Service Management

> **통합 위협 인텔리전스 수집 · 동기화 · 블랙리스트 중앙 관리 · Fortinet 자동 배포 플랫폼**
> **Unified threat-intelligence aggregation, centralized blacklist management, and Fortinet deployment platform.**

---

## 목차 / Table of Contents

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
  - [Architecture](#architecture-1)
  - [Quick Start](#quick-start-1)
  - [Configuration](#configuration-1)
  - [Commands Reference](#commands-reference-1)
  - [Local Development](#local-development-1)
  - [Testing](#testing-1)
  - [Contributing](#contributing-1)
  - [License](#license-1)
- [Repository Structure](#repository-structure)

---

## 한국어

### 개요

**Blacklist Service Management**는 다양한 외부 위협 인텔리전스(Threat Intelligence) 소스로부터 악성 IP·도메인·URL 데이터를 수집·동기화하고, 중앙 블랙리스트로 통합 관리한 뒤 **Fortinet 방화벽 등 외부 보안 장비로 자동 배포**하는 Python 기반 통합 관리 플랫폼입니다. Jinja2 기반 웹 UI, REST API, WebSocket을 통해 실시간 모니터링과 운영 자동화를 제공합니다.

**핵심 사용자**

- **보안 운영팀(SOC)** — 위협 인텔리전스 통합 조회 및 자동 차단 정책 검증
- **네트워크 엔지니어** — Fortinet 등 외부 장비로의 정책/주소 객체 자동 배포
- **플랫폼 운영자** — 컬렉션·세션·통합·설정·모니터링을 단일 콘솔에서 관리

**기본 정보**

| 항목 | 값 |
| --- | --- |
| 기본 포트 | `2542` (`PORT` 환경 변수로 변경 가능) |
| 기본 실행 환경 | `development` (`ENV`) |
| Python 버전 | 3.11+ (`target-version = "py311"`) |
| 로컬 진입점 | `app/run_app.py` |
| 컨테이너 진입점 | `app/entrypoint.sh` |
| 배포 전 검증 스크립트 | `app/deployment_validation.py` |
| 컨테이너 정의 | `app/Dockerfile` |
| Python 의존성 | `app/requirements.txt` |
| Docker Compose | `deploy/docker-compose.yml` |
| 환경 변수 파일 | `deploy/.env` |

### 주요 기능

- **중앙 집중식 블랙리스트 관리** — IP/도메인 항목의 CRUD, 일괄 처리(`batch.py`), 외부 컬렉션과의 양방향 동기화, 변경 이력 추적 (`app/core/routes/api/blacklist/`)
- **컬렉션 동기화** — 여러 TI 소스에서 주기·수동 데이터 수집(`sources.py`), 자격 증명 관리(`credentials.py`), 동기화 트리거(`sync.py`, `trigger.py`), 실행 이력(`history.py`), 상태 모니터링(`status.py`) (`app/core/routes/api/collection/`)
- **Fortinet 통합** — Fortinet API 등록(`fortinet_register.py`), 정책/주소 객체 동기화 코어(`app/core/routes/api/fortinet/core.py`), 프록시 라우트(`proxy_routes.py`)
- **인증·세션 보안** — JWT 발급·검증(`jwt_service.py`), 데코레이터 기반 인가(`decorators.py`), 미들웨어(`middleware.py`), 인증 라우트(`auth_routes.py`)
- **모니터링·관측성** — 시스템 메트릭(`metrics.py`), 캐시 메트릭(`cache_metrics.py`), 에러 메트릭(`error_metrics.py`), 대시보드(`dashboard.py`, `dashboard_api.py`)
- **웹 콘솔(Jinja2)** — 인덱스, 컬렉션, 세션, 통합, 설정, 모니터링 대시보드 페이지 (`app/templates/`)
- **WebSocket 실시간 채널** — 운영 이벤트 푸시 (`websocket_routes.py`)
- **프록시 라우트** — 외부 시스템과의 안전한 중계 (`proxy_routes.py`)
- **시스템 API** — 분석(`analytics.py`), 데이터베이스(`database_api.py`), 마이그레이션(`migration.py`), 시스템 상태(`system_api.py`, `system_routes.py`)
- **구조화 로깅 + 로그 로테이션** — `structured_logging.py`, `log_rotation_manager.py`

### 아키텍처

애플리케이션은 **Flask + Blueprint** 기반의 모듈형 백엔드와 **Jinja2 SSR 프런트엔드**로 구성됩니다. 외부 TI 소스 → 컬렉션 엔진 → 중앙 블랙리스트 → Fortinet 배포의 단방향 파이프라인과, 각 단계의 관측성을 위한 모니터링 레이어로 이루어집니다.

| 계층 | 위치 | 책임 |
| --- | --- | --- |
| Entry | `app/run_app.py`, `app/entrypoint.sh`, `app/Dockerfile` | 프로세스 부트스트랩, Gunicorn/개발 서버 기동 |
| Config | `app/core/config.py` | 환경 변수 로드, 런타임 설정 |
| Auth | `app/core/auth/` | JWT 발급/검증, 데코레이터, 미들웨어 |
| App Core | `app/core/app.py` | Flask 앱 팩토리, Blueprint 등록 |
| API Routes | `app/core/routes/api/`, `app/core/routes/api/blacklist/`, `app/core/routes/api/collection/`, `app/core/routes/api/fortinet/` | REST API (블랙리스트, 컬렉션, Fortinet, 시스템) |
| Web Routes | `app/core/routes/web_routes.py`, `collection_routes_simple.py` | SSR 페이지 라우팅 |
| Realtime | `app/core/routes/websocket_routes.py`, `proxy_routes.py` | WebSocket 푸시, 외부 프록시 |
| Monitoring | `app/core/monitoring/`, `app/core/dashboard.py` | 메트릭 수집, 대시보드 집계 |
| Templates | `app/templates/` | Jinja2 SSR 페이지 |
| Utils | `app/utils/structured_logging.py`, `app/utils/log_rotation_manager.py` | 로깅, 로그 회전 |

**요청 흐름 (컬렉션 → Fortinet 배포 예시)**

1. 운영자가 `web_routes.py` 또는 `api/collection/trigger.py`로 동기화 트리거
2. `credentials.py`로 소스 자격 증명 조회 → `sources.py`로 외부 TI 호출
3. 정규화 결과를 `api/blacklist/`로 머지, `history.py`에 이력 기록
4. `fortinet_register.py` / `api/fortinet/core.py`가 Fortinet API로 주소 객체·정책 배포
5. `monitoring/metrics.py`가 지표 갱신, WebSocket으로 대시보드 푸시
6. `dashboard_api.py`가 UI에 메트릭·로그 제공

### 빠른 시작

Docker Compose를 사용한 1분 기동입니다.

```bash
# 1) 저장소 클론
git clone <repository-url>
cd blacklist-service-management

# 2) 환경 변수 준비
cp deploy/.env.example deploy/.env   # 예시 파일이 없으면 deploy/.env를 직접 작성

# 3) Git 훅 설치 (선택)
make setup-hooks

# 4) 개발 환경 기동 (핫 리로드 포함)
make dev
# 또는 재빌드 없이 빠르게
make dev-no-build
```

기본 포트 `2542`에서 다음 자원에 접속할 수 있습니다.

| 경로 | 설명 |
| --- | --- |
| `http://localhost:2542/` | 인덱스 대시보드 |
| `http://localhost:2542/collection/` | 컬렉션 관리 |
| `http://localhost:2542/sessions/` | 세션/세션 로그 |
| `http://localhost:2542/integrations/` | 외부 통합(Fortinet 등) |
| `http://localhost:2542/settings/` | 설정 |
| `http://localhost:2542/monitoring/dashboard` | 모니터링 대시보드 |
| `ws://localhost:2542/<websocket>` | 실시간 이벤트 채널 |

### 설정

런타임 설정은 `app/core/config.py`가 환경 변수(`ENV`, `PORT` 등)와 `deploy/.env`를 통해 로드합니다. 컨테이너 외부에서 기동할 때는 동일 키를 셸 환경으로 전달하세요.

| 환경 변수 | 설명 | 기본값 |
| --- | --- | --- |
| `ENV` | 실행 환경 (`development` / `production`) | `development` |
| `PORT` | HTTP 리스닝 포트 | `2542` |
| `DEPLOY_*` | 컬렉션/Fortinet/DB 자격 증명 등 (예시는 `deploy/.env`) | — |

> **보안 주의:** `deploy/.env`는 절대로 커밋하지 마세요. 시크릿 스캔은 `make verify-secrets`로 사전 검증할 수 있습니다.

### 명령어 레퍼런스

`Makefile`은 단일 진입점으로 컨테이너·테스트·검증을 모두 다룹니다. `make help`로 전체 목록을 확인할 수 있습니다.

| 명령어 | 설명 |
| --- | --- |
| `make help` | 사용 가능한 명령어와 설명 출력 |
| `make setup-hooks` | pre-commit + commitlint + 프런트엔드 husky 훅 설치 |
| `make dev` | 개발 환경 기동 (이미지 재빌드 + 핫 리로드) |
| `make dev-no-build` | 기존 이미지로 빠르게 기동 |
| `make dev-prod` | 프로덕션 유사 환경 기동 (오버라이드 없음) |
| `make dev-app` | `app` 서비스만 재시작 (빠른 코드 반영) |
| `make build` | Docker 이미지 빌드 |
| `make up` | Compose 스택 기동 |
| `make down` | Compose 스택 종료 |
| `make logs` | 서비스 로그 스트리밍 |
| `make restart` | 서비스 재시작 |
| `make health` | 헬스 체크 엔드포인트 확인 |
| `make clean` | 빌드 산출물·중지 컨테이너 정리 |
| `make test` | 테스트 실행 |
| `make deploy` | 배포 절차 실행 |
| `make prod` | 프로덕션 모드 기동 |
| `make release` | 릴리스 절차 실행 |
| `make release-dry` | 릴리스 드라이런 |
| `make verify` | 전체 검증 |
| `make verify-lint` | 린트 (Ruff) |
| `make verify-types` | 타입 검사 (mypy) |
| `make verify-secrets` | 시크릿 스캔 |
| `make verify-pre-commit` | pre-commit 훅 전 구간 실행 |
| `make verify-quick` | 빠른 검증 스위트 |
| `make verify-all` | 전체 검증 스위트 |

### 로컬 개발

**컨테이너 없이 Python만으로 개발하는 경우 (3.11+ 권장)**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
export ENV=development PORT=2542
python app/run_app.py
```

**프런트엔드(템플릿/자산) 작업**

```bash
cd frontend && npm install
# ESLint + Prettier는 husky 훅이 pre-commit에서 자동 실행
```

**코드 품질**

- 린터: `ruff` (`pyproject.toml`의 `[tool.ruff]`, `line-length = 120`, `target-version = "py311"`)
- 타입 체커: `mypy` (`mypy.ini`)
- 커밋 메시지: Conventional Commits (`commitlint.config.js`)
- 비밀 검출: `make verify-secrets`

### 테스트

테스트 러너는 **pytest**이며 `pyproject.toml`의 `[tool.pytest.ini_options]`에 정의된 마커로 카테고리를 구분합니다.

| 마커 | 용도 |
| --- | --- |
| `unit` | 외부 의존성 없는 단위 테스트 |
| `integration` | 실제 서비스가 필요한 통합 테스트 |
| `security` | 보안 관련 테스트 |
| `db` | 데이터베이스 테스트 |
| `api` | API 엔드포인트 테스트 |

```bash
# 전체 테스트
make test
# 또는
pytest

# 카테고리만 실행
pytest -m unit
pytest -m integration
pytest -m "security or api"
```

기본 옵션: `-v --tb=short` (`addopts`).

### 기여 가이드

1. 이슈 등록 → 작업 범위 합의
2. 브랜치 생성 (예: `feat/collection-scheduler`)
3. 커밋 메시지는 Conventional Commits 형식 (`feat:`, `fix:`, `chore:` 등)
4. PR 전 `make verify-all` 통과 확인
5. `CONTRIBUTING.md`의 리뷰어 가이드라인 준수

코드 스타일은 `pyproject.toml`의 Ruff 설정, 타입 규칙은 `mypy.ini`를 따릅니다.

### 라이선스

이 프로젝트는 저장소 루트의 `LICENSE` 파일에 명시된 라이선스를 따릅니다.

---

## English

### Overview

**Blacklist Service Management** is a Python-based unified platform that **aggregates threat intelligence from multiple external sources, centralizes blacklist management, and automatically deploys them to Fortinet firewalls and other security appliances**. It exposes a Jinja2-rendered web console, a REST API, and WebSocket channels for real-time monitoring and operational automation.

**Primary users**

- **SOC operators** — unified TI lookup and automated blocking policy validation
- **Network engineers** — push policies/address objects to Fortinet and other appliances
- **Platform operators** — single console for collections, sessions, integrations, settings, and monitoring

**At a glance**

| Item | Value |
| --- | --- |
| Default port | `2542` (overridable via `PORT`) |
| Default environment | `development` (`ENV`) |
| Python version | 3.11+ (`target-version = "py311"`) |
| Local entry point | `app/run_app.py` |
| Container entry point | `app/entrypoint.sh` |
| Pre-deploy validator | `app/deployment_validation.py` |
| Container definition | `app/Dockerfile` |
| Python dependencies | `app/requirements.txt` |
| Docker Compose | `deploy/docker-compose.yml` |
| Env file | `deploy/.env` |

### Features

- **Centralized blacklist management** — CRUD, batch processing (`batch.py`), bidirectional sync with external collections, change history (`app/core/routes/api/blacklist/`)
- **Collection sync** — periodic/manual ingestion from multiple TI sources (`sources.py`), credential management (`credentials.py`), triggers (`sync.py`, `trigger.py`), execution history (`history.py`), status monitoring (`status.py`) (`app/core/routes/api/collection/`)
- **Fortinet integration** — Fortinet API registration (`fortinet_register.py`), policy/address-object sync core (`app/core/routes/api/fortinet/core.py`), proxy routes (`proxy_routes.py`)
- **Auth & session security** — JWT issuance/validation (`jwt_service.py`), decorator-based authorization (`decorators.py`), middleware (`middleware.py`), auth routes (`auth_routes.py`)
- **Observability** — system metrics (`metrics.py`), cache metrics (`cache_metrics.py`), error metrics (`error_metrics.py`), dashboards (`dashboard.py`, `dashboard_api.py`)
- **Web console (Jinja2)** — index, collection, sessions, integrations, settings, and monitoring dashboard pages (`app/templates/`)
- **WebSocket real-time channel** — operational event push (`websocket_routes.py`)
- **Proxy routes** — safe mediation with external systems (`proxy_routes.py`)
- **System API** — analytics (`analytics.py`), database (`database_api.py`), migrations (`migration.py`), system status (`system_api.py`, `system_routes.py`)
- **Structured logging + log rotation** — `structured_logging.py`, `log_rotation_manager.py`

### Architecture

The application is built on **Flask + Blueprints** for the backend and **Jinja2 SSR** for the frontend. It implements a forward pipeline — external TI sources → collection engine → centralized blacklist → Fortinet deployment — with an observability layer for every stage.

| Layer | Location | Responsibility |
| --- | --- | --- |
| Entry | `app/run_app.py`, `app/entrypoint.sh`, `app/Dockerfile` | Process bootstrap, Gunicorn/dev server startup |
| Config | `app/core/config.py` | Env-var loading, runtime settings |
| Auth | `app/core/auth/` | JWT issuance/validation, decorators, middleware |
| App Core | `app/core/app.py` | Flask app factory, Blueprint registration |
| API Routes | `app/core/routes/api/`, `api/blacklist/`, `api/collection/`, `api/fortinet/` | REST API (blacklist, collection, Fortinet, system) |
| Web Routes | `core/routes/web_routes.py`, `collection_routes_simple.py` | SSR page routing |
| Realtime | `core/routes/websocket_routes.py`, `proxy_routes.py` | WebSocket push, external proxy |
| Monitoring | `app/core/monitoring/`, `app/core/dashboard.py` | Metric collection, dashboard aggregation |
| Templates | `app/templates/` | Jinja2 SSR pages |
| Utils | `app/utils/structured_logging.py`, `app/utils/log_rotation_manager.py` | Logging, log rotation |

**Request flow (collection → Fortinet deployment)**

1. Operator triggers sync via `web_routes.py` or `api/collection/trigger.py`
2. `credentials.py` retrieves source credentials → `sources.py` calls external TI
3. Normalized results merge into `api/blacklist/` and `history.py` records the run
4. `fortinet_register.py` / `api/fortinet/core.py` deploys address objects/policies to Fortinet
5. `monitoring/metrics.py` updates metrics; WebSocket pushes to the dashboard
6. `dashboard_api.py` serves metrics/logs to the UI

### Quick Start

One-minute startup using Docker Compose.

```bash
# 1) Clone
git clone <repository-url>
cd blacklist-service-management

# 2) Prepare env
cp deploy/.env.example deploy/.env   # or create deploy/.env directly

# 3) Install git hooks (optional)
make setup-hooks

# 4) Start dev environment (with hot reload)
make dev
# or, without rebuilding
make dev-no-build
```

On the default port `2542`, the following resources are available.

| Path | Description |
| --- | --- |
| `http://localhost:2542/` | Index dashboard |
| `http://localhost:2542/collection/` | Collection management |
| `http://localhost:2542/sessions/` | Sessions / session logs |
| `http://localhost:2542/integrations/` | External integrations (Fortinet, etc.) |
| `http://localhost:2542/settings/` | Settings |
| `http://localhost:2542/monitoring/dashboard` | Monitoring dashboard |
| `ws://localhost:2542/<websocket>` | Real-time event channel |

### Configuration

Runtime configuration is loaded by `app/core/config.py` from environment variables (`ENV`, `PORT`, etc.) and `deploy/.env`. When running outside a container, export the same keys in your shell environment.

| Env var | Description | Default |
| --- | --- | --- |
| `ENV` | Runtime environment (`development` / `production`) | `development` |
| `PORT` | HTTP listen port | `2542` |
| `DEPLOY_*` | Collection/Fortinet/DB credentials, etc. (see `deploy/.env`) | — |

> **Security note:** never commit `deploy/.env`. Use `make verify-secrets` for pre-commit secret scanning.

### Commands Reference

The `Makefile` is the single entry point for containers, tests, and verification. Run `make help` for the full list.

| Command | Description |
| --- | --- |
| `make help` | List available commands |
| `make setup-hooks` | Install pre-commit + commitlint + frontend husky hooks |
| `make dev` | Start dev environment (rebuild images + hot reload) |
| `make dev-no-build` | Start with existing images (fast) |
| `make dev-prod` | Start production-like environment (no overrides) |
| `make dev-app` | Restart only the `app` service (fast code reload) |
| `make build` | Build Docker images |
| `make up` | Bring up the Compose stack |
| `make down` | Tear down the Compose stack |
| `make logs` | Stream service logs |
| `make restart` | Restart services |
| `make health` | Probe health endpoints |
| `make clean` | Clean build artifacts and stopped containers |
| `make test` | Run tests |
| `make deploy` | Run deployment procedure |
| `make prod` | Start in production mode |
| `make release` | Run release procedure |
| `make release-dry` | Dry-run a release |
| `make verify` | Full verification |
| `make verify-lint` | Lint (Ruff) |
| `make verify-types` | Type check (mypy) |
| `make verify-secrets` | Secret scanning |
| `make verify-pre-commit` | Run pre-commit hook suite |
| `make verify-quick` | Quick verification suite |
| `make verify-all` | Full verification suite |

### Local Development

**Python-only development (no container), Python 3.11+ recommended**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
export ENV=development PORT=2542
python app/run_app.py
```

**Frontend (templates/assets)**

```bash
cd frontend && npm install
# ESLint + Prettier run automatically via husky pre-commit
```

**Code quality**

- Linter: `ruff` (see `[tool.ruff]` in `pyproject.toml`, `line-length = 120`, `target-version = "py311"`)
- Type checker: `mypy` (`mypy.ini`)
- Commit messages: Conventional Commits (`commitlint.config.js`)
- Secret scanning: `make verify-secrets`

### Testing

The test runner is **pytest**, with markers defined in `[tool.pytest.ini_options]` in `pyproject.toml`.

| Marker | Purpose |
| --- | --- |
| `unit` | Unit tests (no external dependencies) |
| `integration` | Integration tests (require services) |
| `security` | Security-related tests |
| `db` | Database tests |
| `api` | API endpoint tests |

```bash
# All tests
make test
# or
pytest

# By category
pytest -m unit
pytest -m integration
pytest -m "security or api"
```

Default options: `-v --tb=short` (`addopts`).

### Contributing

1. Open an issue → agree on scope
2. Create a branch (e.g. `feat/collection-scheduler`)
3. Use Conventional Commits (`feat:`, `fix:`, `chore:`, ...)
4. Pass `make verify-all` before opening a PR
5. Follow the reviewer guidelines in `CONTRIBUTING.md`

Style follows the Ruff config in `pyproject.toml`; type rules follow `mypy.ini`.

### License

This project is licensed under the terms described in the `LICENSE` file at the repository root.

---

## Repository Structure

```text
.
├── AGENTS.md              # Internal contributor / agent guide
├── CHANGELOG.md           # Release notes
├── CONTRIBUTING.md        # Contribution guide
├── LICENSE                # License terms
├── Makefile               # Single entry point for dev/test/verify/deploy
├── OWNERS                 # Code ownership
├── README.md              # This document
├── VERSION                # Current version
├── commitlint.config.js   # Conventional Commits config
├── mypy.ini               # mypy configuration
├── pyproject.toml         # Project config (pytest, ruff, build)
└── app/
    ├── AGENTS.md
    ├── Dockerfile
    ├── __init__.py
    ├── deployment_validation.py  # Pre-deploy checks
    ├── entrypoint.sh             # Container entrypoint
    ├── requirements.txt          # Python dependencies
    ├── run_app.py                # Local entrypoint
    ├── utils/
    │   ├── log_rotation_manager.py
    │   └── structured_logging.py
    ├── templates/                # Jinja2 SSR pages
    │   ├── collection.html
    │   ├── collection_logs.html
    │   ├── index.html
    │   ├── integrations.html
    │   ├── sessions.html
    │   ├── settings.html
    │   └── monitoring/dashboard.html
    └── core/
        ├── AGENTS.md
        ├── __init__.py
        ├── app.py                # Flask app factory
        ├── auth_manager.py
        ├── config.py
        ├── dashboard.py
        ├── testing_app.py
        ├── auth/
        │   ├── decorators.py
        │   ├── jwt_service.py
        │   └── middleware.py
        ├── monitoring/
        │   ├── cache_metrics.py
        │   ├── error_metrics.py
        │   └── metrics.py
        └── routes/
            ├── api_routes.py
            ├── collection_routes_simple.py
            ├── proxy_routes.py
            ├── system_routes.py
            ├── web_routes.py
            ├── websocket_routes.py
            ├── api/
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
            │   ├── monitoring/metrics.py
            │   ├── blacklist/      # batch, collection, core, management, system
            │   ├── collection/     # config, credentials, history, sources, status, sync, trigger, utils
            │   └── fortinet/       # core
```