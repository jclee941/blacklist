<think>
The user wants me to generate a comprehensive README.md for the repository based on the provided project structure, workflow files, and existing documentation snippets. Let me analyze the information:

1. **Project Name**: Blacklist Intelligence Platform (from README.md)
2. **Repository**: jclee941/blacklist
3. **Purpose**: IP blacklist platform for collecting and distributing threat intelligence data from REGTECH (한국금융보안원)
4. **Key integrations**: FortiGate, Cloudflare WAF

**Workflow files (37 total):**
- 01_branch-to-pr.yml
- 02_issue-to-branch.yml
- 03_pr-checks.yml
- 04_actionlint.yml
- 05_gitleaks.yml
- 06_codeql.yml
- 07_dependency-review.yml
- 08_scorecard.yml
- 09_semantic-pr.yml
- 10_pr-review.yml
- 12_dependabot-auto-merge.yml
- 13_pr-auto-merge.yml
- 14_bot-auto-fix.yml
- 15_merged-pr-cleanup.yml
- 18_issue-management.yml
- 19_issue-backfill.yml
- 20_readme-gen.yml
- 21_docs-sync.yml
- 24_release-notes.yml
- 25_release-publish.yml
- 29_downstream-health-check.yml
- 37_ci-failure-issues.yml
- 42_reusable-docs-sync.yml
- 43_reusable-issue-management.yml
- 44_reusable-pr-checks.yml
- 45_reusable-gitleaks.yml
- 60_ci-auto-heal.yml
- _ci-node.yml
- auto-merge.yml
- build-images.yml
- ci.yml
- labeler.yml


- release.yml
- security.yml
- standard-ci.yml
- welcome.yml
- security/11_pr-review.yml

No Go automation tools found in the codebase.

**Modules:**
- `collector/` - Python ETL for data collection
- `collector/core/` - Core modules (archive_manager, data_quality_manager, fortigate_collector, multi_source_collector, policy_monitor, rate_limiter, regtech_collector, validators)
- `collector/core/fortigate/` - FortiGate specific
- `collector/core/database/` - Database layer
- `collector/core/regtech/` - Regtech specific
- `collector/core/multi_source/` - Multi-source collection
- `postgres/` - PostgreSQL schema and migrations

The automation suite includes Python tooling for collection and management, with no Go-based automation present. The project structure separates data collection pipelines from database persistence and multi-source aggregation capabilities. .yaml"
- "app/core/routes/api/blacklist/__init__.py"
- "app/core/routes/api/collection/__init__.py"
- "app/core/routes/api/fortinet/__init__.py"
- "app/core/schemas/__init__.py"
- "app/core/utils/__init__.py"
- "app/core/services/*.py"

Now I need to structure a bilingual README covering the title, badges, overview, features, architecture, automation details, quick start, local development, commands reference, and contribution guidelines. I'll make sure to be thorough about documenting the existing automation workflows and tools while using the specified model (minimax-m2.7 with fallback).

</think>

```markdown
# Blacklist Intelligence Platform

[![CI](https://github.com/jclee941/blacklist/actions/workflows/ci.yml/badge.svg)](https://github.com/jclee941/blacklist/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/jclee941/blacklist)](https://github.com/jclee941/blacklist/releases/latest)
[![Tests](https://img.shields.io/badge/Tests-2175%20passing-brightgreen)](#테스트)
[![Docker](https://img.shields.io/badge/Docker-5%20Services-blue)](#아키텍처)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> **English**: REGTECH (Korea Financial Security Institute) threat intelligence IP blacklist platform — collect, manage, and distribute threat data via FortiGate and Cloudflare WAF integrations.
>
> **한국어**: REGTECH (한국금융보안원) 위협 인텔리전스 데이터를 수집, 관리, 배포하는 IP 블랙리스트 플랫폼입니다. FortiGate 외부 커넥터 및 Cloudflare WAF와 연동하여 네트워크/엣지 레벨 차단을 자동화합니다.

---

## 목차 / Table of Contents

- [개요 / Overview](#개요--overview)
- [주요 기능 / Features](#주요-기능--features)
- [아키텍처 / Architecture](#아키텍처--architecture)
- [자동화 인벤토리 / Automation Inventory](#자동화-인벤토리--automation-inventory)
- [빠른 시작 / Quick Start](#빠른-시작--quick-start)
- [로컬 개발 / Local Development](#로컬-개발--local-development)
- [명령어 참조 / Commands Reference](#명령어-참조--commands-reference)
- [기여 가이드 / Contribution](#기여-가이드--contribution)

---

## 개요 / Overview

The **Blacklist Intelligence Platform**는 collects and distributes threat intelligence IPs from REGTECH (한국금융보안원) via automated scheduling. It provides FortiGate Threat Feed integration (pull) and Cloudflare WAF integration (push) for network/edge-level blocking.

**주요 변경 사항 / Breaking Changes**:

> **v3.6.9**: FortiManager 통합이 완전히 제거되었습니다. FortiGate Threat Feed (pull) 또는 Cloudflare WAF (push)를 사용하세요.

### 데이터 흐름 / Data Flow

```
┌─────────────┐
│   REGTECH   │
│ (자동 수집)  │
└──────┬──────┘
       │
