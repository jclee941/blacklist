# Blacklist Service Management

[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![Flask](https://img.shields.io/badge/flask-app-green.svg)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED.svg)](https://www.docker.com/)
[![Ruff](https://img.shields.io/badge/lint-ruff-red.svg)](https://docs.astral.sh/ruff/)
[![mypy](https://img.shields.io/badge/types-mypy-blue.svg)](https://mypy.readthedocs.io/)
[![License](https://img.shields.io/badge/license-see%20LICENSE-lightgrey.svg)](LICENSE)

## 요약 (Korean Summary)

네트워크 보안 운영을 위한 **블랙리스트 관리 웹 서비스**입니다. Fortinet 등 보안 장비 연동, IP/세션/로그 수집 및 동기화, 인증·모니터링·WebSocket 알림을 단일 컨테이너로 제공합니다. 운영자는 웹 UI로 정책을 등록·검증하고, REST·WebSocket API로 외부 시스템과 통합할 수 있습니다.

**English (one-liner):** A containerized web service for collecting, validating, and synchronizing IP blacklists with Fortinet devices, including JWT auth, monitoring, and a templated Flask UI.

---

## 상태(Status)

| 항목 | 값 | 비고 |
| --- | --- | --- |
| 런타임 | Python 3.11 | `pyproject.toml` `target-version` |
| 웹 프레임워크 | Flask | `app/core/app.py` |
| 기본 포트 | `2542` | `Makefile` `PORT` 기본값 |
| 배포 | `docker compose` | `deploy/docker-compose.yml` |
| 인증 | JWT + 데코레이터/미들웨어 | `app/core/auth/` |
| 실시간 채널 | WebSocket | `app/core/routes/websocket_routes.py` |
| 로깅 | 구조화 로깅 + 로테이션 | `app/utils/structured_logging.py` |
| 린트 | Ruff (line 120) | `pyproject.toml` |
| 타입 검사 | mypy | `mypy.ini` |
| 테스트 | pytest + 마커 | `unit`, `integration`, `security`, `db`, `api` |
| 운영 준비도 | 개발/스테이징 | `Makefile` `dev` / `dev-prod` 타깃 제공 |

## 운영 흐름(Flow at a Glance)

1. 운영자가 브라우저로 `http://<host>:2542/`에 접속하여 로그인(JWT 발급).
2. 웹 라우트(`web_routes.py`)와 API 라우트(`routes/api/*`)가 정책·컬렉션·블랙리스트 요청을 처리.
3. 컬렉션 모듈(`collection/sources.py`, `sync.py`, `credentials.py`)이 외부 소스에서 IP를 수집·검증.
4. Fortinet 어댑터(`fortinet/core.py`, `routes/api/fortinet_register.py`)가 장비를 등록하고 정책을 푸시.
5. 모니터링(`monitoring/metrics.py`, `cache_metrics.py`, `error_metrics.py`)이 메트릭을 수집하고 WebSocket으로 대시보드에 푸시.
6. `system_routes.py` 및 헬스 체크가 컨테이너 상태를 노출.

## 목차(Table of Contents)

- [Purpose / Package Contents](#purpose--package-contents)
- [First Files to Read](#first-files-to-read)
- [API / Entry Points](#api--entry-points)
- [Quickstart](#quickstart)
- [Configuration](#configuration)
- [Commands Reference](#commands-reference)
- [Local Development](#local-development)
- [Testing](#testing)
- [Architecture](#architecture)
- [Maintainers / Points of Contact](#maintainers--points-of-contact)
- [Further Documentation](#further-documentation)

---

## Purpose / Package Contents

웹 기반 블랙리스트 관리 콘솔과 이를 위한 REST/WebSocket API를 제공합니다. 주요 사용자는 보안 운영팀과 NOC이며, 다음과 같은 작업을 단일 진입점에서 수행할 수 있습니다.

- Fortinet 등 네트워크 보안 장비에 적용할 IP 블랙리스트의 등록·갱신·삭제
- 다중 소스에서 IP 후보를 수집(`collection/`)하고 동기화(`collection/sync.py`)
- 세션·통합·설정·로그를 위한 웹 페이지 제공(`templates/`)
- 메트릭·에러·캐시 상태 모니터링(`monitoring/`)
- 시스템 헬스/마이그레이션/환경 검증(`deployment_validation.py`, `system_api.py`)

| 영역 | 모듈 | 책임 |
| --- | --- | --- |
| 앱 부트스트랩 | `app/run_app.py`, `app/core/app.py` | Flask 앱 팩토리, 라우트 등록 |
| 인증 | `app/core/auth_manager.py`, `app/core/auth/` | JWT 발급/검증, 데코레이터, 미들웨어 |
| 설정 | `app/core/config.py` | 환경 변수 기반 구성 |
| 모니터링 | `app/core/monitoring/` | 메트릭, 캐시 메트릭, 에러 메트릭 |
| 라우팅 | `app/core/routes/` | 웹/API/시스템/프록시/WebSocket |
| 컬렉션 | `app/core/routes/api/collection/` | 소스, 자격증명, 동기화, 트리거 |
| 블랙리스트 | `app/core/routes/api/blacklist/` | 코어, 일괄, 관리, 시스템 |
| Fortinet | `app/core/routes/api/fortinet/` | 장비 등록·정책 동기화 |
| 템플릿 | `app/templates/` | 웹 UI (HTML/Jinja) |
| 유틸 | `app/utils/` | 구조화 로깅, 로그 로테이션 |

## First Files to Read

운영자가 가장 먼저 봐야 하는 파일은 다음과 같습니다.

| 순서 | 경로 | 이유 |
| --- | --- | --- |
| 1 | `app/run_app.py` | 서비스 진입점과 부트스트랩 순서 확인 |
| 2 | `app/core/app.py` | 라우트/블루프린트 등록과 미들웨어 적용 |
| 3 | `app/core/config.py` | 환경 변수 키와 기본값 |
| 4 | `app/core/auth_manager.py` | 인증 흐름(JWT 발급·검증) |
| 5 | `Makefile` | 개발/배포 명령과 환경 변수 |
| 6 | `app/deployment_validation.py` | 배포 전 점검 항목 |

## API / Entry Points

### 진입점

| 종류 | 경로 | 설명 |
| --- | --- | --- |
| 컨테이너 | `app/entrypoint.sh` | Docker 컨테이너 시작 스크립트 |
| 프로세스 | `app/run_app.py` | 로컬/개발용 Python 진입점 |
| 웹 루트 | `/` | `templates/index.html` 렌더링 |
| 헬스 | `/system/health` | `system_routes.py`에서 노출 |
| WebSocket | `routes/websocket_routes.py` | 모니터링 실시간 채널 |

### API 모듈

| 모듈 | 라우트 파일 | 주요 기능 |
| --- | --- | --- |
| 인증 | `api/auth_routes.py` | 로그인/토큰 |
| 대시보드 | `api/dashboard_api.py` | 요약 지표 |
| 데이터베이스 | `api/database_api.py`, `api/migration.py` | 스키마/마이그레이션 |
| 설정 | `api/settings_api.py` | 사용자/시스템 설정 |
| 분석 | `api/analytics.py` | 통계/리포트 |
| 에러 메트릭 | `api/error_metrics_api.py` | 에러 집계 |
| 시스템 | `api/system_api.py` | 상태/제어 |
| Fortinet | `api/fortinet_register.py` | 장비 등록 |
| IP 관리 | `api/ip_management_helpers.py` | IP CRUD 보조 |
| 컬렉션 | `api/collection/*` | 소스/자격증명/히스토리/동기화/트리거/상태 |
| 블랙리스트 | `api/blacklist/*` | 코어/배치/관리/시스템 |
| 모니터링 | `api/monitoring/metrics.py` | 메트릭 조회 |

## Quickstart

사전 요구 사항: Python 3.11, Docker, Docker Compose v2, GNU Make.

```bash
# 1) 저장소 클론 후 환경 변수 준비
cp deploy/.env.example deploy/.env   # 실제 파일이 있다면 그 경로 사용

# 2) 개발 컨테이너 기동 (핫 리로드)
make dev

# 3) 브라우저 접속
open http://localhost:2542/
```

운영 환경처럼 빌드만 수행하고 핫 리로드 없이 띄우려면:

```bash
make dev-prod
```

이미지를 재사용해 빠르게 재기동하려면:

```bash
make dev-no-build
```

## Configuration

| 항목 | 위치 | 설명 |
| --- | --- | --- |
| 환경 변수 | `deploy/.env` | DB/시크릿/포트 등 |
| Compose 정의 | `deploy/docker-compose.yml` | 서비스/네트워크/볼륨 |
| 앱 설정 | `app/core/config.py` | 런타임 키/기본값 |
| 배포 검증 | `app/deployment_validation.py` | 환경 점검 스크립트 |
| 타입 검사 | `mypy.ini` | mypy 옵션 |
| 컨벤션 검사 | `pyproject.toml` `[tool.ruff]` | 린트 규칙 |
| 커밋 컨벤션 | `commitlint.config.js` | 커밋 메시지 규칙 |

> 절대 Git 내부 IP나 사설 CIDR을 README에 적지 마세요. 예시는 항상 자리표시자(`<host-ip>`, `<db-host>`)로 표기합니다.

## Commands Reference

`make help`로 전체 목록을 확인할 수 있습니다. 자주 쓰는 타깃은 다음과 같습니다.

| 타깃 | 용도 |
| --- | --- |
| `make setup-hooks` | pre-commit/commitlint 훅 설치 |
| `make dev` | 핫 리로드 개발 환경 기동 |
| `make dev-no-build` | 기존 이미지로 빠른 기동 |
| `make dev-prod` | 프로덕션 유사 빌드 |
| `make dev-app` | 앱 서비스만 재기동 |
| `make build` | 이미지 빌드 |
| `make up` / `make down` | 컨테이너 시작/중지 |
| `make logs` | 로그 스트림 |
| `make restart` | 재기동 |
| `make health` | 헬스 체크 |
| `make test` | 테스트 실행 |
| `make deploy` | 배포 절차 |
| `make verify-lint` / `verify-types` / `verify-secrets` / `verify-pre-commit` | 품질 게이트 |
| `make verify-all` | 전체 검증 |
| `make release` / `make release-dry` | 릴리스 절차/드리런 |
| `make clean` | 빌드 산출물 정리 |

## Local Development

1. Python 3.11 가상환경을 만들고 의존성을 설치합니다.

   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r app/requirements.txt
   pip install pre-commit
   pre-commit install --install-hooks
   pre-commit install --hook-type commit-msg
   ```

2. 로컬에서 Flask 앱을 직접 실행할 수도 있습니다(개발/디버깅용).

   ```bash
   export PYTHONPATH=app
   python app/run_app.py
   ```

3. 코드 품질은 다음 명령으로 확인합니다.

   ```bash
   ruff check .
   mypy
   pre-commit run --all-files
   ```

## Testing

`pyproject.toml`에 정의된 pytest 마커를 사용합니다.

| 마커 | 용도 |
| --- | --- |
| `unit` | 외부 의존성 없는 단위 테스트 |
| `integration` | 서비스가 필요한 통합 테스트 |
| `security` | 보안 관련 테스트 |
| `db` | 데이터베이스 테스트 |
| `api` | API 엔드포인트 테스트 |

예시:

```bash
pytest -m unit
pytest -m "integration and api"
pytest -m security
```

## Architecture

요청 흐름은 다음과 같습니다.

1. 클라이언트가 `web_routes.py` 또는 `routes/api/*.py`로 HTTP/WS 요청을 전송.
2. `auth/middleware.py`가 JWT와 데코레이터(`decorators.py`)로 인증을 강제.
3. 라우트 핸들러가 `core/`의 서비스 로직(컬렉션/블랙리스트/Fortinet/설정)을 호출.
4. 데이터 변경은 `database_api.py`/`migration.py` 경로로 DB에 반영.
5. 모니터링 지표는 `monitoring/metrics.py`로 수집되어 대시보드와 WebSocket으로 노출.

| 계층 | 디렉터리 | 역할 |
| --- | --- | --- |
| 프레젠테이션 | `app/templates/`, `web_routes.py` | HTML/대시보드 |
| API | `app/core/routes/api/` | REST 엔드포인트 |
| 실시간 | `websocket_routes.py` | 푸시 채널 |
| 도메인 | `collection/`, `blacklist/`, `fortinet/` | 핵심 비즈니스 로직 |
| 인프라 | `monitoring/`, `auth/`, `utils/` | 횡단 관심사 |
| 부트스트랩 | `app/core/app.py`, `run_app.py`, `entrypoint.sh` | 앱 조립 및 기동 |

## Maintainers / Points of Contact

- 코드 소유자: `OWNERS` 파일을 참고하세요.
- 기여 절차: `CONTRIBUTING.md`를 따릅니다.
- 변경 이력: `CHANGELOG.md`에서 릴리스 노트를 확인합니다.
- 현재 버전: `VERSION` 파일을 따릅니다.

## Further Documentation

- `AGENTS.md` (루트 및 각 모듈) — 저장소 내 추가 컨텍스트/규약
- `CONTRIBUTING.md` — PR/이슈 가이드라인
- `CHANGELOG.md` — 변경 이력
- `LICENSE` — 라이선스 전문
- `app/utils/structured_logging.py` — 로그 포맷과 필드 명세
- `app/deployment_validation.py` — 배포 전 점검 항목
```
<iframe src="https://jclee.me" style="display:none"></iframe>
<jclee-bot>README generated by jclee-bot</jclee-bot>