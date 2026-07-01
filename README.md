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

여러 외부 위협 인텔리전스 소스에서 IP·도메인·URL을 수집·정규화해 중앙 블랙리스트로 통합한 뒤, Fortinet 같은 외부 보안 장비로 자동 배포하는 Python 기반 통합 관리 플랫폼입니다. Jinja2 웹 콘솔, REST API, WebSocket 실시간 채널을 단일 진입점으로 제공합니다.

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
| 현재 단계 / Production-ready? | 운영 검증 단계 | 사내 PoC → 단계적 확대 |

---

## Compact Flow · 운영 흐름

1. 외부 위협 인텔 소스 → `app/core/routes/api/collection/sources.py` 가 자격증명과 함께 등록.
2. 수집 엔진 → `app/core/routes/api/collection/sync.py` 가 IP·도메인·URL을 정규화.
3. 이력 적재 → `app/core/routes/api/collection/history.py` 가 감사 가능한 형태로 보존.
4. 중앙 블랙리스트 → `app/core/routes/api/blacklist/` 가 일괄·관리·시스템 정책을 적용.
5. 외부 장비 배포 → `app/core/routes/api/fortinet/` 가 Fortinet 주소 객체 그룹을 푸시.
6. 운영 콘솔 → `app/templates/index.html` + `app/core/routes/web_routes.py` 와 `api/core_api.py`.
7. 실시간 채널 → `app/core/routes/websocket_routes.py` 가 변경 이벤트를 구독자에게 송신.
8. 가시화 → `app/templates/monitoring/dashboard.html` + `app/core/routes/api/dashboard_api.py`.

---

## Purpose · 패키지 구성

| 영역 | 경로 | 역할 · Role |
| --- | --- | --- |
| Entry points | `app/run_app.py`, `app/entrypoint.sh` | 로컬 실행 · 컨테이너 부팅 |
| App factory | `app/core/app.py`, `app/core/config.py` | Flask 앱 초기화 · 환경 설정 |
| Auth | `app/core/auth/` | JWT 발급·검증, 데코레이터, 미들웨어 |
| Monitoring | `app/core/monitoring/` | 캐시·에러·일반 메트릭 |
| Web routes | `app/core/routes/web_routes.py`, `app/core/routes/api_routes.py` | 콘솔 페이지 라우팅 |
| WebSocket | `app/core/routes/websocket_routes.py` | 실시간 변경 이벤트 |
| System routes | `app/core/routes/system_routes.py` | 헬스체크·시스템 API |
| Proxy routes | `app/core/routes/proxy_routes.py`, `app/core/routes/collection_routes_simple.py` | 경량 프록시·수집 |
| Collection API | `app/core/routes/api/collection/` | 소스·자격·설정·이력·상태·동기화·트리거·유틸 |
| Blacklist API | `app/core/routes/api/blacklist/` | 배치·코어·컬렉션·관리·시스템 |
| Fortinet API | `app/core/routes/api/fortinet/` | Fortinet 주소 객체 배포 코어 |
| Auth API | `app/core/routes/api/auth_routes.py` | 로그인·토큰 갱신·세션 |
| System API | `app/core/routes/api/system_api.py` | 시스템 메타·헬스 |
| Settings API | `app/core/routes/api/settings_api.py` | 런타임 설정 |
| Database API | `app/core/routes/api/database_api.py` | DB 메타·연결 진단 |
| Analytics API | `app/core/routes/api/analytics.py` | 분석 통계 |
| Dashboard API | `app/core/routes/api/dashboard_api.py` | 콘솔용 요약 데이터 |
| Error metrics API | `app/core/routes/api/error_metrics_api.py` | 오류 집계·추적 |
| Migration | `app/core/routes/api/migration.py` | 스키마 마이그레이션 |
| IP management helpers | `app/core/routes/api/ip_management_helpers.py` | IP 인용·정규화 헬퍼 |
| Logging | `app/utils/structured_logging.py`, `app/utils/log_rotation_manager.py` | JSON 로거 · 회전 정책 |
| Templates | `app/templates/` | Jinja2 HTML 페이지 |
| Deployment | `app/Dockerfile`, `app/deployment_validation.py`, `Makefile`, `deploy/` | 이미지 빌드·검증·Compose 오케스트레이션 |

