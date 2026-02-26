# API 명세서 (API Specification)

**프로젝트명:** REGTECH 블랙리스트 인텔리전스 플랫폼  
**버전:** 3.6.7
**작성일:** 2026-02-27
**문서번호:** API-REGTECH-2026-001

---

## 1. 개요

### 1.1 기본 정보
| 항목 | 값 |
|------|-----|
| Base URL | `https://blacklist.<YOUR_DOMAIN>/api` |
| 프로토콜 | HTTPS (TLS 1.2+) |
| 인증 | Session Cookie / Bearer Token |
| Content-Type | `application/json` |

### 1.2 응답 형식

**성공 응답:**
```json
{
  "success": true,
  "data": { ... }
}
```

**에러 응답 (RFC 7807):**
```json
{
  "type": "https://api.example.com/errors/validation",
  "title": "Validation Error",
  "status": 400,
  "detail": "ip_address field is required",
  "instance": "/api/ip/blacklist"
}
```

**페이지네이션 응답:**
```json
{
  "items": [...],
  "total": 1250,
  "page": 1,
  "per_page": 20,
  "pages": 63
}
```

### 1.3 HTTP 상태 코드

| 코드 | 의미 | 설명 |
|------|------|------|
| 200 | OK | 요청 성공 |
| 201 | Created | 리소스 생성 성공 |
| 400 | Bad Request | 잘못된 요청 (유효성 검증 실패) |
| 401 | Unauthorized | 인증 필요 |
| 403 | Forbidden | 권한 없음 |
| 404 | Not Found | 리소스 없음 |
| 429 | Too Many Requests | Rate Limit 초과 |
| 500 | Internal Server Error | 서버 오류 |

---

## 2. 대시보드 API

### 2.1 시스템 통계 조회
```
GET /api/dashboard/stats
```

**응답:**
```json
{
  "success": true,
  "data": {
    "total_ips": 15234,
    "active_blacklist": 12890,
    "new_today": 45,
    "last_updated": "2026-01-15T06:30:00Z"
  }
}
```

### 2.2 시스템 상태 조회
```
GET /api/dashboard/status
```

**응답:**
```json
{
  "success": true,
  "data": {
    "database": "connected",
    "redis": "connected",
    "collector": "running",
    "memory_usage": "45%",
    "cpu_usage": "12%"
  }
}
```

### 2.3 탐지 타임라인 조회
```
GET /api/analytics/detection-timeline?days=30
```

**파라미터:**
| 이름 | 타입 | 필수 | 설명 |
|------|------|------|------|
| days | integer | N | 조회 기간 (기본값: 30) |

**응답:**
```json
{
  "success": true,
  "data": [
    {"date": "2026-01-15", "count": 45},
    {"date": "2026-01-07", "count": 38}
  ]
}
```

---

## 3. IP 관리 API

### 3.1 블랙리스트 목록 조회
```
GET /api/ip/blacklist
```

**파라미터:**
| 이름 | 타입 | 필수 | 설명 |
|------|------|------|------|
| page | integer | N | 페이지 번호 (기본값: 1) |
| per_page | integer | N | 페이지당 항목 수 (기본값: 20, 최대: 100) |
| search | string | N | IP 주소 검색 |
| source | string | N | 소스 필터 (regtech, urlhaus, etc.) |
| is_active | boolean | N | 활성 상태 필터 |
| sort | string | N | 정렬 필드 (created_at, ip_address) |
| order | string | N | 정렬 순서 (asc, desc) |

**응답:**
```json
{
  "items": [
    {
      "id": 12345,
      "ip_address": "192.168.1.100",
      "source": "regtech",
      "threat_type": "malware",
      "is_active": true,
      "raw_data": {"country": "KR", "asn": "AS1234"},
      "created_at": "2026-01-15T06:00:00Z",
      "updated_at": "2026-01-15T06:00:00Z"
    }
  ],
  "total": 12890,
  "page": 1,
  "per_page": 20
}
```

