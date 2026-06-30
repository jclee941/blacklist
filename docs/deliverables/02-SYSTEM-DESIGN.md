# 시스템 설계서 (System Design)

**프로젝트명:** REGTECH 블랙리스트 인텔리전스 플랫폼  
**버전:** 3.6.9
**작성일:** 2026-02-27
**문서번호:** DES-REGTECH-2026-001

---

## 1. 시스템 개요

### 1.1 시스템 구성도

#### Diagram summary 1

- Type: flowchart
- Component: REGTECH / 한국금융보안원 (REGTECH)
- Component: FortiGate / 방화벽 (FORTIGATE)
- Component: PostgreSQL 15 / :5432 (PG)
- Component: Redis 7 / :6379 (REDIS)
- Component: Collector / ETL Service / :8545 (COLLECTOR)
- Component: App / Flask API / :2542 (APP)
- Component: Frontend / Next.js 15 / :443 (FRONTEND)
- Component: 웹 브라우저 (BROWSER)
- REGTECH / 한국금융보안원 (REGTECH) -> Collector / ETL Service / :8545 (COLLECTOR)
- Collector / ETL Service / :8545 (COLLECTOR) -> PostgreSQL 15 / :5432 (PG)
- Collector / ETL Service / :8545 (COLLECTOR) -> Redis 7 / :6379 (REDIS)
- App / Flask API / :2542 (APP) -> PostgreSQL 15 / :5432 (PG)
- App / Flask API / :2542 (APP) -> Redis 7 / :6379 (REDIS)
- App / Flask API / :2542 (APP) -> Collector / ETL Service / :8545 (COLLECTOR)
- Frontend / Next.js 15 / :443 (FRONTEND) -> App / Flask API / :2542 (APP)
- 웹 브라우저 (BROWSER) -> Frontend / Next.js 15 / :443 (FRONTEND)
- FortiGate / 방화벽 (FORTIGATE) -> App / Flask API / :2542 (APP)


### 1.2 설계 원칙

| 원칙 | 설명 | 구현 방식 |
|------|------|----------|
| **Air-Gap First** | 폐쇄망 환경 우선 설계 | Docker 이미지 번들, 오프라인 설치 스크립트 |
| **Manual DI** | 수동 의존성 주입 | ServiceFactory 패턴, `current_app.extensions[]` |
| **Raw SQL Only** | ORM 사용 금지 | SQLAlchemy/Prisma 배제, parameterized `%s` 사용 |
| **Shared-Nothing** | 서비스 간 코드 공유 금지 | DB/Redis/HTTP로만 통신 |
| **Proxy Mandate** | API 프록시 강제 | Frontend는 `lib/api.ts` 통해서만 API 호출 |
| **Host Network** | Docker host 네트워크 모드 | `network_mode: host`, Named Volume 영속화 |

---

## 2. 서비스 아키텍처

### 2.1 서비스 목록

| 서비스 | 이미지 | 포트 | 헬스체크 | 볼륨 |
|--------|--------|------|----------|------|
| **blacklist-frontend** | `node:20-alpine` | 443 | `curl --insecure /health` | — |
| **blacklist-app** | `python:3.11-slim` | 2542 | `curl /health` | `blacklist-logs`, `blacklist-uploads` |
| **blacklist-collector** | `python:3.11-slim` | 8545 | `curl /health` | `blacklist-collector-data` |
| **blacklist-postgres** | `postgres:15-alpine` | 5432 | `pg_isready` | `blacklist-pgdata` |
| **blacklist-redis** | `redis:7-alpine` | 6379 | `redis-cli ping` | `blacklist-redis-data` |

### 2.2 Frontend Service (Next.js 15)

