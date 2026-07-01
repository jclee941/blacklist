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

1. 외부 위협 인텔 소스 → `app/core/routes/api/collection/sources.py` 가 정의한 어댑터가 IP·도메인·URL을 수집
2. 정규화·중복 제거 → 중앙 블랙리스트 (`app/core/routes/api/blacklist/`) 에 적재
3. 동기화 트리거 → `collection/sync.py`, `collection/trigger.py` 가 배치·수동·예약 실행을 분기
4. 외부 장비 푸시 → `fortinet/core.py`, `fortinet_register.py` 가 REST API 로 주소 객체·그룹을 반영
5. 운영 가시화 → `monitoring/metrics.py`, `dashboard_api.py`, `monitoring/dashboard.html` 로 지표·이력 노출
6. 실시간 채널 → `websocket_routes.py` 가 수집·동기화·배포 이벤트를 콘솔에 푸시

---

## Purpose · 프로젝트 목적

이 저장소는 다음 세 가지 책임을 하나의 서비스로 묶습니다.

- **수집 (Collection)**: 다수의 위협 인텔리전스 피드를 플러그인 형태로 등록·실행
- **관리 (Blacklist)**: 수집 결과를 IP·도메인·URL 별로 통합·검색·정책화
- **배포 (Deployment)**: 변경분을 Fortinet 등 외부 보안 장비로 자동 반영

운영자는 별도 스크립트 없이 웹 콘솔에서 소스 등록, 수동 동기화, Fortinet 대상 관리, 로그·지표 확인을 모두 처리할 수 있습니다.

---

## Features · 주요 기능

| 영역 | 제공 기능 | 관련 모듈 |
| --- | --- | --- |
| 위협 인텔 수집 | 소스 등록·자격증명 관리·스케줄·수동 트리거·이력 | `app/core/routes/api/collection/` |
| 블랙리스트 | IP·도메인·URL 통합 검색, 배치 처리, 시스템 정책 | `app/core/routes/api/blacklist/` |
| Fortinet 연동 | 주소 객체·주소 그룹 등록·갱신, 대상 디바이스 자격증명 | `app/core/routes/api/fortinet/`, `fortinet_register.py` |
| 웹 콘솔 | Jinja2 기반 대시보드·세션·통합·설정 화면 | `app/templates/` |
| REST API | 라우트 그룹별 모듈화, JWT 인증 미들웨어 | `app/core/routes/api/`, `app/core/auth/` |
| WebSocket | 수집·동기화·배포 이벤트 실시간 스트림 | `app/core/routes/websocket_routes.py` |
| 모니터링 | 캐시·에러·일반 메트릭, 메트릭 API | `app/core/monitoring/`, `routes/api/monitoring/` |
| 인증 | JWT 발급·검증, 데코레이터·미들웨어 | `app/core/auth/` |
| 운영 도구 | 구조화 로깅, 로그 회전, 배포 전 검증 | `app/utils/`, `app/deployment_validation.py` |
| 프록시 | 외부 호출 중계 라우트 | `app/core/routes/proxy_routes.py` |

---

## Architecture · 아키텍처

### 요청 흐름 (Request Flow)

| 단계 | 컴포넌트 | 역할 |
| --- | --- | --- |
| 1 | `app/run_app.py` / `entrypoint.sh` | 부트스트랩, 환경 로드, 앱 팩토리 호출 |
| 2 | `app/core/app.py` | Flask/WSGI 앱 생성, 블루프린트 등록 |
| 3 | `app/core/auth/middleware.py` | JWT 검증, 세션 주입 |
| 4 | `app/core/routes/*` | 웹·API·프록시·WebSocket 라우팅 |
| 5 | `app/core/routes/api/*` | 도메인 로직 (수집·블랙리스트·Fortinet·설정) |
| 6 | `app/core/monitoring/*` | 메트릭·캐시·에러 카운터 기록 |
| 7 | `app/utils/structured_logging.py` | JSON 구조화 로그 출력 |

### 라우트 그룹 (Route Map)

