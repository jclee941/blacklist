# 시스템 아키텍처

## 개요

Blacklist Intelligence Platform은 5개의 Docker 컨테이너로 구성된 마이크로서비스 아키텍처입니다.  
모든 서비스는 `network_mode: host`로 동작하며, Docker Named Volume으로 데이터를 영속화합니다.

---

## 서비스 토폴로지

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
- App / Flask API / :2542 (APP) -> FORTIMGR
- FortiGate / 방화벽 (FORTIGATE) -> App / Flask API / :2542 (APP)


---

## 서비스 상세

| 서비스 | 이미지 | 포트 | 헬스체크 | 의존성 | 볼륨 |
|--------|--------|------|----------|--------|------|
| **blacklist-postgres** | `postgres:15-alpine` | 5432 | `pg_isready` | 없음 | `blacklist-pgdata` |
| **blacklist-redis** | `redis:7-alpine` | 6379 | `redis-cli ping` | 없음 | `blacklist-redis-data` |
| **blacklist-collector** | `python:3.11-slim` | 8545 | `curl /health` | postgres, redis | `blacklist-collector-data` |
| **blacklist-app** | `python:3.11-slim` | 2542 | `curl /health` | postgres, redis | `blacklist-logs`, `blacklist-uploads` |
| **blacklist-frontend** | `node:20-alpine` | 443 | `curl --insecure /health` | app | — |

### 헬스체크 설정 (공통)

- **Interval**: 30초
- **Timeout**: 10초
- **Retries**: 3회
- **Start Period**: 서비스별 상이 (postgres 40초, app 90초, frontend 60초)

---

## 데이터 흐름

### 1. IP 수집 흐름 (ETL)

#### Diagram summary 2

- Type: sequence
- Participant: U as 사용자/스케줄러
- Participant: A as App (:2542)
- Participant: C as Collector (:8545)
- Participant: R as REGTECH
- Participant: DB as PostgreSQL
- Participant: RD as Redis
- U -> A: POST /api/collection/trigger/regtech
- A -> C: HTTP POST /trigger/regtech
- C -> R: HTTPS 로그인 (다단계 인증)
- R -> C: 인증 토큰
- C -> R: Excel/HTML 데이터 요청
- R -> C: 위협 IP 데이터
- C -> DB: INSERT ... ON CONFLICT DO UPDATE
- C -> RD: 캐시 무효화
- C -> A: 수집 결과 (itemscollected, success)
- A -> U: 200 OK {collected: N}


### 2. IP 조회 흐름

#### Diagram summary 3

- Type: sequence
- Participant: B as 브라우저
- Participant: F as Frontend (:443)
- Participant: A as App (:2542)
- Participant: RD as Redis
- Participant: DB as PostgreSQL
- B -> F: GET /ip-management
- F -> A: GET /api/ip-management/unified?page=1
- A -> RD: 캐시 확인
- RD -> A: 캐시된 데이터
- A -> DB: SELECT ... FROM blacklistips
- DB -> A: IP 목록
- A -> RD: 캐시 저장 (TTL)
- A -> F: JSON {items, total, page}
- F -> B: 렌더링된 페이지


### 3. FortiGate 연동 흐름

#### Diagram summary 4

- Type: sequence
- Participant: FG as FortiGate 장비
- Participant: A as App (:2542)
- Participant: DB as PostgreSQL
- FG -> A: GET /api/fortinet/threat-feed
- A -> DB: SELECT active IPs
- A -> FG: Plain text IP 목록


---

## 통신 패턴

| 구간 | 프로토콜 | 인증 | 비고 |
|------|----------|------|------|
| 브라우저 → Frontend | HTTPS (443) | — | Self-signed SSL 내장 |
| Frontend → App | HTTP (2542) | Bearer JWT | Next.js rewrites 프록시 |
| App → Collector | HTTP (8545) | 없음 | 내부 네트워크 전용 |
| App → PostgreSQL | TCP (5432) | 패스워드 | ThreadedConnectionPool |
| App → Redis | TCP (6379) | 없음 | 캐시 전용 |
| Collector → REGTECH | HTTPS | 다단계 인증 | 세션 기반 |

---

## Flask Application Factory

