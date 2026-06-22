# Blacklist Service / 블랙리스트 서비스

[![CI](https://img.shields.io/badge/CI-jclee--bot%20owned-blueviolet)](#jclee-bot-automation-surfaces--jclee-bot-자동화-영역)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](#local-development--로컬-개발)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED?logo=docker&logoColor=white)](#quick-start--빠른-시작)
[![Code style: Ruff](https://img.shields.io/badge/lint-ruff-D7FF64?logo=ruff&logoColor=black)](pyproject.toml)
[![Types: mypy](https://img.shields.io/badge/types-mypy-2A6DB2)](mypy.ini)
[![Conventional Commits](https://img.shields.io/badge/commits-conventional-FE5196)](commitlint.config.js)
[![PR reviews: qodo-ai/pr-agent](https://img.shields.io/badge/PR%20review-qodo--ai%2Fpr--agent-FF6F61)](https://github.com/qodo-ai/pr-agent)
[![License](https://img.shields.io/badge/license-see%20LICENSE-lightgrey)](LICENSE)

> **TL;DR / 요약**
> A self-hosted Python web service that centralises **blacklist management**, **source collection**, and **Fortinet gateway** push, with JWT-based access control, structured logging, and a real-time WebSocket monitoring dashboard. / Fortinet 게이트웨이 푸시, JWT 기반 접근 제어, 구조화된 로깅, 실시간 WebSocket 모니터링 대시보드를 갖춘 셀프 호스팅 Python 웹 서비스로, **블랙리스트 관리**와 **소스 수집**을 중앙 집중화합니다.

---

## Overview / 개요

Blacklist Service is a Flask-based application that ingests IP / domain threat intelligence from external sources, normalises and stores it, and pushes curated entries to a Fortinet gateway on demand or on schedule. It ships with a web UI, a JSON API, a WebSocket channel for live metrics, and a deployment validation pipeline.

Blacklist Service는 외부 소스에서 IP/도메인 위협 인텔리전스를 수집·정규화·저장하고, 필요 시 또는 스케줄에 따라 Fortinet 게이트웨이로 푸시하는 Flask 기반 애플리케이션입니다. Web UI, JSON API, 실시간 메트릭용 WebSocket 채널, 배포 검증 파이프라인을 함께 제공합니다.

The repository is **app-first**: automation surfaces are owned by the **jclee-bot** account, while the Python service is the only first-party runtime. Workflow files under `.github/workflows/` are *implementation triggers* — the *source of truth* for automation behaviour is this README and the project's `AGENTS.md` files.

이 저장소는 **애플리케이션 중심**입니다. 자동화 영역은 **jclee-bot** 계정이 소유하며, Python 서비스가 유일한 1차 런타임입니다. `.github/workflows/`의 워크플로 파일은 *구현 트리거*이며, 자동화 동작의 *진실의 근원(SSOT)* 은 본 README와 프로젝트 내 `AGENTS.md` 입니다.

---

## Features / 주요 기능

- **Centralised Blacklist CRUD** — manage IP / domain entries through a REST API and a Jinja2-rendered web UI (`app/templates/`, `app/core/routes/api/blacklist/`).
- **Source Collection** — pull threat intel from configured external sources, with credential storage, history, sync triggers, and per-source status (`app/core/routes/api/collection/`).
- **Fortinet Push** — register the service with a Fortinet gateway, push curated rules, and reconcile state (`app/core/routes/api/fortinet/core.py`, `fortinet_register.py`).
- **JWT-based Access Control** — token issuance, refresh, and request-level decorators and middleware (`app/core/auth/`).
- **Real-time Monitoring** — WebSocket dashboard, cache and error metrics, structured logs with rotation (`app/core/monitoring/`, `app/core/routes/websocket_routes.py`).
- **Deployment Validation** — `app/deployment_validation.py` runs pre-flight checks before the service accepts traffic.
- **Husky + Pre-commit Toolchain** — conventional commits, Ruff, mypy, and secret scanning enforced locally and in CI.

---

## Architecture / 아키텍처

The Flask app sits at the centre, behind a reverse proxy, and is the only first-party runtime in this repo. Structured logs and metrics flow to an external ELK stack; the LLM-backed automation layer is reached through the public CLIProxyAPI endpoint. / Flask 앱은 리버스 프록시 뒤 중앙에 위치하며, 본 저장소의 유일한 1차 런타임입니다. 구조화된 로그와 메트릭은 외부 ELK 스택으로 흐르고, LLM 기반 자동화 계층은 공개 CLIProxyAPI 엔드포인트를 통해 연결됩니다.

```mermaid
flowchart TB
    Client["Client Browser<br/>Web UI / WS Client"]
    Proxy["Reverse Proxy<br/>HTTPS / WSS termination"]
    Web["Web Routes<br/>app/core/routes/web_routes.py"]
    API["REST API<br/>app/core/routes/api_routes.py"]
    WS["WebSocket<br/>app/core/routes/websocket_routes.py"]
    App["Flask Application<br/>app/run_app.py -&gt; app/core/app.py"]

    Auth["Auth Layer<br/>app/core/auth/"]
    Mon["Monitoring<br/>app/core/monitoring/"]

    Coll["Collection Service<br/>app/core/routes/api/collection/"]
    BL["Blacklist Service<br/>app/core/routes/api/blacklist/"]
    Forti["Fortinet Service<br/>app/core/routes/api/fortinet/"]
    Settings["Settings / System API<br/>api/settings_api.py, api/system_api.py"]
    Dash["Dashboard API<br/>api/dashboard_api.py, api/analytics.py"]

    Sources["External Blacklist Sources"]
    FortiGW["Fortinet Gateway"]
    ELK["ELK / Observability<br/>&lt;homelab-elk&gt;"]
    LLM["LLM Proxy Endpoint<br/>https://cliproxy.jclee.me/v1"]

    Client --&gt; Proxy
    Proxy --&gt; Web
    Proxy --&gt; API
    Proxy --&gt; WS
    Web --&gt; App
    API --&gt; App
    WS --&gt; App

    App --&gt; Auth
    App --&gt; Mon
    API --&gt; Coll
    API --&gt; BL
    API --&gt; Forti
    API --&gt; Settings
    API --&gt; Dash
    Mon --&gt; LLM

    Coll --&gt;|fetch| Sources
    Forti --&gt;|push rules| FortiGW
    App --&gt;|structured logs| ELK
```

> Placeholders like `&lt;homelab-elk&gt;` and the `cliproxy.jclee.me` endpoint are *intentional* — they identify the role of each neighbour without leaking private addressing.

---

## jclee-bot Automation Surfaces / jclee-bot 자동화 영역

All mutating automation in this repository is owned by the **jclee-bot** GitHub account. The workflow YAML files under `.github/workflows/` are only the *trigger implementations*; behaviour, ownership, and trust boundaries are described here.

본 저장소의 모든 변경을 일으키는(mutating) 자동화는 **jclee-bot** GitHub 계정이 소유합니다. `.github/workflows/` 의 워크플로 YAML 파일은 *트리거 구현체*일 뿐이며, 동작·소유·신뢰 경계는 본 섹션에서 정의합니다.

### Issue Automation / 이슈 자동화

- New issues are auto-triaged, auto-labelled, and (where appropriate) promoted into a PR-ready branch by jclee-bot. This is the **jclee-bot에의해자동화됨** surface — opening an issue can result in a branch and pull request without further human action.
- Stale and locked threads, Dependabot follow-ups, and CI-failure issues are all funnelled through the same bot identity to keep audit trails single-authored.
- Backfill and lifecycle jobs reconcile historical issues when governance policy changes.

### Pull Request Automation / 풀 리퀘스트 자동화

- **Branch → PR promotion** for branches cut by jclee-bot (via the `01_*` / `02_*` workflow triggers).
- **Code review** delegated to `qodo-ai/pr-agent` for general feedback, and a separate **security review** pass for sensitive paths.
- **Auto-merge** for Dependabot PRs and trusted PRs that pass required checks, with the bot identity acting as the committer.
- **Auto-fix** application: jclee-bot opens a follow-up PR when a review surfaces a mechanically-fixable problem.
- **Branch cleanup** after a PR is merged to keep the working tree small.

### Release Automation / 릴리스 자동화

- Release notes are drafted from conventional-commit history and the published release is cut, tagged, and pushed by jclee-bot. The `VERSION` file at the repository root is the single source for the next version string.

### Continuous Integration & Build / 지속적 통합 및 빌드

- Python CI runs the test matrix, Ruff, and mypy; the reusable Node CI surface is available for the bundled frontend tooling; security scanning runs on every push and pull request.
- Container images are built by `build-images.yml` and published as part of the release flow.

### Downstream Health / 다운스트림 상태 점검

- A periodic workflow checks the health of downstream consumers (e.g., the Fortinet gateway, the ELK ingest endpoint) and opens a jclee-bot-authored issue when a regression is detected.

---

## Go Tools / Go 도구

This repository ships **no first-party Go tools**. The runtime is pure Python, and the only Go code that touches the project is the README-generation pipeline itself:

본 저장소에는 **1차 Go 도구가 포함되어 있지 않습니다**. 런타임은 순수 Python이며, 본 저장소를 다루는 유일한 Go 코드는 README 생성 파이프라인 자체입니다.

- **Primary model / 기본 모델**: `gpt-5.5`
- **Fallback / 폴백**: `minimax-m3`, reached through the public CLIProxyAPI endpoint at `https://cliproxy.jclee.me/v1`.

If a future contribution needs to add a Go-based helper (for example, a fast log normaliser or an ELK shipper binary), it should live under a clearly-named directory and be added to the CI matrix in `ci.yml`.

향후 Go 기반 헬퍼(예: 빠른 로그 정규화기, ELK 셔이퍼 바이너리 등)가 추가된다면, 명확한 이름의 디렉터리에 배치하고 `ci.yml` 의 CI 매트릭스에 등록해야 합니다.

---

## Repository Layout / 저장소 구조

The layout below reflects the **actual** top-level files and the `app/` tree. The transient CI checkout path `_bot-scripts/` is *not* a permanent directory and is intentionally omitted.

아래 레이아웃은 **실제** 최상위 파일과 `app/` 트리를 반영합니다. 일회성 CI 체크아웃 경로인 `_bot-scripts/` 는 영구 디렉터리가 아니므로 의도적으로 제외했습니다.

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
└── app/
    ├── AGENTS.md
    ├── Dockerfile
    ├── __init__.py
    ├── deployment_validation.py
    ├── entrypoint.sh
    ├── requirements.txt
    ├── run_app.py
    ├── utils/
    │   ├── log_rotation_manager.py
    │   └── structured_logging.py
    ├── templates/
    │   ├── collection.html
    │   ├── collection_logs.html
    │   ├── index.html
    │   ├── integrations.html
    │   ├── sessions.html
    │   ├── settings.html
    │   └── monitoring/
    │       └── dashboard.html
    └── core/
        ├── AGENTS.md
        ├── __init__.py
        ├── app.py
        ├── auth_manager.py
        ├── config.py
        ├── dashboard.py
        ├── testing_app.py
        ├── auth/
        │   ├── AGENTS.md
        │   ├── __init__.py
        │   ├── decorators.py
        │   ├── jwt_service.py
        │   └── middleware.py
        ├── monitoring/
        │   ├── AGENTS.md
        │   ├── __init__.py
        │   ├── cache_metrics.py
        │   ├── error_metrics.py
        │   └── metrics.py
        └── routes/
            ├── AGENTS.md
            ├── api_routes.py
            ├── collection_routes_simple.py
            ├── proxy_routes.py
            ├── system_routes.py
            ├── web_routes.py
            ├── websocket_routes.py
            └── api/
                ├── AGENTS.md
                ├── __init__.py
                ├── analytics.py
                ├── auth_routes.py
                ├── core_api.py
                ├── dashboard_api.py
                ├── database_api.py
                ├── error_metrics_api.py
                ├── fortinet_register.py
                ├── ip_management_helpers.py
                ├── migration.py
                ├── settings_api.py
                ├── system_api.py
                ├── monitoring/
                │   └── __init__.py
                │   └── metrics.py
                ├── collection/
                │   ├── AGENTS.md
                │   ├── __init__.py
                │   ├── config.py
                │   ├── credentials.py
                │   ├── history.py
                │   ├── sources.py
                │   ├── status.py
                │   ├── sync.py
                │   ├── trigger.py
                │   └── utils.py
                ├── blacklist/
                │   ├── AGENTS.md
                │   ├── __init__.py
                │   ├── batch.py
                │   ├── collection.py
                │   ├── core.py
                │   ├── management.py
                │   └── system.py
                └── fortinet/
                    ├── AGENTS.md
                    ├── __init__.py
                    └── core.py
```

---

## Quick Start / 빠른 시작

The fastest way to run the service is via the bundled `Makefile`, which wraps `docker compose` with the project's own environment file.

가장 빠른 실행 경로는 프로젝트의 환경 파일을 사용하는 `docker compose` 를 감싼 번들 `Makefile` 을 통하는 것입니다.

1. **Clone and configure / 클론 및 설정**

   ```bash
   git clone <your-fork-or-mirror>.git blacklist-service
   cd blacklist-service
   cp deploy/.env.example deploy/.env   # then edit secrets, Fortinet endpoint, JWT keys
   ```

2. **Start the development stack with hot reload / 핫 리로드 개발 스택 시작**

   ```bash
   make dev
   ```

   This rebuilds changed images and starts every service defined in `deploy/docker-compose.yml`. The app becomes available at `http://localhost:2542` by default.

3. **Open the web UI and log in / Web UI 열기 및 로그인**

   The bundled `entrypoint.sh` runs `app/deployment_validation.py` first; on success the Flask app is launched. JWT credentials are issued through `app/core/routes/api/auth_routes.py`.

4. **Run a smoke test / 스모크 테스트 실행**

   ```bash
   make verify-quick
   ```

---

## Local Development / 로컬 개발

For day-to-day development outside Docker (or inside the dev container), the toolchain is described in `pyproject.toml`, `mypy.ini`, and the `Makefile` `verify-*` targets.

Docker 외부(또는 개발 컨테이너 내부)에서의 일상적인 개발을 위해, 툴체인은 `pyproject.toml`, `mypy.ini`, 그리고 `Makefile` 의 `verify-*` 타깃에 정의되어 있습니다.

- **Python / 파이썬**: 3.11+
- **Lint / 린트**: Ruff (`pyproject.toml` → `[tool.ruff]`)
- **Types / 타입**: mypy (`mypy.ini`)
- **Tests / 테스트**: pytest with markers for `unit`, `integration`, `security`, `db`, `api`
- **Pre-commit / 프리커밋**: install with `make setup-hooks`. The hook chain runs Ruff, mypy, secret scanning, conventional-commit validation, and the frontend Husky hooks.
- **Frontend hooks / 프론트엔드 훅**: `cd frontend && npm install` is invoked by `make setup-hooks` to wire Husky.

### Common loops / 자주 쓰는 루프

```bash
# Lint everything / 전체 린트
make verify-lint

# Type-check / 타입 검사
make verify-types

# Secret scan / 시크릿 스캔
make verify-secrets

# Pre-commit dry run / 프리커밋 드라이런
make verify-pre-commit

# Full battery / 전체 검증
make verify-all
```

### Reading logs / 로그 확인

Application logs are written through `app/utils/structured_logging.py` with rotation handled by `app/utils/log_rotation_manager.py`. The `collection_logs.html` template exposes a UI to browse them, and a copy is shipped to the ELK endpoint identified by the `&lt;homelab-elk&gt;` placeholder in this README.

애플리케이션 로그는 `app/utils/structured_logging.py` 를 통해 기록되며, 로테이션은 `app/utils/log_rotation_manager.py` 가 처리합니다. `collection_logs.html` 템플릿에서 UI로 열람할 수 있으며, 본 README의 `&lt;homelab-elk&gt;` 플레이스홀더로 식별되는 ELK 엔드포인트에도 복사본이 전송됩니다.

---

## Commands Reference / 명령어 레퍼런스

The `Makefile` is the canonical entry point. Run `make help` for an auto-generated, colourised listing. The most common targets are:

`Makefile` 이 정식 진입점입니다. `make help` 로 자동 생성된 컬러 목록을 확인할 수 있습니다. 가장 자주 사용하는 타깃은 다음과 같습니다.

| Command | Purpose / 용도 |
| --- | --- |
| `make setup-hooks` | Install pre-commit, commit-msg hook, and Husky for the frontend. / 프리커밋, 커밋 메시지 훅, 프론트엔드용 Husky 설치. |
| `make dev` | Start the development stack with hot reload (rebuilds changed images). / 핫 리로드 개발 스택 시작 (변경된 이미지 재빌드). |
| `make dev-no-build` | Start the dev stack using existing images. / 기존 이미지로 개발 스택 시작. |
| `make dev-prod` | Production-like run with no override and no hot reload. / 오버라이드/핫 리로드 없는 프로덕션 유사 실행. |
| `make dev-app` | Restart only the `app` service. / `app` 서비스만 재시작. |
| `make up` / `make down` | Bring the compose stack up / tear it down. / 컴포즈 스택 기동 / 종료. |
| `make logs` | Tail compose logs. / 컴포즈 로그 tail. |
| `make restart` | Restart the stack. / 스택 재시작. |
| `make health` | Probe service health endpoints. / 서비스 헬스 엔드포인트 점검. |
| `make test` | Run the pytest suite. / pytest 스위트 실행. |
| `make verify-lint` | Ruff only. / Ruff만 실행. |
| `make verify-types` | mypy only. / mypy만 실행. |
| `make verify-secrets` | Secret-detection scan. / 시크릿 탐지 스캔. |
| `make verify-pre-commit` | Run the full pre-commit chain. / 전체 프리커밋 체인 실행. |
| `make verify-quick` | Fast subset of verifications for local iteration. / 로컬 반복 작업을 위한 빠른 검증 묶음. |
| `make verify-all` | Run every verification step. / 모든 검증 단계 실행. |
| `make build` | Build all images without starting them. / 시작 없이 모든 이미지 빌드. |
| `make deploy` | Deploy to the configured target. / 구성된 대상에 배포. |
| `make prod` | Switch to the production compose profile. / 프로덕션 컴포즈 프로파일로 전환. |
| `make clean` | Remove containers, images, and build artefacts. / 컨테이너/이미지/빌드 산출물 제거. |
| `make release` | Cut a release (delegated to jclee-bot). / 릴리스 생성 (jclee-bot 에 위임). |
| `make release-dry` | Preview release notes and changelog. / 릴리스 노트/체인지로그 미리보기. |

> Anything not listed here is documented in the `Makefile` itself; the file is the authoritative spec.

> 위에 나열되지 않은 항목은 `Makefile` 본문에서 그대로 확인하실 수 있으며, `Makefile` 이 권위 있는 명세입니다.

---

## Contributing / 기여 가이드

1. **Read the AGENTS files first / AGENTS 파일을 먼저 읽으세요.** Every subsystem has its own `AGENTS.md` (root, `app/`, `app/core/`, `app/core/auth/`, `app/core/monitoring/`, `app/core/routes/`, `app/core/routes/api/`, and the `collection/`, `blacklist/`, `fortinet/` subpackages). They define local conventions that take precedence over this README.
2. **Open an issue or let jclee-bot open one for you / 이슈를 직접 열거나 jclee-bot 이 대신 열도록 하세요.** Issue automation is the **jclee-bot에의해자동화됨** surface: simply describing the problem is usually enough to trigger triage, labelling, and a draft branch.
3. **Use Conventional Commits / 컨벤셔널 커밋 사용.** The chain is enforced by commitlint (`commitlint.config.js`) and Husky.
4. **Run `make verify-quick` locally before pushing / 푸시 전 `make verify-quick` 로컬 실행.** CI will run the same chain plus the full matrix.
5. **Do not commit secrets or hardcoded endpoints / 시크릿이나 하드코딩된 엔드포인트를 커밋하지 마세요.** Use `deploy/.env` and reference placeholders (`&lt;homelab-host&gt;`, `&lt;homelab-elk&gt;`, `https://cliproxy.jclee.me/v1`) in documentation.
6. **Trust the bot, audit the diff / 봇을 신뢰하되 diff 는 감사하세요.** All mutating automation is performed by jclee-bot, but every bot PR is reviewable. Security-sensitive changes go through the dedicated security PR review workflow.

---

## License / 라이선스

See [LICENSE](LICENSE). Third-party components retain their own licences; the only external integrations explicitly endorsed in this README are the [qodo-ai/pr-agent](https://github.com/qodo-ai/pr-agent) PR-review tooling and the public endpoints `https://cliproxy.jclee.me` and `https://bot.jclee.me`.