| 그룹 | 파일 | 설명 |
| --- | --- | --- |
| Web | `app/core/routes/web_routes.py` | 대시보드·세션·설정·통합 페이지 렌더 |
| API root | `app/core/routes/api_routes.py` | `/api/*` 진입점 |
| System | `app/core/routes/system_routes.py` | 헬스체크·시스템 정보 |
| Proxy | `app/core/routes/proxy_routes.py` | 외부 호스트 중계 |
| WebSocket | `app/core/routes/websocket_routes.py` | 실시간 이벤트 채널 |
| Collection | `app/core/routes/collection_routes_simple.py` + `api/collection/` | 수집 라이프사이클 |
| Blacklist | `api/blacklist/` | 검색·배치·정책 |
| Fortinet | `api/fortinet/` + `fortinet_register.py` | 디바이스 배포·등록 |
| Monitoring | `api/monitoring/metrics.py` | 메트릭 API |

### 템플릿 (Templates)

| 화면 | 파일 |
| --- | --- |
| 메인 | `app/templates/index.html` |
| 컬렉션 | `app/templates/collection.html`, `collection_logs.html` |
| 통합 | `app/templates/integrations.html` |
| 세션 | `app/templates/sessions.html` |
| 설정 | `app/templates/settings.html` |
| 모니터링 | `app/templates/monitoring/dashboard.html` |

---

## Directory Layout · 디렉터리 구조

```text
.
├── AGENTS.md                # 저장소 작업 가이드
├── CHANGELOG.md             # 변경 이력
├── CONTRIBUTING.md          # 기여 절차
├── LICENSE                  # 라이선스
├── Makefile                 # 빌드·배포·검증 명령
├── OWNERS                   # 책임자 목록
├── README.md                # 본 문서
├── VERSION                  # 시맨틱 버전
├── commitlint.config.js     # 커밋 컨벤션
├── mypy.ini                 # 정적 타입 설정
├── pyproject.toml           # 의존성·도구 설정
└── app/
    ├── Dockerfile           # 컨테이너 빌드 정의
    ├── deployment_validation.py  # 배포 전 검증 스크립트
    ├── entrypoint.sh        # 컨테이너 시작점
    ├── requirements.txt     # 런타임 의존성
    ├── run_app.py           # 로컬 진입점
    ├── core/
    │   ├── app.py           # 앱 팩토리
    │   ├── auth_manager.py  # 인증 매니저
    │   ├── config.py        # 설정 로더
    │   ├── dashboard.py     # 대시보드 집계
    │   ├── testing_app.py   # 테스트용 앱
    │   ├── auth/            # JWT·데코레이터·미들웨어
    │   ├── monitoring/      # 메트릭·캐시·에러
    │   └── routes/          # 웹·API·WebSocket 라우트
    ├── templates/           # Jinja2 템플릿
    └── utils/               # 로깅·로그 회전
```

---

## API & Entry Points · 진입점

### 애플리케이션 부트스트랩

| 진입점 | 용도 | 호출 |
| --- | --- | --- |
| `app/run_app.py` | 로컬 개발 실행 | `python app/run_app.py` |
| `app/entrypoint.sh` | 컨테이너 시작 | Docker 가 자동 실행 |
| `app/core/app.py` | 앱 팩토리 | 다른 스크립트에서 import |
| `app/deployment_validation.py` | 배포 전 점검 | `python app/deployment_validation.py` |

### 외부 노출 엔드포인트 (대표)

| 메서드 | 경로 | 라우트 | 설명 |
| --- | --- | --- | --- |
| `GET` | `/` | `web_routes` | 메인 대시보드 |
| `GET` | `/health` | `system_routes` | 헬스체크 |
| `POST` | `/api/auth/login` | `api/auth_routes` | JWT 발급 |
| `GET` | `/api/collection/sources` | `api/collection/sources` | 소스 목록 |
| `POST` | `/api/collection/sync` | `api/collection/sync` | 수동 동기화 |
| `GET` | `/api/blacklist/search` | `api/blacklist/core` | 블랙리스트 검색 |
| `POST` | `/api/fortinet/register` | `fortinet_register` | Fortinet 디바이스 등록 |
| `GET` | `/api/monitoring/metrics` | `api/monitoring/metrics` | 메트릭 조회 |
| `WS` | `/ws` | `websocket_routes` | 실시간 이벤트 |

> 경로는 실제 라우트 정의에 따라 추가·변경될 수 있습니다. 정확한 목록은 `app/core/routes/` 하위 모듈에서 확인하세요.

