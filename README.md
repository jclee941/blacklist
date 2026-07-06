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

여러 외부 위협 인텔리전스 소스에서 IP·도메인·URL 을 수집·정규화해 중앙 블랙리스트로 통합한 뒤, Fortinet 형 보안 장비로 자동 배포하는 Python 기반 통합 관리 플랫폼입니다. Jinja2 웹 콘솔, REST API, WebSocket 실시간 채널을 단일 Flask 진입점으로 제공합니다.

## English Summary

A Python platform that aggregates external threat-intel feeds, normalizes entries (IPs, domains, URLs) into a centralized blacklist, and pushes the resulting address objects to Fortinet-style network devices via REST and WebSocket. A Jinja2 web console, REST API, and real-time WebSocket channel share a single Flask application entry point.

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

1. **수집 / Collect** — `core/routes/api/collection/sources.py` 가 외부 피드를 호출
2. **정규화 / Normalize** — `collection/utils.py` 에서 IP·도메인·URL 형식 통일
3. **저장 / Persist** — `collection/history.py` 가 변경 이력과 함께 중앙 블랙리스트에 반영
4. **배포 / Deploy** — `fortinet/core.py` 가 REST API 로 Fortinet 주소 객체 푸시
5. **모니터링 / Monitor** — `monitoring/metrics.py` 가 캐시·에러·처리량 지표를 노출
6. **운영 / Operate** — `web_routes.py` 의 Jinja2 콘솔과 `websocket_routes.py` 의 실시간 채널이 알림 제공

---

## Table of Contents · 목차