### 3.2 블랙리스트 상세 조회
```
GET /api/ip/blacklist/{id}
```

**경로 파라미터:**
| 이름 | 타입 | 설명 |
|------|------|------|
| id | integer | IP 레코드 ID |

**응답:**
```json
{
  "success": true,
  "data": {
    "id": 12345,
    "ip_address": "192.168.1.100",
    "source": "regtech",
    "threat_type": "malware",
    "is_active": true,
    "raw_data": {
      "country": "KR",
      "asn": "AS1234",
      "first_seen": "2026-01-01",
      "tags": ["botnet", "c2"]
    },
    "created_at": "2026-01-15T06:00:00Z",
    "updated_at": "2026-01-15T06:00:00Z"
  }
}
```

### 3.3 블랙리스트 등록
```
POST /api/ip/blacklist
```

**요청 본문:**
```json
{
  "ip_address": "10.0.0.1",
  "threat_type": "phishing",
  "description": "수동 등록",
  "raw_data": {"note": "사용자 신고"}
}
```

**응답:**
```json
{
  "success": true,
  "data": {
    "id": 12346,
    "ip_address": "10.0.0.1",
    "source": "manual",
    "threat_type": "phishing",
    "is_active": true,
    "created_at": "2026-01-15T06:35:00Z"
  }
}
```

### 3.4 블랙리스트 수정
```
PUT /api/ip/blacklist/{id}
```

**요청 본문:**
```json
{
  "threat_type": "malware",
  "is_active": false,
  "description": "업데이트된 설명"
}
```

### 3.5 블랙리스트 삭제
```
DELETE /api/ip/blacklist/{id}
```

**응답:**
```json
{
  "success": true,
  "message": "IP successfully deactivated"
}
```

### 3.6 IP 검색
```
GET /api/search/{ip}
```

**경로 파라미터:**
| 이름 | 타입 | 설명 |
|------|------|------|
| ip | string | 검색할 IP 주소 |

**응답:**
```json
{
  "success": true,
  "data": {
    "found": true,
    "blacklist": {...},
    "whitelist": null
  }
}
```

### 3.7 화이트리스트 API
```
GET    /api/ip/whitelist          # 목록 조회
POST   /api/ip/whitelist          # 등록
PUT    /api/ip/whitelist/{id}     # 수정
DELETE /api/ip/whitelist/{id}     # 삭제
```

### 3.8 통합 목록 조회
```
GET /api/ip/unified
```

### 3.9 블랙리스트 통계
```
GET /api/blacklist/stats
```

### 3.10 Raw 데이터 내보내기
```
GET /api/blacklist/export-raw
```

---

## 4. 데이터 수집 API

### 4.1 수집 상태 조회
```
GET /api/collection/status
```

**응답:**
```json
{
  "success": true,
  "data": {
    "is_running": false,
    "last_run": "2026-01-15T02:00:00Z",
    "next_run": "2026-01-09T02:00:00Z",
    "last_result": "success"
  }
}
```

### 4.2 수집 이력 조회
```
GET /api/collection/history?page=1&per_page=20
```

### 4.3 수집 통계 조회
```
GET /api/collection/statistics
```

**응답:**
```json
{
  "success": true,
  "data": {
    "regtech": {"total": 150, "success": 148, "failed": 2},
    "urlhaus": {"total": 720, "success": 720, "failed": 0}
  }
}
```

### 4.4 REGTECH 수집 트리거
```
POST /api/collection/regtech/trigger
```

**요청 본문:**
```json
{
  "start_date": "2026-01-01",
  "end_date": "2026-01-15"
}
```

### 4.5 소스별 수집 트리거
```
POST /api/collection/{source}/trigger
```

**요청 본문:**
```json
{
  "force": true
}
```

### 4.6 스케줄러 상태 조회
```
GET /api/scheduler/status
```

### 4.7 스케줄러 재시작
```
POST /api/scheduler/restart
```

### 4.8 Secudium 수동 수집 트리거
```
POST /api/collection/trigger/secudium
```

