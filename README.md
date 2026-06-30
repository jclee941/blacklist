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
| 의존성 | `app/requirements.txt` |
| Docker Compose | `deploy/docker-compose.yml` |
| 환경 변수 파일 | `deploy/.env` |

### 주요 기능

- **중앙 집중식 블랙리스트 관리** — IP/도메인 항목의 CRUD, 일괄 처리(`batch.py`), 외부 컬렉션과의 양방향 동기화, 변경 이력 추적 (`app/core/routes/api/blacklist/`)
- **컬렉션 동기화** — 여러 TI 소스에서 주기·수동 데이터 수집(`sources.py`), 자격 증명 관리(`credentials.py`), 동기화 트리거(`sync.py`, `trigger.py`), 실행 이력(`history.py`), 상태 모니터링(`status.py`)
- **Fortinet 자동 배포** — Fortinet 디바이스 등록(`fortinet_register.py`), 코어 동기화 로직(`fortinet/core.py`), 정책/주소 객체 배포 API
- **인증·인가** — JWT 기반 토큰 서비스(`jwt_service.py`), 데코레이터 기반 권한 검사(`decorators.py`), 인증 미들웨어(`middleware.py`), 세션 관리
- **모니터링·관측성** — 메트릭 수집(`metrics.py`), 캐시 메트릭(`cache_metrics.py`), 에러 메트릭(`error_metrics.py`), 대시보드(`dashboard.py`), 구조화 로깅(`structured_logging.py`), 로그 로테이션(`log_rotation_manager.py`)
- **웹 UI** — Jinja2 템플릿 기반 대시보드(`dashboard.html`), 컬렉션/로그/세션/통합/설정 화면 제공
- **REST API & WebSocket** — 컬렉션·블랙리스트·Fortinet·분석·설정·시스템·DB 엔드포인트, 실시간 푸시 알림(`websocket_routes.py`)
- **프록시·시스템 라우트** — 외부 시스템 연동 프록시(`proxy_routes.py`), 시스템 메타 라우트(`system_routes.py`)

### 아키텍처

**디렉터리 구성 요약**

| 경로 | 책임 |
| --- | --- |
| `app/run_app.py` | 로컬 개발용 앱 부트스트랩 |
| `app/entrypoint.sh` | 컨테이너 시작 스크립트 |
| `app/deployment_validation.py` | 배포 전 환경/설정 검증 |
| `app/core/app.py` | Flask 앱 팩토리 및 글로벌 초기화 |
| `app/core/config.py` | 환경 변수 기반 설정 로더 |
| `app/core/auth_manager.py` | 인증 매니저 (JWT/세션 조율) |
| `app/core/dashboard.py` | 대시보드 백엔드 로직 |
| `app/core/testing_app.py` | 테스트 모드 앱 팩토리 |
| `app/core/auth/` | JWT 서비스, 데코레이터, 미들웨어 |
| `app/core/monitoring/` | 메트릭, 캐시·에러 메트릭 |
| `app/core/routes/web_routes.py` | Jinja2 페이지 라우트 |
| `app/core/routes/api_routes.py` | REST API 라우트 등록 |
| `app/core/routes/websocket_routes.py` | WebSocket 라우트 |
| `app/core/routes/proxy_routes.py` | 외부 시스템 프록시 라우트 |
| `app/core/routes/system_routes.py` | 시스템 헬스/메타 라우트 |
| `app/core/routes/collection_routes_simple.py` | 컬렉션 심플 라우트 |
| `app/core/routes/api/collection/` | 컬렉션 API (`sources`, `sync`, `trigger`, `history`, `status`, `credentials`, `config`, `utils`) |
| `app/core/routes/api/blacklist/` | 블랙리스트 API (`core`, `collection`, `management`, `batch`, `system`) |
| `app/core/routes/api/fortinet/` | Fortinet 연동 API (`core`, 등록) |
| `app/core/routes/api/monitoring/metrics.py` | 모니터링 메트릭 API |
| `app/core/routes/api/auth_routes.py` | 인증 API |
| `app/core/routes/api/analytics.py` | 분석 API |
| `app/core/routes/api/core_api.py` | 코어 API |
| `app/core/routes/api/dashboard_api.py` | 대시보드 API |
| `app/core/routes/api/database_api.py` | DB API |
| `app/core/routes/api/error_metrics_api.py` | 에러 메트릭 API |
| `app/core/routes/api/ip_management_helpers.py` | IP 관리 헬퍼 |
| `app/core/routes/api/migration.py` | 스키마/데이터 마이그레이션 API |
| `app/core/routes/api/settings_api.py` | 설정 API |
| `app/core/routes/api/system_api.py` | 시스템 API |
| `app/templates/` | Jinja2 페이지 템플릿 (`index`, `collection`, `collection_logs`, `sessions`, `integrations`, `settings`, `monitoring/dashboard`) |
| `app/utils/` | 구조화 로깅, 로그 로테이션 매니저 |
| `deploy/docker-compose.yml` | 컨테이너 오케스트레이션 |
| `deploy/.env` | 환경 변수 정의 |

