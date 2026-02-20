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