**요청 본문:**
```json
{
  "force": true
}
```

---

## 5. Fortinet 연동 API

### 5.1 활성 IP 조회
```
GET /api/fortinet/active-ips
```

### 5.2 Pull 로그 조회
```
GET /api/fortinet/pull-logs?page=1&per_page=50
```

**응답:**
```json
{
  "items": [
    {
      "id": 1,
      "device_ip": "10.0.0.1",
      "request_time": "2026-01-15T06:30:00Z",
      "ip_count": 150,
      "status": "success"
    }
  ],
  "total": 1440
}
```

### 5.3 블록리스트 조회
```
GET /api/fortinet/blocklist?format=json
```

**파라미터:**
| 이름 | 타입 | 필수 | 설명 |
|------|------|------|------|
| format | string | N | 출력 형식 (json, text) |

---

## 6. 인증정보 관리 API

### 6.1 인증정보 조회
```
GET /api/collection/credentials/{source}
```

**응답:**
```json
{
  "success": true,
  "data": {
    "service_name": "regtech",
    "username": "admin",
    "password": "********",
    "last_updated": "2026-01-01T00:00:00Z"
  }
}
```

### 6.2 인증정보 수정
```
PUT /api/collection/credentials/{source}
```

**요청 본문:**
```json
{
  "username": "new_user",
  "password": "new_password"
}
```

### 6.3 인증정보 테스트
```
POST /api/collection/credentials/{source}/test
```

**응답:**
```json
{
  "success": true,
  "data": {
    "valid": true,
    "message": "Authentication successful"
  }
}
```

### 6.4 REGTECH 상태 조회
```
GET /api/credentials/regtech
```

---

## 7. 데이터베이스 API

### 7.1 테이블 목록 조회
```
GET /api/database/tables
```

### 7.2 스키마 조회
```
GET /api/database/schema
```

### 7.3 테이블 데이터 조회
```
GET /api/database/table/{name}?page=1&per_page=50
```

---

## 8. 시스템 API

### 8.1 헬스체크
```
GET /health
```

**응답:**
```json
{
  "status": "healthy",
  "version": "3.6.7",
  "timestamp": "2026-01-15T06:40:00Z"
}
```

### 8.2 메트릭 조회
```
GET /api/monitoring/metrics
```

### 8.3 시스템 설정 조회
```
GET /api/settings
```

### 8.4 시스템 설정 수정
```
PUT /api/settings
```

**요청 본문:**
```json
{
  "key": "setting_name",
  "value": "new_value"
}
```

---

## 9. Collector Service API (Port 8545)

### 9.1 헬스체크
```
GET /health
```

### 9.2 상세 상태
```
GET /status
```

### 9.3 수동 수집
```
POST /collect
```

### 9.4 Prometheus 메트릭
```
GET /metrics
```

### 9.5 설정 조회
```
GET /config
```

### 9.6 성능 정보
```
GET /api/enhanced/performance
```

### 9.7 소스 정보
```
GET /api/enhanced/sources
```

---

## 10. API 요약

| 도메인 | 엔드포인트 수 | 주요 파일 ||--------|--------------|----------|| 대시보드 | ~15 | dashboard_api.py || IP 관리 | ~40 | ip_management_api.py || 수집 | ~35 | collection/ || Fortinet | ~25 | fortinet/ || 인증정보 | ~15 | credentials_api.py || DB | ~10 | database_api.py || 시스템 | ~10 | 루트 레벨 || Collector | ~65 | collector/ || **합계** | **~215** | 55개 라우트 파일, 37개 Blueprint |

---

## 11. 변경 이력

| 버전 | 일자 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 1.0 | 2026-01-15 | Sisyphus | 초기 작성 |
| 2.0 | 2026-02-27 | Sisyphus | v3.6.7 현행화, 엔드포인트 수 갱신 (~215개), Secudium 수집 트리거 및 Settings CRUD 엔드포인트 추가 |