---

## Quickstart · 빠른 시작

### 1) 사전 요구 사항

- Python `3.11+`
- Docker + Docker Compose
- Make (선택, 명령 단순화용)

### 2) 환경 변수 준비

`deploy/.env` 파일을 생성하고 운영 환경 값을 채워 넣습니다. Compose 가 자동으로 주입합니다.

```env
ENV=development
PORT=2542
# Fortinet 대상·자격증명, 위협 인텔 소스 키 등 추가
```

### 3) 로컬 실행 (개발 모드)

```bash
python app/run_app.py
# 브라우저: http://localhost:2542
```

### 4) Docker Compose 실행 (권장)

```bash
make dev          # 빌드 + 핫리로드
make dev-no-build # 기존 이미지 재사용
make dev-prod     # 운영 유사 (오버라이드 없음)
```

### 5) 배포 전 검증

```bash
make verify       # lint + type + secret + pre-commit 종합
make verify-quick # 빠른 점검
```

---

## Configuration · 설정

| 키 | 출처 | 설명 |
| --- | --- | --- |
| `ENV` | `deploy/.env` | `development` / `production` 등 |
| `PORT` | `deploy/.env` | 웹 리스너 포트, 기본 `2542` |
| Fortinet 자격증명 | `app/core/routes/api/fortinet/` | 디바이스 호스트·토큰 |
| 소스 자격증명 | `app/core/routes/api/collection/credentials.py` | 위협 인텔 API 키 |
| 로깅 | `app/utils/structured_logging.py` | JSON 포맷·레벨 |
| 로그 회전 | `app/utils/log_rotation_manager.py` | 사이즈·시간 정책 |
| 도구 규칙 | `pyproject.toml`, `mypy.ini`, `commitlint.config.js` | 린트·타입·커밋 컨벤션 |

`deploy/.env` 는 저장소에 커밋하지 마세요. 비밀 값은 별도 시크릿 매니저 또는 CI 환경 변수로 주입합니다.

---

## Commands · 명령어 (Makefile)

| 명령 | 설명 |
| --- | --- |
| `make help` | 사용 가능한 타겟 목록 출력 |
| `make setup-hooks` | pre-commit·commitlint·husky 훅 설치 |
| `make dev` | 개발 환경 (빌드 + 핫리로드) 기동 |
| `make dev-no-build` | 기존 이미지로 기동 |
| `make dev-prod` | 운영 유사 환경 (오버라이드 없음) |
| `make dev-app` | 앱 서비스만 재시작 |
| `make build` | 컨테이너 이미지 빌드 |
| `make up` / `make down` | 스택 기동 / 종료 |
| `make logs` | 컨테이너 로그 스트림 |
| `make restart` | 스택 재기동 |
| `make health` | 헬스체크 호출 |
| `make test` | 테스트 실행 (pytest) |
| `make verify` | 린트·타입·시크릿·pre-commit 종합 검증 |
| `make verify-lint` | Ruff 린트 |
| `make verify-types` | mypy 정적 타입 |
| `make verify-secrets` | 시크릿 누출 점검 |
| `make verify-pre-commit` | pre-commit 훅 전체 실행 |
| `make verify-quick` | 빠른 검증 |
| `make verify-all` | 전체 검증 |
| `make deploy` | 배포 |
| `make release` | 릴리스 태그 생성 |
| `make release-dry` | 릴리스 드라이런 |
| `make clean` | 로컬 산출물·중간 캐시 정리 |

> 각 타겟의 상세 주석은 `Makefile` 의 `## .*` 코멘트에 있습니다. `make help` 가 이를 표로 정리해 출력합니다.

---

## Local Development · 로컬 개발

1. 저장소를 클론하고 의존성을 설치합니다.

   ```bash
   pip install -r app/requirements.txt
   pip install pre-commit
   pre-commit install --install-hooks
   pre-commit install --hook-type commit-msg
   ```

2. `deploy/.env` 를 작성한 뒤 `python app/run_app.py` 로 기동합니다.

3. 코드 스타일은 Ruff (line length 120), 타입은 mypy, 커밋은 Commitlint (Conventional Commits) 를 따릅니다.

