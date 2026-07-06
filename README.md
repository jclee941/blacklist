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

여러 외부 위협 인텔리전스 소스에서 IP·도메인·URL 을 수집·정규화해 중앙 블랙리스트로 통합한 뒤, Fortinet 같은 외부 보안 장비로 자동 배포하는 Python 기반 통합 관리 플랫폼입니다. Jinja2 웹 콘솔, REST API, WebSocket 실시간 채널을 단일 진입점으로 제공합니다.

A Python platform that aggregates external threat-intel feeds, normalizes entries into a centralized blacklist, and pushes the resulting address objects to Fortinet-style devices via REST API and WebSocket, exposed through a Jinja2 web console.

---

## Status · 운영 한눈표

| 항목 / Item | 값 / Value | 비고 / Notes |
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
| 운영 단계 / Production-ready? | 운영 검증 단계 | 사내 PoC → 단계적 확대 |

---

## Compact Flow · 운영 흐름

1. **수집 · Collect** — 외부 소스(`collection/sources`) 에서 IP·도메인·URL 항목을 주기·수동으로 가져옵니다. · External feeds are pulled on schedule or on demand.
2. **정규화 · Normalize** — `collection/` 모듈이 스키마 정합성·중복 제거 후 중앙 블랙리스트 저장소에 적재합니다. · `collection/` modules dedupe and persist entries.
3. **검토 · Review** — 운영자는 콘솔·WebSocket 으로 인증 후 큐를 검토하고 `blacklist/batch` 로 일괄 처리합니다. · Operators authenticate, review the queue, and apply batched actions.
4. **배포 · Deploy** — `fortinet/core` 어댑터가 변경분을 외부 장비의 주소 객체(`Address Object`) 로 동기화합니다. · The Fortinet adapter syncs diffs as address objects.
5. **관측 · Observe** — 캐시·에러·DB 메트릭과 회전 로그가 감사 추적과 운영 지표를 제공합니다. · Rotated JSON logs and metrics deliver the audit trail.

---

## 목차 · Contents

