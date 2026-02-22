# 시스템 아키텍처

## 개요

Blacklist Intelligence Platform은 5개의 Docker 컨테이너로 구성된 마이크로서비스 아키텍처입니다.  
모든 서비스는 `network_mode: host`로 동작하며, Docker Named Volume으로 데이터를 영속화합니다.

---

## 서비스 토폴로지

```mermaid
graph TD
    subgraph "External Sources"
        REGTECH["REGTECH<br/>한국금융보안원"]
        SECUDIUM["Secudium/ISAP<br/>SK쉴더스"]
        FORTIGATE["FortiGate<br/>방화벽"]
    end

    subgraph "Blacklist Platform (Docker Host Network)"
        PG[("PostgreSQL 15<br/>:5432")]
        REDIS[("Redis 7<br/>:6379")]
        COLLECTOR["Collector<br/>ETL Service<br/>:8545"]
        APP["App<br/>Flask API<br/>:2542"]
        FRONTEND["Frontend<br/>Next.js 15<br/>:443"]
    end

    subgraph "Clients"
        BROWSER["웹 브라우저"]
        FORTIMGR["FortiManager"]
    end

    REGTECH -->|HTTPS| COLLECTOR
    SECUDIUM -->|HTTPS + OTP| COLLECTOR
    COLLECTOR -->|Raw SQL| PG
    COLLECTOR -->|캐시| REDIS
    APP -->|Raw SQL| PG
    APP -->|캐시/메트릭| REDIS
    APP -->|HTTP POST| COLLECTOR
    FRONTEND -->|Proxy /api/*| APP
    BROWSER -->|HTTPS :443| FRONTEND
    APP -->|JSON-RPC| FORTIMGR
    FORTIGATE -->|Pull| APP
```

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

```mermaid
sequenceDiagram
    participant U as 사용자/스케줄러
    participant A as App (:2542)
    participant C as Collector (:8545)
    participant R as REGTECH
    participant S as Secudium
    participant DB as PostgreSQL
    participant RD as Redis

    U->>A: POST /api/collection/trigger/regtech
    A->>C: HTTP POST /trigger/regtech
    C->>R: HTTPS 로그인 (다단계 인증)
    R-->>C: 인증 토큰
    C->>R: Excel/HTML 데이터 요청
    R-->>C: 위협 IP 데이터
    C->>DB: INSERT ... ON CONFLICT DO UPDATE
    C->>RD: 캐시 무효화
    C-->>A: 수집 결과 (items_collected, success)
    A-->>U: 200 OK {collected: N}
```

### 2. IP 조회 흐름

```mermaid
sequenceDiagram
    participant B as 브라우저
    participant F as Frontend (:443)
    participant A as App (:2542)
    participant RD as Redis
    participant DB as PostgreSQL

    B->>F: GET /ip-management
    F->>A: GET /api/ip-management/unified?page=1
    A->>RD: 캐시 확인
    alt 캐시 히트
        RD-->>A: 캐시된 데이터
    else 캐시 미스
        A->>DB: SELECT ... FROM blacklist_ips
        DB-->>A: IP 목록
        A->>RD: 캐시 저장 (TTL)
    end
    A-->>F: JSON {items, total, page}
    F-->>B: 렌더링된 페이지
```

### 3. FortiGate 연동 흐름

```mermaid
sequenceDiagram
    participant FG as FortiGate 장비
    participant A as App (:2542)
    participant FM as FortiManager
    participant DB as PostgreSQL

    Note over A,FM: Push 방식 (App → FortiManager)
    A->>DB: SELECT active IPs
    A->>FM: JSON-RPC: Address Object 생성
    A->>FM: JSON-RPC: 정책 할당
    FM-->>FG: 정책 배포

    Note over FG,A: Pull 방식 (FortiGate → App)
    FG->>A: GET /api/fortinet/threat-feed
    A->>DB: SELECT active IPs
    A-->>FG: Plain text IP 목록
```

---

## 통신 패턴

| 구간 | 프로토콜 | 인증 | 비고 |
|------|----------|------|------|
| 브라우저 → Frontend | HTTPS (443) | — | Self-signed SSL 내장 |
| Frontend → App | HTTP (2542) | Bearer JWT | Next.js rewrites 프록시 |
| App → Collector | HTTP (8545) | 없음 | 내부 네트워크 전용 |
| App → PostgreSQL | TCP (5432) | 패스워드 | ThreadedConnectionPool |
| App → Redis | TCP (6379) | 없음 | 캐시 전용 |
| App → FortiManager | HTTPS | API 키 | JSON-RPC |
| Collector → REGTECH | HTTPS | 다단계 인증 | 세션 기반 |
| Collector → Secudium | HTTPS | OTP (이메일) | 토큰 기반 (4시간 TTL) |

