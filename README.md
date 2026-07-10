# Blacklist Service

[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/flask-3.x-lightgrey.svg)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-see%20LICENSE-blue.svg)](./LICENSE)

> IP 차단 목록(블랙리스트)을 통합 관리하고 Fortinet 등 방화벽으로 자동 배포하는 웹 서비스입니다.
> A Flask-based service for managing IP blocklists, syncing collection sources, and pushing policy to Fortinet-style firewalls.

## 개요 / Overview

블랙리스트 데이터 소스에서 IP를 수집하고, 정책(레퍼레이션)을 만들어 Fortinet 장비에 자동 등록하며, 모든 변경을 웹 대시보드와 WebSocket으로 모니터링합니다. 소규모 보안 운영팀이 단일 진입점에서 차단 정책을 운영하도록 설계되었습니다.

The service collects IPs from external feeds, normalizes them, and pushes the result to registered Fortinet devices. It exposes a web dashboard, REST API, and WebSocket channel for live updates.

## 한눈 보기 / At a Glance

| 항목 / Item       | 값 / Value                                                         |
| ----------------- | ------------------------------------------------------------------ |
| 제품 / Product    | Blacklist management web service                                   |
| 진입점 / Entry    | `app/run_app.py` → `app/core/app.py` (Flask factory)               |
| 기본 포트         | `2542` (Makefile `PORT`)                                           |
| 인증 / Auth       | JWT (`app/core/auth/jwt_service.py`) with cookie or `Authorization` header |
| 실시간 채널       | WebSocket (`app/core/routes/websocket_routes.py`)                  |
| 데이터 소스       | `app/core/routes/api/collection/` (sources, sync, trigger)         |
| 방화벽 연동       | Fortinet register (`app/core/routes/api/fortinet/core.py`)         |
| 컨테이너          | `app/Dockerfile` + `deploy/docker-compose.yml`                     |
| 기본 명령         | `make dev` (hot reload) / `make build up`                          |

## 운영 흐름 / Operational Flow

1. 운영자가 대시보드에서 **Collection Source**를 등록합니다 → `app/core/routes/api/collection/sources.py`.
2. 스케줄러 또는 수동 `trigger`가 외부 피드에서 IP를 수집·중복 제거합니다 → `collection/sync.py`, `collection/trigger.py`.
3. 수집 결과는 **Blacklist Management**로 전달되어 정책(레퍼레이션 단위)을 구성합니다 → `blacklist/management.py`.
4. 정책은 **Fortinet Integration**을 통해 등록된 방화벽으로 푸시됩니다 → `fortinet/core.py`.
5. **Monitoring** 모듈이 캐시, 에러, 처리량을 수집하고 `/api/metrics` 및 WebSocket으로 노출합니다 → `monitoring/metrics.py`, `monitoring/cache_metrics.py`, `monitoring/error_metrics.py`.
6. 운영자는 **Settings / Sessions** 화면에서 인증·세션·통합 상태를 관리합니다 → `api/settings_api.py`, templates `sessions.html`, `settings.html`.

---

## 목차 / Table of Contents