- [특징 · Features](#특징--features)
- [아키텍처 · Architecture](#아키텍처--architecture)
- [빠른 시작 · Quick Start](#빠른-시작--quick-start)
- [환경 설정 · Configuration](#환경-설정--configuration)
- [운영 명령 · Commands](#운영-명령--commands)
- [API & WebSocket](#api--websocket)
- [모니터링 · Monitoring](#모니터링--monitoring)
- [테스트 · Testing](#테스트--testing)
- [디렉터리 · Directory](#디렉터리--directory)
- [기여 · Contributing](#기여--contributing)
- [라이선스 · License](#라이선스--license)
- [OWNERS · 유지보수](#owners--유지보수)

---

## 특징 · Features

- 멀티 소스 위협 인텔리전스 수집과 동기화 트리거 — [`collection/`](app/core/routes/api/collection/)
- 중앙 블랙리스트 관리: 배치, 시스템 컬렉션, 일반 관리 — [`blacklist/`](app/core/routes/api/blacklist/)
- Fortinet 주소 객체 자동 등록 및 어댑터 — [`fortinet_register.py`](app/core/routes/api/fortinet_register.py), [`fortinet/core.py`](app/core/routes/api/fortinet/core.py)
- Jinja2 웹 콘솔: 인덱스, 세션, 설정, 통합, 로그, 모니터링 대시보드 — [`app/templates/`](app/templates/)
- JWT 인증과 데코레이터·미들웨어 — [`app/core/auth/`](app/core/auth/)
- WebSocket 실시간 채널 (수집 진행, 동기화 결과, 시스템 알림) — [`websocket_routes.py`](app/core/routes/websocket_routes.py)
- 캐시·에러·DB 메트릭 노출과 대시보드 — [`app/core/monitoring/`](app/core/monitoring/), [`app/core/dashboard.py`](app/core/dashboard.py)
- 구조화 JSON 로깅과 사이즈·시간 기반 회전 — [`app/utils/`](app/utils/)
- Docker Compose 개발·운영 분리, 배포 전 검증 스크립트 — [`Makefile`](Makefile), [`deployment_validation.py`](app/deployment_validation.py)
- Ruff + mypy + commitlint + pre-commit + husky 통합 게이트

## 아키텍처 · Architecture

| 영역 / Area | 모듈 / Module | 책임 / Responsibility |
| --- | --- | --- |
| Web Console | [`app/templates/`](app/templates/), [`web_routes.py`](app/core/routes/web_routes.py) | Jinja2 페이지 렌더링, 폼·세션 |
| REST API | [`api_routes.py`](app/core/routes/api_routes.py) + [`api/`](app/core/routes/api/) | 엔드포인트 라우팅 (`/api/...`) |
| WebSocket | [`websocket_routes.py`](app/core/routes/websocket_routes.py) | 실시간 푸시·구독 |
| Proxy | [`proxy_routes.py`](app/core/routes/proxy_routes.py) | 상류 보안 장비 프록시 |
| Auth | [`auth_manager.py`](app/core/auth_manager.py), [`app/core/auth/`](app/core/auth/) | JWT 발급·검증, 데코레이터·미들웨어 |
| Monitoring | [`dashboard.py`](app/core/dashboard.py), [`app/core/monitoring/`](app/core/monitoring/) | 메트릭 집계·대시보드 |
| Logging | [`structured_logging.py`](app/utils/structured_logging.py), [`log_rotation_manager.py`](app/utils/log_rotation_manager.py) | JSON 로그, 회전 정책 |
| Config | [`config.py`](app/core/config.py), [`testing_app.py`](app/core/testing_app.py) | ENV 기반 설정, 테스트 모드 진입 |

요청 흐름 (Read) · Read flow:

1. 클라이언트가 `/`, `/api/...`, `ws://...` 로 요청을 전송
2. `web_routes` / `api_routes` 가 호출되고 `auth/middleware` 가 JWT 검증
3. 도메인 핸들러(`collection/`, `blacklist/`, `fortinet/`, ...) 가 비즈니스 로직 수행
4. 결과를 JSON 또는 HTML 로 직렬화, 필요 시 WebSocket 으로 추가 브로드캐스트
5. `monitoring/*` 가 캐시·에러 카운터를 갱신, `structured_logging` 이 JSON 로그 출력

기동 흐름 · Boot flow: `entrypoint.sh` → `deployment_validation.py` (sanity check) → `run_app.py` (Flask-style 앱) → 모듈 임포트(`auth`, `routes`, `monitoring`) → 첫 요청 수신.

## 빠른 시작 · Quick Start

사전 요구 사항 / Prerequisites: Python 3.11+, Docker 24+, Make.

```bash
# 1) 환경 변수 템플릿 준비 (deploy/.env 가 없다면 신규 작성)
cp deploy/.env.example deploy/.env 2>/dev/null || true

# 2) 개발 모드 (핫 리로드, 변경 이미지 재빌드)
make dev

# 3) 브라우저에서 접속
open http://localhost:2542
```

Compose 없이 로컬 실행 / Run without Compose:

```bash
pip install -r app/requirements.txt
export PORT=2542 ENV=development
python app/run_app.py
```

운영 모드 전환 / Switch to production profile:

```bash
make prod     # deploy/docker-compose.yml 운영 프로파일 기동
make verify   # 배포 전 검증 (deployment_validation.py)
```

## 환경 설정 · Configuration

| 키 / Key | 용도 / Purpose | 예시 / Example |
| --- | --- | --- |
| `PORT` | HTTP 수신 포트 | `2542` |
| `ENV` | 실행 모드 (`development` / `production`) | `production` |
| `JWT_SECRET` | 토큰 서명 키 (32자 이상 권장) | _(env-only)_ |
| `JWT_EXPIRES` | 토큰 TTL | `1h` |
| `LOG_LEVEL` | 구조화 로그 레벨 | `INFO` |
| `LOG_DIR` | 회전 로그 디렉터리 | `/var/log/blacklist` |
| `FORTINET_BASE_URL` | Fortinet 장비 베이스 URL | `https://<fortinet-host>` |
| `FORTINET_TOKEN` | Fortinet API 토큰 | _(env-only)_ |

설정 모듈 / Config module: [`app/core/config.py`](app/core/config.py). 배포 환경에서는 `deploy/.env` 와 Compose 의 환경 변수 주입을 사용하세요.

## 운영 명령 · Commands

| 타깃 / Target | 설명 / Purpose |
| --- | --- |
| `make help` | 사용 가능한 타깃 나열 |
| `make setup-hooks` | pre-commit + commitlint + husky 설치 |
| `make dev` | 핫 리로드 개발 환경 기동 (이미지 재빌드) |
| `make dev-no-build` | 재빌드 없이 기동 |
| `make dev-prod` | 운영 모드에 가까운 개발 환경 |
| `make dev-app` | 앱 서비스만 빠른 재기동 |
| `make up` / `make down` | Compose 서비스 시작 / 중지 |
| `make logs` | 컨테이너 로그 tail |
| `make restart` | 서비스 재시작 |
| `make health` | 헬스 체크 |
| `make build` | 이미지 빌드 |
| `make test` | pytest 실행 (`tests/`) |
| `make deploy` | 배포 절차 |
| `make verify` | 배포 전 검증 (`deployment_validation.py`) |
| `make verify-lint` | Ruff 검사 |
| `make verify-types` | mypy 검사 |
| `make verify-secrets` | 시크릿 누출 검사 |
| `make verify-pre-commit` | pre-commit 훅 실행 |
| `make verify-quick` | 빠른 검증 스위트 |
| `make verify-all` | 전체 검증 |
| `make release` / `make release-dry` | 릴리스 / 드라이런 |
| `make clean` | 정리 |

## API & WebSocket

REST 엔드포인트는 `/api/` 하위 모듈과 1:1 대응됩니다.

| 경로 / Path | 모듈 / Module | 설명 / Purpose |
| --- | --- | --- |
| `/api/auth/...` | [`auth_routes.py`](app/core/routes/api/auth_routes.py) | 인증·토큰 발급 |
| `/api/dashboard/...` | [`dashboard_api.py`](app/core/routes/api/dashboard_api.py) | 대시보드 데이터 |
| `/api/database/...` | [`database_api.py`](app/core/routes/api/database_api.py) | DB 메타·쿼리 |
| `/api/settings/...` | [`settings_api.py`](app/core/routes/api/settings_api.py) | 설정 값 |
| `/api/system/...` | [`system_api.py`](app/core/routes/api/system_api.py) | 시스템 상태 |
| `/api/analytics/...` | [`analytics.py`](app/core/routes/api/analytics.py) | 분석 |
| `/api/error-metrics/...` | [`error_metrics_api.py`](app/core/routes/api/error_metrics_api.py) | 에러 카운터 |
| `/api/migration/...` | [`migration.py`](app/core/routes/api/migration.py) | 데이터 마이그레이션 |
| `/api/fortinet-register/...` | [`fortinet_register.py`](app/core/routes/api/fortinet_register.py) | Fortinet 직접 등록 |
| `/api/collection/...` | [`collection/`](app/core/routes/api/collection/) | 수집 트리거·이력·설정 |
| `/api/blacklist/...` | [`blacklist/`](app/core/routes/api/blacklist/) | 블랙리스트 관리·배치·시스템 |
| `/api/fortinet/...` | [`fortinet/core.py`](app/core/routes/api/fortinet/core.py) | Fortinet 어댑터 |
| `/api/monitoring/...` | [`monitoring/metrics.py`](app/core/routes/api/monitoring/metrics.py) | 메트릭 조회 |

WebSocket: [`websocket_routes.py`](app/core/routes/websocket_routes.py) — 수집 진행, 동기화 결과, 시스템 알림 푸시.

## 모니터링 · Monitoring

- 캐시 메트릭: [`cache_metrics.py`](app/core/monitoring/cache_metrics.py)
- 에러 메트릭: [`error_metrics.py`](app/core/monitoring/error_metrics.py)
- 일반 메트릭: [`metrics.py`](app/core/monitoring/metrics.py)
- 대시보드 페이지: [`dashboard.html`](app/templates/monitoring/dashboard.html), [`dashboard.py`](app/core/dashboard.py)

운영자는 대시보드에서 캐시 적중률, 에러 비율, 큐 깊이를 모니터링합니다. 구조화 로깅은 [`structured_logging.py`](app/utils/structured_logging.py), 로그 회전 정책은 [`log_rotation_manager.py`](app/utils/log_rotation_manager.py) 에서 관리합니다.

## 테스트 · Testing

테스트 디렉터리 / Test directory: `tests/`. 마커 / Markers (`pyproject.toml` 참조): `unit`, `integration`, `security`, `db`, `api`.

```bash
make test             # 전체 pytest
pytest -m unit        # 단위 테스트만
pytest -m integration # 통합 테스트 (서비스 필요)
pytest -m security    # 보안 테스트
```

CI 게이트 / CI gates: `make verify-lint verify-types verify-pre-commit verify-all` 을 PR 전 로컬에서 실행해 두면 원격 실패가 줄어듭니다.

## 디렉터리 · Directory

```text
.
├── app/
│   ├── core/
│   │   ├── app.py
│   │   ├── auth_manager.py
│   │   ├── config.py
│   │   ├── dashboard.py
│   │   ├── testing_app.py
│   │   ├── auth/             # jwt_service, decorators, middleware
│   │   ├── monitoring/       # cache_metrics, error_metrics, metrics
│   │   └── routes/
│   │       ├── api_routes.py
│   │       ├── collection_routes_simple.py
│   │       ├── proxy_routes.py
│   │       ├── system_routes.py
│   │       ├── web_routes.py
│   │       ├── websocket_routes.py
│   │       └── api/          # 도메인별 API 블루프린트
│   │           ├── analytics.py
│   │           ├── auth_routes.py
│   │           ├── core_api.py
│   │           ├── dashboard_api.py
│   │           ├── database_api.py
│   │           ├── error_metrics_api.py
│   │           ├── fortinet_register.py
│   │           ├── ip_management_helpers.py
│   │           ├── migration.py
│   │           ├── settings_api.py
│   │           ├── system_api.py
│   │           ├── blacklist/   # batch, collection, core, management, system
│   │           ├── collection/  # config, credentials, history, sources, status, sync, trigger, utils
│   │           ├── fortinet/    # core
│   │           └── monitoring/  # metrics
│   ├── templates/            # Jinja2: index, collection, sessions, settings, integrations, ...
│   │   └── monitoring/dashboard.html
│   ├── utils/                # structured_logging, log_rotation_manager
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── deployment_validation.py
│   ├── requirements.txt
│   └── run_app.py
├── deploy/                   # docker-compose, .env 템플릿 (Makefile 참조)
├── AGENTS.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── OWNERS
├── README.md
├── VERSION
├── commitlint.config.js
├── mypy.ini
└── pyproject.toml
```

## 기여 · Contributing

1. 피처 브랜치 생성 (예: `feat/collection-retry`)
2. Conventional Commits 형식으로 커밋 (`commitlint.config.js` 참조)
3. 사전 검증 통과: `make verify-lint verify-types verify-pre-commit`
4. PR 작성 후 [`OWNERS`](OWNERS) 의 리뷰 대기
5. 상세 가이드 / Detailed guide: [`CONTRIBUTING.md`](CONTRIBUTING.md)

행동 강령·보안 이슈 제보는 [`CONTRIBUTING.md`](CONTRIBUTING.md) 의 절차를 따르고, 민감 정보는 공개 이슈 대신 책임자에게 비공개로 전달하세요.

## 라이선스 · License

본 저장소는 [`LICENSE`](LICENSE) 파일의 조건에 따라 배포됩니다. 사내 정책 변경 또는 상업적 사용 전 반드시 검토하세요.

## OWNERS · 유지보수

운영 책임자 / Maintainers 목록은 [`OWNERS`](OWNERS) 파일을 참조하세요. 운영·보안 이슈 또는 배포 변경 요청 시 책임자에게 먼저 문의합니다.

추가 자료 / Further documentation: [`CONTRIBUTING.md`](CONTRIBUTING.md), [`CHANGELOG.md`](CHANGELOG.md), [`app/AGENTS.md`](app/AGENTS.md), [`app/core/AGENTS.md`](app/core/AGENTS.md), [`app/core/auth/AGENTS.md`](app/core/auth/AGENTS.md), [`app/core/monitoring/AGENTS.md`](app/core/monitoring/AGENTS.md), [`app/core/routes/AGENTS.md`](app/core/routes/AGENTS.md), [`app/core/routes/api/AGENTS.md`](app/core/routes/api/AGENTS.md), [`app/core/routes/api/blacklist/AGENTS.md`](app/core/routes/api/blacklist/AGENTS.md), [`app/core/routes/api/collection/AGENTS.md`](app/core/routes/api/collection/AGENTS.md), [`app/core/routes/api/fortinet/AGENTS.md`](app/core/routes/api/fortinet/AGENTS.md).