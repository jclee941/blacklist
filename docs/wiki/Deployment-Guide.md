# 배포 가이드

## 개요

Blacklist Platform은 Docker 기반으로 배포되며, 오프라인 환경 설치를 지원합니다.

| 배포 방식       | 대상 환경      | Compose 파일                      |
| --------------- | -------------- | --------------------------------- |
| 개발 (make dev) | 로컬 개발      | `deploy/docker-compose.yml`       |
| CI/CD           | GitHub Actions | `.github/docker-compose.ci.yml`   |
| 프로덕션        | 서버           | `deploy/base.yml` + `release.yml` |
| 오프라인        | 폐쇄망         | `install.sh` + 이미지 번들        |

---

## Docker 이미지

| 서비스        | 베이스 이미지               | 빌드 스테이지                   | 사용자          | 포트 |
| ------------- | --------------------------- | ------------------------------- | --------------- | ---- |
| **app**       | `python:3.11-slim-bullseye` | 2단계 (build + runtime)         | `app:app`       | 2542 |
| **collector** | `python:3.11-slim`          | 2단계 (builder + runtime)       | 비root          | 8545 |
| **frontend**  | `node:20-alpine`            | 3단계 (deps + builder + runner) | `nextjs:nodejs` | 443  |
| **postgres**  | `postgres:15-alpine`        | 단일                            | postgres        | 5432 |
| **redis**     | `redis:7-alpine`            | 단일                            | redis           | 6379 |

### 빌드 인자

```dockerfile
ARG APP_VERSION=0.0.0-dev
ARG GIT_COMMIT
ARG BUILD_DATE
```

---

## 개발 환경

```bash
# 전체 서비스 실행 (핫 리로드)
make dev

# 개별 서비스 재시작
make dev-app
make dev-frontend

# 로그 확인
make logs

# 헬스 체크
make health

# DB 쉘
make db-shell
```

### 볼륨

| 볼륨                       | 마운트 위치                | 용도           |
| -------------------------- | -------------------------- | -------------- |
| `blacklist-pgdata`         | `/var/lib/postgresql/data` | DB 데이터      |
| `blacklist-redis-data`     | `/data`                    | Redis 캐시     |
| `blacklist-collector-data` | `/app/data`                | Collector 상태 |
| `blacklist-logs`           | `/app/logs`                | 공유 로그      |
| `blacklist-uploads`        | `/app/uploads`             | 업로드 파일    |
| `blacklist-app-data`       | `/app/data`                | App 상태       |

---

## 프로덕션 배포

### 사전 요구사항

- Docker Engine 24+
- Docker Compose V2
- 최소 4GB RAM, 20GB 디스크

### 환경변수 설정

`deploy/.env.example`을 복사하여 `.env` 파일을 생성합니다:

```bash
cp deploy/.env.example .env
```

**필수 환경변수:**

| 변수                        | 설명                    | 생성 방법                                                  |
| --------------------------- | ----------------------- | ---------------------------------------------------------- |
| `CREDENTIAL_MASTER_KEY`     | AES-256 마스터 키 (hex) | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `SECRET_KEY`                | Flask 시크릿 키         | 위와 동일                                                  |
| `CREDENTIAL_ENCRYPTION_KEY` | 크레덴셜 암호화 키      | 위와 동일                                                  |
| `ENCRYPTION_SALT`           | 암호화 솔트             | 위와 동일                                                  |
| `POSTGRES_PASSWORD`         | DB 비밀번호             | 직접 설정                                                  |

**선택 환경변수:**

| 변수                  | 기본값                          | 설명                                |
| --------------------- | ------------------------------- | ----------------------------------- |
| `POSTGRES_USER`       | postgres                        | DB 사용자                           |
| `POSTGRES_DB`         | blacklist                       | DB 이름                             |
| `JWT_SECRET_KEY`      | —                               | JWT 서명 키                         |
| `JWT_EXPIRY_HOURS`    | 8                               | JWT 만료 시간                       |
| `ADMIN_USERNAME`      | **SET_ADMIN_USERNAME**          | 관리자 계정 (배포 시 변경 필수)     |
| `ADMIN_PASSWORD`      | **SET_ADMIN_PASSWORD**          | 관리자 비밀번호 (배포 시 변경 필수) |