**요청 흐름 (웹 페이지)**

1. 브라우저 → `web_routes.py`의 페이지 라우트 호출
2. 라우트 핸들러가 필요한 경우 `api/` 하위 모듈(컬렉션/블랙리스트/Fortinet/분석)을 호출
3. `auth/` 계층이 JWT/세션을 검증하고 권한 데코레이터 적용
4. `monitoring/` 계층이 메트릭을 수집하고 캐시/에러 카운터를 갱신
5. `dashboard.py` 또는 페이지 전용 로직이 데이터를 가공
6. Jinja2 템플릿(`app/templates/`)이 응답을 렌더링

**요청 흐름 (REST API)**

1. 클라이언트 → `api_routes.py`에 마운트된 엔드포인트 호출
2. `auth/middleware.py`가 인증 컨텍스트를 주입
3. 해당 도메인 모듈(`blacklist/`, `collection/`, `fortinet/`)이 비즈니스 로직 수행
4. 결과는 JSON으로 반환되며, `monitoring/metrics.py`에 카운터/히스토그램 기록

**요청 흐름 (WebSocket)**

1. 클라이언트 → `websocket_routes.py` 핸드셰이크
2. 인증 후 구독 채널(컬렉션 상태, 로그, 배포 진행률 등) 등록
3. 백그라운드 워커가 변경 이벤트를 푸시

### 빠른 시작

**사전 요구사항**

| 항목 | 버전/비고 |
| --- | --- |
| Docker / Docker Compose | v2 이상 권장 |
| Python (로컬 실행 시) | 3.11+ |
| Node.js (프론트엔드 훅) | 프론트엔드 디렉터리 사용 시 |

**1) 환경 변수 파일 준비**

`deploy/.env.example`이 있다면 다음 명령으로 복사 후 값을 채웁니다.

```bash
cp deploy/.env.example deploy/.env
# 그 후 deploy/.env 수정 (PORT, ENV, DB, JWT SECRET 등)
```

**2) 개발 환경 기동 (핫 리로드)**

```bash
make dev
```

- 기본 URL: `http://localhost:2542`
- 코드 변경 시 볼륨 마운트로 자동 리로드

**3) 기존 이미지로 빠르게 기동**

```bash
make dev-no-build
```

**4) 프로덕션-유사 모드 (핫 리로드 없음)**

```bash
make dev-prod
```

### 설정

주요 환경 변수 (예시, 실제 키는 `deploy/.env` 참조)

| 변수 | 설명 | 기본값 |
| --- | --- | --- |
| `PORT` | 앱 리슨 포트 | `2542` |
| `ENV` | 실행 환경 (`development` / `production` / `testing`) | `development` |
| `JWT_SECRET` | JWT 서명 비밀키 | (필수, 변경 권장) |
| `JWT_EXPIRES_IN` | 토큰 만료 시간 | (설정 파일 참조) |
| `LOG_LEVEL` | 로그 레벨 (`DEBUG`/`INFO`/`WARNING`/`ERROR`) | `INFO` |
| `LOG_DIR` | 로그 파일 경로 | (설정 파일 참조) |
| DB 관련 키 | 데이터베이스 접속 정보 | (설정 파일 참조) |
| Fortinet 관련 키 | Fortinet API 토큰/엔드포인트 | (설정 파일 참조) |
| 컬렉션 소스 키 | 각 TI 소스 API 키/자격 증명 | (설정 파일 참조) |

설정 로더는 `app/core/config.py`에 있으며, 환경 변수 미설정 시 안전한 기본값 또는 명시적 오류로 동작합니다.

### 명령어 레퍼런스

`Makefile`은 다음 타겟을 제공합니다 (발췌). 전체 목록은 `make help`로 확인하세요.

