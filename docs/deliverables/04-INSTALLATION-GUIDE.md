---
title: "Nextrade Blacklist 오프라인 설치 및 운영 가이드"
subtitle: "폐쇄망 패키지 반입, 설치, 검증 및 장애 대응"
date: "버전 4.1.0 | 2026-07-28"
lang: ko-KR
---

## 1. 개요

### 1.1 문서 목적

본 문서는 인터넷 연결이 없는 폐쇄망 서버에 Nextrade Blacklist 오프라인 패키지를 설치하고 운영하는 절차를 설명합니다.

패키지에는 실행에 필요한 Docker 이미지, Compose 설정, checksum, 오프라인 설치 스크립트와 운영 문서가 포함됩니다. 대상 서버에서 소스 코드를 빌드하거나 외부 저장소에 접속할 필요가 없습니다.

### 1.2 대상 독자

- 시스템 관리자
- 보안 운영 담당자
- 인프라 및 배포 담당자

### 1.3 적용 범위

- 신규 폐쇄망 서버 설치
- 기존 버전 업그레이드와 롤백
- 서비스 기동, 중지 및 상태 확인
- REGTECH 데이터 수집 운영
- Cloudflare Lists API 연동
- 백업, 복구 및 장애 대응

> **중요:** 일반 설치를 실행하면 대상 서버에서 실행 중인 모든 Docker 컨테이너가 중지됩니다. Nextrade Blacklist 외 다른 컨테이너가 필요한 경우 설치 완료 후 승인된 운영 절차에 따라 별도로 기동해야 합니다.

---

## 2. 설치 전 준비

### 2.1 시스템 요구사항

| 구분 | 최소 기준 | 권장 기준 |
|---|---|---|
| CPU | 4 Core | 8 Core |
| RAM | 8GB | 16GB |
| 디스크 | 50GB SSD | 100GB SSD |
| 패키지 임시 공간 | 3GB 이상 | 5GB 이상 |
| 운영체제 | 패키지와 호환되는 Linux x86_64 | Linux x86_64 |

Docker Engine과 Docker Compose Plugin이 없으면 설치 스크립트가 패키지에 포함된 오프라인 실행 파일을 사용해 설치를 시도합니다. 시스템 서비스 설치와 Docker 실행이 가능한 관리자 권한이 필요합니다.

### 2.2 포트 요구사항

| 포트 | 서비스 | 외부 노출 |
|---|---|---|
| 443 | Frontend HTTPS | 운영자 접속에 필요 |
| 2542 | Application API | 서버 내부 |
| 5432 | PostgreSQL | 서버 내부 |
| 6379 | Redis | 서버 내부 |
| 8545 | Collector | 서버 내부 |

설치 전에 동일 포트를 사용하는 프로세스가 없는지 확인합니다.

```bash
sudo ss -lntp
```

### 2.3 패키지 반입

승인된 이동식 매체 또는 내부 파일 전송 절차로 아래 파일을 대상 서버에 반입합니다.

```text
blacklist-4.1.0.tar.gz
blacklist-4.1.0.tar.gz.sha256
```

패키지와 checksum 파일은 같은 디렉터리에 둡니다.

### 2.4 외부 패키지 무결성 확인

압축 해제 전에 SHA-256 값을 검증합니다.

```bash
sha256sum -c blacklist-4.1.0.tar.gz.sha256
```

정상 결과는 다음과 같습니다.

```text
blacklist-4.1.0.tar.gz: OK
```

검증이 실패하면 설치하지 말고 패키지를 다시 반입합니다.

### 2.5 패키지 구성

```text
blacklist-4.1.0/
├── VERSION
├── MANIFEST.sha256
├── RELEASE_NOTES.md
├── base.yml
├── docker-compose.yml
├── install.sh
├── docs/
│   └── blacklist-offline-deployment-guide.pdf
├── images/
│   ├── blacklist-app.tar.gz
│   ├── blacklist-collector.tar.gz
│   ├── blacklist-frontend.tar.gz
│   ├── blacklist-postgres.tar.gz
│   ├── blacklist-redis.tar.gz
│   └── checksums.sha256
└── prereqs/
    ├── docker-29.2.1.tgz
    ├── docker-compose-linux-x86_64
    └── docker.service
```

