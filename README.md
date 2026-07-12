# Blacklist Management Service

## 개요 (Overview)

IP 블랙리스트 수집·동기화·관리와 Fortinet 방화벽 등록을 묶은 Python 웹 서비스입니다. 수집기 설정, 자격증명, 변경 이력, 동기화 트리거, 대량 작업, 시스템 운영 API를 한 프로세스에서 제공하며, 기본 포트 `2542`에서 동작합니다.

A Python web service that consolidates IP blacklist collection, synchronization, and registration to Fortinet firewalls. It bundles collector configuration, credentials, change history, sync triggers, batch operations, and operator-facing APIs in one process, default port `2542`.

## 한눈에 보기 / At a Glance

| 항목 / Item | 값 / Value |
| --- | --- |
| 제품 / Product | Blacklist Management Service |
| 런타임 / Runtime | Python 3.11 + Flask-style web app |
| 진입점 / Entry point | `app/run_app.py` (`make dev` / `make prod`) |
| 기본 포트 / Default port | `2542` |
| 인증 / Auth | JWT + 인증 데코레이터·미들웨어 (`app/core/auth`) |
| 데이터 수집 / Collection | 다중 소스 수집·자격증명·이력·동기화 (`app/core/routes/api/collection`) |
| 통합 / Integration | Fortinet 등록 API (`app/core/routes/api/fortinet`, `fortinet_register.py`) |
| 모니터링 / Monitoring | 캐시·에러·메트릭, 대시보드 템플릿 (`app/core/monitoring`, `templates/monitoring/dashboard.html`) |
| 전송 / Transport | REST + WebSocket (`websocket_routes.py`) |
| 로깅 / Logging | 구조화 로깅 + 로그 로테이션 (`utils/structured_logging.py`, `log_rotation_manager.py`) |
| 배포 / Deploy | Docker, `Makefile` (`make up` / `down` / `build` / `health`) |
| 소유 / Owner | `OWNERS` 참조 |
| 상태 / Status | 운영 가능 / Production-ready |
| 라이선스 / License | `LICENSE` |

## 핵심 흐름 / Operating Flow

1. 운영자는 `make dev`로 컨테이너를 띄우고 `http://localhost:2542`에 접속합니다.
2. 웹 UI(`templates/index.html`, `sessions.html`, `settings.html`)에서 수집·동기화 작업을 설정합니다.
3. REST API와 WebSocket이 인증 후 변경·트리거를 수신하고, 동기화 모듈(`collection/sync.py`, `trigger.py`)이 실행됩니다.
4. 결과는 이력(`collection/history.py`)과 상태(`collection/status.py`)에 기록되며, 모니터링 API(`monitoring/metrics.py`)와 대시보드에서 확인합니다.
5. Fortinet 등록 모듈이 IP를 방화벽으로 배포하고, 변경 사항은 블랙리스트 배치·시스템 모듈이 추적합니다.

## 목차 / Contents

