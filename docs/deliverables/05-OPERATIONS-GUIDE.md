# 운영 매뉴얼 (Operations Manual)

**프로젝트명:** REGTECH 블랙리스트 인텔리전스 플랫폼  
**버전:** 3.6.9
**작성일:** 2026-02-27
**문서번호:** OPS-REGTECH-2026-001

---

## 1. 개요

### 1.1 문서 목적
본 문서는 REGTECH 블랙리스트 인텔리전스 플랫폼의 일상 운영, 모니터링, 장애 대응 절차를 설명합니다.

### 1.2 시스템 구성

| 서비스 | 포트 | 역할 |
|--------|------|------|
| Frontend | 443 | 웹 대시보드 (직접 SSL) |
| API | 2542 | REST API |
| Collector | 8545 | 데이터 수집 |
| PostgreSQL | 5432 | 데이터 저장 |
| Redis | 6379 | 캐시, Rate Limit |

---

## 2. 일상 운영

### 2.1 서비스 관리

#### 서비스 시작
```bash
cd /opt/blacklist
docker compose up -d
```

#### 서비스 중지
```bash
docker compose down
```

#### 서비스 재시작
```bash
docker compose restart
# 또는 특정 서비스만
docker compose restart blacklist-app
```

#### 상태 확인
```bash
docker compose ps
docker compose logs -f
```

### 2.2 헬스체크

#### API 헬스체크
```bash
curl https://localhost/health
```

**정상 응답:**
```json
{
  "status": "healthy",
  "version": "3.6.9"
}
```

#### Collector 헬스체크
```bash
curl http://localhost:8545/status
```

#### 전체 시스템 상태
```bash
curl https://localhost/api/dashboard/status
```

### 2.3 로그 관리

#### 로그 조회
```bash
# 전체 로그
docker compose logs -f

# 특정 서비스 로그
docker compose logs -f blacklist-app
docker compose logs -f blacklist-collector

# 최근 100줄
docker compose logs --tail=100 blacklist-app
```

#### 로그 파일 위치
```
/var/lib/docker/containers/<container-id>/<container-id>-json.log
```

### 2.4 수집 스케줄

| 소스 | 주기 | 시간 |
|------|------|------|
| REGTECH | 매일 | 02:00 |
| URLHaus | 매시간 | :00 |
| ThreatFox | 매시간 | :15 |
| Feodo Tracker | 매시간 | :30 |
| PhishTank | 6시간 | 00:00, 06:00, 12:00, 18:00 |
| FortiGate Sync | 5분 | - |

---

## 3. 모니터링

### 3.1 주요 지표

| 지표 | 정상 범위 | 확인 방법 |
|------|----------|----------|
| API 응답시간 | < 500ms | Prometheus |
| 메모리 사용률 | < 80% | `docker stats` |
| 디스크 사용률 | < 85% | `df -h` |
| DB 연결 수 | < 100 | PostgreSQL logs |
| 수집 성공률 | > 95% | `/api/collection/statistics` |

### 3.2 Docker 리소스 모니터링
```bash
docker stats --no-stream
```

### 3.3 디스크 사용량
```bash
# 전체 디스크
df -h

# Docker 볼륨
docker system df
```

### 3.4 Prometheus 메트릭
```bash
curl http://localhost:8545/metrics
```

**주요 메트릭:**
- `collector_total_runs`: 총 수집 횟수
- `collector_successful_runs`: 성공 횟수
- `collector_failed_runs`: 실패 횟수
- `collector_total_ips`: 총 IP 개수

### 3.5 Prometheus + Grafana 모니터링
별도의 모니터링 스택을 통해 시스템 지표를 시각화할 수 있습니다:

```bash
# 모니터링 스택 시작
docker compose -f deploy/docker-compose.monitoring.yml up -d
```

**서비스:**
- Prometheus (port 9090): 메트릭 수집 및 저장
- Grafana (port 3000): 시각화 대시보드

**기본 접근:** admin/admin (첫 로그인 후 변경 필요)

### 3.6 Watchtower 자동 업데이트
Watchtower 컨테이너가 Docker Hub의 이미지 변경을 감지하여 자동으로 서비스를 업데이트합니다.

```bash
# 상태 확인
docker ps | grep watchtower

# 수동 업데이트 트리거
docker run --rm --name watchtower \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower --run-once
```

**참고:** 프로덕션 환경에서는 자동 업데이트 대신 수동 검증 후 배포를 권장합니다.
---

## 4. 백업 및 복구

### 4.1 데이터베이스 백업

#### 수동 백업
```bash
cd /opt/blacklist/scripts
./backup-database.sh
```

#### 백업 파일 위치
```
/opt/blacklist/backups/blacklist_backup_YYYYMMDD_HHMMSS.sql.gz
```

#### 자동 백업 설정 (crontab)
```bash
# 매일 03:00 백업
0 3 * * * /opt/blacklist/scripts/backup-database.sh
```

### 4.2 데이터베이스 복구