```
frontend/
├── app/                    # App Router (Server Components)
│   ├── page.tsx            # Dashboard
│   ├── ip-management/      # IP 관리
│   ├── collection/         # 수집 관리
│   ├── fortinet/           # Fortinet 연동
│   ├── analytics/          # 분석 대시보드
│   ├── monitoring/         # 시스템 모니터링
│   ├── settings/           # 설정
│   └── database/           # DB 관리
├── components/
│   └── ui/                 # Radix UI / shadcn Primitives
├── lib/
│   └── api.ts              # Centralized API Client (필수 프록시)
├── hooks/                  # Custom React hooks
├── types/                  # TypeScript 인터페이스
├── __tests__/              # Unit tests (Vitest, 39 files, 448 tests)
└── e2e/                    # E2E tests (Playwright)
```

**기술 스택:**
- Next.js 15.x (App Router, Standalone output)
- React 19.x, TypeScript 5.x
- Tailwind CSS v4
- React Query (서버 상태), Zustand (클라이언트 상태)
- 내장 SSL (Self-signed, Docker 이미지 포함)

### 2.3 Backend API Service (Flask)

```
app/
├── run_app.py              # Entry Point
├── core/
│   ├── app.py              # Application Factory (479L, complexity 39.91)
│   ├── config.py           # 48 @property 환경 설정
│   ├── routes/
│   │   ├── api/            # REST API (6 blueprints, CSRF-exempt)
│   │   │   ├── blacklist/  # 블랙리스트 CRUD (core/management/batch/system)
│   │   │   ├── collection/ # 수집 관리 (9 files, 18 endpoints)
│   │   │   ├── fortinet/   # Fortinet 연동 (threat feed, device, health)
│   │   │   ├── ip_management/ # IP 관리 (11 routes)
│   │   │   └── ...         # dashboard, settings, analytics, error_metrics
│   │   └── web/            # Legacy 한국어 Admin (5 blueprints, Jinja2)
│   ├── services/           # 14개 비즈니스 서비스 (ServiceFactory DI)
│   ├── auth/               # JWT 인증 (현재 비활성)
│   ├── database/           # SmartConnectionManager, 복구 메커니즘
│   ├── monitoring/         # Prometheus 메트릭
│   ├── exceptions/         # RFC 7807 APIError 계층
│   └── utils/              # 응답 헬퍼, AES-256-GCM 암호화, 캐싱, 검증
├── requirements.txt
└── Dockerfile
```

**기술 스택:**
- Flask 3.x (Application Factory 패턴)
- Python 3.11+, psycopg2 (ThreadedConnectionPool)
- Flask-Limiter (Rate Limiting)

### 2.4 Collector Service (ETL)

```
collector/
├── run_collector.py        # CollectorApplication entry point
├── config.py               # CollectorConfig
├── scheduler.py            # CollectionScheduler (APScheduler, adaptive 300s–3600s)
├── health_server.py        # HealthServer (:8545)
└── core/
    ├── database.py         # Collector DatabaseService
    ├── regtech/            # REGTECH 수집 패키지
    │   ├── regtech_collector.py
    │   ├── regtech_auth.py     # 다단계 인증 (세션 기반)
    │   ├── regtech_parser.py
    │   └── regtech_data_processor.py
    ├── multi_source/       # 멀티소스 수집 패키지
│   ├── fortigate_collector.py
│   └── generic_parser.py
    ├── data_quality.py     # DataQualityManager
    ├── ip_validator.py     # IPValidator
    └── rate_limiter.py     # Token Bucket Rate Limiter
```

**기술 스택:**
- Python 3.11+ (독립 런타임, Flask 미사용)
- APScheduler, Requests/httpx, BeautifulSoup4, openpyxl

**Collector 엔드포인트:**

| 경로 | 메서드 | 설명 |
|------|--------|------|
| `/health` | GET | 헬스체크 |
| `/status` | GET | 전체 상태 |
| `/trigger/<source>` | POST | 수집 트리거 |
| `/api/scheduler/status` | GET | 스케줄러 상태 |
| `/api/scheduler/force-collection/<source>` | POST | 강제 수집 |
| `/api/test-auth/<source>` | GET | 인증 테스트 |

---

## 3. 데이터베이스 설계

### 3.1 ER 다이어그램

#### Diagram summary 2

- Type: entity relationship
- collectioncredentials relates to collectionhistory: servicename
- fortigatedevices relates to fortigatepulllogs: deviceip