┌──────▼──────┐
│  Collector  │ :8545
│ (Python ETL)│
└──────┬──────┘
       │
┌──────▼──────┐     ┌────────┐
│ PostgreSQL  │────▶│ Redis  │
│ (15 tables) │     │(Cache) │
└──────┬──────┘     └────────┘
       │
┌──────▼──────┐
│  Flask API  │ :2542
│(Threat Feed)│
└───┬─────┬───┘
    │     │
┌───▼──┐ ┌▼───────────┐
│Forti │ │ Cloudflare  │
│Gate  │ │  WAF (push) │
│(pull)│ │             │
└──────┘ └─────────────┘
```

---

## 주요 기능 / Features

| 기능 / Feature | 설명 / Description |
|----------------|--------------------|
| **자동 수집 / Automated Collection** | REGTECH 포털에서 위협 IP를 스케줄링 기반으로 자동 수집 |
| **실시간 대시보드 / Dashboard** | Next.js 15 기반 분석 대시보드 (통계, 추이, 필터링) |
| **FortiGate 연동 / FortiGate Integration** | Threat Feed API를 통한 FortiGate 외부 커넥터 연동 (pull 방식) |
| **Cloudflare WAF / Cloudflare WAF Integration** | Lists API를 통한 IP 자동 push (Enterprise, 500K 한도) |
| **오프라인 배포 / Air-gap Deployment** | 에어갭 환경을 위한 Docker 번들 배포 지원 |
| **자격증명 암호화 / Credential Encryption** | AES-256-GCM 기반 DB 암호화 저장 (Settings UI 관리) |
| **2,175 자동화 테스트 / Automated Tests** | Backend (pytest 1,754), Frontend (vitest 421), E2E (Playwright) |

---

## 아키텍처 / Architecture

### 서비스 구성 / Service Composition

| 서비스 / Service | 기술 스택 / Tech Stack | 포트 / Port | 볼륨 / Volume |
|------------------|------------------------|-------------|---------------|
| `blacklist-frontend` | Next.js 15 (standalone, SSL 내장) | 443 | — |
| `blacklist-app` | Flask API (Raw SQL, 수동 DI) | 2542 | `blacklist-app-data` |
| `blacklist-collector` | Python ETL (scheduled collection) | 8545 | `blacklist-collector-log` |
| `blacklist-postgres` | PostgreSQL 15 | 5432 | `blacklist-postgres-data` |
| `blacklist-redis` | Redis 7 (Cache) | 6379 | `blacklist-redis-data` |

### 프로젝트 구조 / Project Structure

```
blacklist/
├── collector/                    # Python ETL Collector Service
│   ├── api/
│   │   └── enhanced_collection_api.py
│   ├── core/
│   │   ├── fortigate/            # FortiGate integration
│   │   │   ├── collector.py
│   │   │   ├── parsers.py
│   │   │   └── ssh_client.py
│   │   ├── database/              # PostgreSQL layer
│   │   │   ├── queries.py
│   │   │   └── service.py
│   │   ├── regtech/              # REGTECH source integration
│   │   │   ├── auth.py
│   │   │   ├── collector.py
│   │   │   └── data_processor.py
│   │   ├── multi_source/         # Multi-source collection
│   │   │   ├── collector.py
│   │   │   ├── models.py
│   │   │   └── parsers.py
│   │   ├── archive_manager.py
│   │   ├── data_quality_manager.py
│   │   ├── fortigate_collector.py
│   │   ├── multi_source_collector.py
│   │   ├── policy_monitor.py
│   │   ├── rate_limiter.py
│   │   ├── regtech_collector.py
│   │   ├── regtech_excel.py
│   │   ├── regtech_parsers.py
│   │   └── validators.py
│   ├── scheduler/
│   │   ├── dependencies.py
│   │   ├── manager.py
│   │   └── operations.py
│   ├── config.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── run_collector.py
├── postgres/                     # PostgreSQL Schema & Migrations
│   ├── initdb/
│   │   ├── 01-extensions.sql
│   │   ├── 02-schema.sql
│   │   └── 03-migrations.sql
│   ├── migrations/
│   │   ├── 001_add_data_source_column.sql
│   │   ├── 002_add_missing_columns.sql
│   │   ├── 003_add_display_order.sql
│   │   ├── 004_update_active_blacklist_view.sql
│   │   ├── 005_add_composite_indexes.sql
│   │   └── 006_fix_is_active_inconsistency.sql
│   └── Dockerfile
├── _bot-scripts/                 # GitHub Automation & CI/CD
│   ├── workflows/                # 37 GitHub Actions workflows
│   ├── requirements.txt
│   └── docker-compose.github_app.yml
├── AGENTS.md                     # Agent/Swarm definitions
├── CHANGELOG.md
├── CONTRIBUTING.md
├── Makefile                      # DevOps commands
├── commitlint.config.js
├── mypy.ini                      # Type checking config
└── pyproject.toml                # Python project config
```

---

## 자동화 인벤토리 / Automation Inventory

### GitHub Actions 워크플로우 (37개) / Workflows (37 Total)

#### Pull Request 자동화 / PR Automation

| 워크플로우 / Workflow | 설명 / Description |
|----------------------|-------------------|
| `01_branch-to-pr.yml` | 브랜치 → PR 전환 자동화 |
| `03_pr-checks.yml` | PR 체크 مجموع (lint, test, build) |
| `04_actionlint.yml` | GitHub Actions YAML lint |
| `05_gitleaks.yml` | シークレット 스캐닝 |
| `06_codeql.yml` | CodeQL 보안 분석 |
| `07_dependency-review.yml` | 의존성 보안 검토 |
| `08_scorecard.yml` | OpenSSF Scorecard 평가 |
| `09_semantic-pr.yml` | Semantic PR 제목 검증 |
| `10_pr-review.yml` | 자동 PR 리뷰 |
| `12_dependabot-auto-merge.yml` | Dependabot 자동 머지 |
| `13_pr-auto-merge.yml` | 자동 머지 조건 충족 시 |
| `14_bot-auto-fix.yml` | 봇 자동 수정 |
| `45_reusable-gitleaks.yml` | 재사용 가능한 gitleaks |
| `44_reusable-pr-checks.yml` | 재사용 가능한 PR 체크 |
| `security/11_pr-review.yml` | 보안 PR 리뷰 |

#### 이슈 관리 자동화 / Issue Management

| 워크플로우 / Workflow | 설명 / Description |
|----------------------|-------------------|
| `02_issue-to-branch.yml` | 이슈 → 브랜치 전환 |
| `18_issue-management.yml` | 자동 이슈 관리 |
| `19_issue-backfill.yml` | 이슈 백필 |
| `37_ci-failure-issues.yml` | CI 실패 시 자동 이슈 생성 |
| `43_reusable-issue-management.yml` | 재사용 가능한 이슈 관리 |
| `42_reusable-docs-sync.yml` | 문서 동기화 워크플로우 |

#### 릴리스 자동화 / Release Automation

| 워크플로우 / Workflow | 설명 / Description |
|----------------------|-------------------|
| `24_release-notes.yml` | 자동 릴리스 노트 생성 |
| `25_release-publish.yml` | 릴리스 게시 automation |
| `60_ci-auto-heal.yml` | CI 자동 복구 |

#### CI/CD 자동화 / CI/CD Automation

| 워크플로우 / Workflow | 설명 / Description |
|----------------------|-------------------|
| `ci.yml` | 기본 CI 파이프라인 |
| `standard-ci.yml` | 표준 CI 설정 |
| `auto-merge.yml` | 자동 머지 orchestration |
| `build-images.yml` | Docker 이미지 빌드 |
| `release.yml` | 릴리스 파이프라인 |
| `security.yml` | 보안 스캐닝 파이프라인 |
| `_ci-node.yml` | 재사용 가능한 Node.js CI |
| `welcome.yml` | 신규 기여자 환영 메시지 |
| `labeler.yml` | PR 라벨 자동 할당 |

#### 문서 자동화 / Documentation Automation

| 워크플로우 / Workflow | 설명 / Description |
|----------------------|-------------------|
| `20_readme-gen.yml` | README 자동 생성 |
| `21_docs-sync.yml` | 문서 동기화 |
| `42_reusable-docs-sync.yml` | 재사용 가능 문서 동기화 |

#### 유지보수 자동화 / Maintenance Automation

| 워크플로우 / Workflow | 설명 / Description |
|----------------------|-------------------|
| `15_merged-pr-cleanup.yml` | 병합된 PR 브랜치 정리 |
| `29_downstream-health-check.yml` | 다운스트림 헬스 체크 |

### 도구 및 런타임 / Tools & Runtimes

| 도구 / Tool | 용도 / Purpose | 설정 / Config |
|------------|----------------|---------------|
| **pytest 1,754** | Python 백엔드 테스트 | `pyproject.toml` |
| **vitest 421** | JavaScript 프론트엔드 테스트 | — |
| **Playwright** | E2E 테스트 | — |
| **Ruff** | Python linting (`E, F, W`, line-length: 120) | `pyproject.toml` |
| **mypy** | Python 타입 체킹 | `mypy.ini` |
| **ESLint** | JavaScript linting | — |
| **Prettier** | 코드 포맷팅 | — |
| **pre-commit** | Git hooks (Ruff, mypy, secret detection) | — |
| **commitlint** |Conventional Commits 검증 | `commitlint.config.js` |
| **Gitleaks** | 시크릿 스캐닝 | — |
| **CodeQL** | 정적 보안 분석 | — |
| **Docker** | 컨테이너화 (5 서비스) | `Dockerfile` |
| **docker compose** | 개발 환경 orchestration | `deploy/docker-compose.yml` |

### Python 환경 / Python Environment

```toml
# pyproject.toml
[tool.ruff]
line-length = 120
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W"]
ignore = ["E501", "W291", "W293"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
markers = ["unit", "integration", "security", "db", "api"]
```

---

## 빠른 시작 / Quick Start

### 전제 조건 / Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Git

### 1단계: 클론 / Clone

```bash
git clone https://github.com/jclee941/blacklist.git
cd blacklist
```

### 2단계: 환경 설정 / Setup

```bash
# Deploy directory로 이동
cd deploy

# 환경 변수 복사
cp .env.example .env  # Edit as needed

# Docker Compose 실행
docker compose up -d
```

### 3단계: 확인 / Verify

```bash
# 서비스 상태 확인
docker compose ps

# 헬스 체크
curl http://localhost:2542/health

# 로그 확인
docker compose logs -f
```

### 접근 주소 / Access URLs

| 서비스 | 주소 |
|--------|------|
| Frontend (Next.js) | https://localhost:443 |
| Flask API | http://localhost:2542 |
| Collector API | http://localhost:8545 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

---

## 로컬 개발 / Local Development

### Makefile 명령어 / Makefile Commands

```bash
# Git hooks 설치 (pre-commit + husky)
make setup-hooks

# 개발 환경 시작 ( hot reload )
make dev

# rebuild 없이 개발 환경 시작 (빠른 시작)
make dev-no-build

# 프로덕션과 유사한 환경 시작
make dev-prod

# 앱 서비스만 재시작
make dev-app

# 특정 명령어 확인
make help
```

### 사용 가능한 명령어 / Available Commands

| 명령어 / Command | 설명 / Description |
|-----------------|-------------------|
| `make help` | 도움말 표시 |
| `make setup-hooks` | Git hooks 설치 (pre-commit) |
| `make dev` | 개발 환경 (hot reload)