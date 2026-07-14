# Blacklist Service

![Python 3.11](https://img.shields.io/badge/Python-3.11-blue)
![Docker](https://img.shields.io/badge/Docker-supported-blue)
![License](https://img.shields.io/badge/License-see%20LICENSE-green)
![Status](https://img.shields.io/badge/Status-active-brightgreen)

Fortinet 연동, 블랙리스트 수집, 운영 대시보드, API, 인증, 모니터링을 제공하는
Python 기반 블랙리스트 관리 서비스입니다.

English: A Python service for blacklist collection, Fortinet integration,
operator dashboards, authenticated APIs, and runtime monitoring.

## 빠른 상태 / Quick Glance

| 항목 | 현재 값 |
|---|---|
| 제품 상태 | 활성 개발 중, 운영 배포 가능. 프로덕션 적용 전 환경 검증 필요 |
| 주요 사용자 | 보안 운영자, 네트워크 관리자, 플랫폼 운영자, API 클라이언트 |
| 실행 단위 | `app/run_app.py`, `app/core/app.py`, Docker `app/Dockerfile` |
| 주요 화면 | `/`, `/settings`, `/sessions`, `/integrations`, `/monitoring` |
| 주요 API | `/api/*`, `/api/blacklist/*`, `/api/collection/*`, `/api/fortinet/*` |
| 운영 명령 | `make dev`, `make logs`, `make health`, `make test` |
| 품질 도구 | `pytest`, `ruff`, `mypy`, `commitlint`, `pre-commit` |
| 도움말 | [`CONTRIBUTING.md`](CONTRIBUTING.md), [`CHANGELOG.md`](CHANGELOG.md), [`OWNERS`](OWNERS) |

## 운영 흐름 / Operator Flow

1. 수집 설정을 확인합니다: `/settings`, `/api/collection/*`
2. 블랙리스트 소스를 동기화합니다: `/api/collection/sync` 또는 관련 trigger API
3. Fortinet 등록 상태를 확인합니다: `/integrations`, `/api/fortinet/*`
4. 운영 상태를 봅니다: `/monitoring`, `/api/system/*`, `/api/*/metrics`
5. 문제가 있으면 로그와 헬스체크를 확인합니다: `make logs`, `make health`

English: Configure sources, trigger collection, register or verify Fortinet
integration, then monitor service health through dashboard/API and logs.

## 목차 / Table of Contents

- [목적 / Purpose](#목적--purpose)
- [주요 기능 / Features](#주요-기능--features)
- [패키지 구성 / Package Contents](#패키지-구성--package-contents)
- [처음 읽을 파일 / First Files to Read](#처음-읽을-파일--first-files-to-read)
- [아키텍처 / Architecture](#아키텍처--architecture)
- [API 및 진입점 / API and Entry Points](#api-및-진입점--api-and-entry-points)
- [빠른 시작 / Quick Start](#빠른-시작--quick-start)
- [설정 / Configuration](#설정--configuration)
- [명령어 / Commands](#명령어--commands)
- [로컬 개발 / Local Development](#로컬-개발--local-development)
- [테스트 / Testing](#테스트--testing)
- [운영 관찰성 / Observability](#운영-관찰성--observability)
- [보안 참고 / Security Notes](#보안-참고--security-notes)
- [기여 / Contributing](#기여--contributing)
- [유지보수 / Maintainers](#유지보수--maintainers)
- [라이선스 / License](#라이선스--license)

## 목적 / Purpose

Blacklist Service는 여러 수집 소스에서 블랙리스트 데이터를 가져오고,
운영자가 웹 대시보드와 API를 통해 상태를 확인하며,
Fortinet 장비 또는 관련 보안 시스템에 등록 작업을 수행할 수 있게 하는
운영용 백엔드 애플리케이션입니다.

English: The service centralizes blacklist collection, exposes operational
APIs and dashboards, and supports Fortinet-oriented registration workflows.

이 프로젝트가 유용한 이유:

- 수집, 동기화, 등록, 모니터링을 하나의 서비스로 묶습니다.
- 운영자는 웹 화면으로 세션, 설정, 통합, 로그를 확인할 수 있습니다.
- 자동화 클라이언트는 REST API를 통해 블랙리스트와 시스템 상태를 제어할 수 있습니다.
- JWT 인증, 구조화 로깅, 메트릭, 오류 지표를 포함해 운영 환경에 맞게 확장할 수 있습니다.

## 주요 기능 / Features

- 블랙리스트 관리 API
  - 조회, 관리, 배치 처리, 시스템 상태 엔드포인트
  - `app/core/routes/api/blacklist/`에서 기능별 라우트 분리
- 수집 파이프라인
  - 수집 소스, 인증정보, 히스토리, 상태, 동기화, 수동 트리거 지원
  - `app/core/routes/api/collection/`에 세부 API 구성
- Fortinet 통합
  - Fortinet 등록 및 핵심 연동 라우트 제공
  - `app/core/routes/api/fortinet/`, `fortinet_register.py`
- 웹 운영 화면
  - 홈, 수집, 수집 로그, 세션, 설정, 통합, 모니터링 대시보드
- 인증 및 권한 기반 보호
  - JWT 서비스, 인증 미들웨어, 데코레이터 구조
- 모니터링
  - 캐시 메트릭, 오류 메트릭, 시스템/API 메트릭 라우트
- 배포 친화 구조
  - Dockerfile, entrypoint, Makefile 기반 개발/운영 명령 제공

English: Features include blacklist APIs, source collection, Fortinet
integration, dashboards, JWT-based auth, metrics, logging, and Docker support.

## 패키지 구성 / Package Contents

실제 최상위 레이아웃은 다음과 같습니다.

```text
/
├── AGENTS.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── Makefile
├── OWNERS
├── README.md
├── VERSION
├── commitlint.config.js
├── mypy.ini
├── pyproject.toml
└── app/
    ├── Dockerfile
    ├── entrypoint.sh
    ├── requirements.txt
    ├── run_app.py
    ├── deployment_validation.py
    ├── core/
    ├── templates/
    └── utils/
```

핵심 애플리케이션 코드는 `app/` 아래에 있습니다.

- `app/run_app.py`: 애플리케이션 실행 진입점
- `app/core/app.py`: 웹 애플리케이션 생성 및 라우팅 결합 지점
- `app/core/config.py`: 런타임 설정
- `app/core/auth_manager.py`: 인증 관리자
- `app/core/routes/`: 웹, API, 프록시, 시스템, WebSocket 라우트
- `app/core/routes/api/`: 기능별 REST API
- `app/core/monitoring/`: 메트릭 수집 및 오류 지표
- `app/templates/`: 운영자용 HTML 화면
- `app/utils/`: 구조화 로깅 및 로그 로테이션 유틸리티

English: The repository is centered on the `app/` Python service with
supporting quality, contribution, and ownership files at the root.

## 처음 읽을 파일 / First Files to Read

처음 참여하는 개발자 또는 운영자는 아래 순서로 읽는 것을 권장합니다.

1. [`app/core/app.py`](app/core/app.py)  
   애플리케이션 조립 방식과 라우트 등록 흐름을 확인합니다.
2. [`app/core/config.py`](app/core/config.py)  
   환경 변수와 설정 기본값을 확인합니다.
3. [`app/core/routes/api/`](app/core/routes/api/)  
   외부 클라이언트가 사용하는 API 표면을 확인합니다.
4. [`app/templates/`](app/templates/)  
   운영자 웹 화면의 기능 범위를 확인합니다.
5. [`Makefile`](Makefile)  
   개발, 테스트, 배포, 검증 명령을 확인합니다.
6. [`CONTRIBUTING.md`](CONTRIBUTING.md)  
   커밋, 리뷰, 기여 절차를 확인합니다.
7. [`OWNERS`](OWNERS)  
   코드 소유자와 리뷰 담당자를 확인합니다.

English: Start with the application factory, configuration, route modules,
templates, Makefile, contribution guide, and owners file.

## 아키텍처 / Architecture

서비스는 웹 UI, REST API, 인증, 수집, Fortinet 통합, 모니터링 계층으로 나뉩니다.

### 주요 구성 요소

- 애플리케이션 코어
  - `app/core/app.py`
  - 앱 생성, 라우트 연결, 공통 미들웨어 적용을 담당합니다.
- 인증 계층
  - `app/core/auth/`
  - JWT 발급/검증, 인증 미들웨어, 라우트 보호 데코레이터를 제공합니다.
- API 라우트
  - `app/core/routes/api/`
  - 블랙리스트, 수집, 대시보드, 데이터베이스, 설정, 시스템 API를 제공합니다.
- 웹 라우트와 템플릿
  - `app/core/routes/web_routes.py`
  - `app/templates/`
  - 운영자가 브라우저에서 사용하는 화면을 렌더링합니다.
- 모니터링
  - `app/core/monitoring/`
  - 캐시, 오류, 시스템 메트릭을 수집하고 API로 노출합니다.
- 운영 유틸리티
  - `app/utils/structured_logging.py`
  - `app/utils/log_rotation_manager.py`
  - 구조화 로그와 로그 로테이션을 지원합니다.

### 요청 흐름

1. 클라이언트가 웹 화면 또는 REST API로 요청합니다.
2. 인증 미들웨어가 필요한 라우트에서 JWT 또는 세션 상태를 검증합니다.
3. 라우트 모듈이 요청을 기능별 핸들러로 전달합니다.
4. 수집, 블랙리스트, Fortinet, 설정 또는 시스템 로직이 실행됩니다.
5. 응답은 JSON API 또는 HTML 템플릿으로 반환됩니다.
6. 로그, 오류 지표, 메트릭이 운영 확인용으로 기록됩니다.

English: Requests enter through web/API routes, pass auth where required,
execute domain handlers, and emit logs and metrics for operators.

## API 및 진입점 / API and Entry Points

### 애플리케이션 실행 진입점

- `app/run_app.py`
  - 로컬 또는 컨테이너에서 서비스를 시작하는 기본 진입점입니다.
- `app/entrypoint.sh`
  - Docker 컨테이너 시작 스크립트입니다.
- `app/Dockerfile`
  - 애플리케이션 컨테이너 이미지 정의입니다.
- `app/deployment_validation.py`
  - 배포 전 환경과 설정 검증에 사용되는 유틸리티입니다.

### 웹 화면

대표 템플릿:

- `app/templates/index.html`: 홈 화면
- `app/templates/collection.html`: 수집 화면
- `app/templates/collection_logs.html`: 수집 로그
- `app/templates/integrations.html`: 외부 통합
- `app/templates/sessions.html`: 세션 관리
- `app/templates/settings.html`: 설정
- `app/templates/monitoring/dashboard.html`: 모니터링 대시보드

### REST API 영역

주요 API 모듈:

- `analytics.py`: 분석 API
- `auth_routes.py`: 인증 API
- `core_api.py`: 공통 API
- `dashboard_api.py`: 대시보드 API
- `database_api.py`: 데이터베이스 관련 API
- `error_metrics_api.py`: 오류 지표 API
- `settings_api.py`: 설정 API
- `system_api.py`: 시스템 API
- `migration.py`: 마이그레이션 관련 API
- `fortinet_register.py`: Fortinet 등록 API

기능별 하위 API:

- `api/blacklist/`: 블랙리스트 배치, 수집, 관리, 시스템 API
- `api/collection/`: 수집 소스, 인증정보, 상태, 이력, 동기화, 트리거 API
- `api/fortinet/`: Fortinet 핵심 연동 API
- `api/monitoring/`: 메트릭 API

English: The service exposes HTML dashboards and REST APIs grouped by
auth, blacklist, collection, Fortinet, system, settings, and monitoring.

## 빠른 시작 / Quick Start

### 1. 요구사항

권장 환경:

- Python 3.11
- Docker 및 Docker Compose
- `make`
- `pip`
- 테스트 실행 시 `pytest`
- 기여 시 `pre-commit`, `ruff`, `mypy`

### 2. 저장소 준비

```bash
git clone <repository-url>
cd <repository-directory>
```

`<repository-url>`과 `<repository-directory>`는 사용하는 배포 위치에 맞게 바꾸세요.

### 3. Python 의존성 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
```

### 4. 로컬 실행

```bash
python app/run_app.py
```

기본 개발 포트는 Makefile 메시지 기준 `2542`가 사용됩니다.
환경에서 `PORT`를 지정하면 해당 포트를 사용하도록 구성할 수 있습니다.

```bash
PORT=2542 python app/run_app.py
```

### 5. Docker 기반 개발 실행

Makefile은 Docker Compose 기반 개발 명령을 제공합니다.

```bash
make dev
```

주의: Makefile은 `deploy/docker-compose.yml` 및 `deploy/.env`를 참조합니다.
현재 체크아웃에 `deploy/` 파일이 제공되지 않은 경우,
운영 배포 패키지 또는 환경별 설정을 먼저 준비해야 합니다.

English: Install Python dependencies, run `python app/run_app.py`, or use
`make dev` when the deployment compose files are available.

## 설정 / Configuration

설정은 `app/core/config.py`와 런타임 환경 변수에서 관리됩니다.
정확한 변수명과 기본값은 해당 파일을 기준으로 확인하세요.

일반적으로 준비해야 하는 설정 범주:

- 서버
  - 포트, 호스트, 디버그 여부
- 인증
  - JWT 비밀키, 토큰 만료 시간, 관리자 계정 또는 외부 인증 설정
- 수집
  - 블랙리스트 소스 URL
  - 소스별 인증정보
  - 동기화 주기와 타임아웃
- Fortinet 통합
  - 장비 또는 관리 API 엔드포인트
  - 인증정보
  - 등록 정책
- 데이터 저장소
  - 데이터베이스 연결 정보 또는 파일 경로
- 로깅
  - 로그 레벨
  - 로그 파일 위치
  - 로테이션 정책
- 모니터링
  - 메트릭 활성화 여부
  - 오류 지표 보관 정책

민감정보는 코드에 커밋하지 마세요.
환경 변수, 시크릿 매니저, 또는 배포 시스템의 secret 기능을 사용하세요.

English: Configuration is controlled by `app/core/config.py` and environment
variables. Keep credentials outside source control.

## 명령어 / Commands

Makefile은 운영자가 자주 쓰는 명령을 제공합니다.
사용 가능한 전체 명령은 아래로 확인합니다.

```bash
make help
```

대표 명령:

```bash
make dev          # 개발 환경 시작
make dev-no-build # 기존 이미지로 빠르게 시작
make dev-prod     # 프로덕션 유사 환경 시작
make logs         # 서비스 로그 확인
make health       # 헬스체크 실행
make test         # 테스트 실행
make clean        # 생성물 정리
make restart      # 서비스 재시작
make verify       # 기본 검증 실행
make verify-all   # 전체 검증 실행
```

코드 품질 관련 명령:

```bash
make verify-lint
make verify-types
make verify-secrets
make verify-pre-commit
make verify-quick
```

Git hook 설정:

```bash
make setup-hooks
```

`setup-hooks`는 Python pre-commit hook과 commit message 검증을 설치합니다.
Makefile에는 프론트엔드 hook 설치 명령도 포함되어 있으므로,
현재 체크아웃에 관련 디렉터리가 없으면 환경에 맞게 조정하세요.

English: Use `make help` as the source of truth for local command names.

## 로컬 개발 / Local Development

### 개발 루프

권장 개발 흐름:

1. 가상환경을 활성화합니다.
2. `pip install -r app/requirements.txt`를 실행합니다.
3. 변경 전 `make test` 또는 관련 pytest 명령을 실행합니다.
4. 기능을 수정합니다.
5. `ruff`, `mypy`, `pytest`를 실행합니다.
6. 변경 내용을 작은 단위로 커밋합니다.

### 코드 스타일

`pyproject.toml` 기준:

- Python 대상 버전: `py311`
- Ruff line length: `120`
- Ruff lint 선택: `E`, `F`, `W`
- 일부 `__init__.py`와 서비스 모듈에는 import 순서 관련 예외가 있습니다.

직접 실행 예시:

```bash
ruff check app
mypy app
```

### 커밋 규칙

`commitlint.config.js`가 포함되어 있습니다.
커밋 메시지는 Conventional Commits 형식을 따르는 것을 권장합니다.

예시:

```text
feat(collection): add source sync status endpoint
fix(auth): reject expired jwt tokens
test(blacklist): cover batch import validation
docs: update local development guide
```

English: Development uses Python 3.11, Ruff, mypy, pytest, pre-commit,
and conventional commit checks.

## 테스트 / Testing

`pyproject.toml`의 pytest 설정:

- 테스트 경로: `tests`
- 테스트 파일: `test_*.py`
- 테스트 클래스: `Test*`
- 테스트 함수: `test_*`
- 기본 옵션: `-v --tb=short`

테스트 마커:

- `unit`: 외부 의존성이 없는 단위 테스트
- `integration`: 서비스 의존성이 필요한 통합 테스트
- `security`: 보안 관련 테스트
- `db`: 데이터베이스 테스트
- `api`: API 엔드포인트 테스트

실행 예시:

```bash
pytest
pytest -m unit
pytest -m api
pytest -m "not integration"
```

Makefile을 사용할 수 있으면:

```bash
make test
```

테스트 디렉터리가 현재 체크아웃에 없거나 별도 패키지로 제공되는 경우,
테스트 자산을 먼저 동기화한 뒤 실행하세요.

English: Pytest is configured for unit, integration, security, database,
and API endpoint tests.

## 운영 관찰성 / Observability

서비스는 운영 확인을 위해 다음 구성 요소를 제공합니다.

- 구조화 로깅
  - `app/utils/structured_logging.py`
  - 로그 필드 일관성을 유지해 검색과 분석을 쉽게 합니다.
- 로그 로테이션
  - `app/utils/log_rotation_manager.py`
  - 장기 실행 환경에서 로그 파일 크기와 보관을 관리합니다.
- 오류 메트릭
  - `app/core/monitoring/error_metrics.py`
  - 오류 발생 추세와 API 실패 상태를 추적합니다.
- 캐시 메트릭
  - `app/core/monitoring/cache_metrics.py`
  - 캐시 사용 상태와 성능 지표를 추적합니다.
- 메트릭 API
  - `app/core/routes/api/monitoring/metrics.py`
  - 운영 대시보드 또는 외부 모니터링에서 사용할 수 있습니다.
- 대시보드
  - `app/templates/monitoring/dashboard.html`
  - 브라우저에서 시스템 상태를 확인합니다.

운영 중 우선 확인 순서:

1. `make health`
2. `make logs`
3. `/monitoring`
4. `/api/system/*`
5. 오류 메트릭 API

English: Logs, health checks, dashboards, and metrics APIs are the primary
operator-facing observability surfaces.

## 보안 참고 / Security Notes

이 서비스는 블랙리스트와 보안 장비 연동 정보를 다룰 수 있으므로,
운영 환경에서는 아래 항목을 반드시 확인하세요.

- JWT secret과 외부 시스템 인증정보를 안전하게 보관합니다.
- 기본 관리자 계정이나 개발용 토큰을 운영에 사용하지 않습니다.
- Fortinet 또는 외부 보안 장비 API 접근 권한을 최소화합니다.
- 로그에 토큰, 비밀번호, API key가 남지 않도록 설정합니다.
- 수집 소스 URL과 파일 입력을 검증합니다.
- 통합 테스트와 보안 테스트를 배포 전 실행합니다.
- 공개 네트워크에 직접 노출하는 경우 TLS와 접근 제어를 적용합니다.

English: Treat credentials, blacklist data, and network device integration
settings as sensitive operational data.

## 기여 / Contributing

기여 절차는 [`CONTRIBUTING.md`](CONTRIBUTING.md)를 따릅니다.

일반 원칙:

- 작은 변경 단위로 PR을 만듭니다.
- 기능 변경에는 테스트를 추가합니다.
- API 동작 변경은 문서와 예시를 함께 갱신합니다.
- 운영 설정 또는 보안 동작 변경은 리뷰어에게 명확히 알립니다.
- 커밋 메시지는 Conventional Commits 형식을 사용합니다.

권장 검증:

```bash
ruff check app
mypy app
pytest
```

또는 Makefile이 준비된 환경에서는:

```bash
make verify-all
```

English: See the contribution guide and run lint, type checks, and tests
before submitting changes.

## 유지보수 / Maintainers

유지보수자와 코드 소유권은 [`OWNERS`](OWNERS)를 확인하세요.

도움이 필요할 때:

- 사용법 또는 개발 절차: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- 변경 이력: [`CHANGELOG.md`](CHANGELOG.md)
- 릴리스/버전 확인: [`VERSION`](VERSION)
- 코드 소유자 확인: [`OWNERS`](OWNERS)

English: Maintainers and review ownership are defined in `OWNERS`.

## 추가 문서 / Further Documentation

- [`CHANGELOG.md`](CHANGELOG.md): 변경 이력
- [`CONTRIBUTING.md`](CONTRIBUTING.md): 기여 가이드
- [`LICENSE`](LICENSE): 라이선스
- [`VERSION`](VERSION): 현재 버전
- [`pyproject.toml`](pyproject.toml): 테스트 및 Ruff 설정
- [`mypy.ini`](mypy.ini): 타입 검사 설정
- [`Makefile`](Makefile): 개발/운영 명령

English: These files provide detailed release, contribution, license,
versioning, testing, typing, and command information.

## 라이선스 / License

라이선스 정보는 [`LICENSE`](LICENSE)를 확인하세요.

English: See `LICENSE` for the project license.