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
| 운영 단계 / Production-ready? | 운영 검증 단계 | 사내 PoC → 단계적 확대 |

---

## Compact Flow · 운영 흐름

1. 외부 위협 인텔 소스에서 IP·도메인·URL 항목 수집 — `app/core/routes/api/collection/sources.py`, `sync.py`
2. 항목 정규화·중복 제거 후 중앙 블랙리스트 스토어 적재 — `app/core/routes/api/blacklist/core.py`, `collection/collection.py`
3. 관리 콘솔에서 항목 검토·승인·수동 편집 — `app/templates/collection.html`, `collection_logs.html`
4. Fortinet 디바이스 등록·자격증명 검증 — `app/core/routes/api/fortinet_register.py`, `app/core/routes/api/fortinet/core.py`
5. 변경 사항을 디바이스로 자동 푸시, 결과를 WebSocket 으로 실시간 통지 — `app/core/routes/websocket_routes.py`, `proxy_routes.py`
6. 대시보드·모니터링 메트릭으로 운영 가시화 — `app/core/dashboard.py`, `app/core/monitoring/metrics.py`, `app/templates/monitoring/dashboard.html`
7. 구조화 JSON 로그와 사이즈·시간 기반 로그 회전으로 감사 추적 — `app/utils/structured_logging.py`, `log_rotation_manager.py`
8. 사전 배포 검증으로 환경 변수·시크릿·마이그레이션 무결성 확인 — `make verify`, `make verify-all`

---

## Purpose · 프로젝트 목적

- **운영자가 한 곳에서 위협 인텔을 통합 관리**: 여러 외부 피드(스피어 피싱 도메인, 악성 IP, C2 URL 등)를 자동으로 모아 정규화된 블랙리스트로 만듭니다.
- **외부 보안 장비로의 배포를 자동화**: Fortinet 디바이스에 주소 객체(address object) / 그룹으로 자동 배포해, 정책 차단까지의 지연을 줄입니다.
- **변경 이력과 운영 가시성 확보**: 모든 동기화·배포는 구조화 로그와 메트릭으로 기록되며, 대시보드와 WebSocket 으로 실시간 확인 가능합니다.
- **셀프호스트형 단일 진입점**: 웹 콘솔 + REST API + WebSocket 을 같은 프로세스에서 제공해, 사내 SIEM·SOAR 와 손쉽게 연동됩니다.

### What users can do

- 새 외부 위협 인텔 소스(스피어 피싱 도메인, C2 IP, 악성 URL 등)를 등록하고 동기화 주기·자격증명을 관리합니다.
- 중앙 블랙리스트를 항목 단위로 조회·추가·삭제·배치 처리하고, 변경 이력을 감사합니다.
- Fortinet 디바이스를 등록·검증한 뒤, 변경된 블랙리스트를 즉시 또는 예약 배포합니다.
- 세션·통합·설정 화면을 통해 인증, 외부 시스템 연동, 운영 파라미터를 조정합니다.
- 대시보드와 메트릭으로 동기화 성공률, 배포 지연, 오류 추이를 모니터링합니다.

---

## Features · 주요 기능

| 영역 | 기능 | 진입점 · 모듈 |
| --- | --- | --- |
| 수집 (Collection) | 외부 소스 등록·스케줄·트리거·동기화 | `app/core/routes/api/collection/{sources,trigger,sync,credentials,history,status,config,utils}.py` |
| 정규화 (Normalization) | IP·도메인·URL 파싱, 중복 제거, 메타데이터 부착 | `app/core/routes/api/collection/utils.py` |
| 블랙리스트 (Blacklist) | 항목 CRUD, 배치, 시스템 정책, 이력 | `app/core/routes/api/blacklist/{core,batch,management,system,collection}.py` |
| Fortinet 배포 | 디바이스 등록, 주소 객체 푸시, 결과 회신 | `app/core/routes/api/fortinet_register.py`, `app/core/routes/api/fortinet/core.py` |
| 인증·인가 (Auth) | JWT 발급·검증, 데코레이터·미들웨어 | `app/core/auth/{jwt_service.py,decorators.py,middleware.py}`, `routes/api/auth_routes.py` |
| 모니터링 (Monitoring) | 캐시·오류·일반 메트릭 | `app/core/monitoring/{metrics,cache_metrics,error_metrics}.py`, `routes/api/monitoring/metrics.py` |
| 대시보드 (Dashboard) | 운영 콘솔 페이지, 통계 카드 | `app/core/dashboard.py`, `app/templates/monitoring/dashboard.html` |
| 설정 (Settings) | 사용자·시스템·외부 연동 설정 | `app/core/routes/api/settings_api.py`, `app/templates/settings.html` |
| 운영 통합 (Sessions/Integrations) | 세션 관리, 외부 시스템 연동 | `app/templates/{sessions,integrations}.html` |
| API 게이트 (Routes) | REST·웹·WebSocket·프록시·시스템 라우터 | `app/core/routes/{api_routes,web_routes,websocket_routes,proxy_routes,system_routes,collection_routes_simple}.py` |
| 로깅 (Logging) | JSON 구조화 로그, 사이즈·시간 회전 | `app/utils/{structured_logging,log_rotation_manager}.py` |
| 배포 검증 (Pre-deploy) | 환경 변수·시크릿·마이그레이션 검증 | `app/deployment_validation.py`, `make verify` |