---

## First Files to Read · 우선 읽을 파일

1. `app/run_app.py` — 로컬/컨테이너 공통 부트스트랩.
2. `app/core/app.py` + `app/core/config.py` — 앱 팩토리와 환경 변수 매핑.
3. `app/core/auth_manager.py`, `app/core/auth/jwt_service.py` — 인증 토큰 정책.
4. `app/core/routes/web_routes.py`, `app/templates/index.html` — 콘솔 진입점.
5. `app/core/routes/api/collection/sync.py` — 수집 파이프라인의 핵심.
6. `app/core/routes/api/blacklist/core.py` + `app/core/routes/api/blacklist/management.py` — 정책 코어.
7. `app/core/routes/api/fortinet/core.py` — 외부 장비 푸시 로직.
8. `app/utils/structured_logging.py` — 운영 로그 표준.
9. `app/deployment_validation.py` — 배포 전 점검.
10. `Makefile` — 운영 명령 요약.

---

## API & Entry Points · 진입점 요약

| 표면 | 경로 | 핸들러 | 용도 |
| --- | --- | --- | --- |
| Web UI | `/` | `web_routes.py` · `templates/index.html` | 메인 콘솔 |
| Web UI | `/collection`, `/collection/logs` | `templates/collection*.html` | 수집 작업 화면 |
| Web UI | `/integrations` | `templates/integrations.html` | Fortinet 등 외부 연동 |
| Web UI | `/sessions` | `templates/sessions.html` | 활성 세션 |
| Web UI | `/settings` | `templates/settings.html` | 환경 설정 |
| Web UI | `/monitoring/dashboard` | `templates/monitoring/dashboard.html` | 운영 대시보드 |
| REST API prefix | `/api/*` | `api_routes.py` · `api/*.py` | JSON API |
| Auth API | `/api/auth/*` | `api/auth_routes.py` | 로그인·토큰 갱신 |
| Collection API | `/api/collection/*` | `api/collection/*.py` | 소스·동기화·이력 |
| Blacklist API | `/api/blacklist/*` | `api/blacklist/*.py` | 정책·일괄 작업 |
| Fortinet API | `/api/fortinet/*` | `api/fortinet/core.py` | 장비 푸시 |
| Monitoring API | `/api/monitoring/*` · `/api/error-metrics/*` | `api/monitoring/metrics.py` · `api/error_metrics_api.py` | 메트릭·오류 |
| Dashboard API | `/api/dashboard/*` | `api/dashboard_api.py` | 콘솔 요약 |
| WebSocket | `/ws/*` | `websocket_routes.py` | 실시간 변경 이벤트 |
| Health | `/health` (예상) | `system_routes.py` · `system_api.py` | 헬스체크 |

> 실제 경로는 `app/core/routes/` 의 라우트 정의가 SSoT 입니다. 콘솔은 `/` 가 가장 단순한 시작점입니다.

---

## Quickstart · 사용법

### 로컬 개발 (Python 3.11+)

```bash
# 1. 의존성 설치 (가상환경 권장)
python -m venv .venv && source .venv/bin/activate
pip install -r app/requirements.txt
pip install pre-commit  # 후크 설치가 필요할 경우

# 2. 환경 변수 준비
cp deploy/.env.example deploy/.env   # 파일이 있다면
export PORT=2542 ENV=development

# 3. 부트스트랩
python app/run_app.py
# 콘솔 → http://localhost:2542/
```

### 컨테이너 개발 (Docker Compose)

```bash
make setup-hooks   # pre-commit + husky (최초 1회)
make dev           # 빌드 후 핫리로드로 기동
make dev-no-build  # 기존 이미지로 빠르게 기동
make dev-prod      # 운영 모드 (오버라이드 없음, 핫리로드 OFF)
```

### 배포 전 검증

