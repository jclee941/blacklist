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

1. **수집 (Collection)** — 외부 위협 인텔 소스에서 IP / Domain / URL 항목을 주기적·수동으로 가져옵니다. (`app/core/routes/api/collection/`)
2. **정규화 (Normalization)** — `app/core/routes/api/blacklist/core.py` 가 엔트리를 형식·중복 검사 후 중앙 블랙리스트에 머지합니다.
3. **관리 (Management)** — `app/core/routes/api/blacklist/management.py` 와 `batch.py` 가 일괄 추가·삭제·TTL 만료를 처리합니다.
4. **배포 (Deployment)** — `app/core/routes/api/fortinet/core.py` 가 Fortinet 장비로 주소 객체를 푸시합니다.
5. **관측 (Observability)** — `app/core/monitoring/` 의 메트릭·에러 카운터와 `dashboard.html` 이 상태를 시각화하고 WebSocket 으로 알립니다.
6. **인증 (Auth)** — `app/core/auth/` 의 JWT/데코레이터/미들웨어가 모든 라우트의 인가를 통제합니다.

English summary: collect from intel sources → normalize and merge into the central blacklist → batch-manage with TTL → push to Fortinet → observe via metrics/dashboard → enforce auth across the stack.

---

## Package Contents · 구성 요소

| 영역 / Area | 경로 / Path | 역할 / Role |
| --- | --- | --- |
| App bootstrap | `app/run_app.py`, `app/entrypoint.sh`, `app/Dockerfile` | 로컬/컨테이너 실행 진입점 |
| Pre-deploy checks | `app/deployment_validation.py` | 배포 전 환경·시크릿 검증 |
| Core | `app/core/app.py`, `app/core/config.py`, `app/core/dashboard.py`, `app/core/testing_app.py` | 앱 팩토리·설정·대시보드 집계 |
| Auth | `app/core/auth/` | JWT 발급·검증, `@require_*` 데코레이터, 요청 미들웨어 |
| Monitoring | `app/core/monitoring/` | 캐시·에러·시스템 메트릭 수집기 |
| Web routes | `app/core/routes/web_routes.py` | Jinja2 페이지 라우팅 |
| API routes | `app/core/routes/api_routes.py`, `app/core/routes/api/` | REST API 블루프린트 등록 |
| Collection API | `app/core/routes/api/collection/` | 소스 등록·자격증명·동기화·트리거·이력 |
| Blacklist API | `app/core/routes/api/blacklist/` | 머지·배치·관리·시스템 상태 |
| Fortinet API | `app/core/routes/api/fortinet/core.py` | 장비 등록·주소 객체 배포 |
| Proxy / WS | `app/core/routes/proxy_routes.py`, `app/core/routes/websocket_routes.py`, `app/core/routes/system_routes.py` | 프록시, 실시간 채널, 시스템 엔드포인트 |
| Templates | `app/templates/`, `app/templates/monitoring/dashboard.html` | 로그인·메인·수집·통합·세션·설정·대시보드 UI |
| Utils | `app/utils/structured_logging.py`, `app/utils/log_rotation_manager.py` | JSON 로깅·로그 회전 |

---

## First Files to Read · 먼저 읽을 파일

1. `app/run_app.py` — 로컬 실행·앱 팩토리 진입점.
2. `app/core/config.py` — 환경 변수, 기본 포트, ENV 모드 정의.
3. `app/core/app.py` — 블루프린트 등록 순서, 미들웨어 체인.
4. `app/core/auth/decorators.py` — 라우트 보호 패턴과 권한 매트릭스.
5. `app/core/routes/api/collection/sync.py` — 위협 인텔 동기화 핵심 로직.
6. `app/core/routes/api/blacklist/core.py` — 머지·정규화 정책.
7. `app/core/routes/api/fortinet/core.py` — Fortinet 푸시 프로토콜.
8. `app/deployment_validation.py` — 배포 직전 점검 시나리오.
9. `Makefile` — 일상 운영 명령 모음.
10. `AGENTS.md` (루트) — 코드베이스 운영 규약.

---

## API & Entry Points · 엔드포인트

### Web 콘솔 (Jinja2)

| Path | Template | 설명 / Description |
| --- | --- | --- |
| `/` | `app/templates/index.html` | 로그인 후 메인 대시보드 |
| `/collection` | `collection.html` | 수집 작업·소스 상태 |
| `/collection/logs` | `collection_logs.html` | 수집 로그 스트림 |
| `/integrations` | `integrations.html` | Fortinet 등 외부 시스템 연결 |
| `/sessions` | `sessions.html` | 활성 세션/토큰 관리 |
| `/settings` | `settings.html` | 환경·계정·TTL 설정 |
| `/monitoring/dashboard` | `monitoring/dashboard.html` | 메트릭·에러 시각화 |

### REST API (blueprint: `app/core/routes/api/`)