| `COLLECTOR_URL`       | http://blacklist-collector:8545 | Collector URL                       |
| `LOG_LEVEL`           | INFO                            | 로그 레벨                           |
| `COLLECTION_INTERVAL` | 3600                            | 수집 간격 (초)                      |

### 빌드 및 실행

```bash
# 프로덕션 이미지 빌드 (clean git tree 필요)
make build

# 배포
make deploy
```

---

## 오프라인 설치

인터넷이 없는 폐쇄망 환경을 위한 배포 방식입니다.

### 번들 구조

```
blacklist-{VERSION}/
├── images/
│   ├── app.tar.gz
│   ├── collector.tar.gz
│   ├── frontend.tar.gz
│   ├── postgres.tar.gz
│   ├── redis.tar.gz
│   └── checksums.sha256
├── docker-compose.yml
├── base.yml
├── install.sh
├── prereqs/               # Docker 오프라인 바이너리 (선택)
└── VERSION
```

### 설치 과정

```bash
# 1. 번들 압축 해제
tar xzf blacklist-3.6.9.tar.gz
cd blacklist-3.6.9

# 2. 설치 스크립트 실행
chmod +x install.sh
./install.sh
```

### install.sh 동작 순서

#### Diagram summary 1

- Type: flowchart
- 1. Preflight 체크 / (Docker, 이미지 파일) (A) -> 2. Docker 오프라인 설치 / (필요 시, prereqs/) (B)
- 2. Docker 오프라인 설치 / (필요 시, prereqs/) (B) -> 3. 이미지 로드 / (docker load .tar.gz) (C)
- 3. 이미지 로드 / (docker load .tar.gz) (C) -> 4. 암호화 키 자동 생성 (D)
- 4. 암호화 키 자동 생성 (D) -> 5. .env 파일 생성 (E)
- 5. .env 파일 생성 (E) -> 6. docker-compose up (F)
- 6. docker-compose up (F) -> 7. 헬스체크 대기 / (PostgreSQL → Redis → App → Frontend) (G)
- 7. 헬스체크 대기 / (PostgreSQL → Redis → App → Frontend) (G) -> 8. 전체 서비스 검증 (H)


### Rollback

`install.sh`는 `.rollback-images` 디렉토리에 이전 이미지를 백업합니다.

---

## CI/CD 파이프라인

### CI (`ci.yml` — Push/PR to master)

#### Diagram summary 2

- Type: flowchart
- detect-changes (A) -> lint-backend (B)
- detect-changes (A) -> lint-frontend (C)
- lint-backend (B) -> test-backend (D)
- lint-frontend (C) -> test-frontend (E)
- detect-changes (A) -> test-collector (F)
- test-backend (D) -> build (G)
- test-frontend (E) -> build (G)
- test-collector (F) -> build (G)
- build (G) -> e2e (H)
- e2e (H) -> push-images (I)


| Job                | 도구         | 상세                                          |
| ------------------ | ------------ | --------------------------------------------- |
| **detect-changes** | path filter  | frontend/, app/, collector/, tests/ 변경 감지 |
| **lint-backend**   | Ruff         | check + format (line-length 120)              |
| **lint-frontend**  | ESLint + tsc | `--noEmit` 타입 체크                          |
| **test-backend**   | pytest       | 785+ tests, coverage >= 80% 필수              |
| **test-frontend**  | vitest       | 207+ tests                                    |
| **test-collector** | pytest       | 세션 관리 보안 테스트 포함                    |
| **build**          | Docker       | matrix: frontend, app, collector              |
| **e2e**            | Playwright   | smoke + chromium + webkit                     |
| **push-images**    | GHCR         | master 브랜치만                               |

### Release (`release.yml` — Tag v\*)

#### Diagram summary 3

- Type: flowchart
- validate (A) -> build-images (B)
- build-images (B) -> package (C)
- package (C) -> create-release (D)
- package (C) -> push-to-registry (E)
- create-release (D) -> notify (F)
- push-to-registry (E) -> notify (F)


| Job                  | 상세                                        |
| -------------------- | ------------------------------------------- |
| **validate**         | VERSION 파일 == 태그, CHANGELOG 확인        |
| **build-images**     | 5개 서비스 매트릭스 빌드                    |
| **package**          | 타르볼 생성 (이미지 + compose + install.sh) |
| **create-release**   | GitHub Release + 번들 asset                 |
| **push-to-registry** | GHCR: version + latest 태그                 |

### 릴리스 담당자 작업 체크리스트

