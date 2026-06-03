# Blacklist Service Management

## English | [한국어](#한국어)

---

[![CI Checks](https://github.com/qws941/BlacklistService/actions/workflows/03_pr-checks.yml/badge.svg)](https://github.com/qws941/BlacklistService/actions/workflows/03_pr-checks.yml)
[![Release](https://github.com/qws941/BlacklistService/actions/workflows/release.yml/badge.svg)](https://github.com/qws941/BlacklistService/actions/workflows/release.yml)
[![CodeQL](https://github.com/qws941/BlacklistService/actions/workflows/06_codeql.yml/badge.svg)](https://github.com/qws941/BlacklistService/actions/workflows/06_codeql.yml)
[![Scorecard](https://github.com/qws941/BlacklistService/actions/workflows/08_scorecard.yml/badge.svg)](https://github.com/qws941/BlacklistService/actions/workflows/08_scorecard.yml)
[![GitHub Security Best Practices](https://img.shields.io/badge/GitHub-Security%20Best%20Practices-blue)](https://github.com/qws941/BlacklistService/security)

[![Python Version](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-Proprietary-red)](LICENSE)

---

## Overview

**Blacklist Service Management** is a threat intelligence platform that collects, processes, and distributes IP blacklist data from the Korea Financial Security Institute (REGTECH). It integrates with FortiGate firewalls and Cloudflare WAF to automatically gather malicious IP lists.

### Key Components

| Component | Description |
|-----------|-------------|
| `collector/` | Main Python data collector with modular architecture |
| `postgres/` | PostgreSQL database with schema and migration management |
| `_bot-scripts/` | GitHub automation scripts (internal CI use only) |

---

## Features

- **Multi-Source Collection**: Automatic IP blacklist collection from REGTECH, FortiGate, and multiple external sources
- **Data Quality Management**: Integrity validation and deduplication of collected data
- **Automatic Archiving**: Daily/monthly backups with incremental archive support
- **Policy Monitoring**: Real-time tracking of blacklist policy changes
- **Rate Limiting**: API call throttling to ensure service stability
- **Database Management**: PostgreSQL-based storage with versioned migrations
- **Docker Deployment**: Containerized application and database services
- **Comprehensive Testing**: Unit, integration, security, database, and API tests
- **GitHub Automation**: 38 automated workflows for code quality and release management

---

## Architecture

```mermaid
flowchart TB
    subgraph DataSources["Data Sources"]
        REGTECH["REGTECH API<br/>Korea Financial<br/>Security Institute"]
        FORTIGATE["FortiGate Firewall<br/>Fortinet Firewall"]
        MULTI["Multi-Source Collector<br/>External Sources"]
        CLOUDFLARE["Cloudflare WAF<br/>Web Application<br/>Firewall"]
    end

    subgraph Collector["collector/ Collector"]
        CORE["core/ Core Modules"]
        SCHEDULER["scheduler/ Scheduler"]
        API["api/ API Server"]

        CORE --> FORTIGATE
        CORE --> REGTECH
        CORE --> MULTI
    end

    subgraph Database["postgres/ Database"]
        PG["PostgreSQL<br/>Database"]
        MIGRATIONS["migrations/ Migrations"]
    end

    subgraph GitHubAutomation["GitHub Automation"]
        WORKFLOWS[".github/workflows/<br/>38 Workflows"]
        BOTS["GitHub Bot Scripts<br/>qodo-ai/pr-agent"]
    end

    subgraph ExternalServices["External Services"]
        ELK["ELK Stack<br/>&lt;homelab-elk&gt;"]
        PROXY["CLIProxyAPI<br/>https://cliproxy.jclee.me/v1"]
    end

    DataSources --> Collector
    Collector --> Database
    Collector --> GitHubAutomation
    GitHubAutomation -->|"Workflow Trigger"| Collector
    Collector --> ELK
    Collector --> PROXY
```

---

## Automation Inventory

### GitHub Workflows (38 Total)

| # | Workflow File | Purpose |
|---|---------------|---------|
| 01 | `01_branch-to-pr.yml` | Branch to PR conversion |
| 02 | `02_issue-to-branch.yml` | Issue to feature branch |
| 03 | `03_pr-checks.yml` | PR validation checks |
| 04 | `04_actionlint.yml` | Workflow file linting |
| 05 | `05_gitleaks.yml` | Secret detection |
| 06 | `06_codeql.yml` | Code security analysis |
| 07 | `07_dependency-review.yml` | Dependency vulnerability review |
| 08 | `08_scorecard.yml` | OpenSSF Scorecard assessment |
| 09 | `09_semantic-pr.yml` | Semantic PR validation |
| 10 | `10_pr-review.yml` | Automated PR review |
| 12 | `12_dependabot-auto-merge.yml` | Dependabot auto-merge |
| 13 | `13_pr-auto-merge.yml` | PR auto-merge |
| 14 | `14_bot-auto-fix.yml` | Bot automated fixes |
| 15 | `15_merged-pr-cleanup.yml` | Post-merge cleanup |
| 18 | `18_issue-management.yml` | Issue management |
| 19 | `19_issue-backfill.yml` | Issue backfill |
| 20 | `20_readme-gen.yml` | README generation |
| 21 | `21_docs-sync.yml` | Documentation sync |
| 24 | `24_release-notes.yml` | Release notes draft |
| 25 | `25_release-publish.yml` | Release publishing |
| 29 | `29_downstream-health-check.yml` | Downstream service health |
| 37 | `37_ci-failure-issues.yml` | CI failure issue creation |
| 42 | `42_reusable-docs-sync.yml` | Reusable docs sync |
| 43 | `43_reusable-issue-management.yml` | Reusable issue management |
| 44 | `44_reusable-pr-checks.yml` | Reusable PR checks |
| 45 | `45_reusable-gitleaks.yml` | Reusable secret detection |
| 60 | `60_ci-auto-heal.yml` | CI self-healing |
| 91 | `91_issue-classification.yml` | Issue classification |
| - | `_ci-node.yml` | Node.js CI reusable workflow |
| - | `auto-merge.yml` | Auto-merge workflow |
| - | `build-images.yml` | Docker image build |
| - | `ci.yml` | Main CI workflow |
| - | `labeler.yml` | PR labeler |
| - | `release.yml` | Release workflow |
| - | `security.yml` | Security scanning |
| - | `standard-ci.yml` | Standard CI workflow |
| - | `welcome.yml` | Welcome message |
| - | `security/11_pr-review.yml` | Security PR review |

### GitHub Automation Tools

| Tool | Purpose |
|------|---------|
| [qodo-ai/pr-agent](https://github.com/qodo-ai/pr-agent) | Automated PR review and coding assistance |
| CLIProxyAPI (`https://cliproxy.jclee.me/v1`) | CLI Proxy API for bot operations |
| bot.jclee.me | Bot service endpoint |

### Testing Tools

| Tool | Configuration |
|------|---------------|
| pytest | `pyproject.toml` - markers: unit, integration, security, db, api |
| ruff | `pyproject.toml` - linting (E, F, W rules) |
| mypy | `mypy.ini` - type checking |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL (via Docker)

### Installation

```bash
# Clone the repository
git clone https://github.com/qws941/BlacklistService.git
cd BlacklistService

# Install dependencies
pip install -r collector/requirements.txt

# Setup git hooks
make setup-hooks
```

### Running with Docker Compose

```bash
# Start all services (development with hot reload)
make dev

# Or start without rebuilding
make dev-no-build

# Check service health
make health
```

### Access Points

| Service | URL |
|---------|-----|
| Application | <http://localhost:2542> |
| Health Check | <http://localhost:2542/health> |

---

## Local Development

### Environment Variables

Create a `.env` file in `deploy/` directory:

```env
# Application
PORT=2542
DATABASE_URL=postgresql://user:pass@postgres:5432/blacklist

# External Services
ELK_HOST=<homelab-elk>
CLI_PROXY_URL=https://cliproxy.jclee.me/v1

# API Keys (REGTECH, FortiGate, Cloudflare)
REGTECH_API_KEY=your_regtech_key
FORTIGATE_HOST=your_fortigate_host
CLOUDFLARE_API_KEY=your_cloudflare_key
```

### Database Setup

```bash
# Run migrations
make db-migrate

# Check migration status
make db-status
```

### Running Tests

```bash
# All tests
make test

# Quick test (unit tests only)
make verify-quick

# Full verification
make verify-all
```

---

## Commands Reference

### Makefile Targets

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make setup-hooks` | Install git hooks (pre-commit, commit-msg) |
| `make dev` | Start development with hot reload |
| `make dev-no-build` | Start without rebuilding images |
| `make dev-prod` | Start production-like environment |
| `make dev-app` | Restart only app service |
| `make up` | Start all services |
| `make down` | Stop all services |
| `make logs` | View container logs |
| `make clean` | Clean up containers and volumes |
| `make test` | Run test suite |
| `make health` | Check service health |
| `make release` | Create release |
| `make release-dry` | Dry-run release |
| `make verify` | Run all verifications |
| `make verify-lint` | Run ruff linter |
| `make verify-types` | Run mypy type checker |
| `make verify-secrets` | Run secret detection |
| `make verify-pre-commit` | Run pre-commit hooks |
| `make verify-quick` | Run quick verification |
| `make verify-all` | Run full verification suite |

### Git Hooks

| Hook | Purpose |
|------|---------|
| pre-commit | Python linting (Ruff, mypy), secret detection |
| commit-msg | Conventional commits enforcement |

---

## Project Structure

```
/
├── AGENTS.md                  # Project knowledge base
├── CHANGELOG.md               # Version changelog
├── CONTRIBUTING.md            # Contribution guidelines
├── LICENSE                    # License file
├── Makefile                   # Management commands
├── OWNERS                     # Code ownership
├── README.md                  # This file
├── VERSION                    # Version file
├── commitlint.config.js       # Commit lint configuration
├── mypy.ini                   # Type checking configuration
├── pyproject.toml             # Python project configuration
│
├── collector/                 # Main data collector (Python)
│   ├── AGENTS.md              # Collector knowledge base
│   ├── Dockerfile             # Collector container image
│   ├── RATE-LIMITING.md       # Rate limiting documentation
│   ├── README.md              # Collector documentation
│   ├── __init__.py
│   ├── config.py              # Configuration management
│   ├── entrypoint.sh          # Container entrypoint
│   ├── exceptions.py          # Custom exceptions
│   ├── health_server.py       # Health check server
│   ├── requirements.txt       # Python dependencies
│   ├── run_collector.py       # Collector entry point
│   ├── api/                   # API server module
│   │   └── enhanced_collection_api.py
│   ├── core/                  # Core modules
│   │   ├── AGENTS.md
│   │   ├── __init__.py
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
│   │   ├── fortigate/        # FortiGate integration
│   │   │   ├── __init__.py
│   │   │   ├── collector.py
│   │   │   ├── parsers.py
│   │   │   └── ssh_client.py
│   │   ├── database/          # Database layer
│   │   │   ├── __init__.py
│   │   │   ├── queries.py
│   │   │   └── service.py
│   │   ├── regtech/           # REGTECH integration
│   │   │   ├── AGENTS.md
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── collector.py
│   │   │   └── data_processor.py
│   │   └── multi_source/      # Multi-source collection
│   │       ├── AGENTS.md
│   │       ├── __init__.py
│   │       ├── collector.py
│   │       ├── models.py
│   │       └── parsers.py
│   └── scheduler/             # Scheduler module
│       ├── __init__.py
│       ├── dependencies.py
│       ├── manager.py
│       └── operations.py
│
└── postgres/                  # PostgreSQL database
    ├── AGENTS.md
    ├── Dockerfile
    └── initdb/
        ├── 01-extensions.sql
        ├── 02-schema.sql
        └── 03-migrations.sql
    └── migrations/
        ├── 001_add_data_source_column.sql
        ├── 002_add_missing_columns.sql
        ├── 003_add_display_order.sql
        ├── 004_update_active_blacklist_view.sql
        ├── 005_add_composite_indexes.sql
        └── 006_fix_is_active_inconsistency.sql
```

---

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting pull requests.

### Commit Message Format

This project follows the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Code Standards

| Tool | Purpose |
|------|---------|
| ruff | Linting (E, F, W rules) |
| mypy | Static type checking |
| pytest | Testing with markers: unit, integration, security, db, api |

### Pull Request Process

1. Create a feature branch from `master`
2. Run `make verify-quick` to check your changes
3. Submit a PR with a clear description
4. Ensure all CI checks pass
5. Request review from code owners

---

## License

Proprietary - See [LICENSE](LICENSE) file for details.

---

## External Links

| Service | URL |
|---------|-----|
| CLIProxy API | <https://cliproxy.jclee.me/v1> |
| Bot Service | <https://bot.jclee.me> |
| PR Agent | <https://github.com/qodo-ai/pr-agent> |

---

# 한국어 (Korean)

---

[![CI Checks](https://github.com/qws941/BlacklistService/actions/workflows/03_pr-checks.yml/badge.svg)](https://github.com/qws941/BlacklistService/actions/workflows/03_pr-checks.yml)
[![Release](https://github.com/qws941/BlacklistService/actions/workflows/release.yml/badge.svg)](https://github.com/qws941/BlacklistService/actions/workflows/release.yml)
[![CodeQL](https://github.com/qws941/BlacklistService/actions/workflows/06_codeql.yml/badge.svg)](https://github.com/qws941/BlacklistService/actions/workflows/06_codeql.yml)
[![Scorecard](https://github.com/qws941/BlacklistService/actions/workflows/08_scorecard.yml/badge.svg)](https://github.com/qws941/BlacklistService/actions/workflows/08_scorecard.yml)
[![GitHub 보안 모범 사례](https://img.shields.io/badge/GitHub-Security%20Best%20Practices-blue)](https://github.com/qws941/BlacklistService/security)

[![Python 버전](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://www.docker.com/)
[![라이선스](https://img.shields.io/badge/license-Proprietary-red)](LICENSE)

---

## 개요

**Blacklist Service Management**는 금융보안원(REGTECH) 기반 IP 블랙리스트 데이터를 수집, 처리, 분산하는 위협 인텔리전스 플랫폼입니다. FortiGate 방화벽 및 Cloudflare WAF와 연동하여 악성 IP 목록을 자동 수집합니다.

### 주요 구성 요소

| 구성 요소 | 설명 |
|-----------|------|
| `collector/` | 모듈형 아키텍처의 Python 데이터 수집기 |
| `postgres/` | 스키마 및 마이그레이션 관리 PostgreSQL 데이터베이스 |
| `_bot-scripts/` | GitHub 자동화 스크립트 (내부 CI 전용) |

---

## 주요 기능

- **멀티 소스 수집**: REGTECH, FortiGate, 다중 외부 소스로부터 IP 블랙리스트 자동 수집
- **데이터 품질 관리**: 수집된 데이터의 무결성 검증 및 중복 제거
- **자동 아카이브**: 일별/월별 백업 및 증분 아카이브 지원
- **정책 모니터링**: 블랙리스트 정책 변경 사항 실시간 추적
- **Rate Limiting**: API 호출 제한으로 서비스 안정성 확보
- **데이터베이스 관리**: PostgreSQL 기반 스토리지 및 버전 관리 마이그레이션
- **Docker 배포**: 컨테이너화된 애플리케이션 및 데이터베이스
- **종합 테스트**: 유닛, 통합, 보안, 데이터베이스, API 테스트
- **GitHub 자동화**: 코드 품질 및 릴리스 관리를 위한 38개 자동화 워크플로우

---

## 아키텍처

```mermaid
flowchart TB
    subgraph DataSources["데이터 소스"]
        REGTECH["REGTECH API<br/>금융보안원"]
        FORTIGATE["FortiGate Firewall<br/>포트게이트 방화벽"]
        MULTI["Multi-Source Collector<br/>멀티소스 수집기"]
        CLOUDFLARE["Cloudflare WAF<br/>클라우드플레어"]
    end

    subgraph Collector["collector/ 수집기"]
        CORE["core/ 코어 모듈"]
        SCHEDULER["scheduler/ 스케줄러"]
        API["api/ API 서버"]

        CORE --> FORTIGATE
        CORE --> REGTECH
        CORE --> MULTI
    end

    subgraph Database["postgres/ 데이터베이스"]
        PG["PostgreSQL<br/>포스트그레SQL"]
        MIGRATIONS["migrations/ 마이그레이션"]
    end

    subgraph GitHubAutomation["GitHub 자동화"]
        WORKFLOWS[".github/workflows/<br/>38개 워크플로우"]
        BOTS["GitHub Bot Scripts<br/>qodo-ai/pr-agent"]
    end

    subgraph ExternalServices["외부 서비스"]
        ELK["ELK Stack<br/>&lt;homelab-elk&gt;"]
        PROXY["CLIProxyAPI<br/>https://cliproxy.jclee.me/v1"]
    end

    DataSources --> Collector
    Collector --> Database
    Collector --> GitHubAutomation
    GitHubAutomation -->|"워크플로우 트리거"| Collector
    Collector --> ELK
    Collector --> PROXY
```

---

## 자동화 목록

### GitHub 워크플로우 (38개)

| # | 워크플로우 파일 | 용도 |
|---|----------------|------|
| 01 | `01_branch-to-pr.yml` | 브랜치에서 PR로 변환 |
| 02 | `02_issue-to-branch.yml` | 이슈에서 기능 브랜치 생성 |
| 03 | `03_pr-checks.yml` | PR 유효성 검사 |
| 04 | `04_actionlint.yml` | 워크플로우 파일 린팅 |
| 05 | `05_gitleaks.yml` | 시크릿 탐지 |
| 06 | `06_codeql.yml` | 코드 보안 분석 |
| 07 | `07_dependency-review.yml` | 의존성 취약점 검토 |
| 08 | `08_scorecard.yml` | OpenSSF 점수 평가 |
| 09 | `09_semantic-pr.yml` | 시맨틱 PR 검증 |
| 10 | `10_pr-review.yml` | 자동 PR 리뷰 |
| 12 | `12_dependabot-auto-merge.yml` | Dependabot 자동 병합 |
| 13 | `13_pr-auto-merge.yml` | PR 자동 병합 |
| 14 | `14_bot-auto-fix.yml` | 봇 자동 수정 |
| 15 | `15_merged-pr-cleanup.yml` | 병합 후 정리 |
| 18 | `18_issue-management.yml` | 이슈 관리 |
| 19 | `19_issue-backfill.yml` | 이슈 백필 |
| 20 | `20_readme-gen.yml` | README 생성 |
| 21 | `21_docs-sync.yml` | 문서 동기화 |
| 24 | `24_release-notes.yml` | 릴리스 노트 초안 |
| 25 | `25_release-publish.yml` | 릴리스 게시 |
| 29 | `29_downstream-health-check.yml` | 하류 서비스 상태 확인 |
| 37 | `37_ci-failure-issues.yml` | CI 실패 이슈 생성 |
| 42 | `42_reusable-docs-sync.yml` | 재사용 가능 문서 동기화 |
| 43 | `43_reusable-issue-management.yml` | 재사용 가능 이슈 관리 |
| 44 | `44_reusable-pr-checks.yml` | 재사용 가능 PR 검사 |
| 45 | `45_reusable-gitleaks.yml` | 재사용 가능 시크릿 탐지 |
| 60 | `60_ci-auto-heal.yml` | CI 자동 복구 |
| 91 | `91_issue-classification.yml` | 이슈 분류 |
| - | `_ci-node.yml` | Node.js CI 재사용 워크플로우 |
| - | `auto-merge.yml` | 자동 병합 워크플로우 |
| - | `build-images.yml` | Docker 이미지 빌드 |
| - | `ci.yml` | 메인 CI 워크플로우 |
| - | `labeler.yml` | PR 라벨러 |
| - | `release.yml` | 릴리스 워크플로우 |
| - | `security.yml` | 보안 스캐닝 |
| - | `standard-ci.yml` | 표준 CI 워크플로우 |
| - | `welcome.yml` | 환영 메시지 |
| - | `security/11_pr-review.yml` | 보안 PR 리뷰 |

### GitHub 자동화 도구

| 도구 | 용도 |
|------|------|
| [qodo-ai/pr-agent](https://github.com/qodo-ai/pr-agent) | 자동 PR 리뷰 및 코딩 지원 |
| CLIProxyAPI (`https://cliproxy.jclee.me/v1`) | 봇 운영용 CLI 프록시 API |
| bot.jclee.me | 봇 서비스 엔드포인트 |

### 테스트 도구

| 도구 | 설정 |
|------|------|
| pytest | `pyproject.toml` - 마커: unit, integration, security, db, api |
| ruff | `pyproject.toml` - 린팅 (E, F, W 규칙) |
| mypy | `mypy.ini` - 타입 검사 |

---

## 빠른 시작

### 전제 조건

- Python 3.11+
- Docker 및 Docker Compose
- PostgreSQL (Docker를 통해)

### 설치

```bash
# 저장소 복제
git clone https://github.com/qws941/BlacklistService.git
cd BlacklistService

# 의존성 설치
pip install -r collector/requirements.txt

# Git 훅 설정
make setup-hooks
```

### Docker Compose 실행

```bash
# 개발 환경 시작 (핫 리로드 포함)
make dev

# 이미지 재빌드 없이 시작
make dev-no-build

# 서비스 상태 확인
make health
```

### 접근 주소

| 서비스 | URL |
|--------|-----|
| 애플리케이션 | <http://localhost:2542> |
| 상태 확인 | <http://localhost:2542/health> |

---

## 로컬 개발

### 환경 변수

`deploy/` 디렉토리에 `.env` 파일 생성:

```env
# 애플리케이션
PORT=2542
DATABASE_URL=postgresql://user:pass@postgres:5432/blacklist

# 외부 서비스
ELK_HOST=<homelab-elk>
CLI_PROXY_URL=https://cliproxy.jclee.me/v1

# API 키 (REGTECH, FortiGate, Cloudflare)
REGTECH_API_KEY=your_regtech_key
FORTIGATE_HOST=your_fortigate_host
CLOUDFLARE_API_KEY=your_cloudflare_key
```

### 데이터베이스 설정

```bash
# 마이그레이션 실행
make db-migrate

# 마이그레이션 상태 확인
make db-status
```

### 테스트 실행

```bash
# 전체 테스트
make test

# 빠른 테스트 (유닛 테스트만)
make verify-quick

# 전체 검증
make verify-all
```

---

## 명령어 참조

### Makefile 타겟

| 명령어 | 설명 |
|--------|------|
| `make help` | 사용 가능한 모든 명령어 표시 |
| `make setup-hooks` | Git 훅 설치 (pre-commit, commit-msg) |
| `make dev` | 핫 리로드로 개발 환경 시작 |
| `make dev-no-build` | 이미지 재빌드 없이 시작 |
| `make dev-prod` | 프로덕션 유사 환경 시작 |
| `make dev-app` | 앱 서비스만 재시작 |
| `make up` | 모든 서비스 시작 |
| `make down` | 모든 서비스 중지 |
| `make logs` | 컨테이너 로그 보기 |
| `make clean` | 컨테이너 및 볼륨 정리 |
| `make test` | 테스트 스위트 실행 |
| `make health` | 서비스 상태 확인 |
| `make release` | 릴리스 생성 |
| `make release-dry` | 릴리스 드라이런 |
| `make verify` | 모든 검증 실행 |
| `make verify-lint` | ruff 린터 실행 |
| `make verify-types` | mypy 타입 체커 실행 |
| `make verify-secrets` | 시크릿 탐지 실행 |
| `make verify-pre-commit` | pre-commit 훅 실행 |
| `make verify-quick` | 빠른 검증 실행 |
| `make verify-all` | 전체 검증 스위트 실행 |

### Git 훅

| 훅 | 용도 |
|----|------|
| pre-commit | Python 린팅 (Ruff, mypy), 시크릿 탐지 |
| commit-msg | 커밋 컨벤션 enforcing |

---

## 프로젝트 구조

```
/
├── AGENTS.md                  # 프로젝트 지식 베이스
├── CHANGELOG.md               # 버전 변경 로그
├── CONTRIBUTING.md            # 기여 가이드라인
├── LICENSE                    # 라이선스 파일
├── Makefile                   # 관리 명령어
├── OWNERS                     # 코드 소유권
├── README.md                  # 이 파일
├── VERSION                    # 버전 파일
├── commitlint.config.js       # 커밋 린팅 설정
├── mypy.ini                   # 타입 검사 설정
├── pyproject.toml             # Python 프로젝트 설정
│
├── collector/                 # 메인 데이터 수집기 (Python)
│   ├── AGENTS.md              # 수집기 지식 베이스
│   ├── Dockerfile             # 수집기 컨테이너 이미지
│   ├── RATE-LIMITING.md       # Rate limiting 문서
│   ├── README.md              # 수집기 문서
│   ├── __init__.py
│   ├── config.py              # 설정 관리
│   ├── entrypoint.sh          # 컨테이너 진입점
│   ├── exceptions.py          # 커스텀 예외
│   ├── health_server.py       # 상태 확인 서버
│   ├── requirements.txt       # Python 의존성
│   ├── run_collector.py       # 수집기 진입점
│   ├── api/                   # API 서버 모듈
│   │   └── enhanced_collection_api.py
│   ├── core/                  # 코어 모듈
│   │   ├── AGENTS.md
│   │   ├── __init__.py
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
│   │   ├── fortigate/         # FortiGate 연동
│   │   │   ├── __init__.py
│   │   │   ├── collector.py
│   │   │   ├── parsers.py
│   │   │   └── ssh_client.py
│   │   ├── database/           # 데이터베이스 레이어
│   │   │   ├── __init__.py
│   │   │   ├── queries.py
│   │   │   └── service.py
│   │   ├── regtech/            # REGTECH 연동
│   │   │   ├── AGENTS.md
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── collector.py
│   │   │   └── data_processor.py
│   │   └── multi_source/       # 멀티소스 수집
│   │       ├── AGENTS.md
│   │       ├── __init__.py
│   │       ├── collector.py
│   │       ├── models.py
│   │       └── parsers.py
│   └── scheduler/              # 스케줄러 모듈
│       ├── __init__.py
│       ├── dependencies.py
│       ├── manager.py
│       └── operations.py
│
└── postgres/                  # PostgreSQL 데이터베이스
    ├── AGENTS.md
    ├── Dockerfile
    └── initdb/
        ├── 01-extensions.sql
        ├── 02-schema.sql
        └── 03-migrations.sql
    └── migrations/
        ├── 001_add_data_source_column.sql
        ├── 002_add_missing_columns.sql
        ├── 003_add_display_order.sql
        ├── 004_update_active_blacklist_view.sql
        ├── 005_add_composite_indexes.sql
        └── 006_fix_is_active_inconsistency.sql
```

---

## 기여하기

풀 리퀘스트를 제출하기 전에 [CONTRIBUTING.md](CONTRIBUTING.md)를 읽어주세요.

### 커밋 메시지 형식

이 프로젝트는 [Conventional Commits](https://www.conventionalcommits.org/) 사양을 따릅니다:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**유형:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### 코드 표준

| 도구 | 용도 |
|------|------|
| ruff | 린팅 (E, F, W 규칙) |
| mypy | 정적 타입 검사 |
| pytest | 마커가 있는 테스트: unit, integration, security, db, api |

### 풀 리퀘스트 프로세스

1. `master`에서 기능 브랜치를 생성하세요
2. 변경 사항을 확인하려면 `make verify-quick`을 실행하세요
3. 명확한 설명과 함께 PR을 제출하세요
4. 모든 CI 검사가 통과하는지 확인하세요
5. 코드 소유자에게 리뷰를 요청하세요

---

## 라이선스

专属 - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

---

## 외부 링크

| 서비스 | URL |
|--------|-----|
| CLIProxy API | <https://cliproxy.jclee.me/v1> |
| Bot Service | <https://bot.jclee.me> |
| PR Agent | <https://github.com/qodo-ai/pr-agent> |

---

*이 README는 자동으로 생성되었습니다. 수정 시 변경 사항이 덮어써질 수 있습니다.*