- [Purpose and Package Contents](#purpose-and-package-contents)
- [Status](#status)
- [First Files to Read](#first-files-to-read)
- [API and Entry Points](#api-and-entry-points)
- [Quickstart](#quickstart)
- [Commands Reference](#commands-reference)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Local Development](#local-development)
- [Testing](#testing)
- [Contribution Guide](#contribution-guide)
- [Maintainers](#maintainers)
- [Further Documentation](#further-documentation)

---

## Purpose and Package Contents

블랙리스트 서비스는 차단 IP의 수집·정규화·정책화·배포를 한 화면에서 다룹니다. 다음을 한 번에 제공합니다.

- 여러 **컬렉션 소스**를 등록하고 일정/수동으로 동기화
- 소스 결과를 **블랙리스트 정책**으로 그룹핑 (라벨, 만료, 메모)
- 등록된 **Fortinet** 방화벽으로 정책 배포
- **JWT 인증**, 세션 관리, 역할 기반 데코레이터
- **모니터링 지표**(캐시, 에러율, 카운터)와 Grafana/Prometheus 호환 출력
- 운영자가 사용하는 **웹 대시보드** 템플릿 + REST/JSON API + WebSocket

The product packages the full blacklist lifecycle into a single Flask application with both a web UI and a JSON/WS API.

### 디렉터리 / Top-level Layout

| 경로                  | 역할                                                         |
| --------------------- | ------------------------------------------------------------ |
| `app/`                | Flask 앱 진입점·런처 (`run_app.py`) 및 Dockerfile            |
| `app/core/`           | 핵심 코어: 앱 팩토리, 인증, 라우트, 모니터링                 |
| `app/core/auth/`      | JWT 발급·검증, 인증 데코레이터, 미들웨어                      |
| `app/core/routes/`    | 웹/웹소켓/API 라우트                                         |
| `app/core/routes/api/`| 기능별 API 블루프린트 (analytics, collection, blacklist, fortinet, monitoring 등) |
| `app/templates/`      | Jinja2 웹 페이지 템플릿 (대시보드, 컬렉션, 통합, 세션, 설정)  |
| `app/utils/`          | 로테이션 가능한 구조화 로깅(`structured_logging.py`, `log_rotation_manager.py`) |
| `Makefile`            | 개발·검증·릴리스 명령 (dev / build / test / verify / release) |
| `pyproject.toml`      | pytest/ruff 설정, `pythonpath = ["app"]`                     |
| `mypy.ini`            | 타입 검사 설정                                               |
| `commitlint.config.js`| 커밋 메시지 컨벤션 검사                                      |
| `deploy/`             | docker-compose, 환경 파일 (Makefile이 참조)                  |

---

## Status

| 항목 / Area       | 상태 / Status                                              |
| ----------------- | ---------------------------------------------------------- |
| 전체 / Overall    | 운영 가능(preview / 내부 1차 배포 권장). 테스트 통과 기준. |
| 인증 / Auth       | JWT 기반, 데코레이터/미들웨어로 보호                        |
| 데이터 영속화     | 외부 DB 어댑터 사용 (코드 구조상 API 경유)                  |
| 운영 도구         | Make 타깃: `dev`, `build`, `up`, `down`, `test`, `verify*` |
| 릴리스            | `make release`, `make release-dry`로 태그 드래프트 생성    |
| deprecation 표지  | 없음 (현행 마스터)                                         |

---

## First Files to Read

이 순서로 보면 백엔드 구조를 빠르게 파악할 수 있습니다.

1. `app/run_app.py` — 런처 (Gunicorn/로컬 진입점)
2. `app/core/app.py` — Flask 앱 팩토리, 블루프린트 등록, 미들웨어 체인
3. `app/core/config.py` — 환경 변수 기반 설정
4. `app/core/auth/jwt_service.py` + `auth/decorators.py` + `auth/middleware.py` — 인증의 세 조각
5. `app/core/routes/web_routes.py` + `app/core/routes/api_routes.py` — 라우트 표면
6. `app/core/routes/api/collection/` — 핵심 도메인(소스/동기화/트리거)
7. `app/core/routes/api/blacklist/` — 정책 관리
8. `app/core/routes/api/fortinet/core.py` — 방화벽 푸시
9. `app/core/monitoring/metrics.py` — 메트릭 수집·내보내기
10. `app/templates/index.html` 및 `monitoring/dashboard.html` — UI 골격

---

## API and Entry Points

### HTTP 라우트 (Blueprint)

| Blueprint 모듈                          | Prefix           | 설명                                  |
| ---------------------------------------- | ----------------- | ------------------------------------- |
| `app.core.routes.web_routes`             | `/`               | 대시보드·페이지                       |
| `app.core.routes.api_routes`             | `/api`            | 상위 API 디스패치                      |
| `app.core.routes.api.auth_routes`        | `/api/auth`       | 로그인·토큰 발급·갱신                  |
| `app.core.routes.api.collection.*`       | `/api/collection` | 컬렉션 소스/동기화/트리거/이력/상태    |
| `app.core.routes.api.blacklist.*`        | `/api/blacklist`  | 정책 관리·배치·시스템                  |
| `app.core.routes.api.fortinet.core`      | `/api/fortinet`   | Fortinet 등록·동기화 푸시             |
| `app.core.routes.api.dashboard_api`      | `/api/dashboard`  | 대시보드 요약                         |
| `app.core.routes.api.system_api`         | `/api/system`     | 시스템 헬스·버전                      |
| `app.core.routes.api.settings_api`       | `/api/settings`   | 설정 조회/변경                        |
| `app.core.routes.api.database_api`       | `/api/database`   | DB 진단·쿼리 도구                     |
| `app.core.routes.api.analytics`          | `/api/analytics`  | 분석 데이터                           |
| `app.core.routes.api.ip_management_helpers` | `/api/ip`       | IP 정규화·검증 헬퍼                   |
| `app.core.routes.api.migration`          | `/api/migration`  | 스키마/데이터 마이그레이션             |
| `app.core.routes.api.error_metrics_api`  | `/api/error_metrics` | 에러율 카운터                      |
| `app.core.routes.api.monitoring.metrics` | `/api/metrics`    | 카운터/히스토그램 노출                 |

### 실시간 채널

| 채널                 | 모듈                                  | 용도                              |
| -------------------- | ------------------------------------- | --------------------------------- |
| WebSocket            | `app/core/routes/websocket_routes.py` | 라이브 로그·카운터 푸시           |
| SSE/JSON 폴링        | `api/collection/status.py`, `system_api.py` | 단방향 업데이트            |

### 운영 진입점 (Entrypoints)

- 컨테이너 진입: `app/entrypoint.sh`
- 앱 런처: `app/run_app.py`
- 배포 검증: `app/deployment_validation.py`

---

## Quickstart

### 사전 요구사항 / Prerequisites

- Docker Engine + Docker Compose v2
- 권장: Python 3.11 (개발 시)
- (선택) Node.js 20+ (프런트엔드 변경 시)

### 1) 저장소 클론

```bash
git clone <repository-url> blacklist-service
cd blacklist-service
```

### 2) 환경 변수 작성

`deploy/.env.example`을 참고하여 `deploy/.env`를 만듭니다. 최소 항목은 다음과 같습니다.

```bash
# deploy/.env (예시 / example)
PORT=2542
FLASK_ENV=development
JWT_SECRET=***REDACTED***
DATABASE_URL=postgresql://user:***REDACTED***@db-host:5432/blacklist
FORTINET_API_BASE=https://your-fortinet-host/api/v2
FORTINET_TOKEN=***REDACTED***
```

> 실제 호스트 주소는 자신의 환경에 맞춰 사용하세요. 예시는 보안용 더미 값입니다.

### 3) 개발 모드(Hot Reload) 실행

```bash
make dev
```

정상 기동 후 다음 주소에서 동작을 확인합니다.

- 앱 UI: `http://<host>:2542/`
- 헬스: `http://<host>:2542/api/system` → 상태 코드 200 확인
- 메트릭: `http://<host>:2542/api/metrics`

이미지를 그대로 사용(빠른 기동)하려면 다음을 사용합니다.

```bash
make dev-no-build
```

### 4) 프로덕션 모드(빌드 후 기동)

```bash
make prod
```

### 5) 기본 동작 확인

```bash
# 로그인 후 토큰 받기 (예시 페이로드)
curl -i -X POST http://<host>:2542/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"<password>"}'

# 컬렉션 소스 목록 (Bearer 토큰 필요)
curl http://<host>:2542/api/collection/sources \
  -H "Authorization: Bearer <JWT>"

# Fortinet에 등록
curl -X POST http://<host>:2542/api/fortinet/register \
  -H "Authorization: Bearer <JWT>" \
  -H 'Content-Type: application/json' \
  -d '{"address_group":"blocklist","entries":["198.51.100.10"]}'
```

> 위 IP/주소는 RFC 문서용 더미 값입니다. 실제로는 자체 차단 정책에 따라 입력하세요.

---

## Commands Reference

Makefile의 타깃을 그대로 사용합니다. (`make help`로 전체 목록 출력)

| 명령 / Command        | 설명                                  |
| --------------------- | ------------------------------------- |
| `make setup-hooks`    | pre-commit·husky·commitlint 훅 설치   |
| `make dev`            | 개발 환경 기동 (볼륨 마운트 + 리로드) |
| `make dev-no-build`   | 캐시된 이미지로 빠르게 기동           |
| `make dev-prod`       | 핫리로드 없는 프로덕션 유사 환경      |
| `make build`          | 이미지 빌드                           |
| `make up` / `make down` | 컨테이너 기동 / 중지                |
| `make logs`           | 로그 스트림                           |
| `make test`           | pytest 실행 (`tests/`)                |
| `make verify`         | `verify-lint verify-types verify-secrets verify-pre-commit` 일괄 실행 |
| `make verify-lint`    | Ruff                                  |
| `make verify-types`   | mypy                                  |
| `make verify-secrets` | 비밀값 패턴 검사                      |
| `make verify-pre-commit` | pre-commit 훅 전체 실행           |
| `make verify-quick`   | 빠른 검증 세트                        |
| `make verify-all`     | 모든 검증 일괄                        |
| `make release`        | 릴리스 태그 생성 (drafter 호환)        |
| `make release-dry`    | 릴리스 드래프트 미리보기              |
| `make health`         | 헬스 체크                             |
| `make restart`        | 서비스 재시작                         |
| `make clean`          | 컨테이너·볼륨 정리                   |

---

## Configuration

설정은 코드와 환경 변수 양쪽에서 들어옵니다. 우선순위는 **환경 변수 > 코드 기본값** 입니다.

### 환경 변수 / Environment Variables

| 변수 / Variable           | 용도 / Purpose                                 | 기본값 / Default |
| ------------------------- | ---------------------------------------------- | ---------------- |
| `PORT`                    | 웹 리스닝 포트                                 | `2542`           |
| `FLASK_ENV`               | `development` / `production`                   | `development`    |
| `JWT_SECRET`              | JWT 서명 키                                    | (없음, 필수)     |
| `JWT_TTL`                 | 토큰 유효 시간(초)                             | 코드 기본값      |
| `DATABASE_URL`            | DB 연결 문자열                                 | 코드 기본값      |
| `FORTINET_API_BASE`       | Fortinet API 엔드포인트                        | 비어 있음        |
| `FORTINET_TOKEN`          | Fortinet 인증 토큰                             | 비어 있음        |
| `LOG_LEVEL`               | 로깅 레벨 (DEBUG/INFO/WARNING/ERROR)           | `INFO`           |
| `LOG_DIR`                 | 로테이션 로그 디렉터리                          | 앱 내부          |
| `CORS_ORIGINS`            | 허용 Origin 목록 (콤마 구분)                   | `*`              |

### 코드 설정 / Code-side Config

`app/core/config.py`가 환경 변수를 읽어 설정 객체로 만듭니다. 새 옵션을 추가할 때 여기부터 수정하면 됩니다.

### 로그 / Logging

`app/utils/structured_logging.py`가 JSON 라인 구조화 로그를 만들고, `log_rotation_manager.py`가 일별/크기 기반 회전을 담당합니다. 운영 환경에서는 `LOG_DIR`을 마운트하여 보존 기간을 관리하세요.

---

## Architecture

### 책임 분리

| 레이어 / Layer        | 모듈                                                                  | 역할                                  |
| --------------------- | --------------------------------------------------------------------- | ------------------------------------- |
| 런처                  | `app/run_app.py`, `app/entrypoint.sh`                                  | 부팅·시그널 처리                      |
| 앱 팩토리             | `app/core/app.py`                                                     | Flask 인스턴스, 블루프린트 등록       |
| 설정                  | `app/core/config.py`                                                  | 환경 변수 → 설정 객체                 |
| 인증                  | `app/core/auth/*`                                                     | JWT 발급·검증·데코레이터·미들웨어     |
| 라우팅(웹)            | `app/core/routes/web_routes.py`                                       | 페이지 렌더링                         |
| 라우팅(API)           | `app/core/routes/api_routes.py`                                       | 도메인 API 디스패치                   |
| 도메인 API            | `app/core/routes/api/{collection,blacklist,fortinet,...}/*`           | 비즈니스 로직                         |
| 모니터링              | `app/core/monitoring/{metrics,cache_metrics,error_metrics}.py`        | 카운터·히스토그램 캐시·에러 추적      |
| 템플릿                | `app/templates/*.html`                                                | Jinja2 UI                             |
| 유틸                  | `app/utils/*`                                                         | 로깅·로테이션                         |

### 요청 흐름 (일반 API)

1. 클라이언트 요청 도착 → `web_routes` / `api_routes` 디스패치.
2. `auth/middleware`가 JWT 파싱, 만료/시그니처 검증.
3. 인증 실패 시 데코레이터가 401 응답, 성공 시 핸들러 진입.
4. 도메인 라우트(`collection/*`, `blacklist/*`, `fortinet/*`)가 비즈니스 로직 수행.
5. 외부 I/O 발생 시 `utils/structured_logging`이 컨텍스트와 함께 기록.
6. 모니터링 모듈이 카운터·히스토그램 갱신.
7. 응답 직렬화 후 반환, 변경 이벤트는 `websocket_routes`로 동시 전파.

### 요청 흐름 (Fortinet 푸시)

1. 운영자가 정책 변경 또는 수동 트리거 실행.
2. `blacklist/management`가 정책 정규화 → `ip_management_helpers`로 IP 검증.
3. `fortinet/core`가 `FORTINET_API_BASE` + `FORTINET_TOKEN`으로 REST 호출.
4. 결과(성공/실패/부분 성공)는 `fortinet_register` 라우트로 JSON 응답 + WebSocket 이벤트.
5. 실패는 `monitoring/error_metrics`에 카운팅.

---

## Local Development

### 컨테이너 기반 개발

- `make dev`는 `deploy/docker-compose.yml`을 빌드 후 띄우며 `app/`을 볼륨 마운트하여 코드 변경이 자동 반영됩니다.
- `make logs`로 컨테이너 로그를 실시간 확인합니다.
- 단일 서비스만 재시작: `make dev-app` (Makefile 상에서 정의된 부분 타깃).

### 호스트에서 직접 실행(컨테이너 외부)

`pyproject.toml`이 `pythonpath = ["app"]`을 지정하므로 `app/`을 모듈 경로로 인식합니다.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r app/requirements.txt
export PYTHONPATH="$(pwd)/app"
python app/run_app.py
```

### 코드 스타일

- Python 3.11, Ruff (`line-length = 120`)
- mypy (strict 영역은 `mypy.ini` 참조)
- 커밋 메시지는 `commitlint.config.js`의 conventional commits 규칙

### 사전 커밋 훅

```bash
make setup-hooks
```

---

## Testing

테스트는 `tests/` 디렉터리에서 발견 규칙에 따라 실행됩니다 (`test_*.py`, `Test*`, `test_*`).

```bash
# 전체
make test

# 마커로 부분 실행
pytest -m unit
pytest -m integration
pytest -m security
pytest -m db
pytest -m api
```

`pyproject.toml`에 등록된 마커:

| 마커 / Marker    | 의미                                            |
| ---------------- | ----------------------------------------------- |
| `unit`           | 외부 의존성 없는 단위 테스트                    |
| `integration`    | 외부 서비스(DB, Fortinet 등) 필요 테스트        |
| `security`       | 인증·인가·권한 관련                             |
| `db`             | DB 연동 테스트                                  |
| `api`            | API 엔드포인트 테스트                           |

추가 옵션: `addopts = "-v --tb=short"` (pytest 기본 옵션).

---

## Contribution Guide

- 이 저장소는 `CONTRIBUTING.md`의 절차와 커밋 컨벤션을 따릅니다.
- 한 PR은 가능한 한 작은 단위로 유지하고, 변경 파일 외 영역에 영향을 주지 않도록 합니다.
- 변경 전 `make verify` 통과를 권장합니다.
- 새 의존성을 추가할 경우 `app/requirements.txt`에 명시하고 영향 범위를 PR 설명에 적어 주세요.
- 시크릿, 인증 토큰, 사내 호스트/도메인을 커밋에 포함하지 마세요.

---

## Maintainers

운영 책임과 권한은 `OWNERS` 파일을 진실 공급원(SSoT)으로 사용합니다. 주요 영역:

| 영역 / Area           | 책임 / Responsibility                              |
| --------------------- | -------------------------------------------------- |
| 백엔드 코어           | `app/core/**`                                      |
| 인증·인가             | `app/core/auth/**`                                 |
| 모니터링·관측         | `app/core/monitoring/**`, `utils/structured_logging.py` |
| 컬렉션·Fortinet 통합  | `app/core/routes/api/collection/**`, `fortinet/**` |
| UI 템플릿             | `app/templates/**`                                 |
| 인프라·배포           | `Makefile`, `deploy/**`, `app/Dockerfile`          |
| 테스트                | `tests/**`, `pyproject.toml`의 pytest 설정         |
| 릴리스                | `Makefile`의 `release*` 타깃, `CHANGELOG.md`       |

자세한 담당자 표기는 `OWNERS`를 참조하세요.

---

## Further Documentation

| 문서 / Document             | 위치 / Location                | 용도                                  |
| --------------------------- | ------------------------------ | ------------------------------------- |
| 프로젝트 지식 베이스       | `AGENTS.md`                    | AI/자동화 에이전트를 위한 운영 메모    |
| 변경 로그                  | `CHANGELOG.md`                 | 버전별 변경 이력                       |
| 기여 가이드                | `CONTRIBUTING.md`              | PR·이슈 절차                          |
| 권한·책임                  | `OWNERS`                       | 영역별 담당자                          |
| 라이선스                   | `LICENSE`                      | 이용 약관                              |
| 현재 버전                  | `VERSION`                      | 빌드 식별자                            |

---

© Contributors. 자세한 권리 표기는 `LICENSE`를 참조하세요.
For rights, licenses, and attributions see `LICENSE`.