#### 1. 릴리스 입력 파일 준비

태그를 만들기 전에 다음 파일을 대상 버전에 맞춥니다. `${VERSION}`은 `VERSION`
파일에 기록된 SemVer 값입니다.

- [ ] `VERSION`에 대상 버전이 기록되어 있습니다.
- [ ] `frontend/package.json`의 `version`이 `VERSION`과 같습니다.
- [ ] `CHANGELOG.md`에 `## [${VERSION}]` 항목이 있습니다.
- [ ] `docs/manual/blacklist-${VERSION}-release-notes.md`가 있습니다.
- [ ] `docs/manual/blacklist-offline-deployment-guide.pdf`가 최신 운영 절차를 반영합니다.
- [ ] `deploy/docker-compose.release.yml`, `deploy/base.yml`, `deploy/install.sh`,
      `deploy/prereqs/`를 검토했습니다.

`release.yml`의 `package` 작업은 위 릴리스 노트와 PDF를 번들에 복사하므로 파일이
없으면 릴리스가 실패합니다. 이미지 압축 파일과 최종 번들은 워크플로가 생성하므로
저장소에 직접 추가하지 않습니다.

#### 2. 게시 경로 선택

아래 두 경로 중 하나만 사용합니다.

**일반 자동 버전 상승**

현재 `VERSION`이 이전 릴리스 버전일 때 사용합니다. `scripts/release.sh`가 버전,
CHANGELOG, Frontend 버전을 갱신한 뒤 커밋과 태그를 생성합니다.

```bash
make release-dry TYPE=patch
make release TYPE=patch
```

**이미 준비된 버전 게시**

릴리스 준비 PR에서 `VERSION`, CHANGELOG, 릴리스 노트를 이미 대상 버전으로
갱신했다면 `make release`를 실행하지 않습니다. 다시 실행하면 다음 버전으로 한 번 더
상승합니다. `master`의 필수 CI 성공을 확인한 뒤 현재 버전으로 태그만 게시합니다.

```bash
VERSION="$(tr -d '[:space:]' < VERSION)"
test "$(node -p "require('./frontend/package.json').version")" = "${VERSION}"
grep -q "^## \[${VERSION}\]" CHANGELOG.md
test -f "docs/manual/blacklist-${VERSION}-release-notes.md"
test -f docs/manual/blacklist-offline-deployment-guide.pdf

git tag -a "v${VERSION}" -m "v${VERSION}"
git push origin "v${VERSION}"
```

#### 3. 릴리스 워크플로 확인

- [ ] `Release`의 `validate`, `build-images`, `package`, `create-release`,
      `push-to-registry` 작업이 성공했습니다.
- [ ] `Release Notes Generator`가 동일 태그의 GitHub Release를 생성하거나
      갱신했습니다.
- [ ] GitHub Release에 `blacklist-${VERSION}.tar.gz`와
      `blacklist-${VERSION}.tar.gz.sha256`가 첨부되었습니다.
- [ ] GHCR의 5개 서비스 이미지에 `${VERSION}`과 `latest` 태그가 게시되었습니다.

#### 4. 릴리스 번들 검증

다운로드한 두 파일이 같은 디렉토리에 있는 상태에서 패키지 체크섬과 구성을
확인합니다.

```bash
sha256sum -c "blacklist-${VERSION}.tar.gz.sha256"
tar tzf "blacklist-${VERSION}.tar.gz"
tar xzf "blacklist-${VERSION}.tar.gz"
cd "blacklist-${VERSION}"
sha256sum -c images/checksums.sha256
```

압축 해제된 번들에 이미지 5종, `docker-compose.yml`, `base.yml`, `install.sh`,
`VERSION`, `RELEASE_NOTES.md`, `docs/blacklist-offline-deployment-guide.pdf`가 있어야
합니다.

#### 5. 운영 배포 및 완료 확인

- [ ] 데이터베이스와 기존 `.env`를 백업했습니다.
- [ ] 점검 시간을 확보하고 `install.sh`가 실행 중인 모든 Docker 컨테이너를
      중지한다는 내용을 운영자에게 전달했습니다.
- [ ] `./install.sh`를 실행하고 이미지 체크섬 검증이 성공했습니다.
- [ ] `docker compose ps`에서 5개 서비스가 정상 상태입니다.
- [ ] 5개 컨테이너의 `org.opencontainers.image.version` 라벨이 `${VERSION}`과
      같고 `0.0.0-dev` 또는 이전 버전이 아닙니다.
