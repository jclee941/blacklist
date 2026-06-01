# Blacklist Service Management

Korean | [English](#english)

---

## Korean

### 개요

**Blacklist Service Management**는 금융보안원(REGTECH) 기반 IP 블랙리스트 데이터를 수집, 처리, 분산하는威胁インテリジェンス 플랫폼입니다. FortiGate 방화벽 및 Cloudflare WAF와 연동하여 악성 IP 목록을 자동 수집합니다.

### 주요 기능

- **멀티 소스 수집**: REGTECH, FortiGate, 다중 외부 소스からの IP 블랙리스트 자동 수집
- **데이터 품질 관리**: 수집된 데이터의 무결성 검증 및 중복 제거
- **자동 아카이브**: 일별/월별 백업 및 증분 아카이브 지원
- **정책 모니터링**: 블랙리스트 정책 변경 사항 실시간 추적
- **Rate Limiting**: API 호출 제한으로 서비스 안정성 확보
- **데이터베이스 관리**: PostgreSQL 기반 스토리지 및 마이그레이션
- **Docker 배포**: 컨테이너화된 애플리케이션 및 데이터베이스

### 프로젝트 구조

```
/
├── collector/              # 메인 데이터 수집기 (Python)
│   ├── core/              # 코어 모듈
│   │   ├── fortigate/     # FortiGate 수집기
│   │   ├── regtech/       # REGTECH 수집기
│   │   ├── multi_source/  # 멀티소스 수집기
│   │   └── database/      # 데이터베이스 레이어
│   ├── scheduler/         # 작업 스케줄러
│   └── api/               # API 서버
├── postgres/              # PostgreSQL 스키마 및 마이그레이션
│   ├── initdb/           # 초기화 스크립트
│   └── migrations/       # 스키마 마이그레이션
├── _bot-scripts/         # GitHub Bot 자동화 스크립트
└── Makefile              # 개발/배포 명령어
```

### 자동화 인벤토리

#### GitHub Actions 워크플로우 (37개)

| 카테고리 | 워크플로우 파일 | 설명 |
|---------|---------------|------|
| **PR 자동화** | `01_branch-to-pr.yml`, `02_issue-to-branch.yml`, `13_pr-auto-merge.yml`, `14_bot-auto-fix.yml`, `15_merged-pr-cleanup.yml` | PR 생성, 자동 병합, 정리 |
| **코드 보안** | `05_gitleaks.yml`, `06_codeql.yml`, `07_dependency-review.yml`, `08_scorecard.yml` | 시크릿 스캔, 코드 분석, 의존성 검토 |
| **CI/CD** | `03_pr-checks.yml`, `04_actionlint.yml`, `44_reusable-pr-checks.yml`, `ci.yml`, `standard-ci.yml`, `release.yml` | PR 검사, 린트, 빌드, 릴리스 |
| **자동修復** | `12_dependabot-auto-merge.yml`, `60_ci-auto-heal.yml` | Dependabot 자동 병합, CI 복구 |
| **릴리스 관리** | `24_release-notes.yml`, `25_release-publish.yml`, `release.yml` |.Release 노트 생성 및 게시 |
| **문서 동기화** | `20_readme-gen.yml`, `21_docs-sync.yml`, `42_reusable-docs-sync.yml` | README 자동 생성, 문서 동기화 |
| **이슈 관리** | `18_issue-management.yml`, `19_issue-backfill.yml`, `37_ci-failure-issues.yml`, `43_reusable-issue-management.yml` | 이슈 자동 생성, 백필, CI 실패 추적 |
| **PR 리뷰** | `10_pr-review.yml`, `security/11_pr-review.yml` | 자동 PR 리뷰 (qodo-ai/pr-agent 활용) |
| **이미지 빌드** | `build-images.yml` | Docker 이미지 빌드 |
| **헬스 체크** | `29_downstream-health-check.yml` | 다운스트림 서비스 헬스 체크 |
| **기타** | `09_semantic-pr.yml`, `auto-merge.yml`, `labeler.yml`, `welcome.yml`, `security.yml` | 시맨틱 PR, 라벨링, 웰컴 메시지 |

#### 사용 도구

- **Python**: `ruff` (린팅), `mypy` (타입 체크), `pytest` (테스트)
- **Secret Detection**: `gitleaks`
- **Code Analysis**: `CodeQL`, `actionlint`
- **Dependency Management**: `Dependabot`
- **PR Review**: `qodo-ai/pr-agent`
- **README Generation**: `minimax-m2.7` (기본), `gpt-5.5` (폴백 via CLIProxyAPI)

### 빠른 시작

#### 사전 요구사항

- Docker 및 Docker Compose
- Python 3.11+
- PostgreSQL 클라이언트 (선택)

#### 1. 환경 설정

```bash
# 레포지토리 클론
git clone https://github.com/jclee941/.github
cd blacklist

# Docker Compose 환경 파일 준비
cp deploy/.env.example deploy/.env  # 필요시 수정
```

#### 2. Docker로 실행

```bash
# 개발 환경 (핫 리로드)
make dev

# 프로덕션 환경
make dev-prod

# 헬스 체크
make health
```

#### 3. 서비스 접근

- **애플리케이션**: <http://localhost:2542>
- **PostgreSQL**: localhost:5432

### 로컬 개발

#### Git Hooks 설정

```bash
make setup-hooks
```

설치되는 훅:

- **pre-commit**: Python 린팅 (Ruff), 타입 체크 (mypy), 시크릿 탐지
- **commit-msg**: Conventional Commits 강제 적용
- **Husky**: Frontend 린팅 (ESLint, Prettier)

#### 테스트 실행

```bash
# 전체 테스트
make test

# 특정 마커 테스트
pytest -m unit
pytest -m integration
pytest -m security
pytest -m db
pytest -m api
```

#### 검증 명령어

```bash
make verify          # 전체 검증 (lint + types + secrets + pre-commit)
make verify-lint     # Ruff 린팅만
make verify-types    # mypy 타입 체크만
make verify-secrets  # Gitleaks 시크릿 탐지만
make verify-quick    # 빠른 검증 (린트 + 타입)
```

### 명령어 참조

| 명령어 | 설명 |
|-------|------|
| `make help` | 사용 가능한 명령어 목록 표시 |
| `make setup-hooks` | Git hooks 설치 |
| `make dev` | 개발 환경 시작 (핫 리로드) |
| `make dev-no-build` | 빌드 없이 개발 환경 시작 |
| `make dev-prod` | 프로덕션 유사 환경 시작 |
| `make dev-app` | 앱 서비스만 재시작 |
| `make down` | 서비스 중지 |
| `make logs` | 로그 확인 |
| `make clean` | Docker 리소스 정리 |
| `make test` | 테스트 실행 |
| `make verify` | 전체 코드 검증 |
| `make release` | 릴리스 실행 |
| `make health` | 헬스 체크 |

### 기여 가이드

기여를 환영합니다! 자세한 내용은 [CONTRIBUTING.md](./CONTRIBUTING.md)를 참고하세요.

#### 커밋 메시지 규칙

이 프로젝트는 **Conventional Commits** 규칙을 따릅니다:

```
<type>(<scope>): <description>

Types:
- feat: 새 기능
- fix: 버그 수정
- docs: 문서 변경
- style: 코드 스타일 변경 (기능 없음)
- refactor: 리팩토링
- perf: 성능 개선
- test: 테스트 변경
- chore: 빌드/도구 변경
```

#### Pull Request 프로세스

1. **브랜치 생성**: `git checkout -b feature/my-feature`
2. **변경사항 작성**: conventional commit 규칙 따르기
3. **검증 실행**: `make verify-quick`
4. **PR 제출**: 자동으로 label 및 reviewer 배정
5. **병합**: 자동 병합 또는 maintainer 승인 후 병합

#### 테스트 마커

| 마커 | 설명 |
|-----|------|
| `unit` | 단위 테스트 (외부 의존성 없음) |
| `integration` | 통합 테스트 (서비스 필요) |
| `security` | 보안 관련 테스트 |
| `db` | 데이터베이스 테스트 |
| `api` | API 엔드포인트 테스트 |

### 라이선스

이 프로젝트는 특정 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](./LICENSE) 파일을 참고하세요.

