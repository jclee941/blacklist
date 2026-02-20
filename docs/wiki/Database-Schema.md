# 데이터베이스 스키마

## 개요

- **DBMS**: PostgreSQL 15 Alpine
- **드라이버**: psycopg2 (Raw SQL, ORM 사용 금지)
- **익스텐션**: `uuid-ossp`, `pg_stat_statements`, `pg_trgm`
- **스키마 버전**: 3.0.0 + 마이그레이션 6건

> **정책**: 모든 쿼리는 파라미터화(`%s`) 필수. SQL 문자열 연결 금지.

---

## 테이블 목록

| # | 테이블 | 유형 | 설명 |
|---|--------|------|------|
| 1 | `blacklist_ips` | 테이블 | 메인 블랙리스트 IP (핵심 테이블) |
| 2 | `collection_credentials` | 테이블 | 수집 인증정보 |
| 3 | `collection_history` | 테이블 | 수집 이력 |
| 4 | `collection_status` | 테이블 | 수집 상태 |
| 5 | `collection_metrics` | 테이블 | 수집 메트릭 |
| 6 | `collection_stats` | 테이블 | 수집 통계 (마이그레이션 002) |
| 7 | `monitoring_data` | 테이블 | 모니터링 데이터 |
| 8 | `system_logs` | 테이블 | 시스템 로그 |
| 9 | `pipeline_metrics` | 테이블 | 파이프라인 메트릭 |
| 10 | `whitelist_ips` | 테이블 | 화이트리스트 IP (마이그레이션) |
| 11 | `fortigate_devices` | 테이블 | FortiGate 장비 (마이그레이션) |
| 12 | `fortinet_pull_logs` | 테이블 | Fortinet Pull 로그 (마이그레이션 002) |
| 13 | `credentials` | 테이블 | 크레덴셜 (마이그레이션) |
| 14 | `settings` | 테이블 | 설정 (마이그레이션) |
| 15 | `system_settings` | 테이블 | 시스템 설정 (마이그레이션) |
| 16 | `unified_ip_list` | 테이블 | 통합 IP 목록 (마이그레이션) |
| 17 | `active_blacklist` | **뷰** | 활성 블랙리스트 (is_active=TRUE) |
| 18 | `blacklist_ips_with_auto_inactive` | **뷰** | 자동 비활성화 포함 뷰 |
| 19 | `collection_statistics` | **뷰** | 수집 통계 집계 |
| 20 | `recent_activity` | **뷰** | 최근 24시간 활동 |

---

## 핵심 테이블 정의

### `blacklist_ips` — 메인 블랙리스트

```sql
CREATE TABLE blacklist_ips (
    id              SERIAL PRIMARY KEY,
    ip_address      VARCHAR(45) NOT NULL,
    reason          TEXT,
    source          VARCHAR(100) NOT NULL,
    category        VARCHAR(50) DEFAULT 'unknown',
    confidence_level INTEGER DEFAULT 50
                    CHECK (confidence_level >= 0 AND confidence_level <= 100),
    detection_count INTEGER DEFAULT 1,
    is_active       BOOLEAN DEFAULT TRUE,
    country         VARCHAR(10),          -- ISO 국가 코드
    detection_date  DATE,                 -- 최초 탐지 날짜
    removal_date    DATE,                 -- 제거 날짜
    last_seen       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    raw_data        JSONB,                -- 원본 데이터 (마이그레이션 002)
    data_source     VARCHAR(50),          -- 데이터 소스 (마이그레이션 001)

    CONSTRAINT unique_ip_source UNIQUE(ip_address, source),
    CONSTRAINT valid_ip_format CHECK (ip_address ~ '^([0-9]{1,3}\.){3}[0-9]{1,3}$'),
    CONSTRAINT detection_before_removal CHECK (
        removal_date IS NULL OR detection_date <= removal_date
    )
);
```

**인덱스** (9개):

