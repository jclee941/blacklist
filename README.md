# Blacklist Service

[![Python](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![Ruff](https://img.shields.io/badge/lint-ruff-D7FF64?logo=ruff&logoColor=black)](pyproject.toml)
[![pytest](https://img.shields.io/badge/test-pytest-0A9EDC?logo=pytest&logoColor=white)](pyproject.toml)
[![Docker](https://img.shields.io/badge/deploy-docker--compose-2496ED?logo=docker&logoColor=white)](Makefile)
[![License](https://img.shields.io/badge/license-Apache_2.0-blue)](LICENSE)

**블랙리스트 관리 서비스** — 다중 소스에서 IP/도메인 블랙리스트를 수집하고, 로컬 블랙리스트
DB를 관리하며, Fortinet 방화벽 및 외부 시스템에 변경분을 동기화하는 Python 웹 애플리케이션.
JWT 기반 인증, 구조화 로깅, 캐시/에러 메트릭 모니터링을 제공합니다.

**Blacklist Service** — Python web application that ingests IP/domain blacklists from multiple
sources, maintains a local blacklist store, and synchronizes changes to Fortinet firewalls and
external systems. Includes JWT auth, structured logging, and cache/error metrics monitoring.

---

## 한눈에 보기 / At a glance

| 영역 / Area | 값 / Value | 출처 / Source |
| --- | --- | --- |
| 앱 진입점 / App entry | `app/run_app.py` → `app/core/app.py` | `app/` |
| 테스트 앱 / Testing app | `app/core/testing_app.py` | `app/core/` |
| 패키지 매니페스트 / Package manifest | `pyproject.toml` | root |
| 컨테이너 빌드 / Container build | `app/Dockerfile` (+ `app/entrypoint.sh`) | `app/` |
| 오케스트레이션 / Orchestration | `Makefile` → `docker compose` (`deploy/docker-compose.yml`) | root |
| 인증 방식 / Auth | JWT (cookie `access_token`) | `app/core/auth/jwt_service.py` |
| API 베이스 / API base | Flask Blueprints under `/api/*` | `app/core/routes/api/` |
| 웹 UI / Web UI | Jinja2 templates | `app/templates/` |

### 운영 흐름 / Operator flow

1. `make dev` → `docker compose up -d --build` → `http://localhost:2542` (앱) .
2. `/api/auth/login` 으로 JWT 발급 → 보호 라우트는 `@jwt_required` (`app/core/auth/decorators.py`) .
3. 소스 등록 → `/api/collection/sources` → 동기화 → `/api/collection/trigger` .
4. 블랙리스트 조회/편집 → `/api/blacklist/*` → Fortinet 등록 → `/api/fortinet/register` .
5. 모니터링 → `/monitoring/dashboard` + `/api/monitoring/*` (Prometheus-compatible 메트릭) .

---

## 목차 / Contents

- [목적 / Purpose](#목적--purpose)
- [패키지 구성 / Package Contents](#패키지-구성--package-contents)
- [상태 / Status](#상태--status)
- [먼저 읽을 파일 / First Files to Read](#먼저-읽을-파일--first-files-to-read)
- [API 및 진입점 / API & Entry Points](#api-및-진입점--api--entry-points)
- [빠른 시작 / Quickstart](#빠른-시작--quickstart)
- [명령어 / Commands](#명령어--commands)
- [구성 / Configuration](#구성--configuration)
- [로컬 개발 / Local Development](#로컬-개발--local-development)
- [테스트 / Testing](#테스트--testing)
- [기여 / Contributing](#기여--contributing)
- [유지보수 담당 / Maintainers](#유지보수-담당--maintainers)
- [추가 문서 / Further Documentation](#추가-문서--further-documentation)

---

## 목적 / Purpose

보안 운영자(SecOps)·네트워크 엔지니어·플랫폼 팀이 다음을 한 곳에서 처리하도록 돕습니다.

- 여러 외부 위협 인텔리전스 소스에서 블랙리스트 수집/동기화.
- 로컬 블랙리스트 DB 조회·검색·일괄 작업.
- Fortinet 장비로 변경분 푸시 및 등록 상태 확인.
- 세션, 통합, 설정, 모니터링을 위한 웹 콘솔 제공.

운영자는 CLI 가 아닌 웹 UI 와 JSON API 만으로 일상 작업을 마칠 수 있고, 모든 작업은
JWT 발급 이후의 보호 라우트에서 수행됩니다.

---

## 패키지 구성 / Package Contents

```
.
├── app/                     # 런타임 코드 / Runtime code
│   ├── core/                # 도메인 로직, 라우트, 미들웨어
│   │   ├── auth/            # JWT 발급·검증·데코레이터
│   │   ├── monitoring/      # 캐시·에러·요약 메트릭
│   │   └── routes/
│   │       ├── api/         # /api/* Blueprints
│   │       │   ├── auth_routes.py
│   │       │   ├── collection/   # 소스·자격·히스토리·상태·트리거
│   │       │   ├── blacklist/    # 배치·코어·관리·시스템
│   │       │   ├── fortinet/     # Fortinet 등록·코어
│   │       │   ├── monitoring/   # 메트릭
│   │       │   └── ...
│   │       ├── web_routes.py      # HTML 라우트
│   │       ├── websocket_routes.py
│   │       └── proxy_routes.py
│   ├── templates/           # Jinja2 (index, collection, sessions, ...)
│   ├── utils/               # log_rotation_manager, structured_logging
│   ├── deployment_validation.py
│   ├── entrypoint.sh
│   ├── run_app.py
│   └── Dockerfile
├── Makefile                 # dev / prod / verify / release 타깃
├── pyproject.toml           # Ruff + pytest 설정
├── commitlint.config.js     # 커밋 메시지 규약
├── mypy.ini                 # 타입 검사
├── AGENTS.md                # 에이전트/기여자 노트
├── CONTRIBUTING.md
├── CHANGELOG.md
├── LICENSE
├── OWNERS
└── VERSION
```

---

## 상태 / Status

| 항목 / Item | 상태 / Status | 비고 / Notes |
| --- | --- | --- |
| 런타임 안정성 / Production-ready | 운영 가능 — 공개 릴리즈 진행 중 | `CHANGELOG.md`, `VERSION` 추적 |
| Python 지원 버전 / Python | 3.11+ | `pyproject.toml` `target-version` |
| Lint | Ruff (`E`, `F`, `W`) | `pyproject.toml` |
| 타입 검사 / Types | mypy | `mypy.ini` |
| 테스트 / Tests | pytest (단위/통합/보안/DB/API 마커) | `pyproject.toml` |
| 컨테이너 / Container | Dockerfile + docker-compose | `Makefile` |
| 지원 종단 / End-of-life | 없음 | — |

---

## 먼저 읽을 파일 / First Files to Read

1. `app/run_app.py` — 앱 팩토리 부트스트랩.
2. `app/core/app.py` — Flask 앱 구성, Blueprint 등록, 미들웨어 와이어업.
3. `app/core/config.py` — 환경 변수 기반 설정 로딩.
4. `app/core/auth/jwt_service.py` + `decorators.py` — 인증·인가 흐름.
5. `app/core/routes/api/__init__.py` — API Blueprint 노출 순서.
6. `Makefile` 의 `help` 타깃으로 사용 가능한 명령 확인.

---

## API 및 진입점 / API & Entry Points

### 인증 / Auth

| 메서드 / Method | 경로 / Path | 설명 / Purpose |
| --- | --- | --- |
| POST | `/api/auth/login` | 자격 검증 → JWT 발급 (`auth_routes.py`) |
| POST | `/api/auth/logout` | 세션 종료 |
| GET | `/api/auth/me` | 현재 사용자 정보 |

### 컬렉션(소스) / Collection

| 메서드 / Method | 경로 / Path | 모듈 / Module |
| --- | --- | --- |
| GET / POST | `/api/collection/sources` | `collection/sources.py` |
| POST | `/api/collection/trigger` | `collection/trigger.py` |
| GET | `/api/collection/history` | `collection/history.py` |
| GET | `/api/collection/status` | `collection/status.py` |
| GET | `/api/collection/config` | `collection/config.py` |

### 블랙리스트 관리 / Blacklist management

| 영역 / Area | 모듈 / Module |
| --- | --- |
| 코어 CRUD / Core CRUD | `blacklist/core.py` |
| 일괄 작업 / Batch ops | `blacklist/batch.py` |
| 컬렉션 진입 / Collection dispatch | `blacklist/collection.py` |
| 정책/관리 UI 백엔드 / Management backend | `blacklist/management.py` |
| 시스템 수준 / System level | `blacklist/system.py` |

### Fortinet 통합

| 메서드 / Method | 경로 / Path | 모듈 / Module |
| --- | --- | --- |
| POST | `/api/fortinet/register` | `fortinet_register.py`, `fortinet/core.py` |

### 분석·대시보드·메트릭 / Analytics & Monitoring

| 영역 / Area | 경로 / Path |
| --- | --- |
| 분석 / Analytics | `/api/analytics` (`analytics.py`) |
| 대시보드 / Dashboard | `/api/dashboard`, `/monitoring/dashboard` |
| 에러 메트릭 / Error metrics | `/api/monitoring/error-metrics` |
| 캐시 메트릭 / Cache metrics | `monitoring/cache_metrics.py` |
| DB API / Database | `/api/database` |

### 웹 라우트 / Web routes

`GET /` → `index.html`, `GET /collection` → `collection.html`,
`GET /sessions` → `sessions.html`, `GET /settings` → `settings.html`,
`GET /integrations` → `integrations.html`, 로그/모니터링 등 추가 경로는 `web_routes.py`.

### 실시간 / Realtime

`websocket_routes.py` 가 클라이언트 푸시 채널을 제공합니다. 자세한 핸들러는
`app/core/routes/websocket_routes.py` 참조.

---

## 빠른 시작 / Quickstart

사전 요구 사항 / Prerequisites: Docker + Docker Compose, GNU Make, Python 3.11+ (로컬
개발 시).

```bash
# 1. 환경 변수 준비
cp deploy/.env.example deploy/.env   # 실제 경로가 없다면 deploy/.env 생성

# 2. 훅 설치 (선택이지만 권장)
make setup-hooks

# 3. 개발 스택 기동 (핫 리로드, 자동 재빌드)
make dev
# → http://localhost:2542

# 4. 상태 확인
make health
make logs
```

로컬에서 Python 직접 실행:

```bash
pip install -r app/requirements.txt
PYTHONPATH=app python app/run_app.py
```

---

## 명령어 / Commands

`make help` 가 전체 목록을 출력합니다. 주요 타깃:

| 타깃 / Target | 목적 / Purpose |
| --- | --- |
| `make dev` | 핫 리로드 개발 스택 기동 (`docker compose up -d --build`) |
| `make dev-no-build` | 이미지 재빌드 없이 기동 |
| `make dev-prod` | 프로덕션 유사 모드 (오버라이드 없음) |
| `make dev-app` | 앱 서비스만 재시작 |
| `make up` / `make down` | 스택 시작 / 종료 |
| `make logs` | 로그 스트림 |
| `make restart` | 서비스 재시작 |
| `make prod` | 프로덕션 빌드 |
| `make deploy` | 배포 절차 |
| `make health` | 헬스 체크 |
| `make test` | 테스트 실행 |
| `make clean` | 정리 |
| `make verify-lint` / `verify-types` / `verify-secrets` / `verify-pre-commit` / `verify-quick` / `verify-all` | CI 게이트 묶음 |
| `make release` / `release-dry` | 릴리즈 절차 |

---

## 구성 / Configuration

설정은 환경 변수를 통해 주입되며 `app/core/config.py` 에서 로드됩니다.

| 키 / Key | 용도 / Purpose |
| --- | --- |
| `PORT` | 앱 노출 포트 (기본 `2542`) |
| `FLASK_ENV` | `development` / `production` |
| `JWT_SECRET` | JWT 서명 키 (필수) |
| `DATABASE_URL` | 백엔드 저장소 |
| `COLLECTION_*` | 컬렉션 소스/자격/주기 |
| `FORTINET_*` | Fortinet 장비 엔드포인트/자격 |

> 보안 키와 자격 증명은 절대 커밋하지 마세요. `deploy/.env` 는 gitignore 대상입니다.

---

## 로컬 개발 / Local Development

- 코드 스타일: Ruff (라인 길이 120). 저장소 정책은 `pyproject.toml` 참조.
- 타입 검사: `mypy.ini`. 린트와 분리된 게이트.
- 커밋 규약: Conventional Commits (`commitlint.config.js`).
- 사전 커밋 훅: `make setup-hooks` 로 설치.
- 새 라우트 추가 시 `app/core/routes/api/` 하위 도메인 모듈에 배치하고, Blueprint 가
  `app/core/routes/api/__init__.py` 에서 노출되는지 확인.

---

## 테스트 / Testing

`pyproject.toml` 의 `[tool.pytest.ini_options]` 가 테스트 디렉터리와 마커를 정의합니다.

```bash
make test                  # 전체 실행
pytest -m unit             # 단위만
pytest -m integration      # 통합 (서비스 의존)
pytest -m security         # 보안 시나리오
pytest -m api              # API 엔드포인트
```

테스트는 `tests/` 하위(저장소 루트)에서 발견되며, 모듈 경로 해석을 위해 `pythonpath = ["app"]`
이 적용됩니다.

---

## 기여 / Contributing

기여 절차는 `CONTRIBUTING.md` 를 따릅니다. PR 전 권장 사항:

1. `make verify-all` 통과.
2. 커밋 메시지 형식 준수.
3. 변경 모듈이 위치하는 도메인 폴더(`auth`, `monitoring`, `collection`, `blacklist`,
   `fortinet`)에 새 `AGENTS.md` 규칙이 있다면 그 가이드 우선 적용.

---

## 유지보수 담당 / Maintainers

`OWNERS` 파일의 책임자가 코드 리뷰 및 릴리즈 권한을 가집니다. 문의는
[Issues](../../issues) 또는 저장소 소유자에게 직접 연락하세요.

---

## 추가 문서 / Further Documentation

| 문서 / Document | 용도 / Purpose |
| --- | --- |
| `AGENTS.md` | 저장소·도메인별 에이전트 가이드 |
| `CONTRIBUTING.md` | 기여 절차, PR 규약 |
| `CHANGELOG.md` | 릴리즈 노트 |
| `VERSION` | 현재 시맨틱 버전 |
| `LICENSE` | 라이선스 전문 |
| `app/templates/` | 웹 UI 템플릿 (Jinja2) |
| `app/core/routes/api/*` | API 명세의 진실 공급원(SSOT) |