---

## 3. 신규 설치

### 3.1 패키지 압축 해제

```bash
sudo mkdir -p /opt/blacklist
sudo tar -xzf blacklist-4.1.0.tar.gz \
  -C /opt/blacklist --strip-components=1
cd /opt/blacklist
```

### 3.2 내부 파일 무결성 확인

```bash
sha256sum -c MANIFEST.sha256
```

모든 파일이 `OK`로 표시되어야 합니다. 설치 스크립트는 실행 중 이미지 checksum도 다시 검증합니다.

### 3.3 필수 환경값 생성 및 검증

```bash
chmod +x install.sh
sudo ./install.sh --check-secrets
```

최초 실행 시 설치기가 다음 필수 값을 대상 서버의 `.env` 파일에 생성합니다.

- 데이터베이스 비밀번호
- 애플리케이션 secret key
- 자격증명 master key
- 자격증명 암호화 key
- 암호화 salt

설치기는 `.env` 권한을 `0600`으로 설정합니다. 파일에는 리터럴 값만 저장해야 하며 파일 경로, 변수 표현식, 자리표시자 또는 빈 값을 사용할 수 없습니다.

```bash
stat -c '%a %n' .env
```

정상 권한은 `600 .env`입니다.

### 3.4 설치 실행

```bash
sudo ./install.sh
```

설치 스크립트는 다음 작업을 수행합니다.

1. Docker 및 Docker Compose 사전 점검
2. 패키지와 이미지 checksum 검증
3. 5개 Docker 이미지 오프라인 로드
4. 필수 환경값 검증
5. Docker Compose 구성 검증
6. 실행 중인 Docker 컨테이너 중지
7. 기존 Nextrade Blacklist 컨테이너 교체
8. 서비스 기동
9. API, Collector 및 Frontend 헬스 체크

다음 메시지가 표시되면 설치가 완료된 것입니다.

```text
Installation completed!
```

### 3.5 이미지가 이미 로드된 경우

이미지 로드를 생략하고 재설치하려면 다음 옵션을 사용합니다.

```bash
sudo ./install.sh --skip-load
```

---

## 4. 기존 버전 업그레이드

### 4.1 업그레이드 전 백업

기존 `.env`와 데이터베이스를 먼저 백업합니다. 기존 암호화 key가 변경되면 저장된 REGTECH 및 Cloudflare 자격증명을 복호화할 수 없습니다.

```bash
sudo cp -p /opt/blacklist/.env \
  /opt/blacklist.env.backup
```

데이터베이스는 8장의 백업 절차를 따릅니다. 이전 오프라인 패키지도 롤백 완료 전까지 보관합니다.

### 4.2 신규 패키지 준비

```bash
sudo mkdir -p /opt/blacklist-new
sudo tar -xzf blacklist-4.1.0.tar.gz \
  -C /opt/blacklist-new --strip-components=1
sudo cp -p /opt/blacklist/.env /opt/blacklist-new/.env
cd /opt/blacklist-new
```

### 4.3 환경값 검증 및 설치

```bash
sudo ./install.sh --check-secrets
sudo ./install.sh
```

기존 `.env`가 있으면 설치기는 값을 다시 생성하지 않고 유효성만 검사합니다. 설치 완료 후 5장의 설치 검증을 수행합니다.

---

## 5. 설치 검증 및 기본 운영

모든 명령은 설치 디렉터리에서 실행합니다.

### 5.1 컨테이너 상태

```bash
docker compose ps
```

다음 5개 서비스가 실행 중이며 health 상태가 정상이어야 합니다.

- blacklist-app
- blacklist-collector
- blacklist-frontend
- blacklist-postgres
- blacklist-redis

