# Blacklist Service · 블랙리스트 관리 서비스

> 네트워크/IP 블랙리스트 수집·동기화·운영을 위한 Python 3.11 기반 웹 서비스. Fortinet 연동, 실시간 모니터링, JWT 인증을 제공합니다.
> A Python 3.11 web service for collecting, synchronizing, and operating network/IP blacklists with Fortinet integration, real-time monitoring, and JWT authentication.

| 항목 / Item | 값 / Value |
| --- | --- |
| 런타임 / Runtime | Python 3.11 |
| 웹 프레임워크 / Web framework | Flask (Jinja2 templates) |
| 기본 포트 / Default port | `2542` (override via `PORT`) |
| 컨테이너 / Container | Docker Compose (`deploy/docker-compose.yml`) |
| 테스트 / Tests | pytest + markers (unit / integration / security / db / api) |
| 린트·타입 / Lint & types | ruff, mypy |
| 인증 / Auth | JWT + 세션 미들웨어 |
| 실시간 채널 / Realtime | WebSocket 라우트 |
| 상태 / Status | Active — production-ready |
| 라이선스 / License | `LICENSE` 참조 / see `LICENSE` |

---

## 빠른 흐름 / Quick flow

1. `make setup-hooks` — pre-commit · commitlint · husky 훅 설치.
2. `make dev` — Docker Compose로 앱 컨테이너 기동 (hot reload, `PORT=2542`).
3. 브라우저에서 `http://localhost:2542` 접속 → 로그인 → 대시보드.
4. 컬렉션 소스 등록 → 자동/수동 동기화 → Fortinet 디바이스 반영.
5. `/monitoring/dashboard`에서 캐시·에러·처리량 지표 확인.

> Hot reload via volume mounts; rebuild only changed services with `make dev` or single-service restart with `make dev-app`.

---

## 패키지 구성 / Package Contents

| 경로 / Path | 역할 / Role |
| --- | --- |
| `app/run_app.py` | 엔트리포인트 스크립트 / entrypoint script |
| `app/entrypoint.sh` | 컨테이너 부트스트랩 / container bootstrap |
| `app/Dockerfile` | 서비스 이미지 정의 / service image definition |
| `app/requirements.txt` | Python 의존성 / Python dependencies |
| `app/deployment_validation.py` | 기동 전 환경 검증 / pre-flight env validation |
| `app/utils/log_rotation_manager.py` | 로그 로테이션 / log rotation |
| `app/utils/structured_logging.py` | 구조화 로거 / structured logger |
| `app/templates/` | Jinja2 페이지 (index, collection, sessions, settings, integrations 등) |
| `app/templates/monitoring/dashboard.html` | 모니터링 대시보드 / monitoring dashboard |
| `app/core/app.py` | Flask 앱 팩토리 / Flask app factory |
| `app/core/config.py` | 설정 로더 / configuration loader |
| `app/core/auth_manager.py` | 인증 관리자 / auth manager |
| `app/core/dashboard.py` | 대시보드 핸들러 / dashboard handler |
| `app/core/testing_app.py` | 테스트 앱 팩토리 / test app factory |
| `app/core/auth/` | JWT 서비스, 데코레이터, 미들웨어 / JWT, decorators, middleware |
| `app/core/monitoring/` | metrics, cache metrics, error metrics |
| `app/core/routes/` | web, api, websocket, proxy, system, collection 라우트 |
| `app/core/routes/api/` | REST API 모듈 (analytics, settings, database, system 등) |
| `app/core/routes/api/collection/` | 컬렉션 소스·자격·히스토리·동기화·트리거 |
| `app/core/routes/api/blacklist/` | 블랙리스트 코어·배치·관리·시스템 |
| `app/core/routes/api/fortinet/` | Fortinet 코어·등록 |
| `app/core/routes/api/monitoring/` | 메트릭 수집 / metrics ingest |

---

## 첫 번째로 읽을 파일 / First Files to Read

| 순서 / Order | 파일 / File | 이유 / Why |
| --- | --- | --- |
| 1 | [`app/run_app.py`](app/run_app.py) | 부트스트랩 진입점 / bootstrap entrypoint |
| 2 | [`app/core/app.py`](app/core/app.py) | Flask 팩토리, 블루프린트 등록 / Flask factory & blueprint wiring |
| 3 | [`app/core/config.py`](app/core/config.py) | 환경 변수와 설정 키 / env vars & config keys |
| 4 | [`app/core/routes/web_routes.py`](app/core/routes/web_routes.py) | 페이지 라우팅 / page routing |
| 5 | [`app/core/routes/api/core_api.py`](app/core/routes/api/core_api.py) | REST API 진입점 / REST entry |
| 6 | [`app/AGENTS.md`](app/AGENTS.md) | 모듈별 컨벤션 / module conventions |
| 7 | [`Makefile`](Makefile) | 운영 명령 / operator commands |
| 8 | [`pyproject.toml`](pyproject.toml) | 테스트·린트 설정 / test & lint config |

