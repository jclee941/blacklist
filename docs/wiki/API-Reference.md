# API 레퍼런스

## 개요

- **베이스 URL**: `http://localhost:2542/api`
- **프로토콜**: REST (JSON)
- **인증**: Bearer JWT (현재 비활성화 — 모든 엔드포인트 공개)
- **에러 형식**: RFC 7807 Problem Detail
- **총 엔드포인트**: 80+

### 에러 응답 형식

```json
{
  "type": "https://blacklist.local/errors/invalid-ip",
  "title": "Validation Error",
  "status": 400,
  "detail": "유효하지 않은 IP 형식입니다",
  "code": "VALID_IP"
}
```

**에러 코드 접두사**: `AUTH_`, `VALID_`, `NOT_FOUND_`, `INTERNAL_`

---

## 인증 (Authentication)

> Blueprint: `auth` | Prefix: `/api/auth`

| 메서드 | 경로 | 인증 | 설명 |
|--------|------|------|------|
| POST | `/api/auth/login` | @public | 로그인 → JWT 토큰 반환 |
| GET | `/api/auth/me` | JWT | 현재 사용자 정보 |
| GET | `/api/auth/verify` | JWT | 토큰 유효성 검증 |
| GET | `/api/auth/status` | — | 인증 시스템 상태 (REGTECH 크레덴셜 확인) |

### POST `/api/auth/login`

```json
// Request
{"username": "admin", "password": "admin"}

// Response 200
{"token": "eyJhbG...", "expires_in": 28800, "user": {"id": 1, "role": "admin"}}
```

---

## 핵심 API (Core)

> Blueprint: `core` | Prefix: `/api`

| 메서드 | 경로 | 인증 | 설명 |
|--------|------|------|------|
| GET | `/api/health` | @public | 서비스 헬스체크 (graceful degradation) |
| GET | `/api/docs` | — | API 문서 |
| GET | `/api/stats` | — | 대시보드 통계 |
| GET | `/api/status` | — | 시스템 상태 |

---

## IP 관리 (IP Management)

> Blueprint: `ip_management` | Prefix: `/api/ip-management`

### 통합 목록

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/ip-management/unified` | 통합 IP 목록 (페이지네이션, 필터) |
| GET | `/api/ip-management/list` | IP 목록 |
| GET | `/api/ip-management/statistics` | IP 통계 |

### 화이트리스트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/ip-management/whitelist` | 화이트리스트 조회 (페이지네이션) |
| POST | `/api/ip-management/whitelist` | 화이트리스트 IP 추가 |
| PUT | `/api/ip-management/whitelist/<id>` | 화이트리스트 IP 수정 |
| DELETE | `/api/ip-management/whitelist/<id>` | 화이트리스트 IP 삭제 |

### 블랙리스트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/ip-management/blacklist` | 블랙리스트 조회 (페이지네이션) |
| POST | `/api/ip-management/blacklist` | 블랙리스트 IP 추가 |
| PUT | `/api/ip-management/blacklist/<id>` | 블랙리스트 IP 수정 |
| DELETE | `/api/ip-management/blacklist/<id>` | 블랙리스트 IP 삭제 |

### 요청/응답 예시

```json
// GET /api/ip-management/unified?page=1&per_page=20&source=REGTECH
// Response 200
{
  "items": [
    {
      "id": 1,
      "ip_address": "192.168.1.100",
      "source": "REGTECH",
      "category": "malware",
      "confidence_level": 85,
      "is_active": true,
      "country": "KR",
      "detection_date": "2025-01-15",
      "detection_count": 3
    }
  ],
  "total": 1500,
  "page": 1,
  "per_page": 20
}
```

---

## 수집 관리 (Collection)

> Blueprint: `collection` | Prefix: `/api/collection`

### 상태 및 이력

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/collection/status` | 수집 상태 (actively_collecting, last_collection, next_scheduled) |
| GET | `/api/collection/health` | 수집 서비스 헬스체크 |
| GET | `/api/collection/history` | 수집 이력 (페이지네이션) |
| GET | `/api/collection/statistics` | 수집 통계 (서비스별, 날짜별) |

### 트리거

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/collection/trigger/<source>` | 수집 트리거 (REGTECH 등) — Collector :8545로 HTTP POST |
| POST | `/api/collection/data/refresh` | 데이터 강제 새로고침 |
| POST | `/api/collection/config/update` | 수집 설정 업데이트 |

### 동기화

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/collection/sync/collector` | Collector 서비스와 동기화 |

### 인증정보

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/collection/credentials` | 전체 인증정보 목록 |
| GET | `/api/collection/credentials/<source>` | 소스별 인증정보 |
| PUT | `/api/collection/credentials/<source>` | 인증정보 업데이트 |
| POST | `/api/collection/credentials/<source>/test` | 인증정보 연결 테스트 |

### 소스

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/collection/sources` | 소스 목록 (REGTECH 등) |
| GET | `/api/collection/sources/<source_id>` | 소스 상세 |
| GET | `/api/collection/sources/<source_id>/status` | 소스 상태 |

---

## FortiGate 연동 (Fortinet)

> Blueprint: `fortinet` | Prefix: `/api/fortinet`

### 데이터

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/fortinet/active-ips` | FortiGate용 활성 IP (JSON) |
| GET | `/api/fortinet/blocklist` | 차단 목록 (format=json 또는 csv) |
| GET | `/api/fortinet/threat-feed` | Threat Feed (plain text IP 목록) |
| GET | `/api/fortinet/json-connector` | JSON Connector 형식 |

