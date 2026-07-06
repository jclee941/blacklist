# Blacklist Service

[![Status: Active](https://img.shields.io/badge/status-active-success)](#status)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](#quick-start)
[![License](https://img.shields.io/badge/license-see%20LICENSE-lightgrey)](LICENSE)
[![Compose](https://img.shields.io/badge/deploy-docker%20compose-2496ED)](#deployment)

운영자가 IP/도메인 블랙리스트를 수집 · 관리 · 동기화하고, Fortinet 장비 및 다운스트림 서비스로 배포할 수 있도록 돕는 Python 웹 서비스입니다. 본 README는 저장소의 실제 코드(`app/`, `Makefile`, `pyproject.toml`)를 기준으로 작성되었습니다.

> 본 저장소는 위에서 보이는 `app/` 패키지, `Makefile`, 템플릿, 라우트 모듈이 핵심 산출물입니다. 저장소 최상위 `AGENTS.md` 일부가 다른 템플릿의 잔재로 보일 경우, 본 README의 설명을 우선합니다.

## 한눈에 보기 (Status)

| 항목 | 값 |
| --- | --- |
| 서비스명 | Blacklist Service |
| 기본 포트 | `2542` (env `PORT`) |
| 런타임 | Python 3.11+, Docker Compose |
| 엔트리포인트 | `app/run_app.py`, 컨테이너 `app/entrypoint.sh` |
| 헬스체크 | `GET /health` (web), `GET /api/...` |
| 인증 | JWT (`app/core/auth/jwt_service.py`) |
| 주요 기능 | 블랙리스트, 컬렉션, Fortinet 연동, 모니터링, WebSocket |
| 빌드/실행 | `make dev` / `make dev-prod` |
| 검증 | `make verify` (lint · type · secret) |
| 라이선스 | `LICENSE` 참조 |

## 실행 흐름 요약 (Flow)

1. `app/entrypoint.sh` 또는 `app/run_app.py`가 Flask 앱 팩토리(`app/core/app.py`)를 부트스트랩합니다.
2. `app/core/config.py`가 환경 변수와 `.env`를 로드하고 로깅(`app/utils/structured_logging.py`)을 초기화합니다.
3. 라우트가 등록됩니다: 웹(`web_routes.py`), API 그룹(`api/`), 프록시, WebSocket, 시스템.
4. 인증 미들웨어(`core/auth/middleware.py`)가 JWT를 검증하고, 운영자는 `templates/index.html` 대시보드에서 작업을 수행합니다.
5. 컬렉션/블랙리스트/Fortinet 모듈이 비동기로 데이터를 수집·동기화하고, 모니터링 모듈이 메트릭을 노출합니다.

## 목차 (Table of Contents)

- [프로젝트 소개](#프로젝트-소개)
- [주요 기능](#주요-기능)
- [아키텍처](#아키텍처)
- [디렉터리 구조](#디렉터리-구조)
- [빠른 시작](#빠른-시작)
- [설정](#설정)
- [명령어 레퍼런스](#명령어-레퍼런스)
- [API 진입점](#api-진입점)
- [로컬 개발](#로컬-개발)
- [테스트](#테스트)
- [배포](#배포)
- [유지보수자와 연락처](#유지보수자와-연락처)
- [추가 문서](#추가-문서)
- [기여 가이드](#기여-가이드)
- [라이선스](#라이선스)

---

## 프로젝트 소개

Blacklist Service는 사내/외부에서 유입되는 위협 인텔리전스(IP, 도메인, CIDR 등)을 일관된 컬렉션 파이프라인으로 수집하고, 운영자가 검증·승인한 항목만 Fortinet 장비 및 다운스트림 차단 시스템으로 배포할 수 있도록 만든 웹 애플리케이션입니다. 웹 UI, REST API, WebSocket 채널을 모두 제공하며 단일 Docker Compose 스택으로 실행됩니다.

### 사용 대상

- 보안 운영팀: 위협 인텔리전스 큐레이션, 승인 워크플로우
- 네트워크 운영팀: Fortinet 정책 자동 배포, 변경 이력 추적
- 플랫폼 팀: 단일 바이너리/컨테이너로 통합된 차단 데이터 서비스

## 주요 기능

- **컬렉션(Collection)**: 다중 소스에서 IP/도메인 항목을 수집하고 중복 제거·정규화 (`app/core/routes/api/collection/`).
- **블랙리스트(Blacklist)**: 배치/단건 추가, 시스템/관리/콜렉션 분리 API (`app/core/routes/api/blacklist/`).
- **Fortinet 연동**: 디바이스 등록, 정책 동기화 (`app/core/routes/api/fortinet/`, `fortinet_register.py`).
- **인증/권한**: JWT 발급·검증, 데코레이터 기반 보호 (`app/core/auth/`).
- **모니터링**: 캐시/에러 메트릭, 대시보드 (`app/core/monitoring/`, `templates/monitoring/`).
- **프록시 라우트**: 다운스트림 클라이언트용 프록시 엔드포인트.
- **WebSocket**: 실시간 알림/상태 채널 (`websocket_routes.py`).
- **웹 UI**: Jinja2 템플릿(`index.html`, `collection.html`, `settings.html`, `sessions.html`, `integrations.html`, `monitoring/dashboard.html`).
- **로그 회전/구조화 로깅**: 운영용 로깅 파이프라인 (`app/utils/`).
- **배포 검증**: 기동 전 설정 무결성 점검 (`app/deployment_validation.py`).

## 아키텍처

| 계층 | 모듈 | 책임 |
| --- | --- | --- |
| 엔트리 | `app/run_app.py`, `app/entrypoint.sh` | 부트스트랩, 컨테이너 시작 |
| 앱 팩토리 | `app/core/app.py` | Flask 앱 생성, 블루프린트 등록 |
| 설정/로깅 | `app/core/config.py`, `app/utils/structured_logging.py` | 환경 로드, JSON 로그 |
| 인증 | `app/core/auth/*` | JWT, 미들웨어, 데코레이터 |
| 라우트 | `app/core/routes/*` | 웹/API/WebSocket/프록시/시스템 |
| 도메인 API | `app/core/routes/api/{collection,blacklist,fortinet,monitoring}/` | 비즈니스 로직 |
| 모니터링 | `app/core/monitoring/*` | 메트릭 수집·노출 |
| UI | `app/templates/*` | 서버 렌더링 페이지 |
| 운영 | `app/utils/log_rotation_manager.py`, `deployment_validation.py` | 로그 회전, 사전 점검 |

요청 흐름 예시(컬렉션 동기화):

1. 운영자가 `POST /api/collection/sync` 호출.
2. `collection/sync.py`가 소스 어댑터(`sources.py`)를 통해 데이터를 수집.
3. `credentials.py`가 자격증명을 안전하게 로드.
4. `history.py`가 변경 이력을 기록.
5. WebSocket 채널(`websocket_routes.py`)이 클라이언트에 진행 상태를 푸시.
6. 메트릭이 `monitoring/metrics.py`에 누적되어 대시보드에서 확인.

## 디렉터리 구조

| 경로 | 설명 |
| --- | --- |
| `app/` | 애플리케이션 패키지 루트 |
| `app/run_app.py` | 로컬 실행 엔트리포인트 |
| `app/entrypoint.sh` | 컨테이너 시작 스크립트 |
| `app/deployment_validation.py` | 기동 전 무결성 검사 |
| `app/Dockerfile` | 서비스 이미지 빌드 정의 |
| `app/requirements.txt` | Python 의존성 |
| `app/core/app.py` | Flask 앱 팩토리 |
| `app/core/config.py` | 환경설정 로더 |
| `app/core/auth/` | JWT, 미들웨어, 데코레이터 |
| `app/core/monitoring/` | 메트릭, 캐시, 에러 |
| `app/core/routes/` | 웹/API/프록시/WebSocket/시스템 라우트 |
| `app/core/routes/api/` | 도메인 API (collection, blacklist, fortinet, monitoring) |
| `app/templates/` | Jinja2 템플릿(웹 UI) |
| `app/utils/` | 로깅, 로그 회전 |
| `Makefile` | 빌드/실행/검증/릴리스 타겟 |
| `pyproject.toml` | Ruff, pytest, mypy 설정 |
| `mypy.ini` | 타입 체커 옵션 |
| `commitlint.config.js` | 커밋 메시지 규약 |
| `CHANGELOG.md`, `VERSION` | 변경 이력/버전 |
| `OWNERS` | 코드 오너십 |
| `CONTRIBUTING.md` | 기여 절차 |

## 빠른 시작

### 사전 요구사항

- Docker 24+ 및 Docker Compose v2
- Python 3.11+ (로컬 직접 실행 시)
- Make

### 컨테이너로 실행 (권장)

```bash
# 1) 환경 파일 준비
cp deploy/.env.example deploy/.env  # 없다면 deploy/.env를 직접 작성

# 2) 개발 스택 기동 (핫 리로드)
make dev

# 3) 브라우저에서 접속
open http://localhost:2542
```

### 로컬에서 직접 실행

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
python app/run_app.py
```

## 설정

환경 변수는 `deploy/.env` 또는 런타임 환경에서 주입합니다. 주요 키는 다음과 같습니다.

| 변수 | 용도 | 기본값 |
| --- | --- | --- |
| `PORT` | 웹 리스닝 포트 | `2542` |
| `FLASK_ENV` | `development` / `production` | `development` |
| `JWT_SECRET` | JWT 서명 비밀 | (필수) |
| `JWT_EXPIRES` | 토큰 만료(초) | 운영 정책 |
| `DATABASE_URL` | DB 연결 문자열 | 운영 정책 |
| `FORTINET_*` | Fortinet 디바이스 정보 | 컬렉션 정책 |
| `LOG_LEVEL` | 루트 로그 레벨 | `INFO` |
| `LOG_DIR` | 로그 파일 경로 | `/var/log/blacklist` |

상세 키 정의는 `app/core/config.py`를 참조하세요.

## 명령어 레퍼런스

`make help`로 전체 목록을 확인할 수 있습니다.

| 타겟 | 설명 |
| --- | --- |
| `make setup-hooks` | pre-commit · commit-msg 훅 설치 |
| `make dev` | 개발 스택 기동 (빌드 포함, 핫 리로드) |
| `make dev-no-build` | 기존 이미지로 빠르게 기동 |
| `make dev-prod` | 운영 모드에 가까운 스택 기동 (핫 리로드 없음) |
| `make dev-app` | app 서비스만 재기동 |
| `make build` | 이미지 빌드 |
| `make up` / `make down` | 스택 기동/중지 |
| `make logs` | 로그 스트림 |
| `make restart` | 재기동 |
| `make health` | 헬스체크 |
| `make test` | 테스트 실행 |
| `make verify` | lint · type · secret 일괄 점검 |
| `make verify-lint` | Ruff |
| `make verify-types` | mypy |
| `make verify-secrets` | 시크릿 스캔 |
| `make verify-pre-commit` | pre-commit 훅 실행 |
| `make verify-quick` | 빠른 검증 |
| `make verify-all` | 전체 검증 |
| `make release` | 릴리스 절차 |
| `make release-dry` | 릴리스 드라이런 |
| `make clean` | 정리 |

## API 진입점

라우트는 `app/core/routes/`에 모듈 단위로 분리되어 있습니다. 대표 진입점은 다음과 같습니다.

| 카테고리 | 모듈 | 비고 |
| --- | --- | --- |
| 웹 UI | `web_routes.py` | Jinja2 페이지 렌더링 |
| 시스템 | `system_routes.py` | 헬스, 메타, 헬스체크 |
| 프록시 | `proxy_routes.py` | 다운스트림 전달 |
| WebSocket | `websocket_routes.py` | 실시간 채널 |
| 인증 API | `api/auth_routes.py` | 로그인/토큰 |
| 코어 API | `api/core_api.py` | 공통 리소스 |
| 대시보드 API | `api/dashboard_api.py` | 요약 데이터 |
| 데이터베이스 API | `api/database_api.py` | DB 메타 |
| 설정 API | `api/settings_api.py` | 런타임 설정 |
| 분석 API | `api/analytics.py` | 통계/리포트 |
| 마이그레이션 | `api/migration.py` | 스키마 변경 |
| Fortinet 등록 | `api/fortinet_register.py` | 디바이스 등록 |
| IP 관리 | `api/ip_management_helpers.py` | IP CIDR 유틸 |
| 에러 메트릭 | `api/error_metrics_api.py` | 오류 가시화 |
| 컬렉션 | `api/collection/*` | sync, history, sources, trigger, status |
| 블랙리스트 | `api/blacklist/*` | batch, collection, management, system |
| Fortinet | `api/fortinet/*` | 정책 동기화 |
| 모니터링 | `api/monitoring/metrics.py` | 메트릭 조회 |

## 로컬 개발

1. `make setup-hooks`로 pre-commit 훅을 설치합니다.
2. `make dev`로 기동한 뒤 `app/` 하위 코드 변경은 볼륨 마운트로 즉시 반영됩니다.
3. 코드 스타일: Ruff(`pyproject.toml`, line-length 120, Python 3.11 타깃).
4. 타입 검사: `mypy.ini` 정책에 따라 `make verify-types`.
5. 커밋 규약: Conventional Commits(`commitlint.config.js`).
6. 템플릿 변경 시 `app/templates/`의 Jinja2 파일을 수정합니다.

## 테스트

- 러너: pytest (`pyproject.toml`의 `[tool.pytest.ini_options]`)
- 경로: `tests/`
- 마커: `unit`, `integration`, `security`, `db`, `api`
- 실행: `make test` 또는 `pytest`

## 배포

- 단일 컨테이너: `app/Dockerfile`로 이미지를 빌드하고 `app/entrypoint.sh`로 기동.
- Docker Compose: `deploy/docker-compose.yml` + `deploy/.env`.
- 기동 전 무결성 검사: `app/deployment_validation.py`.
- 로그: `app/utils/log_rotation_manager.py`로 회전 정책 적용.

## 유지보수자와 연락처

- 코드 오너십: [`OWNERS`](OWNERS)
- 이슈/요청: 저장소 Issue 트래커 사용
- 변경 이력: [`CHANGELOG.md`](CHANGELOG.md)
- 현재 버전: [`VERSION`](VERSION)
- 기여 절차: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- AI 에이전트 지침: [`AGENTS.md`](AGENTS.md)

## 추가 문서

- 릴리스 노트: [`CHANGELOG.md`](CHANGELOG.md)
- 기여 가이드: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- 패키지 메타: [`pyproject.toml`](pyproject.toml)
- 빌드/실행 규약: [`Makefile`](Makefile)
- 애플리케이션 가이드: [`app/AGENTS.md`](app/AGENTS.md)
- 코어 가이드: [`app/core/AGENTS.md`](app/core/AGENTS.md)

## 기여 가이드

1. 이슈를 먼저 등록하거나 기존 이슈를 참조합니다.
2. `CONTRIBUTING.md`의 절차와 `commitlint.config.js` 규약을 따릅니다.
3. PR 전 `make verify` 통과를 권장합니다 (`verify-lint`, `verify-types`, `verify-secrets`).
4. 도메인 모듈(`collection`, `blacklist`, `fortinet`, `monitoring`) 변경 시 각 하위 `AGENTS.md`의 가이드를 우선합니다.

## 라이선스

[`LICENSE`](LICENSE) 파일의 조항을 따릅니다.
```

```json
{
  "version": 1,
  "title": "Blacklist Service README",
  "language": ["ko", "en"],
  "viewports": {
    "first_viewport_under_120_lines": true,
    "status_table_count": 1,
    "flow_summary_present": true
  },
  "structure": [
    "Title + badges",
    "Korean summary",
    "Status table",
    "Flow summary",
    "TOC",
    "Introduction",
    "Features",
    "Architecture (table)",
    "Directory structure (table)",
    "Quickstart",
    "Configuration",
    "Commands reference",
    "API entry points",
    "Local development",
    "Testing",
    "Deployment",
    "Maintainers",
    "Further docs",
    "Contributing",
    "License"
  ],
  "removed_stale_blocks": [
    "jclee-bot automation surfaces",
    "cliproxy references",
    "bot.jclee.me control plane",
    "monorepo branding",
    "auto-generated README metadata"
  ],
  "notes": "Stale AGENTS.md content describing community-health-file SSoT was ignored; the actual product is the Python Blacklist Service under app/. All directory listings are derived strictly from the provided project tree."
}