---

## API 및 진입점 / API & Entry Points

| 영역 / Area | 모듈 / Module | 비고 / Notes |
| --- | --- | --- |
| App factory | `app.core.app:create_app` | 테스트 팩토리는 `app.core.testing_app` |
| Auth | `app.core.auth_manager`, `app.core.auth.jwt_service` | JWT 발급·검증, 데코레이터, 미들웨어 |
| Web pages | `app.core.routes.web_routes` | `index`, `collection`, `sessions`, `settings`, `integrations` |
| WebSocket | `app.core.routes.websocket_routes` | 실시간 채널 / realtime channel |
| Proxy | `app.core.routes.proxy_routes` | 업스트림 프록시 / upstream proxy |
| System | `app.core.routes.system_routes` | 헬스·메타 / health & meta |
| Collection API | `app.core.routes.api.collection.*` | sources, sync, trigger, history, credentials, status, config |
| Blacklist API | `app.core.routes.api.blacklist.*` | core, batch, management, system |
| Fortinet API | `app.core.routes.api.fortinet.*` | core, register |
| Monitoring API | `app.core.routes.api.monitoring.metrics` | 메트릭 수집 / metrics ingest |
| Settings API | `app.core.routes.api.settings_api` | 설정 CRUD |
| Database API | `app.core.routes.api.database_api` | DB 운영 / DB ops |
| Error metrics | `app.core.routes.api.error_metrics_api` | 오류 카운터 / error counters |

### 인증 / Authentication

JWT 기반. 보호 라우트는 `app/core/auth/decorators.py`의 데코레이터 사용. 세션·쿠키 미들웨어는 `app/core/auth/middleware.py`.

### WebSocket

`/ws` 엔드포인트 — 실시간 로그·메트릭 스트림. 클라이언트는 페이지에서 자동 연결.

---

## 빠른 시작 / Quickstart

### 1) 훅 설치 / Install hooks

```bash
make setup-hooks
```

### 2) 개발 환경 기동 / Start development

```bash
make dev
# 컨테이너 기동 후 http://localhost:2542 접속
```

빠른 재기동(리빌드 없음):

```bash
make dev-no-build
```

프로덕션 유사(볼륨 마운트 없음):

```bash
make dev-prod
```

앱만 재시작:

```bash
make dev-app
```

### 3) 로그·상태 / Logs & status

```bash
make logs      # docker compose logs -f
make health    # 헬스 체크
```

### 4) 종료 / Stop & clean

```bash
make down
make clean
```

---

## 설정 / Configuration

환경 변수는 `deploy/.env`에 둡니다(컨테이너가 `--env-file deploy/.env`로 로드). 주요 키:

| 키 / Key | 기본값 / Default | 설명 / Description |
| --- | --- | --- |
| `PORT` | `2542` | HTTP 리슨 포트 / HTTP listen port |
| `ENV` | `development` | `development` / `production` |
| `SECRET_KEY` | _(required)_ | Flask·JWT 서명 키 / Flask & JWT signing key |
| `DATABASE_URL` | _(required)_ | DB 연결 문자열 / DB connection string |
| `JWT_TTL` | _(provider)_ | 토큰 만료(초) / token TTL seconds |
| `LOG_LEVEL` | `INFO` | 로그 레벨 / log level |

`app/core/config.py`가 모든 키의 단일 출처입니다. 컨테이너 기동 전 `app/deployment_validation.py`가 필수 키를 검사합니다.

---

## 명령어 참조 / Commands Reference

| 명령 / Command | 용도 / Purpose |
| --- | --- |
| `make help` | 전체 타깃 목록 / list all targets |
| `make setup-hooks` | pre-commit·commitlint·husky 설치 |
| `make dev` | 개발 환경 빌드 후 기동 |
| `make dev-no-build` | 기존 이미지로 기동 |
| `make dev-prod` | 핫리로드 없는 프로덕션 유사 기동 |
| `make dev-app` | 앱 서비스만 재시작 |
| `make up` / `make down` | 스택 기동 / 종료 |
| `make logs` | 로그 스트림 |
| `make restart` | 스택 재기동 |
| `make health` | 헬스 체크 |
| `make test` | pytest 실행 |
| `make build` | 이미지 빌드 |
| `make verify` | 빠른 검증 (lint·types·secrets) |
| `make verify-lint` | ruff 검사 |
| `make verify-types` | mypy 검사 |
| `make verify-secrets` | 시크릿 누출 검사 |
| `make verify-pre-commit` | pre-commit 전체 |
| `make verify-quick` | 빠른 통합 검증 |
| `make verify-all` | 전체 검증 |
| `make release-dry` | 릴리스 드라이런 |
| `make release` | 릴리스 실행 |
| `make clean` | 로컬 산출물 정리 |