### 장비 관리

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/fortinet/devices` | FortiGate 장비 목록 |
| GET | `/api/fortinet/config` | FortiGate 설정 |
| GET | `/api/fortinet/health` | 연동 헬스체크 |

### 로그

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/fortinet/active-sessions` | 활성 세션 |
| GET | `/api/fortinet/pull-logs` | Pull 로그 (페이지네이션) |

---

## 분석 (Analytics)

> Blueprint: `analytics` | Prefix: `/api/analytics`

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/analytics/detection-timeline` | 일별 탐지 통계 (days 파라미터, 기본 30일) |

---

## 대시보드 (Dashboard)

> Blueprint: `dashboard` | Prefix: `/api/dashboard`

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/dashboard/stats` | 대시보드 통계 (total_ips, active_ips, by_source, by_country) |
| GET | `/api/dashboard/status` | 대시보드 상태 (service, components, collection) |

---

## 시스템 관리 (System)

> Blueprint: `system` | Prefix: `/api`

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/monitoring/dashboard` | 모니터링 대시보드 (total_ips, recent_collections) |
| GET | `/api/system-stats` | 시스템 통계 (소스별, 국가별, 사유별) |
| GET | `/api/chart/data` | 차트 데이터 (30일 수집 타임라인) |
| GET | `/api/logs` | 시스템 로그 (최근 100줄) |
| POST | `/api/reset-database` | DB 초기화 (X-Admin-Key 헤더 필요) |
| GET | `/api/database/schema` | 스키마 정보 (테이블, 컬럼, 타입) |
| GET | `/api/database/tables` | 데이터베이스 테이블 목록 |
| POST | `/api/database/schema/update` | 스키마 업데이트 |
| POST | `/api/database/schema/fix` | 스키마 강제 수정 |

---

## 설정 (Settings)

> Blueprint: `settings` | Prefix: `/api/settings`

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/settings` | 전체 설정 (category 필터, include_encrypted 플래그) |
| GET | `/api/settings/all` | 전체 설정 (별칭) |
| GET | `/api/settings/grouped` | 카테고리별 설정 |
| GET | `/api/settings/<key>` | 특정 설정 조회 |
| POST | `/api/settings` | 설정 생성 |
| PUT | `/api/settings/<key>` | 설정 수정 (body: {value, encrypt: bool}) |
| PUT | `/api/settings/batch` | 일괄 설정 수정 |
| DELETE | `/api/settings/<key>` | 설정 삭제 |

---

## Web Admin API

> Blueprint: `admin` | Prefix: `/`

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/regtech/credentials` | REGTECH 인증정보 설정 |
| GET | `/regtech/credentials` | REGTECH 인증정보 조회 |
| POST | `/regtech/test-connection` | REGTECH 연결 테스트 |
| PUT | `/regtech/update-password` | REGTECH 비밀번호 변경 |
| POST | `/regtech/initialize` | REGTECH 초기화 |
| DELETE | `/regtech/credentials` | REGTECH 인증정보 삭제 |
| POST | `/regtech/collect` | REGTECH 수집 트리거 |
| GET | `/api/admin/regtech/credentials` | API: REGTECH 인증정보 |
| POST | `/api/admin/regtech/credentials` | API: REGTECH 인증정보 저장 |
| DELETE | `/api/admin/regtech/credentials` | API: REGTECH 인증정보 삭제 |
| POST | `/api/admin/regtech/test-connection` | API: REGTECH 연결 테스트 |
| GET | `/api/credentials/<service_name>` | 서비스별 크레덴셜 조회 |
| POST | `/api/credentials/<service_name>` | 서비스별 크레덴셜 저장 |
| DELETE | `/api/credentials/<service_name>` | 서비스별 크레덴셜 삭제 |

---

## Frontend API 클라이언트

프론트엔드는 `lib/api.ts`를 통해 모든 API를 호출합니다.

### 인스턴스

| 인스턴스 | 타임아웃 | 용도 |
|----------|----------|------|
| `api` | 60초 | 일반 API 호출 |
| `collectionApi` | 300초 | 수집 관련 장시간 작업 |

### JWT 처리

- 저장: `localStorage` 키 `blacklist_auth_token`
- 자동 첨부: Axios request interceptor (`Authorization: Bearer <token>`)
- 프록시: Next.js `rewrites` — `/api/*` → `http://localhost:2542/api/*`

### 주요 메서드

```typescript
// 인증
authApi.login(username, password)
authApi.verify()

// IP 관리
api.get('/ip-management/unified', { params })
api.post('/ip-management/blacklist', payload)
api.put('/ip-management/whitelist/{id}', payload)
api.delete('/ip-management/blacklist/{id}')

// 수집
collectionApi.post('/collection/trigger/regtech')
api.get('/collection/status')
api.get('/collection/history')

// FortiGate
api.get('/fortinet/blocklist')
api.get('/fortinet/pull-logs', { params })

// 설정
api.get('/settings/grouped')
api.put('/settings/batch', { settings })
```