### 외부 링크

- **PR Review Bot**: <https://bot.jclee.me>
- **CLI Proxy API**: <https://cliproxy.jclee.me>

---

## English

### Overview

**Blacklist Service Management** is a threat intelligence platform that collects, processes, and distributes IP blacklist data from REGTECH (Korea Financial Security Institute). It integrates with FortiGate firewalls and Cloudflare WAF to automatically collect malicious IP lists.

### Key Features

- **Multi-Source Collection**: Automatic IP blacklist collection from REGTECH, FortiGate, and multiple external sources
- **Data Quality Management**: Integrity validation and deduplication of collected data
- **Automatic Archiving**: Daily/monthly backups and incremental archive support
- **Policy Monitoring**: Real-time tracking of blacklist policy changes
- **Rate Limiting**: API call limiting for service stability
- **Database Management**: PostgreSQL-based storage and migrations
- **Docker Deployment**: Containerized application and database

### Project Structure

```
/
├── collector/              # Main data collector (Python)
│   ├── core/              # Core modules
│   │   ├── fortigate/     # FortiGate collector
│   │   ├── regtech/       # REGTECH collector
│   │   ├── multi_source/  # Multi-source collector
│   │   └── database/      # Database layer
│   ├── scheduler/         # Job scheduler
│   └── api/               # API server
├── postgres/              # PostgreSQL schema and migrations
│   ├── initdb/           # Initialization scripts
│   └── migrations/       # Schema migrations
├── _bot-scripts/         # GitHub Bot automation scripts
└── Makefile              # Development/deployment commands
```

### Automation Inventory

#### GitHub Actions Workflows (37 total)