### 5.2 헬스 체크

```bash
curl -fsS http://localhost:2542/health
curl -fsS http://localhost:8545/health
curl -kfsS https://localhost:443 >/dev/null
```

각 명령이 오류 없이 종료되어야 합니다.

### 5.3 화면 접속

::: {.keep-together}
운영자 PC에서 다음 주소로 접속합니다.

```text
https://<대상-서버-주소>/
```

대시보드와 상단 메뉴가 표시되는지 확인합니다.
:::

### 5.4 서비스 명령

| 작업 | 명령 |
|---|---|
| 상태 확인 | `docker compose ps` |
| 전체 로그 | `docker compose logs -f` |
| 최근 로그 | `docker compose logs --since 30m` |
| 특정 서비스 로그 | `docker compose logs -f blacklist-app` |
| 전체 재시작 | `docker compose restart` |
| 전체 중지 | `docker compose down` |
| 전체 시작 | `docker compose up -d` |

`docker compose down` 실행 시 볼륨 삭제 옵션을 추가하지 마십시오. 영구 볼륨을 삭제하면 블랙리스트, 설정과 수집 이력이 손실될 수 있습니다.

---

## 6. 데이터 수집 운영

### 6.1 REGTECH 자격증명 설정

1. 상단 메뉴에서 **데이터 수집**을 선택합니다.
2. REGTECH 카드에서 **설정 및 저장**을 선택합니다.
3. 사용자명, 비밀번호, 수집 주기와 활성화 여부를 입력합니다.
4. 저장 후 **연결 테스트**를 실행합니다.
5. 연결이 성공하면 **수집**을 실행합니다.

비밀번호는 암호화되어 저장되며 화면에 다시 표시되지 않습니다. 변경이 필요한 경우 새 값을 저장합니다.

### 6.2 수집 결과 확인

::: {.keep-together}
수집 완료 후 다음 항목을 확인합니다.

- 최근 실행 시각
- 수집 성공 여부
- 수집 건수와 오류 건수
- IP 관리 및 대시보드 반영 수량

REGTECH 요청 규격과 페이지네이션에 맞춰 페이지당 50건씩 마지막 페이지까지 수집합니다. 중간 페이지 전송 실패는 재시도하며, 복구되지 않으면 부분 수집을 성공으로 처리하지 않습니다.
:::

---

## 7. Cloudflare 연동

### 7.1 사전 준비

- Account Filter Lists 편집 권한이 있는 API Token
- Cloudflare Account ID
- 동기화할 List ID
- 대상 서버에서 Cloudflare API로 연결할 수 있는 승인된 통신 경로

API Token은 화면 캡처, 작업 기록, 로그 또는 장애 보고서에 남기지 않습니다.

### 7.2 설정 및 검증

1. 상단 메뉴에서 **Cloudflare 연동**을 선택합니다.
2. API Token, Account ID와 List ID를 입력합니다.
3. **저장**을 선택합니다.
4. **연결 테스트**를 실행합니다.
5. 연결 상태가 정상인지 확인합니다.

연결 테스트가 실패하면 Token 권한, Account ID와 List ID의 소유 관계 및 외부 통신 정책을 확인합니다.

---

## 8. 백업 및 복구

### 8.1 백업 대상

- PostgreSQL 데이터베이스
- `.env`와 암호화 key
- 인증서와 운영 설정
- 현재 오프라인 패키지와 checksum

### 8.2 데이터베이스 백업

```bash
docker compose exec -T blacklist-postgres \
  pg_dump -U postgres -d blacklist -Fc \
  > blacklist-backup.dump
sha256sum blacklist-backup.dump \
  > blacklist-backup.dump.sha256
```

백업 파일은 운영 볼륨과 다른 승인된 저장소에 보관합니다.

### 8.3 데이터베이스 복구

```bash
sha256sum -c blacklist-backup.dump.sha256
docker compose exec -T blacklist-postgres \
  pg_restore --clean --if-exists \
  -U postgres -d blacklist \
  < blacklist-backup.dump
```