| 타겟 | 용도 |
| --- | --- |
| `make help` | 사용 가능한 타겟과 설명 출력 |
| `make setup-hooks` | pre-commit/Commitlint/Husky 훅 설치 |
| `make dev` | 핫 리로드 포함 개발 환경 기동 (이미지 리빌드) |
| `make dev-no-build` | 기존 이미지로 개발 환경 기동 |
| `make dev-prod` | 핫 리로드 없이 프로덕션-유사 환경 기동 |
| `make dev-app` | 앱 서비스만 재시작 |
| `make build` | 컨테이너 이미지 빌드 |
| `make up` | 컨테이너 기동 |
| `make down` | 컨테이너 종료 |
| `make restart` | 컨테이너 재시작 |
| `make logs` | 컨테이너 로그 스트림 |
| `make health` | 헬스 체크 |
| `make test` | 테스트 실행 |
| `make clean` | 로컬 산출물/캐시 정리 |
| `make deploy` | 배포 절차 실행 |
| `make release` | 릴리스 절차 |
| `make release-dry` | 릴리스 드라이런 |
| `make verify` | 일반 검증 |
| `make verify-lint` | 린트(Ruff) 검증 |
| `make verify-types` | 타입 검사(mypy) |
| `make verify-secrets` | 시크릿 누출 검사 |
| `make verify-pre-commit` | pre-commit 훅 전체 실행 |
| `make verify-quick` | 빠른 검증 스위트 |
| `make verify-all` | 전체 검증 스위트 |

### 로컬 개발