| Category | Workflow Files | Description |
|---------|---------------|-------------|
| **PR Automation** | `01_branch-to-pr.yml`, `02_issue-to-branch.yml`, `13_pr-auto-merge.yml`, `14_bot-auto-fix.yml`, `15_merged-pr-cleanup.yml` | PR creation, auto-merge, cleanup |
| **Code Security** | `05_gitleaks.yml`, `06_codeql.yml`, `07_dependency-review.yml`, `08_scorecard.yml` | Secret scanning, code analysis, dependency review |
| **CI/CD** | `03_pr-checks.yml`, `04_actionlint.yml`, `44_reusable-pr-checks.yml`, `ci.yml`, `standard-ci.yml`, `release.yml` | PR checks, lint, build, release |
| **Auto-Fix** | `12_dependabot-auto-merge.yml`, `60_ci-auto-heal.yml` | Dependabot auto-merge, CI healing |
| **Release Management** | `24_release-notes.yml`, `25_release-publish.yml`, `release.yml` | Release notes generation and publishing |
| **Docs Sync** | `20_readme-gen.yml`, `21_docs-sync.yml`, `42_reusable-docs-sync.yml` | README auto-generation, doc sync |
| **Issue Management** | `18_issue-management.yml`, `19_issue-backfill.yml`, `37_ci-failure-issues.yml`, `43_reusable-issue-management.yml` | Auto-issue creation, backfill, CI failure tracking |
| **PR Review** | `10_pr-review.yml`, `security/11_pr-review.yml` | Automated PR review (using qodo-ai/pr-agent) |
| **Image Build** | `build-images.yml` | Docker image build |
| **Health Check** | `29_downstream-health-check.yml` | Downstream service health check |
| **Misc** | `09_semantic-pr.yml`, `auto-merge.yml`, `labeler.yml`, `welcome.yml`, `security.yml` | Semantic PR, labeling, welcome message |

#### Tools Used

- **Python**: `ruff` (linting), `mypy` (type checking), `pytest` (testing)
- **Secret Detection**: `gitleaks`
- **Code Analysis**: `CodeQL`, `actionlint`
- **Dependency Management**: `Dependabot`
- **PR Review**: `qodo-ai/pr-agent`
- **README Generation**: `minimax-m2.7` (primary), `gpt-5.5` (fallback via CLIProxyAPI)

### Quick Start

#### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- PostgreSQL client (optional)

#### 1. Environment Setup

```bash
# Clone repository
git clone https://github.com/jclee941/.github
cd blacklist

# Prepare Docker Compose environment file
cp deploy/.env.example deploy/.env  # Modify as needed
```

#### 2. Run with Docker

```bash
# Development environment (hot reload)
make dev

# Production-like environment
make dev-prod

# Health check
make health
```

#### 3. Access Services

- **Application**: <http://localhost:2542>
- **PostgreSQL**: localhost:5432

### Local Development

#### Git Hooks Setup

```bash
make setup-hooks
```

Installed hooks:

- **pre-commit**: Python linting (Ruff), type checking (mypy), secret detection
- **commit-msg**: Conventional Commits enforcement
- **Husky**: Frontend linting (ESLint, Prettier)

#### Running Tests

```bash
# All tests
make test

# Specific marker tests
pytest -m unit
pytest -m integration
pytest -m security
pytest -m db
pytest -m api
```

#### Verification Commands

```bash
make verify          # Full verification (lint + types + secrets + pre-commit)
make verify-lint     # Ruff linting only
make verify-types    # mypy type check only
make verify-secrets  # Gitleaks secret scan only
make verify-quick    # Quick verification (lint + types)
```

### Commands Reference

| Command | Description |
|---------|-------------|
| `make help` | Show available commands |
| `make setup-hooks` | Install Git hooks |
| `make dev` | Start development environment (hot reload) |
| `make dev-no-build` | Start without rebuild |
| `make dev-prod` | Start production-like environment |
| `make dev-app` | Restart app service only |
| `make down` | Stop services |
| `make logs` | View logs |
| `make clean` | Clean Docker resources |
| `make test` | Run tests |
| `make verify` | Full code verification |
| `make release` | Run release |
| `make health` | Health check |

### Contribution Guide

Contributions are welcome! See [CONTRIBUTING.md](./CONTRIBUTING.md) for details.

#### Commit Message Rules

This project follows **Conventional Commits**:

```
<type>(<scope>): <description>

Types:
- feat: New feature
- fix: Bug fix
- docs: Documentation changes
- style: Code style changes (no functional change)
- refactor: Refactoring
- perf: Performance improvement
- test: Test changes
- chore: Build/tool changes
```

#### Pull Request Process

1. **Create Branch**: `git checkout -b feature/my-feature`
2. **Make Changes**: Follow conventional commit rules
3. **Run Verification**: `make verify-quick`
4. **Submit PR**: Labels and reviewers auto-assigned
5. **Merge**: Auto-merge or maintainer approval

#### Test Markers

| Marker | Description |
|--------|-------------|
| `unit` | Unit tests (no external dependencies) |
| `integration` | Integration tests (require services) |
| `security` | Security-related tests |
| `db` | Database tests |
| `api` | API endpoint tests |

### License

This project is distributed under a specific license. See [LICENSE](./LICENSE) file for details.

### External Links

- **PR Review Bot**: <https://bot.jclee.me>
- **CLI Proxy API**: <https://cliproxy.jclee.me>
