# Blacklist Service / 블랙리스트 서비스

네트워크 차단·정책 데이터를 Fortigate 방화벽, Regtech 공시, 다중 소스에서 통합 수집하고 품질 검증 후 본 서비스 DB로 동기화하는 보안 운영 백엔드입니다. 본 저장소는 **Blacklist Service**의 핵심 컴포넌트인 `collector/` 패키지와 운영 도구 체인(Make, Docker Compose, pre-commit)을 제공합니다.

## 한눈에 보기

| 구분 | 상태 / 값 | 근거 |
|---|---|---|
| 언어 런타임 | Python 3.11 | `pyproject.toml` `target-version = "py311"` |
| 린트 / 타입 | ruff(line-length 120) + mypy | `pyproject.toml`, `mypy.ini` |
| 컨테이너 | Docker Compose 기반 개발/운영 | `Makefile` (`COMPOSE_FILE := deploy/docker-compose.yml`) |
| 프런트엔드 | Node.js + husky(pre-commit) | `Makefile` `setup-hooks` |
| 데이터 소스 | Fortigate(SSH), Regtech(HTTP/Excel), Multi-source | `collector/core/fortigate/`, `collector/core/regtech/`, `collector/core/multi_source/` |
| 보조 기능 | 정책 모니터링, 아카이브, 데이터 품질, 레이트 리밋 | `collector/core/*.py` |
| 스케줄러 | APScheduler 스타일 의존성·매니저 | `collector/scheduler/` |
| 외부 API | Enhanced Collection API | `collector/api/enhanced_collection_api.py` |
| 헬스체크 | 컨테이너 엔트리포인트 + health_server | `collector/entrypoint.sh`, `collector/health_server.py` |
| 테스트 | pytest(unit/integration/security/db/api) | `pyproject.toml` markers |
| 커밋 규칙 | Conventional Commits | `commitlint.config.js` |
| 배포 | `make release` / `release.sh` | `scripts/release.sh` |

## 운영 흐름 요약

1. 스케줄러(`collector/scheduler/manager.py`)가 등록된 잡을 트리거합니다.
2. 해당 소스별 Collector(`fortigate_collector.py`, `regtech_collector.py`, `multi_source_collector.py`)가 원천 시스템에서 데이터를 수집합니다.
3. `rate_limiter.py` → `validators.py` → `data_quality_manager.py` 순으로 품질을 검증합니다.
4. `database/service.py`의 쿼리/트랜잭션을 통해 메인 DB에 영속화하고, 필요 시 `archive_manager.py`가 원본을 보관합니다.
5. `policy_monitor.py`가 임계값 위반·변경 사항을 감지하여 운영 알림으로 전달합니다.
6. 외부 연동은 `collector/api/enhanced_collection_api.py`를 통해 즉시 수집 트리거를 제공합니다.

## 목차

