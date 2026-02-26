# Runbook - 운영 플레이북

**버전:** 3.6.7
**최종수정:** 2026-02-27

---

## 1. 서비스 시작/중지

### 1.1 전체 서비스 시작

```bash
make dev
```

### 1.2 개별 서비스 시작

```bash
make dev-app        # API Server만
make dev-frontend   # Dashboard만
docker compose -f deploy/docker-compose.yml up -d blacklist-collector  # Collector만
```

### 1.3 서비스 중지

```bash
docker compose down
```

---

## 2. 장애 대응 플레이북

### 2.1 API 서버 무응답

| 단계 | 확인/조치 |
|------|-----------|
| **증상** | Dashboard에서 API 호출 실패, 504 Gateway Timeout |
| **확인 1** | `docker ps \| grep blacklist-app` |
| **확인 2** | `docker logs blacklist-app --tail 100` |
| **원인 A** | 컨테이너 비정상 종료 → `docker compose restart api` |
| **원인 B** | DB 연결 실패 → DB 상태 확인 (섹션 2.2) |
| **원인 C** | 메모리 부족 → `docker stats` 확인, 컨테이너 재시작 |
| **검증** | `curl http://localhost:2542/api/system/health` |

### 2.2 PostgreSQL 연결 실패

| 단계 | 확인/조치 |
|------|-----------|
| **증상** | API 로그에 "connection refused" 또는 "timeout" |
| **확인 1** | `docker ps \| grep postgres` |
| **확인 2** | `docker exec blacklist-postgres pg_isready` |
| **원인 A** | DB 컨테이너 중지 → `docker compose restart db` |
| **원인 B** | 커넥션 풀 고갈 → API 재시작 |
| **원인 C** | 디스크 풀 → `docker system df` 확인 |
| **검증** | `docker exec blacklist-postgres psql -U blacklist -c "SELECT 1"` |

### 2.3 Redis 연결 실패

| 단계 | 확인/조치 |
|------|-----------|
| **증상** | 캐시 미스 급증, 세션 유실 |
| **확인 1** | `docker ps \| grep redis` |
| **확인 2** | `docker exec blacklist-redis redis-cli ping` |
| **원인 A** | Redis 컨테이너 중지 → `docker compose restart redis` |
| **원인 B** | 메모리 초과 → `docker exec blacklist-redis redis-cli info memory` |
| **검증** | `docker exec blacklist-redis redis-cli ping` → PONG |

### 2.4 수집 실패

| 단계 | 확인/조치 |
|------|-----------|
| **증상** | 대시보드에서 "수집 실패" 표시, 데이터 갱신 안됨 |
| **확인 1** | `docker logs blacklist-collector --tail 100` |
| **확인 2** | Dashboard > Collection > Logs 확인 |
| **원인 A** | 네트워크 오류 → 외부 연결 확인, 재시도 대기 |
| **원인 B** | 자격증명 만료 → Dashboard > Credentials에서 갱신 |
| **원인 C** | 소스 API 변경 → 로그 확인 후 코드 수정 필요 |
| **검증** | Dashboard에서 수동 수집 트리거 후 상태 확인 |

### 2.5 FortiGate 동기화 실패

| 단계 | 확인/조치 |
|------|-----------|
| **증상** | 동기화 상태 "failed", FortiGate에 정책 미반영 |
| **확인 1** | API 로그에서 FortiGate 관련 에러 확인 |
| **확인 2** | FortiGate 장비 연결 상태 확인 |
| **원인 A** | 자격증명 오류 → Credentials 재설정 |
| **원인 B** | 네트워크 단절 → 방화벽/라우팅 확인 |
| **원인 C** | FortiGate API 제한 → 재시도 간격 조정 |
| **검증** | Dashboard에서 동기화 재실행 |

---

## 3. 정기 점검 항목

### 3.1 일일 점검

| 항목 | 확인 방법 | 정상 기준 |
|------|-----------|-----------|
| 서비스 상태 | `docker ps` | 모든 컨테이너 Up |
| 헬스체크 | `curl localhost:2542/api/system/health` | status: healthy |
| 수집 상태 | Dashboard > Collection | 마지막 성공 < 24시간 |
| 디스크 사용량 | `df -h` | 사용률 < 80% |

### 3.2 주간 점검

| 항목 | 확인 방법 | 조치 |
|------|-----------|------|
| 로그 용량 | `du -sh /var/log/blacklist/` | 필요시 로테이션 |
| DB 크기 | Dashboard > System > Stats | 비정상 증가시 확인 |
| 백업 상태 | 백업 로그 확인 | 실패시 수동 백업 |

### 3.3 월간 점검

| 항목 | 확인 방법 | 조치 |
|------|-----------|------|
| 보안 패치 | `docker images` 버전 확인 | 취약점 발견시 업데이트 |
| 인증서 만료 | TLS 인증서 확인 | 만료 30일 전 갱신 |
| 백업 복구 테스트 | 스테이징에서 복구 테스트 | 연 1회 이상 |

---

## 4. 백업 및 복구

### 4.1 수동 백업

```bash
./scripts/backup-database.sh
```

### 4.2 복구

```bash
./scripts/restore-database.sh backup_20260110.sql.gz
```

### 4.3 백업 파일 위치

```
/var/backups/blacklist/
├── db_backup_20260110_120000.sql.gz
├── db_backup_20260109_120000.sql.gz
└── ...
```

---

## 5. 로그 확인

### 5.1 실시간 로그

```bash
docker logs -f blacklist-app
docker logs -f blacklist-frontend
docker logs -f blacklist-collector
```

### 5.2 에러 로그 필터링

```bash
docker logs blacklist-app 2>&1 | grep -i error
docker logs blacklist-collector 2>&1 | grep -i "failed\|error"
```

### 5.3 로그 위치

| 서비스 | 컨테이너 내부 | 호스트 마운트 |
|--------|--------------|---------------|
| API | `/app/logs/` | `./logs/api/` |
| Collector | `/app/logs/` | `./logs/collector/` |
| PostgreSQL | stdout | Docker logs |
| Redis | stdout | Docker logs |

---

## 6. 긴급 연락처

| 역할 | 담당 | 연락처 |
|------|------|--------|
| 시스템 관리자 | - | - |
| DB 관리자 | - | - |
| 네트워크 관리자 | - | - |

---

## 7. 자주 묻는 질문 (FAQ)

### Q1: 수집 데이터가 갱신되지 않아요
**A:** Collector 로그 확인 → 자격증명 확인 → 수동 수집 트리거

### Q2: Dashboard 로딩이 느려요
**A:** Redis 상태 확인 → 브라우저 캐시 클리어 → API 응답 시간 확인

### Q3: IP를 등록했는데 FortiGate에 반영이 안돼요
**A:** 동기화 상태 확인 → 수동 동기화 실행 → FortiGate 연결 상태 확인

### Q4: 컨테이너가 자꾸 재시작해요
**A:** `docker logs` 확인 → 메모리/디스크 확인 → OOM Killer 여부 확인

---

## 8. 변경 이력

| 버전 | 일자 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 3.6.7 | 2026-02-27 | Sisyphus | Traefik 제거, 컨테이너 이름 변경 (blacklist-api→blacklist-app, blacklist-db→blacklist-postgres), Docker Compose 경로 변경 (deploy/docker-compose.yml) |
| 1.0 | 2026-01-10 | Sisyphus | 초기 작성 |
