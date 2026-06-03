# Blacklist Service Management

Korean | [English](#english)

---

## Korean (한국어)

### 개요

**Blacklist Service Management**는 금융보안원(REGTECH) 기반 IP 블랙리스트 데이터를 수집, 처리, 분산하는 위협 인텔리전스 플랫폼입니다. FortiGate 방화벽 및 Cloudflare WAF와 연동하여 악성 IP 목록을 자동 수집합니다.

### 주요 기능

- **멀티 소스 수집**: REGTECH, FortiGate, 다중 외부 소스로부터 IP 블랙리스트 자동 수집
- **데이터 품질 관리**: 수집된 데이터의 무결성 검증 및 중복 제거
- **자동 아카이브**: 일별/월별 백업 및 증분 아카이브 지원
- **정책 모니터링**: 블랙리스트 정책 변경 사항 실시간 추적
- **Rate Limiting**: API 호출 제한으로 서비스 안정성 확보
- **데이터베이스 관리**: PostgreSQL 기반 스토리지 및 마이그레이션
- **Docker 배포**: 컨테이너화된 애플리케이션 및 데이터베이스

### 아키텍처

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
        BOTS["_bot-scripts/<br/>GitHub Bot 스크립트"]
    end

    subgraph ExternalServices["외부 서비스"]
        ELK["ELK Stack<br/>&lt;homelab-elk&gt;"]
        PROXY["CLIProxyAPI<br/>https://cliproxy.jclee.me/v1"]
    end

    DataSources --> Collector
    Collector --> Database
    Collector --> GitHubAutomation
    GitHubAutomation -->|"Workflow 트리거"| Collector
    Collector --> ELK
    Collector --> PROXY
```

### 프로젝트 구조

```
/
├── collector/              # 메인 데이터 수집기 (Python)
│   ├── core/               # 코어 모듈
│   │   ├── fortigate/      # FortiGate 수집기
│   │   ├── regtech/        # REGTECH 수집기
│   │   ├── multi_source/  # 멀티소스 수집기
│   │   └── database/       # 데이터베이스 레이어
│   ├── scheduler/          # 작업 스케줄러
│   ├── api/                # API 서버
│   └── scheduler/          # 스케줄링 모듈
├── postgres/               # PostgreSQL 데이터베이스
│   ├── initdb/             # 초기화 스크립트
│   └── migrations/         # 마이그레이션 파일
├── _bot-scripts/           # GitHub Bot 자동화 스크립트
├── .github/
│   └── workflows/          # GitHub Actions 워크플로우 (38개)
└── Makefile                # 개발 명령어
```

### 자동화 인벤토리

#### GitHub Actions 워크플로우 (38개)

| 워크플로우 파일 | 설명 |
|----------------|------|
| `01_branch-to-pr.yml` | 브랜치에서 PR로 변환 |
| `02_issue-to-branch.yml` | 이슈から브랜치 생성 |
| `03_pr-checks.yml` | PR 체크 실행 |
| `04_actionlint.yml` | GitHub Actions YAML 검증 |
| `05_gitleaks.yml` | 시크릿/민감정보 스캔 |
| `06_codeql.yml` | CodeQL 코드 분석 |
| `07_dependency-review.yml` | 의존성 보안 검토 |
| `08_scorecard.yml` | OpenSSF Scorecard 평가 |
| `09_semantic-pr.yml` | 시맨틱 PR 검증 |
| `10_pr-review.yml` | PR 코드 리뷰 (qodo-ai/pr-agent) |
| `12_dependabot-auto-merge.yml` | Dependabot 자동 머지 |
| `13_pr-auto-merge.yml` | PR 자동 머지 |
| `14_bot-auto-fix.yml` | Bot 자동 수정 |
| `15_merged-pr-cleanup.yml` | 머지 후 정리 |
| `18_issue-management.yml` | 이슈 관리 |
| `19_issue-backfill.yml` | 이슈 백필 |
| `20_readme-gen.yml` | README 생성 |
| `21_docs-sync.yml` | 문서 동기화 |
| `24_release-notes.yml` |.Release 노트 생성 |
| `25_release-publish.yml` | Release 게시 |
| `29_downstream-health-check.yml` | 다운스트림 헬스 체크 |
| `37_ci-failure-issues.yml` | CI 실패 시 이슈 생성 |
| `42_reusable-docs-sync.yml` | 재사용 가능 문서 동기화 |
| `43_reusable-issue-management.yml` | 재사용 가능 이슈 관리 |
| `44_reusable-pr-checks.yml` | 재사용 가능 PR 체크 |
| `45_reusable-gitleaks.yml` | 재사용 가능 Gitleaks |
| `60_ci-auto-heal.yml` | CI 자동 복구 |
| `91_issue-classification.yml` | 이슈 분류 |
| `_ci-node.yml` | Node.js CI 템플릿 |
| `auto-merge.yml` | 자동 머지 |
| `build-images.yml` | Docker 이미지 빌드 |
| `ci.yml` | CI 워크플로우 |
| `labeler.yml` | PR 라벨러 |
| `release.yml` | Release 워크플로우 |
| `security.yml` | 보안 스캔 |
| `standard-ci.yml` | 표준 CI |
| `welcome.yml` | 신규 기여자 환영 |
| `security/11_pr-review.yml` | 보안 PR 리뷰 |

#### 재사용 가능 워크플로우 (Reusable Workflows)

| 재사용 워크플로우 | 설명 |
|------------------|------|
| `_ci-python.yml` | Python CI 파이프라인 |
| `_ci-node.yml` | Node.js CI 파이프라인 |
| `_commitlint.yml` | 커밋 메시지 린팅 |
| `_gitleaks.yml` | 시크릿 스캔 |
| `_codex-pr-review.yml` | AI PR 리뷰 (qodo-ai/pr-agent) |
| `_codex-auto-issue.yml` | 자동 이슈 생성 |
| `_codex-issue-timeout.yml` | 이슈 타임아웃 관리 |
| `_codex-triage.yml` | 트라이지 자동화 |
| `_dependabot-auto-fix.yml` | Dependabot 자동 수정 |
| `_release-drafter.yml` | Release 드래프팅 |
| `_stale.yml` | 오래된 이슈/PR 정리 |
| `_labeler.yml` | 라벨 자동 적용 |
| `_issue-label.yml` | 이슈 자동 라벨링 |
| `_issue-lifecycle.yml` | 이슈 수명주기 관리 |
| `_lock-threads.yml` | 스레드 잠금 |
| `_pr-size.yml` | PR 크기 라벨링 |
| `_auto-approve-runs.yml` | 실행 자동 승인 |
| `_auto-merge.yml` | 자동 머지 |
| `_branch-cleanup.yml` | 브랜치 정리 |
| `_ci-notify-failure.yml` | CI 실패 알림 |
| `_elk-ingest.yml` | ELK 로그 수집 |
| `_deploy-cf-worker.yml` | Cloudflare Worker 배포 |
| `_welcome.yml` | 신규 기여자 환영 |

### 외부 서비스 연동

| 서비스 | 엔드포인트 | 용도 |
|--------|-----------|------|
| ELK Stack | `<homelab-elk>` | 로그 수집 및 모니터링 |
| CLIProxy API | `https://cliproxy.jclee.me/v1` | AI 모델 프록시 (qodo-ai/pr-agent) |
| REGTECH API | 금융보안원 | IP 블랙리스트 원본 |
| FortiGate | `<homelab-host>` | 방화벽 로그 수집 |
| Cloudflare WAF | Cloudflare | WAF 로그 통합 |

### 빠른 시작

#### prerequisites

- Docker 및 Docker Compose
- Python 3.11+
- PostgreSQL (별도 또는 Docker)

#### 개발 환경 시작

```bash
# 저장소 클론
git clone <repository-url>
cd <repository-name>

# Git hooks 설치
make setup-hooks

# 개발 환경 시작 (핫 리로드)
make dev

# 또는 빌드 없이 시작
make dev-no-build
```

#### Docker Compose로 시작

```bash
# 프로덕션 환경
make deploy

# 헬스 체크
make health
```

### 로컬 개발

#### Makefile 명령어 레퍼런스

| 명령어 | 설명 |
|--------|------|
| `make help` | 사용 가능한 명령어 목록 |
| `make setup-hooks` | Git hooks 및 Husky 설치 |
| `make dev` | 개발 환경 시작 (핫 리로드) |
| `make dev-no-build` | 기존 이미지로 시작 |
| `make dev-prod` | 프로덕션类似 환경 시작 |
| `make dev-app` | 앱 서비스만 재시작 |
| `make build` | Docker 이미지 빌드 |
| `make up` | 컨테이너 시작 |
| `make down` | 컨테이너 중지 |
| `make logs` | 로그 확인 |
| `make restart` | 컨테이너 재시작 |
| `make health` | 헬스 체크 실행 |
| `make test` | 테스트 실행 |
| `make verify` | 전체 검증 (lint, types, secrets) |
| `make verify-lint` | Ruff 린트 검사 |
| `make verify-types` | mypy 타입 검사 |
| `make verify-secrets` | 시크릿 스캔 |
| `make verify-pre-commit` | pre-commit 검사 |
| `make verify-quick` | 빠른 검증 |
| `make verify-all` | 전체 검증 실행 |
| `make release` | Release 실행 |
| `make release-dry` | Release 드라이 런 |

#### 환경 변수

```bash
# deploy/.env 파일 생성
PORT=2542
DATABASE_URL=postgresql://user:pass@localhost:5432/blacklist
REGTECH_API_KEY=<your-api-key>
FORTIGATE_HOST=<homelab-host>
```

#### 테스트 실행

```bash
# 전체 테스트
make test

# 특정 마커로 테스트
pytest -m unit
pytest -m integration
pytest -m security
pytest -m db
pytest -m api
```

### 기여 가이드

기여之前 请阅读 [CONTRIBUTING.md](./CONTRIBUTING.md) 및 [AGENTS.md](./AGENTS.md)를 확인하세요.

1. **브랜치 생성**: `02_issue-to-branch.yml` 워크플로우를 사용하거나 수동으로 생성
2. **변경 사항 적용**: Conventional Commits 규칙 준수 (`fix:`, `feat:`, `docs:` 등)
3. **PR 생성**: `10_pr-review.yml` 워크플로우가 자동 리뷰를 수행
4. **머지**: 시맨틱 PR (`09_semantic-pr.yml`) 검증 통과 후 자동 또는 수동 머지

#### 커밋 메시지 규칙

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`, `build`, `revert`

---

## English

### Overview

**Blacklist Service Management** is a threat intelligence platform that collects, processes, and distributes IP blacklist data from Korea Financial Security Institute (REGTECH). It integrates with FortiGate firewalls and Cloudflare WAF for automated malicious IP collection.

### Key Features

- **Multi-Source Collection**: Automated IP blacklist collection from REGTECH, FortiGate, and multiple external sources
- **Data Quality Management**: Data integrity validation and deduplication
- **Automatic Archiving**: Daily/monthly backups and incremental archive support
- **Policy Monitoring**: Real-time tracking of blacklist policy changes
- **Rate Limiting**: API call limiting for service stability
- **Database Management**: PostgreSQL-based storage and migrations
- **Docker Deployment**: Containerized application and database

### Architecture

```mermaid
flowchart TB
    subgraph DataSources["Data Sources"]
        REGTECH["REGTECH API<br/>Korea Financial<br/>Security Institute"]
        FORTIGATE["FortiGate Firewall"]
        MULTI["Multi-Source Collector"]
        CLOUDFLARE["Cloudflare WAF"]
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
        PG["PostgreSQL"]
        MIGRATIONS["migrations/ Migrations"]
    end

    subgraph GitHubAutomation["GitHub Automation"]
        WORKFLOWS[".github/workflows/<br/>38 Workflows"]
        BOTS["_bot-scripts/<br/>GitHub Bot Scripts"]
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

### Project Structure

```
/
├── collector/              # Main data collector (Python)
│   ├── core/               # Core modules
│   │   ├── fortigate/      # FortiGate collector
│   │   ├── regtech/        # REGTECH collector
│   │   ├── multi_source/  # Multi-source collector
│   │   └── database/       # Database layer
│   ├── scheduler/          # Job scheduler
│   ├── api/                # API server
│   └── scheduler/          # Scheduling module
├── postgres/               # PostgreSQL database
│   ├── initdb/             # Initialization scripts
│   └── migrations/         # Migration files
├── _bot-scripts/           # GitHub Bot automation scripts
├── .github/
│   └── workflows/          # GitHub Actions workflows (38)
└── Makefile                # Development commands
```

### Automation Inventory

#### GitHub Actions Workflows (38 total)

| Workflow File | Description |
|---------------|-------------|
| `01_branch-to-pr.yml` | Branch to PR conversion |
| `02_issue-to-branch.yml` | Issue to branch creation |
| `03_pr-checks.yml` | PR checks execution |
| `04_actionlint.yml` | GitHub Actions YAML validation |
| `05_gitleaks.yml` | Secret/sensitive data scan |
| `06_codeql.yml` | CodeQL code analysis |
| `07_dependency-review.yml` | Dependency security review |
| `08_scorecard.yml` | OpenSSF Scorecard assessment |
| `09_semantic-pr.yml` | Semantic PR validation |
| `10_pr-review.yml` | PR code review (qodo-ai/pr-agent) |
| `12_dependabot-auto-merge.yml` | Dependabot auto-merge |
| `13_pr-auto-merge.yml` | PR auto-merge |
| `14_bot-auto-fix.yml` | Bot auto-fix |
| `15_merged-pr-cleanup.yml` | Post-merge cleanup |
| `18_issue-management.yml` | Issue management |
| `19_issue-backfill.yml` | Issue backfill |
| `20_readme-gen.yml` | README generation |
| `21_docs-sync.yml` | Documentation sync |
| `24_release-notes.yml` | Release notes generation |
| `25_release-publish.yml` | Release publishing |
| `29_downstream-health-check.yml` | Downstream health check |
| `37_ci-failure-issues.yml` | CI failure issue creation |
| `42_reusable-docs-sync.yml` | Reusable docs sync |
| `43_reusable-issue-management.yml` | Reusable issue management |
| `44_reusable-pr-checks.yml` | Reusable PR checks |
| `45_reusable-gitleaks.yml` | Reusable Gitleaks |
| `60_ci-auto-heal.yml` | CI auto-heal |
| `91_issue-classification.yml` | Issue classification |
| `_ci-node.yml` | Node.js CI template |
| `auto-merge.yml` | Auto-merge |
| `build-images.yml` | Docker image build |
| `ci.yml` | CI workflow |
| `labeler.yml` | PR labeler |
| `release.yml` | Release workflow |
| `security.yml` | Security scan |
| `standard-ci.yml` | Standard CI |
| `welcome.yml` | New contributor welcome |
| `security/11_pr-review.yml` | Security PR review |

#### Reusable Workflows

| Reusable Workflow | Description |
|-------------------|-------------|
| `_ci-python.yml` | Python CI pipeline |
| `_ci-node.yml` | Node.js CI pipeline |
| `_commitlint.yml` | Commit message linting |
| `_gitleaks.yml` | Secret scanning |
| `_codex-pr-review.yml` | AI PR review (qodo-ai/pr-agent) |
| `_codex-auto-issue.yml` | Auto issue creation |
| `_codex-issue-timeout.yml` | Issue timeout management |
| `_codex-triage.yml` | Triage automation |
| `_dependabot-auto-fix.yml` | Dependabot auto-fix |
| `_release-drafter.yml` | Release drafting |
| `_stale.yml` | Stale issue/PR cleanup |
| `_labeler.yml` | Auto label application |
| `_issue-label.yml` | Issue auto-labeling |
| `_issue-lifecycle.yml` | Issue lifecycle management |
| `_lock-threads.yml` | Thread locking |
| `_pr-size.yml` | PR size labeling |
| `_auto-approve-runs.yml` | Run auto-approve |
| `_auto-merge.yml` | Auto-merge |
| `_branch-cleanup.yml` | Branch cleanup |
| `_ci-notify-failure.yml` | CI failure notification |
| `_elk-ingest.yml` | ELK log ingestion |
| `_deploy-cf-worker.yml` | Cloudflare Worker deployment |
| `_welcome.yml` | New contributor welcome |

### External Service Integration

| Service | Endpoint | Purpose |
|---------|----------|---------|
| ELK Stack | `<homelab-elk>` | Log collection and monitoring |
| CLIProxy API | `https://cliproxy.jclee.me/v1` | AI model proxy (qodo-ai/pr-agent) |
| REGTECH API | Korea Financial Security Institute | IP blacklist source |
| FortiGate | `<homelab-host>` | Firewall log collection |
| Cloudflare WAF | Cloudflare | WAF log integration |

### Quick Start

#### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- PostgreSQL (standalone or Docker)

#### Development Environment

```bash
# Clone repository
git clone <repository-url>
cd <repository-name>

# Install git hooks
make setup-hooks

# Start development environment (hot reload)
make dev

# Or start without rebuild
make dev-no-build
```

#### Docker Compose

```bash
# Production environment
make deploy

# Health check
make health
```

### Local Development

#### Makefile Command Reference

| Command | Description |
|---------|-------------|
| `make help` | Show available commands |
| `make setup-hooks` | Install Git hooks and Husky |
| `make dev` | Start development (hot reload) |
| `make dev-no-build` | Start with existing images |
| `make dev-prod` | Start production-like environment |
| `make dev-app` | Restart only app service |
| `make build` | Build Docker images |
| `make up` | Start containers |
| `make down` | Stop containers |
| `make logs` | View logs |
| `make restart` | Restart containers |
| `make health` | Run health check |
| `make test` | Run tests |
| `make verify` | Full verification |
| `make verify-lint` | Ruff lint check |
| `make verify-types` | mypy type check |
| `make verify-secrets` | Secret scan |
| `make verify-pre-commit` | Pre-commit check |
| `make verify-quick` | Quick verification |
| `make verify-all` | Run all verifications |
| `make release` | Execute release |
| `make release-dry` | Release dry run |

#### Environment Variables

```bash
# Create deploy/.env file
PORT=2542
DATABASE_URL=postgresql://user:pass@localhost:5432/blacklist
REGTECH_API_KEY=<your-api-key>
FORTIGATE_HOST=<homelab-host>
```

#### Running Tests

```bash
# All tests
make test

# By marker
pytest -m unit
pytest -m integration
pytest -m security
pytest -m db
pytest -m api
```

### Contribution Guide

Before contributing, please review [CONTRIBUTING.md](./CONTRIBUTING.md) and [AGENTS.md](./AGENTS.md).

1. **Create Branch**: Use `02_issue-to-branch.yml` workflow or create manually
2. **Make Changes**: Follow Conventional Commits (`fix:`, `feat:`, `docs:`, etc.)
3. **Create PR**: `10_pr-review.yml` workflow performs automatic review
4. **Merge**: Pass semantic PR validation (`09_semantic-pr.yml`) before merging

#### Commit Message Rules

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`, `build`, `revert`

---

## Badges

[![CI](https://github.com/<owner>/<repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/<owner>/<repo>/actions/workflows/ci.yml)
[![Security](https://github.com/<owner>/<repo>/actions/workflows/security.yml/badge.svg)](https://github.com/<owner>/<repo>/actions/workflows/security.yml)
[![Release](https://github.com/<owner>/<repo>/actions/workflows/release.yml/badge.svg)](https://github.com/<owner>/<repo>/actions/workflows/release.yml)
[![OpenSSF Scorecard](https://github.com/<owner>/<repo>/actions/workflows/08_scorecard.yml/badge.svg)](https://github.com/<owner>/<repo>/actions/workflows/08_scorecard.yml)

---

## License

See [LICENSE](./LICENSE) file for details.
