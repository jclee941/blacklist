# Blacklist Service Management

> **통합 위협 인텔리전스 수집·동기화 · 블랙리스트 중앙 관리 · Fortinet 자동 배포 플랫폼**
> **Unified threat-intel aggregation, centralized blacklist management, and Fortinet deployment platform.**

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Ruff](https://img.shields.io/badge/lint-Ruff-D7FF64?logo=ruff&logoColor=black)
![mypy](https://img.shields.io/badge/types-mypy-2A6DB2)
![Container](https://img.shields.io/badge/container-Docker%20%2F%20Compose-2496ED?logo=docker&logoColor=white)
![Commit](https://img.shields.io/badge/commits-Commitlint-F8C445?logo=conventionalcommits&logoColor=black)
![Status](https://img.shields.io/badge/status-Internal%20PoC-orange)

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

1. 외부 위협 인텔 소스 → `app/core/routes/api/collection/sources.py` 가 스케줄별 수집 트리거
2. 원본 항목 정규화 → `app/core/routes/api/collection/config.py` · `utils.py` 가 IP/도메인/URL 분류
3. 중앙 블랙리스트 적재 → `app/core/routes/api/blacklist/core.py` + `database_api.py` 가 영속화
4. 수동/배치 가공 → `blacklist/batch.py`, `blacklist/management.py` (병합·만료·코멘트)
5. Fortinet 배포 → `blacklist/system.py` + `fortinet/core.py` 가 address object group 동기화
6. 운영자 확인 → `app/templates/index.html`, `collection.html`, `monitoring/dashboard.html`
7. 실시간 채널 → `app/core/routes/websocket_routes.py` 가 수집·동기화 이벤트를 푸시

---

## 주요 기능 · Features

| 기능 영역 | 설명 | 핵심 모듈 |
| --- | --- | --- |
| 위협 인텔 수집 | 다중 소스 스케줄 수집, 메타데이터 보존 | `app/core/routes/api/collection/` |
| 컬렉션 관리 | 자격 증명, 소스, 이력, 수동 트리거 | `collection/credentials.py`, `sources.py`, `history.py`, `trigger.py` |
| 정규화·중복 제거 | IP/CIDR/도메인/URL 분류, 만료 정책 | `app/core/routes/api/collection/utils.py` |
| 블랙리스트 CRUD | 항목 추가/병합/태그/만료/롤백 | `app/core/routes/api/blacklist/` |
| Fortinet 배포 | address object group 자동 동기화 | `app/core/routes/api/fortinet/core.py` |
| 인증·인가 | 세션, JWT, 데코레이터 기반 가드 | `app/core/auth/` |
| 모니터링 | 메트릭, 캐시, 에러 카운터, 대시보드 | `app/core/monitoring/`, `templates/monitoring/dashboard.html` |
| 웹 콘솔 | Jinja2 SPA-ish 콘솔, 설정/세션 화면 | `app/templates/*.html` |
| 구조화 로깅 | JSON 로깅, 사이즈·시간 기반 회전 | `app/utils/structured_logging.py`, `log_rotation_manager.py` |
| 배포 검증 | 컨테이너 기동 전 환경/설정 점검 | `app/deployment_validation.py` |

---

## 패키지 구성 · Package Contents

| 경로 | 역할 |
| --- | --- |
| `app/run_app.py` | 로컬/CI 기동 엔트리포인트 |
| `app/entrypoint.sh` | 컨테이너 내부 기동 스크립트 |
| `app/Dockerfile` | 컨테이너 이미지 정의 |
| `app/requirements.txt` | Python 의존성 고정본 |
| `app/deployment_validation.py` | 배포 전 환경 검증 |
| `app/utils/structured_logging.py` | JSON 구조화 로거 |
| `app/utils/log_rotation_manager.py` | 로그 회전 정책 |
| `app/templates/` | Jinja2 웹 콘솔 화면 |
| `app/core/app.py` | Flask/FastAPI 앱 팩토리 |
| `app/core/config.py` | 환경 변수 기반 설정 |
| `app/core/auth_manager.py` | 인증/세션 관리 |
| `app/core/auth/` | JWT, 미들웨어, 데코레이터 |
| `app/core/monitoring/` | 메트릭·캐시·에러 카운터 |
| `app/core/routes/web_routes.py` | 콘솔 라우트 |
| `app/core/routes/api_routes.py` | API 라우트 등록기 |
| `app/core/routes/websocket_routes.py` | WebSocket 채널 |
| `app/core/routes/proxy_routes.py` | 업스트림 프록시 |
| `app/core/routes/system_routes.py` | 헬스/시스템 엔드포인트 |
| `app/core/routes/collection_routes_simple.py` | 단순 수집 라우트 |
| `app/core/routes/api/` | 도메인별 API 블루프린트 |
| `app/core/routes/api/collection/` | 수집 도메인 |
| `app/core/routes/api/blacklist/` | 블랙리스트 도메인 |
| `app/core/routes/api/fortinet/` | Fortinet 연동 |
| `Makefile` | 빌드/검증/배포 태스크 |
| `pyproject.toml` | Ruff/mypy/pytest 설정 |
| `mypy.ini` | 타입 체커 설정 |
| `commitlint.config.js` | 커밋 메시지 규칙 |
| `OWNERS`, `VERSION`, `CHANGELOG.md` | 거버넌스/릴리스 메타 |
| `AGENTS.md`, `CONTRIBUTING.md` | 기여자 가이드 |

---

## 먼저 읽을 파일 · First Files to Read

| 순서 | 파일 | 왜 읽는지 |
| --- | --- | --- |
| 1 | `app/core/app.py` | 앱 팩토리, 미들웨어, 라우트 등록 순서 |
| 2 | `app/core/config.py` | 환경 변수 스키마 |
| 3 | `app/core/routes/api_routes.py` | API 블루프린트 등록 구조 |
| 4 | `app/core/routes/api/collection/sources.py` | 수집 워크플로 진입점 |
| 5 | `app/core/routes/api/blacklist/core.py` | 블랙리스트 도메인 모델 |
| 6 | `app/core/routes/api/fortinet/core.py` | Fortinet 배포 로직 |
| 7 | `app/entrypoint.sh`, `app/Dockerfile` | 컨테이너 라이프사이클 |
| 8 | `app/deployment_validation.py` | 배포 전 체크리스트 |
| 9 | `Makefile` | 운영자가 실제로 칠 명령 |
| 10 | `app/templates/index.html` | 콘솔 UX 기준선 |

---

## 아키텍처 · Architecture

| 계층 | 책임 | 코드 위치 |
| --- | --- | --- |
| Presentation | Jinja2 콘솔, 정적 자원 | `app/templates/` |
| Edge | WebSocket, 프록시, 시스템 라우트 | `app/core/routes/websocket_routes.py`, `proxy_routes.py`, `system_routes.py` |
| API | 도메인별 REST 블루프린트 | `app/core/routes/api/` |
| Auth | JWT 발급·검증, 가드 데코레이터 | `app/core/auth/` |
| Domain | 수집·블랙리스트·Fortinet 도메인 서비스 | `collection/`, `blacklist/`, `fortinet/` |
| Observability | 메트릭, 캐시, 에러 카운터 | `app/core/monitoring/` |
| Platform | 설정, 로깅, 회전, 배포 검증 | `app/core/config.py`, `app/utils/`, `app/deployment_validation.py` |
| Runtime | 엔트리포인트, 컨테이너 | `app/run_app.py`, `app/entrypoint.sh`, `app/Dockerfile` |

### 요청 흐름 · Request Flow (웹 콘솔 로그인 → Fortinet 배포)

1. 브라우저가 `/` 로 진입 → `web_routes.py` 가 `index.html` 렌더링
2. 로그인 POST → `api/auth_routes.py` 가 자격 증명 검증, `auth/jwt_service.py` 가 토큰 발급
3. 이후 요청은 `auth/middleware.py` + `auth/decorators.py` 로 가드
4. 운영자가 “수집 실행” 클릭 → `api/collection/trigger.py` 가 작업 큐에 등록
5. `collection/sources.py` 워커가 외부 피드 호출, `utils.py` 가 정규화
6. 결과를 `api/blacklist/core.py` + `database_api.py` 로 영속화
7. 배포 트리거 → `blacklist/system.py` → `fortinet/core.py` 가 address object group 동기화
8. `monitoring/metrics.py` 가 메트릭 증가, `monitoring/dashboard.html` 가 갱신
9. `websocket_routes.py` 가 진행 상태/완료 이벤트를 콘솔에 푸시
10. 모든 단계 로그는 `utils/structured_logging.py` + `log_rotation_manager.py` 로 기록

---

## 빠른 시작 · Quickstart

### 사전 요구 사항 · Prerequisites

| 항목 | 권장 버전 |
| --- | --- |
| Python | 3.11 이상 |
| Docker / Compose | 최근 stable |
| Make | GNU Make |
| OS | Linux (컨테이너 기준) |

### 1) 저장소 준비

```bash
git clone <your-fork-or-mirror-url> blacklist-service-management
cd blacklist-service-management
cp deploy/.env.example deploy/.env   # 실제 값으로 편집
```

### 2) 컨테이너로 실행 (권장)

```bash
make setup-hooks
make dev                # 빌드 후 기동, 핫 리로드 활성화
# http://localhost:2542
```

| Make 타깃 | 용도 |
| --- | --- |
| `make dev` | 개발 환경 (빌드 + 핫 리로드) |
| `make dev-no-build` | 기존 이미지로 빠르게 기동 |
| `make dev-prod` | 프로덕션 유사 (오버라이드 없음, 핫 리로드 OFF) |
| `make dev-app` | app 서비스만 재기동 |
| `make up` | Compose `up -d` |
| `make down` | Compose `down` |
| `make logs` | 로그 스트림 |
| `make restart` | 서비스 재기동 |
| `make health` | 헬스 체크 |
| `make test` | pytest 실행 |
| `make verify` | 린트·타입·시크릿·프리커밋 통합 검증 |
| `make verify-lint` | Ruff |
| `make verify-types` | mypy |
| `make verify-secrets` | 시크릿 누출 점검 |
| `make verify-pre-commit` | pre-commit 훅 |
| `make verify-quick` | 빠른 검증 세트 |
| `make verify-all` | 전체 검증 |
| `make release` | 릴리스 절차 |
| `make release-dry` | 릴리스 드라이런 |
| `make clean` | 산출물 정리 |

### 3) 로컬에서 직접 실행

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
export PORT=2542 ENV=development
python app/run_app.py
```

---

## 환경 설정 · Configuration

`app/core/config.py` 가 다음 키들을 사용합니다. `deploy/.env` 또는 컨테이너 환경으로 주입하세요.

| 키 | 기본값 | 설명 |
| --- | --- | --- |
| `ENV` | `development` | `development` / `production` |
| `PORT` | `2542` | HTTP 리스닝 포트 |
| `DATABASE_URL` | (필수) | 영속 DB 연결 문자열 |
| `REDIS_URL` | (선택) | 캐시·WebSocket 백엔드 |
| `JWT_SECRET` | (필수) | 토큰 서명 키 |
| `JWT_EXPIRES` | `3600` | 토큰 만료(초) |
| `LOG_LEVEL` | `INFO` | 루트 로거 레벨 |
| `LOG_FORMAT` | `json` | `json` / `text` |
| `LOG_ROTATION_MAX_BYTES` | `10485760` | 회전 임계(10MB) |
| `LOG_ROTATION_BACKUP_COUNT` | `10` | 보관 파일 수 |
| `FORTINET_API_URL` | (선택) | Fortinet 관리 엔드포인트 |
| `FORTINET_API_TOKEN` | (선택) | Fortinet 인증 토큰 |
| `COLLECTION_CRON` | (선택) | 수집 스케줄 (crontab) |

---

## API · Entry Points

콘솔: `http://<host>:2542/`
헬스: `http://<host>:2542/health` (system_routes)
WebSocket: `ws://<host>:2542/ws` (websocket_routes)

| 메서드 | 경로 | 모듈 | 설명 |
| --- | --- | --- | --- |
| POST | `/api/auth/login` | `api/auth_routes.py` | 로그인, JWT 발급 |
| POST | `/api/auth/refresh` | `api/auth_routes.py` | 토큰 갱신 |
| GET | `/api/dashboard` | `api/dashboard_api.py` | 대시보드 요약 |
| GET | `/api/system` | `api/system_api.py` | 시스템 상태 |
| GET | `/api/settings` | `api/settings_api.py` | 설정 조회 |
| PUT | `/api/settings` | `api/settings_api.py` | 설정 변경 |
| GET | `/api/database` | `api/database_api.py` | DB 메타 |
| GET | `/api/analytics` | `api/analytics.py` | 분석 지표 |
| GET | `/api/error-metrics` | `api/error_metrics_api.py` | 에러 카운터 |
| GET | `/api/migration` | `api/migration.py` | 마이그레이션 상태 |
| GET | `/api/ip-management` | `api/ip_management_helpers.py` | IP 헬퍼 |
| GET | `/api/collection/sources` | `api/collection/sources.py` | 소스 목록 |
| POST | `/api/collection/trigger` | `api/collection/trigger.py` | 수동 수집 |
| GET | `/api/collection/history` | `api/collection/history.py` | 수집 이력 |
| GET | `/api/collection/status` | `api/collection/status.py` | 작업 상태 |
| GET | `/api/collection/config` | `api/collection/config.py` | 정규화 설정 |
| GET | `/api/collection/credentials` | `api/collection/credentials.py` | 소스 자격 증명 |
| POST | `/api/collection/sync` | `api/collection/sync.py` | 동기화 |
| GET | `/api/blacklist` | `api/blacklist/core.py` | 항목 조회 |
| POST | `/api/blacklist` | `api/blacklist/management.py` | 항목 추가 |
| POST | `/api/blacklist/batch` | `api/blacklist/batch.py` | 일괄 작업 |
| POST | `/api/blacklist/collect` | `api/blacklist/collection.py` | 통합 수집 |
| GET | `/api/blacklist/system` | `api/blacklist/system.py` | 시스템 뷰 |
| POST | `/api/fortinet/register` | `api/fortinet_register.py` | Fortinet 등록 |
| POST | `/api/fortinet/deploy` | `api/fortinet/core.py` | address object 동기화 |

자세한 스키마는 각 모듈의 docstring과 `app/core/routes/api/` 하위 코드를 확인하세요.

---

## 로컬 개발 · Local Development

| 작업 | 명령 |
| --- | --- |
| 가상환경 | `python -m venv .venv && source .venv/bin/activate` |
| 의존성 설치 | `pip install -r app/requirements.txt` |
| 핫 리로드 기동 | `make dev` |
| 앱만 재기동 | `make dev-app` |
| 로그 확인 | `make logs` |
| 셸 진입 | `docker compose -f deploy/docker-compose.yml --env-file deploy/.env exec app sh` |
| 코드 포맷 | `ruff format app/` |
| 임포트 정렬 | `ruff check --fix app/` |
| 타입 검사 | `mypy app/` |
| 시크릿 점검 | `make verify-secrets` |

기여 전 `make verify` 통과가 권장됩니다.

---

## 테스트 · Testing

`pyproject.toml` 의 pytest 설정:

- 테스트 경로: `tests/`
- 마커: `unit`, `integration`, `security`, `db`, `api`
- 기본 옵션: `-v --tb=short`

```bash
make test
# 또는
pytest -m unit
pytest -m integration
pytest -m security
pytest -m "api and not integration"
```

`integration`, `security`, `db` 마커는 실제 서비스가 필요하므로 CI 또는 staging 환경에서만 실행하세요.

---

## 문제 해결 · Troubleshooting

| 증상 | 점검 |
| --- | --- |
| 2542 포트 충돌 | `PORT` 변경 또는 `lsof -i :2542` |
| Fortinet 배포 실패 | `FORTINET_API_URL`, `FORTINET_API_TOKEN` 만료, address object group 권한 |
| JWT 401 | `JWT_SECRET` 회전 후 토큰 폐기 여부, `JWT_EXPIRES` |
| 로그 누락 | `LOG_ROTATION_MAX_BYTES` 너무 작음, 디스크 여유 |
| 컨테이너 기동 실패 | `make verify` 로 사전 검증, `app/deployment_validation.py` 출력 확인 |
| 수집 실패 | `collection/credentials.py` 자격 증명, `collection/sources.py` 스케줄 |

---

## 기여 가이드 · Contributing

1. 이슈를 먼저 등록하거나 기존 이슈에 연결
2. 브랜치: `feature/<scope>` 또는 `fix/<scope>`
3. 커밋 메시지: Conventional Commits (commitlint가 강제)
4. `make verify` 통과 후 PR 생성
5. `OWNERS` 의 리뷰어를 지정

자세한 절차는 `CONTRIBUTING.md` 를 따르세요.

---

## 거버넌스 · Governance

| 파일 | 용도 |
| --- | --- |
| `OWNERS` | 코드 오너십 |
| `VERSION` | 시맨틱 버전 |
| `CHANGELOG.md` | 릴리스 노트 |
| `AGENTS.md` | 에이전트/자동화 컨텍스트 |
| `LICENSE` | 라이선스 전문 |
| `commitlint.config.js` | 커밋 규칙 |

---

## 운영자 / 담당자 · Maintainers

`OWNERS` 파일을 참고하세요. 내부 핸드오프는 사내 메신저 `#blacklist-platform` 채널을 기본으로 사용합니다.

| 역할 | 채널 |
| --- | --- |
| 1차 운영 | 사내 `#blacklist-platform` |
| 보안 이슈 | 사내 보안팀 핫라인 |
| 릴리스 코디 | OWNERS 내 release captain |

---

## 추가 문서 · Further Documentation

| 주제 | 위치 |
| --- | --- |
| 커밋 규칙 | `commitlint.config.js` |
| 릴리스 절차 | `Makefile` (`release`, `release-dry`) |
| 환경 변수 | `app/core/config.py` |
| API 스키마 | `app/core/routes/api/` 하위 docstring |
| 프록시 | `app/core/routes/proxy_routes.py` |
| WebSocket | `app/core/routes/websocket_routes.py` |
| 모니터링 | `app/core/monitoring/`, `app/templates/monitoring/dashboard.html` |
| 배포 검증 | `app/deployment_validation.py` |
| 라이선스 | `LICENSE` |

---

## 라이선스 · License

저장소 루트의 `LICENSE` 파일을 따릅니다. 사내 사용 조건이 명시된 경우 그 조건이 우선합니다.