### 3.2 주요 테이블 (15개)

| 테이블 | 용도 | 주요 컬럼 |
|--------|------|----------|
| `blacklist_ips` | 위협 IP 저장 | ip_address, source, category, confidence_level, is_active, raw_data(JSONB) |
| `whitelist_ips` | 신뢰 IP 저장 | ip_address, reason, source, country |
| `unified_ip_list` | 블랙+화이트 통합 | ip_address, list_type, source, is_active |
| `collection_credentials` | 수집 서비스 인증정보 | service_name, username, password, config(JSONB), encrypted |
| `collection_history` | 수집 이력 | service_name, items_collected, success, execution_time_ms |
| `collection_status` | 수집 상태 | service_name, enabled, status(idle/running/error/disabled) |
| `collection_metrics` | 수집 메트릭 | service_name, collection_count, success_count, avg_execution_time |
| `collection_stats` | 소스별 통계 | source, total_ips, last_seen |
| `pipeline_metrics` | 파이프라인 메트릭 | pipeline_name, execution_time, success_rate, status |
| `monitoring_data` | 모니터링 데이터 | metric_name, metric_value, tags(JSONB) |
| `system_logs` | 시스템 로그 | level(DEBUG~CRITICAL), message, module |
| `system_settings` | 시스템 설정 | setting_key, setting_value, setting_type, is_encrypted |
| `credentials` | 암호화 인증정보 | service_name, encrypted_data |
| `fortigate_devices` | FortiGate 장비 | device_ip, device_name, firmware_version, config(JSONB) |
| `fortigate_pull_logs` | FortiGate Pull 로그 | device_ip, user_agent, request_count |

### 3.3 뷰 (4개)

| 뷰 | 용도 |
|----|------|
| `active_blacklist` | 활성 블랙리스트 (is_active, ordered by last_seen, confidence) |
| `collection_statistics` | 서비스별 수집 통계 집계 |
| `blacklist_ips_with_auto_inactive` | 30일 미확인 자동 비활성 |
| `settings` | system_settings 별칭 |

### 3.4 인덱스 및 확장

- **인덱스:** 50+ (`IF NOT EXISTS`), 단일 + 복합 인덱스
- **확장:** `uuid-ossp`, `pg_trgm`
- **트리거:** `updated_at` 자동 갱신
- **마이그레이션:** 6개 (001–006, `postgres/migrations/`)

---

## 4. 서비스 레이어 설계

### 4.1 Service Factory (DI Container)

#### Diagram summary 3

- Type: flowchart
- Component: DatabaseService / (기반) (DB)
- DatabaseService / (기반) (DB) -> BlacklistService (BL)
- DatabaseService / (기반) (DB) -> AnalyticsService (AN)
- DatabaseService / (기반) (DB) -> CollectionService (COL)
- DatabaseService / (기반) (DB) -> CredentialService (CRED)
- DatabaseService / (기반) (DB) -> SecureCredentialService (SCRED)
- DatabaseService / (기반) (DB) -> RegtechConfigService (RTC)
- DatabaseService / (기반) (DB) -> SettingsService (SET)
- DatabaseService / (기반) (DB) -> ScoringService (SCO)
- DatabaseService / (기반) (DB) -> IPExpiryService (EXP)
- DatabaseService / (기반) (DB) -> ABTestService (AB)
- DatabaseService / (기반) (DB) -> OptimizedBlacklistService (OPT)
- CollectionService (COL) -> CollectionScheduler (SCHED)


### 4.2 초기화 순서 (14개 서비스)

