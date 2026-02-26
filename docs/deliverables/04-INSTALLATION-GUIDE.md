# 설치 가이드 (Installation Guide)

**프로젝트명:** REGTECH 블랙리스트 인텔리전스 플랫폼  
**버전:** 3.6.7
**작성일:** 2026-02-27
**문서번호:** INS-REGTECH-2026-001

---

## 1. 개요

### 1.1 문서 목적
본 문서는 REGTECH 블랙리스트 인텔리전스 플랫폼의 설치 및 구성 절차를 설명합니다.

### 1.2 대상 독자
- 시스템 관리자
- DevOps 엔지니어
- 인프라 담당자

### 1.3 배포 모드

| 모드 | 설명 | 네트워크 요구사항 |
|------|------|------------------|
| **Air-Gap** | 폐쇄망 오프라인 배포 | 없음 |
| **NAS** | WARP 프록시 환경 | 프록시 접근 |
| **Dev** | 로컬 개발 환경 | 인터넷 |

---

## 2. 시스템 요구사항

### 2.1 하드웨어

| 구분 | 최소 사양 | 권장 사양 |
|------|----------|----------|
| CPU | 4 Core | 8 Core |
| RAM | 8 GB | 16 GB |
| 디스크 | 50 GB SSD | 100 GB SSD |
| 네트워크 | 100 Mbps | 1 Gbps |

### 2.2 소프트웨어

| 소프트웨어 | 버전 | 비고 |
|-----------|------|------|
| Docker | 24.0+ | 필수 |
| Docker Compose | v2.0+ | 필수 |
| Git | 2.30+ | LFS 지원 필요 |
| Git LFS | 3.0+ | Air-Gap 이미지 관리 |

### 2.3 포트 요구사항

| 포트 | 서비스 | 외부 노출 |
|------|--------|----------|
| 2542 | Flask API | No (내부) |
| 443 | Next.js Frontend (직접 SSL) | Yes |
| 5432 | PostgreSQL | No (내부) |
| 6379 | Redis | No (내부) |
| 8545 | Collector | No (내부) |

---

## 3. Air-Gap 배포 (폐쇄망)

### 3.1 사전 준비

#### 3.1.1 패키지 획득
인터넷이 연결된 환경에서 Air-Gap 패키지를 다운로드합니다:

```bash
# GitLab에서 airgap 브랜치 클론
git clone -b airgap https://github.com/qws941/blacklist.git
cd blacklist

# LFS 파일 다운로드
git lfs install
git lfs pull
```

#### 3.1.2 패키지 전송
USB 또는 내부 네트워크를 통해 폐쇄망 서버로 전송합니다:
```
blacklist/
├── dist/
│   └── images/
│       ├── blacklist-app.tar.gz       (~200MB)
│       ├── blacklist-frontend.tar.gz  (~150MB)
│       ├── blacklist-collector.tar.gz (~180MB)
│       ├── blacklist-postgres.tar.gz  (~200MB)
│       └── blacklist-redis.tar.gz     (~50MB)
├── scripts/
│   └── deploy-airgap.sh
├── docker-compose.yml
└── .env.example
```

### 3.2 설치 절차

#### Step 1: 디렉토리 설정
```bash
# 설치 디렉토리 생성
sudo mkdir -p /opt/blacklist
sudo chown $USER:$USER /opt/blacklist

# 패키지 복사
cp -r blacklist/* /opt/blacklist/
cd /opt/blacklist
```

#### Step 2: 환경 설정
```bash
# 환경 파일 생성
cp .env.example .env

# 필수 설정 수정
nano .env
```

**.env 필수 설정:**
```bash
# 데이터베이스
POSTGRES_USER=blacklist
POSTGRES_PASSWORD=<강력한_비밀번호>
POSTGRES_DB=blacklist

# Redis
REDIS_URL=redis://blacklist-redis:6379/0

# 암호화 키 경로
CREDENTIAL_MASTER_KEY=/opt/blacklist/keys/CREDENTIAL_MASTER_KEY.txt

# 환경
FLASK_ENV=production
```

#### Step 3: 마스터 키 생성
```bash
# 키 디렉토리 생성
mkdir -p /opt/blacklist/keys

# 마스터 키 생성 (한 번만)
openssl rand -base64 32 > /opt/blacklist/keys/CREDENTIAL_MASTER_KEY.txt
chmod 600 /opt/blacklist/keys/CREDENTIAL_MASTER_KEY.txt
```

#### Step 4: 배포 실행
```bash
cd /opt/blacklist/scripts
chmod +x deploy-airgap.sh

# Air-Gap 모드로 배포
./deploy-airgap.sh airgap
```

**스크립트 실행 과정:**
1. Docker 이미지 로드 (`docker load`)
2. 네트워크 생성
3. 컨테이너 시작
4. 헬스체크 수행

