# Blacklist Service

외부 위협 인텔리전스 소스에서 IP 블랙리스트를 수집·정규화·저장하고 Fortinet 방화벽으로 동기화하며, JWT 인증, 웹 대시보드, Prometheus 형식 메트릭을 함께 제공하는 Python 웹 서비스입니다.

Web service that ingests threat-intel feeds, normalizes and stores IP blacklists, syncs them to Fortinet firewalls, and ships with JWT auth, a web dashboard, and Prometheus-style metrics.

| 항목 | 값 |
| --- | --- |
| 상태 | 프로덕션 가능 (Production-ready) |
| 런타임 | Python 3.11+ |
| 컨테이너 | Docker / Docker Compose |
| 기본 포트 | 2542 (HTTP) |
| 인증 | JWT + 데코레이터/미들웨어 |
| 외부 통합 | Fortinet 방화벽 어댑터 |
| 관측성 | 메트릭, 대시보드, 구조화 로그 |
| 테스트 | pytest (unit / integration / security / db / api) |
| 린트 / 타입 | Ruff, mypy |
| 라이선스 | 저장소 `LICENSE` 참조 |

## 동작 흐름 (Flow)

1. 운영자가 웹 UI 또는 `/api/...` 엔드포인트로 소스와 자격증명을 등록합니다.
2. `collection` 워커가 외부 위협 인텔리전스 피드에서 IP 항목을 가져옵니다.
3. `blacklist` 모듈이 정규화·중복 제거 후 저장하고 변경 이력을 남깁니다.
4. `fortinet` 어댑터가 변경분을 Fortinet 방화벽 주소 객체로 동기화합니다.
5. `monitoring` 모듈이 메트릭과 헬스체크를 노출하고, 알림 채널이 이를 구독합니다.

## 목차 (Table of Contents)

