# Blacklist Management Service

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED.svg)](https://docs.docker.com/compose/)
[![Ruff](https://img.shields.io/badge/lint-ruff-orange.svg)](https://docs.astral.sh/ruff/)
[![Status](https://img.shields.io/badge/status-production--ready-brightgreen.svg)](#status)

## 개요 / Overview

**블랙리스트 수집·동기화·배포를 한 곳에서 관리하는 웹 서비스입니다.**
외부 위협 인텔리전스 소스에서 IP 블랙리스트를 주기적으로 수집하고, 정규화 후 Fortinet 방화벽으로 배포하며, JWT 기반 인증과 Prometheus 호환 메트릭을 함께 제공합니다.

A web-based service that **collects, normalizes, and deploys IP blacklists**.
It periodically pulls threat-intel feeds, normalizes entries, syncs them to Fortinet
firewalls, and exposes JWT-authenticated APIs with Prometheus-style metrics.

---

## 빠른 상태 / Quick Status

| 항목 / Item | 값 / Value |
| --- | --- |
| Status | Production-ready |
| Runtime | Python 3.11 |
| Web stack | Flask + Jinja2 templates |
| Auth | JWT (HS256) + decorator-based |
| Storage | SQLAlchemy (Postgres/MySQL) |
| Packaging | Docker + docker compose |
| Default port | `2542` |
| Entry point | `app/run_app.py` |
| Health endpoint | `GET /health` |
| Metrics endpoint | `GET /metrics` |
| Config | env-driven via `app/core/config.py` |

---

## 운영 흐름 / Operator Flow

1. 운영자가 `make dev`로 컨테이너 스택을 기동한다.
2. 앱이 `PORT`(기본 2542)에서 웹 UI와 REST API를 동시에 노출한다.
3. `/login`에서 자격증명을 입력하고 JWT를 발급받는다.
4. 이후 모든 `/api/*` 호출은 `Authorization: Bearer <token>` 헤더를 사용한다.
5. `Collection` 모듈이 외부 소스에서 블랙리스트를 주기적으로 수집한다.
6. `Blacklist` 모듈이 정규화된 엔트리를 저장·조회·배치 처리한다.
7. `Fortinet` 어댑터가 변경분을 대상 방화벽으로 푸시한다.
8. `Monitoring` 모듈이 메트릭·에러율·캐시 상태를 대시보드와 `/metrics`로 노출한다.

---

## 목차 / Contents

- [패키지 구성 / Package Contents](#패키지-구성--package-contents)
- [먼저 읽을 파일 / First Files to Read](#먼저-읽을-파일--first-files-to-read)
- [API 및 진입점 / API & Entry Points](#api-및-진입점--api--entry-points)
- [빠른 시작 / Quickstart](#빠른-시작--quickstart)
- [명령 레퍼런스 / Command Reference](#명령-레퍼런스--command-reference)
- [로컬 개발 / Local Development](#로컬-개발--local-development)
- [테스트 / Testing](#테스트--testing)
- [운영·관측 / Operations & Observability](#운영관측--operations--observability)
- [기여 / Contributing](#기여--contributing)
- [메인테이너 / Maintainers](#메인테이너--maintainers)
- [라이선스 / License](#라이선스--license)

---

## 패키지 구성 / Package Contents

부트스트랩 / Bootstrap

- `app/run_app.py` — 엔트리포인트. `create_app()` 팩토리와 헬스체크 라우트 제공.
- `app/entrypoint.sh` — 컨테이너 부트스트랩 스크립트.
- `app/deployment_validation.py` — 배포 전 환경 검증.
- `app/Dockerfile` — 컨테이너 이미지 빌드 정의.

코어 / Core

- `app/core/app.py` — Flask 앱 팩토리, 블루프린트 등록, 미들웨어 와이어링.
- `app/core/config.py` — 환경 변수 기반 설정 객체.
- `app/core/auth_manager.py` — 로그인·세션·토큰 헬퍼.
- `app/core/dashboard.py` — 대시보드 집계 로직.
- `app/core/testing_app.py` — 테스트 전용 앱 팩토리.

인증 / Auth

- `app/core/auth/jwt_service.py` — JWT 발급·검증·갱신.
- `app/core/auth/decorators.py` — `@require_auth`, `@require_role` 등.
- `app/core/auth/middleware.py` — 요청별 인증 미들웨어.

모니터링 / Monitoring

- `app/core/monitoring/metrics.py` — 카운터·히스토그램 등록.
- `app/core/monitoring/cache_metrics.py` — 캐시 적중률/지연.
- `app/core/monitoring/error_metrics.py` — 에러율·예외 분류.

라우트 / Routes

- `app/core/routes/web_routes.py` — HTML 페이지 라우트.
- `app/core/routes/api_routes.py` — API 블루프린트 등록기.
- `app/core/routes/proxy_routes.py` — 패스스루 프록시.
- `app/core/routes/system_routes.py` — 헬스·시스템 엔드포인트.
- `app/core/routes/websocket_routes.py` — 실시간 채널.

API 모듈 / API Modules

- `auth_routes.py` — 로그인·갱신·로그아웃.
- `blacklist/` — CRUD, 배치, 관리, 시스템 액션.
- `collection/` — 소스, 자격증명, 이력, 동기화 트리거.
- `fortinet/` — Fortinet 어댑터 코어.
- `database_api.py` — DB 마이그레이션·관리.
- `settings_api.py` — 런타임 설정 변경.
- `system_api.py` — 시스템 운영 액션.
- `analytics.py` — 분석 집계.
- `migration.py` — 스키마 마이그레이션 헬퍼.

프런트엔드 / Frontend

- `app/templates/*.html` — Jinja2 페이지 템플릿 (`index`, `sessions`, `collection`, `integrations`, `settings`, `dashboard`).

유틸리티 / Utilities

- `app/utils/structured_logging.py` — JSON 구조화 로깅.
- `app/utils/log_rotation_manager.py` — 로그 로테이션.

기타 / Misc

- `Makefile` — 모든 운영 명령의 진실 공급원.
- `pyproject.toml` — Ruff·pytest·마커 설정.
- `commitlint.config.js` — Conventional Commits 규약.
- `mypy.ini` — 타입 검사 설정.
- `VERSION`, `CHANGELOG.md` — 버전·변경 이력.

---

## 먼저 읽을 파일 / First Files to Read

1. `Makefile` — 운영 명령과 환경 변수 키 모음.
2. `app/run_app.py` — 앱 부트스트랩과 헬스체크 진입점.
3. `app/core/app.py` — 라우트·미들웨어 등록 흐름.
4. `app/core/config.py` — 환경 변수 키 전체 목록.
5. `app/core/auth/jwt_service.py` — 토큰 발급·검증 규약.

---

## API 및 진입점 / API & Entry Points

페이지 라우트 / Web Pages

- `/` — 랜딩 페이지
- `/login`, `/logout` — 인증 페이지
- `/dashboard` — 모니터링 대시보드
- `/sessions` — 세션·활동 목록
- `/integrations` — 외부 연동 상태
- `/settings` — 런타임 설정
- `/collection`, `/collection/logs` — 수집 작업 페이지

시스템 라우트 / System

- `GET /health` — 헬스체크
- `GET /metrics` — Prometheus 호환 메트릭

API 라우트 / API (모두 JWT 필요)

- `POST /api/auth/login`, `POST /api/auth/refresh`
- `/api/blacklist/*` — 블랙리스트 CRUD·배치·관리·시스템 액션
- `/api/collection/*` — 소스·자격·이력·동기화 트리거·상태
- `/api/fortinet/*` — Fortinet 동기화·상태
- `/api/database/*` — DB 마이그레이션·관리
- `/api/settings/*` — 런타임 설정 변경
- `/api/system/*` — 시스템 운영 액션
- `/api/analytics/*` — 분석 집계
- `/api/monitoring/*` — 메트릭 조회·리셋

WebSocket

- `/ws/*` — `websocket_routes.py`가 제공하는 실시간 채널.

---

## 빠른 시작 / Quickstart

### 사전 요구사항 / Prerequisites

- Docker 24+ 및 docker compose v2
- Python 3.11 (소스 직접 실행 시)
- 호스트에서 `PORT`(기본 2542) 사용 가능

### 환경 변수 / Environment

`deploy/.env`에 최소한 다음 키를 정의한다.

- `PORT` — 선택, 기본 `2542`
- `ENV` — 선택, `development` / `production`
- `JWT_SECRET` — 필수, HS256 서명 비밀
- `DB_URL` — 필수, SQLAlchemy 데이터베이스 URL
- `FORTINET_HOST`, `FORTINET_TOKEN` — Fortinet 연동 사용 시 필수
- 추가 키는 `app/core/config.py` 참조.

### 컨테이너 실행 / Run via Docker

```bash
make setup-hooks   # 1회만: pre-commit + husky
make dev           # hot reload 개발 스택 (build + up)
make dev-no-build  # 기존 이미지로 up
make dev-prod      # 운영 모드 (no override)
```

### 소스 직접 실행 / Run from Source

```bash
cd app
pip install -r requirements.txt
python run_app.py
```

### 첫 로그인 / First Login

1. `http://<host>:2542/login` 접속.
2. 관리자 계정으로 로그인해 JWT를 발급받는다.
3. 이후 API 호출 시 `Authorization: Bearer <token>` 헤더를 사용한다.

---

## 명령 레퍼런스 / Command Reference

- `make help` — 사용 가능한 타깃 목록 출력.
- `make setup-hooks` — pre-commit + husky 1회 설치.
- `make dev` — 개발 스택 (build + up, hot reload).
- `make dev-no-build` — 캐시된 이미지로 빠르게 up.
- `make dev-prod` — 운영 모드 컨테이너 (no override).
- `make dev-app` — app 서비스만 재기동.
- `make up` / `make down` — 스택 up / down.
- `make logs` — 컨테이너 로그 스트림.
- `make restart` — 전체 재기동.
- `make health` — 헬스체크 호출.
- `make test` — 테스트 스위트 실행.
- `make verify` / `verify-quick` — 린트·타입·시크릿 검증.
- `make verify-lint`, `verify-types`, `verify-secrets`, `verify-pre-commit` — 개별 검증.
- `make verify-all` — 전체 검증.
- `make release` / `release-dry` — 릴리스 생성 (dry-run 가능).
- `make clean` — 빌드 산출물 정리.

---

## 로컬 개발 / Local Development

- 린트: `ruff` (line-length 120, target py311). 무시 규칙은 `pyproject.toml` 참조.
- 타입: `mypy` (설정은 `mypy.ini`).
- 커밋 메시지: Conventional Commits, `commitlint` + husky로 강제.
- 시크릿 검사: pre-commit 훅에서 자동 수행.
- 핫 리로드: `make dev` 사용 시 볼륨 마운트로 코드 변경 자동 반영.
- 도메인별 노트는 각 디렉터리의 `AGENTS.md` 참조 (`app/`, `app/core/`, `app/core/auth/`, `app/core/monitoring/`, `app/core/routes/`, `app/core/routes/api/`, `app/core/routes/api/blacklist/`, `app/core/routes/api/collection/`, `app/core/routes/api/fortinet/`).

---

## 테스트 / Testing

```bash
make test
# 또는 마커 기반 실행
pytest -m unit
pytest -m integration
pytest -m security
pytest -m db
pytest -m api
```

마커 정의는 `pyproject.toml`의 `tool.pytest.ini_options.markers` 참조.

---

## 운영·관측 / Operations & Observability

- 로그: `app/utils/structured_logging.py`로 JSON 출력. `log_rotation_manager.py`가 로테이션 담당.
- 메트릭: `/metrics` Prometheus 호환. 카운터·히스토그램은 `app/core/monitoring/metrics.py`, 캐시 메트릭은 `cache_metrics.py`, 에러 메트릭은 `error_metrics.py`.
- 헬스체크: `make health` 또는 `GET /health`.
- 런타임 설정 변경: `/api/settings/*` 엔드포인트.

---

## 기여 / Contributing

기여 절차는 `CONTRIBUTING.md`를 따른다. PR 규칙과 이슈 템플릿은 저장소 표준을 따른다. 커밋 메시지는 Conventional Commits 규약을 준수한다.

---

## 메인테이너 / Maintainers

책임자 목록은 저장소 루트의 `OWNERS` 파일을 참조한다. 보안 이슈는 공개 채널 대신 비공개로 메인테이너에게 먼저 보고한다.

---

## 라이선스 / License

이 저장소는 저장소 내 `LICENSE` 파일의 조항에 따라 배포된다. 외부 배포 시 해당 라이선스 전문을 함께 제공해야 한다.

---

## 추가 문서 / Further Documentation

- `CHANGELOG.md` — 변경 이력.
- `VERSION` — 현재 시맨틱 버전.
- 도메인별 `AGENTS.md` — 컬렉션·블랙리스트·Fortinet·모니터링 모듈 노트.