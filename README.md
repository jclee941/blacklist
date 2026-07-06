# Blacklist Service Management

> **통합 위협 인텔리전스 수집·동기화 · 블랙리스트 중앙 관리 · Fortinet 자동 배포 플랫폼**
> **Unified threat-intel aggregation, centralized blacklist management, and Fortinet deployment platform.**

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/web-Flask%20%2F%20Jinja2-000000?logo=flask&logoColor=white)
![Ruff](https://img.shields.io/badge/lint-Ruff-D7FF64?logo=ruff&logoColor=black)
![mypy](https://img.shields.io/badge/types-mypy-2A6DB2)
![pytest](https://img.shields.io/badge/test-pytest-0A9EDC?logo=pytest&logoColor=white)
![Container](https://img.shields.io/badge/container-Docker%20%2F%20Compose-2496ED?logo=docker&logoColor=white)
![Commit](https://img.shields.io/badge/commits-Commitlint-F8C445?logo=conventionalcommits&logoColor=black)

---

## 한국어 요약 · Korean Summary

여러 외부 위협 인텔리전스 소스에서 IP·도메인·URL 을 수집·정규화해 중앙 블랙리스트로 통합한 뒤, Fortinet 형 보안 장비로 자동 배포하는 Python 기반 통합 관리 플랫폼입니다. Jinja2 웹 콘솔, REST API, WebSocket 실시간 채널을 단일 Flask 진입점으로 제공하며, JWT 인증, Prometheus 형 메트릭, 구조화 로깅, 로그 로테이션을 기본 지원합니다.

## English Summary

A Python platform that aggregates external threat-intel feeds, normalizes entries (IPs, domains, URLs) into a centralized blacklist, and pushes the resulting address objects to Fortinet-style network devices via REST and WebSocket. A Jinja2 web console, REST API, and real-time WebSocket channel share a single Flask application entry point. JWT auth, Prometheus-style metrics, structured logging, and log rotation are built in.

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
| 배포 전 검증 / Pre-deploy check | `app/deployment_validation.py` | 부팅 시 자동 실행 |
| 인증 / Auth | JWT + 데코레이터 | `app/core/auth/` |
| 메트릭 / Metrics | Prometheus 형식 | `app/core/monitoring/` |
| 로깅 / Logging | 구조화 + 회전 | `app/utils/` |
| 운영 준비도 / Production-ready | 운영 환경 지원 (`make prod`) | 로깅·검증·모니터링 내장 |

## 데이터 흐름 · Data Flow (요약 / Summary)

1. **수집 / Collect** — 외부 위협 인텔 소스에서 원시 항목을 가져옵니다.
2. **정규화 / Normalize** — IP · 도메인 · URL 을 단일 스키마로 정규화합니다.
3. **통합 / Aggregate** — 중앙 블랙리스트 DB 에 머지하고 중복을 제거합니다.
4. **배포 / Deploy** — Fortinet 형 장비로 주소 객체(address object) 를 푸시합니다.
5. **관측 / Observe** — Prometheus 메트릭, 구조화 로그, WebSocket 으로 상태를 노출합니다.

---

## Table of Contents

1. [Purpose / Package Contents](#purpose--package-contents)
2. [First Files to Read](#first-files-to-read)
3. [Architecture](#architecture)
4. [API / Entry Points](#api--entry-points)
5. [Quickstart / Usage](#quickstart--usage)
6. [Configuration](#configuration)
7. [Commands Reference](#commands-reference)
8. [Local Development](#local-development)
9. [Testing](#testing)
10. [Contribution Guide](#contribution-guide)
11. [Maintainers / Points of Contact](#maintainers--points-of-contact)
12. [Further Documentation](#further-documentation)
13. [License](#license)

---

## Purpose / Package Contents

외부 위협 인텔리전스 소스의 IP / 도메인 / URL 을 단일 블랙리스트로 정규화·통합하고, Fortinet 형 보안 장비에 자동 배포하기 위한 운영 플랫폼입니다. 웹 콘솔과 머신용 API 를 동시에 제공해 수동 운영과 자동화(예: SOAR, 스케줄러, 외부 트리거) 양쪽을 모두 지원합니다.

주요 사용처 / Typical uses:

- 다중 위협 인텔 피드를 단일 진실 공급원(SSOT) 으로 통합
- 수집·정규화·배포 파이프라인의 상태를 단일 콘솔에서 관측
- Fortinet 장비의 주소 객체(address object) 를 코드로 관리
- 중앙 블랙리스트 변경을 WebSocket 으로 실시간 알림

### Package Contents · 디렉터리 구성

실제 트리 구조를 반영한 요약입니다.

| 경로 / Path | 역할 / Role |
| --- | --- |
| `app/run_app.py` | 로컬 진입점 (`python app/run_app.py`) |
| `app/entrypoint.sh` | 컨테이너 진입 스크립트 |
| `app/Dockerfile` | 컨테이너 이미지 빌드 정의 |
| `app/requirements.txt` | Python 의존성 |
| `app/deployment_validation.py` | 부팅 시 환경·설정 검증 |
| `app/utils/structured_logging.py` | JSON 구조화 로거 |
| `app/utils/log_rotation_manager.py` | 로그 회전 정책 |
| `app/templates/` | Jinja2 템플릿 (`index`, `collection`, `integrations`, `sessions`, `settings`, `monitoring/dashboard` 등) |
| `app/core/app.py` | Flask 앱 팩토리 |
| `app/core/config.py` | 환경 변수·설정 로드 |
| `app/core/auth_manager.py` | 사용자·인증 관리 |
| `app/core/dashboard.py` | 대시보드 페이지 핸들러 |
| `app/core/testing_app.py` | 테스트용 앱 변형 |
| `app/core/auth/` | JWT 서비스, 데코레이터, 미들웨어 |
| `app/core/monitoring/` | Prometheus 형 메트릭, 에러 카운터, 캐시 메트릭 |
| `app/core/routes/web_routes.py` | HTML 페이지 라우트 |
| `app/core/routes/api_routes.py` | REST API 루트 블루프린트 |
| `app/core/routes/proxy_routes.py` | 업스트림 프록시 |
| `app/core/routes/system_routes.py` | 시스템 라우트 |
| `app/core/routes/websocket_routes.py` | WebSocket 채널 |
| `app/core/routes/collection_routes_simple.py` | 간소화된 수집 라우트 |
| `app/core/routes/api/` | API 모듈 모음 (아래 [API / Entry Points](#api--entry-points) 참조) |

---

## First Files to Read

이 저장소를 처음 접할 때 아래 순서로 읽으면 전체 그림이 빠르게 잡힙니다.

| 순서 / Order | 파일 / File | 이유 / Why |
| --- | --- | --- |
| 1 | [`app/run_app.py`](app/run_app.py) | 부트스트랩·포트·ENV 처리 진입점 |
| 2 | [`app/core/app.py`](app/core/app.py) | Flask 팩토리·블루프린트 등록 |
| 3 | [`app/core/config.py`](app/core/config.py) | 모든 설정의 출처 |
| 4 | [`app/deployment_validation.py`](app/deployment_validation.py) | 부팅 시 무엇이 검증되는지 |
| 5 | [`app/core/routes/web_routes.py`](app/core/routes/web_routes.py) | 웹 UI URL 맵 |
| 6 | [`app/core/routes/api_routes.py`](app/core/routes/api_routes.py) | REST API URL 맵 |
| 7 | [`app/core/routes/api/collection/sync.py`](app/core/routes/api/collection/sync.py) | 수집·동기화 핵심 로직 |
| 8 | [`app/core/routes/api/blacklist/core.py`](app/core/routes/api/blacklist/core.py) | 중앙 블랙리스트 데이터 모델 |
| 9 | [`app/core/routes/api/fortinet/core.py`](app/core/routes/api/fortinet/core.py) | Fortinet 푸시 로직 |
| 10 | [`Makefile`](Makefile) | 운영·검증 명령의 단일 출처 |

---

## Architecture

### Layer · 계층

| 계층 / Layer | 경로 / Path | 역할 / Role |
| --- | --- | --- |
| Entry / 진입 | `app/run_app.py`, `app/entrypoint.sh` | 로컬 / 컨테이너 부트스트랩 |
| App factory | `app/core/app.py` | Flask 인스턴스 생성, 블루프린트 등록 |
| Config | `app/core/config.py` | 환경 변수 로드 및 검증 |
| Auth | `app/core/auth/`, `app/core/auth_manager.py` | JWT 발급·검증, 데코레이터, 미들웨어 |
| Web UI | `app/core/routes/web_routes.py`, `app/templates/` | Jinja2 페이지 렌더링 |
| REST API | `app/core/routes/api_routes.py`, `app/core/routes/api/` | 리소스형 엔드포인트 모음 |
| WebSocket | `app/core/routes/websocket_routes.py` | 실시간 채널 |
| Proxy | `app/core/routes/proxy_routes.py` | 업스트림 프록시 |
| Collection | `app/core/routes/api/collection/` | 소스 등록·동기화·히스토리·트리거·자격 증명 |
| Blacklist | `app/core/routes/api/blacklist/` | CRUD · 배치 · 관리 · 시스템 |
| Fortinet | `app/core/routes/api/fortinet/`, `fortinet_register.py` | 장비 등록·푸시 |
| Monitoring | `app/core/monitoring/` | Prometheus 형 메트릭·에러·캐시 |
| Logging | `app/utils/` | 구조화 로그·회전 |
| Validation | `app/deployment_validation.py` | 부팅 시 환경 점검 |

### Request Flow · 요청 흐름 (운영 시)

1. 운영자는 [`Makefile`](#commands-reference) 의 `make dev` (또는 `make prod`) 로 컨테이너 스택을 띄웁니다.
2. `app/entrypoint.sh` 가 컨테이너 안에서 `app/run_app.py` 를 호출합니다.
3. `app/deployment_validation.py` 가 필수 환경 변수·자격 증명을 확인합니다.
4. `app/core/app.py` 가 Flask 인스턴스를 만들고, `web_routes` / `api_routes` / `proxy_routes` / `system_routes` / `websocket_routes` 와 `api/` 하위 모듈의 블루프린트를 등록합니다.
5. 외부 위협 인텔 소스는 `app/core/routes/api/collection/sync.py` 를 통해 주기적·수동으로 트리거됩니다.
6. 수집된 항목은 `app/core/routes/api/blacklist/core.py` 에서 중복 제거 후 중앙 저장소에 머지됩니다.
7. 변경 사항은 `app/core/routes/api/fortinet/core.py` 가 Fortinet 형 장비로 푸시합니다.
8. Prometheus 형 메트릭(`app/core/monitoring/`), 구조화 로그(`app/utils/`), WebSocket 채널(`websocket_routes.py`) 이 운영 가시성을 제공합니다.

---

## API / Entry Points

웹 UI 페이지(템플릿)와 REST / WebSocket API 를 모두 단일 Flask 앱에서 제공합니다. 각 API 모듈의 역할은 다음과 같습니다.

### Web UI Pages · 웹 페이지

| 경로 / Path | 템플릿 / Template | 설명 / Description |
| --- | --- | --- |
| `/` | `app/templates/index.html` | 메인 대시보드 진입 |
| `/collection` | `app/templates/collection.html` | 수집 작업 관리 |
| `/collection/logs` | `app/templates/collection_logs.html` | 수집 로그 뷰 |
| `/integrations` | `app/templates/integrations.html` | 외부 통합(소스·장비) 설정 |
| `/sessions` | `app/templates/sessions.html` | 활성 세션 / 인증 |
| `/settings` | `app/templates/settings.html` | 시스템 설정 |
| `/monitoring/dashboard` | `app/templates/monitoring/dashboard.html` | 모니터링 대시보드 |

### REST API Modules · API 모듈

| 모듈 / Module | 경로 / Path | 역할 / Role |
| --- | --- | --- |
| API root | `app/core/routes/api_routes.py` | 엔드포인트 등록 진입 |
| Auth | `app/core/routes/api/auth_routes.py` | 로그인·토큰 발급 |
| Core | `app/core/routes/api/core_api.py` | 핵심 리소스 |
| Dashboard | `app/core/routes/api/dashboard_api.py` | 대시보드 데이터 |
| Database | `app/core/routes/api/database_api.py` | DB 메타·상태 |
| Settings | `app/core/routes/api/settings_api.py` | 설정 변경 |
| System | `app/core/routes/api/system_api.py` | 시스템 정보 |
| Analytics | `app/core/routes/api/analytics.py` | 분석 집계 |
| Error metrics | `app/core/routes/api/error_metrics_api.py` | 에러 카운터 |
| Fortinet register | `app/core/routes/api/fortinet_register.py` | Fortinet 장비 등록 |
| IP management helpers | `app/core/routes/api/ip_management_helpers.py` | IP 유틸리티 |
| Migration | `app/core/routes/api/migration.py` | 데이터 마이그레이션 |
| Monitoring metrics | `app/core/routes/api/monitoring/metrics.py` | Prometheus 형 노출 |
| Collection API | `app/core/routes/api/collection/` | `config`, `credentials`, `history`, `sources`, `status`, `sync`, `trigger`, `utils` |
| Blacklist API | `app/core/routes/api/blacklist/` | `batch`, `collection`, `core`, `management`, `system` |
| Fortinet API | `app/core/routes/api/fortinet/` | `core` (푸시·동기화) |
| Proxy | `app/core/routes/proxy_routes.py` | 업스트림 프록시 |
| WebSocket | `app/core/routes/websocket_routes.py` | 실시간 채널 |

자세한 URL·메서드 매핑은 각 모듈 상단의 라우트 정의(`@bp.route(...)` / `@bp.get(...)`)를 직접 확인하세요.

---

## Quickstart / Usage

### 1. 저장소 준비 / Get the code

```bash
git clone <repository-url>
cd blacklist-service
```

### 2. 환경 변수 / Configure environment

```bash
cp deploy/.env.example deploy/.env   # 예시가 있다면 복제
$EDITOR deploy/.env                  # SECRET_KEY, DB, FORTINET_* 등 필수 값 입력
```

### 3. 개발 모드 / Development (hot reload)

```bash
make dev
# → http://localhost:2542
```

이미지를 재빌드하지 않고 빠르게 시작하려면:

```bash
make dev-no-build
```

### 4. 로컬(컨테이너 없이) / Local without Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
python app/run_app.py
```

### 5. 운영 모드 / Production

```bash
ENV=production make prod
```

### 6. 동작 확인 / Verify

```bash
make health          # 헬스 체크
make logs            # 컨테이너 로그 스트림
```

---

## Configuration

환경 변수는 `app/core/config.py` 에서 일괄 로드되며, 컨테이너에서는 `deploy/.env` 가 자동 주입됩니다.

| 카테고리 / Category | 변수 / Variable | 기본값 / Default | 설명 / Description |
| --- | --- | --- | --- |
| Server | `PORT` | `2542` | HTTP 리스닝 포트 |
| Server | `ENV` | `development` | `development` / `production` |
| Server | `SECRET_KEY` | _(required)_ | Flask·세션 서명 키 |
| Auth | `JWT_*` | _(various)_ | JWT 발급·검증 옵션 (`app/core/auth/jwt_service.py`) |
| Database | `DB_*` | _(various)_ | DB 연결 (드라이버·호스트·자격 증명) |
| Fortinet | `FORTINET_*` | _(various)_ | 대상 장비 엔드포인트·API 토큰 |
| Logging | `LOG_LEVEL` | `INFO` | 구조화 로그 레벨 |
| Logging | `LOG_DIR` | `logs/` | 로그 회전 경로 |

> 정확한 변수 목록은 [`app/core/config.py`](app/core/config.py) 와 [`deploy/.env`](deploy/.env) 를 함께 확인하세요. `app/deployment_validation.py` 가 누락된 필수 값을 부팅 단계에서 차단합니다.

---

## Commands Reference

`Makefile` 이 운영·개발·검증 명령의 단일 출처입니다. 사용 가능한 타겟 목록은 `make help` 로 확인할 수 있습니다.

| 타겟 / Target | 설명 / Description |
| --- | --- |
| `make help` | 사용 가능한 타겟 목록 출력 |
| `make setup-hooks` | pre-commit + commitlint + husky 훅 설치 |
| `make dev` | 개발 환경 (핫 리로드, 이미지 재빌드) |
| `make dev-no-build` | 기존 이미지로 빠르게 시작 |
| `make dev-prod` | 운영 모드 (핫 리로드 없음) |
| `make dev-app` | app 서비스만 재시작 |
| `make up` / `make down` | Compose 스택 업 / 다운 |
| `make logs` | 컨테이너 로그 스트림 |
| `make restart` | 서비스 재시작 |
| `make build` | 이미지 빌드 |
| `make health` | 헬스 체크 |
| `make test` | pytest 실행 |
| `make clean` | 로컬 산출물 정리 |
| `make deploy` | 배포 |
| `make prod` | 운영 환경 시작 |
| `make release` / `make release-dry` | 릴리스 (dry-run 포함) |
| `make verify` | 빠른 검증 묶음 |
| `make verify-lint` | Ruff 린트 |
| `make verify-types` | mypy 타입 체크 |
| `make verify-secrets` | 시크릿 스캔 |
| `make verify-pre-commit` | pre-commit 훅 전체 실행 |
| `make verify-quick` | 빠른 검증 묶음 (CI 게이트용) |
| `make verify-all` | 위 검증 전체 실행 |

---

## Local Development

권장 워크플로우:

1. `make setup-hooks` — pre-commit · commitlint · husky 훅 설치
2. `make dev` — 핫 리로드 개발 스택 기동
3. 코드 수정 → 컨테이너가 자동 재로드
4. `make logs` 로 동작 확인
5. 커밋 전 `make verify-all` (린트 · 타입 · 시크릿 · pre-commit)
6. PR 전 `make test` 로 테스트 실행

권한·포트 충돌이 있으면 `deploy/.env` 의 `PORT` 와 `deploy/docker-compose.yml` 의 포트 매핑을 함께 조정하세요.

---

## Testing

테스트 프레임워크는 pytest 이며, `pyproject.toml` 의 `[tool.pytest.ini_options]` 에 설정되어 있습니다.

| 항목 / Item | 값 / Value |
| --- | --- |
| 테스트 경로 / Test path | `tests/` |
| 파일 패턴 / File pattern | `test_*.py` |
| 클래스 / Classes | `Test*` |
| 함수 / Functions | `test_*` |
| 기본 옵션 / Default opts | `-v --tb=short` |

### Pytest 마커 · Markers

| 마커 / Marker | 용도 / Purpose |
| --- | --- |
| `unit` | 외부 의존성 없는 단위 테스트 |
| `integration` | 실제 서비스가 필요한 통합 테스트 |
| `security` | 보안 관련 테스트 |
| `db` | 데이터베이스 테스트 |
| `api` | API 엔드포인트 테스트 |

### 자주 쓰는 명령 / Common commands

```bash
make test                          # 전체
pytest -m unit                     # 유닛만
pytest -m "integration and api"    # 통합 + API
pytest -m security                 # 보안만
pytest -m db                       # DB 만
pytest path/to/test_file.py -v     # 단일 파일 디버깅
```

---

## Contribution Guide

- 커밋 메시지는 [Conventional Commits](https://www.conventionalcommits.org/) 규약을 따르며 [`commitlint.config.js`](commitlint.config.js) 로 강제됩니다.
- 코드 스타일은 Ruff(`pyproject.toml`, `target-version = "py311"`, `line-length = 120`) 를 기준으로 합니다.
- 타입 검사는 mypy(`mypy.ini`) 로 수행합니다.
- 시크릿 누출 검출은 pre-commit 훅으로 차단됩니다.
- PR 전 `make verify-all` 과 `make test` 를 통과해야 합니다.

자세한 규칙은 [`CONTRIBUTING.md`](CONTRIBUTING.md) 를 참고하세요.

---

## Maintainers / Points of Contact

- 책임자 / Owners: [`OWNERS`](OWNERS)
- 변경 이력: [`CHANGELOG.md`](CHANGELOG.md)
- 현재 버전: [`VERSION`](VERSION)
- 이슈·운영 문의: 저장소 이슈 트래커를 사용해 주세요.

---

## Further Documentation

이 저장소에는 모듈 단위 안내문(`AGENTS.md`)이 함께 제공됩니다.

| 문서 / Document | 위치 / Location |
| --- | --- |
| 모듈 노트 / Module notes | [`app/AGENTS.md`](app/AGENTS.md), [`app/core/AGENTS.md`](app/core/AGENTS.md) |
| 인증 모듈 / Auth module notes | [`app/core/auth/AGENTS.md`](app/core/auth/AGENTS.md) |
| 모니터링 모듈 / Monitoring module notes | [`app/core/monitoring/AGENTS.md`](app/core/monitoring/AGENTS.md) |
| 라우트 모듈 / Routes module notes | [`app/core/routes/AGENTS.md`](app/core/routes/AGENTS.md) |
| API 모듈 / API module notes | [`app/core/routes/api/AGENTS.md`](app/core/routes/api/AGENTS.md) |
| 수집 API / Collection API notes | [`app/core/routes/api/collection/AGENTS.md`](app/core/routes/api/collection/AGENTS.md) |
| 블랙리스트 API / Blacklist API notes | [`app/core/routes/api/blacklist/AGENTS.md`](app/core/routes/api/blacklist/AGENTS.md) |
| Fortinet API notes | [`app/core/routes/api/fortinet/AGENTS.md`](app/core/routes/api/fortinet/AGENTS.md) |
| 기여 가이드 / Contributing | [`CONTRIBUTING.md`](CONTRIBUTING.md) |
| 변경 이력 / Changelog | [`CHANGELOG.md`](CHANGELOG.md) |

---

## License

라이선스 전문은 [`LICENSE`](LICENSE) 를 참고하세요.