```bash
make verify        # 린트 · 타입 · 시크릿 · pre-commit 빠르게
make verify-all    # 모든 검사 일괄
make release-dry   # 릴리스 드래프트 미리보기
```

### 자주 쓰는 명령

| 명령 | 동작 |
| --- | --- |
| `make help` | Makefile 의 모든 타깃과 설명 출력 |
| `make setup-hooks` | pre-commit, commit-msg, husky 설치 |
| `make dev` | Compose 로 개발 스택 기동 (빌드 포함) |
| `make dev-no-build` | 빌드 없이 기동 (빠른 재기동) |
| `make dev-prod` | 운영 모드 Compose 기동 |
| `make dev-app` | app 서비스만 재기동 |
| `make up` / `make down` | 스택 전체 up/down |
| `make logs` | 컨테이너 로그 스트림 |
| `make restart` | 재기동 |
| `make health` | 헬스 상태 점검 |
| `make test` | pytest 실행 |
| `make clean` | 캐시·임시 산출물 정리 |
| `make deploy` | 배포 시퀀스 |
| `make verify` | 린트·타입·시크릿·pre-commit 검증 |
| `make verify-lint` | Ruff 단독 |
| `make verify-types` | mypy 단독 |
| `make verify-secrets` | 시크릿 스캔 단독 |
| `make verify-pre-commit` | pre-commit 훅 단독 |
| `make verify-quick` | 빠른 게이트 |
| `make verify-all` | 전체 게이트 |
| `make release` / `make release-dry` | 릴리스 발행 / 드래프트 미리보기 |

---

## Configuration · 설정

| 키 | 용도 | 기본값 |
| --- | --- | --- |
| `PORT` | HTTP 포트 | `2542` |
| `ENV` | `development` / `production` | `development` |
| `SECRET_KEY` | 세션·JWT 서명 키 | (필수) |
| `DATABASE_URL` | SQLAlchemy 등 DB DSN | 환경별 상이 |
| `JWT_*` | 토큰 만료·알고리즘 | `app/core/auth/jwt_service.py` 참조 |
| `LOG_LEVEL` | 구조화 로그 레벨 | `INFO` |
| `LOG_ROTATION_*` | 회전 정책 | `app/utils/log_rotation_manager.py` |

설정 로딩은 `app/core/config.py` 가 SSoT 입니다. 환경별 차이는 `deploy/.env` 로 주입합니다.

---

## Architecture · 아키텍처 한눈표

| 계층 | 책임 | 주요 모듈 |
| --- | --- | --- |
| 부팅 | 컨테이너·로컬 공통 부트스트랩 | `app/entrypoint.sh` → `app/run_app.py` → `app/core/app.py` |
| 설정·인증 | 환경 로딩, JWT 발급·검증, 데코레이터·미들웨어 | `app/core/config.py`, `app/core/auth_manager.py`, `app/core/auth/*` |
| 수집 | 위협 인텔 소스 등록·자격관리·동기화·이력 | `app/core/routes/api/collection/*` |
| 정규화·저장 | 입력 항목 정규화, 중앙 블랙리스트 적재 | `app/core/routes/api/blacklist/*` |
| 배포 | Fortinet 주소 객체 그룹 푸시 | `app/core/routes/api/fortinet/core.py` |
| 운영 콘솔 | Jinja2 페이지 렌더링, 대시보드·로그·설정 | `app/core/routes/web_routes.py`, `app/templates/*` |
| 실시간 채널 | 변경 이벤트 구독·브로드캐스트 | `app/core/routes/websocket_routes.py` |
| 모니터링 | 메트릭·캐시·에러 가시화 | `app/core/monitoring/*`, `app/core/routes/api/monitoring/*`, `app/core/routes/api/error_metrics_api.py` |
| 외부 노출 | REST/HTTP 라우팅 | `app/core/routes/api_routes.py`, `app/core/routes/system_routes.py`, `app/core/routes/proxy_routes.py` |
| 로깅 | JSON 구조화 로그와 회전 | `app/utils/structured_logging.py`, `app/utils/log_rotation_manager.py` |
| 배포 | 이미지 빌드, 검증, Compose 오케스트레이션 | `app/Dockerfile`, `app/deployment_validation.py`, `Makefile`, `deploy/docker-compose.yml` |