| Prefix | 모듈 / Module | 역할 / Role |
| --- | --- | --- |
| `/api/auth` | `auth_routes.py` | 로그인·토큰 갱신·로그아웃 |
| `/api/analytics` | `analytics.py` | 집계·리포트 |
| `/api/dashboard` | `dashboard_api.py` | 대시보드 요약 카드 |
| `/api/database` | `database_api.py` | DB 상태·마이그레이션 트리거 |
| `/api/migration` | `migration.py` | 스키마 마이그레이션 |
| `/api/settings` | `settings_api.py` | 런타임 설정 조회/변경 |
| `/api/system` | `system_api.py` | 헬스·정보·모드 |
| `/api/core` | `core_api.py` | 핵심 기능 게이트웨이 |
| `/api/error-metrics` | `error_metrics_api.py` | 에러 카운터 노출 |
| `/api/fortinet` | `fortinet_register.py` | Fortinet 장비 등록·해제 |
| `/api/ip-management` | `ip_management_helpers.py` | IP 보조 유틸리티 |
| `/api/monitoring/metrics` | `monitoring/metrics.py` | 메트릭 노출 (Prometheus 친화) |
| `/api/collection/*` | `collection/*.py` | 소스·자격증명·동기화·트리거·이력·상태 |
| `/api/blacklist/*` | `blacklist/*.py` | 머지·배치·관리·시스템 |

### Realtime

| Endpoint | Module | 비고 |
| --- | --- | --- |
| WebSocket `/ws/*` | `app/core/routes/websocket_routes.py` | 수집 진행·배포 결과 푸시 |

---

## Quickstart · 빠른 시작

### 1. 사전 요구 / Prerequisites

- Python 3.11+
- Docker / Docker Compose (컨테이너 실행 시)
- `deploy/.env` (Compose 가 자동 로드)

### 2. 로컬 직접 실행 / Local (no container)

```bash
git clone <repo-url> blacklist-service
cd blacklist-service

python -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt

cp deploy/.env.example deploy/.env   # 필요 시 시크릿 채우기
export PORT=2542
export ENV=development

python app/run_app.py
# → http://localhost:2542
```

### 3. 컨테이너 실행 / Docker Compose

```bash
make setup-hooks     # 1회: pre-commit + husky
make dev             # 빌드 + 핫리로드 개발 환경
make dev-no-build    # 기존 이미지로 빠르게 기동
make dev-prod        # 운영 모드에 가까운 빌드
make logs            # tail 로그
make health          # 헬스 체크
```

### 4. 배포 직전 검증 / Pre-deploy verification

```bash
make verify          # 전체 검증
make verify-lint     # Ruff
make verify-types    # mypy
make verify-secrets  # 시크릿 누출 점검
make verify-pre-commit
make verify-quick
make verify-all
```

### 5. 릴리스 / Release

```bash
make release-dry     # 시뮬레이션 (CHANGELOG, VERSION 확인)
make release         # VERSION bump + 커밋 + 태그
```

---

## Configuration · 환경 설정

`.env` 의 주요 키 (실제 키 목록은 `app/core/config.py` 가 SSoT):

| Key | 기본값 / Default | 설명 / Description |
| --- | --- | --- |
| `ENV` | `development` | `development` / `production` |
| `PORT` | `2542` | 웹 리스너 포트 |
| `DATABASE_URL` | (env) | 중앙 블랙리스트 저장소 |
| `JWT_SECRET` | (required in prod) | `app/core/auth/jwt_service.py` |
| `FORTINET_BASE_URL` | (env) | Fortinet API 엔드포인트 |
| `FORTINET_API_TOKEN` | (required) | Fortinet 인증 토큰 |
| `LOG_LEVEL` | `INFO` | 구조화 로깅 레벨 |
| `LOG_ROTATE_MAX_BYTES` | `10485760` | 로그 회전 임계치 |
| `LOG_ROTATE_BACKUPS` | `10` | 보관 세대 수 |

> 운영 환경에서는 `deployment_validation.py` 가 누락 시크릿과 ENV 불일치를 부트스트랩 전에 차단합니다.

---

## Commands Reference · Make 명령

| Target | 목적 / Purpose |
| --- | --- |
| `make help` | 사용 가능한 타깃과 설명 출력 |
| `make setup-hooks` | pre-commit + husky + commit-msg 훅 설치 |
| `make dev` | 개발 환경 up (빌드 + 핫리로드) |
| `make dev-no-build` | 기존 이미지로 빠르게 기동 |
| `make dev-prod` | 운영 모드 빌드 (오버라이드 없음) |
| `make dev-app` | app 서비스만 재시작 (빠른 반복) |
| `make build` | 이미지 빌드 |
| `make up` / `make down` | Compose 기동/중지 |
| `make logs` | 로그 tail |
| `make restart` | 재기동 |
| `make health` | 헬스 체크 |
| `make clean` | 로컬 산출물 정리 |
| `make test` | pytest (unit / integration / security / db / api 마커) |
| `make deploy` | 배포 시퀀스 |
| `make verify` / `verify-lint` / `verify-types` / `verify-secrets` / `verify-pre-commit` / `verify-quick` / `verify-all` | 검증 묶음 |
| `make release` / `make release-dry` | 릴리스 (VERSION + CHANGELOG + 태그) |

---

## Local Development · 로컬 개발

