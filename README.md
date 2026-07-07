# Blacklist Service Management

![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![Framework](https://img.shields.io/badge/framework-Flask-lightgrey.svg)
![Compose](https://img.shields.io/badge/orchestration-Docker%20Compose-2496ED.svg)
![License](https://img.shields.io/badge/license-See%20LICENSE-blue.svg)
![Status](https://img.shields.io/badge/status-Active-success.svg)

## 한국어 요약

Blacklist Service Management는 Fortinet 방화벽과 연동되는 IP/도메인 블랙리스트 수집·정규화·배포 백엔드입니다. 외부 위협 인텔리전스 소스에서 입력 항목을 자동 수집하고, JWT 인증 기반의 REST API와 WebSocket으로 운영자에게 통합 관리 화면과 실시간 동기화 기능을 제공합니다. Docker Compose와 Make 타깃을 통해 빌드·배포·검증을 자동화합니다.

## English Summary

A Flask-based backend that aggregates IP/domain threat intelligence from external feeds, normalizes the entries, and pushes them to Fortinet address groups. It exposes a JWT-protected REST API, a WebSocket channel for live updates, and a web UI for collection, sessions, integrations, settings, and monitoring. The project is shipped with Docker Compose orchestration, Make targets for build/test/deploy, and a strict verify-all gate (Ruff, mypy, secrets, pre-commit).

## Quick Status

| 항목 | 값 |
| --- | --- |
| 제품 | Blacklist Service Management (Python 웹 애플리케이션) |
| Python | 3.11 |
| 기본 포트 | 2542 (개발) |
| 런타임 | Docker Compose (Makefile 기반) |
| 인증 | JWT (`app/core/auth/`) |
| API | REST + WebSocket (`app/core/routes/`) |
| 외부 연동 | Fortinet (`app/core/routes/api/fortinet/`) |
| 모니터링 | Metrics + 구조화 로그 + 대시보드 |
| 테스트 | pytest (unit, integration, security, db, api) |
| 코드 품질 | Ruff, mypy, pre-commit, commitlint |
| 라이선스 | `LICENSE` 참조 |

## 흐름 요약

1. `make dev` 실행 → Docker Compose로 앱 컨테이너 기동 → `http://localhost:2542` 노출.
2. 소스 컬렉션(외부 위협 피드)에서 `credentials.py`로 자격증명을 받아 데이터 수집 → `collection/sync.py`로 동기화.
3. 수집 항목은 `blacklist/collection.py`와 `blacklist/batch.py`를 거쳐 정규화·중복 제거 → `blacklist/core.py`에서 블랙리스트로 통합.
4. 관리자는 웹 UI(`templates/index.html`, `collection.html`, `monitoring/dashboard.html`) 또는 REST API로 조회·수정.
5. `fortinet/core.py`가 변경분을 Fortinet 방화벽에 푸시 → 결과가 `error_metrics`와 `metrics.py`로 노출.
6. WebSocket(`websocket_routes.py`)이 운영자에게 실시간 상태·로그 알림 전달.

## 목차

- [Purpose / Package Contents](#purpose--package-contents)
- [Status](#status)
- [First Files to Read](#first-files-to-read)
- [API & Entry Points](#api--entry-points)
- [Quickstart](#quickstart)
- [아키텍처](#아키텍처)
- [Configuration](#configuration)
- [Commands Reference](#commands-reference)
- [Local Development](#local-development)
- [Testing](#testing)
- [Contribution Guide](#contribution-guide)
- [Maintainers](#maintainers)
- [License](#license)
- [Further Documentation](#further-documentation)

## Purpose / Package Contents

이 저장소는 Fortinet 방화벽과 연동되는 블랙리스트 관리 백엔드 서비스를 제공합니다. 위협 인텔리전스 소스로부터 IP/도메인 항목을 자동 수집·검증한 뒤 Fortinet 주소 그룹으로 배포하며, 운영자는 대시보드에서 동기화 이력과 에러 메트릭을 확인할 수 있습니다.

디렉토리 역할:

| 경로 | 설명 |
| --- | --- |
| `app/run_app.py` | 애플리케이션 부트스트랩 진입점 |
| `app/Dockerfile`, `app/entrypoint.sh` | 컨테이너 이미지 및 부트 스크립트 |
| `app/requirements.txt` | Python 의존성 |
| `app/deployment_validation.py` | 배포 전 환경 검증 |
| `app/utils/` | 구조화 로깅, 로그 로테이션 |
| `app/templates/` | 웹 UI (index, collection, sessions, integrations, settings, monitoring/dashboard) |
| `app/core/app.py` | Flask 앱 팩토리 |
| `app/core/config.py` | 환경 설정 로더 |
| `app/core/auth_manager.py` | 인증 정책 진입점 |
| `app/core/dashboard.py` | 대시보드 데이터 어그리게이터 |
| `app/core/testing_app.py` | 테스트 모드 부트스트랩 |
| `app/core/auth/` | JWT 서비스, 데코레이터, 미들웨어 |
| `app/core/monitoring/` | metrics, error_metrics, cache_metrics |
| `app/core/routes/` | web, api, proxy, websocket, system 라우터 |
| `app/core/routes/api/collection/` | 소스, 동기화, 트리거, 자격증명, 히스토리, 상태, 설정 |
| `app/core/routes/api/blacklist/` | 코어, 배치, 관리, 시스템 |
| `app/core/routes/api/fortinet/` | Fortinet 등록·푸시 어댑터 |
| `app/core/routes/api/monitoring/` | 메트릭 API |

## Status

| 영역 | 상태 |
| --- | --- |
| 프로덕션 준비도 | 운영 중 (`make prod`, `make deploy` 타깃 보유) |
| 릴리스 프로세스 | Conventional Commits + `make release` / `make release-dry` |
| 코드 품질 게이트 | Ruff, mypy, pre-commit, commitlint |
| 보안 검증 | `make verify-secrets` 타깃 제공 |
| 일괄 검증 | `make verify-all` (lint + types + secrets + pre-commit) |
| 모듈별 운영 규칙 | `AGENTS.md` 트리 (모듈 단위 가이드) |

## First Files to Read

운영자가 코드를 처음 살펴볼 때 다음 순서로 읽으면 전체 구조를 빠르게 파악할 수 있습니다.

1. `Makefile` — 빌드/실행/검증 명령어와 환경 변수
2. `app/run_app.py` — 앱 부트스트랩
3. `app/core/app.py` — Flask 팩토리, 라우터 등록
4. `app/core/config.py` — 환경 변수 기반 설정
5. `app/core/routes/api/collection/sync.py` — 핵심 동기화 흐름
6. `app/core/routes/api/fortinet/core.py` — Fortinet 연동 어댑터
7. `app/core/monitoring/metrics.py` — 메트릭 정의
8. `app/utils/structured_logging.py` — 로깅 정책

## API & Entry Points

### 엔트리 포인트

| 진입점 | 위치 | 설명 |
| --- | --- | --- |
| 부트 | `app/run_app.py` | 개발·운영 부트 |
| 컨테이너 | `app/entrypoint.sh` | Docker 컨테이너 시작 스크립트 |
| 테스트 부트 | `app/core/testing_app.py` | 테스트 모드 앱 팩토리 |
| 배포 검증 | `app/deployment_validation.py` | 배포 전 환경 점검 |

### 라우트 그룹

| 그룹 | 파일 | 역할 |
| --- | --- | --- |
| 웹 UI | `app/core/routes/web_routes.py` | 템플릿 렌더링, 대시보드 |
| REST API | `app/core/routes/api_routes.py` | API v1 마운트 |
| 프록시 | `app/core/routes/proxy_routes.py` | 외부 시스템 프록시 |
| 시스템 | `app/core/routes/system_routes.py` | 헬스체크, 시스템 정보 |
| WebSocket | `app/core/routes/websocket_routes.py` | 실시간 이벤트 |
| 컬렉션 API | `app/core/routes/api/collection/` | 소스, 동기화, 트리거, 자격증명, 히스토리, 상태, 설정 |
| 블랙리스트 API | `app/core/routes/api/blacklist/` | 코어, 배치, 관리, 시스템 |
| Fortinet API | `app/core/routes/api/fortinet/` | 방화벽 등록·푸시 |
| 인증 API | `app/core/routes/api/auth_routes.py` | 로그인/토큰 발급 |
| 모니터링 API | `app/core/routes/api/monitoring/metrics.py` | 메트릭 노출 |

### 인증

JWT 기반 인증은 `app/core/auth/jwt_service.py`에서 토큰을 발급·검증하며, `decorators.py`와 `middleware.py`가 라우트 보호와 요청 컨텍스트 구성을 담당합니다. 인증 정책 진입점은 `app/core/auth_manager.py`입니다.

## Quickstart

### 1) 환경 변수 준비

```bash
cp deploy/.env.example deploy/.env
# edit deploy/.env (필수 키 입력)
```

### 2) 개발 환경 기동

```bash
make dev
```

Makefile이 `deploy/docker-compose.yml`을 사용해 빌드 후 컨테이너를 띄우며, 볼륨 마운트로 핫 리로드됩니다. 앱은 `http://localhost:2542`에서 접근할 수 있습니다.

### 3) 시나리오별 명령

| 시나리오 | 명령 |
| --- | --- |
| 코드만 바뀌었을 때 빠른 재기동 | `make dev-app` |
| 이미지 재빌드 없이 빠르게 시작 | `make dev-no-build` |
| 프로덕션 유사 환경 (볼륨 마운트 없음) | `make dev-prod` |
| 헬스 체크 | `make health` |

## 아키텍처

본 서비스는 단일 백엔드 앱과 Docker Compose 오케스트레이션으로 구성됩니다.

### 컴포넌트

| 레이어 | 모듈 | 책임 |
| --- | --- | --- |
| Entry | `run_app.py`, `entrypoint.sh` | 부트, 마이그레이션, 헬스체크 |
| Web | `core/app.py`, `routes/web_routes.py` | Flask 팩토리, 템플릿 |
| API | `routes/api_routes.py`, `routes/api/*` | REST v1 엔드포인트 |
| Realtime | `routes/websocket_routes.py` | WebSocket 푸시 |
| Domain | `routes/api/collection/*`, `routes/api/blacklist/*` | 동기화, 배치, 관리 |
| Adapter | `routes/api/fortinet/core.py` | Fortinet 방화벽 연동 |
| Auth | `core/auth/*`, `core/auth_manager.py` | JWT, 권한 검사 |
| Observability | `core/monitoring/*`, `utils/structured_logging.py` | 메트릭, 구조화 로그 |
| Validation | `deployment_validation.py` | 배포 전 검증 |

### 요청 흐름

1. 클라이언트(웹 UI 또는 외부 시스템)가 `/api/v1/...` 엔드포인트 호출.
2. `routes/api_routes.py`가 블루프린트를 마운트하고 `core/auth/middleware.py`가 JWT 검증.
3. 도메인 라우터가 `routes/api/collection`/`blacklist` 서비스 호출.
4. 컬렉션 동기화 시 외부 소스에서 페치 → 정규화 → `blacklist/core.py`로 합류.
5. `routes/api/fortinet/core.py`가 변경분을 Fortinet으로 푸시, 결과를 `monitoring/error_metrics.py`에 기록.
6. WebSocket 채널이 운영자에게 진행 상황/오류 푸시.
7. 응답 직전에 `monitoring/metrics.py`가 카운터·히스토그램 갱신.

## Configuration

설정은 환경 변수 기반으로 `app/core/config.py`가 로드합니다. 다음은 일반적으로 사용되는 키입니다 (실제 키 목록은 `deploy/.env.example` 참조).

| 키 | 용도 | 비고 |
| --- | --- | --- |
| `ENV` | 실행 환경 | `development`, `production` |
| `PORT` | 앱 노출 포트 | 기본 `2542` |
| `JWT_SECRET` | JWT 서명 키 | 필수, 강력한 랜덤 값 |
| `DATABASE_URL` | DB 연결 문자열 | 필수 |
| `FORTINET_HOST` | Fortinet 관리 호스트 | 필수 |
| `FORTINET_API_TOKEN` | Fortinet API 토큰 | 필수 |
| `LOG_LEVEL` | 로그 레벨 | `INFO`, `DEBUG` |
| `LOG_DIR` | 로그 디렉터리 | `/var/log/blacklist` 등 |

`.env` 파일 또는 배포 매니페스트(`deploy/`)를 통해 주입합니다.

## Commands Reference

| 명령 | 설명 |
| --- | --- |
| `make help` | 사용 가능한 타깃 목록 출력 |
| `make setup-hooks` | pre-commit, commit-msg, husky 설치 |
| `make dev` | 개발 환경 기동 (빌드 포함, 핫 리로드) |
| `make dev-no-build` | 기존 이미지로 빠른 기동 |
| `make dev-app` | 앱 서비스만 재기동 |
| `make dev-prod` | 프로덕션 유사 환경 (볼륨 마운트 없음) |
| `make build` | 컨테이너 이미지 빌드 |
| `make up` | 컨테이너 기동 |
| `make down` | 컨테이너 종료 |
| `make restart` | 컨테이너 재기동 |
| `make logs` | 컨테이너 로그 스트리밍 |
| `make health` | 헬스 체크 |
| `make test` | 테스트 실행 |
| `make deploy` | 배포 |
| `make prod` | 프로덕션 모드 기동 |
| `make verify` | 기본 검증 |
| `make verify-lint` | Ruff 검사 |
| `make verify-types` | mypy 검사 |
| `make verify-secrets` | 비밀키 검사 |
| `make verify-pre-commit` | pre-commit 훅 실행 |
| `make verify-quick` | 빠른 검증 (lint + secrets) |
| `make verify-all` | 모든 검증 일괄 실행 |
| `make release` | 릴리스 절차 실행 |
| `make release-dry` | 릴리스 드라이런 |
| `make clean` | 임시 파일/이미지 정리 |

## Local Development

### 환경 요건

- Python 3.11
- Docker + Docker Compose v2
- Make
- (선택) Node.js — 프런트엔드 패키지가 있을 경우 ESLint/Prettier 실행용

### 권장 워크플로우

1. `make setup-hooks`로 깃 훅을 한 번 설치합니다.
2. `make dev`로 컨테이너 환경을 띄웁니다.
3. `app/core/` 및 `app/core/routes/api/` 하위 모듈을 수정합니다.
4. 변경 후 `make verify-quick`로 빠르게 린트·시크릿 점검.
5. PR 전 `make verify-all`로 전체 검증.

### 로깅

`app/utils/structured_logging.py`가 JSON 구조화 로그를 생성하며, `log_rotation_manager.py`가 디스크 로테이션 정책을 관리합니다. 로그 디렉터리는 `LOG_DIR` 환경 변수로 변경할 수 있습니다.

## Testing

테스트 설정은 `pyproject.toml`의 `[tool.pytest.ini_options]`에 정의되어 있습니다.

| 항목 | 값 |
| --- | --- |
| `pythonpath` | `app` |
| `testpaths` | `tests` |
| 마커 | `unit`, `integration`, `security`, `db`, `api` |

### 실행 예시

```bash
# 전체 테스트
make test

# 단위 테스트만
pytest -m unit

# 통합 테스트
pytest -m integration

# API 테스트
pytest -m api
```

### 마커 가이드

| 마커 | 용도 |
| --- | --- |
| `unit` | 외부 의존성 없는 단위 테스트 |
| `integration` | 실제 서비스(DB 등) 연동 테스트 |
| `security` | 인증/인가 보안 테스트 |
| `db` | 데이터베이스 마이그레이션·쿼리 테스트 |
| `api` | REST/WebSocket 엔드포인트 테스트 |

## Contribution Guide

1. `CONTRIBUTING.md`의 절차와 코드 스타일 가이드를 먼저 확인합니다.
2. Conventional Commits(`commitlint.config.js`) 형식을 따릅니다.
3. PR 전 `make verify-all` 통과가 필요합니다.
4. API/라우트 변경 시 관련 마커(`api`, `db`, `security`)로 테스트를 추가합니다.
5. `OWNERS` 파일에 정의된 리뷰어의 승인을 받아야 머지됩니다.
6. 변경 이력은 `CHANGELOG.md` 형식을 따릅니다.

## Maintainers

| 역할 | 위치 |
| --- | --- |
| 리뷰어/승인자 | `OWNERS` |
| 에이전트 운영 규칙 | `AGENTS.md` |
| 모듈별 상세 규칙 | `app/AGENTS.md`, `app/core/AGENTS.md`, `app/core/auth/AGENTS.md`, `app/core/monitoring/AGENTS.md`, `app/core/routes/AGENTS.md`, `app/core/routes/api/AGENTS.md`, `app/core/routes/api/collection/AGENTS.md`, `app/core/routes/api/blacklist/AGENTS.md`, `app/core/routes/api/fortinet/AGENTS.md` |
| 변경 이력 | `CHANGELOG.md` |
| 현재 버전 | `VERSION` |

## License

라이선스 전문은 `LICENSE` 파일을 참조하십시오.

## Further Documentation

| 주제 | 위치 |
| --- | --- |
| 릴리스 절차 | `CHANGELOG.md`, `VERSION` |
| 기여 절차 | `CONTRIBUTING.md` |
| 컨테이너 운영 | `deploy/docker-compose.yml`, `app/Dockerfile` |
| 인증 메커니즘 | `app/core/auth/AGENTS.md`, `app/core/auth_manager.py` |
| 모니터링 정책 | `app/core/monitoring/AGENTS.md`, `app/core/monitoring/metrics.py` |
| 컬렉션 도메인 | `app/core/routes/api/collection/AGENTS.md`, `app/core/routes/api/collection/sync.py` |
| 블랙리스트 도메인 | `app/core/routes/api/blacklist/AGENTS.md`, `app/core/routes/api/blacklist/core.py` |
| Fortinet 연동 | `app/core/routes/api/fortinet/AGENTS.md`, `app/core/routes/api/fortinet/core.py` |
| 배포 검증 | `app/deployment_validation.py` |