---

## Architecture · 아키텍처

단일 Python 프로세스가 웹 콘솔, REST API, WebSocket 을 함께 제공합니다. 데이터는 중앙 블랙리스트 스토어를 중심으로, **수집 → 정규화 → 배포** 의 단방향 파이프라인으로 흐릅니다.

### 요청 흐름 (Request flow)

1. 클라이언트(웹 브라우저, CLI, 사내 시스템)가 HTTP / WebSocket 으로 진입합니다.
2. 인증 미들웨어가 JWT 를 검증하고, 권한 데코레이터가 라우트별 접근을 제어합니다 — `app/core/auth/middleware.py`, `decorators.py`.
3. 라우터가 요청을 도메인별 모듈(수집·블랙리스트·Fortinet·모니터링·설정)로 분기합니다 — `app/core/routes/*`.
4. 도메인 서비스가 비즈니스 로직을 수행하고 결과를 반환합니다.
5. 모든 단계의 이벤트가 구조화 로그와 메트릭으로 기록됩니다 — `app/utils/structured_logging.py`, `app/core/monitoring/metrics.py`.
6. WebSocket 채널이 동기화·배포 상태를 클라이언트에 실시간 푸시합니다 — `app/core/routes/websocket_routes.py`.

### 모듈 책임 (Module responsibilities)

| 영역 | 디렉터리 | 책임 |
| --- | --- | --- |
| 앱 부트스트랩 | `app/run_app.py`, `app/entrypoint.sh`, `app/core/app.py` | 프로세스 시작, 미들웨어 등록, 라우터 마운트 |
| 설정·검증 | `app/core/config.py`, `app/deployment_validation.py` | 환경 변수 로딩, 배포 전 점검 |
| 인증 | `app/core/auth_manager.py`, `app/core/auth/*` | JWT 발급·검증, 보호 라우트 |
| 라우팅 | `app/core/routes/*` | 웹 / API / WebSocket / 프록시 / 시스템 라우터 |
| 도메인 API | `app/core/routes/api/*` | 수집·블랙리스트·Fortinet·모니터링 API |
| 대시보드 | `app/core/dashboard.py`, `app/templates/*` | 운영 콘솔, Jinja2 페이지 |
| 로깅·관측 | `app/utils/*`, `app/core/monitoring/*` | 구조화 로그, 로그 회전, 메트릭 |
| 컨테이너 | `app/Dockerfile`, `deploy/docker-compose.yml` | 빌드·오케스트레이션 |

---

## Package Contents · 디렉터리 구조

저장소 최상위 기준 실제 레이아웃입니다.

```text
.
├── AGENTS.md                  # 보조 가이드(루트 요약)
├── CHANGELOG.md               # 릴리스 변경 이력
├── CONTRIBUTING.md            # 기여 가이드
├── LICENSE                    # 라이선스
├── Makefile                   # 개발 / 배포 / 검증 명령
├── OWNERS                     # 책임자 · 리뷰어 명단
├── README.md                  # 본 문서
├── VERSION                    # 시맨틱 버전
├── commitlint.config.js       # Conventional Commits 규칙
├── mypy.ini                   # 정적 타입 검사 설정
├── pyproject.toml             # Ruff / pytest 설정, 패키지 메타데이터
└── app/
    ├── AGENTS.md
    ├── Dockerfile             # 컨테이너 빌드
    ├── __init__.py
    ├── deployment_validation.py  # 배포 전 환경·시크릿·마이그레이션 검증
    ├── entrypoint.sh          # 컨테이너 진입점
    ├── requirements.txt       # Python 의존성
    ├── run_app.py             # 로컬 개발 진입점
    ├── core/
    │   ├── AGENTS.md
    │   ├── __init__.py
    │   ├── app.py             # 앱 팩토리
    │   ├── auth_manager.py    # 인증 매니저
    │   ├── config.py          # 환경 설정 로더
    │   ├── dashboard.py       # 대시보드 로직
    │   ├── testing_app.py     # 테스트용 앱 팩토리
    │   ├── auth/              # JWT 서비스, 데코레이터, 미들웨어
    │   ├── monitoring/        # 캐시·오류·일반 메트릭
    │   └── routes/            # web / api / websocket / proxy / system 라우터
    │       └── api/
    │           ├── analytics.py, auth_routes.py, core_api.py, dashboard_api.py,
    │           │   database_api.py, error_metrics_api.py, fortinet_register.py,
    │           │   ip_management_helpers.py, migration.py, settings_api.py,
    │           │   system_api.py
    │           ├── collection/    # 수집 도메인 API
    │           ├── blacklist/     # 블랙리스트 도메인 API
    │           ├── fortinet/      # Fortinet 디바이스 API
    │           └── monitoring/    # 메트릭 조회 API
    ├── templates/             # Jinja2 HTML(index, collection, sessions, …)
    │   └── monitoring/dashboard.html
    └── utils/
        ├── log_rotation_manager.py   # 사이즈·시간 기반 로그 회전
        └── structured_logging.py     # JSON 구조화 로거
```

