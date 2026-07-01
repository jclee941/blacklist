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
  - [Features](#features-1)
  - [Architecture](#architecture-1)
  - [Request Flow](#request-flow)
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
| 라인 길이 정책 | 120자 (Ruff) |
| 캐시·로그 회전 | `app/utils/log_rotation_manager.py` |
| 구조화 로깅 | `app/utils/structured_logging.py` |

### 주요 기능

- **중앙 집중식 블랙리스트 관리** — IP/도메인 항목의 CRUD, 일괄 처리(`batch.py`), 외부 컬렉션과의 양방향 동기화, 변경 이력 추적 (`app/core/routes/api/blacklist/`)
- **컬렉션 동기화** — 여러 TI 소스에서 주기·수동 데이터 수집(`sources.py`), 자격 증명 관리(`credentials.py`), 동기화 트리거(`sync.py`, `trigger.py`), 실행 이력(`history.py`), 상태 모니터링(`status.py`, `config.py`)
- **Fortinet 통합** — FortiGate 주소 객체/주소 그룹 자동 등록(`fortinet_register.py`, `app/core/routes/api/fortinet/core.py`), 정책 푸시 검증
- **인증·세션 보안** — JWT 발급/검증(`app/core/auth/jwt_service.py`), 데코레이터 기반 권한 제어(`decorators.py`), 요청 미들웨어(`middleware.py`), 외부 세션 관리
- **모니터링·관측성** — 메트릭(`app/core/monitoring/metrics.py`), 캐시 메트릭(`cache_metrics.py`), 에러 메트릭(`error_metrics.py`), WebSocket 기반 실시간 스트림(`websocket_routes.py`), 대시보드 UI(`app/templates/monitoring/dashboard.html`)
- **프록시 게이트웨이** — `proxy_routes.py`를 통한 업스트림 통합 어댑터 노출
- **웹 콘솔** — 인덱스/컬렉션/세션/통합/설정/모니터링 페이지를 Jinja2 템플릿(`app/templates/*.html`)으로 제공
- **시스템 운영 API** — 헬스체크, 마이그레이션, DB 메타 정보(`system_api.py`, `database_api.py`, `migration.py`)
- **분석/설정** — 분석 대시보드(`analytics.py`), 사용자/통합 설정(`settings_api.py`), 대시보드 데이터 API(`dashboard_api.py`)

### 아키텍처

애플리케이션은 라우터, 도메인 모듈(컬렉션/블랙리스트/Fortinet), 인증·모니터링 크로스컷팅 레이어, 그리고 Jinja2 템플릿 UI로 구성됩니다. `app/core/app.py`가 Flask 앱 팩토리 역할을 하며, `run_app.py` 또는 `entrypoint.sh`가 부트스트랩합니다.

| 계층 | 모듈 | 책임 |
| --- | --- | --- |
| 부트스트랩 | `app/run_app.py`, `app/entrypoint.sh` | 환경 변수 로드, 마이그레이션 트리거, WSGI 서버 기동 |
| 앱 팩토리 | `app/core/app.py`, `app/core/config.py` | Flask 인스턴스 생성, 블루프린트 등록, 전역 미들웨어 와이어링 |
| 인증 | `app/core/auth/` | JWT 발급/검증, 권한 데코레이터, 인증 미들웨어 |
| 모니터링 | `app/core/monitoring/` | 메트릭 수집, 캐시/에러 메트릭, 헬스 체크 |
| 웹 라우트 | `app/core/routes/web_routes.py` | Jinja2 페이지 렌더링(인덱스/설정/세션 등) |
| API 라우트 | `app/core/routes/api_routes.py`, `app/core/routes/api/` | REST 엔드포인트 등록 및 버전 라우팅 |
| WebSocket | `app/core/routes/websocket_routes.py` | 실시간 메트릭/이벤트 푸시 |
| 프록시 | `app/core/routes/proxy_routes.py` | 업스트림 통합 어댑터 게이트웨이 |
| 시스템 | `app/core/routes/system_routes.py`, `api/system_api.py`, `api/migration.py` | 헬스체크, 마이그레이션, 운영 액션 |
| 컬렉션 도메인 | `app/core/routes/api/collection/` | TI 소스, 자격증명, 동기화 트리거/이력/상태 |
| 블랙리스트 도메인 | `app/core/routes/api/blacklist/` | 항목 CRUD, 일괄 처리, 외부 컬렉션 매핑 |
| Fortinet 도메인 | `app/core/routes/api/fortinet/`, `api/fortinet_register.py` | FortiGate 주소 객체/그룹 자동 등록 |
| UI 템플릿 | `app/templates/` | Jinja2 페이지, 모니터링 대시보드 |
| 로깅 | `app/utils/structured_logging.py`, `app/utils/log_rotation_manager.py` | 구조화 로그 출력, 회전 정책 |
| 보조 | `app/core/dashboard.py`, `app/core/testing_app.py`, `app/core/auth_manager.py` | 대시보드 헬퍼, 테스트 모드, 인증 매니저 |
| 배포 검증 | `app/deployment_validation.py` | 컨테이너 기동 전 환경/구성 무결성 점검 |

### 요청 흐름

1. 클라이언트가 `http://<host>:2542/`로 요청을 보내면 `entrypoint.sh`(또는 `run_app.py`)가 기동한 WSGI 서버가 수신합니다.
2. `app/core/app.py`의 Flask 팩토리가 요청을 라우터 디스패처에 위임합니다.
3. 인증이 필요한 경로는 `app/core/auth/middleware.py` → `jwt_service.py` 순으로 JWT를 검증하고, `decorators.py`로 역할 기반 권한을 부여합니다.
4. 페이지 요청은 `web_routes.py`가 처리하여 `app/templates/*.html`을 렌더링합니다.
5. API 요청은 `api_routes.py`가 `/api/...` 프리픽스로 마운트한 하위 모듈(컬렉션/블랙리스트/Fortinet/시스템/설정/분석/모니터링)로 라우팅합니다.
6. 실시간 채널은 `websocket_routes.py`가 열고, 모니터링 메트릭은 `app/core/monitoring/`이 캐시/에러 카운터를 누적합니다.
7. 외부 Fortinet 장비 등 업스트림 호출은 `proxy_routes.py` 또는 `app/core/routes/api/fortinet/core.py`가 수행하며, 요청·응답 메트릭이 모니터링 계층으로 피드백됩니다.
8. 응답은 JSON(REST/JSON-RPC) 또는 HTML(Jinja2) 또는 WebSocket 프레임으로 직렬화되어 클라이언트에 전달되며, 모든 액세스 로그는 `structured_logging`을 통해 출력되고 `log_rotation_manager`로 회전됩니다.

### 빠른 시작

**사전 요구사항**

- Docker 24+ 및 Docker Compose v2
- Python 3.11+ (컨테이너 없이 로컬 실행 시)
- GNU Make
- `deploy/.env` 파일(예시는 저장소의 `deploy/.env.example` 참고)

**1) 저장소 클론 및 환경 변수 준비**

```bash
git clone <repository-url> blacklist-service
cd blacklist-service
cp deploy/.env.example deploy/.env   # 실제 값으로 수정
```

**2) Git 훅 설치(선택)**

```bash
make setup-hooks
```

**3) 개발 환경 기동(볼륨 마운트 + 핫 리로드)**