- [패키지 구성 / Package Contents](#패키지-구성--package-contents)
- [상태 / Status](#상태--status)
- [먼저 읽을 파일 / First Files to Read](#먼저-읽을-파일--first-files-to-read)
- [API와 진입점 / API and Entry Points](#api와-진입점--api-and-entry-points)
- [빠른 시작 / Quickstart](#빠른-시작--quickstart)
- [설정 / Configuration](#설정--configuration)
- [명령어 참조 / Commands Reference](#명령어-참조--commands-reference)
- [로컬 개발 / Local Development](#로컬-개발--local-development)
- [테스트 / Testing](#테스트--testing)
- [기여 / Contributing](#기여--contributing)
- [운영자 / Maintainers](#운영자--maintainers)
- [추가 문서 / Further Documentation](#추가-문서--further-documentation)
- [라이선스 / License](#라이선스--license)

## 패키지 구성 / Package Contents

| 경로 / Path | 역할 / Role |
| --- | --- |
| `app/run_app.py` | 서비스 부트스트랩, Flask 앱 팩토리 |
| `app/entrypoint.sh` | 컨테이너 진입 스크립트 |
| `app/Dockerfile` | 서비스 이미지 빌드 정의 |
| `app/deployment_validation.py` | 배포 사전 검증 |
| `app/requirements.txt` | 런타임 의존성 |
| `app/utils/` | 구조화 로깅, 로그 로테이션 유틸 |
| `app/templates/` | HTML 템플릿 (index, sessions, settings, integrations, collection, monitoring) |
| `app/core/app.py` | 코어 앱 초기화 |
| `app/core/auth_manager.py` | 인증 관리자 |
| `app/core/config.py` | 환경설정 로더 |
| `app/core/dashboard.py` | 대시보드 로직 |
| `app/core/testing_app.py` | 테스트 모드 앱 |
| `app/core/auth/` | JWT, 데코레이터, 미들웨어 |
| `app/core/monitoring/` | 캐시·에러·메트릭 수집기 |
| `app/core/routes/` | 웹·API·WebSocket 라우트 |
| `app/core/routes/api/` | REST API 모듈 (analytics, auth, dashboard, database, settings, system, migration 등) |
| `app/core/routes/api/collection/` | 수집 설정·자격증명·이력·소스·상태·동기화·트리거 |
| `app/core/routes/api/blacklist/` | 블랙리스트 배치·수집·코어·관리·시스템 |
| `app/core/routes/api/fortinet/` | Fortinet 등록·코어 |
| `app/core/routes/websocket_routes.py` | 실시간 채널 |

## 상태 / Status

| 영역 / Area | 상태 / State | 비고 / Notes |
| --- | --- | --- |
| 핵심 API | 운영 가능 / Production-ready | `app/core/routes/api` |
| 인증·인가 | 운영 가능 / Production-ready | JWT + 데코레이터 기반 |
| 모니터링 | 운영 가능 / Production-ready | 메트릭·캐시·에러 노출 |
| Fortinet 통합 | 운영 가능 / Production-ready | 등록 API 제공 |
| 웹 UI | 운영 가능 / Production-ready | 템플릿 기반, WebSocket 갱신 |
| 배포 | 운영 가능 / Production-ready | Docker, `Makefile` 검증 명령 |
| 로깅 | 운영 가능 / Production-ready | 구조화 + 로테이션 |

## 먼저 읽을 파일 / First Files to Read

1. `app/run_app.py` — 부트스트랩과 엔트리 포인트.
2. `app/core/app.py`, `app/core/config.py` — 앱 초기화와 환경설정.
3. `app/core/auth_manager.py` 및 `app/core/auth/` — 인증 흐름 이해의 기초.
4. `app/core/routes/api/__init__.py`, `api_routes.py`, `web_routes.py` — 라우트 등록 형태 파악.
5. `app/core/routes/api/collection/` — 수집·동기화 도메인 진입점.
6. `app/core/routes/api/fortinet/` — Fortinet 통합 진입점.
7. `app/utils/structured_logging.py` — 로그 규약 확인.
8. `Makefile` — 운영 명령.

## API와 진입점 / API and Entry Points

| 영역 / Area | 경로·모듈 / Path or Module | 비고 / Notes |
| --- | --- | --- |
| REST 수집 | `app/core/routes/api/collection/*` | config, credentials, history, sources, status, sync, trigger |
| REST 블랙리스트 | `app/core/routes/api/blacklist/*` | batch, collection, core, management, system |
| REST Fortinet | `app/core/routes/api/fortinet/*`, `api/fortinet_register.py` | 방화벽 등록 |
| REST 분석·데이터베이스·설정·시스템 | `app/core/routes/api/analytics.py`, `database_api.py`, `settings_api.py`, `system_api.py`, `core_api.py`, `dashboard_api.py`, `error_metrics_api.py`, `migration.py` | 운영 API |
| REST 모니터링 | `app/core/routes/api/monitoring/metrics.py` | 메트릭 노출 |
| WebSocket | `app/core/routes/websocket_routes.py` | 실시간 갱신 |
| 웹 페이지 | `app/core/routes/web_routes.py` + `app/templates/*` | index, sessions, settings, integrations, collection, collection_logs, monitoring/dashboard |
| 헬스 체크 | `Makefile` `health` 타깃 | 운영 점검 |

## 빠른 시작 / Quickstart

요구 사항: Python 3.11, `make`, Docker(컨테이너 실행 시).

```bash
# 저장소 진입
git clone <repo-url> blacklist-service
cd blacklist-service

# 개발 컨테이너 기동 (핫 리로드)
make dev

# 웹 UI
# http://localhost:2542
```

Python 로컬 실행이 필요할 때는 다음 절차를 따릅니다.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
python app/run_app.py
```

## 설정 / Configuration

| 항목 / Setting | 출처 / Source | 비고 / Notes |
| --- | --- | --- |
| 포트 / Port | `Makefile` `ENV` (`PORT?=2542`) | 기본 2542 |
| 환경 변수 파일 | `Makefile` `--env-file deploy/.env` | 컨테이너 모드 |
| Compose 파일 | `Makefile` `COMPOSE_FILE := deploy/docker-compose.yml` | 배포·개발 공통 |
| 도구 설정 | `pyproject.toml` (pytest, ruff, mypy) | 라인 길이 120, Python 3.11 |
| 커밋 규약 | `commitlint.config.js` | 컨벤셔널 커밋 |
| 린트 | `mypy.ini` | 타입 검사 |
| 인증 | `app/core/auth/*` | JWT 발급·검증 |

## 명령어 참조 / Commands Reference

| 명령어 / Command | 설명 / Purpose |
| --- | --- |
| `make help` | 사용 가능한 타깃 목록 출력 |
| `make setup-hooks` | pre-commit, commit-msg, husky 훅 설치 |
| `make dev` | 개발 컨테이너 기동 (빌드 + 핫 리로드) |
| `make dev-no-build` | 기존 이미지로 기동 |
| `make dev-prod` | 프로덕션 유사 환경 (오버라이드 없음) |
| `make dev-app` | 앱 서비스만 재시작 |
| `make up` / `make down` / `make logs` | 컨테이너 라이프사이클 |
| `make build` | 이미지 빌드 |
| `make test` | 테스트 실행 (pytest, `pyproject.toml` 마커 사용) |
| `make health` | 서비스 헬스 체크 |
| `make verify` / `verify-lint` / `verify-types` / `verify-secrets` / `verify-pre-commit` / `verify-quick` / `verify-all` | 정적 검증 묶음 |
| `make release` / `make release-dry` | 릴리스 절차 / 드라이런 |
| `make clean` | 정리 |

## 로컬 개발 / Local Development

- 코드 스타일: `pyproject.toml`의 Ruff 설정(`line-length = 120`, `target-version = "py311"`).
- 타입 검사: `mypy.ini` 기준. 영역별 무시는 `pyproject.toml` `per-file-ignores` 참조.
- 테스트 마커: `unit`, `integration`, `security`, `db`, `api`. 테스트는 `tests/`(`pyproject.toml` `testpaths`)에서 실행.
- 로그: `app/utils/structured_logging.py` 형식 유지, `log_rotation_manager.py`로 로테이션 점검.
- 컨테이너: `app/Dockerfile`, `app/entrypoint.sh`, 사전 검증은 `app/deployment_validation.py`.

## 테스트 / Testing

```bash
make test
# 또는
pytest -m unit
pytest -m integration
pytest -m api
```

테스트 마커 의미는 다음 표를 따릅니다.

| 마커 / Marker | 용도 / Purpose |
| --- | --- |
| `unit` | 외부 의존성 없는 단위 테스트 |
| `integration` | 서비스 의존 통합 테스트 |
| `security` | 보안 점검 |
| `db` | 데이터베이스 연동 |
| `api` | API 엔드포인트 |

## 기여 / Contributing

- 커밋 컨벤션은 Conventional Commits. `commitlint.config.js` 검사가 적용됩니다.
- PR 전 `make verify`(또는 `verify-all`)으로 린트·타입·시크릿·pre-commit 통과를 확인합니다.
- 자세한 절차는 `CONTRIBUTING.md`, 변경 이력은 `CHANGELOG.md`, 버전은 `VERSION`을 참조합니다.

## 운영자 / Maintainers

| 역할 / Role | 출처 / Source |
| --- | --- |
| 책임자 / Owners | `OWNERS` |
| 정책 기여 규칙 | `CONTRIBUTING.md` |
| 변경 이력 | `CHANGELOG.md` |
| 버전 | `VERSION` |

## 추가 문서 / Further Documentation

| 문서 / Document | 위치 / Location |
| --- | --- |
| 변경 이력 / Changelog | `CHANGELOG.md` |
| 기여 절차 / Contributing | `CONTRIBUTING.md` |
| 에이전트 지침 / Agent notes | `AGENTS.md`, `app/AGENTS.md`, `app/core/AGENTS.md`, `app/core/auth/AGENTS.md`, `app/core/monitoring/AGENTS.md`, `app/core/routes/AGENTS.md`, `app/core/routes/api/AGENTS.md`, `app/core/routes/api/collection/AGENTS.md`, `app/core/routes/api/blacklist/AGENTS.md`, `app/core/routes/api/fortinet/AGENTS.md` |
| 린트·테스트 설정 | `pyproject.toml`, `mypy.ini`, `commitlint.config.js` |
| 운영 명령 | `Makefile` |
| 라이선스 / License | `LICENSE` |

## 라이선스 / License

`LICENSE` 파일의 조항을 따릅니다.