`app/core/app.py` (479줄, complexity 39.91)에서 Flask 앱을 생성합니다.

### 초기화 순서

#### Diagram summary 5

- Type: flowchart
- 1. Flask 인스턴스 생성 (A) -> 2. 설정 로드 (config.py) (B)
- 2. 설정 로드 (config.py) (B) -> 3. JWT 서비스 초기화 (C)
- 3. JWT 서비스 초기화 (C) -> 4. 보안 미들웨어 / (CSRF, Rate Limit, Headers) (D)
- 4. 보안 미들웨어 / (CSRF, Rate Limit, Headers) (D) -> 5. ServiceFactory DI / (14개 서비스) (E)
- 5. ServiceFactory DI / (14개 서비스) (E) -> 6. Blueprint 등록 / (API + Web) (F)
- 6. Blueprint 등록 / (API + Web) (F) -> 7. 미들웨어 체인 / (Request ID, Compression) (G)
- 7. 미들웨어 체인 / (Request ID, Compression) (G) -> 8. 헬스체크 엔드포인트 (H)
- 8. 헬스체크 엔드포인트 (H) -> 9. 백그라운드 태스크 / (Expiry, Scheduler) (I)


### 핵심 패턴

```python
# DI 패턴 (필수): Flask extensions를 통한 서비스 접근
service = current_app.extensions['blacklist_service']

# 에러 처리: RFC 7807 Problem Detail
raise APIError(status=400, code="VALID_IP", message="유효하지 않은 IP 형식")

# 공개 엔드포인트: @public 데코레이터
@public
@bp.route("/health")
def health(): ...
```

---

## 환경별 구성

| 환경 | Compose 파일 | 네트워크 | 이미지 |
|------|-------------|----------|--------|
| **개발** | `deploy/docker-compose.yml` | host | 소스 빌드 |
| **CI** | `.github/docker-compose.ci.yml` | bridge | Pre-built |
| **프로덕션** | `deploy/base.yml` + `release.yml` | host | GHCR 이미지 |
| **오프라인** | `deploy/base.yml` + `release.yml` | host | `docker load` |

---

## ServiceFactory DI 의존성 그래프

14개 서비스가 `ServiceFactory`에 의해 엄격한 순서로 초기화됩니다.  
순서 변경 시 의존성 미충족으로 런타임 에러가 발생합니다.

#### Diagram summary 6

- Type: flowchart
- Component: dbservice / DatabaseService (DB)
- Component: redisservice / RedisService (REDIS)
- Component: cacheservice / CacheService (CACHE)
- Component: blacklistservice / BlacklistService (BL)
- Component: collectionservice / CollectionService (COLL)
- Component: firewallservice / FirewallService (FW)
- Component: settingsservice / SettingsService (SET)
- Component: credentialservice / CredentialService (CRED)
- Component: threatfeedservice / ThreatFeedService (TF)
- Component: metricservice / MetricService (METRIC)
- Component: healthservice / HealthService (HEALTH)
- Component: statisticsservice / StatisticsService (STATS)
- Component: analyticsservice / AnalyticsService (ANAL)
- dbservice / DatabaseService (DB) -> blacklistservice / BlacklistService (BL)
- dbservice / DatabaseService (DB) -> collectionservice / CollectionService (COLL)
- dbservice / DatabaseService (DB) -> firewallservice / FirewallService (FW)
- dbservice / DatabaseService (DB) -> settingsservice / SettingsService (SET)
- dbservice / DatabaseService (DB) -> statisticsservice / StatisticsService (STATS)
- dbservice / DatabaseService (DB) -> analyticsservice / AnalyticsService (ANAL)
- redisservice / RedisService (REDIS) -> cacheservice / CacheService (CACHE)
- cacheservice / CacheService (CACHE) -> blacklistservice / BlacklistService (BL)
- cacheservice / CacheService (CACHE) -> statisticsservice / StatisticsService (STATS)
- credentialservice / CredentialService (CRED) -> settingsservice / SettingsService (SET)
- credentialservice / CredentialService (CRED) -> collectionservice / CollectionService (COLL)
- blacklistservice / BlacklistService (BL) -> threatfeedservice / ThreatFeedService (TF)
- dbservice / DatabaseService (DB) -> healthservice / HealthService (HEALTH)
- redisservice / RedisService (REDIS) -> healthservice / HealthService (HEALTH)
- metricservice / MetricService (METRIC) -> healthservice / HealthService (HEALTH)