- [Purpose & Package Contents · 목적과 구성](#purpose--package-contents--목적과-구성)
- [Who Uses It · 사용자](#who-uses-it--사용자)
- [Features · 주요 기능](#features--주요-기능)
- [Architecture · 아키텍처](#architecture--아키텍처)
- [First Files to Read · 먼저 읽을 파일](#first-files-to-read--먼저-읽을-파일)
- [API & Entry Points · API 와 진입점](#api--entry-points--api-와-진입점)
- [Quickstart · 빠른 시작](#quickstart--빠른-시작)
- [Configuration · 설정](#configuration--설정)
- [Commands Reference · 명령어](#commands-reference--명령어)
- [Local Development · 로컬 개발](#local-development--로컬-개발)
- [Testing · 테스트](#testing--테스트)
- [Operations · 운영](#operations--운영)
- [Contributing · 기여](#contributing--기여)
- [Maintainers · 관리자](#maintainers--관리자)
- [License · 라이선스](#license--라이선스)
- [Further Documentation · 추가 문서](#further-documentation--추가-문서)

---

## Purpose & Package Contents · 목적과 구성

### 목적 / Purpose

분산된 위협 인텔리전스 소스를 단일 사실 출처(SSOT) 블랙리스트로 통합하고, 이를 Fortinet 같은 외부 보안 장비에 자동 배포·동기화하기 위한 내부 운영 플랫폼입니다. 중앙 집중식 관리 콘솔과 자동화된 동기화 워크플로를 통해 SOC·네트워크 운영팀의 수동 작업을 줄이고 차단 정확도를 높이는 것이 목표입니다.

The platform centralizes distributed threat-intel sources into a single source-of-truth blacklist and automates deployment to Fortinet-style devices. It targets SOC and network operations teams that need to reduce manual curation work and improve blocking accuracy.

### 패키지 구성 / Package Contents

| 경로 / Path | 역할 / Role |
| --- | --- |
| `app/run_app.py` | 로컬 개발용 Flask 부트스트랩 |
| `app/entrypoint.sh` | 컨테이너 시작 스크립트 |
| `app/Dockerfile` | 런타임 이미지 정의 |
| `app/deployment_validation.py` | 배포 전 환경·설정 검증 |
| `app/core/app.py` | Flask 앱 팩토리, 블루프린트 등록 |
| `app/core/config.py` | 환경 변수 기반 설정 로더 |
| `app/core/auth_manager.py` | 인증 정책 관리 |
| `app/core/dashboard.py` | 운영 대시보드 집계 |
| `app/core/testing_app.py` | 테스트 모드 부트스트랩 |
| `app/core/auth/` | JWT 발급·검증, 데코레이터, 미들웨어 |
| `app/core/routes/web_routes.py` | Jinja2 페이지 라우팅 |
| `app/core/routes/api_routes.py` | REST API 진입점 |
| `app/core/routes/websocket_routes.py` | 실시간 채널 |
| `app/core/routes/proxy_routes.py` | 외부 프록시 라우팅 |
| `app/core/routes/system_routes.py` | 헬스체크·메트릭 노출 |
| `app/core/routes/api/collection/` | 피드 수집·이력·상태·트리거 |
| `app/core/routes/api/blacklist/` | 블랙리스트 CRUD·일괄 처리 |
| `app/core/routes/api/fortinet/` | Fortinet 주소 객체 배포 |
| `app/core/routes/api/migration.py` | 데이터 마이그레이션 |
| `app/core/routes/api/fortinet_register.py` | Fortinet 디바이스 등록 |
| `app/core/monitoring/` | 캐시·에러·일반 메트릭 |
| `app/utils/structured_logging.py` | JSON 구조화 로그 |
| `app/utils/log_rotation_manager.py` | 로그 회전 정책 |
| `app/templates/` | Jinja2 템플릿 (index, collection, sessions, settings, integrations, monitoring) |
| `Makefile` | 개발·검증·배포 명령어 |
| `pyproject.toml` | Ruff, mypy, pytest 설정 |
| `commitlint.config.js` | Conventional Commit 강제 |

---

## Who Uses It · 사용자

| 역할 / Role | 사용 시나리오 / Scenario |
| --- | --- |
| SOC 분석가 / SOC analyst | 신규 위협 인텔을 검토하고 블랙리스트 편입 여부 결정 |
| 네트워크 운영자 / Network ops | Fortinet 장비 동기화 상태를 대시보드에서 확인 |
| 보안 엔지니어 / Security engineer | 새 외부 피드 소스를 등록하고 정규화 규칙 튜닝 |
| 플랫폼 운영자 / Platform ops | `make verify`, `make deploy`, 헬스체크로 안정성 확보 |
| 감사·컴플라이언스 / Audit & compliance | 변경 이력(`history`) 과 동기화 결과를 추적 |

---

## Features · 주요 기능

| 기능 / Feature | 설명 / Description |
| --- | --- |
| 위협 인텔 수집 / Threat-intel collection | 외부 피드를 주기적·수동으로 수집 (`collection/sources.py`, `trigger.py`) |
| 중앙 블랙리스트 / Centralized blacklist | IP·도메인·URL 통합 저장 및 CRUD (`blacklist/management.py`) |
| Fortinet 자동 배포 / Fortinet auto-deploy | REST API 로 주소 객체 푸시 (`fortinet/core.py`, `fortinet_register.py`) |
| 실시간 채널 / Real-time channel | WebSocket 으로 수집·동기화 상태 푸시 (`websocket_routes.py`) |
| 인증·인가 / AuthN-Z | JWT 발급·검증, 데코레이터, 미들웨어 (`auth/`) |
| 운영 대시보드 / Operations dashboard | 메트릭·로그·컬렉션 시각화 (`dashboard.py`, `templates/monitoring/`) |
| 구조화 로깅 / Structured logging | JSON 로그 + 회전 정책 (`utils/structured_logging.py`, `utils/log_rotation_manager.py`) |
| 캐시·에러 메트릭 / Cache & error metrics | 모니터링 모듈 (`monitoring/cache_metrics.py`, `monitoring/error_metrics.py`) |
| 배포 전 검증 / Pre-deploy validation | 환경·설정·시크릿 일괄 점검 (`deployment_validation.py`) |
| 컨테이너·핫 리로드 / Container with hot reload | Docker Compose, `make dev` 로 즉시 개발 환경 |

---

## Architecture · 아키텍처

### 레이어 / Layers

| 레이어 / Layer | 모듈 / Module | 책임 / Responsibility |
| --- | --- | --- |
| 진입점 / Entry | `app/run_app.py`, `app/entrypoint.sh` | 부트스트랩, 마이그레이션, 기동 |
| 앱 팩토리 / App factory | `core/app.py` | Flask 앱 생성, 블루프린트 등록 |
| 설정 / Config | `core/config.py` | 환경 변수 → 설정 객체 |
| 인증 / Auth | `core/auth/` | JWT, 데코레이터, 미들웨어 |
| 라우팅 / Routing | `core/routes/` | Web, API, WebSocket, Proxy, System |
| 도메인 / Domain | `core/routes/api/collection|blacklist|fortinet` | 수집·블랙리스트·배포 도메인 로직 |
| 모니터링 / Monitoring | `core/monitoring/` | 메트릭, 캐시, 에러 |
| UI / UI | `app/templates/` | Jinja2 페이지 |
| 유틸 / Utils | `app/utils/` | 로깅, 로그 회전 |

### 요청 흐름 / Request Flow

1. 클라이언트가 `web_routes.py` 또는 `api_routes.py` 로 요청
2. `auth/middleware.py` 가 JWT 검증 (선택)
3. 블루프린트가 `collection|sync|fortinet|blacklist` 하위 모듈로 위임
4. 도메인 로직이 외부 소스 호출 또는 DB I/O 수행
5. `monitoring/metrics.py` 가 지표 갱신, `structured_logging.py` 가 로그 기록
6. 응답 반환, 필요 시 WebSocket 으로 후속 이벤트 푸시

### 외부 의존성 / External Dependencies

| 의존 / Dependency | 용도 / Use |
| --- | --- |
| Flask + Jinja2 | 웹 콘솔, REST API |
| WebSocket | 실시간 채널 |
| JWT 라이브러리 | 인증 토큰 |
| 외부 위협 인텔 피드 | 수집 대상 (피드별 어댑터) |
| Fortinet REST API | 주소 객체 배포 대상 |
| Docker / Compose | 런타임, 배포 |

---

## First Files to Read · 먼저 읽을 파일

운영자가 가장 먼저 봐야 할 파일들입니다.

| 우선순위 / Priority | 파일 / File | 이유 / Why |
| --- | --- | --- |
| 1 | `app/run_app.py` | 로컬 진입점, 부트스트랩 순서 확인 |
| 2 | `app/core/app.py` | 앱 팩토리, 블루프린트 등록 순서 |
| 3 | `app/core/config.py` | 환경 변수 키 목록 파악 |
| 4 | `app/core/routes/api_routes.py` | REST API 표면 |
| 5 | `app/core/routes/api/fortinet/core.py` | Fortinet 배포 동작 |
| 6 | `app/core/routes/api/blacklist/core.py` | 블랙리스트 도메인 로직 |
| 7 | `app/deployment_validation.py` | 배포 전 검증 항목 |
| 8 | `Makefile` | 사용 가능한 운영 명령어 |

---

## API & Entry Points · API 와 진입점

### HTTP 진입점 / HTTP Endpoints

| 메서드 / Method | 경로 / Path | 모듈 / Module | 용도 / Purpose |
| --- | --- | --- | --- |
| GET | `/` | `web_routes.py` | 메인 콘솔 |
| GET | `/collection` | `web_routes.py` | 피드 수집 페이지 |
| GET | `/sessions` | `web_routes.py` | 세션 관리 |
| GET | `/settings` | `web_routes.py` | 환경 설정 |
| GET | `/integrations` | `web_routes.py` | 외부 통합 |
| GET | `/monitoring/dashboard` | `web_routes.py` | 운영 대시보드 |
| * | `/api/v1/*` | `api_routes.py` + 하위 블루프린트 | REST API |
| * | `/ws/*` | `websocket_routes.py` | 실시간 채널 |
| * | `/proxy/*` | `proxy_routes.py` | 외부 프록시 |
| GET | `/healthz`, `/readyz` | `system_routes.py` | 헬스체크 |

### 핵심 REST 모듈 / Key REST Modules

| 모듈 / Module | 책임 / Responsibility |
| --- | --- |
| `api/auth_routes.py` | 로그인·토큰 발급·갱신 |
| `api/dashboard_api.py` | 대시보드 집계 조회 |
| `api/database_api.py` | DB 메타 조회 |
| `api/system_api.py` | 시스템 정보·헬스 |
| `api/settings_api.py` | 설정 조회·갱신 |
| `api/migration.py` | 스키마 마이그레이션 트리거 |
| `api/analytics.py` | 분석 데이터 |
| `api/error_metrics_api.py` | 에러 지표 조회 |
| `api/ip_management_helpers.py` | IP 주소 헬퍼 |
| `api/fortinet_register.py` | Fortinet 디바이스 등록 |
| `api/collection/config.py` | 수집 설정 |
| `api/collection/credentials.py` | 피드 자격증명 |
| `api/collection/history.py` | 변경 이력 |
| `api/collection/sources.py` | 소스 정의 |
| `api/collection/status.py` | 수집 상태 |
| `api/collection/sync.py` | 동기화 트리거 |
| `api/collection/trigger.py` | 수동 트리거 |
| `api/blacklist/batch.py` | 일괄 처리 |
| `api/blacklist/collection.py` | 컬렉션 단위 작업 |
| `api/blacklist/core.py` | CRUD 코어 |
| `api/blacklist/management.py` | 운영 액션 |
| `api/blacklist/system.py` | 시스템 단위 액션 |

### 프로세스 진입점 / Process Entries

| 진입점 / Entry | 시나리오 / Scenario |
| --- | --- |
| `python app/run_app.py` | 로컬 개발 실행 |
| `bash app/entrypoint.sh` | 컨테이너 부팅, 마이그레이션 후 gunicorn 기동 |
| `python app/deployment_validation.py` | 배포 전 환경 점검 |

---

## Quickstart · 빠른 시작

### 사전 준비 / Prerequisites

| 항목 / Item | 버전 / Version |
| --- | --- |
| Python | `3.11+` |
| Docker + Compose | latest stable |
| GNU Make | any |
| `deploy/.env` | 필수 (Compose 자동 주입) |

### 로컬에서 5분 안에 실행 / Run locally in 5 minutes

1. 저장소 클론 후 의존성 설치

   ```bash
   git clone <repository-url> blacklist-service
   cd blacklist-service
   pip install -r app/requirements.txt
   ```

2. 환경 변수 준비

   ```bash
   cp deploy/.env.example deploy/.env   # (해당 파일이 있을 경우)
   ```

3. 앱 실행

   ```bash
   python app/run_app.py
   # → 기본 포트 2542 에서 콘솔 가동
   ```

4. 브라우저에서 `http://localhost:2542` 접속

### Docker Compose 로 실행 / Run with Docker Compose

```bash
make dev                 # 빌드 후 기동 (핫 리로드)
make dev-no-build        # 기존 이미지 재사용
make dev-prod            # 운영 모드 (핫 리로드 없음)
```

---

## Configuration · 설정

### 환경 변수 / Environment Variables

| 키 / Key | 기본값 / Default | 설명 / Description |
| --- | --- | --- |
| `ENV` | `development` | 실행 환경 토글 |
| `PORT` | `2542` | HTTP 리슨 포트 |
| `LOG_LEVEL` | `INFO` | 로그 레벨 |
| `LOG_FORMAT` | `json` | `json` 또는 `text` |
| `JWT_SECRET` | _required_ | JWT 서명 키 (운영 필수) |
| `FORTINET_*` | _optional_ | Fortinet 디바이스 자격증명·엔드포인트 |
| `FEED_*` | _optional_ | 외부 피드 자격증명·엔드포인트 |
| `DATABASE_URL` | _optional_ | DB 연결 문자열 |

> 정확한 키 목록과 누락 시 동작은 `app/core/config.py` 에서 직접 확인하세요.

### Compose 환경 / Compose Env

`deploy/.env` 가 자동으로 주입됩니다. 운영 환경에서는 시크릿을 별도 시크릿 매니저로 주입하는 것을 권장합니다.

---

## Commands Reference · 명령어

`make help` 로 사용 가능한 전체 타겟을 확인할 수 있습니다.

| 타겟 / Target | 용도 / Purpose |
| --- | --- |
| `help` | 사용 가능한 Make 타겟 출력 |
| `setup-hooks` | pre-commit + husky 설치 |
| `dev` | 개발 환경 기동 (빌드 + 핫 리로드) |
| `dev-no-build` | 기존 이미지로 기동 |
| `dev-prod` | 운영 모드 (핫 리로드 없음) |
| `dev-app` | 앱 서비스만 재시작 |
| `build` | 컨테이너 이미지 빌드 |
| `up` | Compose 기동 |
| `down` | Compose 종료 |
| `logs` | 컨테이너 로그 스트림 |
| `restart` | 서비스 재시작 |
| `health` | 헬스체크 |
| `clean` | 정리 |
| `test` | 테스트 실행 |
| `deploy` | 배포 절차 |
| `prod` | 운영 빌드/기동 |
| `release` | 릴리스 절차 |
| `release-dry` | 릴리스 드라이런 |
| `verify` | 배포 전 검증 |
| `verify-lint` | Ruff 린트 |
| `verify-types` | mypy 타입 검사 |
| `verify-secrets` | 시크릿 점검 |
| `verify-pre-commit` | pre-commit 훅 실행 |
| `verify-quick` | 빠른 검증 집합 |
| `verify-all` | 모든 검증 일괄 실행 |

---

## Local Development · 로컬 개발

| 작업 / Task | 명령어 / Command |
| --- | --- |
| 개발 환경 기동 | `make dev` |
| 앱만 재시작 | `make dev-app` |
| 로그 실시간 확인 | `make logs` |
| 헬스체크 | `make health` |
| 컨테이너 종료 | `make down` |
| 깨끗이 정리 | `make clean` |

권장 워크플로:

1. `make setup-hooks` 로 pre-commit + husky 설치
2. 코드 수정 → `make verify-quick` 으로 빠른 검증
3. 새 의존성은 `app/requirements.txt` 에 추가 후 `make build`
4. PR 전 `make verify-all` 로 린트·타입·시크릿·테스트 일괄 확인

---

## Testing · 테스트

`pyproject.toml` 의 pytest 설정 기준:

| 마커 / Marker | 의미 / Meaning |
| --- | --- |
| `unit` | 외부 의존성 없는 단위 테스트 |
| `integration` | 외부 서비스가 필요한 통합 테스트 |
| `security` | 보안 관련 테스트 |
| `db` | 데이터베이스 테스트 |
| `api` | API 엔드포인트 테스트 |

| 작업 / Task | 명령어 / Command |
| --- | --- |
| 전체 테스트 | `make test` |
| 마커 지정 실행 | `pytest -m unit` |
| 빠른 출력 | `pytest -v --tb=short` (기본 `addopts`) |

테스트 루트는 `pyproject.toml` 의 `testpaths = ["tests"]` 를 따릅니다.

---

## Operations · 운영

### 로깅 / Logging

- `app/utils/structured_logging.py` 가 JSON 구조화 로그 출력
- `app/utils/log_rotation_manager.py` 가 사이즈·시간 기반 로그 회전 정책 관리
- 운영 시 `LOG_LEVEL` 과 회전 임계치 모니터링 권장

### 모니터링 / Monitoring

| 모듈 / Module | 지표 / Metric |
| --- | --- |
| `monitoring/metrics.py` | 일반 처리량·응답 시간 |
| `monitoring/cache_metrics.py` | 캐시 적중률·크기 |
| `monitoring/error_metrics.py` | 오류율·오류 분류 |
| `api/error_metrics_api.py` | 지표 조회 엔드포인트 |
| `api/monitoring/metrics.py` | 모니터링 라우트 모음 |
| `system_routes.py` | 헬스·레디니스 |

### 배포 전 검증 / Pre-deploy Validation

```bash
make verify           # 통합 검증
make verify-lint      # Ruff
make verify-types     # mypy
make verify-secrets   # 시크릿 점검
make verify-all       # 전체 검증
```

검증 로직은 `app/deployment_validation.py` 에서 정의됩니다.

---

## Contributing · 기여

1. 이슈 생성 → 변경 범위 합의
2. 브랜치 생성 (`feat/`, `fix/`, `chore/`, `docs/` 등 컨벤션 준수)
3. 코드 수정 → `make verify-quick`
4. 커밋 메시지는 Conventional Commit (`commitlint.config.js`)
5. PR 생성 → 라벨·리뷰 자동화 흐름 따르기
6. `CONTRIBUTING.md` 의 세부 가이드 확인

기여 전 `CODE_OF_CONDUCT` 가 있는 경우 함께 확인해 주세요.

---

## Maintainers · 관리자

| 역할 / Role | 담당 / Owner |
| --- | --- |
| 제품 오너 / Product owner | `OWNERS` 파일 참조 |
| 코드 오너 / Code owners | `OWNERS` 파일 참조 |
| 운영 책임 / Operations | `OWNERS` 파일 참조 |

> 정확한 담당자·연락처는 저장소 내 `OWNERS` 를 확인하세요.

운영 중 문제 발생 시:

1. `make health` 로 기본 상태 점검
2. `make logs` 로 컨테이너 로그 확인
3. 이슈 트래커에 환경·재현 단계·로그 첨부

---

## License · 라이선스

본 저장소는 `LICENSE` 파일에 명시된 라이선스를 따릅니다. 사용 전 라이선스 전문을 확인해 주세요.

---

## Further Documentation · 추가 문서

| 문서 / Document | 위치 / Location |
| --- | --- |
| 에이전트 작업 가이드 / Agent guide | `AGENTS.md`, `app/AGENTS.md`, `app/core/AGENTS.md`, 하위 디렉토리 |
| 변경 이력 / Changelog | `CHANGELOG.md` |
| 버전 / Version | `VERSION` |
| 린트·타입 설정 / Lint & types | `pyproject.toml` |
| 커밋 컨벤션 / Commit convention | `commitlint.config.js` |
| mypy 설정 / mypy config | `mypy.ini` |
| 의존성 / Dependencies | `app/requirements.txt` |
| 운영 명령 / Operations | `Makefile` |