복구는 변경 승인과 서비스 중지 계획을 확보한 후 수행합니다. 복구 후 헬스 체크, IP 조회, 수집 이력과 외부 연동을 다시 확인합니다.

---

## 9. 롤백

1. 장애 시각, 증상과 신규 배포 로그를 보존합니다.
2. 현재 서비스와 데이터베이스 상태를 백업합니다.
3. 보관한 이전 오프라인 패키지를 별도 디렉터리에 압축 해제합니다.
4. 백업한 기존 `.env`를 이전 패키지 디렉터리에 복원합니다.
5. `./install.sh --check-secrets`로 환경값을 검증합니다.
6. 이전 패키지의 `./install.sh`을 실행합니다.
7. 5장의 설치 검증과 6장, 7장의 핵심 기능을 확인합니다.

데이터베이스 스키마 변경이 포함된 경우 승인된 데이터 복구 절차를 함께 수행합니다.

---

## 10. 장애 대응

| 증상 | 확인 | 조치 |
|---|---|---|
| checksum 실패 | 외부 및 내부 checksum | 설치 중단 후 패키지 재반입 |
| 이미지 로드 실패 | 디스크, Docker daemon, 이미지 파일 | 공간 확보 후 설치 재실행 |
| 서비스 기동 실패 | Compose 검증, 상태, 최근 로그 | 하위 의존성부터 복구 |
| 헬스 체크 실패 | App, PostgreSQL, Redis 상태 | 원인 서비스 복구 후 재시작 |
| 데이터 수집 실패 | 자격증명, 외부 통신, Collector 로그 | 원인 수정 후 제한 기간 재수집 |
| Cloudflare 연결 실패 | Token 권한, ID, 외부 통신 | 설정 수정 후 연결 테스트 |
| Frontend 접속 실패 | 443 포트, 방화벽, Frontend 로그 | 포트 충돌과 네트워크 정책 수정 |
| 업그레이드 후 오류 | 변경 전후 로그, 이미지, DB 상태 | 이전 패키지로 롤백 |

### 10.1 기본 증적 수집

```bash
mkdir -p incident
docker compose ps > incident/services.txt
docker compose logs --since 30m > incident/compose.log
docker stats --no-stream > incident/resources.txt
df -h > incident/disk.txt
```

증적을 공유하기 전에 Token, 비밀번호, 세션 또는 개인정보가 포함되지 않았는지 확인합니다. `.env` 파일은 증적에 포함하지 않습니다.

---

## 11. 설치 및 인수인계 체크리스트

- [ ] 외부 패키지 checksum 검증이 정상이다.
- [ ] 내부 `MANIFEST.sha256` 검증이 정상이다.
- [ ] 다른 Docker 서비스의 중단 영향을 확인했다.
- [ ] `.env` 권한이 `0600`이다.
- [ ] 업그레이드 시 기존 암호화 key를 유지했다.
- [ ] 5개 컨테이너가 모두 정상 상태이다.
- [ ] API, Collector 및 Frontend 헬스 체크가 성공했다.
- [ ] REGTECH 연결 테스트와 수동 수집을 확인했다.
- [ ] Cloudflare 연결 테스트를 확인했다.
- [ ] 데이터베이스와 `.env` 백업을 보관했다.
- [ ] 이전 오프라인 패키지를 롤백용으로 보관했다.
- [ ] 운영 담당자에게 상태, 로그와 재시작 절차를 인계했다.

---

## 12. 변경 이력

| 버전 | 일자 | 변경 내용 |
|---|---|---|
| 4.1.0 | 2026-07-28 | 오프라인 패키지 설치, REGTECH 전체 페이지 수집, Cloudflare 연동 및 운영 절차 통합 |
| 3.6.9 | 2026-02-27 | Frontend 직접 SSL, 서비스 명칭 및 Compose 경로 정리 |