### 초기화 순서 (변경 금지)

```
1. db_service          # PostgreSQL 연결 풀
2. redis_service        # Redis 연결
3. cache_service        # Redis 기반 캐시
4. credential_service   # AES-256-GCM 암호화
5. settings_service     # 시스템 설정
6. blacklist_service    # 블랙리스트 CRUD
7. collection_service   # 수집 관리
8. firewall_service     # 방화벽 규칙
9. threat_feed_service  # Threat Feed 생성
10. statistics_service   # 통계/분석
11. analytics_service    # 분석 엔진
12. health_service       # 헬스체크 (마지막 — 모든 서비스 상태 확인)
```

---

## Collector 파이프라인 아키텍처

Collector는 Flask와 독립된 Python 프로세스로, APScheduler 기반 ETL 파이프라인입니다.

#### Diagram summary 7

- Type: flowchart
- Component: CollectorApplication / runcollector.py (ENTRY)
- Component: CollectionScheduler / APScheduler (SCHED)
- Component: HealthServer / GET /health (HEALTH)
- Component: SchedulerAPI / REST 제어 (API)
- Component: RegtechAuth / 다단계 인증 (RA)
- Component: RegtechCollector / 데이터 수집 (RC)
- Component: RegtechParser / Excel/HTML 파싱 (RP)
- Component: AsyncFeedAggregator / 비동기 수집 (MS)
- Component: ParserMixin / 포맷 파싱 (MP)
- Component: DedupeMerger / 중복 제거 (MD)
- Component: IPValidator / IP 검증 (IPV)
- Component: DataQualityManager / 품질 관리 (DQM)
- Component: RateLimiter / Token Bucket (RL)
- Component: PostgreSQL (DB)
- Component: Redis (RD)
- CollectorApplication / runcollector.py (ENTRY) -> CollectionScheduler / APScheduler (SCHED)
- CollectorApplication / runcollector.py (ENTRY) -> HealthServer / GET /health (HEALTH)
- CollectorApplication / runcollector.py (ENTRY) -> SchedulerAPI / REST 제어 (API)
- CollectionScheduler / APScheduler (SCHED) -> RegtechCollector / 데이터 수집 (RC)
- CollectionScheduler / APScheduler (SCHED) -> AsyncFeedAggregator / 비동기 수집 (MS)
- RegtechCollector / 데이터 수집 (RC) -> RegtechAuth / 다단계 인증 (RA)
- RegtechCollector / 데이터 수집 (RC) -> RegtechParser / Excel/HTML 파싱 (RP)
- AsyncFeedAggregator / 비동기 수집 (MS) -> ParserMixin / 포맷 파싱 (MP)
- AsyncFeedAggregator / 비동기 수집 (MS) -> DedupeMerger / 중복 제거 (MD)
- RegtechParser / Excel/HTML 파싱 (RP) -> IPValidator / IP 검증 (IPV)
- ParserMixin / 포맷 파싱 (MP) -> IPValidator / IP 검증 (IPV)
- IPValidator / IP 검증 (IPV) -> DataQualityManager / 품질 관리 (DQM)
- DataQualityManager / 품질 관리 (DQM) -> PostgreSQL (DB)
- DataQualityManager / 품질 관리 (DQM) -> Redis (RD)
- RateLimiter / Token Bucket (RL) -> RegtechCollector / 데이터 수집 (RC)
- RateLimiter / Token Bucket (RL) -> AsyncFeedAggregator / 비동기 수집 (MS)


### 스케줄링 정책

| 작업 | 주기 | 전략 |
|------|------|------|
| REGTECH 수집 | 매일 02:00 | Cron (고정) |
| Multi-Source 수집 | 300s ~ 3600s | 적응형 (성공률 기반) |
| 데이터 정리 | 매일 00:00 | Cron (만료 IP 삭제) |
| 헬스 리포트 | 60s | Interval |

---

## CI/CD 파이프라인

#### Diagram summary 8

