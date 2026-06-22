# Blacklist Service Management

[English](#english) | [한국어](#한국어)

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Docker](https://img.shields.io/badge/Docker-ready-blue)
![Ruff](https://img.shields.io/badge/Lint-Ruff-46a2f1)
![pytest](https://img.shields.io/badge/Test-pytest-0a9edc)
![mypy](https://img.shields.io/badge/Types-mypy-2a6db2)
![CodeQL](https://img.shields.io/badge/Security-CodeQL-purple)
![Gitleaks](https://img.shields.io/badge/Secrets-Gitleaks-red)
![OpenSSF Scorecard](https://img.shields.io/badge/Supply%20Chain-Scorecard-brightgreen)
![License](https://img.shields.io/badge/License-See%20LICENSE-lightgrey)
![PR-Agent](https://img.shields.io/badge/Review-PR--Agent-orange)

---

<a id="english"></a>

# English

## Overview

**Blacklist Service Management** is a Python 3.11 web application that consolidates blacklist collection, operational monitoring, role-based API access, Fortinet firewall integration, and AI-assisted automation behind a single Flask-based service.

The runtime under `app/` exposes a layered architecture:

- **Web tier** — Flask templates (`templates/index.html`, `templates/collection.html`, `templates/sessions.html`, `templates/settings.html`, `templates/integrations.html`, `templates/collection_logs.html`, `templates/monitoring/dashboard.html`).
- **API tier** — REST endpoints under `app/core/routes/api/` covering analytics, auth, dashboard, database, error metrics, settings, system, Fortinet registration, blacklist, collection, migration, and IP management.
- **Realtime tier** — WebSocket routes for live dashboard updates.
- **Integration tier** — Proxy routes that bridge the service to **CLIProxyAPI** at `https://cliproxy.jclee.me/v1` for LLM access (primary model `gpt-5.5`, fallback `minimax-m3`).
- **Operations tier** — Structured logging, log rotation, deployment validation, and Docker packaging.

Automation is first-class: the repository carries **20 GitHub Actions workflows** that govern branches, pull requests, security scanning, releases, downstream health, and self-healing.

## Features

- Flask 3 web UI with role-based access control (RBAC) and JWT-backed sessions.
- Centralized blacklist ingestion with multi-source sync (`sources.py`), credential vault (`credentials.py`), and history (`history.py`).
- Fortinet firewall registration and IP-management helpers (`fortinet_register.py`, `ip_management_helpers.py`).
- Live monitoring via WebSockets, structured JSON logging, log rotation manager, and deployment validation (`deployment_validation.py`).
- AI-assisted workflows powered by **PR-Agent** (`qodo-ai/pr-agent`) and **Codex** automations.
- Container-first delivery: `app/Dockerfile`, `app/entrypoint.sh`, `app/run_app.py`, and a Makefile-driven `make dev` / `make deploy` lifecycle.

## Architecture

```mermaid
flowchart TB
    subgraph Client["Client Surface"]
        Browser["Web Browser<br/>(Flask templates)"]
        Operator["Operator CLI / Scripts"]
        Fortinet["Fortinet Gateway"]
    end

    subgraph App["app/ - Flask Service"]
        WebTier["Web Tier<br/>core/routes/web_routes.py"]
        APITier["API Tier<br/>core/routes/api_routes.py<br/>+ api/* blueprints"]
        WSTier["Realtime Tier<br/>core/routes/websocket_routes.py"]
        ProxyTier["Integration Tier<br/>core/routes/proxy_routes.py"]
        OpsTier["Operations Tier<br/>structured_logging.py<br/>log_rotation_manager.py<br/>deployment_validation.py"]
        Auth["Auth Layer<br/>core/auth/<br/>jwt_service, middleware, decorators"]
        Monitoring["Monitoring<br/>core/monitoring/<br/>metrics, cache_metrics, error_metrics"]
    end

    subgraph Data["Data Plane"]
        BlacklistStore["Blacklist Store"]
        SettingsDB["Settings / Sessions DB"]
        LogSink["Structured Log Sink"]
    end

    subgraph Ext["External Services"]
        CLIP["CLIProxyAPI<br/>https://cliproxy.jclee.me/v1<br/>gpt-5.5 / minimax-m3"]
        Homelab["Homelab Host<br/>CLIProxy["&lt;homelab-host&gt;:8317<br/>CLIProxyAPI"]"]
        ELK["ELK Stack<br/>&lt;homelab-elk&gt;<br/>log ingest"]
        Bot["Automation Bot<br/>https://bot.jclee.me"]
    end

    Browser -->|HTTPS| WebTier
    Operator -->|REST| APITier
    Fortinet -->|REST| APITier
    WebTier --> APITier
    WebTier --> WSTier
    APITier --> Auth
    APITier --> Monitoring
    APITier --> BlacklistStore
    APITier --> SettingsDB
    WSTier --> Monitoring
    ProxyTier -->|HTTPS| CLIP
    ProxyTier -.fallback.-> Homelab
    App --> OpsTier
    OpsTier --> LogSink
    OpsTier -->|ship| ELK
    Bot -. orchestrates .-> App
```

## Automation Inventory

The repository ships with **20 GitHub Actions workflows** under `.github/workflows/`. They are grouped by lifecycle stage and listed with their real on-disk filenames.

### Issue & Branch Lifecycle

- `01_branch-to-branch.yml` — promotes an issue into a working branch.
- `02_issue-to-branch.yml` — converts a tracked issue into a feature branch with metadata.
- `19_issue-backfill.yml` — backfills missing labels and metadata on legacy issues.
- `91_issue-classification.yml` — auto-classifies incoming issues by topic and severity.
- `15_merged-pr-cleanup.yml` — deletes head branches after PR merge.

### Pull Request Automation

- `10_pr-review.yml` — PR-Agent (`qodo-ai/pr-agent`) code review on every PR.
- `11_security-pr-review.yml` — security-focused PR review with extra threat-model context.
- `12_dependabot-auto-merge.yml` — auto-merges eligible Dependabot patch updates.
- `13_pr-auto-merge.yml` — squash-merges PRs that pass all required checks.
- `14_bot-auto-fix.yml` — bot-driven remediation of lint, type, and trivial-fix issues.

### Continuous Integration

- `ci.yml` — main pipeline (lint, type-check, unit, integration).
- `_ci-node.yml` — Node.js frontend CI helper invoked by `ci.yml`.
- `build-images.yml` — builds and tags the container image.
- `security.yml` — CodeQL static analysis plus OpenSSF Scorecard checks.

### Release Engineering

- `24_release-notes.yml` — drafts release notes from merged PRs.
- `25_release-publish.yml` — publishes a GitHub Release with artifacts and changelog.
- `release.yml` — orchestrates the end-to-end release flow.

### Reliability & Self-Healing

- `29_downstream-health-check.yml` — probes downstream services and posts status.
- `37_ci-failure-issues.yml` — opens a tracked issue when CI fails repeatedly.
- `60_ci-auto-heal.yml` — attempts automated remediation of common CI breakages.

## Quick Start

```bash
# Clone
git clone <repo-url> blacklist-service-management
cd blacklist-service-management

# Install git hooks (pre-commit + commitlint + husky)
make setup-hooks

# Start the development stack (hot reload)
make dev

# Open the app
open http://localhost:2542
```

The Makefile target `make dev` rebuilds changed images and starts the stack via `deploy/docker-compose.yml`. Use `make dev-no-build` for a faster start when images are already current.

## Local Development

| Command | Purpose |
| --- | --- |
| `make dev` | Start dev stack with rebuild + hot reload. |
| `make dev-no-build` | Start dev stack using existing images. |
| `make dev-prod` | Production-like stack, no hot reload. |
| `make dev-app` | Restart only the app service. |
| `make up` | Bring the stack up. |
| `make down` | Tear the stack down. |
| `make logs` | Tail logs from all services. |
| `make restart` | Restart the stack. |
| `make health` | Probe service health endpoints. |

### Verification Suite

| Command | Purpose |
| --- | --- |
| `make verify` | Run the full verification suite. |
| `make verify-lint` | Ruff lint only. |
| `make verify-types` | mypy type-check only. |
| `make verify-secrets` | Gitleaks secret scan only. |
| `make verify-pre-commit` | All pre-commit hooks. |
| `make verify-quick` | Lint + types (no tests). |
| `make verify-all` | Lint + types + secrets + tests. |

## Commands Reference

### Docker / Compose

```bash
make up            # docker compose up -d
make down          # docker compose down
make logs          # docker compose logs -f
make clean         # remove containers, volumes, build cache
make deploy        # production deploy
make prod          # production-mode stack
make release       # cut a release (CI-driven)
make release-dry   # dry-run release
```

### Testing (pytest)

Markers are defined in `pyproject.toml`:

- `unit` — fast tests with no external services.
- `integration` — tests that require live services.
- `security` — security-focused test cases.
- `db` — database-backed tests.
- `api` — REST endpoint tests.

```bash
pytest -m unit
pytest -m integration
pytest -m security
pytest -m "api or db"
```

### Linting & Types

```bash
ruff check app/
ruff format app/
mypy app/
pre-commit run --all-files
```

## Contribution Guide

1. Fork and create a topic branch (`feat/...`, `fix/...`, `chore/...`).
2. Follow Conventional Commits — enforced by `commitlint.config.js` and the commit-msg hook installed via `make setup-hooks`.
3. Before pushing, run `make verify-quick` locally; CI will run `make verify-all`.
4. Open a PR — `10_pr-review.yml` (PR-Agent) will review automatically, and `13_pr-auto-merge.yml` will merge once all required checks pass.
5. After merge, `15_merged-pr-cleanup.yml` removes the head branch; `24_release-notes.yml` will fold your change into the next release draft.

Security issues should NOT be filed as public issues — see `SECURITY` policy and `OWNERS` for contact channels.

---

<a id="한국어"></a>

# 한국어

## 개요

**Blacklist Service Management**는 블랙리스트 수집, 운영 모니터링, 역할 기반 API 접근, Fortinet 방화벽 통합, AI 기반 자동화를 단일 Flask 서비스로 통합한 Python 3.11 웹 애플리케이션입니다.

`app/` 하위의 런타임은 계층화된 아키텍처를 제공합니다:

- **Web 티어** — Flask 템플릿 (`templates/index.html`, `templates/collection.html`, `templates/sessions.html`, `templates/settings.html`, `templates/integrations.html`, `templates/collection_logs.html`, `templates/monitoring/dashboard.html`).
- **API 티어** — `app/core/routes/api/` 하위의 REST 엔드포인트 (analytics, auth, dashboard, database, error metrics, settings, system, Fortinet 등록, blacklist, collection, migration, IP 관리).
- **Realtime 티어** — 라이브 대시보드 갱신을 위한 WebSocket 라우트.
- **Integration 티어** — LLM 접근을 위해 **CLIProxyAPI** (`https://cliproxy.jclee.me/v1`)와 서비스를 연결하는 프록시 라우트 (주 모델 `gpt-5.5`, 폴백 `minimax-m3`).
- **Operations 티어** — 구조화 로깅, 로그 로테이션, 배포 검증, Docker 패키징.

자동화는 1급 시민입니다. 본 저장소는 브랜치, PR, 보안 스캔, 릴리스, 다운스트림 헬스 체크, 자가 치유를 관리하는 **20개의 GitHub Actions 워크플로우**를 포함합니다.

## 주요 기능

- Flask 3 웹 UI, 역할 기반 접근 제어 (RBAC) 및 JWT 기반 세션.
- 다중 소스 동기화 (`sources.py`), 자격증명 저장소 (`credentials.py`), 이력 (`history.py`)을 갖춘 중앙 집중식 블랙리스트 수집.
- Fortinet 방화벽 등록 및 IP 관리 헬퍼 (`fortinet_register.py`, `ip_management_helpers.py`).
- WebSocket, 구조화 JSON 로깅, 로그 로테이션 매니저, 배포 검증 (`deployment_validation.py`)을 통한 실시간 모니터링.
- **PR-Agent** (`qodo-ai/pr-agent`) 및 **Codex** 자동화로 구동되는 AI 기반 워크플로우.
- 컨테이너 우선 배포: `app/Dockerfile`, `app/entrypoint.sh`, `app/run_app.py`, Makefile 기반의 `make dev` / `make deploy` 라이프사이클.

## 아키텍처

```mermaid
flowchart TB
    subgraph Client["클라이언트 영역"]
        Browser["웹 브라우저<br/>(Flask 템플릿)"]
        Operator["운영자 CLI / 스크립트"]
        Fortinet["Fortinet 게이트웨이"]
    end

    subgraph App["app/ - Flask 서비스"]
        WebTier["Web 티어<br/>core/routes/web_routes.py"]
        APITier["API 티어<br/>core/routes/api_routes.py<br/>+ api/* 블루프린트"]
        WSTier["Realtime 티어<br/>core/routes/websocket_routes.py"]
        ProxyTier["Integration 티어<br/>core/routes/proxy_routes.py"]
        OpsTier["Operations 티어<br/>structured_logging.py<br/>log_rotation_manager.py<br/>deployment_validation.py"]
        Auth["Auth 계층<br/>core/auth/<br/>jwt_service, middleware, decorators"]
        Monitoring["모니터링<br/>core/monitoring/<br/>metrics, cache_metrics, error_metrics"]
    end

    subgraph Data["데이터 영역"]
        BlacklistStore["블랙리스트 저장소"]
        SettingsDB["설정 / 세션 DB"]
        LogSink["구조화 로그 싱크"]
    end

    subgraph Ext["외부 서비스"]
        CLIP["CLIProxyAPI<br/>https://cliproxy.jclee.me/v1<br/>gpt-5.5 / minimax-m3"]
        Homelab["Homelab 호스트<br/>CLIProxy["&lt;homelab-host&gt;:8317<br/>CLIProxyAPI"]"]
        ELK["ELK 스택<br/>&lt;homelab-elk&gt;<br/>로그 수집"]
        Bot["자동화 봇<br/>https://bot.jclee.me"]
    end

    Browser -->|HTTPS| WebTier
    Operator -->|REST| APITier
    Fortinet -->|REST| APITier
    WebTier --> APITier
    WebTier --> WSTier
    APITier --> Auth
    APITier --> Monitoring
    APITier --> BlacklistStore
    APITier --> SettingsDB
    WSTier --> Monitoring
    ProxyTier -->|HTTPS| CLIP
    ProxyTier -.폴백.-> Homelab
    App --> OpsTier
    OpsTier --> LogSink
    OpsTier -->|전송| ELK
    Bot -. 오케스트레이션 .-> App
```

## 자동화 인벤토리

본 저장소는 `.github/workflows/` 하위에 **20개의 GitHub Actions 워크플로우**를 제공합니다. 수명 주기 단계별로 그룹화되어 있으며 실제 디스크 상의 파일명으로 기재합니다.

### 이슈 및 브랜치 라이프사이클

- `01_branch-to-branch.yml` — 이슈를 작업 브랜치로 승격합니다.
- `02_issue-to-branch.yml` — 추적 중인 이슈를 메타데이터가 포함된 기능 브랜치로 변환합니다.
- `19_issue-backfill.yml` — 기존 이슈의 누락된 라벨 및 메타데이터를 보강합니다.
- `91_issue-classification.yml` — 신규 이슈를 주제와 심각도 기준으로 자동 분류합니다.
- `15_merged-pr-cleanup.yml` — PR 머지 후 헤드 브랜치를 삭제합니다.

### 풀 리퀘스트 자동화

- `10_pr-review.yml` — 모든 PR에 대해 PR-Agent (`qodo-ai/pr-agent`) 코드 리뷰를 수행합니다.
- `11_security-pr-review.yml` — 보안 위협 모델 컨텍스트를 포함한 보안 중심 PR 리뷰를 수행합니다.
- `12_dependabot-auto-merge.yml` — Dependabot 패치 업데이트를 자동 머지합니다.
- `13_pr-auto-merge.yml` — 필수 체크를 통과한 PR을 스쿼시 머지합니다.
- `14_bot-auto-fix.yml` — 린트, 타입, 사소한 수정 사항을 봇이 자동 수정합니다.

### 지속적 통합 (CI)

- `ci.yml` — 메인 파이프라인 (린트, 타입 검사, 단위, 통합).
- `_ci-node.yml` — `ci.yml`에서 호출되는 Node.js 프런트엔드 CI 헬퍼.
- `build-images.yml` — 컨테이너 이미지를 빌드하고 태깅합니다.
- `security.yml` — CodeQL 정적 분석과 OpenSSF Scorecard 체크를 수행합니다.

### 릴리스 엔지니어링

- `24_release-notes.yml` — 머지된 PR로부터 릴리스 노트를 초안 작성합니다.
- `25_release-publish.yml` — 아티팩트와 변경 로그를 포함하여 GitHub Release를 게시합니다.
- `release.yml` — 엔드투엔드 릴리스 플로우를 오케스트레이션합니다.

### 안정성 및 자가 치유

- `29_downstream-health-check.yml` — 다운스트림 서비스를 프로빙하고 상태를 게시합니다.
- `37_ci-failure-issues.yml` — CI가 반복적으로 실패할 경우 추적용 이슈를 등록합니다.
- `60_ci-auto-heal.yml` — 일반적인 CI 장애를 자동 복구합니다.

## 빠른 시작

```bash
# 클론
git clone <repo-url> blacklist-service-management
cd blacklist-service-management

# Git 훅 설치 (pre-commit + commitlint + husky)
make setup-hooks

# 개발 스택 시작 (핫 리로드)
make dev

# 앱 열기
open http://localhost:2542
```

`make dev` 타깃은 변경된 이미지를 리빌드하고 `deploy/docker-compose.yml`을 통해 스택을 기동합니다. 이미 최신일 경우 더 빠르게 시작하려면 `make dev-no-build`를 사용하세요.

## 로컬 개발

| 명령어 | 설명 |
| --- | --- |
| `make dev` | 리빌드 + 핫 리로드로 개발 스택 시작. |
| `make dev-no-build` | 기존 이미지로 개발 스택 시작. |
| `make dev-prod` | 프로덕션 유사 스택, 핫 리로드 없음. |
| `make dev-app` | 앱 서비스만 재시작. |
| `make up` | 스택을 기동. |
| `make down` | 스택을 종료. |
| `make logs` | 모든 서비스 로그를 tail. |
| `make restart` | 스택 재시작. |
| `make health` | 서비스 헬스 엔드포인트 프로빙. |

### 검증 스위트

| 명령어 | 설명 |
| --- | --- |
| `make verify` | 전체 검증 스위트 실행. |
| `make verify-lint` | Ruff 린트만. |
| `make verify-types` | mypy 타입 검사만. |
| `make verify-secrets` | Gitleaks 시크릿 스캔만. |
| `make verify-pre-commit` | 모든 pre-commit 훅. |
| `make verify-quick` | 린트 + 타입 (테스트 제외). |
| `make verify-all` | 린트 + 타입 + 시크릿 + 테스트. |

## 명령어 레퍼런스

### Docker / Compose

```bash
make up            # docker compose up -d
make down          # docker compose down
make logs          # docker compose logs -f
make clean         # 컨테이너, 볼륨, 빌드 캐시 제거
make deploy        # 프로덕션 배포
make prod          # 프로덕션 모드 스택
make release       # 릴리스 컷 (CI 기반)
make release-dry   # 릴리스 드라이런
```

### 테스트 (pytest)

`pyproject.toml`에 정의된 마커:

- `unit` — 외부 서비스가 필요 없는 빠른 테스트.
- `integration` — 라이브 서비스가 필요한 테스트.
- `security` — 보안 중심 테스트.
- `db` — 데이터베이스 기반 테스트.
- `api` — REST 엔드포인트 테스트.

```bash
pytest -m unit
pytest -m integration
pytest -m security
pytest -m "api or db"
```

### 린트 및 타입

```bash
ruff check app/
ruff format app/
mypy app/
pre-commit run --all-files
```

## 기여 가이드

1. 포크 후 토픽 브랜치를 생성합니다 (`feat/...`, `fix/...`, `chore/...`).
2. Conventional Commits를 따릅니다 — `commitlint.config.js` 및 `make setup-hooks`로 설치되는 commit-msg 훅이 강제합니다.
3. 푸시 전에 로컬에서 `make verify-quick`를 실행합니다. CI는 `make verify-all`을 수행합니다.
4. PR을 엽니다 — `10_pr-review.yml` (PR-Agent)이 자동 리뷰하며, 모든 필수 체크를 통과하면 `13_pr-auto-merge.yml`이 머지합니다.
5. 머지 후 `15_merged-pr-cleanup.yml`이 헤드 브랜치를 제거하고, `24_release-notes.yml`이 변경 사항을 다음 릴리스 초안에 포함합니다.

보안 이슈는 공개 이슈로 등록하지 마세요 — `SECURITY` 정책 및 `OWNERS`의 연락 채널을 참고하세요.