---

## 로컬 개발 / Local Development

- Python 3.11 + 가상환경 권장.
- 컨테이너 외부에서 실행 시 `PYTHONPATH=app` 설정.
- 코드 변경은 `make dev`의 볼륨 마운트로 즉시 반영(템플릿·라우트·정적).
- 구조화 로거는 `app/utils/structured_logging.py`, 로테이션은 `log_rotation_manager.py`.
- `app/AGENTS.md`의 모듈별 규칙을 우선 적용.

### 디렉토리 규약 / Directory conventions

| 영역 / Area | 위치 / Location | 규약 / Convention |
| --- | --- | --- |
| 페이지 템플릿 / Page templates | `app/templates/` | 1기능 1템플릿, `base` 상속 |
| API 블루프린트 / API blueprints | `app/core/routes/api/` | 도메인별 서브패키지 |
| 메트릭 / Metrics | `app/core/monitoring/` | 카운터·게이지 분리 |
| 인증 / Auth | `app/core/auth/` | 미들웨어 → 데코레이터 → 서비스 순 의존 |

---

## 테스트 / Testing

```bash
make test
# 또는
pytest -m unit
pytest -m integration
pytest -m security
pytest -m db
pytest -m api
```

`pyproject.toml`의 마커:

| 마커 / Marker | 의미 / Meaning |
| --- | --- |
| `unit` | 외부 의존성 없음 / no external deps |
| `integration` | 실행 중인 서비스 필요 / requires services |
| `security` | 보안 시나리오 / security scenarios |
| `db` | DB 시나리오 / DB scenarios |
| `api` | API 엔드포인트 / API endpoints |

테스트 앱 팩토리는 `app/core/testing_app.py`를 사용하세요.

---

## 기여 가이드 / Contribution Guide

- 커밋 규약: Conventional Commits (`commitlint.config.js`).
- 린트: `make verify-lint` (ruff) — `pyproject.toml`의 무시 규칙 준수.
- 타입: `make verify-types` (mypy).
- 시크릿: `make verify-secrets`로 사전 점검.
- PR 전: `make verify-quick` 통과 후 `make verify-all`.
- 자세한 절차는 [`CONTRIBUTING.md`](CONTRIBUTING.md) 참조.

---

## 유지보수자 / Maintainers

- [`OWNERS`](OWNERS) 파일의 책임자 목록을 따릅니다.
- 운영·릴리스 절차는 [`Makefile`](Makefile)과 [`CONTRIBUTING.md`](CONTRIBUTING.md) 참조.
- 변경 이력은 [`CHANGELOG.md`](CHANGELOG.md), 버전은 [`VERSION`](VERSION).

---

## 추가 문서 / Further Documentation

| 문서 / Document | 위치 / Location |
| --- | --- |
| 모듈별 컨벤션 / Module conventions | [`app/AGENTS.md`](app/AGENTS.md), [`app/core/AGENTS.md`](app/core/AGENTS.md) |
| 인증 모듈 / Auth module | [`app/core/auth/AGENTS.md`](app/core/auth/AGENTS.md) |
| 모니터링 모듈 / Monitoring module | [`app/core/monitoring/AGENTS.md`](app/core/monitoring/AGENTS.md) |
| 라우트 모듈 / Routes module | [`app/core/routes/AGENTS.md`](app/core/routes/AGENTS.md) |
| API 모듈 / API module | [`app/core/routes/api/AGENTS.md`](app/core/routes/api/AGENTS.md) |
| 컬렉션 모듈 / Collection module | [`app/core/routes/api/collection/AGENTS.md`](app/core/routes/api/collection/AGENTS.md) |
| 블랙리스트 모듈 / Blacklist module | [`app/core/routes/api/blacklist/AGENTS.md`](app/core/routes/api/blacklist/AGENTS.md) |
| Fortinet 모듈 / Fortinet module | [`app/core/routes/api/fortinet/AGENTS.md`](app/core/routes/api/fortinet/AGENTS.md) |
| 변경 이력 / Changelog | [`CHANGELOG.md`](CHANGELOG.md) |
| 기여 절차 / Contribution | [`CONTRIBUTING.md`](CONTRIBUTING.md) |
| 라이선스 / License | [`LICENSE`](LICENSE) |

### 도움말 / Getting help

- 이슈 트래커: GitHub Issues (저장소 기본 채널).
- 보안 이슈: 공개 이슈 대신 `OWNERS`에 기재된 책임자에게 비공개 연락.
- 내부 운영 질문: `CONTRIBUTING.md`의 연락 경로 참조.

---

© Project contributors. Released under the terms of [`LICENSE`](LICENSE).