- [ ] API `/api/health`, Collector `/health`, Frontend HTTPS 접근을 확인했습니다.
- [ ] 수동 REGTECH 수집을 1회 실행하고 수집 상태와 로그를 확인했습니다.
- [ ] 설치 과정에서 중지된 다른 운영 컨테이너가 있다면 별도 운영 절차에 따라
      다시 기동했습니다.

```bash
for container in blacklist-app blacklist-collector blacklist-frontend \
  blacklist-postgres blacklist-redis; do
  deployed_version="$(docker inspect --format \
    '{{ index .Config.Labels "org.opencontainers.image.version" }}' "${container}")"
  test "${deployed_version}" = "${VERSION}"
done
```

헬스 체크 또는 수집 검증이 실패하면 신규 배포를 완료로 기록하지 않습니다. 로그와
실패 시점을 보존한 뒤 이전 이미지 태그와 데이터베이스 백업으로 복구하고, 복구 후
동일한 헬스 체크를 다시 수행합니다.

### 릴리스 프로세스

```bash
# 패치 릴리스
make release

# 마이너 릴리스
make release TYPE=minor

# 메이저 릴리스
make release TYPE=major

# Dry-run
make release-dry
```

**`scripts/release.sh` 동작:**

1. Clean working tree + master 브랜치 확인
2. 현재 VERSION 파싱 (semver)
3. 버전 bump (patch/minor/major)
4. CHANGELOG 자동 생성 (git log)
5. VERSION + CHANGELOG 커밋
6. Annotated 태그 생성 (`v{VERSION}`)
7. master + 태그 Push
8. GitHub Actions 릴리스 파이프라인 자동 트리거

---

## 모니터링

### Prometheus 메트릭

| 도메인                | 파일               | 크기  | 메트릭                                      |
| --------------------- | ------------------ | ----- | ------------------------------------------- |
| **Request/Business**  | `metrics.py`       | 412줄 | HTTP 요청수, 블랙리스트 작업수, 수집 이벤트 |
| **Cache Performance** | `cache_metrics.py` | 397줄 | Hit/miss 비율, 레이턴시                     |
| **Error Rates**       | `error_metrics.py` | 289줄 | 에러 분류, 비율 추적                        |

**엔드포인트**: `GET /metrics` (public, JWT 불필요)

### 헬스체크

| 서비스    | 엔드포인트       | Interval | Timeout | Start Period |
| --------- | ---------------- | -------- | ------- | ------------ |
| postgres  | `pg_isready`     | 30s      | 10s     | 40s          |
| redis     | `redis-cli ping` | 30s      | 10s     | 10s          |
| collector | `/health`        | 30s      | 10s     | 40s          |
| app       | `/health`        | 30s      | 10s     | 90s          |
| frontend  | `/health`        | 30s      | 10s     | 60s          |

### 로깅

- 공유 볼륨: `/app/logs`
- 로그 레벨: `LOG_LEVEL` 환경변수 (기본 INFO)
- 형식: Python logging (Flask) + APScheduler (Collector)

---

## Makefile 타겟 요약

| 카테고리   | 명령                         | 설명                       |
| ---------- | ---------------------------- | -------------------------- |
| **개발**   | `make dev`                   | 전체 서비스 핫 리로드      |
|            | `make dev-app`               | App만 재시작               |
|            | `make dev-frontend`          | Frontend만 재시작          |
|            | `make logs`                  | 로그 확인                  |
|            | `make health`                | 헬스 체크                  |
| **테스트** | `make test`                  | 전체 테스트                |
|            | `make test-backend-unit`     | Backend unit (pytest)      |
|            | `make test-backend-coverage` | Coverage >= 80%            |
|            | `make test-frontend-unit`    | Frontend unit (vitest)     |
|            | `make test-e2e`              | E2E (Playwright)           |
| **빌드**   | `make build`                 | 프로덕션 이미지 빌드       |
|            | `make deploy`                | 프로덕션 배포              |
|            | `make release`               | 릴리스 (bump + tag + push) |
| **DB**     | `make db-shell`              | PostgreSQL 쉘              |
|            | `make db-backup`             | DB 백업                    |
|            | `make db-restore`            | DB 복원                    |
| **유틸**   | `make clean`                 | 정리                       |