---

## First Files to Read · 먼저 읽을 파일

새 합류자가 코드를 파악할 때 권장하는 순서입니다.

1. `README.md` — 본 문서로 전체 그림을 파악합니다.
2. `app/run_app.py` — 로컬 실행 진입점, 의존성 부트스트랩 순서를 확인합니다.
3. `app/core/app.py` — 앱 팩토리, 미들웨어, 라우터 마운트 순서를 확인합니다.
4. `app/core/config.py` — 어떤 환경 변수가 무엇을 결정하는지 확인합니다.
5. `app/core/routes/api_routes.py`, `web_routes.py`, `websocket_routes.py` — 외부 표면(URL 계약)을 훑습니다.
6. `app/core/routes/api/collection/sources.py`, `app/core/routes/api/blacklist/core.py`, `app/core/routes/api/fortinet/core.py` — 핵심 도메인 로직을 읽습니다.
7. `app/utils/structured_logging.py`, `app/core/monitoring/metrics.py` — 관측 가능성(observability) 계약을 확인합니다.
8. `app/deployment_validation.py` — 배포 게이트가 무엇을 검사하는지 확인합니다.

---

## API & Entry Points · 진입점과 엔드포인트

### 운영 진입점 (Operator entry points)

| 진입점 | 설명 | 위치 |
| --- | --- | --- |
| 로컬 개발 서버 | `python app/run_app.py` | `app/run_app.py` |
| 컨테이너 부트 | `app/entrypoint.sh` → `app/run_app.py` | `app/Dockerfile` |
| 배포 검증 | `python app/deployment_validation.py` | `app/deployment_validation.py` |
| Compose 오케스트레이션 | `make up` / `make down` | `Makefile`, `deploy/docker-compose.yml` |

### HTTP / WebSocket 표면 (Surface)

라우터는 `app/core/routes/` 아래에 분리되어 있습니다.

| 라우터 | 용도 | 모듈 |
| --- | --- | --- |
| Web 콘솔 | Jinja2 페이지(인덱스, 대시보드, 설정, 세션, 연동, 수집 로그) | `web_routes.py` |
| REST API | 외부 시스템·콘솔 AJAX | `api_routes.py` |
| WebSocket | 동기화·배포 상태 실시간 푸시 | `websocket_routes.py` |
| 프록시 | 외부 디바이스(예: Fortinet) 로의 프록시·헬스체크 | `proxy_routes.py` |
| 시스템 | 헬스체크, 메트릭, 내부 진단 | `system_routes.py` |
| 수집 (단순 뷰) | 운영자 친화 수집 라우트 | `collection_routes_simple.py` |

### 도메인 API (Domain API)

| 도메인 | 하위 모듈 | 모듈 위치 |
| --- | --- | --- |
| 인증 | `auth_routes.py` | `app/core/routes/api/` |
| 코어/세션 | `core_api.py` | `app/core/routes/api/` |
| 대시보드 | `dashboard_api.py` | `app/core/routes/api/` |
| 데이터베이스 | `database_api.py` | `app/core/routes/api/` |
| 마이그레이션 | `migration.py` | `app/core/routes/api/` |
| 설정 | `settings_api.py` | `app/core/routes/api/` |
| 시스템 | `system_api.py` | `app/core/routes/api/` |
| 분석 | `analytics.py` | `app/core/routes/api/` |
| IP 관리 헬퍼 | `ip_management_helpers.py` | `app/core/routes/api/` |
| 오류 메트릭 | `error_metrics_api.py` | `app/core/routes/api/` |
| Fortinet 등록 | `fortinet_register.py` | `app/core/routes/api/` |
| 수집 | `config.py`, `credentials.py`, `history.py`, `sources.py`, `status.py`, `sync.py`, `trigger.py`, `utils.py` | `app/core/routes/api/collection/` |
| 블랙리스트 | `batch.py`, `collection.py`, `core.py`, `management.py`, `system.py` | `app/core/routes/api/blacklist/` |
| Fortinet | `core.py` | `app/core/routes/api/fortinet/` |
| 모니터링 | `metrics.py` | `app/core/routes/api/monitoring/` |