| 순서 | 서비스 | Extension 키 | 책임 |
|------|--------|-------------|------|
| 1 | DatabaseService | `db_service` | Raw SQL, ThreadedConnectionPool, 자동 복구 |
| 2 | BlacklistService | `blacklist_service` | IP CRUD, 검색, 캐싱 |
| 3 | AnalyticsService | `analytics_service` | 통계, 집계 |
| 4 | CollectionService | `collection_service` | 수집 오케스트레이션 |
| 5 | CollectionScheduler | `scheduler_service` | 백그라운드 스케줄링 |
| 6 | CredentialService | `credential_service` | 인증정보 관리 |
| 7 | SecureCredentialService | `secure_credential_service` | AES-256-GCM 암호화 |
| 8 | RegtechConfigService | `regtech_config_service` | REGTECH 설정 |
| 9 | SettingsService | `settings_service` | 시스템 설정 CRUD |
| 10 | ScoringService | `scoring_service` | 위협 점수 산출 |
| 11 | IPExpiryService | `expiry_service` | IP 만료 관리 |
| 12 | ABTestService | `ab_test_service` | A/B 테스트 |
| 13 | OptimizedBlacklistService | `optimized_blacklist_service` | 최적화 블랙리스트 |

---

## 5. 보안 설계

### 5.1 보안 계층

#### Diagram summary 4

- Type: flowchart
- Component: JWT 인증 / (현재 비활성, app.py:155) (JWT)
- Component: CSRF Protection / (Flask-WTF, API exempt) (CSRF)
- Component: Rate Limiting / (Flask-Limiter, Redis-backed) (RL)
- Component: Security Headers / (HSTS, X-Content-Type, X-Frame) (SH)
- Component: AES-256-GCM / 인증정보 암호화 (AES)
- Component: PBKDF2 / 키 파생 (PBKDF)
- Component: CREDENTIALMASTERKEY / (환경 외부 파일) (MASTER)
- CREDENTIALMASTERKEY / (환경 외부 파일) (MASTER) -> PBKDF2 / 키 파생 (PBKDF)


### 5.2 네트워크 보안

| 구간 | 프로토콜 | 인증 |
|------|----------|------|
| 브라우저 → Frontend | HTTPS (443) | — (Self-signed SSL) |
| Frontend → App | HTTP (2542) | Bearer JWT (비활성) |
| App → Collector | HTTP (8545) | 없음 (내부 전용) |
| App → PostgreSQL | TCP (5432) | 패스워드 |
| App → Redis | TCP (6379) | 없음 (캐시 전용) |
| Collector → REGTECH | HTTPS | 다단계 인증 (세션 기반) |

---

## 6. 배포 설계

### 6.1 오프라인 배포 흐름

#### Diagram summary 5

- Type: flowchart
- Docker Build / (5 서비스) (B1) -> docker save / + tar.gz (B2)
- docker save / + tar.gz (B2) -> GitHub Release / 번들 업로드 (B3)
- 번들 다운로드 / (USB/물리 매체) (D1) -> install.sh / (docker load) (D2)
- install.sh / (docker load) (D2) -> docker compose up (D3)
- GitHub Release / 번들 업로드 (B3) -> 번들 다운로드 / (USB/물리 매체) (D1)


### 6.2 배포 모드

| 모드 | 설명 | Compose 파일 | 네트워크 |
|------|------|-------------|----------|
| **개발** | 로컬 핫 리로드 | `deploy/docker-compose.yml` | host |
| **CI** | GitHub Actions | `.github/docker-compose.ci.yml` | bridge |
| **프로덕션** | 오프라인 번들 | `deploy/base.yml` + `release.yml` | host |

> Traefik reverse proxy는 v3.5.x에서 제거됨. Frontend가 SSL을 직접 처리합니다.

---

## 7. 변경 이력

| 버전 | 일자 | 변경 내용 |
|------|------|----------|
| 1.0 | 2026-01-15 | 초기 작성 (v3.5.11) |
| 2.0 | 2026-02-23 | v3.6.3 전면 갱신: Traefik 제거, 포트 수정(Frontend=443), JWT 인증 체계, AES-256-GCM 암호화, 15 테이블/4 뷰 DB 스키마, 14 서비스 DI, Collector 아키텍처 갱신, Mermaid 다이어그램 |
| 3.0 | 2026-02-27 | v3.6.9 현행화, 테스트 수 갱신: Frontend 테스트 39개 파일 448개로 증가, 총 164개 테스트 파일 2,368개 테스트
