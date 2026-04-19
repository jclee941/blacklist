# Environment Matrix - 환경별 설정 매트릭스

**버전:** 3.6.9  
**최종수정:** 2026-02-27

---

## 1. 환경 개요

| 환경 | 용도 | 접근 |
|------|------|------|
| **Development** | 로컬 개발 | localhost |
| **Staging** | 통합 테스트 | 내부망 |
| **Production** | 운영 | 내부망 |

---

## 2. 서비스 URL/포트

| 서비스 | Development | Staging | Production |
|--------|-------------|---------|------------|
| **Frontend** | http://localhost:3000 | https://stg-blacklist:3000 | https://blacklist:443 |
| **API** | http://localhost:2542 | https://stg-blacklist:2542 | https://blacklist:2542 |
| **Collector Health** | http://localhost:8545 | http://stg-collector:8545 | http://collector:8545 |
| **PostgreSQL** | localhost:5432 | stg-db:5432 | db-cluster:5432 |
| **Redis** | localhost:6379 | stg-redis:6379 | redis-cluster:6379 |

---

## 3. 환경변수

### 3.1 공통 환경변수

| 변수 | 설명 | 필수 |
|------|------|------|
| `DATABASE_URL` | PostgreSQL 연결 문자열 | ✅ |
| `REDIS_URL` | Redis 연결 문자열 | ✅ |
| `SECRET_KEY` | Flask 시크릿 키 | ✅ |
| `ENCRYPTION_KEY` | 자격증명 암호화 키 | ✅ |
| `CREDENTIAL_MASTER_KEY` | DB 자격증명 암호화 마스터 키 | ✅ |
| `DISABLE_JWT_AUTH` | JWT 인증 비활성화 (개발용, true/false) | ❌ |

### 3.2 환경별 값

| 변수 | Development | Staging | Production |
|------|-------------|---------|------------|
| `FLASK_ENV` | development | staging | production |
| `FLASK_DEBUG` | 1 | 0 | 0 |
| `LOG_LEVEL` | DEBUG | INFO | WARNING |
| `DATABASE_URL` | postgresql://... (로컬) | (스테이징 DB) | (운영 DB) |
| `REDIS_URL` | redis://localhost:6379 | (스테이징 Redis) | (운영 Redis) |

### 3.3 Frontend 환경변수

| 변수 | Development | Staging | Production |
|------|-------------|---------|------------|
| `NEXT_PUBLIC_API_URL` | http://localhost:2542 | /api (proxy) | /api (proxy) |
| `NODE_ENV` | development | production | production |

---

## 4. Docker Compose 파일

| 환경 | 파일 | 명령 |
|------|------|------|
| 개발 | `deploy/docker-compose.yml` | `make dev` |
| 운영/릴리즈 | `deploy/docker-compose.release.yml` | `docker compose -f deploy/docker-compose.release.yml up` |
| CI | `.github/docker-compose.ci.yml` | `docker compose -f .github/docker-compose.ci.yml up` |

---

## 5. 데이터베이스

### 5.1 연결 정보

| 항목 | Development | Staging | Production |
|------|-------------|---------|------------|
| Host | localhost | stg-db | db-cluster |
| Port | 5432 | 5432 | 5432 |
| Database | blacklist_dev | blacklist_stg | blacklist |
| User | blacklist | blacklist | blacklist |
| SSL | 비활성 | 활성 | 활성 |
| Pool Size | 5 | 10 | 20 |

### 5.2 초기화

```bash
# Development
make db-init

# Staging/Production
./scripts/migrate.sh
```

---

## 6. 로깅

| 항목 | Development | Staging | Production |
|------|-------------|---------|------------|
| Level | DEBUG | INFO | WARNING |
| Format | Console (색상) | JSON | JSON |
| 보관기간 | - | 30일 | 90일 |
| 위치 | stdout | /var/log/blacklist/ | /var/log/blacklist/ |

---

## 7. 보안 설정

| 항목 | Development | Staging | Production |
|------|-------------|---------|------------|
| HTTPS | 비활성 | 활성 | 활성 |
| CORS | * (전체 허용) | 특정 도메인 | 특정 도메인 |
| Rate Limit | 비활성 | 100 req/min | 100 req/min |
| JWT 만료 | 24h | 8h | 8h |

---

## 8. 외부 연동

### 8.1 수집 소스

| 소스 | Development | Staging | Production |
|------|-------------|---------|------------|
| REGTECH API | Mock 서버 | 테스트 API | 운영 API |
| Multi-Source | 일부 활성 | 전체 활성 | 전체 활성 |

### 8.2 FortiGate

| 항목 | Development | Staging | Production |
|------|-------------|---------|------------|
| 연동 | Mock | 테스트 장비 | 운영 장비 |
| 동기화 | 수동 | 수동 | 자동 (5분) |

---

## 9. 컨테이너 리소스

| 서비스 | Development | Staging | Production |
|--------|-------------|---------|------------|
| **API** | 제한 없음 | 1 CPU, 1GB | 2 CPU, 2GB |
| **Frontend** | 제한 없음 | 0.5 CPU, 512MB | 1 CPU, 1GB |
| **Collector** | 제한 없음 | 1 CPU, 1GB | 2 CPU, 2GB |
| **PostgreSQL** | 제한 없음 | 2 CPU, 2GB | 4 CPU, 8GB |
| **Redis** | 제한 없음 | 0.5 CPU, 512MB | 1 CPU, 2GB |

---

## 10. 배포 프로세스

| 단계 | Development | Staging | Production |
|------|-------------|---------|------------|
| 트리거 | 수동 | Push to develop | Tag v*.*.* |
| 테스트 | 로컬 | CI 자동 | CI 자동 |
| 승인 | 불필요 | 불필요 | 필요 |
| 롤백 | Git checkout | 자동 | 수동 |

---

## 11. 모니터링

| 항목 | Development | Staging | Production |
|------|-------------|---------|------------|
| Health Check | 수동 | 자동 (30s) | 자동 (30s) |
| 메트릭 | 비활성 | Prometheus | Prometheus |
| 알림 | 없음 | 이메일 | 이메일 + 메신저 |

---

## 12. 백업

| 항목 | Development | Staging | Production |
|------|-------------|---------|------------|
| 자동 백업 | 비활성 | 일 1회 | 일 1회 |
| 보관 기간 | - | 7일 | 30일 |
| 복구 테스트 | - | 월 1회 | 월 1회 |
---

## 13. 변경 이력

| 버전 | 일자 | 변경 내용 |
|------|------|-----------|
| 3.5.11 | 2026-01-10 | 초안 작성 |
| 3.6.9 | 2026-02-27 | 버전 현행화: Frontend URL 업데이트 (2543→3000/443), Docker Compose 파일 경로 갱신, 환경변수 추가 (CREDENTIAL_MASTER_KEY, DISABLE_JWT_AUTH), FortiGate 동기화 간격 5분 단축 |