**Python 의존성 설치**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
pip install pre-commit
```

**앱 로컬 실행**

```bash
# 환경 변수 주입 후
python app/run_app.py
```

**배포 전 검증**

```bash
python app/deployment_validation.py
# 또는
make verify-all
```

**린트 / 타입 검사**

```bash
ruff check .
mypy .
```

**Git 훅 설치**

```bash
make setup-hooks
```

### 테스트

`pyproject.toml`의 pytest 설정에 따라 다음 마커를 사용합니다.

| 마커 | 의미 |
| --- | --- |
| `unit` | 외부 의존성 없는 단위 테스트 |
| `integration` | 외부 서비스가 필요한 통합 테스트 |
| `security` | 보안 관련 테스트 |
| `db` | 데이터베이스 테스트 |
| `api` | API 엔드포인트 테스트 |

**전체 테스트 실행**

```bash
make test
# 또는
pytest
```

**특정 마커만 실행**

```bash
pytest -m unit
pytest -m integration
pytest -m api
```

### 기여 가이드

- 커밋 메시지는 [Conventional Commits](https://www.conventionalcommits.org/)를 따르며, `commitlint.config.js`로 강제됩니다.
- 코드 스타일은 `ruff` (line-length 120, py311)를 기준으로 합니다.
- 타입은 `mypy`로 검증합니다.
- PR 전 `make verify-all` 통과를 권장합니다.
- 이슈/PR 템플릿, 라벨 정책 등 거버넌스 파일은 저장소 최상위(예: `CONTRIBUTING.md`)를 따릅니다.

### 라이선스

본 저장소는 `LICENSE` 파일에 명시된 라이선스를 따릅니다.

---

## English

### Overview

**Blacklist Service Management** is a Python-based unified platform that aggregates threat-intelligence data (malicious IPs, domains, URLs) from multiple external sources, manages them as a centralized blacklist, and **automatically deploys them to external security devices such as Fortinet firewalls**. It provides a Jinja2-based web UI, REST API, and WebSocket for real-time monitoring and operational automation.

**Primary users**

- **Security Operations (SOC)** — unified TI lookup and automated blocking-policy validation
- **Network Engineers** — automated deployment of policies/address objects to Fortinet and similar devices
- **Platform Operators** — single console for collections, sessions, integrations, settings, and monitoring

**Basic information**

| Item | Value |
| --- | --- |
| Default port | `2542` (overridable via `PORT`) |
| Default environment | `development` (`ENV`) |
| Python | 3.11+ (`target-version = "py311"`) |
| Local entrypoint | `app/run_app.py` |
| Container entrypoint | `app/entrypoint.sh` |
| Pre-deploy validation | `app/deployment_validation.py` |
| Container definition | `app/Dockerfile` |
| Dependencies | `app/requirements.txt` |
| Docker Compose | `deploy/docker-compose.yml` |
| Env file | `deploy/.env` |

### Features

- **Centralized blacklist management** — CRUD for IP/domain entries, batch processing (`batch.py`), bidirectional sync with external collections, change-history tracking (`app/core/routes/api/blacklist/`)
- **Collection sync** — scheduled/on-demand ingestion from multiple TI sources (`sources.py`), credential management (`credentials.py`), sync triggers (`sync.py`, `trigger.py`), run history (`history.py`), status monitoring (`status.py`)
- **Fortinet auto-deployment** — device registration (`fortinet_register.py`), core sync logic (`fortinet/core.py`), policy/address-object deployment endpoints
- **AuthN / AuthZ** — JWT service (`jwt_service.py`), decorator-based authorization (`decorators.py`), auth middleware (`middleware.py`), session management
- **Observability** — metrics collection (`metrics.py`), cache metrics (`cache_metrics.py`), error metrics (`error_metrics.py`), dashboard backend (`dashboard.py`), structured logging (`structured_logging.py`), log rotation (`log_rotation_manager.py`)
- **Web UI** — Jinja2 templates for dashboard, collection, collection logs, sessions, integrations, and settings
- **REST API & WebSocket** — endpoints for collection, blacklist, Fortinet, analytics, settings, system, and database; realtime push via `websocket_routes.py`
- **Proxy & system routes** — external integration proxy (`proxy_routes.py`), system meta routes (`system_routes.py`)

### Architecture

**Module map**

| Path | Responsibility |
| --- | --- |
| `app/run_app.py` | Local development bootstrap |
| `app/entrypoint.sh` | Container startup script |
| `app/deployment_validation.py` | Pre-deploy env/config validation |
| `app/core/app.py` | Flask app factory and global init |
| `app/core/config.py` | Env-driven config loader |
| `app/core/auth_manager.py` | Auth manager (JWT/session orchestration) |
| `app/core/dashboard.py` | Dashboard backend logic |
| `app/core/testing_app.py` | Test-mode app factory |
| `app/core/auth/` | JWT service, decorators, middleware |
| `app/core/monitoring/` | Metrics, cache & error counters |
| `app/core/routes/web_routes.py` | Jinja2 page routes |
| `app/core/routes/api_routes.py` | REST API mounting |
| `app/core/routes/websocket_routes.py` | WebSocket routes |
| `app/core/routes/proxy_routes.py` | External-system proxy routes |
| `app/core/routes/system_routes.py` | System health/meta routes |
| `app/core/routes/collection_routes_simple.py` | Simple collection routes |
| `app/core/routes/api/collection/` | Collection API (`sources`, `sync`, `trigger`, `history`, `status`, `credentials`, `config`, `utils`) |
| `app/core/routes/api/blacklist/` | Blacklist API (`core`, `collection`, `management`, `batch`, `system`) |
| `app/core/routes/api/fortinet/` | Fortinet integration API (`core`, registration) |
| `app/core/routes/api/monitoring/metrics.py` | Monitoring metrics API |
| `app/core/routes/api/auth_routes.py` | Auth API |
| `app/core/routes/api/analytics.py` | Analytics API |
| `app/core/routes/api/core_api.py` | Core API |
| `app/core/routes/api/dashboard_api.py` | Dashboard API |
| `app/core/routes/api/database_api.py` | Database API |
| `app/core/routes/api/error_metrics_api.py` | Error metrics API |
| `app/core/routes/api/ip_management_helpers.py` | IP management helpers |
| `app/core/routes/api/migration.py` | Schema/data migration API |
| `app/core/routes/api/settings_api.py` | Settings API |
| `app/core/routes/api/system_api.py` | System API |
| `app/templates/` | Jinja2 page templates (`index`, `collection`, `collection_logs`, `sessions`, `integrations`, `settings`, `monitoring/dashboard`) |
| `app/utils/` | Structured logging, log rotation manager |
| `deploy/docker-compose.yml` | Container orchestration |
| `deploy/.env` | Environment variables |

**Request flow — web page**

1. Browser hits a page route in `web_routes.py`
2. The handler calls `api/` submodules (collection / blacklist / Fortinet / analytics) as needed
3. `auth/` layer validates JWT/session and applies authorization decorators
4. `monitoring/` layer records metrics and updates cache/error counters
5. `dashboard.py` or page-specific logic shapes the data
6. Jinja2 templates (`app/templates/`) render the response

**Request flow — REST API**

1. Client invokes an endpoint mounted by `api_routes.py`
2. `auth/middleware.py` injects the auth context
3. The domain module (`blacklist/`, `collection/`, `fortinet/`) executes business logic
4. Result is returned as JSON, and counters/histograms are recorded in `monitoring/metrics.py`

**Request flow — WebSocket**

1. Client completes handshake via `websocket_routes.py`
2. After auth, the client subscribes to channels (collection status, logs, deploy progress, …)
3. Background workers push change events to subscribers

### Quick Start

**Prerequisites**

| Item | Version / Note |
| --- | --- |
| Docker / Docker Compose | v2 or newer recommended |
| Python (for local run) | 3.11+ |
| Node.js (for frontend hooks) | Required only when using the frontend directory |

**1) Prepare env file**

```bash
cp deploy/.env.example deploy/.env
# Then edit deploy/.env (PORT, ENV, DB, JWT secret, etc.)
```

**2) Start development (hot reload)**

```bash
make dev
```

- Default URL: `http://localhost:2542`
- Code changes are auto-reloaded via volume mounts