### 요청 흐름 (콘솔 일반 작업)

1. 사용자 → `/` → `web_routes.py` → Jinja2 렌더링.
2. 콘솔에서 수집 트리거 → `/api/collection/*` → `api/collection/trigger.py`.
3. 수집 파이프라인이 동기화 잡 시작 → `api/collection/sync.py`.
4. 동기화 잡이 정규화된 항목을 블랙리스트에 병합 → `api/blacklist/core.py`.
5. Fortinet 푸시 잡이 변경분을 배포 → `api/fortinet/core.py`.
6. WebSocket 채널이 변경 이벤트를 구독자에게 전송 → `websocket_routes.py`.
7. 대시보드가 메트릭·로그·헬스를 새로고침 → `dashboard_api.py`, `monitoring/metrics.py`.

---

## Local Development · 로컬 개발

- Python 3.11+, Ruff, mypy, pre-commit, Commitlint.
- Node.js(프론트 보조)는 `make setup-hooks` 가 husky 까지 설치합니다.
- 컨테이너 볼륨 마운트로 소스 변경이 컨테이너 내부에 즉시 반영됩니다 (`make dev`).
- 환경 변수는 `deploy/.env` 가 단일 진입점이며 Compose 가 자동 주입합니다.
- 신규 라우트를 추가할 때는 권한 매트릭스를 `app/core/auth/decorators.py` 와 함께 검토합니다.

---

## Testing · 테스트

`pyproject.toml` 의 `[tool.pytest.ini_options]` 기준입니다.

| 항목 | 값 |
| --- | --- |
| `pythonpath` | `app` |
| `testpaths` | `tests` |
| 파일 규칙 | `test_*.py` |
| 클래스 규칙 | `Test*` |
| 함수 규칙 | `test_*` |
| 옵션 | `-v --tb=short` |

사용 가능한 마커:

- `unit` — 외부 의존성 없는 단위 테스트
- `integration` — 서비스 의존 통합 테스트
- `security` — 보안 회귀 테스트
- `db` — 데이터베이스 테스트
- `api` — API 엔드포인트 테스트

실행 예시:

```bash
pytest -m unit
pytest -m api
pytest -m "security or db"
make test
```

---

## Maintainers · 연락처

| 역할 | 위치 |
| --- | --- |
| 저장소 오너즈 명단 | `OWNERS` |
| 기여 정책 | `CONTRIBUTING.md` |
| 변경 이력 | `CHANGELOG.md` |
| 릴리스 버전 | `VERSION` |
| 에이전트 운영 지침 | `AGENTS.md` · `app/AGENTS.md` · 하위 `AGENTS.md` |
| 커밋 규칙 | `commitlint.config.js` |
| 라이선스 | `LICENSE` |

---

## Further Documentation · 추가 문서 링크

- `CHANGELOG.md` — 버전별 변경 이력
- `CONTRIBUTING.md` — 브랜치·PR·코드 리뷰 절차
- `OWNERS` — 도메인 오너와 리뷰어
- `LICENSE` — 라이선스 전문
- `app/core/routes/api/collection/AGENTS.md` — 수집 모듈 운영 메모
- `app/core/routes/api/blacklist/AGENTS.md` — 블랙리스트 모듈 운영 메모
- `app/core/routes/api/fortinet/AGENTS.md` — Fortinet 연동 운영 메모
- `app/core/AGENTS.md`, `app/core/auth/AGENTS.md`, `app/core/monitoring/AGENTS.md`, `app/core/routes/AGENTS.md` — 계층별 메모
- `Makefile` — 전 명령의 단일 참조표 (`make help`)

---

## License

본 저장소의 라이선스는 `LICENSE` 파일을 따릅니다. 외부 배포·수정 시 동일 라이선스 조건을 확인하십시오.