| 인덱스 | 컬럼 |
|--------|------|
| `idx_blacklist_ips_ip` | `ip_address` |
| `idx_blacklist_ips_source` | `source` |
| `idx_blacklist_ips_category` | `category` |
| `idx_blacklist_ips_country` | `country` |
| `idx_blacklist_ips_detection_date` | `detection_date` |
| `idx_blacklist_ips_removal_date` | `removal_date` |
| `idx_blacklist_ips_last_seen` | `last_seen` |
| `idx_blacklist_ips_active` | `is_active` |
| `idx_blacklist_ips_confidence` | `confidence_level` |

**복합 인덱스** (마이그레이션 005):
- `idx_blacklist_ips_source_active` — `(source, is_active)`
- `idx_blacklist_ips_detection_active` — `(detection_date, is_active)`

---

### `collection_credentials` — 수집 인증정보

```sql
CREATE TABLE collection_credentials (
    id           SERIAL PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL UNIQUE,
    username     VARCHAR(255),
    password     TEXT,                    -- AES-256-GCM 암호화 저장
    config       JSONB DEFAULT '{}',
    encrypted    BOOLEAN DEFAULT FALSE,
    is_active    BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_service_name CHECK (service_name ~ '^[A-Z_]+$')
);
```

---

### `collection_history` — 수집 이력

```sql
CREATE TABLE collection_history (
    id               SERIAL PRIMARY KEY,
    service_name     VARCHAR(100) NOT NULL,
    collection_date  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    items_collected  INTEGER DEFAULT 0,
    success          BOOLEAN DEFAULT FALSE,
    error_message    TEXT,
    execution_time_ms INTEGER DEFAULT 0,
    details          JSONB DEFAULT '{}',

    CONSTRAINT positive_items CHECK (items_collected >= 0),
    CONSTRAINT positive_execution_time CHECK (execution_time_ms >= 0)
);
```

---

### `collection_status` — 수집 상태

```sql
CREATE TABLE collection_status (
    id            SERIAL PRIMARY KEY,
    service_name  VARCHAR(100) NOT NULL UNIQUE,
    enabled       BOOLEAN DEFAULT TRUE,
    last_run      TIMESTAMP,
    next_run      TIMESTAMP,
    status        VARCHAR(50) DEFAULT 'idle',
    error_count   INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    config        JSONB DEFAULT '{}',
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_status CHECK (status IN ('idle', 'running', 'error', 'disabled')),
    CONSTRAINT non_negative_counts CHECK (error_count >= 0 AND success_count >= 0)
);
```

---

### `monitoring_data` — 모니터링

```sql
CREATE TABLE monitoring_data (
    id              SERIAL PRIMARY KEY,
    metric_name     VARCHAR(100) NOT NULL,
    metric_value    DECIMAL(12,4),
    metric_unit     VARCHAR(20),
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    additional_data JSONB DEFAULT '{}',
    tags            JSONB DEFAULT '{}',
    numeric_value   DECIMAL(12,4),    -- 호환성
    unit            VARCHAR(20),      -- 호환성

    CONSTRAINT valid_metric_name CHECK (metric_name != '')
);
```

---

### `system_logs` — 시스템 로그

```sql
CREATE TABLE system_logs (
    id                 SERIAL PRIMARY KEY,
    level              VARCHAR(20) NOT NULL DEFAULT 'INFO',
    message            TEXT NOT NULL,
    module             VARCHAR(100),
    function_name      VARCHAR(100),
    line_number        INTEGER,
    timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    additional_context JSONB DEFAULT '{}',

    CONSTRAINT valid_log_level CHECK (
        level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    )
);
```

---

### `pipeline_metrics` — 파이프라인 메트릭

```sql
CREATE TABLE pipeline_metrics (
    timestamp      TIMESTAMP NOT NULL,
    pipeline_name  VARCHAR(100) NOT NULL,
    execution_time DECIMAL(10,3) DEFAULT 0,
    success_rate   DECIMAL(5,2) DEFAULT 0,
    error_count    INTEGER DEFAULT 0,
    status         VARCHAR(20) DEFAULT 'unknown',
    metadata       JSONB DEFAULT '{}',

    PRIMARY KEY (timestamp, pipeline_name),
    CONSTRAINT valid_success_rate CHECK (success_rate >= 0 AND success_rate <= 100)
);
```

---

### `collection_metrics` — 수집 메트릭