- [개요 / Overview](#개요--overview)
- [주요 기능 / Features](#주요-기능--features)
- [아키텍처 / Architecture](#아키텍처--architecture)
- [빠른 시작 / Quickstart](#빠른-시작--quickstart)
- [설정 / Configuration](#설정--configuration)
- [명령어 / Commands](#명령어--commands)
- [API 진입점 / API Endpoints](#api-진입점--api-endpoints)
- [로컬 개발 / Local Development](#로컬-개발--local-development)
- [테스트 / Testing](#테스트--testing)
- [운영 관측성 / Operations](#운영-관측성--operations)
- [기여 / Contributing](#기여--contributing)
- [유지보수 / Maintainers](#유지보수--maintainers)
- [더 보기 / Further Documentation](#더-보기--further-documentation)
- [라이선스 / License](#라이선스--license)

## 개요 / Overview

Blacklist Service는 보안 운영팀이 여러 위협 인텔리전스 피드를 한 곳으로 모아 검증하고 Fortinet 같은 네트워크 장비에 일관되게 배포할 수 있도록 돕는 백엔드입니다. 수집 → 정규화 → 배포 → 관측의 전 과정을 단일 컨테이너 묶음으로 제공합니다.

For security operations teams: ingest threat-intel feeds, deduplicate, persist, and push the curated IP set to Fortinet firewalls. A single container ships the full collect → normalize → distribute → observe loop.

## 주요 기능 / Features

- 소스 수집: HTTP/파일/자격증명 기반 피드를 스케줄·수동 트리거로 수집
- 블랙리스트 관리: 배치 임포트/익스포트, 중복 제거, 변경 이력 추적
- Fortinet 동기화: 객체 단위 추가·삭제, 상태 추적, 재시도
- 인증/권한: JWT 발급·갱신, 데코레이터·미들웨어로 라우트 보호
- 대시보드/모니터링: 웹 대시보드, Prometheus 형식 메트릭, 캐시·에러 카운터
- 구조화 로깅, 로그 로테이션, 배포 전 자동 검증 스크립트
- WebSocket 채널로 실시간 상태 푸시

## 아키텍처 / Architecture

| 영역 | 위치 | 책임 |
| --- | --- | --- |
| 부트스트랩 | `app/run_app.py`, `app/entrypoint.sh` | 앱 팩토리 실행, 컨테이너 부트 |
| 코어 | `app/core/app.py`, `app/core/config.py` | 앱 인스턴스, 환경 설정 |
| 인증 | `app/core/auth/` | JWT 서비스, 데코레이터, 미들웨어 |
| 웹 라우트 | `app/core/routes/web_routes.py` | 대시보드·세션·설정 화면 |
| API 라우트 | `app/core/routes/api_routes.py`, `app/core/routes/api/` | REST API |
| 블랙리스트 | `app/core/routes/api/blacklist/` | 임포트, 배치, 관리, 시스템 |
| 컬렉션 | `app/core/routes/api/collection/` | 소스, 자격증명, 히스토리, 트리거 |
| Fortinet | `app/core/routes/api/fortinet/` | 방화벽 어댑터, 등록 |
| 모니터링 | `app/core/monitoring/`, `app/core/routes/api/monitoring/` | 메트릭, 캐시, 에러 |
| 프록시/시스템 | `app/core/routes/proxy_routes.py`, `app/core/routes/system_routes.py` | 프록시·시스템 라우트 |
| WebSocket | `app/core/routes/websocket_routes.py` | 실시간 채널 |
| 템플릿 | `app/templates/` | HTML 화면 (대시보드, 통합, 세션, 설정) |
| 유틸 | `app/utils/structured_logging.py`, `app/utils/log_rotation_manager.py` | 로그 |
| 배포 검증 | `app/deployment_validation.py` | 부트 시 환경·연결 검증 |

요청 흐름 (단순화):

1. 클라이언트 요청이 `web_routes` 또는 `api_routes` 로 들어옵니다.
2. 인증 미들웨어가 JWT 를 검증하고 컨텍스트를 주입합니다.
3. 도메인 라우트(blacklist/collection/fortinet)가 서비스 로직을 호출합니다.
4. 결과는 JSON(API) 또는 Jinja 템플릿(웹)으로 직렬화됩니다.
5. 모니터링 모듈이 호출 횟수·지연·에러를 메트릭으로 누적합니다.

## 빠른 시작 / Quickstart

선행 조건: Docker, Docker Compose, Make. 호스트에서 포트 2542 가 비어 있어야 합니다.

| 단계 | 명령 | 비고 |
| --- | --- | --- |
| 1 | 저장소 클론 | - |
| 2 | `cp deploy/.env.example deploy/.env` | 환경 변수 템플릿 (없다면 동등한 키 생성) |
| 3 | `make dev` | 빌드 + 핫 리로드로 기동 |
| 4 | 브라우저에서 `http://localhost:<PORT>` 접속 | 기본 2542 |
| 5 | `ADMIN_USERNAME` / `ADMIN_PASSWORD` 로 로그인 | 부트스트랩 계정 |

운영 환경은 `make dev-prod` (핫 리로드 없음, 프로덕션 유사 이미지) 또는 `make deploy` 로 기동합니다. 헬스체크는 `make health` 입니다.

## 설정 / Configuration

환경 변수는 `deploy/.env` 에 둡니다. `app/deployment_validation.py` 가 부트 시 필수 키와 연결을 검증합니다.

| 키 | 설명 |
| --- | --- |
| `PORT` | HTTP 리스닝 포트 (기본 2542) |
| `ENV` | `development` / `production` |
| `JWT_SECRET` | JWT 서명 키 (필수) |
| `JWT_EXPIRES` | 토큰 만료 시간 |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | 초기 부트스트랩 계정 |
| `FORTINET_*` | Fortinet 호스트/포트/토큰 등 |
| `DB_*` | 데이터베이스 접속 정보 |
| `LOG_LEVEL` | 구조화 로그 레벨 |
| `LOG_DIR` | 로그 로테이션 디렉터리 |

## 명령어 / Commands

| 명령어 | 용도 |
| --- | --- |
| `make help` | 사용 가능한 타겟 목록 출력 |
| `make setup-hooks` | pre-commit·commitlint 훅 설치 |
| `make dev` | 개발 환경(빌드 + 핫 리로드) 기동 |
| `make dev-no-build` | 기존 이미지로 빠르게 기동 |
| `make dev-prod` | 핫 리로드 없는 프로덕션 유사 기동 |
| `make down` | 컨테이너 종료 |
| `make logs` | 로그 스트림 |
| `make restart` | 서비스 재기동 |
| `make health` | 헬스체크 |
| `make test` | 테스트 실행 |
| `make verify` | 린트·타입·시크릿 일괄 검증 |
| `make verify-lint` | Ruff |
| `make verify-types` | mypy |
| `make verify-secrets` | 시크릿 스캔 |
| `make release` | 릴리스 |
| `make release-dry` | 릴리스 드라이런 |

## API 진입점 / API Endpoints

| 경로 | 모듈 | 설명 |
| --- | --- | --- |
| `/api/auth/...` | `app/core/routes/api/auth_routes.py` | 로그인, 토큰 갱신 |
| `/api/blacklist/...` | `app/core/routes/api/blacklist/` | 블랙리스트 CRUD·배치 |
| `/api/collection/...` | `app/core/routes/api/collection/` | 소스, 자격증명, 히스토리, 트리거 |
| `/api/fortinet/...` | `app/core/routes/api/fortinet/core.py`, `fortinet_register.py` | Fortinet 등록·동기화 |
| `/api/monitoring/...` | `app/core/routes/api/monitoring/metrics.py` | 메트릭·헬스 |
| `/api/system/...` | `app/core/routes/api/system_api.py` | 시스템 정보 |
| `/api/database/...` | `app/core/routes/api/database_api.py` | DB 상태 |
| `/api/dashboard/...` | `app/core/routes/api/dashboard_api.py` | 대시보드 집계 |
| `/api/analytics/...` | `app/core/routes/api/analytics.py` | 분석 |
| `/api/settings/...` | `app/core/routes/api/settings_api.py` | 설정 |
| `/api/errors/...` | `app/core/routes/api/error_metrics_api.py` | 에러 카운터 |
| `/api/migration` | `app/core/routes/api/migration.py` | 스키마 마이그레이션 트리거 |
| `/api/ip/...` | `app/core/routes/api/ip_management_helpers.py` | IP 관리 보조 |
| `/ws/...` | `app/core/routes/websocket_routes.py` | 실시간 채널 |
| `/` | `app/core/routes/web_routes.py` | HTML 대시보드·세션·설정 화면 |

## 로컬 개발 / Local Development

- 코드 위치: `app/core/`
- 부트스트랩: `app/run_app.py`
- 컨테이너 진입점: `app/entrypoint.sh`
- 도커 이미지: `app/Dockerfile`
- 의존성: `app/requirements.txt`
- 정적 타입/린트: `mypy.ini`, `pyproject.toml` (Ruff)
- 로깅 유틸: `app/utils/structured_logging.py`, `app/utils/log_rotation_manager.py`

권장 워크플로:

1. `make setup-hooks` 로 커밋 훅을 설치합니다.
2. `make dev` 로 컨테이너를 띄우고 `app/core/...` 하위 코드를 수정합니다.
3. 볼륨 마운트로 자동 리로드되므로 별도 재시작은 필요 없습니다.
4. `make verify` 로 린트·타입·시크릿을 검사합니다.
5. `make test` 로 회귀 테스트를 실행합니다.

처음 읽을 파일 (First Files to Read):

- `app/run_app.py` — 앱 진입점
- `app/core/app.py` — 앱 팩토리/라우트 등록
- `app/core/config.py` — 환경 변수 매핑
- `app/core/auth/jwt_service.py` — 인증 흐름의 핵심
- `Makefile` — 운영 명령어의 단일 출처

## 테스트 / Testing

- 프레임워크: pytest (`pyproject.toml` 의 `[tool.pytest.ini_options]`)
- 경로: `tests/`
- 마커: `unit`, `integration`, `security`, `db`, `api`
- 실행: `make test` 또는 `pytest`
- 사전 커밋 훅이 Ruff·mypy·시크릿 스캔을 강제합니다.

## 운영 관측성 / Operations

| 항목 | 위치 / 엔드포인트 |
| --- | --- |
| 메트릭 | `app/core/monitoring/metrics.py`, `cache_metrics.py`, `error_metrics.py` |
| 헬스 | `make health`, `/api/monitoring/...` |
| 대시보드 | `app/templates/monitoring/dashboard.html` |
| 구조화 로그 | `app/utils/structured_logging.py` |
| 로그 로테이션 | `app/utils/log_rotation_manager.py` |
| 배포 검증 | `app/deployment_validation.py` |

## 기여 / Contributing

- 커밋 규약: Conventional Commits (`commitlint.config.js` 참조)
- 절차: `CONTRIBUTING.md` 참조
- PR 크기·라벨 정책: 저장소 이슈 트래커 및 `OWNERS` 의 책임자 합의 필요

## 유지보수 / Maintainers

자세한 책임자 목록은 저장소 루트의 `OWNERS` 파일을 확인하세요. 보안 이슈는 비공개 채널, 일반 운영 요청은 저장소 이슈 트래커로 접수합니다.

## 더 보기 / Further Documentation

- 변경 이력: `CHANGELOG.md`
- 기여 가이드: `CONTRIBUTING.md`
- 저장소 규약 참고: `AGENTS.md`
- 릴리스 버전: `VERSION`

## 라이선스 / License

저장소 루트의 `LICENSE` 파일을 참조하세요.