```bash
make dev
```

- 기본 포트는 2542입니다. 변경하려면 `PORT=8080 make dev` 형태가 아닌 `deploy/.env`의 `PORT` 값을 수정하세요.
- 컨테이너 정의는 `app/Dockerfile`, Compose 정의는 `deploy/docker-compose.yml`입니다.

**4) 빌드 없이 빠르게 기동(이미지가 캐시된 경우)**

```bash
make dev-no-build
```

**5) 프로덕션-유사 기동(오버레이·핫 리로드 없음)**

```bash
make dev-prod
```

**6) 웹 UI 접속**

- 인덱스: `http://localhost:2542/`
- 컬렉션: `http://localhost:2542/collection`
- 컬렉션 로그: `http://localhost:2542/collection/logs`
- 세션: `http://localhost:2542/sessions`
- 통합: `http://localhost:2542/integrations`
- 설정: `http://localhost:2542/settings`
- 모니터링 대시보드: `http://localhost:2542/monitoring/dashboard`

### 설정

주요 환경 변수는 `deploy/.env`에서 관리합니다. 코드의 기본값은 `app/core/config.py`에 정의되어 있습니다.

| 변수 | 용도 | 기본값 |
| --- | --- | --- |
| `ENV` | 실행 환경(`development`/`production`) | `development` |
| `PORT` | 수신 포트 | `2542` |
| `SECRET_KEY` | Flask 세션/JWT 서명 키 | (필수, 환경별로 안전한 값 사용) |
| `JWT_*` | JWT 발급자/만료/시크릿 등 (`jwt_service.py` 참조) | 앱 기본 |
| `DATABASE_URL` | DB 연결 문자열 | 앱 기본 |
| `LOG_LEVEL` | 구조화 로그 레벨 | `INFO` |
| `LOG_ROTATION_*` | `log_rotation_manager.py` 회전 정책 | 앱 기본 |
| TI 소스 자격증명 | `app/core/routes/api/collection/credentials.py` 경유 | 별도 시크릿 권장 |