- Type: flowchart
- Component: Push/PR / master 브랜치 (PUSH)
- Component: Tag / v 생성 (TAG)
- Component: Lint / Ruff + ESLint (LINT)
- Component: Backend Test / pytest ≥80% (TESTBE)
- Component: Frontend Test / Vitest (TESTFE)
- Component: Docker Build / 5 서비스 매트릭스 (BUILD)
- Component: E2E Test / Playwright (E2E)
- Component: Version 검증 / VERSION ↔ Tag (VALIDATE)
- Component: 이미지 빌드 / 5 서비스 × amd64 (IMG)
- Component: 오프라인 번들 / tar.gz + sha256 (BUNDLE)
- Component: GHCR Push / ghcr.io/qws941 (GHCR)
- Component: GitHub Release / 번들 + 체인지로그 (GHREL)
- Push/PR / master 브랜치 (PUSH) -> Lint / Ruff + ESLint (LINT)
- Lint / Ruff + ESLint (LINT) -> Backend Test / pytest ≥80% (TESTBE)
- Lint / Ruff + ESLint (LINT) -> Frontend Test / Vitest (TESTFE)
- Backend Test / pytest ≥80% (TESTBE) -> Docker Build / 5 서비스 매트릭스 (BUILD)
- Frontend Test / Vitest (TESTFE) -> Docker Build / 5 서비스 매트릭스 (BUILD)
- Docker Build / 5 서비스 매트릭스 (BUILD) -> E2E Test / Playwright (E2E)
- Tag / v 생성 (TAG) -> Version 검증 / VERSION ↔ Tag (VALIDATE)
- Version 검증 / VERSION ↔ Tag (VALIDATE) -> 이미지 빌드 / 5 서비스 × amd64 (IMG)
- 이미지 빌드 / 5 서비스 × amd64 (IMG) -> 오프라인 번들 / tar.gz + sha256 (BUNDLE)
- 이미지 빌드 / 5 서비스 × amd64 (IMG) -> GHCR Push / ghcr.io/qws941 (GHCR)
- 오프라인 번들 / tar.gz + sha256 (BUNDLE) -> GitHub Release / 번들 + 체인지로그 (GHREL)
- GHCR Push / ghcr.io/qws941 (GHCR) -> GitHub Release / 번들 + 체인지로그 (GHREL)


### 프로덕션 배포 (오프라인)

#### Diagram summary 9

- Type: flowchart
- GitHub Release (GH) -> 오프라인 번들 / tar.gz (BUNDLE)
- 오프라인 번들 / tar.gz (BUNDLE) -> 프로덕션 서버 (SERVER)
- 프로덕션 서버 (SERVER) -> Docker 이미지 로드 (IMAGES)
- Docker 이미지 로드 (IMAGES) -> 서비스 시작 (DEPLOY)
- 서비스 시작 (DEPLOY) -> 배포 검증 (VERIFY)


---

## 데이터베이스 관계도 (ER Diagram)

#### Diagram summary 10

- Type: entity relationship
- blacklistips relates to collectionhistory: 수집됨
- collectionconfig relates to collectionhistory: 설정
- fortigatedevices relates to fortigatepushhistory: Push 기록
- blacklistips relates to threatfeedlogs: 제공됨
- credentials relates to collectionconfig: 인증 정보


### 주요 테이블 요약

| 구분 | 테이블 | 설명 |
|------|--------|------|
| **핵심** | blacklist_ips | 위협 IP (메인 테이블) |
| **핵심** | whitelist_ips | 화이트리스트 |
| **수집** | collection_history | 수집 이력 |
| **수집** | collection_config | 수집 설정 |
| **연동** | fortigate_devices | FortiGate 장비 |
| **연동** | fortigate_push_history | Push 이력 |
| **연동** | threat_feed_logs | Threat Feed 접근 로그 |
| **시스템** | credentials | 암호화된 인증 정보 |
| **시스템** | system_settings | 시스템 설정 |
| **뷰** | v_active_blacklist | 활성 블랙리스트 뷰 |
| **뷰** | v_collection_summary | 수집 요약 뷰 |
| **뷰** | v_threat_stats | 위협 통계 뷰 |
| **뷰** | v_ip_management | IP 통합 관리 뷰 |
