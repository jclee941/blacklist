# Blacklist Service Management

> **통합 위협 인텔리전스 수집·동기화 · 블랙리스트 중앙 관리 · Fortinet 자동 배포 플랫폼**
> **Unified threat-intel aggregation, centralized blacklist management, and Fortinet deployment platform.**

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Ruff](https://img.shields.io/badge/lint-Ruff-D7FF64?logo=ruff&logoColor=black)
![mypy](https://img.shields.io/badge/types-mypy-2A6DB2)
![Container](https://img.shields.io/badge/container-Docker%20%2F%20Compose-2496ED?logo=docker&logoColor=white)
![Commit](https://img.shields.io/badge/commits-Commitlint-F8C445?logo=conventionalcommits&logoColor=black)

---

## 한 줄 요약 · One-liner

다수의 외부 위협 인텔리전스 소스로부터 IP·도메인·URL을 수집·정규화해 중앙 블랙리스트로 통합하고, Fortinet 등 외부 보안 장비로 자동 배포하는 Python 기반 통합 관리 플랫폼입니다. Jinja2 웹 UI, REST API, WebSocket 실시간 채널을 통해 운영·모니터링을 단일 콘솔로 제공합니다.

A Python platform that aggregates external threat-intel feeds, normalizes them into a centralized blacklist, and pushes the resulting address objects to Fortinet (and similar) devices via REST API and WebSocket, with a Jinja2 web console for operations.

---

## Status · 운영 한눈표

| 항목 | 값 | 비고 · Notes |
| --- | --- | --- |
| 기본 포트 / Default port | `2542` | `PORT` 환경 변수로 변경 |
| 기본 ENV / Default env | `development` | `ENV=production` 으로 전환 |
| Python | `3.11+` | `pyproject.toml` 의 `target-version = "py311"` |
| 컨테이너 / Container | Docker + Compose | `deploy/docker-compose.yml` |
| 환경 변수 파일 / Env file | `deploy/.env` | Compose 가 자동 주입 |
| 로컬 진입점 / Local entry | `app/run_app.py` | `python app/run_app.py` |
| 컨테이너 진입점 / Container entry | `app/entrypoint.sh` | `app/Dockerfile` 에서 호출 |
| 배포 전 검증 / Pre-deploy check | `app/deployment_validation.py` | `make verify` |
| 라인 길이 / Line length | 120 | Ruff |
| 구조화 로깅 / Structured logging | `app/utils/structured_logging.py` | JSON 출력 |
| 로그 회전 / Log rotation | `app/utils/log_rotation_manager.py` | 사이즈·시간 정책 |
| 현재 단계 / Production-ready? | 운영 검증 단계 | 사내 PoC → 단계적 확대 |

---

## Compact Flow · 운영 흐름 요약

1. **수집** — 외부 위협 인텔리전스 소스 등록 (`app/core/routes/api/collection/sources.py`)
2. **동기화** — 스케줄·수동 트리거 (`app/core/routes/api/collection/sync.py`, `trigger.py`)
3. **정규화·저장** — 중앙 블랙리스트 CRUD·배치 (`app/core/routes/api/blacklist/`)
4. **이력 추적** — 변경 이력 (`app/core/routes/api/collection/history.py`, `blacklist/management.py`)
5. **외부 배포** — Fortinet 주소 객체 등록 (`app/core/routes/api/fortinet_register.py`, `app/core/routes/api/fortinet/core.py`)
6. **실시간 가시화** — WebSocket (`app/core/routes/websocket_routes.py`)
7. **모니터링** — 캐시·에러 메트릭 (`app/core/monitoring/*`)

---

## 목차 · Table of Contents

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
  - [Commands Reference](#commands-reference)
  - [Local Development](#local-development)
  - [Testing](#testing)
  - [Contributing](#contributing)
  - [License](#license)
- [Repository Structure](#repository-structure)
- [Maintainers](#maintainers)
- [Further Documentation](#further-documentation)

---

## 한국어

### 개요

**Blacklist Service Management**는 위협 인텔리전스 소스 다수에서 IP·도메인·URL 데이터를 자동 수집·동기화하고, 중앙 블랙리스트로 통합한 뒤 Fortinet 등 외부 보안 장비로 자동 배포하는 Python 기반 통합 관리 플랫폼입니다. Jinja2 웹 콘솔, REST API, WebSocket 실시간 채널을 단일 진입점(`app/run_app.py` 또는 컨테이너 `app/entrypoint.sh`)에서 제공합니다.

**핵심 사용자**

- **SOC / 보안 운영팀** — 위협 인텔리전스 통합 조회, 차단 정책 검증, 변경 이력 추적
- **네트워크 엔지니어** — Fortinet 등 외부 장비로 주소 객체(address object) 자동 배포
- **플랫폼 운영자** — 컬렉션·세션·통합·설정·모니터링을 단일 콘솔에서 관리

### First Files to Read

| 우선순위 | 파일 | 이유 |
| --- | --- | --- |
| 1 | [`app/run_app.py`](app/run_app.py) | 로컬 진입점 |
| 2 | [`app/entrypoint.sh`](app/entrypoint.sh) | 컨테이너 부트스트랩 |
| 3 | [`app/core/app.py`](app/core/app.py) | 앱 팩토리·라우트 조립 |
| 4 | [`app/core/config.py`](app/core/config.py) | 환경 변수·기본값 |
| 5 | [`app/core/auth_manager.py`](app/core/auth_manager.py) | 인증 정책 |
| 6 | [`app/core/routes/web_routes.py`](app/core/routes/web_routes.py) | UI 라우팅 |
| 7 | [`app/core/routes/api/core_api.py`](app/core/routes/api/core_api.py) | 핵심 API 조립 |
| 8 | [`app/deployment_validation.py`](app/deployment_validation.py) | 배포 전 점검 |

### 주요 기능

- **중앙 집중식 블랙리스트 관리** — IP/도메인 CRUD, 일괄 처리, 변경 이력, 외부 컬렉션과의 양방향 동기화
- **컬렉션 자동화** — 다중 소스 등록(`sources.py`), 자격 증명 안전 저장(`credentials.py`), 스케줄·수동 트리거(`sync.py`, `trigger.py`)
- **Fortinet 자동 배포** — 주소 객체 등록(`fortinet_register.py`, `api/fortinet/core.py`), 동기화 상태 추적
- **인증·인가** — JWT 발급·검증(`auth/jwt_service.py`), 미들웨어(`auth/middleware.py`), 라우트 데코레이터(`auth/decorators.py`)
- **실시간 가시화** — WebSocket 스트림(`websocket_routes.py`), Jinja2 대시보드(`templates/monitoring/dashboard.html`)
- **모니터링** — 캐시 적중률·에러 카운트(`core/monitoring/cache_metrics.py`, `error_metrics.py`), 메트릭 노출(`api/monitoring/metrics.py`)
- **운영 안정성** — 구조화 로깅(`utils/structured_logging.py`), 사이즈/시간 기반 로그 회전(`utils/log_rotation_manager.py`)
- **프록시 어댑터** — 외부 시스템 연동(`proxy_routes.py`), 통합 페이지(`templates/integrations.html`)
- **세션·설정 UI** — 세션 관리(`templates/sessions.html`), 설정(`templates/settings.html`)

### 아키텍처

#### 모듈 레이아웃

| 계층 | 경로 | 역할 |
| --- | --- | --- |
| 엔트리 | `app/run_app.py`, `app/entrypoint.sh` | 로컬·컨테이너 부트스트랩 |
| 앱 팩토리 | `app/core/app.py`, `core/testing_app.py` | 앱 인스턴스 조립, 테스트 모드 |
| 인증 | `app/core/auth/{jwt_service,middleware,decorators}.py` | JWT 발급·검증·권한 |
| 웹 라우트 | `app/core/routes/web_routes.py` | Jinja2 페이지 서빙 |
| API 라우트 | `app/core/routes/api_routes.py` | REST 진입점 |
| 도메인 API | `app/core/routes/api/{analytics,auth_routes,core_api,dashboard_api,database_api,error_metrics_api,fortinet_register,settings_api,system_api}.py` | 도메인별 REST |
| 컬렉션 도메인 | `app/core/routes/api/collection/{sources,sync,trigger,credentials,history,config,status,utils}.py` | 소스·동기화·자격증명·이력 |
| 블랙리스트 도메인 | `app/core/routes/api/blacklist/{core,batch,collection,management,system}.py` | CRUD·일괄·연계 |
| Fortinet 도메인 | `app/core/routes/api/fortinet/core.py` | 주소 객체 푸시·관리 |
| WebSocket | `app/core/routes/websocket_routes.py` | 실시간 푸시 |
| 모니터링 | `app/core/monitoring/{metrics,cache_metrics,error_metrics}.py` | 메트릭 집계·노출 |
| 템플릿 | `app/templates/**/*.html` | Jinja2 UI |
| 유틸 | `app/utils/{structured_logging,log_rotation_manager}.py` | 로깅·회전 |
| 검증 | `app/deployment_validation.py` | 배포 전 점검 |
| 컨테이너 | `app/Dockerfile` | 이미지 빌드 |

#### 요청 흐름 (HTTP)

1. `app/core/routes/web_routes.py` 또는 `api_routes.py` 가 요청을 수신합니다.
2. `app/core/auth/middleware.py` 가 토큰을 파싱하고 `jwt_service.py` 로 검증합니다.
3. 라우트별 데코레이터(`auth/decorators.py`) 가 역할 기반 접근을 강제합니다.
4. 컬렉션 트리거는 `routes/api/collection/{sources,sync,trigger}.py` 로 흐릅니다.
5. 동기화 결과는 `routes/api/blacklist/{core,batch,management}.py` 로 저장·노출됩니다.
6. 외부 장비 배포는 `routes/api/fortinet_register.py` 와 `routes/api/fortinet/core.py` 가 담당합니다.
7. WebSocket 채널이 변경 이벤트를 대시보드로 푸시합니다.
8. `core/monitoring/*` 가 캐시·에러 메트릭을 누적하고 `api/monitoring/metrics.py` 가 노출합니다.

#### 권한 매트릭스 (예시)

| 권한 | Admin | Operator | Viewer |
| --- | :---: | :---: | :---: |
| 컬렉션 소스 생성·수정 | ✓ | ✓ | — |
| 수동 동기화 트리거 | ✓ | ✓ | — |
| Fortinet 자동 배포 | ✓ | ✓ | — |
| 블랙리스트 조회 | ✓ | ✓ | ✓ |
| 사용자·설정 관리 | ✓ | — | — |

> 실제 역할명은 [`app/core/auth/decorators.py`](app/core/auth/decorators.py) 및 [`app/core/auth_manager.py`](app/core/auth_manager.py) 가 SSoT 입니다.

### 빠른 시작

**사전 요구사항**

- Docker 24+ 및 Docker Compose v2
- 로컬 직접 실행 시 Python 3.11+

**Docker Compose (권장)**

```bash
# 1) 후크 설치 (선택)
make setup-hooks

# 2) 환경 변수 준비
cp deploy/.env.example deploy/.env   # 실제 경로 확인 후 편집

# 3) 개발 환경 기동 (이미지 재빌드, 핫 리로드)
make dev
# → http://localhost:2542

# 4) 빌드 없이 빠르게 기동
make dev-no-build

# 5) 운영 유사 환경 (핫 리로드 OFF)
make dev-prod

# 6) 헬스 체크
make health

# 7) 로그 확인
make logs

# 8) 종료
make down
```

**로컬 직접 실행 (개발 워크스테이션)**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r app/requirements.txt
python app/run_app.py
```

### 설정

환경 변수는 [`app/core/config.py`](app/core/config.py) 가 SSoT 이며, Compose 경유 시 `deploy/.env` 에서 주입됩니다.

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `PORT` | `2542` | HTTP 바인딩 포트 |
| `ENV` | `development` | `development` / `production` |
| `LOG_LEVEL` | `INFO` | `structured_logging.py` 가 사용 |
| `JWT_SECRET` | (랜덤) | [`app/core/auth/jwt_service.py`](app/core/auth/jwt_service.py) 의 서명 키 |
| `JWT_TTL` | `3600` | 토큰 만료 초 |
| `BLACKLIST_DB_URL` | (로컬 SQLite) | 중앙 블랙리스트 저장소 URL |
| `FORTINET_API_URL` | (필수) | Fortinet 등록 엔드포인트 |
| `FORTINET_API_TOKEN` | (필수) | Fortinet API 토큰 |
| `LOG_ROTATION_MAX_BYTES` | `10485760` | `log_rotation_manager.py` 가 사용 |
| `LOG_ROTATION_BACKUP_COUNT` | `10` | 보관 파일 수 |

### 명령어 레퍼런스

[`Makefile`](Makefile) 가 모든 운영 진입점을 제공합니다. 컨테이너 그룹은 `deploy/docker-compose.yml` 을 사용합니다.

| 명령 | 용도 |
| --- | --- |
| `make help` | 사용 가능한 타깃과 설명 출력 |
| `make setup-hooks` | pre-commit + commitlint + 프런트 husky 설치 |
| `make build` | 컨테이너 이미지 빌드 |
| `make dev` | 개발 환경 기동 (재빌드, 핫 리로드) |
| `make dev-no-build` | 기존 이미지로 빠르게 기동 |
| `make dev-prod` | 운영 유사 모드로 기동 (핫 리로드 OFF) |
| `make dev-app` | 앱 서비스만 재기동 |
| `make up` | Compose `up -d` |
| `make down` | Compose `down` |
| `make restart` | 앱 서비스 재기동 |
| `make logs` | 서비스 로그 스트림 |
| `make health` | 헬스 체크 |
| `make test` | 테스트 실행 (pytest) |
| `make verify` | 배포 전 종합 검증 |
| `make verify-lint` | Ruff 린트 |
| `make verify-types` | mypy 타입 체크 |
| `make verify-secrets` | 시크릿 누출 점검 |
| `make verify-pre-commit` | pre-commit 훅 재실행 |
| `make verify-quick` | 빠른 검증 (린트 + 타입) |
| `make verify-all` | 전체 검증 |
| `make release` | 릴리스 빌드 |
| `make release-dry` | 릴리스 드라이런 |
| `make deploy` | 배포 |
| `make clean` | 로컬 산출물 정리 |

### 로컬 개발

1. `make setup-hooks` 로 pre-commit / commitlint / husky 를 설치합니다.
2. 브랜치 명명 규칙과 커밋 컨벤션은 [`CONTRIBUTING.md`](CONTRIBUTING.md) 와 [`commitlint.config.js`](commitlint.config.js) 를 따릅니다.
3. 코드 스타일: Ruff 120자 라인, `pyproject.toml` 의 per-file-ignores 준수.
4. 정적 분석: `make verify-types` (mypy, [`mypy.ini`](mypy.ini)).
5. 라우트·도메인 변경 시 [`app/core/routes/api/__init__.py`](app/core/routes/api/__init__.py) 의 익스포트 순서를 유지합니다.
6. UI 변경 시 [`app/templates/**`](app/templates) 의 Jinja2 템플릿을 갱신하고 라우트와 일관성을 유지합니다.
7. 변경 이력은 [`CHANGELOG.md`](CHANGELOG.md) 에 누적합니다.

### 테스트

- 테스트 러너: pytest (구성: [`pyproject.toml`](pyproject.toml) 의 `[tool.pytest.ini_options]`)
- 테스트 디렉터리: `tests/` (`testpaths`)
- 마커: `unit`, `integration`, `security`, `db`, `api`
- 실행: `make test` 또는 `pytest -m unit`

| 마커 | 용도 | 사전 조건 |
| --- | --- | --- |
| `unit` | 외부 의존성 없는 단위 테스트 | 없음 |
| `integration` | 서비스 연동 검증 | DB / Fortinet 등 가용 |
| `security` | 인증·인가·시크릿 회귀 | 테스트용 JWT 가능 |
| `db` | 저장소 마이그레이션·쿼리 회귀 | 임시 DB |
| `api` | REST·WebSocket 엔드포인트 검증 | 앱 부트 가능 |

### 기여 가이드

- 절차·브랜치·리뷰 SLA: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- 행동 강령: [`OWNERS`](OWNERS) 및 정책 문서 참조
- 커밋 컨벤션: Conventional Commits (commitlint 가 강제)
- PR 전 `make verify-quick` 통과 권장, 릴리스 전 `make verify-all`

### 라이선스

이 저장소는 [`LICENSE`](LICENSE) 파일의 조건에 따릅니다. 배포·수정 시 라이선스 전문을 우선 검토하십시오.

---

## English

### Overview

Blacklist Service Management is a Python platform that aggregates external threat-intelligence feeds, normalizes them into a centralized blacklist, and pushes resulting address objects to Fortinet (and similar) devices. It ships a Jinja2 web console, a REST API, and WebSocket live updates behind one entry point.

Primary user roles map to the personas in [개요](#개요).

### Features

- Centralized blacklist management with CRUD, batch ops, and history
- Multi-source collection with credential storage, scheduled and on-demand sync
- Automated Fortinet address-object registration
- JWT auth with middleware and route decorators
- Real-time WebSocket channel and Jinja2 dashboards
- Cache and error metrics with `/metrics`-style exposure
- Structured JSON logging and size/time-based log rotation
- Integration proxy and sessions/settings UI

### Architecture

See the module layout, request flow, and permission matrix in [아키텍처](#아키텍처). The entry surface is the app factory at [`app/core/app.py`](app/core/app.py), wired from [`app/run_app.py`](app/run_app.py) (local) or [`app/entrypoint.sh`](app/entrypoint.sh) (container). Domain modules live under [`app/core/routes/api/`](app/core/routes/api/) split by `collection/`, `blacklist/`, and `fortinet/` subpackages.

### Quick Start

```bash
make setup-hooks                 # optional, one-time
cp deploy/.env.example deploy/.env
make dev                         # http://localhost:2542
make health                      # smoke test
make verify                      # pre-deploy checks
make logs                        # tail logs
```

For local (non-container) runs use `python app/run_app.py` after installing `app/requirements.txt`. The full configuration table lives in [설정](#설정).

### Commands Reference

See [명령어 레퍼런스](#명령어-레퍼런스). Targets delegate to `deploy/docker-compose.yml`. All compose commands inherit `deploy/.env`.

### Local Development

Use the workflow in [로컬 개발](#로컬-개발). Key files: [`pyproject.toml`](pyproject.toml) (Ruff, pytest), [`mypy.ini`](mypy.ini) (types), [`commitlint.config.js`](commitlint.config.js) (commits), [`AGENTS.md`](AGENTS.md) (agent guidance).

### Testing

pytest with markers `unit`, `integration`, `security`, `db`, `api`. See [테스트](#테스트) for prerequisites per marker.

### Contributing

Follow [`CONTRIBUTING.md`](CONTRIBUTING.md) and Conventional Commits. PRs should pass `make verify-quick`; releases require `make verify-all`.

### License

See [`LICENSE`](LICENSE).

---

## Repository Structure

아래 트리는 본 저장소의 실제 최상위 레이아웃을 반영합니다. 추측으로 생성한 디렉터리는 포함하지 않습니다.

```text
./
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
    │           ├── collection/
    │           ├── fortinet/
    │           └── monitoring/
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

> 일부 서브 패키지(`blacklist/`, `collection/`, `fortinet/`, `monitoring/` 내부 모듈)는 링크 인덱스만 보입니다. 각 모듈의 세부 역할은 [아키텍처](#아키텍처) 표를 참조하십시오.

---

## Maintainers

운영·리뷰·승인 책임자는 [`OWNERS`](OWNERS) 파일이 SSoT 입니다. 코드 ownership 변경 시 PR 로 갱신하고 [`CONTRIBUTING.md`](CONTRIBUTING.md) 의 절차에 따라 알립니다.

| 역할 | 책임 |
| --- | --- |
| Maintainer | 릴리스·보안·정책 결정, [`OWNERS`](OWNERS) 관리 |
| Reviewer | 라우트·API·인증 변경 리뷰 |
| Operator | 컬렉션·배포·모니터링 운영 |

---

## Further Documentation

| 주제 | 위치 |
| --- | --- |
| 에이전트 운영 지침 | [`AGENTS.md`](AGENTS.md), [`app/AGENTS.md`](app/AGENTS.md), [`app/core/AGENTS.md`](app/core/AGENTS.md), [`app/core/auth/AGENTS.md`](app/core/auth/AGENTS.md), [`app/core/monitoring/AGENTS.md`](app/core/monitoring/AGENTS.md), [`app/core/routes/AGENTS.md`](app/core/routes/AGENTS.md), [`app/core/routes/api/AGENTS.md`](app/core/routes/api/AGENTS.md), [`app/core/routes/api/blacklist/AGENTS.md`](app/core/routes/api/blacklist/AGENTS.md), [`app/core/routes/api/collection/AGENTS.md`](app/core/routes/api/collection/AGENTS.md) |
| 릴리스 노트 | [`CHANGELOG.md`](CHANGELOG.md) |
| 기여 절차 | [`CONTRIBUTING.md`](CONTRIBUTING.md) |
| 버전 정책 | [`VERSION`](VERSION) |
| 빌드·검증 자동화 | [`Makefile`](Makefile) |
| 린트·테스트 설정 | [`pyproject.toml`](pyproject.toml), [`mypy.ini`](mypy.ini), [`commitlint.config.js`](commitlint.config.js) |
| 컨테이너 빌드 | [`app/Dockerfile`](app/Dockerfile) |
| 배포 전 점검 | [`app/deployment_validation.py`](app/deployment_validation.py) |
| 라이선스 | [`LICENSE`](LICENSE) |

> 본 README 의 링크는 모두 저장소 상대 경로입니다. 외부 GitHub 호스팅 URL 은 의도적으로 사용하지 않습니다.