`Makefile`의 `ENV` 기본값은 `development`이며, 운영 환경에서는 `ENV=production`을 명시적으로 설정하세요.

### 명령어 레퍼런스

`Makefile`에 정의된 주요 타겟입니다. `make help`로 전체 목록을 확인할 수 있습니다.

| 명령어 | 설명 |
| --- | --- |
| `make help` | 사용 가능한 타겟과 설명 출력 |
| `make setup-hooks` | pre-commit + husky 훅 설치, 프론트엔드 의존성 설치 |
| `make build` | Docker 이미지 빌드 |
| `make up` | 컨테이너 기동(빌드 포함) |
| `make down` | 컨테이너 종료 및 제거 |
| `make logs` | 컨테이너 로그 스트림 |
| `make clean` | 로컬 산출물/캐시 정리 |
| `make test` | pytest 실행(`pyproject.toml`의 `addopts` 적용) |
| `make deploy` | 배포 시퀀스 실행 |
| `make dev` | 핫 리로드 개발 환경 기동(변경 이미지 재빌드) |
| `make dev-no-build` | 재빌드 없이 개발 환경 기동 |
| `make dev-prod` | 프로덕션-유사 환경 기동(오버레이 없음) |
| `make dev-app` | 앱 서비스만 재시작(빠른 이터레이션) |
| `make restart` | 서비스 재시작 |
| `make health` | 헬스 체크 |
| `make release` | 릴리스 절차 |
| `make release-dry` | 릴리스 드라이런 |
| `make verify` | 린트/타입/시크릿 검증 묶음 |
| `make verify-lint` | Ruff 린트 검증 |
| `make verify-types` | mypy 타입 검증 |
| `make verify-secrets` | 시크릿 누출 스캔 |
| `make verify-pre-commit` | pre-commit 훅 전체 실행 |
| `make verify-quick` | 빠른 검증 묶음 |
| `make verify-all` | 전체 검증 파이프라인 |

### 로컬 개발

**컨테이너 기반(권장)**

```bash
make dev
```

- 볼륨 마운트를 통해 `app/` 하위 코드 변경이 즉시 반영됩니다.
- 컨테이너 정의는 `app/Dockerfile`, 엔트리포인트 스크립트는 `app/entrypoint.sh`입니다.
- 단일 앱 서비스 재시작이 필요하면 `make dev-app`을 사용하세요.