> 정확한 URL 경로는 각 라우터의 `router`/`Blueprint` 정의를 참고하세요. 본 문서는 정적 경로 목록을 하드코딩하지 않습니다.

---

## Quickstart · 빠른 시작

### 1. 사전 요구 사항 (Prerequisites)

- Python 3.11+
- Docker + Docker Compose(컨테이너 실행 시)
- `make`(래퍼 명령 사용 시)
- (선택) Node.js — `frontend/` 패키지 작업 시

### 2. 환경 변수 파일 준비 (Env file)

`deploy/.env` 를 작성해 Compose 에게 주입합니다. `app/deployment_validation.py` 가 배포 전 누락 변수를 검증합니다.

```bash
# 예시 파일이 있다면
cp deploy/.env.example deploy/.env
# 없다면 Configuration 섹션을 참고해 직접 작성
```

### 3. 로컬에서 직접 실행 (Local)

```bash
pip install -r app/requirements.txt
export $(grep -v '^#' deploy/.env | xargs)
python app/run_app.py
# 브라우저: http://localhost:2542
```

### 4. 컨테이너로 실행 (Docker Compose)

```bash
make dev          # 빌드 후 핫 리로드로 기동
# 또는
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build
```

자세한 명령은 [Commands Reference](#commands-reference--명령-참조) 와 `make help` 를 참고하세요.

---

## Configuration · 환경 설정

핵심 설정은 `app/core/config.py` 에서 환경 변수로 로드하며, Compose 는 `deploy/.env` 를 자동 주입합니다. `make verify` 가 배포 전 누락 변수를 차단합니다.

| 변수 그룹 | 설명 | 예시 |
| --- | --- | --- |
| `PORT` | 웹 서버 포트(기본 `2542`) | `2542` |
| `ENV` | 실행 환경(`development` / `production`) | `production` |
| `SECRET_*` | JWT·세션 시크릿(`deployment_validation.py` 가 검증) | 배포 환경에서 강한 값 |
| 데이터베이스 접속 | 중앙 블랙리스트 스토어 | `DB_*` |
| Fortinet 자격증명 | 디바이스별 토큰/키 | `FORTINET_*` |
| 외부 위협 인텔 | 소스별 API 키/엔드포인트 | `FEED_*` |

> 정확한 변수 이름은 `app/core/config.py` 와 `app/deployment_validation.py` 를 기준으로 확인하세요.

---

## Commands Reference · 명령 참조

`Makefile` 이 단일 진입점입니다. `make help` 로 전체 목록을 출력할 수 있습니다.

| 명령 | 용도 | 비고 |
| --- | --- | --- |
| `make help` | 사용 가능한 명령 출력 | 색상으로 정렬 |
| `make setup-hooks` | git 훅(pre-commit + commit-msg + husky) 설치 | 첫 클론 후 1회 |
| `make dev` | 개발 환경 기동(빌드 + 핫 리로드) | 기본 진입점 |
| `make dev-no-build` | 빌드 없이 기존 이미지로 기동 | 빠른 재기동 |
| `make dev-prod` | 프로덕션 유사 환경 기동(오버라이드 없음, 핫 리로드 없음) | 회귀 점검 |
| `make dev-app` | 앱 서비스만 재기동 | 코드 변경 반영 |
| `make up` | Compose 스택 기동 | |
| `make down` | Compose 스택 종료 | |
| `make restart` | 서비스 재기동 | |
| `make logs` | 로그 스트림 | |
| `make health` | 헬스체크 | |
| `make test` | 테스트 실행 | `pyproject.toml` 의 pytest 설정 사용 |
| `make clean` | 빌드 산출물·중간 캐시 정리 | |
| `make deploy` | 배포 | |
| `make prod` | 프로덕션 모드 기동 | |
| `make release` | 릴리스 절차 실행 | |
| `make release-dry` | 릴리스 드라이런 | |
| `make verify` | 배포 전 검증 | `deployment_validation.py` 호출 |
| `make verify-lint` | Ruff 린트 | |
| `make verify-types` | mypy 타입 검사 | |
| `make verify-secrets` | 시크릿 누락 검사 | |
| `make verify-pre-commit` | pre-commit 훅 전체 실행 | |
| `make verify-quick` | 빠른 검증 | |
| `make verify-all` | 모든 검증 일괄 실행 | |

> 일부 명령의 본문은 `Makefile` 에서 더 길게 정의될 수 있습니다. `make help` 와 소스를 함께 참고하세요.

---

## Local Development · 로컬 개발

1. **의존성 설치** — `pip install -r app/requirements.txt`, 추가 dev 의존성이 있다면 그 패키지 파일도 함께 설치합니다.
2. **훅 설치** — `make setup-hooks`. pre-commit 은 Ruff/mypy/시크릿 탐지, commit-msg 는 Conventional Commits, husky 는 프론트엔드(있다면) ESLint/Prettier 를 강제합니다.
3. **환경 변수 로딩** — `export $(grep -v '^#' deploy/.env | xargs)` 또는 direnv 사용.
4. **핫 리로드 개발** — `make dev` 는 볼륨 마운트로 코드 변경이 컨테이너에 즉시 반영됩니다. 컨테이너 외부에서 `app/run_app.py` 를 직접 실행해도 됩니다.
5. **로그 확인** — `make logs`, 또는 `app/utils/structured_logging.py` 가 출력하는 JSON 로그를 `jq` 로 파싱합니다.
6. **마이그레이션** — `app/core/routes/api/migration.py` 와 `make verify` 가 무결성을 확인합니다.

---

## Testing · 테스트

`pyproject.toml` 의 pytest 설정(`pythonpath = ["app"]`, `testpaths = ["tests"]`)을 따릅니다.

| 마커 | 의미 |
| --- | --- |
| `unit` | 외부 의존성 없는 단위 테스트 |
| `integration` | DB·외부 서비스가 필요한 통합 테스트 |
| `security` | 보안 관련 테스트(인증·인가·시크릿) |
| `db` | 데이터베이스 테스트 |
| `api` | API 엔드포인트 테스트 |

```bash
make test                          # 전체
pytest -m unit                     # 단위 테스트만
pytest -m "api or security"        # 복수 마커
pytest app/core/routes/api/blacklist   # 경로 지정
```

테스트 앱 팩토리는 `app/core/testing_app.py` 를 사용합니다.

---

## Contribution · 기여 가이드

- `CONTRIBUTING.md` 의 절차(브랜치 전략, PR 템플릿, 리뷰어)를 따릅니다.
- 커밋 메시지는 Conventional Commits(`commitlint.config.js`)를 따릅니다.
- 코드 스타일은 Ruff(`pyproject.toml`, line-length 120), 타입은 mypy(`mypy.ini`)를 통과해야 합니다.
- 책임자/리뷰어 명단은 `OWNERS` 파일을 참고합니다.
- 보안 이슈는 공개 PR/PR 코멘트가 아닌, 저장소 정책의 보안 연락처를 통해 신고합니다.

---

## Maintainers · 책임자 / 연락처

- 책임자·리뷰어 명단: [`OWNERS`](./OWNERS)
- 일반 문의: 저장소 이슈 트래커
- 보안 이슈: 저장소 정책의 보안 연락처

---

## Further Documentation · 추가 문서

| 문서 | 경로 | 용도 |
| --- | --- | --- |
| 변경 이력 | [`CHANGELOG.md`](./CHANGELOG.md) | 릴리스 노트 |
| 기여 가이드 | [`CONTRIBUTING.md`](./CONTRIBUTING.md) | PR/이슈 절차 |
| 커밋 규칙 | [`commitlint.config.js`](./commitlint.config.js) | Conventional Commits |
| 린트/타입 설정 | [`pyproject.toml`](./pyproject.toml), [`mypy.ini`](./mypy.ini) | Ruff / mypy 옵션 |
| 현재 버전 | [`VERSION`](./VERSION) | 시맨틱 버전 |
| 보조 가이드 | `app/AGENTS.md`, `app/core/AGENTS.md`, `app/core/auth/AGENTS.md`, `app/core/monitoring/AGENTS.md`, `app/core/routes/AGENTS.md`, `app/core/routes/api/AGENTS.md`, `app/core/routes/api/collection/AGENTS.md`, `app/core/routes/api/blacklist/AGENTS.md`, `app/core/routes/api/fortinet/AGENTS.md` | 모듈별 노트 |

---

## License · 라이선스

본 저장소의 라이선스 조건은 [`LICENSE`](./LICENSE) 파일을 따릅니다.