```bash
# 백업 파일 압축 해제
gunzip blacklist_backup_20260108_030000.sql.gz

# 복구 실행
docker compose exec -T blacklist-postgres psql -U blacklist < blacklist_backup_20260108_030000.sql
```

### 4.3 설정 파일 백업
```bash
tar -czf config_backup.tar.gz \
  .env \
  docker-compose.yml \
  keys/CREDENTIAL_MASTER_KEY.txt
```

---

## 5. 장애 대응

### 5.1 장애 등급

| 등급 | 설명 | 대응 시간 |
|------|------|----------|
| Critical | 전체 서비스 중단 | 즉시 |
| Major | 핵심 기능 장애 | 30분 이내 |
| Minor | 부분 기능 장애 | 2시간 이내 |
| Low | 경미한 이슈 | 다음 영업일 |

### 5.2 장애 대응 절차

#### Step 1: 상태 확인
```bash
docker compose ps
docker compose logs --tail=50
```

#### Step 2: 서비스 재시작
```bash
docker compose restart <service-name>
```

#### Step 3: 전체 재시작 (필요시)
```bash
docker compose down
docker compose up -d
```

#### Step 4: 롤백 (필요시)
```bash
cd /opt/blacklist/scripts
./rollback.sh
```

### 5.3 일반적인 장애 상황

#### API 응답 없음
1. 컨테이너 상태 확인
2. 메모리 사용량 확인
3. 로그 확인 후 재시작

```bash
docker compose restart blacklist-app
```

#### 수집 실패
1. 인증정보 유효성 확인
2. 네트워크 연결 확인 (NAS 모드)
3. 로그 확인

```bash
docker compose logs blacklist-collector
curl http://localhost:8545/status
```

#### 데이터베이스 연결 실패
1. PostgreSQL 컨테이너 상태 확인
2. 연결 풀 상태 확인
3. 재시작

```bash
docker compose restart blacklist-postgres
docker compose restart blacklist-app
```

#### 디스크 공간 부족
1. 오래된 Docker 이미지 정리
2. 오래된 로그 삭제
3. 백업 파일 정리

```bash
docker system prune -f
find /opt/blacklist/backups -mtime +30 -delete
```

---

## 6. 보안 운영

### 6.1 인증정보 관리
- 마스터 키는 `/opt/blacklist/keys/` 외부 저장 금지
- 주기적 비밀번호 변경 (3개월)
- 인증정보 변경 시 연결 테스트 필수

### 6.2 접근 제어
- 관리자 계정만 웹 UI 접근
- SSH 접근은 지정된 IP만 허용
- 포트 80/443만 외부 노출

### 6.3 로그 감사
- 인증 시도 로그 주기적 검토
- 비정상 API 호출 패턴 모니터링
- 수집 실패 원인 분석

---

## 7. 업데이트 절차

### 7.1 버전 업데이트

#### Step 1: 백업
```bash
./scripts/backup-database.sh
```

#### Step 2: 새 버전 획득
```bash
git pull origin master
git lfs pull
```

#### Step 3: 서비스 중지
```bash
docker compose down
```

#### Step 4: 이미지 로드 (Air-Gap)
```bash
./scripts/deploy-airgap.sh airgap
```

#### Step 5: 마이그레이션 (필요시)
```bash
docker compose exec blacklist-postgres psql -U blacklist -f /migrations/VXXX__update.sql
```

#### Step 6: 검증
```bash
curl https://localhost/health
```

### 7.2 롤백 절차
```bash
# 이전 버전으로 체크아웃
git checkout v3.5.0

# 이미지 재로드
./scripts/deploy-airgap.sh airgap

# DB 복구 (필요시)
docker compose exec -T blacklist-postgres psql -U blacklist < backup.sql
```

---

## 8. 운영 체크리스트

### 8.1 일간 점검
- [ ] 시스템 헬스체크 확인
- [ ] 수집 성공 여부 확인
- [ ] 디스크 사용량 확인
- [ ] 오류 로그 검토

### 8.2 주간 점검
- [ ] 백업 파일 존재 확인
- [ ] 리소스 사용 추이 분석
- [ ] 보안 로그 검토
- [ ] 성능 지표 분석

### 8.3 월간 점검
- [ ] 오래된 백업 정리
- [ ] Docker 시스템 정리
- [ ] 인증정보 유효성 확인
- [ ] 용량 계획 검토

---

## 9. 연락처

| 역할 | 담당 | 연락처 |
|------|------|--------|
| 시스템 관리자 | - | - |
| 개발팀 | Nextrade | - |
| 보안 담당 | - | - |

---

## 10. 변경 이력

| 버전 | 일자 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 3.6.9 | 2026-02-27 | Sisyphus | Traefik 제거, Frontend 직접 SSL (포트 443), 컨테이너 이름 변경, Docker Compose 경로 변경 (deploy/docker-compose.yml), Prometheus+Grafana 모니터링 추가, Watchtower 자동 업데이트 설명 추가 |
| 1.0 | 2026-01-15 | Sisyphus | 초기 작성 |