---

## Flask Application Factory

`app/core/app.py` (479줄, complexity 39.91)에서 Flask 앱을 생성합니다.

### 초기화 순서

```mermaid
graph TD
    A["1. Flask 인스턴스 생성"] --> B["2. 설정 로드 (config.py)"]
    B --> C["3. JWT 서비스 초기화"]
    C --> D["4. 보안 미들웨어<br/>(CSRF, Rate Limit, Headers)"]
    D --> E["5. ServiceFactory DI<br/>(14개 서비스)"]
    E --> F["6. Blueprint 등록<br/>(API + Web)"]
    F --> G["7. 미들웨어 체인<br/>(Request ID, Compression)"]
    G --> H["8. 헬스체크 엔드포인트"]
    H --> I["9. 백그라운드 태스크<br/>(Expiry, Scheduler)"]
```

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

```mermaid
graph TD
    subgraph "Infrastructure Layer"
        DB["db_service<br/>DatabaseService"]
        REDIS["redis_service<br/>RedisService"]
        CACHE["cache_service<br/>CacheService"]
    end

    subgraph "Core Business Layer"
        BL["blacklist_service<br/>BlacklistService"]
        COLL["collection_service<br/>CollectionService"]
        FW["firewall_service<br/>FirewallService"]
        SET["settings_service<br/>SettingsService"]
        CRED["credential_service<br/>CredentialService"]
    end

    subgraph "Integration Layer"
        FM["fortimanager_service<br/>FortiManagerService"]
        FMP["fortimanager_push_service<br/>FortiManagerPushService"]
        TF["threat_feed_service<br/>ThreatFeedService"]
    end

    subgraph "Monitoring Layer"
        METRIC["metric_service<br/>MetricService"]
        HEALTH["health_service<br/>HealthService"]
    end

    subgraph "Analytics Layer"
        STATS["statistics_service<br/>StatisticsService"]
        ANAL["analytics_service<br/>AnalyticsService"]
    end

    DB --> BL
    DB --> COLL
    DB --> FW
    DB --> SET
    DB --> STATS
    DB --> ANAL
    DB --> FM
    REDIS --> CACHE
    CACHE --> BL
    CACHE --> STATS
    CRED --> SET
    CRED --> COLL
    BL --> FMP
    FM --> FMP
    BL --> TF
    DB --> HEALTH
    REDIS --> HEALTH
    METRIC --> HEALTH
```

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
9. fortimanager_service # FortiManager API
10. fortimanager_push_service  # 정책 Push
11. threat_feed_service  # Threat Feed 생성
12. statistics_service   # 통계/분석
13. analytics_service    # 분석 엔진
14. health_service       # 헬스체크 (마지막 — 모든 서비스 상태 확인)
```

---

## Collector 파이프라인 아키텍처

Collector는 Flask와 독립된 Python 프로세스로, APScheduler 기반 ETL 파이프라인입니다.

```mermaid
graph TD
    subgraph "Collector Application (:8545)"
        ENTRY["CollectorApplication<br/>run_collector.py"]
        SCHED["CollectionScheduler<br/>APScheduler"]
        HEALTH["HealthServer<br/>GET /health"]
        API["SchedulerAPI<br/>REST 제어"]
    end

    subgraph "REGTECH Pipeline"
        RA["RegtechAuth<br/>다단계 인증"]
        RC["RegtechCollector<br/>데이터 수집"]
        RP["RegtechParser<br/>Excel/HTML 파싱"]
    end

    subgraph "Multi-Source Pipeline"
        MS["AsyncFeedAggregator<br/>비동기 수집"]
        MP["ParserMixin<br/>포맷 파싱"]
        MD["DedupeMerger<br/>중복 제거"]
    end

    subgraph "Data Quality"
        IPV["IPValidator<br/>IP 검증"]
        DQM["DataQualityManager<br/>품질 관리"]
        RL["RateLimiter<br/>Token Bucket"]
    end

    subgraph "Storage"
        DB[("PostgreSQL")]
        RD[("Redis")]
    end

    ENTRY --> SCHED
    ENTRY --> HEALTH
    ENTRY --> API
    SCHED -->|"매일 02:00"| RC
    SCHED -->|"적응형 300s~3600s"| MS
    RC --> RA
    RC --> RP
    MS --> MP
    MS --> MD
    RP --> IPV
    MP --> IPV
    IPV --> DQM
    DQM --> DB
    DQM --> RD
    RL -.->|"요청 제한"| RC
    RL -.->|"요청 제한"| MS
