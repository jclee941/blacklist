# 설치 가이드 (Installation Guide)

**프로젝트명:** REGTECH 블랙리스트 인텔리전스 플랫폼  
**버전:** 3.6.9
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
├── images/
│   ├── app.tar.gz
│   ├── collector.tar.gz
│   ├── frontend.tar.gz
│   ├── postgres.tar.gz
│   └── redis.tar.gz
├── docker-compose.yml
├── base.yml
└── install.sh
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
# 첫 설치: 대상 서버에서 리터럴 키 값을 생성하고 검증
chmod +x install.sh
./install.sh --check-secrets
```

첫 설치에서만 설치기가 대상 서버의 `.env`에 필수 키와 비밀번호를 생성하고 권한을 `0600`으로
설정합니다. `CREDENTIAL_MASTER_KEY`에는 생성된 리터럴 키 값이 들어가야 합니다. 파일 경로,
변수 표현식, 자리표시자, 빈 값은 넣지 마세요. 기존 `.env`가 있으면 설치기는 값을 다시 만들지
않으며, 유효하지 않은 값이 하나라도 있으면 설치를 중단합니다.

설치기가 생성한 `ADMIN_USERNAME`과 `ADMIN_PASSWORD`로 웹 UI에 처음 로그인합니다. 이 값도
`.env`에 보존하며, 문서나 화면에 자격증명 값을 기록하지 않습니다.

업그레이드에서는 기존 배포 디렉터리의 `.env`를 먼저 백업한 뒤 새 번들 디렉터리에 복사하고
검증합니다. 기존 암호화 키와 `ADMIN_USERNAME`, `ADMIN_PASSWORD`를 유지해야 저장된 인증정보와
관리자 로그인 흐름을 보존할 수 있습니다.

```bash
# 업그레이드: 이전 .env를 새 번들에 전달
cp -p /path/to/previous/blacklist/.env /opt/blacklist/.env
cd /opt/blacklist
./install.sh --check-secrets
```

#### Step 3: 배포 실행
```bash
cd /opt/blacklist

# Air-Gap 모드로 배포
./install.sh
```

**스크립트 실행 과정:**
1. Docker 이미지 로드 (`docker load`)
2. 네트워크 생성
3. 컨테이너 시작
4. 헬스체크 수행

#### Step 4: 설치 확인
```bash
# 컨테이너 상태 확인
docker compose ps

# 헬스체크
curl http://localhost:2542/health

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
# 첫 설치: 대상 서버에서 필수 키와 비밀번호 생성
chmod +x deploy/install.sh
./deploy/install.sh --check-secrets
nano deploy/.env  # WARP 프록시 설정 추가

# NAS 모드로 배포
./deploy/install.sh
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

1. `https://localhost`에서 `.env`의 생성된 관리자 계정으로 로그인
2. `https://localhost/collection`에서 REGTECH 카드의 **인증정보 설정** 선택
3. REGTECH 계정 정보, 수집 간격, 활성화 여부 입력 후 **설정 및 저장** 선택
4. **연결 테스트**가 성공한 것을 확인한 뒤 **수집** 실행

저장된 REGTECH 비밀번호는 화면에서 다시 표시되지 않습니다. 인증정보를 다시 설정해야 할 때는
같은 화면에서 새 값을 저장합니다.

### 7.3 첫 수집 실행

관리자 로그인 후 수집 관리 화면에서 REGTECH **수집**을 선택합니다. 완료 후 최근 실행 시각과
수집 건수가 갱신됐는지 확인합니다.

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
| API 헬스 | `curl localhost:2542/health` | `{"status":"healthy"}` |
| Frontend 접근 | 브라우저 접속 | 대시보드 표시 |
| DB 연결 | 관리자 로그인 후 대시보드 확인 | 통계 표시 |
| Collector | `curl localhost:8545/status` | 서비스 정보 |

---

## 10. 변경 이력

| 버전 | 일자 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 3.6.9 | 2026-02-27 | Sisyphus | Traefik 제거, Frontend 직접 SSL 지원, 컨테이너 이름 변경 (blacklist-api→blacklist-app, blacklist-db→blacklist-postgres), Docker Compose 경로 변경 (deploy/docker-compose.yml) |
| 1.0 | 2026-01-15 | Sisyphus | 초기 작성 |
