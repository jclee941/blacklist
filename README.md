# Blacklist Service Management

> **통합 위협 인텔리전스 수집 · 동기화 · 블랙리스트 중앙 관리 · Fortinet 자동 배포 플랫폼**
> **Unified threat-intelligence aggregation, centralized blacklist management, and Fortinet deployment platform.**

---

## 목차 / Table of Contents

- [한국어](#한국어)
  - [개요](#개요)
  - [주요 기능](#주요-기능)
  - [아키텍처](#아키텍처)
  - [요청 흐름](#요청-흐름)
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
  - [Request Flow](#request-flow)
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
| 배포 전 검증 | `app/deployment_validation.py` |
| 컨테이너 정의 | `app/Dockerfile` |
| Python 의존성 | `app/requirements.txt` |
| Docker Compose | `deploy/docker-compose.yml` |
| 환경 변수 파일 | `deploy/.env` |
| 라인 길이 정책 | 120자 (Ruff) |
| 캐시·로그 회전 | `app/utils/log_rotation_manager.py` |
| 구조화 로깅 | `app/utils/structured_logging.py` |

### 주요 기능

- **중앙 집중식 블랙리스트 관리** — IP/도메인 항목의 CRUD, 일괄 처리(`batch.py`), 외부 컬렉션과의 양방향 동기화, 변경 이력 추적 (`blacklist/collection`, `blacklist/management`, `blacklist/system`).
- **위협 인텔리전스 컬렉션 자동화** — 멀티 소스 수집 파이프라인. 소스 등록·자격 증명·동기화 트리거·이력·상태를 분리된 모듈로 운영 (`collection/sources`, `credentials`, `sync`, `trigger`, `history`, `status`, `config`).
- **Fortinet 자동 배포** — Fortinet 방화벽으로의 주소 객체·정책 자동 배포 (`fortinet/core`, `routes/api/fortinet_register.py`).
- **IP 관리 도우미** — IP 레인지·CIDR·예외 처리 유틸리티 (`api/ip_management_helpers.py`).
- **인증·인가** — JWT 발급·검증, 데코레이터 기반 라우트 보호, 미들웨어 (`auth/jwt_service.py`, `auth/decorators.py`, `auth/middleware.py`, `auth_manager.py`).
- **실시간 모니터링** — 메트릭 수집·캐시 통계·에러 메트릭, WebSocket 스트림, 대시보드 템플릿 (`monitoring/metrics.py`, `cache_metrics.py`, `error_metrics.py`, `routes/websocket_routes.py`, `templates/monitoring/dashboard.html`).
- **REST API + 웹 UI** — Flask Blueprint 기반 라우트 분리 (`web_routes`, `api_routes`, `proxy_routes`, `system_routes`, `collection_routes_simple`).
- **데이터베이스 관리 API** — 마이그레이션·백업·상태 점검 엔드포인트 (`api/database_api.py`, `api/migration.py`).
- **분석·설정·통합** — 분석 대시보드, 시스템 설정, 외부 시스템 통합 UI (`api/analytics.py`, `api/settings_api.py`, `api/system_api.py`, `templates/integrations.html`, `templates/settings.html`).
- **구조화 로깅 + 자동 회전** — JSON 형식 로그와 사이즈/시간 기반 자동 회전 (`utils/structured_logging.py`, `utils/log_rotation_manager.py`).
- **세션/컬렉션 로그 뷰** — 사용자 세션 및 수집 작업 이력 시각화 (`templates/sessions.html`, `templates/collection_logs.html`).
- **테스트 분리 환경** — `testing_app.py`로 운영/테스트 앱 팩토리 분리.

### 아키텍처

애플리케이션은 **Flask 애플리케이션 팩토리 패턴** 위에 Blueprint 기반 라우트 분리와 서비스 레이어 모듈화로 구성됩니다.

**모듈 구성**

| 영역 | 위치 | 역할 |
| --- | --- | --- |
| 앱 팩토리 | `app/core/app.py` | Flask 앱 생성, Blueprint 등록, 미들웨어 와이어링 |
| 설정 | `app/core/config.py` | 환경 변수 기반 설정 로드 |
| 인증 | `app/core/auth_manager.py`, `app/core/auth/` | JWT 발급·검증, 데코레이터, 미들웨어 |
| 모니터링 | `app/core/monitoring/` | 메트릭, 캐시 통계, 에러 메트릭 |
| 라우트(웹) | `app/core/routes/web_routes.py` | Jinja2 템플릿 렌더링 (`index`, `collection`, `sessions`, `settings`, `integrations`) |
| 라우트(API) | `app/core/routes/api_routes.py`, `app/core/routes/api/` | REST API (analytics, auth, dashboard, database, error_metrics, fortinet_register, ip_management, migration, settings, system) |
| 도메인 서비스 | `app/core/routes/api/collection/`, `blacklist/`, `fortinet/` | 컬렉션·블랙리스트·Fortinet 도메인 로직 |
| 실시간 채널 | `app/core/routes/websocket_routes.py` | WebSocket 푸시 |
| 프록시 | `app/core/routes/proxy_routes.py` | 외부 시스템 프록시 |
| 시스템 라우트 | `app/core/routes/system_routes.py` | 헬스체크·시스템 정보 |
| 템플릿 | `app/templates/` | HTML 템플릿 (모니터링 대시보드 포함) |
| 유틸 | `app/utils/` | 구조화 로깅, 로그 회전 |
| 배포 | `app/Dockerfile`, `app/entrypoint.sh`, `app/deployment_validation.py` | 컨테이너 빌드·부트스트랩·사전 검증 |
| 데이터 평면 | `deploy/docker-compose.yml`, `deploy/.env` | 다중 서비스 오케스트레이션 |

**권한 모델**

| 역할 | 노출 표면 | 비고 |
| --- | --- | --- |
| 비인증 | 헬스체크(`/healthz`), 로그인 페이지 | `system_routes` |
| 일반 사용자(웹 세션) | 대시보드, 컬렉션 뷰, 세션 조회 | `auth_manager` + 데코레이터 |
| API 클라이언트(JWT) | REST API 전체 | `auth/jwt_service.py` |
| 운영자 | Fortinet 등록, DB 마이그레이션, 설정 변경 | 추가 권한 검사 |

**운영자 관측성(Observability)**

| 표면 | 위치 | 형태 |
| --- | --- | --- |
| 메트릭 | `monitoring/metrics.py`, `api/monitoring/metrics.py` | 카운터·게이지 |
| 캐시 통계 | `monitoring/cache_metrics.py` | 히트율·사이즈 |
| 에러 메트릭 | `monitoring/error_metrics.py`, `api/error_metrics_api.py` | 코드별 카운트 |
| 실시간 채널 | `websocket_routes.py` | 푸시 스트림 |
| 대시보드 | `templates/monitoring/dashboard.html` | 시각화 |
| 구조화 로그 | `utils/structured_logging.py` | JSON 라인 |
| 로그 회전 | `utils/log_rotation_manager.py` | 사이즈/시간 기반 |

### 요청 흐름

일반적인 **REST API 요청 처리**는 다음 단계로 진행됩니다.

1. 클라이언트가 JWT를 `Authorization: Bearer <token>` 헤더로 전달하며 요청을 전송합니다.
2. `auth/middleware.py`가 `auth/jwt_service.py`로 토큰을 검증하고 요청 컨텍스트에 사용자 정보를 주입합니다.
3. Flask 라우터가 `routes/api_routes.py`에 등록된 Blueprint로 요청을 전달합니다.
4. 해당 엔드포인트의 데코레이터(`auth/decorators.py`)가 역할·스코프 검사를 수행합니다.
5. 도메인 서비스(`collection/*`, `blacklist/*`, `fortinet/*`)가 비즈니스 로직을 실행합니다.
6. 응답은 JSON으로 직렬화되어 반환되며, `monitoring/metrics.py`가 호출 카운터와 지연 시간을 기록합니다.
7. 오류 발생 시 `monitoring/error_metrics.py`가 코드별 카운터를 증가시키고 구조화 로그에 기록됩니다.

**Fortinet 자동 배포 흐름**은 다음과 같습니다.

1. 운영자가 UI/API에서 동기화를 트리거(`collection/trigger.py`)합니다.
2. `collection/sync.py`가 외부 소스에서 최신 위협 인텔리전스를 가져와 정규화합니다.
3. `blacklist/core.py`가 중앙 블랙리스트를 갱신하고 변경 이력을 `blacklist/management.py`에 기록합니다.
4. `fortinet/core.py`가 변경분을 Fortinet API로 푸시하여 주소 객체·정책을 동기화합니다.
5. `api/fortinet_register.py`가 결과를 반환하고, 메트릭과 구조화 로그가 결과를 기록합니다.

### 빠른 시작

Docker Compose로 전체 스택을 띄우는 것이 권장 진입점입니다.

1. **저장소 클론 및 의존성 준비**

   ```bash
   git clone <repository-url> blacklist-service-management
   cd blacklist-service-management
   cp deploy/.env.example deploy/.env   # deploy/.env가 없는 경우에만
   ```

2. **환경 변수 편집** — `deploy/.env`에서 `PORT`, 자격 증명, Fortinet 엔드포인트 등을 설정합니다.

3. **개발 환경 기동 (핫 리로드)**

   ```bash
   make dev
   ```

   기본 포트 `2542`로 서비스가 시작되며, 코드 변경 시 볼륨 마운트를 통해 자동 재로드됩니다.

4. **접속**

   - 웹 UI: `http://localhost:2542/`
   - 헬스체크: `http://localhost:2542/healthz`

5. **로그 확인 및 종료**

   ```bash
   make logs
   make down
   ```

### 설정

`deploy/.env`가 단일 소스입니다. 주요 키는 다음과 같습니다.

| 키 | 기본값 | 설명 |
| --- | --- | --- |
| `PORT` | `2542` | 웹/API 리스닝 포트 |
| `ENV` | `development` | 실행 환경 (`development` / `production`) |
| `LOG_LEVEL` | 환경별 기본값 | 구조화 로그 레벨 |
| `JWT_SECRET` | (필수) | 토큰 서명 키 |
| `DATABASE_URL` | (필수) | 데이터베이스 연결 문자열 |
| `FORTINET_API_*` | (선택) | Fortinet 엔드포인트·자격 증명 |
| `COLLECTION_*` | (선택) | 위협 인텔리전스 소스별 자격 증명·주기 |

`app/core/config.py`가 환경 변수를 읽어 Flask 앱에 주입합니다. 운영 환경에서는 `make verify-secrets`로 누락된 시크릿을 사전 점검하세요.

### 명령어 레퍼런스

`Makefile`이 단일 진입점입니다. 전체 목록은 `make help`로 확인할 수 있습니다.

| 명령어 | 설명 |
| --- | --- |
| `make help` | 사용 가능한 타겟과 설명 출력 |
| `make setup-hooks` | pre-commit, commitlint, 프런트엔드 husky 훅 설치 |
| `make dev` | 핫 리로드 포함 개발 스택 기동 (변경 이미지 재빌드) |
| `make dev-no-build` | 기존 이미지로 빠르게 기동 |
| `make dev-prod` | 핫 리로드 없는 운영 유사 환경 |
| `make dev-app` | 앱 서비스만 재시작 |
| `make build` | 컨테이너 이미지 빌드 |
| `make up` | 스택 기동 |
| `make down` | 스택 종료 |
| `make restart` | 스택 재시작 |
| `make logs` | 컨테이너 로그 스트림 |
| `make health` | 헬스체크 |
| `make test` | 테스트 실행 |
| `make deploy` | 배포 절차 실행 |
| `make prod` | 프로덕션 모드 기동 |
| `make clean` | 빌드 산출물/캐시 정리 |
| `make verify` | 사전 검증 일괄 실행 |
| `make verify-lint` | Ruff 린트 |
| `make verify-types` | mypy 타입 체크 |
| `make verify-secrets` | 시크릿 누락 점검 |
| `make verify-pre-commit` | pre-commit 훅 전체 실행 |
| `make verify-quick` | 빠른 검증 (린트 + 타입) |
| `make verify-all` | 전체 검증 (린트 + 타입 + 시크릿 + pre-commit) |
| `make release` | 릴리스 절차 |
| `make release-dry` | 릴리스 드라이런 |

### 로컬 개발

호스트에서 직접 Python으로 실행할 수도 있습니다.

1. **의존성 설치**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r app/requirements.txt
   ```

2. **환경 변수 내보내기** — `deploy/.env`의 키를 `export` 하거나 `direnv`/`.env` 로더를 사용합니다.

3. **앱 실행**

   ```bash
   python app/run_app.py
   ```

4. **린트 및 타입 체크**

   ```bash
   ruff check .
   mypy
   ```

5. **사전 검증 훅** — 커밋 전에 자동으로 실행되도록 `make setup-hooks`로 훅을 설치하세요.

권장 도구:

- Python 3.11+
- Docker / Docker Compose v2
- pre-commit
- Ruff, mypy

### 테스트

테스트 설정은 `pyproject.toml`의 `[tool.pytest.ini_options]`에 정의되어 있습니다.

| 항목 | 값 |
| --- | --- |
| `pythonpath` | `["app"]` |
| `testpaths` | `["tests"]` |
| 파일 패턴 | `test_*.py` |
| 클래스 패턴 | `Test*` |
| 함수 패턴 | `test_*` |
| 마커 | `unit`, `integration`, `security`, `db`, `api` |
| 기본 옵션 | `-v --tb=short` |

실행 예시:

```bash
make test                                # 전체
pytest -m unit                           # 단위 테스트만
pytest -m "integration and not db"       # 통합 테스트(DB 제외)
pytest -m security                       # 보안 관련 테스트
```

### 기여 가이드

1. `make setup-hooks`로 pre-commit, commitlint, husky 훅을 설치합니다.
2. `CONTRIBUTING.md`의 가이드와 `OWNERS`의 리뷰어 정책을 따릅니다.
3. Conventional Commits(`commitlint.config.js`) 규칙을 준수합니다.
4. 변경 사항에 대한 테스트를 `tests/` 하위에 추가하고 마커를 지정합니다.
5. `make verify-all`로 린트·타입·시크릿·pre-commit을 통과시킨 뒤 PR을 올립니다.
6. 큰 변경은 `docs/` 하위에 상세 문서(Mermaid 다이어그램 포함 가능)를 추가합니다.

### 라이선스

본 저장소는 `LICENSE` 파일에 명시된 라이선스를 따릅니다.

---

## English

### Overview

**Blacklist Service Management** is a Python-based platform that aggregates threat-intelligence feeds, maintains a centralized blacklist, and pushes policies out to external security appliances such as Fortinet firewalls. It exposes a Jinja2 web UI, a REST API, and WebSocket streams for real-time monitoring and operations automation.

**Primary users**

- **SOC analysts** — unified view of threat intelligence and validation of automated blocking policies.
- **Network engineers** — automated push of address objects and policies to Fortinet and other appliances.
- **Platform operators** — single console for collections, sessions, integrations, settings, and monitoring.

**Project at a glance**

| Item | Value |
| --- | --- |
| Default port | `2542` (override via `PORT`) |
| Default environment | `development` (`ENV`) |
| Python version | 3.11+ (`target-version = "py311"`) |
| Local entry point | `app/run_app.py` |
| Container entry point | `app/entrypoint.sh` |
| Pre-deploy validation | `app/deployment_validation.py` |
| Container definition | `app/Dockerfile` |
| Python dependencies | `app/requirements.txt` |
| Docker Compose | `deploy/docker-compose.yml` |
| Environment file | `deploy/.env` |
| Line length policy | 120 chars (Ruff) |
| Cache/log rotation | `app/utils/log_rotation_manager.py` |
| Structured logging | `app/utils/structured_logging.py` |

### Features

- **Centralized blacklist management** — CRUD for IP/domain entries, batch processing, bidirectional sync with external collections, and change history (`blacklist/collection`, `blacklist/management`, `blacklist/system`).
- **Threat-intelligence collection automation** — multi-source pipeline with separate modules for sources, credentials, sync triggers, history, and status (`collection/sources`, `credentials`, `sync`, `trigger`, `history`, `status`, `config`).
- **Fortinet automated deployment** — push address objects and policies to Fortinet firewalls (`fortinet/core`, `routes/api/fortinet_register.py`).
- **IP management helpers** — CIDR/range/exception utilities (`api/ip_management_helpers.py`).
- **Authentication and authorization** — JWT issuance and verification, decorator-based route protection, and middleware (`auth/jwt_service.py`, `auth/decorators.py`, `auth/middleware.py`, `auth_manager.py`).
- **Real-time monitoring** — metrics collection, cache statistics, error metrics, WebSocket streams, and a dashboard template (`monitoring/metrics.py`, `cache_metrics.py`, `error_metrics.py`, `routes/websocket_routes.py`, `templates/monitoring/dashboard.html`).
- **REST API plus web UI** — Flask Blueprint-based separation (`web_routes`, `api_routes`, `proxy_routes`, `system_routes`, `collection_routes_simple`).
- **Database management API** — migration, backup, and health endpoints (`api/database_api.py`, `api/migration.py`).
- **Analytics, settings, and integrations** — analytics dashboard, system settings, and external-system integration UI (`api/analytics.py`, `api/settings_api.py`, `api/system_api.py`, `templates/integrations.html`, `templates/settings.html`).
- **Structured logging with rotation** — JSON-line logs with size/time-based rotation (`utils/structured_logging.py`, `utils/log_rotation_manager.py`).
- **Session and collection log views** — UI for user sessions and collection job history (`templates/sessions.html`, `templates/collection_logs.html`).
- **Testing factory separation** — `testing_app.py` keeps the operational app distinct from test fixtures.

### Architecture

The application uses a **Flask application factory** with Blueprint-based route separation and service-layer modules.

**Module map**

| Layer | Location | Responsibility |
| --- | --- | --- |
| App factory | `app/core/app.py` | Flask app creation, Blueprint registration, middleware wiring |
| Configuration | `app/core/config.py` | Environment-driven config loading |
| Authentication | `app/core/auth_manager.py`, `app/core/auth/` | JWT issuance/verification, decorators, middleware |
| Monitoring | `app/core/monitoring/` | Metrics, cache stats, error metrics |
| Web routes | `app/core/routes/web_routes.py` | Jinja2 rendering (`index`, `collection`, `sessions`, `settings`, `integrations`) |
| API routes | `app/core/routes/api_routes.py`, `app/core/routes/api/` | REST endpoints (analytics, auth, dashboard, database, error_metrics, fortinet_register, ip_management, migration, settings, system) |
| Domain services | `app/core/routes/api/collection/`, `blacklist/`, `fortinet/` | Collection, blacklist, and Fortinet domain logic |
| Realtime channel | `app/core/routes/websocket_routes.py` | WebSocket push |
| Proxy | `app/core/routes/proxy_routes.py` | External system proxy |
| System routes | `app/core/routes/system_routes.py` | Health checks and system info |
| Templates | `app/templates/` | HTML templates (including monitoring dashboard) |
| Utilities | `app/utils/` | Structured logging, log rotation |
| Deployment | `app/Dockerfile`, `app/entrypoint.sh`, `app/deployment_validation.py` | Container build, bootstrap, pre-deploy checks |
| Data plane | `deploy/docker-compose.yml`, `deploy/.env` | Multi-service orchestration |

**Permission model**

| Role | Exposed surface | Notes |
| --- | --- | --- |
| Unauthenticated | Health checks (`/healthz`), login page | `system_routes` |
| Web user (session) | Dashboard, collection views, session views | `auth_manager` + decorators |
| API client (JWT) | Full REST API | `auth/jwt_service.py` |
| Operator | Fortinet registration, DB migration, settings changes | Additional permission checks |

**Operator-facing observability**

| Surface | Location | Form |
| --- | --- | --- |
| Metrics | `monitoring/metrics.py`, `api/monitoring/metrics.py` | Counters, gauges |
| Cache stats | `monitoring/cache_metrics.py` | Hit rate, size |
| Error metrics | `monitoring/error_metrics.py`, `api/error_metrics_api.py` | Per-code counters |
| Realtime channel | `websocket_routes.py` | Push stream |
| Dashboard | `templates/monitoring/dashboard.html` | Visualization |
| Structured logs | `utils/structured_logging.py` | JSON lines |
| Log rotation | `utils/log_rotation_manager.py` | Size/time based |

### Request Flow

A typical **REST API request** flows as follows.

1. The client sends a request with `Authorization: Bearer <token>`.
2. `auth/middleware.py` validates the token via `auth/jwt_service.py` and injects the user into the request context.
3. Flask routes the request to the Blueprint registered in `routes/api_routes.py`.
4. Endpoint decorators (`auth/decorators.py`) enforce role and scope checks.
5. Domain services (`collection/*`, `blacklist/*`, `fortinet/*`) execute business logic.
6. The response is serialized to JSON and returned while `monitoring/metrics.py` records call counts and latency.
7. On error, `monitoring/error_metrics.py` increments per-code counters and writes a structured log entry.

The **Fortinet automated deployment flow** is as follows.

1. An operator triggers a sync from the UI or API (`collection/trigger.py`).
2. `collection/sync.py` pulls the latest threat intelligence from external sources and normalizes it.
3. `blacklist/core.py` updates the central blacklist and records the change in `blacklist/management.py`.
4. `fortinet/core.py` pushes the diff to Fortinet to synchronize address objects and policies.
5. `api/fortinet_register.py` returns the result, and metrics and structured logs capture the outcome.

### Quick Start

The recommended entry point is Docker Compose.

1. **Clone and prepare**

   ```bash
   git clone <repository-url> blacklist-service-management
   cd blacklist-service-management
   cp deploy/.env.example deploy/.env   # only if deploy/.env does not exist
   ```

2. **Edit environment** — set `PORT`, credentials, and Fortinet endpoints in `deploy/.env`.

3. **Start the development stack (hot reload)**

   ```bash
   make dev
   ```

   The service starts on the default port `2542`. Code changes reload automatically through volume mounts.

4. **Access**

   - Web UI: `http://localhost:2542/`
   - Health check: `http://localhost:2542/healthz`

5. **View logs and stop**

   ```bash
   make logs
   make down
   ```

### Configuration

`deploy/.env` is the single source. Key variables:

| Key | Default | Description |
| --- | --- | --- |
| `PORT` | `2542` | Web/API listening port |
| `ENV` | `development` | Runtime environment (`development` / `production`) |
| `LOG_LEVEL` | env-specific | Structured log level |
| `JWT_SECRET` | required | Token signing key |
| `DATABASE_URL` | required | Database connection string |
| `FORTINET_API_*` | optional | Fortinet endpoint and credentials |
| `COLLECTION_*` | optional | Per-source credentials and schedules |

`app/core/config.py` reads environment variables and injects them into the Flask app. In production, run `make verify-secrets` to detect missing secrets before deploy.

### Commands Reference

The `Makefile` is the single entry point. Run `make help` for the full list.

| Command | Description |
| --- | --- |
| `make help` | Show available targets with descriptions |
| `make setup-hooks` | Install pre-commit, commitlint, and frontend husky hooks |
| `make dev` | Start dev stack with hot reload (rebuilds changed images) |
| `make dev-no-build` | Start using existing images (faster) |
| `make dev-prod` | Production-like environment without hot reload |
| `make dev-app` | Restart only the app service |
| `make build` | Build container images |
| `make up` | Start the stack |
| `make down` | Stop the stack |
| `make restart` | Restart the stack |
| `make logs` | Tail container logs |
| `make health` | Run health check |
| `make test` | Run tests |
| `make deploy` | Execute deploy procedure |
| `make prod` | Start in production mode |
| `make clean` | Remove build artifacts and caches |
| `make verify` | Run all pre-deploy checks |
| `make verify-lint` | Ruff lint |
| `make verify-types` | mypy type check |
| `make verify-secrets` | Secret-missing check |
| `make verify-pre-commit` | Full pre-commit hook run |
| `make verify-quick` | Fast verification (lint + types) |
| `make verify-all` | Full verification (lint + types + secrets + pre-commit) |
| `make release` | Release procedure |
| `make release-dry` | Dry-run release |

### Local Development

You can run the app directly on the host.

1. **Install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r app/requirements.txt
   ```

2. **Export environment variables** — either `export` keys from `deploy/.env` or use a loader such as `direnv`.

3. **Run the app**

   ```bash
   python app/run_app.py
   ```

4. **Lint and type-check**

   ```bash
   ruff check .
   mypy
   ```

5. **Pre-commit hooks** — install with `make setup-hooks` so they run automatically on commit.

Recommended tooling:

- Python 3.11+
- Docker / Docker Compose v2
- pre-commit
- Ruff, mypy

### Testing

Test configuration lives under `[tool.pytest.ini_options]` in `pyproject.toml`.

| Item | Value |
| --- | --- |
| `pythonpath` | `["app"]` |
| `testpaths` | `["tests"]` |
| File pattern | `test_*.py` |
| Class pattern | `Test*` |
| Function pattern | `test_*` |
| Markers | `unit`, `integration`, `security`, `db`, `api` |
| Default options | `-v --tb=short` |

Examples:

```bash
make test                                # full suite
pytest -m unit                           # unit tests only
pytest -m "integration and not db"       # integration excluding DB
pytest -m security                       # security-focused tests
```

### Contributing

1. Install hooks with `make setup-hooks`.
2. Follow the guidelines in `CONTRIBUTING.md` and the reviewer policy in `OWNERS`.
3. Adhere to Conventional Commits (`commitlint.config.js`).
4. Add tests under `tests/` with the appropriate marker.
5. Pass `make verify-all` before opening a PR.
6. For large changes, add detailed documentation under `docs/` (Mermaid diagrams are allowed in deeper docs but not in the README landing page).

### License

This repository is distributed under the license stated in the `LICENSE` file.

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
            │   ├── blacklist/
            │   │   ├── AGENTS.md
            │   │   ├── __init__.py
            │   │   ├── batch.py
            │   │   ├── collection.py
            │   │   ├── core.py
            │   │   ├── management.py
            │   │   └── system.py
            │   └── fortinet/
            │       ├── AGENTS.md
            │       ├── __init__.py
            │       └── core.py
```

> 참고: `deploy/` 하위의 `docker-compose.yml`, `.env`, 그리고 프런트엔드 자산(`frontend/`), `tests/` 디렉터리는 본 저장소에서 함께 운용되지만, 위 트리에는 핵심 애플리케이션 코드만 명시했습니다. 전체 트리는 저장소 루트에서 `tree -L 3 -I 'node_modules|.venv'`로 확인하세요.
>
> Note: `deploy/` (compose file, `.env`), the frontend assets (`frontend/`), and `tests/` are operated alongside this repository but are omitted from the snippet above for clarity. Run `tree -L 3 -I 'node_modules|.venv'` from the repository root for the full tree.