#### Step 5: 설치 확인
```bash
# 컨테이너 상태 확인
docker compose ps

# 헬스체크
curl http://localhost/health

# 로그 확인
docker compose logs -f
```

---

## 4. NAS 배포 (프록시 환경)

### 4.1 사전 준비
```bash
# 리포지토리 클론
git clone https://github.com/qws941/blacklist.git
cd blacklist
```

### 4.2 설치 절차

```bash
# 환경 설정
cp .env.example .env
nano .env  # WARP 프록시 설정 추가

# NAS 모드로 배포
cd scripts
./deploy-airgap.sh nas
```

---

## 5. 개발 환경 배포

### 5.1 빠른 시작
```bash
# 리포지토리 클론
git clone https://github.com/qws941/blacklist.git
cd blacklist

# 전체 스택 시작 (핫 리로드)
make dev
```

### 5.2 개별 서비스 실행
```bash
# 인프라만 시작
make infra

# 백엔드 개발 서버
cd app && python run_app.py

# 프론트엔드 개발 서버
cd frontend && npm run dev

# Collector 서비스
cd collector && python -m collector.run_collector
```

---

## 6. SSL 인증서 설정

### 6.1 기본 SSL
Frontend 컨테이너에는 자체 서명 SSL 인증서가 기본으로 내장되어 있습니다. 별도의 SSL 설정 없이도 HTTPS로 서비스됩니다.

### 6.2 운영 환경 인증서 교체 (선택)
운영 환경에서는 자체 인증서로 교체할 수 있습니다:

```bash
# 인증서 디렉토리 생성
mkdir -p /opt/blacklist/ssl-certs

# 인증서 파일 복사
cp your-cert.pem /opt/blacklist/ssl-certs/cert.pem
cp your-key.pem /opt/blacklist/ssl-certs/key.pem

# 권한 설정
chmod 644 /opt/blacklist/ssl-certs/cert.pem
chmod 600 /opt/blacklist/ssl-certs/key.pem
```

`deploy/docker-compose.release.yml`의 ssl-certs 볼륨을 통해 인증서가 컨테이너에 마운트됩니다.
---

## 7. 초기 설정

### 7.1 데이터베이스 마이그레이션
```bash
# 마이그레이션 자동 실행 (컨테이너 시작 시)
docker compose exec blacklist-postgres psql -U blacklist -f /docker-entrypoint-initdb.d/000_init_complete_schema.sql
```

### 7.2 인증정보 설정
첫 번째 실행 후 웹 UI에서 인증정보를 설정합니다:

1. `https://localhost/settings` 접속
2. **인증정보 설정** 메뉴 선택
3. REGTECH/Secudium 계정 정보 입력
4. **연결 테스트** 클릭

**참고:** 마스터 키는 환경 변수로도 설정 가능합니다. `CREDENTIAL_MASTER_KEY` 환경 변수를 설정하면 파일 경로 대신 해당 키 값이 사용됩니다.

### 7.3 첫 수집 실행
```bash
# 수동 수집 트리거
curl -X POST https://localhost/api/collection/regtech/trigger \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2026-01-01", "end_date": "2026-01-15"}'
```

---

## 8. 문제 해결

### 8.1 이미지 로드 실패
```bash
# LFS 파일 재다운로드
git lfs pull --all

# 이미지 파일 확인
ls -la dist/images/
```

### 8.2 데이터베이스 연결 실패
```bash
# PostgreSQL 로그 확인
docker compose logs blacklist-postgres

# 연결 테스트
docker compose exec blacklist-postgres psql -U blacklist -c '\l'
```

### 8.3 Collector 실행 안됨
```bash
# Collector 상태 확인
curl http://localhost:8545/status

# 로그 확인
docker compose logs -f blacklist-collector
```

### 8.4 포트 충돌
```bash
# 사용 중인 포트 확인
sudo lsof -i :80
sudo lsof -i :443

# 기존 프로세스 종료 후 재시작
docker compose down
docker compose up -d
```

---

## 9. 설치 검증 체크리스트

| 항목 | 확인 명령 | 예상 결과 |
|------|----------|----------|
| 컨테이너 상태 | `docker compose ps` | 모든 서비스 "Up" |
| API 헬스 | `curl localhost/health` | `{"status":"healthy"}` |
| Frontend 접근 | 브라우저 접속 | 대시보드 표시 |
| DB 연결 | `curl localhost/api/dashboard/stats` | JSON 응답 |
| Collector | `curl localhost:8545/status` | 서비스 정보 |

---

## 10. 변경 이력

| 버전 | 일자 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 3.6.7 | 2026-02-27 | Sisyphus | Traefik 제거, Frontend 직접 SSL 지원, 컨테이너 이름 변경 (blacklist-api→blacklist-app, blacklist-db→blacklist-postgres), Docker Compose 경로 변경 (deploy/docker-compose.yml) |
| 1.0 | 2026-01-15 | Sisyphus | 초기 작성 |