**로컬 Python(컨테이너 없이)**

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
export ENV=development
export PORT=2542
python app/run_app.py
```

- `deployment_validation.py`가 기동 전 필수 환경/구성을 검증합니다.

**코드 품질**

- Ruff: `make verify-lint` (라인 길이 120, `target-version = "py311"`)
- mypy: `make verify-types`
- pre-commit: `make verify-pre-commit`
- 커밋 메시지 규약: `commitlint.config.js` (Conventional Commits)

### 테스트

테스트 설정은 `pyproject.toml`의 `[tool.pytest.ini_options]`에 정의되어 있습니다.

| 항목 | 값 |
| --- | --- |
| `pythonpath` | `app` |
| `testpaths` | `tests` |
| 파일 패턴 | `test_*.py` |
| 클래스 패턴 | `Test*` |
| 함수 패턴 | `test_*` |
| 기본 옵션 | `-v --tb=short` |

사용 가능한 마커

| 마커 | 설명 |
| --- | --- |
| `unit` | 외부 의존성 없는 단위 테스트 |
| `integration` | 외부 서비스가 필요한 통합 테스트 |
| `security` | 보안 관련 테스트 |
| `db` | 데이터베이스 테스트 |
| `api` | API 엔드포인트 테스트 |

**실행 예시**

```bash
make test                              # 전체
pytest -m unit                         # 단위 테스트만
pytest -m "integration and db"         # 통합 + DB 마커
pytest app/core/routes/api/collection  # 특정 경로
```

### 기여 가이드

1. 저장소를 포크하고 기능 브랜치를 생성합니다.
2. Conventional Commits 형식으로 커밋 메시지를 작성합니다 (`commitlint.config.js` 참조).
3. 변경 전 `make verify`를 통과시켜 주세요(린트/타입/시크릿).
4. PR 전 `make test`로 관련 테스트를 실행합니다.
5. 상세 정책은 `CONTRIBUTING.md`, 거버넌스는 `OWNERS`를 참고하세요.
6. 변경 이력은 `CHANGELOG.md`에 누적되며, 버전 표기는 `VERSION` 파일을 따릅니다.

### 라이선스

본 저장소는 `LICENSE` 파일에 명시된 라이선스를 따릅니다. 배포·수정 시 라이선스 전문을 반드시 확인하세요.

---

## English

### Overview

**Blacklist Service Management** is a Python-based platform that aggregates threat intelligence (malicious IPs, domains, URLs) from multiple external sources, normalizes them into a centralized blacklist, and **automatically deploys them to Fortinet firewalls and other external security appliances**. It exposes a Jinja2 web console, a REST API, and WebSocket channels for real-time monitoring and operational automation.

**Primary users**

- **SOC analysts** — unified query across threat feeds and automated blocklist validation.
- **Network engineers** — push policy / address-object updates to Fortinet devices.
- **Platform operators** — manage collections, sessions, integrations, settings, and monitoring from a single console.

**Baseline metadata**

| Item | Value |
| --- | --- |
| Default port | `2542` (override via `PORT` env var) |
| Default environment | `development` (`ENV`) |
| Python version | 3.11+ (`target-version = "py311"`) |
| Local entry point | `app/run_app.py` |
| Container entry point | `app/entrypoint.sh` |
| Pre-deployment validator | `app/deployment_validation.py` |
| Container definition | `app/Dockerfile` |
| Python dependencies | `app/requirements.txt` |
| Docker Compose | `deploy/docker-compose.yml` |
| Environment file | `deploy/.env` |
| Line length policy | 120 chars (Ruff) |
| Cache / log rotation | `app/utils/log_rotation_manager.py` |
| Structured logging | `app/utils/structured_logging.py` |

### Features

- **Centralized blacklist management** — CRUD for IP/domain entries, batch operations (`batch.py`), bidirectional sync with external collections, and change history (`app/core/routes/api/blacklist/`).
- **Collection sync** — scheduled and on-demand ingestion from multiple TI sources (`sources.py`), credential management (`credentials.py`), sync triggers (`sync.py`, `trigger.py`), run history (`history.py`), status monitoring (`status.py`, `config.py`).
- **Fortinet integration** — automated FortiGate address object / address-group registration (`fortinet_register.py`, `app/core/routes/api/fortinet/core.py`) and policy push validation.
- **Authentication & session security** — JWT issuance/verification (`app/core/auth/jwt_service.py`), decorator-based authorization (`decorators.py`), request middleware (`middleware.py`), external session management.
- **Monitoring & observability** — metrics (`app/core/monitoring/metrics.py`), cache metrics (`cache_metrics.py`), error metrics (`error_metrics.py`), real-time WebSocket stream (`websocket_routes.py`), dashboard UI (`app/templates/monitoring/dashboard.html`).
- **Proxy gateway** — upstream integration adapters exposed through `proxy_routes.py`.
- **Web console** — Jinja2 pages for index, collection, collection logs, sessions, integrations, settings, and monitoring (`app/templates/*.html`).
- **System operations API** — health checks, migrations, and DB metadata (`system_api.py`, `database_api.py`, `migration.py`).
- **Analytics & settings** — analytics dashboards (`analytics.py`), user / integration settings (`settings_api.py`), dashboard data API (`dashboard_api.py`).

### Architecture

The application is layered into routing, domain modules (collection / blacklist / Fortinet), cross-cutting concerns (auth, monitoring), and Jinja2 templates. `app/core/app.py` acts as the Flask application factory, bootstrapped by `run_app.py` or `entrypoint.sh`.

| Layer | Module | Responsibility |
| --- | --- | --- |
| Bootstrap | `app/run_app.py`, `app/entrypoint.sh` | Load env vars, trigger migrations, start WSGI server |
| App factory | `app/core/app.py`, `app/core/config.py` | Create Flask instance, register blueprints, wire middleware |
| Authentication | `app/core/auth/` | JWT issuance/verification, permission decorators, auth middleware |
| Monitoring | `app/core/monitoring/` | Metric collection, cache / error metrics, health checks |
| Web routes | `app/core/routes/web_routes.py` | Render Jinja2 pages (index, settings, sessions, etc.) |
| API routes | `app/core/routes/api_routes.py`, `app/core/routes/api/` | Register REST endpoints and version routing |
| WebSocket | `app/core/routes/websocket_routes.py` | Push real-time metrics and events |
| Proxy | `app/core/routes/proxy_routes.py` | Upstream integration adapter gateway |
| System | `app/core/routes/system_routes.py`, `api/system_api.py`, `api/migration.py` | Health checks, migrations, operational actions |
| Collection domain | `app/core/routes/api/collection/` | TI sources, credentials, sync trigger / history / status |
| Blacklist domain | `app/core/routes/api/blacklist/` | Entry CRUD, batch ops, external collection mapping |
| Fortinet domain | `app/core/routes/api/fortinet/`, `api/fortinet_register.py` | FortiGate address object / group auto-registration |
| UI templates | `app/templates/` | Jinja2 pages, monitoring dashboard |
| Logging | `app/utils/structured_logging.py`, `app/utils/log_rotation_manager.py` | Structured log output, rotation policy |
| Supporting | `app/core/dashboard.py`, `app/core/testing_app.py`, `app/core/auth_manager.py` | Dashboard helpers, test mode, auth manager |
| Deployment validation | `app/deployment_validation.py` | Pre-flight environment / configuration checks |

### Request Flow

1. A client sends a request to `http://<host>:2542/`; the WSGI server (started by `entrypoint.sh` or `run_app.py`) accepts it.
2. The Flask factory in `app/core/app.py` dispatches the request to the router.
3. Authenticated paths are processed by `app/core/auth/middleware.py` → `jwt_service.py`, with role-based permissions applied via `decorators.py`.
4. Page requests are handled by `web_routes.py`, which renders `app/templates/*.html`.
5. API requests are routed by `api_routes.py` under the `/api/...` prefix to the relevant domain modules (collection, blacklist, Fortinet, system, settings, analytics, monitoring).
6. Real-time channels are opened by `websocket_routes.py`; metrics are accumulated by `app/core/monitoring/` for cache and error counters.
7. Outbound calls to Fortinet or other upstream targets are executed by `proxy_routes.py` or `app/core/routes/api/fortinet/core.py`; request / response metrics feed back into the monitoring layer.
8. Responses are serialized as JSON (REST), HTML (Jinja2), or WebSocket frames and returned to the client. All access logs are emitted via `structured_logging` and rotated by `log_rotation_manager`.

### Quick Start

**Prerequisites**

- Docker 24+ and Docker Compose v2
- Python 3.11+ (for non-container local execution)
- GNU Make
- A `deploy/.env` file (see `deploy/.env.example` if present)

**1) Clone and prepare environment**

```bash
git clone <repository-url> blacklist-service
cd blacklist-service
cp deploy/.env.example deploy/.env   # edit with real values
```

**2) Install git hooks (optional)**

```bash
make setup-hooks
```

**3) Start the development environment (volume mount + hot reload)**

```bash
make dev
```

- The default port is `2542`. To change it, edit the `PORT` value in `deploy/.env` rather than overriding on the command line.

**4) Quick start without rebuild (when images are cached)**

```bash
make dev-no-build
```

**5) Production-like start (no override, no hot reload)**

```bash
make dev-prod
```

**6) Open the web console**

- Index: `http://localhost:2542/`
- Collection: `http://localhost:2542/collection`
- Collection logs: `http://localhost:2542/collection/logs`
- Sessions: `http://localhost:2542/sessions`
- Integrations: `http://localhost:2542/integrations`
- Settings: `http://localhost:2542/settings`
- Monitoring dashboard: `http://localhost:2542/monitoring/dashboard`

### Configuration

Primary environment variables live in `deploy/.env`. Code-level defaults are defined in `app/core/config.py`.

| Variable | Purpose | Default |
| --- | --- | --- |
| `ENV` | Runtime environment (`development` / `production`) | `development` |
| `PORT` | Listening port | `2542` |
| `SECRET_KEY` | Flask session / JWT signing key | (required, use a strong per-environment value) |
| `JWT_*` | JWT issuer / expiry / secret (see `jwt_service.py`) | app default |
| `DATABASE_URL` | Database connection string | app default |
| `LOG_LEVEL` | Structured logging level | `INFO` |
| `LOG_ROTATION_*` | Rotation policy for `log_rotation_manager.py` | app default |
| TI source credentials | Routed via `app/core/routes/api/collection/credentials.py` | use a dedicated secret store |

The Makefile defaults `ENV` to `development`. For production deployments, set `ENV=production` explicitly.

### Commands Reference

The main targets defined in the `Makefile`. Run `make help` to see the full list.

| Command | Description |
| --- | --- |
| `make help` | Print available targets with descriptions |
| `make setup-hooks` | Install pre-commit + husky hooks and frontend dependencies |
| `make build` | Build Docker images |
| `make up` | Bring containers up (including build) |
| `make down` | Stop and remove containers |
| `make logs` | Stream container logs |
| `make clean` | Remove local build artifacts / caches |
| `make test` | Run pytest (using `pyproject.toml` `addopts`) |
| `make deploy` | Run the deployment sequence |
| `make dev` | Start dev environment with hot reload (rebuilds changed images) |
| `make dev-no-build` | Start dev environment without rebuilding |
| `make dev-prod` | Start production-like environment (no override, no hot reload) |
| `make dev-app` | Restart only the app service (fast iteration) |
| `make restart` | Restart services |
| `make health` | Health check |
| `make release` | Release procedure |
| `make release-dry` | Release dry run |
| `make verify` | Run lint / type / secret checks bundle |
| `make verify-lint` | Ruff lint check |
| `make verify-types` | mypy type check |
| `make verify-secrets` | Secret-leak scan |
| `make verify-pre-commit` | Run all pre-commit hooks |
| `make verify-quick` | Quick verification bundle |
| `make verify-all` | Full verification pipeline |

### Local Development

**Container-based (recommended)**

```bash
make dev
```

- Volume mounts propagate code changes in `app/` immediately.
- Container definition: `app/Dockerfile`; entrypoint script: `app/entrypoint.sh`.
- Use `make dev-app` to restart only the app service for fast iteration.

**Local Python (without containers)**

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
export ENV=development
export PORT=2542
python app/run_app.py
```

- `deployment_validation.py` validates required environment / configuration before startup.

**Code quality**

- Ruff: `make verify-lint` (line length 120, `target-version = "py311"`)
- mypy: `make verify-types`
- pre-commit: `make verify-pre-commit`
- Commit messages: `commitlint.config.js` (Conventional Commits)

### Testing

Test configuration lives in `[tool.pytest.ini_options]` in `pyproject.toml`.

| Setting | Value |
| --- | --- |
| `pythonpath` | `app` |
| `testpaths` | `tests` |
| File pattern | `test_*.py` |
| Class pattern | `Test*` |
| Function pattern | `test_*` |
| Default options | `-v --tb=short` |

Available markers

| Marker | Description |
| --- | --- |
| `unit` | Unit tests (no external dependencies) |
| `integration` | Integration tests (require services) |
| `security` | Security-related tests |
| `db` | Database tests |
| `api` | API endpoint tests |

**Examples**

```bash
make test                              # full suite
pytest -m unit                         # unit only
pytest -m "integration and db"         # integration + db markers
pytest app/core/routes/api/collection  # specific path
```

### Contributing

1. Fork the repository and create a feature branch.
2. Write commit messages in the Conventional Commits format (see `commitlint.config.js`).
3. Before opening a PR, run `make verify` to pass lint / type / secret checks.
4. Run `make test` (or relevant subsets) to validate behavior.
5. See `CONTRIBUTING.md` for detailed policies and `OWNERS` for governance.
6. Aggregate changes in `CHANGELOG.md`; the canonical version lives in `VERSION`.

### License

This repository is licensed under the terms stated in the `LICENSE` file. Always review the full license text before redistributing or modifying.

---

## Repository Structure

```
.
├── AGENTS.md                       # Repository-level guidance for AI/code agents (internal)
├── CHANGELOG.md                    # Change log
├── CONTRIBUTING.md                 # Contribution policy
├── LICENSE                         # License terms
├── Makefile                        # dev / build / test / verify / release targets
├── OWNERS                          # Governance / reviewers
├── README.md                       # This document
├── VERSION                         # Canonical version
├── commitlint.config.js            # Conventional Commits enforcement
├── mypy.ini                        # mypy configuration
├── pyproject.toml                  # Ruff + pytest configuration
└── app/
    ├── AGENTS.md                   # App-level guidance for AI/code agents (internal)
    ├── Dockerfile                  # Container image definition
    ├── __init__.py
    ├── deployment_validation.py    # Pre-flight environment / config validator
    ├── entrypoint.sh               # Container entrypoint
    ├── requirements.txt            # Python dependencies
    ├── run_app.py                  # Local WSGI entrypoint
    ├── utils/
    │   ├── log_rotation_manager.py # Log rotation policy
    │   └── structured_logging.py   # Structured logger
    ├── templates/                  # Jinja2 UI templates
    │   ├── collection.html
    │   ├── collection_logs.html
    │   ├── index.html
    │   ├── integrations.html
    │   ├── sessions.html
    │   ├── settings.html
    │   └── monitoring/
    │       └── dashboard.html
    └── core/
        ├── AGENTS.md               # Core-module guidance (internal)
        ├── __init__.py
        ├── app.py                  # Flask app factory
        ├── auth_manager.py         # Auth manager
        ├── config.py               # Configuration loader
        ├── dashboard.py            # Dashboard helpers
        ├── testing_app.py          # Test-mode app
        ├── auth/
        │   ├── AGENTS.md
        │   ├── __init__.py
        │   ├── decorators.py       # Permission decorators
        │   ├── jwt_service.py      # JWT issuance / verification
        │   └── middleware.py       # Auth middleware
        ├── monitoring/
        │   ├── AGENTS.md
        │   ├── __init__.py
        │   ├── cache_metrics.py    # Cache hit/miss metrics
        │   ├── error_metrics.py    # Error counters
        │   └── metrics.py          # Core metrics
        └── routes/
            ├── AGENTS.md
            ├── api_routes.py                  # API blueprint entrypoint
            ├── collection_routes_simple.py    # Simplified collection routes
            ├── proxy_routes.py                # Upstream proxy gateway
            ├── system_routes.py               # System-level pages
            ├── web_routes.py                  # Web (Jinja2) routes
            ├── websocket_routes.py            # WebSocket channels
            └── api/
                ├── AGENTS.md
                ├── __init__.py
                ├── analytics.py               # Analytics endpoints
                ├── auth_routes.py             # Auth endpoints
                ├── core_api.py                # Core API helpers
                ├── dashboard_api.py           # Dashboard data API
                ├── database_api.py            # DB metadata API
                ├── error_metrics_api.py       # Error metrics API
                ├── fortinet_register.py       # Fortinet registration helper
                ├── ip_management_helpers.py   # IP utilities
                ├── migration.py               # Schema migration endpoints
                ├── settings_api.py            # Settings endpoints
                ├── system_api.py              # System endpoints
                ├── monitoring/
                │   └── __init__.py
                ├── collection/
                │   ├── AGENTS.md
                │   ├── __init__.py
                │   ├── config.py              # Collection config
                │   ├── credentials.py         # TI source credentials
                │   ├── history.py             # Sync run history
                │   ├── sources.py             # TI source adapters
                │   ├── status.py              # Collection status
                │   ├── sync.py                # Sync orchestration
                │   ├── trigger.py             # Manual sync triggers
                │   └── utils.py               # Collection helpers
                ├── blacklist/
                │   ├── AGENTS.md
                │   ├── __init__.py
                │   ├── batch.py               # Bulk operations
                │   ├── collection.py          # Collection mapping
                │   ├── core.py                # Blacklist core logic
                │   ├── management.py          # CRUD management
                │   └── system.py              # Blacklist system ops
                └── fortinet/
                    ├── AGENTS.md
                    ├── __init__.py
                    └── core.py                # FortiGate integration core