```sql
CREATE TABLE collection_metrics (
    id                 SERIAL PRIMARY KEY,
    service_name       VARCHAR(100) NOT NULL,
    collection_count   INTEGER DEFAULT 0,
    success_count      INTEGER DEFAULT 0,
    avg_execution_time DECIMAL(10,3) DEFAULT 0,
    last_collection    TIMESTAMP,
    metadata           JSONB DEFAULT '{}',
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT success_not_exceed_total CHECK (success_count <= collection_count)
);
```

---

## 뷰 정의

### `active_blacklist` — 활성 블랙리스트

```sql
CREATE OR REPLACE VIEW active_blacklist AS
SELECT ip_address, reason, source, category, confidence_level,
       country, detection_date, detection_count, last_seen, created_at
FROM blacklist_ips
WHERE is_active = TRUE
ORDER BY last_seen DESC, confidence_level DESC;
```

### `collection_statistics` — 수집 통계

```sql
CREATE OR REPLACE VIEW collection_statistics AS
SELECT service_name,
       COUNT(*) as total_collections,
       COUNT(CASE WHEN success THEN 1 END) as successful_collections,
       ROUND(COUNT(CASE WHEN success THEN 1 END)::decimal / COUNT(*)::decimal * 100, 2) as success_rate,
       SUM(items_collected) as total_items_collected,
       AVG(execution_time_ms) as avg_execution_time_ms,
       MAX(collection_date) as last_collection_date
FROM collection_history
GROUP BY service_name;
```

### `recent_activity` — 최근 활동 (24시간)

```sql
CREATE OR REPLACE VIEW recent_activity AS
SELECT 'collection' as activity_type, service_name as source,
       items_collected as count, collection_date as timestamp, success as status
FROM collection_history
WHERE collection_date >= NOW() - INTERVAL '24 hours'
UNION ALL
SELECT 'blacklist_update', source, 1, updated_at, true
FROM blacklist_ips
WHERE updated_at >= NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;
```

---

## 트리거

| 트리거 | 테이블 | 이벤트 | 동작 |
|--------|--------|--------|------|
| `update_blacklist_ips_updated_at` | `blacklist_ips` | BEFORE UPDATE | `updated_at = NOW()` |
| `update_collection_credentials_updated_at` | `collection_credentials` | BEFORE UPDATE | `updated_at = NOW()` |
| `update_collection_status_updated_at` | `collection_status` | BEFORE UPDATE | `updated_at = NOW()` |
| `update_collection_metrics_updated_at` | `collection_metrics` | BEFORE UPDATE | `updated_at = NOW()` |

---

## 마이그레이션 이력

| # | 파일 | 설명 |
|---|------|------|
| 001 | `001_add_data_source_column.sql` | `blacklist_ips`에 `data_source` 컬럼 추가 |
| 002 | `002_add_missing_columns.sql` | `last_collection`, `raw_data` 컬럼 추가, `fortinet_pull_logs`/`collection_stats` 테이블 생성 |
| 003 | `003_add_display_order.sql` | 표시 순서 컬럼 추가 |
| 004 | `004_update_active_blacklist_view.sql` | `active_blacklist` 뷰 업데이트 |
| 005 | `005_add_composite_indexes.sql` | 복합 인덱스 추가 (성능 최적화) |
| 006 | `006_fix_is_active_inconsistency.sql` | `is_active` 컬럼 불일치 수정 |

---

## 커넥션 풀 구성

### App (Flask)

| 설정 | 값 |
|------|----|
| 풀 타입 | `ThreadedConnectionPool` (psycopg2) |
| 최소 커넥션 | 3 |
| 최대 커넥션 | 8 |
| 재시도 | 최대 10회, Exponential backoff (2^n초) |
| 에러 억제 | 60초 윈도우 내 최대 5회 로그 |

### Collector

| 설정 | 값 |
|------|----|
| 최대 커넥션 | 20 |
| IP 캐시 TTL | 24시간 |
| IP 캐시 최대 | 100,000건 |
| LRU 방출 | 초과 시 하위 10% 제거 |

### 호스트 우선순위

`DATABASE_URL` → `POSTGRES_URL` → `POSTGRES_HOST` (기본값: `blacklist-postgres` → `postgres` → `localhost`)