- [기능 요약](#기능-요약)
- [아키텍처](#아키텍처)
- [저장소 구조](#저장소-구조)
- [빠른 시작](#빠른-시작)
- [설정](#설정)
- [명령어 레퍼런스](#명령어-레퍼런스)
- [Collector 패키지](#collector-패키지)
- [로컬 개발](#로컬-개발)
- [테스트](#테스트)
- [문제 해결 / 헬스체크](#문제-해결--헬스체크)
- [기여](#기여)
- [유지보수 및 라이선스](#유지보수-및-라이선스)

---

## 기능 요약

- **다중 소스 정책 수집**: Fortigate CLI/SSH, Regtech Excel/HTTP, 기타 멀티 소스 통합 인제스트.
- **수집 스케줄링**: 의존성 기반 잡 매니저와 운영 훅(`scheduler/operations.py`).
- **데이터 품질 관리**: 스키마 검증, 품질 점수, 자동 격리(`core/data_quality_manager.py`, `core/validators.py`).
- **레이트 리밋**: 외부 호출 보호(`core/rate_limiter.py`, `docs/collector/RATE-LIMITING.md`).
- **아카이브 관리**: 원본/스냅샷 보존 정책(`core/archive_manager.py`).
- **정책 모니터링**: 임계 위반·드리프트 감지(`core/policy_monitor.py`, `core/policy_monitor_support.py`).
- **즉시 수집 API**: 관리/백오피스에서 단발성 수집 트리거(`api/enhanced_collection_api.py`).
- **헬스 엔드포인트**: 컨테이너 라이브니스(`health_server.py`).
- **릴리스 자동화**: 시맨틱 버전 + 배포 스크립트(`scripts/release.sh`).
- **위키 동기화**: 사내 XWiki와 본 저장소 문서 동기화(`scripts/wiki-sync.sh`).

## 아키텍처

| 계층 | 디렉터리 / 파일 | 책임 |
|---|---|---|
| Entry | `collector/entrypoint.sh`, `collector/run_collector.py` | 컨테이너 시작, 메인 루프 |
| Scheduler | `collector/scheduler/{manager,operations,dependencies}.py` | 잡 트리거/실행 그래프 |
| Collectors | `collector/core/fortigate/`, `collector/core/regtech/`, `collector/core/multi_source/` | 소스별 어댑터 |
| Cross-cutting | `collector/core/{rate_limiter,validators,data_quality_manager,archive_manager,policy_monitor,policy_monitor_support}.py` | 횡단 품질/안전 로직 |
| Persistence | `collector/core/database/{service,queries}.py` | 트랜잭션·리포지토리 |
| API | `collector/api/enhanced_collection_api.py` | 운영 트리거 API |
| Health | `collector/health_server.py` | 컨테이너 헬스 응답 |
| Config / Errors | `collector/config.py`, `collector/exceptions.py` | 설정·예외 분류 |

**요청 흐름 (즉시 수집 API 기준)**

1. 운영 콘솔 → `enhanced_collection_api.py` 엔드포인트 호출.
2. API가 `Scheduler`에 즉시 실행 잡을 큐잉.
3. 대상 Collector(Fortigate/Regtech/Multi-source)가 원천 시스템 인증(`regtech/auth.py`, `fortigate/ssh_client.py`) 후 페이로드 수집.
4. `RateLimiter` → `Validators` → `DataQualityManager` 순서로 정책·품질 검증.
5. 통과 데이터는 `database/service.py`로 영속화, 실패는 격리 후 `archive_manager`로 보존.
6. `policy_monitor`가 변경/위반을 평가하여 후속 알림 훅 호출.

## 저장소 구조

본 README는 루트와 `collector/`, `docs/`, `scripts/`에 한정해 실제 트리를 반영합니다(존재하지 않는 디렉터리는 절대 추가하지 않음).

```text
.
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
├── collector/
│   ├── AGENTS.md
│   ├── Dockerfile
│   ├── RATE-LIMITING.md
│   ├── README.md
│   ├── __init__.py
│   ├── config.py
│   ├── entrypoint.sh
│   ├── exceptions.py
│   ├── health_server.py
│   ├── requirements.txt
│   ├── run_collector.py
│   ├── api/enhanced_collection_api.py
│   ├── core/
│   │   ├── archive_manager.py
│   │   ├── data_quality_manager.py
│   │   ├── fortigate_collector.py
│   │   ├── multi_source_collector.py
│   │   ├── policy_monitor.py
│   │   ├── policy_monitor_support.py
│   │   ├── rate_limiter.py
│   │   ├── regtech_collector.py
│   │   ├── regtech_excel.py
│   │   ├── regtech_parsers.py
│   │   ├── validators.py
│   │   ├── database/{queries.py,service.py}
│   │   ├── fortigate/{collector.py,parsers.py,ssh_client.py}
│   │   ├── multi_source/{collector.py,models.py,parsers.py}
│   │   └── regtech/{auth.py,collector.py,data_processor.py}
│   ├── scheduler/{dependencies.py,manager.py,operations.py}
│   └── utils/
├── docs/
│   ├── CLOUDFLARE_MIGRATION.md
│   ├── MONOREPO_STRUCTURE.md
│   ├── OPERATOR_MIGRATION_GUIDE.md
│   ├── README.md
│   ├── architecture.drawio
│   ├── deliverables/ (01~09 산출물 + index.md)
│   ├── testing/TEST-GUIDE-MAIN.md
│   └── wiki/ (Home, Architecture, API-Reference, Database-Schema, Deployment-Guide, Security, Service-Details, XWiki-Compatibility, _Sidebar)
└── scripts/
    ├── migrate_env_credentials_to_db.py
    ├── release.sh
    └── wiki-sync.sh
```

## 빠른 시작

사전 요구: Docker Desktop 또는 Docker Engine + Compose v2, Python 3.11(로컬 스크립트 실행 시).

```bash
# 1) Git 훅/린터 도구 설치 (선택이지만 권장)
make setup-hooks

# 2) 환경변수 파일 준비 (운영팀 제공 또는 deploy/.env.example 참고)
cp deploy/.env.example deploy/.env  # 실제 배포 산출물에 포함된 템플릿 사용

# 3) 개발 스택 기동 (핫리로드, 변경 이미지 자동 빌드)
make dev

# 4) 로그 확인 및 상태 점검
make logs
make health
```

기본 포트는 `2542`(`Makefile`의 `PORT` 기본값)이며, `deploy/.env`에서 변경 가능합니다.

## 설정

| 항목 | 위치 | 설명 |
|---|---|---|
| 런타임 환경 변수 | `deploy/.env` | DB, 외부 시스템 자격증명, 포트 |
| 컨테이너 정의 | `deploy/docker-compose.yml` | 서비스·볼륨·네트워크 |
| Collector 설정 | `collector/config.py` | 소스 엔드포인트, 자격증명 참조 키 |
| 자격증명 마이그레이션 | `scripts/migrate_env_credentials_to_db.py` | 환경변수 → DB 시크릿 이전 |
| 린트 규칙 | `pyproject.toml` (`[tool.ruff]`) | 라인 길이 120, py311 타깃 |
| mypy 규칙 | `mypy.ini` | 타입 체크 강도 |
| 커밋 규칙 | `commitlint.config.js` | Conventional Commits 강제 |

자격증명은 가급적 DB 시크릿 테이블로 이전하고, 코드/`.env`에는 키 참조만 남기도록 `migrate_env_credentials_to_db.py`를 사용합니다.

## 명령어 레퍼런스

`make help`로 항상 최신 목록을 확인할 수 있습니다. 주요 타깃:

- `setup-hooks` — pre-commit, commit-msg, husky 설치
- `dev` — 개발 스택 빌드+기동(핫리로드)
- `dev-no-build` — 기존 이미지로 빠르게 기동
- `dev-prod` — 운영 모드(오버라이드 없음, 핫리로드 없음)
- `dev-app` — app 서비스만 재기동
- `up` / `down` / `restart` — 스택 라이프사이클
- `logs` — 컨테이너 로그
- `build` — 이미지 빌드
- `health` — 헬스체크 엔드포인트 확인
- `test` — 테스트 실행
- `verify` / `verify-lint` / `verify-types` / `verify-secrets` / `verify-pre-commit` / `verify-quick` / `verify-all` — 사전 검증 게이트
- `release` / `release-dry` — 버전 갱신 및 배포 (`scripts/release.sh` 호출)
- `deploy` / `prod` — 배포 절차
- `clean` — 빌드 산출물/컨테이너 정리

## Collector 패키지

핵심 진입점: `collector/run_collector.py` (로컬/개발 실행), `collector/entrypoint.sh` (컨테이너 진입). `health_server.py`가 동일 프로세스에서 헬스 엔드포인트를 노출합니다.

| 영역 | 파일 | 용도 |
|---|---|---|
| Fortigate | `core/fortigate_collector.py`, `core/fortigate/ssh_client.py`, `core/fortigate/parsers.py` | SSH 기반 CLI/설정 수집·파싱 |
| Regtech | `core/regtech_collector.py`, `core/regtech/auth.py`, `core/regtech/data_processor.py`, `core/regtech_excel.py`, `core/regtech_parsers.py` | 공시/엑셀 데이터 수집 및 가공 |
| Multi-source | `core/multi_source_collector.py`, `core/multi_source/{collector,models,parsers}.py` | 일반화된 다중 소스 어댑터 |
| 정책/품질 | `core/policy_monitor.py`, `core/policy_monitor_support.py`, `core/data_quality_manager.py`, `core/validators.py` | 정책 변경 추적 및 품질 보증 |
| 운영 | `core/rate_limiter.py`, `core/archive_manager.py` | 호출 보호, 원본 보존 |
| DB | `core/database/service.py`, `core/database/queries.py` | 트랜잭션·쿼리 추상화 |
| API | `api/enhanced_collection_api.py` | 즉시 수집 트리거 |
| 스케줄러 | `scheduler/manager.py`, `scheduler/operations.py`, `scheduler/dependencies.py` | 잡 등록/의존성/실행 |
| 운영 문서 | `collector/RATE-LIMITING.md`, `collector/README.md`, `collector/AGENTS.md` | 소스별 운영 가이드 |

레이트 리밋 동작 방식은 `collector/RATE-LIMITING.md`를, 인증/연동 세부 사항은 각 하위 패키지의 `AGENTS.md`를 참고하세요.

## 로컬 개발

- 코드 스타일: `ruff check .` (라인 길이 120, E/F/W 셀렉트, 일부 파일별 ignore는 `pyproject.toml` 참고).
- 타입 체크: `mypy` (`mypy.ini` 적용).
- 커밋 메시지: Conventional Commits, `commitlint`가 `commit-msg` 훅에서 강제.
- 비밀 검사: `make verify-secrets` 훅 사용.
- 컨테이너 재기동이 잦은 경우 `make dev-app`만으로 빠르게 반영 가능합니다.
- 자격증명 마이그레이션 후에는 `deploy/.env`에서 해당 키를 제거하고 DB 시크릿 키만 유지하세요.

## 테스트

`pyproject.toml`의 pytest 설정(`pythonpath = ["app"]`, `testpaths = ["tests"]`)을 따릅니다.

```bash
make test                 # 전체 테스트
pytest -m unit            # 단위 테스트만
pytest -m integration     # 통합 테스트(서비스 필요)
pytest -m security        # 보안 테스트
pytest -m db              # DB 의존 테스트
pytest -m api             # API 엔드포인트 테스트
```

자세한 시나리오와 체크리스트는 `docs/testing/TEST-GUIDE-MAIN.md`와 `docs/deliverables/07-TEST-REPORT.md`를 참고하세요.

## 문제 해결 / 헬스체크

- 컨테이너가 기동되지 않을 경우 `make logs`로 마지막 로그 확인, 필요 시 `make down && make dev-no-build`로 재기동.
- 헬스 응답은 `collector/health_server.py`가 제공하며 `make health` 타깃으로 검증합니다.
- 외부 시스템 연동 실패는 `collector/exceptions.py`의 예외 클래스로 분류되며, `archive_manager`에 원본이 보존되므로 사후 재처리가 가능합니다.
- 정책 모니터링 알림 미수신 시 `core/policy_monitor_support.py`의 임계값 설정과 알림 훅 구성을 확인하세요.
- 자격증명 오류는 `scripts/migrate_env_credentials_to_db.py` 실행 결과를 우선 확인하세요.

## 기여

- 절차: `CONTRIBUTING.md` 참고.
- 커밋 규칙: `commitlint.config.js`의 Conventional Commits 준수.
- 사전 검증: PR 전 `make verify-all` 통과를 권장(린트/타입/시크릿/프리커밋).
- 코드 리뷰: `OWNERS` 파일의 책임자 목록을 따릅니다.
- 변경 범위가 `collector/`에 한정되면 해당 패키지의 `AGENTS.md`도 함께 갱신하세요.

## 유지보수 및 라이선스

- 유지보수 책임자: `OWNERS` 파일 참조.
- 버전 정책: 시맨틱 버전(`VERSION` 파일 + `scripts/release.sh`).
- 변경 이력: `CHANGELOG.md`.
- 라이선스: `LICENSE` 파일 참조.
- 추가 문서:
  - 운영 가이드: `docs/deliverables/05-OPERATIONS-GUIDE.md`, `docs/deliverables/06-RUNBOOK.md`
  - 설치/배포: `docs/deliverables/04-INSTALLATION-GUIDE.md`, `docs/wiki/Deployment-Guide.md`
  - API/스키마: `docs/deliverables/03-API-REFERENCE.md`, `docs/wiki/API-Reference.md`, `docs/wiki/Database-Schema.md`
  - 아키텍처: `docs/wiki/Architecture.md`, `docs/architecture.drawio`, `docs/deliverables/02-SYSTEM-DESIGN.md`
  - 보안/마이그레이션: `docs/wiki/Security.md`, `docs/OPERATOR_MIGRATION_GUIDE.md`, `docs/CLOUDFLARE_MIGRATION.md`
  - 산출물 전체 색인: `docs/deliverables/index.md`, `docs/wiki/Home.md`
  - 위키 ↔ 저장소 동기화: `scripts/wiki-sync.sh`, `docs/wiki/_Sidebar.md`
```

### ENGLISH SUMMARY (secondary)

**Blacklist Service** is a security-operations backend that ingests, validates, and synchronizes network blocking/policy data from Fortigate firewalls, Regtech disclosures, and other multi-source feeds. This repository ships the `collector/` Python package (sources, scheduler, quality, API, health) and the surrounding toolchain (Make, Docker Compose, pre-commit, commitlint).

- **Stack:** Python 3.11, ruff + mypy, Docker Compose, Node frontend with husky.
- **Core entry points:** `collector/run_collector.py`, `collector/entrypoint.sh`, `collector/api/enhanced_collection_api.py`, `collector/health_server.py`.
- **Quick start:** `make setup-hooks` → `make dev` → `make logs` → `make health`.
- **Verification gates:** `make verify-{lint,types,secrets,pre-commit,quick,all}`.
- **Docs map:** `docs/wiki/Home.md` (portal), `docs/deliverables/index.md` (formal deliverables 01–09), `docs/testing/TEST-GUIDE-MAIN.md`.
- **Status:** Production-ready collector, maintained per `OWNERS`. See `CHANGELOG.md` for history and `LICENSE` for terms.