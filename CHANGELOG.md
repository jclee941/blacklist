# Changelog

All notable changes to the Blacklist Intelligence Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [5.1.1] - 2026-09-04

### Added
- feat(release): include application source in bundle

### Fixed
- fix(release): authenticate offline distribution artifacts
- fix(deploy): enforce least-privilege service isolation
- fix(frontend): secure proxy and interaction boundaries
- fix(collector): harden runtime trust boundaries
- fix(database): enforce deterministic connection ownership
- fix(api): harden external trust boundaries
- fix(auth): enforce durable session lifecycle
- fix(release): exclude test environment policy from source

### Other
- docs(release): add v5.1.1 release notes

---

## [5.1.0] - 2026-08-04

### Breaking
- 배포 환경에 서로 분리된 `FLASK_SECRET_KEY`, `JWT_SECRET_KEY`, `SETTINGS_ENCRYPTION_KEY`가 필요합니다. 설치기는 신규 설치 시 값을 생성하며 기존 설치는 업그레이드 전에 추가해야 합니다.
- FortiGate HTTPS 및 SSH 연동은 각각 명시적인 CA bundle과 `known_hosts`가 없으면 실패합니다.
- Collector는 고정 UID/GID `10001`로 실행되고 PostgreSQL 호스트 인증은 TLS 위의 SCRAM-SHA-256만 허용합니다.

### Added
- feat(frontend): add administrator login flow
- feat(frontend): persist JWT sessions in API client
- feat(auth): enforce administrator JWT sessions
- feat(frontend): add cloudflare integration route

### Changed
- refactor(frontend): remove login page
- refactor(frontend): remove auth redirects
- refactor(frontend): remove login navigation
- refactor(tests): deduplicate REGTECH pagination setup
- refactor(tests): prepare REGTECH pagination scenarios
- refactor(tests): deduplicate REGTECH pagination setup

### Fixed
- fix(frontend): update vulnerable dependencies
- fix(collector): update security dependencies
- fix(app): update cryptography security release
- fix(ci): ignore pip vendored SBOM during image scans
- fix(release): pin a resolvable Python setup action
- fix(dependabot): target frontend package manifest
- fix(ci): repair PR review source checkout
- fix(collector): support CI package imports
- fix(deploy): prevent offline image pulls
- fix(auth): disable jwt middleware
- fix(frontend): validate credential modal on submit
- fix(frontend): clarify collection controls
- fix(frontend): align collection state contracts
- fix(deploy): harden offline secret provisioning
- fix(collector): bind control server to loopback
- fix(scheduler): skip collection without credentials
- fix(credentials): fail closed on decryption errors
- fix(proxy): forward authorization headers
- fix(api): validate collection credential payloads
- fix(scheduler): request all REGTECH pages manually
- fix(scheduler): request all REGTECH pages manually
- fix(regtech): complete pagination without partial results
- fix(health): report persisted collection status
- fix(database): persist collection snapshots atomically
- fix(config): redact collector credentials from diagnostics
- fix(health): report persisted collection status
- fix(database): persist collection snapshots atomically
- fix(scheduler): request all REGTECH pages manually
- fix(regtech): complete pagination without partial results
- fix(config): redact collector credentials from diagnostics
- fix(deps): restore Python 3.11 image builds
- fix(deploy): stop running containers before install
- fix(frontend): improve cloudflare settings layout
- fix(deploy): repair development compose configuration
- fix(collector): use supported regtech page size
- fix(collector): correct regtech request pagination

### CI/CD
- ci(release): package offline documentation

### Other
- test(e2e): consolidate security page login
- test(e2e): consolidate database settings login
- test(e2e): stabilize dashboard navigation
- test(e2e): stabilize collection analytics authentication
- test(e2e): consolidate collection login setup
- test(e2e): authenticate deployment smoke checks
- test(e2e): authenticate integration scenarios
- test(e2e): authenticate core protected pages
- test(e2e): centralize authenticated requests
- test(ci): guard pip vendor SBOM exclusion
- revert(deps): restore TypeScript 5
- revert(deps): restore Vite React plugin 5
- test(ci): enforce Dependabot manifest directory
- docs(deploy): list offline runtime prerequisites
- docs(deploy): remove administrator setup
- docs(release): document v4.1.0 auth changes
- docs: update offline guide indexes
- docs(deploy): consolidate offline installation guide
- docs(frontend): define operational console design
- docs(deploy): document credential bootstrap
- Revert "fix(scheduler): request all REGTECH pages manually"
- Revert "chore(deps): override vulnerable frontend packages"
- docs(release): add operator checklist
- docs(release): note Python 3.11 dependency fix

---

## [5.0.0] - 2026-07-29

정보보호팀 코드검토(2026-07-28) 지적사항을 조치한 보안 릴리즈입니다.

### Breaking