4. PR 전 `make verify-quick` 으로 자기 점검을 권장합니다.

5. 프런트엔드 작업이 있다면 `frontend/` 디렉터리에서 npm 스크립트를 사용하며, `make setup-hooks` 가 husky 까지 함께 설치합니다.

---

## Testing · 테스트

- 테스트 러너: **pytest** (`pyproject.toml` 의 `[tool.pytest.ini_options]`)
- 경로: `tests/`
- 마커: `unit`, `integration`, `security`, `db`, `api`
- 기본 옵션: `-v --tb=short`

```bash
make test                              # 전체 실행
pytest -m unit                         # 단위 테스트만
pytest -m integration                  # 통합 테스트 (서비스 의존)
pytest -m security                     # 보안 점검
```

> 통합·보안 마커는 외부 서비스 (DB, Fortinet, 위협 인텔 API 등) 가 필요할 수 있습니다. 로컬 검증은 `unit` 마커 위주로 시작하세요.

---

## Deployment · 배포

1. 환경 변수 시크릿 준비 (`deploy/.env` 또는 시크릿 매니저)
2. `make verify` 로 린트·타입·시크릿·pre-commit 통과 확인
3. `make build` 로 이미지 빌드
4. `make deploy` 로 스택 배포
5. `make health` 로 헬스체크 확인
6. 로그·메트릭은 `app/utils/structured_logging.py` 와 `/api/monitoring/metrics` 로 확인

컨테이너 네트워크에서 Fortinet 디바이스는 별도 VLAN/시크릿으로 접근합니다. 실제 대상 IP·자격증명은 `deploy/.env` 가 아닌 시크릿 매니저에서 주입하세요.

---

## Troubleshooting · 문제 해결

| 증상 | 확인 경로 | 조치 |
| --- | --- | --- |
| 502/연결 실패 | `make logs` | `app/core/routes/proxy_routes.py` 의 대상 호스트·포트 점검 |
| 인증 실패 | `app/core/auth/jwt_service.py` | 시크릿 키·만료 시각 확인 |
| 동기화 미반영 | `app/core/routes/api/collection/sync.py` | 소스 자격증명·이력(`history.py`) 확인 |
| Fortinet 배포 실패 | `app/core/routes/api/fortinet/core.py` | 디바이스 토큰·주소 그룹 한도 확인 |
| 로그 누락 | `app/utils/log_rotation_manager.py` | 회전 정책·디스크 용량 점검 |
| 메트릭 비어 있음 | `app/core/monitoring/metrics.py` | 카운터 미들웨어 등록 여부 확인 |

---

## Contributing · 기여

- 절차: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- 작업 가이드: [`AGENTS.md`](AGENTS.md)
- 책임자: [`OWNERS`](OWNERS)
- 변경 이력: [`CHANGELOG.md`](CHANGELOG.md)
- 커밋 컨벤션: `commitlint.config.js` (Conventional Commits)
- PR 전 `make verify-quick` 통과를 권장합니다

---

## Maintainers · 책임자

저장소 책임자는 [`OWNERS`](OWNERS) 파일을 참고하세요. 운영 문의는 [`CONTRIBUTING.md`](CONTRIBUTING.md) 의 채널을 이용합니다.

---

## License · 라이선스

[`LICENSE`](LICENSE) 파일의 조항을 따릅니다.

---

## Further Documentation · 추가 문서

- [`AGENTS.md`](AGENTS.md) — 저장소 작업 가이드
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — 기여 절차
- [`CHANGELOG.md`](CHANGELOG.md) — 변경 이력
- [`OWNERS`](OWNERS) — 책임자 목록
- [`Makefile`](Makefile) — 명령어 정의
- [`app/core/routes/api/collection/`](app/core/routes/api/collection/) — 수집 API 상세
- [`app/core/routes/api/blacklist/`](app/core/routes/api/blacklist/) — 블랙리스트 API 상세
- [`app/core/routes/api/fortinet/`](app/core/routes/api/fortinet/) — Fortinet 연동 상세
- [`app/core/monitoring/`](app/core/monitoring/) — 메트릭·캐시·에러 수집
- [`app/utils/`](app/utils/) — 로깅·로그 회전
- [`app/templates/`](app/templates/) — 웹 콘솔 화면 정의