- **린트**: `ruff check app/` (라인 길이 120, `py311`).
- **타입**: `mypy` (`mypy.ini`).
- **테스트**: `pytest` (`app/tests` 기준, 마커: `unit` / `integration` / `security` / `db` / `api`).
- **커밋**: Conventional Commits, `commitlint.config.js` 로 enforce.
- **Pre-commit**: Python lint/타입/시크릿 스캔; 프런트엔드는 `frontend/` 의 husky 가 ESLint·Prettier.
- **핫리로드**: `make dev` 는 볼륨 마운트 + 앱 자동 재시작을 활성화합니다.

---

## Architecture · 아키텍처

### Layered Overview

| Layer | 책임 / Responsibility | 핵심 모듈 |
| --- | --- | --- |
| Edge | HTTP/WS 수신, 인증/인가, 속도제한 | `app/core/auth/middleware.py`, `app/core/routes/web_routes.py` |
| Web UI | Jinja2 페이지 렌더링 | `app/templates/`, `monitoring/dashboard.html` |
| API | REST 엔드포인트, 요청 검증 | `app/core/routes/api_routes.py`, `api/*` |
| Domain | 수집·블랙리스트·Fortinet 도메인 로직 | `api/collection/`, `api/blacklist/`, `api/fortinet/` |
| Infra | DB, 외부 HTTP, 메트릭 | `core/monitoring/`, `app/utils/`, `core/config.py` |
| Ops | 배포·검증·로그 회전 | `deployment_validation.py`, `utils/log_rotation_manager.py` |

### Request Flow · 대표 흐름

1. 클라이언트가 `POST /api/collection/{id}/sync` 호출.
2. `web_routes` → `middleware` 가 JWT 검증 (`auth/decorators.py`).
3. `collection/sync.py` 가 소스 자격증명을 `collection/credentials.py` 에서 로드.
4. 외부 피드를 가져와 정규화 → `blacklist/core.py` 머지.
5. 결과 이벤트를 `monitoring/metrics.py` 에 기록, `websocket_routes.py` 가 구독자에게 푸시.
6. `fortinet/core.py` 가 변경분을 Fortinet 으로 배포 → 결과를 `/api/fortinet` 이력에 저장.
7. `dashboard_api.py` 가 `/monitoring/dashboard` 에 요약 반영.

---

## Testing · 테스트

```bash
# 전체
pytest

# 마커별
pytest -m unit
pytest -m integration     # 외부 서비스 필요
pytest -m security
pytest -m db
pytest -m api
```

`pyproject.toml` 의 `addopts = "-v --tb=short"` 가 적용됩니다. 새 테스트는 `app/tests/` 하위에 `test_*.py` 명명 규칙을 따르세요.

---

## Production Readiness · 운영 준비도

| 영역 / Area | 상태 / Status |
| --- | --- |
| 인증 / Auth | JWT + 데코레이터/미들웨어 적용 |
| 로깅 / Logging | JSON 구조화 + 회전 |
| 메트릭 / Metrics | 캐시·에러·시스템 카운터 노출 |
| 배포 / Deploy | Compose 기반, 검증 스크립트 제공 |
| 문서 / Docs | 본 README + `CHANGELOG.md` + `AGENTS.md` |
| 운영 단계 / Stage | 사내 PoC → 단계적 확대 (Production-ready: 검증 중) |

---

## Maintainers · 책임자

- `OWNERS` 파일이 코드 오너십과 리뷰어의 SSoT 입니다.
- 운영/릴리스 의사결정은 `OWNERS` 의 primary / secondary 그룹이 수행합니다.
- 외부 기여 절차는 `CONTRIBUTING.md` 를 따릅니다.

---

## Further Documentation · 추가 문서

| 문서 / Doc | 경로 / Path | 내용 / Contents |
| --- | --- | --- |
| 변경 이력 / Changelog | `CHANGELOG.md` | 릴리스 노트, 마이그레이션 안내 |
| 기여 가이드 / Contributing | `CONTRIBUTING.md` | PR 절차, 코딩 규약, 리뷰 SLA |
| 코드베이스 규약 / Codebase rules | `AGENTS.md` (루트) | 에이전트/리뷰어 운용 규칙 |
| 앱 모듈 규약 / App rules | `app/AGENTS.md` | `app/` 하위 규약 |
| 코어 규약 / Core rules | `app/core/AGENTS.md` | 코어 레이어 규약 |
| 라이선스 / License | `LICENSE` | 라이선스 전문 |
| 버전 / Version | `VERSION` | 현재 시맨틱 버전 |
| 헬스체크 | `GET /api/system/health` (라우터: `system_api.py`) | liveness/readiness |

---

## Help · 도움말

- 버그 리포트·기능 요청: 저장소 이슈 트래커를 사용하세요.
- 보안 이슈: `OWNERS` 의 책임자에게 비공개로 연락합니다.
- 내부 채팅: 운영팀 채널에서 `blacklist-service` 로 검색.
- 상세 운영 절차: `CHANGELOG.md` 의 마이그레이션 항목과 `app/AGENTS.md` 의 런북을 따릅니다.