```

### 스케줄링 정책

| 작업 | 주기 | 전략 |
|------|------|------|
| REGTECH 수집 | 매일 02:00 | Cron (고정) |
| Multi-Source 수집 | 300s ~ 3600s | 적응형 (성공률 기반) |
| 데이터 정리 | 매일 00:00 | Cron (만료 IP 삭제) |
| 헬스 리포트 | 60s | Interval |

---

## CI/CD 파이프라인

```mermaid
graph LR
    subgraph "Trigger"
        PUSH["Push/PR<br/>master 브랜치"]
        TAG["Tag<br/>v* 생성"]
    end

    subgraph "CI Pipeline (ci.yml)"
        LINT["Lint<br/>Ruff + ESLint"]
        TEST_BE["Backend Test<br/>pytest ≥80%"]
        TEST_FE["Frontend Test<br/>Vitest"]
        BUILD["Docker Build<br/>5 서비스 매트릭스"]
        E2E["E2E Test<br/>Playwright"]
    end

    subgraph "Release Pipeline (release.yml)"
        VALIDATE["Version 검증<br/>VERSION ↔ Tag"]
        IMG["이미지 빌드<br/>5 서비스 × amd64"]
        BUNDLE["오프라인 번들<br/>tar.gz + sha256"]
        GHCR["GHCR Push<br/>ghcr.io/qws941"]
        GH_REL["GitHub Release<br/>번들 + 체인지로그"]
    end

    PUSH --> LINT
    LINT --> TEST_BE
    LINT --> TEST_FE
    TEST_BE --> BUILD
    TEST_FE --> BUILD
    BUILD --> E2E
    TAG --> VALIDATE
    VALIDATE --> IMG
    IMG --> BUNDLE
    IMG --> GHCR
    BUNDLE --> GH_REL
    GHCR --> GH_REL
```

### 프로덕션 배포 (오프라인)

```mermaid
graph LR
    GH["GitHub Release"] -->|"다운로드"| BUNDLE["오프라인 번들<br/>tar.gz"]
    BUNDLE -->|"전송"| SERVER["프로덕션 서버"]
    SERVER -->|"docker load"| IMAGES["Docker 이미지 로드"]
    IMAGES -->|"docker compose up"| DEPLOY["서비스 시작"]
    DEPLOY -->|"헬스체크"| VERIFY["배포 검증"]
```

---

## 데이터베이스 관계도 (ER Diagram)

```mermaid
erDiagram
    blacklist_ips {
        uuid id PK
        inet ip_address
        varchar source_system
        varchar threat_type
        integer risk_score
        timestamp detected_at
        timestamp expires_at
        boolean is_active
    }
    collection_history {
        uuid id PK
        varchar source
        integer items_collected
        varchar status
        timestamp started_at
        timestamp completed_at
    }
    collection_config {
        uuid id PK
        varchar source_name
        jsonb config_data
        boolean is_active
    }
    whitelist_ips {
        uuid id PK
        inet ip_address
        varchar reason
        timestamp created_at
    }
    fortigate_devices {
        uuid id PK
        varchar device_name
        varchar ip_address
        boolean is_active
    }
    fortigate_push_history {
        uuid id PK
        uuid device_id FK
        integer items_pushed
        varchar status
        timestamp pushed_at
    }
    threat_feed_logs {
        uuid id PK
        inet client_ip
        integer items_served
        timestamp accessed_at
    }
    credentials {
        uuid id PK
        varchar service_name
        bytea encrypted_data
        timestamp updated_at
    }
    system_settings {
        uuid id PK
        varchar key
        jsonb value
        timestamp updated_at
    }

    blacklist_ips ||--o{ collection_history : "수집됨"
    collection_config ||--o{ collection_history : "설정"
    fortigate_devices ||--o{ fortigate_push_history : "Push 기록"
    blacklist_ips ||--o{ threat_feed_logs : "제공됨"
    whitelist_ips }o--o{ blacklist_ips : "제외"
    credentials ||--o{ collection_config : "인증 정보"
```

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