**3) Start without rebuild (fast)**

```bash
make dev-no-build
```

**4) Production-like mode (no hot reload)**

```bash
make dev-prod
```

### Configuration

Key environment variables (examples — refer to `deploy/.env` for the actual set).

| Variable | Description | Default |
| --- | --- | --- |
| `PORT` | Listen port | `2542` |
| `ENV` | Runtime environment (`development` / `production` / `testing`) | `development` |
| `JWT_SECRET` | JWT signing secret | (required, change in production) |
| `JWT_EXPIRES_IN` | Token expiration | (see config) |
| `LOG_LEVEL` | Log level (`DEBUG`/`INFO`/`WARNING`/`ERROR`) | `INFO` |
| `LOG_DIR` | Log file directory | (see config) |
| DB variables | Database connection | (see config) |
| Fortinet variables | Fortinet API token / endpoint | (see config) |
| Collection source variables | Per-source TI API keys / credentials | (see config) |

The config loader lives in `app/core/config.py`. Missing required values fall back to safe defaults or fail loudly.

### Commands Reference

`Makefile` provides the following targets (excerpt). Run `make help` for the full list.

| Target | Purpose |
| --- | --- |
| `make help` | List available targets with descriptions |
| `make setup-hooks` | Install pre-commit / Commitlint / Husky hooks |
| `make dev` | Start dev environment with hot reload (rebuild) |
| `make dev-no-build` | Start dev environment using existing images |
| `make dev-prod` | Production-like start (no hot reload) |
| `make dev-app` | Restart only the app service |
| `make build` | Build container images |
| `make up` | Start containers |
| `make down` | Stop containers |
| `make restart` | Restart containers |
| `make logs` | Stream container logs |
| `make health` | Run health checks |
| `make test` | Run tests |
| `make clean` | Clean local artifacts/cache |
| `make deploy` | Run deployment procedure |
| `make release` | Release procedure |
| `make release-dry` | Release dry-run |
| `make verify` | Generic verification |
| `make verify-lint` | Lint (Ruff) |
| `make verify-types` | Type check (mypy) |
| `make verify-secrets` | Secret-leak check |
| `make verify-pre-commit` | Run all pre-commit hooks |
| `make verify-quick` | Quick verification suite |
| `make verify-all` | Full verification suite |

### Local Development

**Install Python dependencies**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
pip install pre-commit
```

**Run app locally**

```bash
# After exporting required env vars
python app/run_app.py
```

**Pre-deploy validation**

```bash
python app/deployment_validation.py
# or
make verify-all
```

**Lint / type-check**

```bash
ruff check .
mypy .
```

**Install git hooks**

```bash
make setup-hooks
```

### Testing

Per `pyproject.toml` pytest configuration, the following markers are available.

| Marker | Meaning |
| --- | --- |
| `unit` | Unit tests with no external dependencies |
| `integration` | Integration tests requiring external services |
| `security` | Security-related tests |
| `db` | Database tests |
| `api` | API endpoint tests |

**Run all tests**

```bash
make test
# or
pytest
```

**Run by marker**

```bash
pytest -m unit
pytest -m integration
pytest -m api
```

### Contributing

- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/), enforced by `commitlint.config.js`.
- Code style follows `ruff` (line-length 120, py311).
- Types are checked with `mypy`.
- Run `make verify-all` before opening a PR.
- Follow the governance files at the repository root (e.g. `CONTRIBUTING.md`) for issue/PR templates and label policy.

### License

This repository is distributed under the license described in the `LICENSE` file.

---

## Repository Structure

```text
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
    │           ├── blacklist/
    │           │   ├── AGENTS.md
    │           │   ├── __init__.py
    │           │   ├── batch.py
    │           │   ├── collection.py
    │           │   ├── core.py
    │           │   ├── management.py
    │           │   └── system.py
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
    │           ├── fortinet/
    │           │   ├── AGENTS.md
    │           │   ├── __init__.py
    │           │   └── core.py
    │           └── monitoring/
    │               └── __init__.py
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