- 모든 서비스를 내부 bridge 네트워크로 옮기고 host 네트워킹을 제거했습니다. 호스트에 공개되는 포트는 frontend `443` 하나뿐이며 PostgreSQL, Redis, Collector, Flask는 더 이상 호스트에서 접근되지 않습니다.
- 필수 시크릿에 `REDIS_PASSWORD`, `COLLECTOR_AUTH_TOKEN`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`를 추가했습니다. 기존 환경 파일은 검증에서 중단되므로 업그레이드 전에 값을 채워야 합니다.
- 생성된 환경 파일 위치를 배포 번들 내부에서 `/etc/blacklist/.env`(디렉터리 700, 파일 600)로 옮겼습니다. 기존 파일을 먼저 이 경로로 이동해야 합니다.
- 릴리즈 이미지 태그를 `:latest`에서 배포 버전으로 고정했습니다. `BLACKLIST_VERSION`이 없으면 배포가 중단됩니다.
- 번들에 `MANIFEST.sha256`이 없으면 설치를 거부합니다.
- 호스트의 모든 컨테이너를 중지하던 동작을 `--stop-all-containers` 옵트인으로 바꿨습니다. 기본 설치는 무관한 컨테이너를 건드리지 않습니다.

### Security

- 설정되지 않은 관리자 자격증명으로 로그인이 가능하던 문제를 수정했습니다. 공개 소스에 있던 `__SET_ADMIN_USERNAME__` 기본값이 실제 인증을 통과했습니다.
- 관리자 자격증명을 대상 호스트에서 생성하고 최초 설치 1회만 표시합니다. 번들에는 포함하지 않습니다.
- Collector 제어 엔드포인트에 베어러 토큰 검증을 추가했습니다. health, status, logs는 헬스체크를 위해 열어 둡니다.
- Docker 바이너리와 번들 전체를 설치 전에 SHA256으로 검증하고, 실패 시 root 권한 작업 이전에 중단합니다. 선택적 GPG 서명 검증을 지원합니다.
- 체크섬 검증을 fail-closed로 바꿨습니다. 목록 파일 누락, 빈 목록, 목록에 있으나 없는 파일을 모두 치명적으로 처리합니다.
- 특권 작업 이전에 root 권한을 요구합니다.
- Redis에 비밀번호를 요구하고 Flask와 Collector가 인증하도록 배선했습니다.
- 배포 형상이 검토된 보안 기준을 위반하면 설치를 거부하는 런타임 게이트를 추가했습니다.

### Changed

- 헬스체크를 고정 대기에서 컨테이너 상태 폴링으로 바꾸고, 응답 상태값을 엄격히 판정합니다.
- 이미지 로드에서 PCRE 의존을 제거했습니다.
- 디스크 여유 공간을 Docker 데이터 디렉터리 기준으로 검사합니다.
- 오프라인 번들을 로컬에서 생성하며 버전은 `VERSION` 파일에서 자동 유도됩니다.

### Fixed

- 브리지 전환 이후 개발 환경에서 WARP 프록시에 접근하지 못하던 문제를 수정했습니다.
- 업그레이드 시 배포 버전이 갱신되지 않아 이전 이미지가 다시 기동되던 문제를 수정했습니다.
- 동작하지 않던 `.rollback-images` 코드를 제거했습니다.

---

## [4.1.0] - 2026-07-28

### Added
- Cloudflare 연동 전용 화면과 전역 메뉴를 추가했습니다.
- 한국어 오프라인 배포·운영 가이드와 패치 노트를 릴리즈 번들에 포함했습니다.
- Collection 화면에서 REGTECH 자격증명을 설정하고 저장할 수 있습니다.

### Changed
- 일반 오프라인 설치 시 실행 중인 모든 Docker 컨테이너를 중지한 후 Blacklist 서비스를 기동합니다.
- 릴리즈 이미지 5종의 버전 라벨을 `4.1.0`으로 통일했습니다.
- 설치 시 데이터베이스 비밀번호와 자격증명 암호화 키를 필수로 검증합니다.

### Fixed
- REGTECH 요청 페이지네이션, 날짜 형식, 페이지 크기와 다중 소스 수집량 계산을 수정했습니다.
- REGTECH 수집 트리거의 요청별 제한 시간과 Collector 패키지 import 충돌을 수정했습니다.
- Compose 빌드 경로와 오프라인 설치 실패 전파를 수정했습니다.
- Python 3.11 이미지에서 설치 가능한 NumPy 2.4 계열로 의존성 범위를 수정했습니다.
- 릴리즈 이미지의 개인 maintainer 메타데이터를 제거했습니다.
- 자격증명 복호화 실패 또는 미설정 상태에서 Collector가 수집을 시작하지 않도록 수정했습니다.
- Collector 제어 서버가 외부 인터페이스에 노출되지 않도록 수정했습니다.

---

## [3.6.9] - 2026-02-27

### Removed
- refactor(collector): remove IMAP-based OTP auto-reader (`OTPEmailReader`) from Secudium collector
- refactor(api): remove auto-OTP credential fields and trigger logic
- refactor(frontend): remove auto-OTP UI controls from credential modal
- refactor(deploy): remove SSL certificate bind mounts from release compose and installer

### Changed
- refactor(frontend): simplify OTP input dialog to manual-only flow
- docs: refresh AGENTS.md hierarchy to v3.6.8

### Fixed
- fix(tests): clean up test references to removed OTP email reader

---

## [3.6.8] - 2026-02-27

### Changed
- style(tests): apply ruff format normalization across test suite

### Fixed
- fix(api): replace hardcoded ports with config-driven values in system status
- fix(ci): resolve scan-images CVEs, e2e env vars, and secrets baseline
- fix(makefile): graceful skip for verify-types and verify-secrets targets
- fix(makefile): run verify targets directly instead of via Docker
- fix(release): add [Unreleased] section to CHANGELOG for release script compatibility
- fix(tests): remove unused imports and variables across test suite

### CI/CD
- ci: re-trigger CI after stuck test-backend job

### Other
- docs: update AGENTS.md hierarchy to v3.6.7 with project-specific content
- docs: update all deliverables to v3.6.7 with current codebase metrics

---

## [3.6.7] - 2026-02-26

### Fixed
- fix(collection): fix secudium manual collection flow bugs

### Changed
- refactor: document SECUDIUM trigger_all exclusion, remove redundant hasattr
- chore: add verify-* Makefile targets and document in AGENTS.md

---

## [3.6.6] - 2026-02-26

### Fixed
- fix(ci): add always() to e2e and scan-images job conditions to prevent systematic skipping
- fix(ci): strip LINE#ID prefixes from ci.yml and release.yml
- fix(ci): add version comments, timeouts, and concurrency to 5 workflow files
- fix(ci): disable 5 ghost workflows (commitlint, lock-threads, pr-size, release-drafter, welcome)
- fix(deploy): resolve credential save error and volume naming issue

### Changed
- refactor(e2e): split collection-process.spec.ts into 4 files by concern (609 LOC → 4 files)
- chore: remove stale tests/e2e/ directory, NavBar test, and Makefile target
- chore(deps): bump marshmallow from 3.20.1 to 3.26.2

---

## [3.6.5] - 2026-02-26

### Fixed
- fix(ci): add ci-gate aggregation job for branch protection compatibility
- fix(ci): remove custom CodeQL job conflicting with GitHub default setup
- fix(ci): add eslint-plugin-react-hooks as explicit devDep

---

## [3.6.4] - 2026-02-26

### Added
- feat(release): add pre-release test gate, version sync, and dynamic versioning

### Changed
- style: ruff format on modified files
- style: fix trailing whitespace and line-too-long across 25 Python files
- refactor: replace print() with logger and expand deploy config docs
- refactor: fix DI violation in admin_routes and replace wildcard import in utils
- refactor(deploy): remove sandbox references from docs and workflows
- refactor(collector): remove secudium auto-collection schedule

### Fixed
- fix(release): replace local pytest gate with gh CLI CI status check
- fix(config): make DB fallback hosts and rate limit whitelist configurable
- fix(deps): bump Werkzeug 3.1.6, Jinja2 3.1.6, Flask-WTF 1.2.2 for Flask 3.1.3 compatibility
- fix(collector): remove credential env fallbacks and align docs to DB-only policy
- fix(docs): correct drawio mxfile attributes to resolve deserialization error
- fix(deploy): harden deployment pipeline
- fix(ci): remove typecheck error suppression and fix Dockerfile warnings
- fix(collection): return 200 for unconfigured credentials instead of 404

### CI/CD
- ci(security): drop advanced CodeQL from Security workflow
- ci(security): avoid duplicate codeql category and gate critical vulns
- ci: add security scanning workflow and enhance CI pipeline
- ci(wiki): remove temporary bootstrap workflow [skip ci]
- ci(wiki): add temporary wiki bootstrap workflow [skip ci]

### Other
- docs(wiki): add XWiki compatibility guide and normalize table formatting
- docs: add CODE MAP sections to all AGENTS.md and create missing files
- docs(wiki): convert wiki-style links to standard markdown for xwiki compatibility
- docs(wiki): add 5 architecture diagrams for service, collector, CI/CD, and data
- docs: update monorepo structure documentation for v3.6.3
- docs(deliverables): rewrite system design document for v3.6.3
- docs: add central documentation hub and unify version to 3.6.3
- docs: regenerate hierarchical AGENTS.md knowledge base
- docs(wiki): add architecture definition document (7 pages + sync script)
- test(coverage): add 34 unit tests for settings, admin, monitoring routes
- test(routes): add 81 unit tests for app factory, IP management, web routes

---

## [3.6.3] - 2026-02-20

### Changed
- Release 3.6.3

---

## [3.6.2] - 2026-02-20

### Fixed
- fix(release): remove airgap branding, fix install.sh bugs, add SSL bind mount

---

## [3.6.1] - 2026-02-20

### Fixed
- **CI/CD**: 43개 CI 테스트 실패 수정 (config password 기본값, PosixPath mock, DI 패턴 정렬)
  - `config.py`: URL 파싱 시 빈 password를 `POSTGRES_PASSWORD` 기본값으로 폴백
  - `credential_service.py`: PermissionError 처리 추가, 불필요한 `encryption` 속성 제거
  - `encryption.py`: bytes/str isinstance 체크 수정
  - `ip_utils.py`: loopback 주소 우선순위 수정
- **Infra**: 모니터링 docker-compose bind mount를 Docker Compose `configs:` 섹션으로 변환
- **Infra**: 모니터링 docker-compose에서 deprecated `version: "3.8"` 제거

### Added
- **Test**: collection route 테스트 추가 (config, sync, utils, fortinet_utils) — 4개 파일
- **Test**: 전체 테스트 스위트 1362개 통과, 0개 실패

---

## [3.6.0] - 2026-02-19

### Added
- **Collector**: DB 전용 credential 관리 구현 — 환경변수 의존성 완전 제거
- **Collector**: 시작 시 credential 유효성 검증 추가
- **Collector**: DB 전용 credentials 통합 테스트 추가
- **Docs**: credential 마이그레이션 가이드 추가 (env → DB)
- **Chore**: credential env-to-DB 마이그레이션 스크립트 추가

### Changed
- **Refactor**: DB-first credential 조회로 app/collector 통합 (`db-first credential lookup`)
- **Refactor**: collector에서 환경변수 폴백 제거
- **Refactor**: `COLLECTOR_API_URL`을 `COLLECTOR_URL`로 통합

### Fixed
- **CI/CD**: blocked GitHub Actions 교체하여 startup_failure 해결
- **Collector**: OTP 파라미터명 수정 및 에러 로깅 추가
- **Collector**: retry 로직 및 시작 health check 추가
- **Collector**: credential 없이도 시작 가능하도록 수정
- **Collector**: Secudium stats 쿼리에 캐시된 DB 인스턴스 사용
- **Collector**: ruff format 적용 (exceptions 모듈)
- **Collector**: credential 테스트를 db-only flow에 맞게 업데이트
- **Credentials**: double-close 제거 및 collector 복호화 로직 수정
- **Deploy**: `.env`를 컨테이너에 전파하고 DatabaseService 캐싱

---

## [3.5.69] - 2026-02-19

### Changed
- **Dependencies (Backend)**: pytz 2023.3→2025.2, requests 2.31.0→2.32.5, markupsafe 2.1.3→3.0.3, psycopg2-binary 2.9.7→2.9.11, flask-limiter 3.5.0→4.1.1, coverage 7.3.2→7.13.4, python-dateutil 2.8.2→2.9.0.post0, schedule 1.2.0→1.2.2
- **Dependencies (Frontend)**: lucide-react 0.545.0→0.574.0, @testing-library/react 16.3.1→16.3.2, @vitejs/plugin-react 5.1.2→5.1.4, @tailwindcss/postcss 4.1.17→4.2.0, prettier 3.8.0→3.8.1, @types/node 24.10.0→25.2.3
- **CI/CD**: actions/checkout v4→v6, actions/labeler 5.0.0→6.0.1, stale automation removed from downstream GitHub Actions

### Fixed
- **CI/CD**: PYTHONPATH 설정 수정 (backend 테스트와 collector 테스트 분리)
- **CI/CD**: 로컬 Node.js CI 워크플로우 추가 (외부 `.github` 의존성 제거)

---

## [3.5.68] - 2026-02-19

> **Note:** 릴리스 파이프라인 `startup_failure`로 인해 실제 배포되지 않음 (v3.5.69에서 대체)

### Changed
- **Refactor**: 중앙 집중식 `AppConfig` 도입 — 환경변수 관리 일원화
  - Database, Auth, Utils, Services, Routes 전 계층 마이그레이션
- **Dependencies (Backend)**: selenium 4.15.2→4.40.0, paramiko 3.4.0→4.0.0, waitress 2.1.2→3.0.2, cryptography 44.0.0→46.0.5, pytest 7.4.3→9.0.2, beautifulsoup4 4.12.2→4.14.3, flake8 6.1.0→7.3.0, openpyxl 3.1.2→3.1.5, jsonschema 4.19.1→4.26.0, pytest-mock 3.12.0→3.15.1
- **Dependencies (Frontend)**: axios 1.13.2→1.13.5
- **CI/CD**: actions/setup-node v4→v6, actions/setup-python v5→v6, actions/upload-artifact v4→v6, actions/download-artifact v4→v7, slackapi/slack-github-action v1→v2

### Added
- **Backend**: 인증 및 페이지네이션 입력 검증 추가
- **Database**: 공통 쿼리용 복합 인덱스 추가
- **Frontend**: `fetch()` 호출을 api 클라이언트로 교체 및 TypeScript 인터페이스 추가
- **Test**: 배치 작업, 모니터링, 404 E2E 테스트 추가
- **Infra**: Dependabot 설정, CODEOWNERS, MIT 라이선스 추가

### Fixed
- **Collector**: SECUDIUM 세션 관리 강화 및 파이프라인 리팩토링 (#70)
- **Backend**: 중복 config import 및 미사용 os import 제거

---

## [3.5.67] - 2026-02-16

### Fixed
- **Backend**: cleanup job이 유효한 removal_date를 가진 IP를 비활성화하는 문제 수정

---

## [3.5.66] - 2026-02-16

### Fixed
- **Collector**: 수집 활성화/비활성화 로직 수정 — DB credential의 enabled 상태를 실제로 반영
- **Collector**: 스케줄 수집 및 수동 수집 시 enabled=false면 건너뜀
- **Collector**: force_collection 엔드포인트에서 비활성화된 수집기 403 반환
- **Frontend**: 대시보드 수집 활성화 표시를 실제 collector 상태 데이터에서 파생

---

## [3.5.65] - 2026-02-16

### Fixed
- **Collector**: Secudium 수집 시 문자/이메일 중복 발송 방지 (auto OTP 모드에서 testCredential 호출 제거)
- **Collector**: `force_collection()` 동시 실행 방지를 위한 idempotency guard 추가
- **Infra**: openpyxl 버전을 >=3.1.5로 업데이트하여 Pandas 호환성 문제 해결 (CI fix)

### Added
- **Test**: Secudium 수집 라이브 E2E 테스트 추가 (자동 OTP 이메일 인증 자동화)

---

## [3.5.64] - 2026-02-15

### Changed
- **Infra**: 전체 Docker Compose 바인드 마운트 → Named Volume 전환 (docker/sandbox/airgap)
- **Infra**: SSL 인증서를 frontend 이미지에 내장 (볼륨 마운트 제거)
- **Infra**: PostgreSQL 마이그레이션을 postgres 이미지에 내장 (볼륨 마운트 제거)
- **Infra**: Frontend Dockerfile 빌드 컨텍스트를 `.` 으로 변경 (release.yml + docker-compose 동기화)
- **Infra**: Sandbox collector에 REGTECH/SECUDIUM 데이터소스 환경변수 명시
- **Infra**: `.dockerignore`에 `**/.next`, `**/node_modules` 안전 패턴 추가

---

## [3.5.63] - 2026-02-15

### Added
- **Test**: 전체 유닛 테스트 커버리지 대폭 확대 (785 tests across 52 files)
  - API 라우트 26개 파일 (347 tests)
  - Collector 12개 파일 (300 tests)
  - DB 인프라 3개 파일 (41 tests)
  - Frontend 클라이언트 5개 파일 (32 tests)
  - Web 라우트 6개 파일 (65 tests)

### Fixed
- **Infra**: Watchtower Docker API 호환성 수정 (`DOCKER_API_VERSION=1.44` for Docker 27+)
- **Frontend**: 컨테이너 healthcheck를 `curl` → `node` 기반으로 변경 (alpine 호환)
- **CI/CD**: Sandbox deploy frontend health check를 https로 변경

### Changed
- **CI/CD**: Airgap 프로덕션 배포를 `workflow_dispatch` 수동 전용으로 변경 (자동 트리거 제거)

---

## [3.5.59] - 2026-02-11

### Added
- **Infra**: Watchtower HTTP API 실시간 pull 트리거 (기존 5분 polling → release 완료 시 즉시 업데이트)
- **CI/CD**: `release.yml`에 `trigger-sandbox-update` job 추가 — GHCR push 후 Watchtower API 호출

### Changed
- **Infra**: Sandbox Watchtower 설정 변경 — HTTP API 활성화 (포트 8080), Bearer token 인증, 1시간 safety net polling

---

## [3.5.58] - 2026-02-11

### Added
- **Frontend**: IP 관리 auto_active 3-state 상태 표시 (활성/비활성/미설정)
- **Frontend**: IP 관리 소스 필터 기능 (REGTECH/SECUDIUM/수동 필터링)
- **Infra**: Prometheus + Grafana 모니터링 스택 (Sandbox용)
- **Infra**: Watchtower 자동 배포 설정 (Sandbox → GHCR :latest 자동 pull)
- **Docs**: 전체 17개 AGENTS.md 파일 재생성 (`/init-deep`)

### Fixed
- **E2E**: 4개 테스트 실패 수정 — 모니터링 리다이렉트, 설정 저장 toast 타이밍, 비주얼 스냅샷
- **CI/CD**: GHCR 전용 태그 사용으로 Docker Hub 401 에러 방지
- **Tests**: `auth_rate_limiter` fixture 격리 — 테스트 간 오염 방지
- **Tests**: `credential_service`, `health_server` CI 테스트 실패 수정
- **Backend**: IP 관리 데이터 정합성 개선

---

## [3.5.57] - 2026-02-11

### Added
- **Backend**: 설정 API 통합 (시스템 설정 CRUD)
- **Tests**: Collector 테스트 스위트 추가

### Fixed
- **CI/CD**: Sandbox 배포 시 SCP → SSH stdin 방식으로 변경 (권한 문제 해결)
- **CI/CD**: `recursive chown` 추가로 배포 디렉토리 권한 정리

---

## [3.5.56] - 2026-02-11

### Fixed
- **GitHub Issues**: #16 #17 #18 #32 #33 #36 일괄 해결
  - #16: 수집 현황 API 응답 구조 정규화
  - #17: 블랙리스트 해제 시 removal_date 설정
  - #18: FortiManager 업로드 대상 IP 필터링 수정
  - #32: 설정 페이지 API 연동 (저장/로드)
  - #33: 수집기 인증정보 수정 시 기존 값 유지
  - #36: 대시보드 통계 null 처리

---

## [3.5.55] - 2026-02-11

### Fixed
- **Database**: Migration 004 — `active_blacklist` 뷰에 `removal_date` 컬럼 추가

---

## [3.5.54] - 2026-02-11

### Added
- **Backend**: Secudium 수동 OTP 로그인 + 자동 수집 트리거
- **Tests**: 14개 이상 코어 서비스 단위 테스트 추가 (포괄적 커버리지)
- **E2E**: 테스트 범위 확장

### Fixed
- **Backend**: REGTECH removal_date 처리 수정
- **Backend**: 데이터 정합성 강화 — 3개월 일관성 검증 + 백엔드 강제 적용
- **Backend**: FortiManager uploader 하드코딩 포트 443 → 2542 수정

---

## [3.5.53] - 2026-02-10

### Changed
- **Backend**: 내부 코드 정리 및 안정화

---

## [3.5.52] - 2026-02-10

### Fixed
- **Frontend**: 데이터베이스 페이지 0건 테이블 '집계중' 표시 수정 → 정상 건수 표시
- **Collector**: Secudium 수집 IP에 `source='SECUDIUM'` 명시적 설정

---

## [3.5.51] - 2026-02-10

### Added
- **Collector**: SECUDIUM 수집 트리거에 OTP 인증 추가

### Fixed
- **Backend**: 수동 수집 트리거가 올바른 소스로 라우팅되도록 수정

---

## [3.5.50] - 2026-02-10

### Changed
- **Backend**: JWT 인증 미들웨어 비활성화 (내부 배포 환경용)

---

## [3.5.49] - 2026-02-10

### Added
- **Tests**: Smoke 테스트 추가

### Changed
- **CI/CD**: 커버리지 임계값 조정 (CI 부트스트랩용)

### Fixed
- **Backend**: 미사용 import 제거 (F401 ruff lint)

---

## [3.5.48] - 2026-02-10

### Fixed
- **Backend**: 통합 IP 목록 쿼리, 프론트엔드 API 설정, Sandbox 환경변수 수정
- **Collector**: Secudium OTP 인증 개선 — 중복 로그인 처리, IMAP 새로고침, 환경변수 추가
- **CI/CD**: 배포 파이프라인 강화 — python3 JSON 파싱, Slack 알림, 심볼릭 링크 해석
- **CI/CD**: health check 이스케이프 수정, `.env` 자동 생성

---

## [3.5.47] - 2026-02-10

### Added
- **CI/CD**: Sandbox 배포 워크플로우 추가 (SSH → GHCR pull 기반)
- **Collector**: SECUDIUM OTP 수집 플로우 개선

### Fixed
- **Frontend**: 401 → `/login` 리다이렉트 제거 (인증 미들웨어 비활성 환경)

### Changed
- **Repo**: 저장소 구조 정리

---

## [3.5.46] - 2026-02-09

### Fixed
- **Backend**: JWTService에 Flask app 객체 대신 `SECRET_KEY` 문자열 전달 (#23)

---

## [3.5.45] - 2026-02-09

### Changed
- **Backend**: `rate_limit` 데코레이터 공유 유틸리티로 중앙화 (#21)
- **Backend**: 코드베이스 위생 정리 (#22)

---

## [3.5.44] - 2026-02-09

### Fixed
- **CI/CD**: 배포 health check 경로 `/api/health` → `/health`로 수정

---

## [3.5.43] - 2026-02-09

### Fixed
- **Backend**: `/api/health` 엔드포인트에 `@public` 데코레이터 추가 — 배포 health check 용 (#20)
- **Backend**: 모든 bare `except Exception` 블록에 예외 변수 캡처 (#19)

---

## [3.5.42] - 2026-02-09

### Fixed
- **Collector**: SECUDIUM health 상태에서 문자열 타입 `scheduler.collectors` 처리
- **Infra**: `install.sh`에서 로드된 이미지를 `:latest` 태그로 지정 (docker-compose 호환)

---

## [3.5.41] - 2026-02-09

### Fixed
- **CI/CD**: Airgap 배포 수정 — 체크섬 파일명 정렬, 번들 이름 패턴, 이미지 태깅
- **CI/CD**: `install.sh` 양방향 체크섬/이미지 이름 패턴 호환
- **CI/CD**: GitHub API 기반 에셋 다운로드, stale 배포 디렉토리 정리

---

## [3.5.40] - 2026-02-09

### Added
- **CI/CD**: 워크플로우 통합 (7개 → 4개: ci, release, deploy, deploy-sandbox)
- **Backend**: JWT 인증 미들웨어 (#1)
- **Backend**: Multi-stage Dockerfile (이미지 크기 최적화)
- **Frontend**: SECUDIUM 수집기 지원 (수집 상태, 인증 UI)

### Changed
- **Backend**: Ruff 린터 도입 — 86개 린트 에러 수정
- **Collector**: `regtech_collector.py` (960L) + `multi_source_collector.py` (711L) → 모듈형 패키지로 리팩토링
- **Backend**: `cache_utils.py` 복잡도 감소 (42 → 20)

### Fixed
- **Frontend**: 대시보드 통계 `statsData.stats` → `.data` 읽기 수정
- **Frontend**: 수집 통계 프론트엔드와 백엔드 API 정렬
- **Frontend**: 화이트리스트/블랙리스트 CRUD, FortiNet 다운로드 응답 처리
- **Frontend**: 7개 스텁 API 함수를 실제 백엔드 호출로 교체
- **Backend**: 암호화 키, Collector URL 기본값, SECUDIUM health 상태 정렬
- **CI/CD**: 배포 시 컨테이너 이름 충돌 방지 (`docker compose down` 추가)

---

## [3.5.39] - 2026-02-08

### Fixed
- **Frontend**: Secudium 수집기 카드가 인증정보 미설정 시에도 표시되도록 수정

---

## [3.5.38] - 2026-02-08

### Added
- **Frontend**: Secudium 수집기 인증 UI (OTP 자동/수동 모드 지원)
- **Frontend**: OTP 수동 입력 다이얼로그 (6자리 입력, 자동 포커스)
- **Frontend**: CredentialEditModal에 Secudium OTP 설정 필드 (이메일, IMAP 서버)
- **Backend**: Secudium 인증정보 API 확장 (OTP 모드, 이메일, IMAP 설정 저장/조회)
- **Backend**: Secudium OTP 제출 엔드포인트 (수동 2단계 인증)
- **Collector**: SecudiumCollector OTP 인증 플로우 (자동 Kakao IMAP + 수동 입력)
- **Collector**: Secudium test-auth 엔드포인트 (410 deprecation 제거, 실제 인증 구현)
- **Collector**: authenticate_step1/step2 메서드 (수동 OTP 2단계 인증 지원)
- **Tests**: Secudium collector 및 parser 단위 테스트

---

## [3.5.37] - 2026-02-08

### Fixed
- **Backend**: Resolved merge conflict markers in system_api.py (timestamp→collection_date, app.log→collector.log)
- **Backend**: Resolved merge conflict markers in analytics.py (days=all support, removed suspicious pattern analysis)
- **Backend**: Added missing `import os` in blacklist/collection.py for collector URL resolution

---

## [3.5.36] - 2026-02-06

### Changed
- **Frontend**: Refactored CollectionManagementClient.tsx (665→119 lines, 82% reduction)
- **Frontend**: Extracted components: types.ts, useCollectionManagement.ts, CollectionStats.tsx, CollectorCard.tsx, CredentialEditModal.tsx

---

## [3.5.35] - 2026-02-06

### Changed
- **E2E Tests**: Removed mobile test projects (Mobile Chrome, Mobile Safari)
- **E2E Tests**: Desktop browsers only (smoke, chromium, firefox, webkit)

---

## [3.5.34] - 2026-02-06

### Added
- **E2E Tests**: Enhanced Playwright config for external URL testing
- **E2E Tests**: Added deployment smoke tests and error handling tests

### Changed
- **Docs**: Updated AGENTS.md hierarchy with project patterns

---

## [3.5.33] - 2026-02-05

### Fixed
- **Frontend**: Resolved TypeScript type narrowing errors in FortinetClient.tsx
- **Frontend**: Fixed API stub return types to include `error` field for proper error handling

---

## [3.5.19] - 2026-02-03

### Fixed
- **App**: Replaced hardcoded `blacklist-collector:8545` URLs with `COLLECTOR_URL` environment variable (8 locations)
- **Collector**: Fixed `trigger_manual_collection()` parameter mismatch in health_server.py

---

## [3.5.18] - 2026-02-03

### Fixed
- **Frontend**: Analytics page default days changed from 30 to 365 and added 180/365/730 day options

---

## [3.5.17] - 2026-02-03

### Fixed
- **Analytics**: Changed detection-timeline default days from 30 to 365 to show full REGTECH detection history

---

## [3.5.16] - 2026-02-03

### Fixed
- **CI/CD**: Fixed airgap bundle to include correct docker-compose.yml with SSL configuration

---

## [3.5.15] - 2026-02-03

### Fixed
- **Analytics**: Fixed GROUP BY clause mismatch in detection-timeline query (GROUP BY source instead of data_source)
- **Docker**: Fixed frontend healthcheck - use node https.request instead of busybox wget (SSL cert issues)
- **API**: Dashboard stats now use `last_seen` instead of `detection_date` for accurate last update time
- **Frontend**: Corrected trigger collection API path (`/collection/trigger/${serviceName}`)

---

## [3.5.14] - 2026-02-03

### Fixed
- **Collector**: Simplified REGTECH auth flow - removed failing `/member/findOneMember` step
- **Collector**: Fixed password decryption in test auth endpoint - use `DatabaseService.get_collection_credentials()`

---

## [3.5.13] - 2026-02-03

### Fixed
- **Collector**: REGTECH login_payload now includes all required form fields
- **Frontend**: Settings button now works when no credentials exist yet

---

## [3.5.11] - 2026-02-02

### Changed
- **AGENTS.md**: SSH jump host download command no longer requires jq (uses grep+cut)

---

## [3.5.7] - 2026-02-02

### Added
- **download.ps1**: PowerShell script for Windows air-gap deployment
- **GitHub Wiki**: Complete documentation (Installation, API Reference, Development, Troubleshooting)

### Changed
- **README.md**: Updated to v3.5.6, added multiple download options (curl, ssh jump, PowerShell)
- **Release workflow**: Include download.ps1 in release assets

---

## [3.5.6] - 2026-02-02

### Fixed
- **GitHub Release Workflow**: Use correct Docker build context per Dockerfile (frontend: `./frontend`, postgres: `./postgres`, redis: `./redis`, app/collector: `.`)

---

## [3.5.5] - 2026-02-02

### Fixed
- **GitHub Release Workflow**: Use project root as Docker build context (fixes `COPY app/requirements.txt` path resolution)

---

## [3.5.4] - 2026-02-02

### Fixed
- **GitHub Release Workflow**: Fixed YAML syntax error in heredoc script

---

## [3.5.3] - 2026-02-02

### Added
- **GitHub Releases Automation**: Tag push now auto-creates GitHub Release with airgap bundle
  - All 5 Docker images packaged (frontend, app, collector, postgres, redis)
  - `install.sh` for air-gapped deployment
  - SHA256 checksums included

---

## [3.5.2] - 2026-02-02

### Added
- **LXC 220 CI/CD Deployment**
  - Self-hosted GitLab runner on LXC 220
  - SSH-based deployment to production environment
  - E2E tests and airgap bundle automation on master branch

### Fixed
- **Collector Stats Persistence** - `last_run` and `run_count` now persist across container restarts (fixes "마지막 업데이트: 없음" bug)
- **Dashboard 24h Statistics** - Correctly use `detection_date` for recent additions count
- **Database Schema**
  - Added `display_order` column to `system_settings`
  - Added `fortigate_devices` table
- **CI/CD Health Check** - Use container status instead of HTTP endpoint for reliability

### Changed
- **CI/CD Workflow Cleanup**
  - Removed legacy workflows (xwiki-auto-sync, docker-build-portainer-deploy, offline-package-build, frontend-tests)
  - Consolidated into unified `.gitlab-ci.yml`
  - Cloudflare Workers deploy set to manual trigger only

### Removed
- Orphaned client components from frontend
- Duplicate/unused UI elements (refactored)

---

## [3.5.1] - 2026-01-06

### Added
- **CI/CD Pipeline v5.0**
  - Parallel Docker builds (5 images simultaneously)
  - File hash-based cache keys for pip/npm dependencies
  - Trivy container scanning for HIGH/CRITICAL vulnerabilities
  - Manual rollback job with `ROLLBACK_TAG` variable

- **Folder Structure Reorganization**
  - `scripts/` reorganized from 65 flat files → 8 subdirectories
  - New structure: `deploy/`, `package/`, `fortinet/`, `setup/`, `testing/`, `database/`, `utils/`, `docs/`
  - Updated Makefile and `.gitlab-ci.yml` script paths

- **Frontend Co-location Pattern**
  - Domain-specific `types.ts` files per route
  - Custom hooks in `hooks/` subdirectories
  - Shared UI components: Button, Input, Modal

- **Documentation**
  - `docs/FOLDER-STRUCTURE.md` - Scripts reorganization guide
  - `docs/CICD-QUICK-REFERENCE.md` - Updated for v5.0
  - `docs/FRONTEND-ARCHITECTURE.md` - Co-location pattern guide

### Changed
- **CI/CD Build Stage**: Sequential → Parallel execution (~80% faster)
- **Cache Strategy**: Branch-based → File hash-based invalidation
- **Visual Regression Snapshots**: Updated for current UI state

### Fixed
- **E2E Tests**: 95 passed, 7 skipped (visual regression snapshots updated)

---

## [3.5.0] - 2026-01-02

### Added
- **REGTECH Excel Download**: Replaced pagination with direct Excel download
  - 10 IPs → 52,318 IPs collected per run
  - 90-day date range for manual collection, 1-day for scheduled
  - `/fcti/securityAdvisory/advisoryListDownloadXlsx` endpoint integration

- **Frontend Collection Dashboard**
  - Real-time collection status banner with 5-second polling
  - Collected data view with IP table and country distribution
  - Search functionality for IP addresses

- **Air-Gap Package V3.3**
  - Dual-package format: `blacklist.tar.gz` (818MB) + `install.sh`
  - 5 Docker images with date-based tagging
  - Automation scripts included (health-monitor, add-credentials, setup-credentials, backup-database)
  - 6 API validation tests in installer

### Changed
- **DNS Compatibility**: WARP proxy now fully optional via `WARP_PROXY_URL` environment variable
- **Credential Encryption**: Fixed `is_encrypted` flag to properly reflect Fernet encryption status
- **Scheduler**: Separate date ranges for manual (90-day) vs scheduled (1-day) collection

### Fixed
- **REGTECH Pagination**: Server-side pagination was broken (same 10 IPs on every page)
- **Credential Flags**: Updated `is_encrypted=true` and `encryption_version=fernet-v1` for REGTECH/SECUDIUM

### Verified
- ✅ **Container Health**: 6/6 services running (5 healthy)
- ✅ **Data Collection**: 52,319 total IPs, 15,634 active, 153 countries
- ✅ **FortiGate Integration**: `/api/fortinet/blocklist` serving 15,671 IPs
- ✅ **Frontend Tests**: Vitest 6/6 passed, Playwright 22/45 passed (Chromium OK, webkit issues)
- ✅ **API Endpoints**: All core endpoints responding correctly

---

## [3.4.0] - 2025-11-12

### Added
- **Comprehensive Codebase Analysis Documentation**
  - Created `CODEBASE_STRUCTURE_ANALYSIS.md` (963 lines) - Complete architectural overview
  - 140 Python files analyzed (42,647 LOC)
  - 14 major sections covering all aspects of the codebase
  - Service layer documentation (15 services)
  - Blueprint pattern details (11 API + 8 web routes)
  - Testing infrastructure guide (34 test files, 8 pytest markers)
  - Deployment models (dev/prod/air-gapped)
  - Performance characteristics and startup flow

- **OpenCode.md Enhancement Recommendations**
  - Created `OpenCode-MD-IMPROVEMENT-RECOMMENDATIONS.md`
  - 7 specific, actionable improvements for AI-assisted development
  - Blueprint pattern deep dive with concrete examples
  - Service layer usage patterns and dependency injection
  - Common utilities guide (db_utils, cache_utils, encryption, validators)
  - Advanced testing strategies (execution, coverage, templates)
  - Troubleshooting guides (migrations, FortiManager, air-gapped deployment)
  - All examples are copy-paste ready and based on actual code patterns

### Changed
- **VERSION**: Updated from 3.3.9 → 3.4.0
- **Documentation Organization**: Enhanced for AI-assisted development workflows
  - Focus on "big picture" patterns requiring multi-file understanding
  - No generic advice - all recommendations based on actual codebase analysis

### Verified
- ✅ **Docker Compose Configurations**: All 3 environments validated (dev/prod/offline)
- ✅ **PostgreSQL Auto-Migration System**: 20 migration files, custom entrypoint confirmed
- ✅ **GitLab CI/CD Pipeline**: 4-stage air-gapped build pipeline operational
- ✅ **Air-Gapped Packaging Scripts**: All 5 packaging scripts syntax validated
- ✅ **Testing Infrastructure**: 34 test files, pytest 7.4.3, 80% coverage requirement
- ✅ **Flask Application**: Import successful, blueprint pattern verified

### Technical Debt Addressed
- GitLab CI YAML style warnings (line length) - non-blocking, functional
- Test directory structure confirmed (previously uncertain)
- Documentation gaps filled with concrete examples

---

## [3.3.9] - 2025-11-07

### Changed
- **Repository Migration**: GitHub → GitLab
  - Migrated from https://github.com/qws941/blacklist to https://gitlab.jclee.me/jclee/blacklist
  - All branches, tags, and commit history preserved
  - Git LFS configuration optimized for GitLab
  - Performance optimizations applied (compression level 9, 2GB pack cache)
  - GitHub repository marked as migrated with redirect notice

### Added
- **GitLab CI/CD Pipeline**: Release-only automation
  - 4-stage pipeline: validate → build → release → notify
  - Semantic version validation (`v[0-9]+\.[0-9]+\.[0-9]+`)
  - Automated tarball artifact creation (90-day retention)
  - GitLab release creation with artifacts
  - Slack notification support
  - Triggers only on tag push (no regular commit builds)

### Fixed
- **Version Management**: VERSION file synchronized
  - Updated to 3.3.9 to match release tag
  - Resolved version mismatch between VERSION, CHANGELOG, and git tags

---

## [3.3.8] - 2025-10-30

### Fixed
- **Credential Initialization UX** (Patch 006)
  - 초기 설정 시 "REGTECH 인증 정보 없음" 경고 메시지가 계속 출력되던 문제 수정
  - 인증 정보가 없는 상태에서도 설정 UI가 정상 동작하도록 개선
  - `secure_credential_service.py`: logger.warning → logger.debug 변경
  - `monitoring_scheduler.py`: credentials 조회 시 조용히 None 반환
  - 사용자가 처음 시스템을 설치했을 때 깨끗한 로그와 UI 제공

### Changed
- **Docker Compose**: Traefik 설정 최적화
  - HTTPS Only (443) - HTTP(80) 제거
  - 간결한 Traefik labels (6줄)
  - `blacklist-app` 컨테이너에 패치 디렉토리 마운트 추가
  - `./offline-packages/patches:/patches:ro` (read-only)

### Added
- **Auto-Patching on Container Start with Smart Detection** (NEW!)
  - `app/entrypoint.sh`: 컨테이너 재부팅 시 **적용 안된 패치만** 자동 스캔 및 적용
  - 패치 추적 파일: `/app/.applied_patches` (성공한 패치 기록)
  - 스마트 감지: 이미 적용된 패치 자동 스킵 (불필요한 재실행 방지)
  - 상대 경로 지원: `/patches`, `/app/patches`, `./offline-packages/patches`
  - `set -eo pipefail` 설정 (파이프 에러 감지)
  - 패치 실행 결과 통계 (Applied/Skipped/Failed 카운트)
  - 패치 히스토리 표시 (총 적용된 패치 개수)
  - 패치 실패 시에도 컨테이너 정상 시작 (graceful degradation)
  - Dockerfile: bash 런타임 추가, ENTRYPOINT 설정
- **Offline Package: Patches 포함**
  - `create-dual-package.sh`: 패치 디렉토리 자동 포함
  - `install.sh`: `setup_patches()` 함수 추가 (실행 권한 설정)
- **Runtime Patches**:
  - `001-upgrade-entrypoint-smart-detection.sh`: 스마트 패치 감지 시스템 (최우선 - 다른 패치 자동 적용 기반)
  - `002-migrate-to-traefik.sh`: Traefik 설정 자동 마이그레이션
  - `003-fix-credential-initialization.sh`: Credential 초기화 UX 개선
- **Documentation**: TRAEFIK-SETUP.md 업데이트 (v3.3.8 반영)

---

## [3.3.7] - 2025-10-30

### Added
- **Traefik Offline Package** (traefik-offline.tar.gz, 48M)
  - 독립 배포 가능한 Traefik 리버스 프록시 패키지
  - NXTD SSL 인증서 지원
  - Multi-service 환경을 위한 별도 배포 옵션

### Fixed
- **HTTPS Port Fix for Air-gap Environments**
  - Monitoring scheduler HTTPS 설정 수정
  - SECUDIUM URL 및 파일 경로 수정
  - 격리 환경(air-gap)에서 HTTPS 통신 안정화

### Changed
- **Interactive Manual Collection Guide**
  - 사용자 친화적인 수동 수집 트리거 가이드 추가
  - Step-by-step 날짜 선택 및 수집 실행 지원

---

## [3.3.6] - 2025-10-25

### Added
- **Web UI Pages** (3 new pages)
  1. **FortiGate/FortiManager Integration** (`/integrations`)
     - 8 FortiGate API endpoints 문서화 및 라이브 테스트
     - FortiManager 자동화 스크립트 가이드
     - 복사-붙여넣기 및 인라인 테스트 기능

  2. **Session History Management** (`/sessions`)
     - 실시간 통계 (active, last hour, last 24h, unique countries)
     - Multi-filter system (time range, status, risk level, country)
     - Auto-refresh every 30 seconds
     - CSV export and session detail modal

  3. **Collection Logs Viewer** (`/collection-logs`)
     - REGTECH/SECUDIUM 실시간 수집 로그
     - Log level 분류 (success/error/warning/info)
     - Auto-refresh toggle with countdown timer
     - Expandable log details and CSV export

---

## [3.3.5] - 2025-10-22

### Added
- **Application Security (Phase 1.3)**
  - CSRF Protection (Flask-WTF) - All state-changing requests
  - Rate Limiting (Flask-Limiter + Redis) - Global: 200/day, 50/hour
  - Security Headers (X-Frame-Options, CSP, HSTS, etc.)
  - Input Validation (SQL injection prevention, IP format validation)

### Changed
- **Security Test Coverage**: `tests/security/test_security.py` (319 lines)
  - CSRF token validation tests
  - Rate limiting tests
  - SQL injection prevention tests
  - Security headers tests

---

## [3.3.4] - 2025-10-20

### Added
- **SECUDIUM Integration** (Multi-collector architecture)
  - Dual-source collection (REGTECH + SECUDIUM)
  - Unified API for multiple threat intelligence sources
  - Browser automation for SECUDIUM data extraction
  - Separate scheduling per source (independent intervals)

### Changed
- **Database Migrations**:
  - 013_add_notify_trigger.sql - PostgreSQL NOTIFY trigger for real-time updates
  - 014_add_source_column.sql - Source tracking for blacklist entries

---

## [3.3.3] - 2025-10-18

### Added
- **Runtime Patch System** (v2.1)
  - Intelligent patch scripts with auto-recovery
  - Unified logging system
  - Password auto-detection
  - 3 retry attempts on service restart
  - Graceful degradation

### Fixed
- **REGTECH Authentication**
  - Two-stage authentication (findOneMember → addLogin)
  - Session management improvements
  - Cookie handling fixes

---

## [3.3.2] - 2025-10-15

### Added
- **Air-gap Deployment** (2-file method)
  - `blacklist.tar.gz` (560M) - 6 Docker images
  - `install.sh` (18K) - Auto-install script
  - Network pre-validation (REGTECH/SECUDIUM connectivity)
  - Air-gap mode support (`--skip-network-check`)

---

## [3.3.1] - 2025-10-12

### Added
- **API Proxying** (`/api/proxy/*`)
  - CORS-free API proxying to collector service
  - Avoids frontend CORS issues

### Changed
- **Network Validation** in `install.sh`
  - Validates REGTECH and SECUDIUM API connectivity
  - Can be skipped with `--skip-network-check` flag

---

## [3.3.0] - 2025-10-10

### Added
- **Whitelist Priority System** (Phase 1)
  - VIP protection - Whitelist checked BEFORE blacklist
  - `is_active` flag for whitelist entries
  - Priority-based IP check logic

### Changed
- **Database Schema**:
  - `whitelist_ips` table with priority check
  - `unified_ip_list` view (blacklist + whitelist)

---

## [3.2.0] - 2025-10-05

### Added
- **FortiGate Integration**
  - 8 FortiGate/FortiManager API endpoints
  - Push-based blacklist updates
  - FortiManager automation scripts

---

## [3.1.0] - 2025-10-01

### Added
- **REGTECH Policy Monitor**
  - Automated daily collection
  - Excel parsing with pandas + openpyxl fallback
  - Database-driven configuration

---

## [3.0.0] - 2025-09-25

### Changed
- **Flask App Factory Pattern**
  - Blueprint-based modular route organization
  - 15+ Blueprints for API endpoints
  - Singleton service pattern

---

## [2.0.0] - 2025-09-20

### Added
- **Container-based Development**
  - 6 microservices in Docker
  - PostgreSQL 15 + Redis 7
  - Next.js SSR frontend
  - Nginx reverse proxy

---

## [1.0.0] - 2025-09-01

### Added
- **Initial Release**
  - Basic blacklist IP management
  - Manual IP add/remove
  - PostgreSQL database
  - Simple Flask API

---

**Version Naming Convention**:
- **Major (X.0.0)**: Architecture changes, breaking changes
- **Minor (3.X.0)**: New features, significant improvements
- **Patch (3.3.X)**: Bug fixes, minor improvements, runtime patches

**Maintained by**: OpenCode
**Project**: REGTECH Blacklist Intelligence Platform
**License**: MIT
