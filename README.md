# Blacklist Collection & Fortinet Integration Service

[![Status](https://img.shields.io/badge/status-active-success)]()
[![Python](https://img.shields.io/badge/python-3.11+-blue)]()
[![Framework](https://img.shields.io/badge/framework-Flask-green)]()
[![Docker](https://img.shields.io/badge/docker-compose-2496ED)]()
[![License](https://img.shields.io/badge/license-see%20LICENSE-lightgrey)]()

## 개요 (Overview)

여러 위협 인텔리전스 소스에서 IP·도메인 블랙리스트를 수집·정규화하고, Fortinet 방화벽 등록, 웹 대시보드, 모니터링, 감사 로그를 한곳에서 제공하는 Flask 기반 백엔드 서비스입니다. 운영자는 단일 엔드포인트에서 위협 차단 목록을 통합 관리할 수 있습니다.

A Flask-based backend that collects, normalizes, and consolidates IP/domain blacklists from multiple threat-intelligence sources, syncs them to Fortinet firewalls, and exposes them through a web dashboard, REST APIs, and monitoring surfaces.

## 빠른 상태 (Quick Status)

| 항목 (Item) | 값 (Value) |
| --- | --- |
| Product | Blacklist Collection & Management Service |
| Language / Runtime | Python 3.11+ |
| Web Framework | Flask (Jinja2 templates) |
| Auth | JWT (`app/core/auth/`) |
| Default Port | `2542` |
| Container | Docker / docker compose (`deploy/docker-compose.yml`) |
| Lint / Type | Ruff, mypy |
| Tests | pytest (`tests/`, markers: unit, integration, security, db, api) |
| Deployment | `make up` / `make deploy` / `make release` |

## 흐름 요약 (Flow Summary)

1. **소스 수집** — `app/core/routes/api/collection/sources.py` 가 외부 위협 인텔리전스 피드를 가져옵니다.
2. **정규화 및 저장** — `collection/credentials.py`, `collection/history.py` 가 항목을 정규화하고 이력을 남깁니다.
3. **관리** — `app/core/routes/api/blacklist/` 가 추가/삭제/배치 작업을 처리합니다.
4. **방화벽 동기화** — `app/core/routes/api/fortinet/core.py` 가 Fortinet 디바이스에 블랙리스트를 반영합니다.
5. **노출** — `web_routes.py` (HTML 대시보드), `api_routes.py` (JSON API), `websocket_routes.py` (실시간 로그) 로 운영자에게 전달합니다.
6. **관측** — `app/core/monitoring/` 이 메트릭·캐시·에러 카운터를 노출하고 `templates/monitoring/dashboard.html` 에 시각화합니다.

## 목차 (Table of Contents)

- [Purpose / Package Contents](#purpose--package-contents)
- [Status](#status)
- [First Files to Read](#first-files-to-read)
- [Architecture](#architecture)
- [Quickstart](#quickstart)
- [Configuration](#configuration)
- [Commands Reference](#commands-reference)
- [Local Development](#local-development)
- [Testing](#testing)
- [Maintainers / Points of Contact](#maintainers--points-of-contact)
- [Contributing](#contributing)
- [License](#license)
- [Further Documentation](#further-documentation)

## Purpose / Package Contents

| 디렉터리 (Directory) | 역할 (Role) |
| --- | --- |
| `app/` | Flask 애플리케이션 진입점 및 컨테이너 이미지 빌드 컨텍스트 |
| `app/core/app.py` | 앱 팩토리, 블루프린트 등록 |
| `app/core/config.py` | 환경 변수 기반 설정 로더 |
| `app/core/auth/` | JWT 발급·검증, 인증 데코레이터, 미들웨어 |
| `app/core/monitoring/` | 캐시·에러·메트릭 수집기 |
| `app/core/routes/web_routes.py` | HTML 페이지 라우팅 (대시보드, 세션, 설정 등) |
| `app/core/routes/api/` | JSON API (auth, analytics, settings, system 등) |
| `app/core/routes/api/collection/` | 소스, 자격증명, 이력, 동기화, 트리거 |
| `app/core/routes/api/blacklist/` | 블랙리스트 CRUD·배치·관리 |
| `app/core/routes/api/fortinet/` | Fortinet 디바이스 등록·동기화 |
| `app/templates/` | Jinja2 HTML 템플릿 |
| `app/utils/` | 구조화 로깅, 로그 로테이션 |
| `deploy/` | docker-compose, 환경 파일 |
| `tests/` | pytest 기반 테스트 스위트 |
| `Makefile` | 개발·배포·릴리즈·검증 작업 |

## Status

- 본 서비스는 **운영 가능(production-ready)** 상태를 목표로 합니다.
- 활성 기능: 수집, 블랙리스트 관리, Fortinet 동기화, 인증, 모니터링, 대시보드.
- 현재 마스터 브랜치는 `master` 입니다 (저장소 메타데이터 기준).

## First Files to Read

운영자가 가장 먼저 살펴봐야 할 파일은 다음 순서를 권장합니다.

| 순서 (Order) | 파일 (File) | 이유 (Why read it) |
| --- | --- | --- |
| 1 | `app/run_app.py` | 서비스 진입점 |
| 2 | `app/core/app.py` | 앱 팩토리와 블루프린트 등록 흐름 |
| 3 | `app/core/config.py` | 환경 변수 키와 기본값 |
| 4 | `app/core/routes/web_routes.py` | 페이지 라우팅 맵 |
| 5 | `app/core/routes/api_routes.py` | REST API 진입점 |
| 6 | `app/core/routes/api/collection/sources.py` | 수집 파이프라인 |
| 7 | `app/core/routes/api/fortinet/core.py` | Fortinet 동기화 로직 |
| 8 | `app/core/auth/jwt_service.py` | 인증 토큰 처리 |
| 9 | `Makefile` | 작업·배포 명령 |
| 10 | `deploy/docker-compose.yml` | 컨테이너 토폴로지 |

## Architecture

### 모듈 구조 (Module Layout)

| 계층 (Layer) | 위치 (Location) | 책임 (Responsibility) |
| --- | --- | --- |
| Entry | `app/run_app.py`, `app/entrypoint.sh` | 컨테이너/로컬 부트스트랩 |
| App Factory | `app/core/app.py` | Flask 앱 생성, 확장 등록 |
| Config | `app/core/config.py` | 환경 기반 설정 |
| Web UI | `app/core/routes/web_routes.py`, `app/templates/` | 서버 렌더링 페이지 |
| REST API | `app/core/routes/api/`, `api_routes.py` | JSON API |
| Realtime | `app/core/routes/websocket_routes.py` | WebSocket 푸시 |
| Domain: Collection | `app/core/routes/api/collection/` | 소스·자격·이력·동기화 |
| Domain: Blacklist | `app/core/routes/api/blacklist/` | 항목 관리 |
| Domain: Fortinet | `app/core/routes/api/fortinet/`, `fortinet_register.py` | 방화벽 등록 |
| Auth | `app/core/auth/` | JWT, 데코레이터, 미들웨어 |
| Observability | `app/core/monitoring/`, `app/utils/` | 메트릭, 로깅 |
| Validation | `app/deployment_validation.py` | 배포 사전 검증 |

### 요청 흐름 (Request Flow)

1. 운영자가 브라우저 또는 API 클라이언트로 요청을 보냅니다.
2. `app/core/auth/middleware.py` 가 인증 헤더와 세션을 검증합니다.
3. 라우터(`web_routes.py` 또는 `api/`)가 도메인 모듈로 위임합니다.
4. 도메인 모듈은 설정(`config.py`)과 자격증명(`collection/credentials.py`)을 사용해 외부 시스템(소스, Fortinet)과 상호작용합니다.
5. 결과는 템플릿 렌더링 또는 JSON 응답으로 반환되며, `app/core/monitoring/` 이 메트릭을 기록합니다.
6. WebSocket 채널은 장기 작업(동기화, 수집)의 진행 상황을 구독자에게 푸시합니다.

## Quickstart

### 사전 요구사항 (Prerequisites)

| 항목 (Item) | 버전 (Version) |
| --- | --- |
| Python | 3.11 이상 |
| Docker / docker compose | 최신 안정 버전 |
| GNU Make | 임의의 최신 버전 |

### 로컬 설치 (Local Install)

```bash
# 1. 의존성 설치
pip install -r app/requirements.txt

# 2. 환경 변수 준비
cp deploy/.env.example deploy/.env  # 필요 시

# 3. 앱 실행
python app/run_app.py
# 또는
make dev
```

### 컨테이너 실행 (Container Run)

```bash
make up           # docker compose up -d --build
make logs         # 로그 스트림
make health       # 헬스 체크
```

기본 진입점은 `http://<host>:2542` 입니다.

## Configuration

모든 설정은 환경 변수로 주입하며, `app/core/config.py` 에서 키를 해석합니다.

| 카테고리 (Category) | 예시 키 (Example Keys) | 설명 (Description) |
| --- | --- | --- |
| Flask | `FLASK_ENV`, `SECRET_KEY` | 앱 모드·시크릿 |
| Auth | `JWT_SECRET`, `JWT_TTL` | 토큰 발급·만료 |
| Server | `HOST`, `PORT` | 바인딩 (기본 `PORT=2542`) |
| Collection | `COLLECTION_INTERVAL`, `SOURCE_TIMEOUT` | 수집 주기·제한 |
| Blacklist | `BLACKLIST_DB_URL` | 블랙리스트 저장소 |
| Fortinet | `FORTINET_HOST`, `FORTINET_TOKEN` | 디바이스 인증 |
| Logging | `LOG_LEVEL`, `LOG_PATH` | 구조화 로깅 레벨·경로 |

값은 `deploy/.env` 또는 컨테이너 오버라이드로 전달합니다.

## Commands Reference

`Makefile` 은 다음 타겟을 제공합니다.

| 명령 (Command) | 목적 (Purpose) |
| --- | --- |
| `make help` | 사용 가능한 타겟 목록 출력 |
| `make setup-hooks` | pre-commit·husky 훅 설치 |
| `make dev` | 개발 환경(볼륨 마운트, 핫 리로드) 기동 |
| `make dev-no-build` | 기존 이미지로 빠르게 기동 |
| `make dev-prod` | 운영 모드에 가까운 환경 기동 |
| `make dev-app` | 앱 서비스만 재시작 |
| `make up` | docker compose 기동 |
| `make down` | docker compose 종료 |
| `make restart` | 서비스 재시작 |
| `make logs` | 컨테이너 로그 스트림 |
| `make health` | 헬스 체크 |
| `make build` | 이미지 빌드 |
| `make clean` | 정리 |
| `make test` | 테스트 실행 |
| `make verify` / `verify-lint` / `verify-types` / `verify-secrets` / `verify-pre-commit` / `verify-quick` / `verify-all` | 정적 검증 묶음 |
| `make deploy` | 배포 실행 |
| `make prod` | 운영 모드 작업 |
| `make release` / `release-dry` | 릴리즈 절차 (드라이런 포함) |

## Local Development

- 코드 스타일: Ruff (`pyproject.toml`, `line-length = 120`).
- 타입 검사: `mypy` (설정 파일 `mypy.ini`).
- 커밋 메시지: Conventional Commits (`commitlint.config.js`).
- 프런트엔드가 있다면 `frontend/` 에서 `npm install` 후 husky 훅이 활성화됩니다 (`make setup-hooks`).
- 로깅은 `app/utils/structured_logging.py` 의 JSON 로거를 사용하며, `app/utils/log_rotation_manager.py` 로 로테이션합니다.
- 배포 전 `app/deployment_validation.py` 로 사전 검증을 권장합니다.

## Testing

테스트 러너는 pytest 입니다 (`pyproject.toml` 의 `[tool.pytest.ini_options]` 참조).

| 마커 (Marker) | 의미 (Meaning) |
| --- | --- |
| `unit` | 외부 의존성 없는 단위 테스트 |
| `integration` | 실행 중인 서비스가 필요한 통합 테스트 |
| `security` | 보안 관련 테스트 |
| `db` | 데이터베이스 테스트 |
| `api` | API 엔드포인트 테스트 |

| 작업 (Task) | 명령 (Command) |
| --- | --- |
| 전체 실행 | `make test` 또는 `pytest` |
| 단위 테스트만 | `pytest -m unit` |
| 통합 테스트만 | `pytest -m integration` |
| API 테스트만 | `pytest -m api` |

`pythonpath = ["app"]` 으로 `app/` 패키지가 자동으로 임포트 경로에 추가됩니다.

## Maintainers / Points of Contact

- 저장소 소유자 정보는 `OWNERS` 파일을 참조하세요.
- 거버넌스 절차는 `CONTRIBUTING.md` 를 따릅니다.
- 변경 이력은 `CHANGELOG.md`, 현재 버전은 `VERSION` 파일을 참조하세요.
- 자동화 정책은 저장소 내 workflow 파일과 `AGENTS.md` 의 지침을 따릅니다 (운영자 참고용).

## Contributing

1. 이슈를 먼저 등록하거나 기존 이슈에 연결합니다.
2. 브랜치를 생성하고 변경 사항을 커밋합니다 (커밋 메시지는 Conventional Commits 준수).
3. 로컬에서 `make verify-all && make test` 를 통과시킵니다.
4. PR 을 열고 리뷰어를 지정합니다 (리뷰어 지정 가이드라인은 `OWNERS` 참조).
5. CI 가 통과하면 자동 머지 또는 수동 머지를 진행합니다.

상세 절차는 `CONTRIBUTING.md` 를 참고하세요.

## License

이 저장소는 `LICENSE` 파일에 명시된 라이선스를 따릅니다. 사용 전 라이선스 전문을 확인하세요.

## Further Documentation

| 문서 (Document) | 경로 (Path) |
| --- | --- |
| 변경 이력 | `CHANGELOG.md` |
| 기여 절차 | `CONTRIBUTING.md` |
| 거버넌스 / 자동화 가이드 | `AGENTS.md`, `app/AGENTS.md`, `app/core/AGENTS.md` |
| 도메인 모듈 가이드 | `app/core/routes/api/collection/AGENTS.md`, `app/core/routes/api/blacklist/AGENTS.md`, `app/core/routes/api/fortinet/AGENTS.md` |
| 인증 모듈 가이드 | `app/core/auth/AGENTS.md` |
| 모니터링 모듈 가이드 | `app/core/monitoring/AGENTS.md` |
| 빌드·배포 작업 | `Makefile` |
| 컨테이너 정의 | `app/Dockerfile`, `deploy/docker-compose.yml` |
| 린트·테스트 설정 | `pyproject.toml`, `mypy.ini`, `commitlint.config.js` |
| 버전 | `VERSION` |