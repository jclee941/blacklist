# Changelog

All notable changes to the Blacklist Intelligence Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
