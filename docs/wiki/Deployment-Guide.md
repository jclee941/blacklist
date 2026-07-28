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

대상 장비에서 설치 스크립트로 필수 부트스트랩 값을 생성합니다:

```bash
deploy/install.sh --check-secrets
```

생성된 `deploy/.env`는 권한이 `0600`으로 설정됩니다. 각 값은 대상 장비에서 생성된 리터럴
값이어야 하며, 파일 경로, 참조 문자열, 변수 표현식, 자리표시자 또는 빈 값은 허용되지 않습니다.
업그레이드할 때는 기존 파일을 그대로 보존하고 새 번들 디렉터리로 복사한 뒤 설치 전에
검증합니다. 암호화 키가 바뀌면 저장된 인증정보를 복호화할 수 없습니다. 첫 설치 후에는
생성된 `ADMIN_USERNAME`과 `ADMIN_PASSWORD`로 웹 UI에 로그인합니다. 업그레이드에서는 이 값도
기존 `.env`에서 보존합니다.

**필수 환경변수:**

| 변수                        | 설명                    | 생성 방법                    |
| --------------------------- | ----------------------- | ---------------------------- |
| `CREDENTIAL_MASTER_KEY`     | AES-256 마스터 키 (hex) | 대상 장비에서 자동 생성      |
| `SECRET_KEY`                | Flask 시크릿 키         | 대상 장비에서 자동 생성      |
| `CREDENTIAL_ENCRYPTION_KEY` | 크레덴셜 암호화 키      | 대상 장비에서 자동 생성      |
| `ENCRYPTION_SALT`           | 암호화 솔트             | 대상 장비에서 자동 생성      |
| `POSTGRES_PASSWORD`         | DB 비밀번호             | 대상 장비에서 자동 생성      |
| `ADMIN_USERNAME`            | 웹 UI 관리자 계정       | 대상 장비에서 자동 생성      |
| `ADMIN_PASSWORD`            | 웹 UI 관리자 비밀번호   | 대상 장비에서 자동 생성      |

**선택 환경변수:**

| 변수                  | 기본값                          | 설명                                |
| --------------------- | ------------------------------- | ----------------------------------- |
| `POSTGRES_USER`       | postgres                        | DB 사용자                           |
| `POSTGRES_DB`         | blacklist                       | DB 이름                             |
| `JWT_SECRET_KEY`      | —                               | JWT 서명 키                         |
| `JWT_EXPIRY_HOURS`    | 8                               | JWT 만료 시간                       |
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
./install.sh --check-secrets
./install.sh
```

첫 실행은 `.env`가 없을 때만 필수 부트스트랩 값을 생성합니다. 기존 `.env`에 빈 값,
파일 경로, 참조 문자열, 변수 표현식, 자리표시자 또는 기본 비밀번호가 있으면 파일을 덮어쓰지
않고 설치를 중단합니다.

서비스가 정상 기동하면 수집 관리 화면에서 REGTECH 카드의 **설정 및 저장**을 선택합니다.
최초 설정에서는 아이디와 비밀번호를 입력하고, 수집 간격과 활성화 여부를 지정한 뒤
저장합니다. 저장 후 **테스트**가 성공한 것을 확인하고 **수집**을 실행합니다. 저장된
비밀번호는 화면으로 다시 반환되지 않습니다.

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

### 릴리스 실행 절차

릴리스 작업은 저장소의 `master` 브랜치에서 수행합니다. 배포 작업은 릴리스 번들을
전달받은 운영 서버에서 수행합니다. 각 단계의 명령이 실패하면 원인을 해결하기 전까지
다음 단계로 넘어가지 않습니다.

#### 1. 릴리스 대상 확인

저장소 루트에서 브랜치, 작업 트리, 대상 버전을 먼저 확인합니다.

```bash
git switch master
git pull --ff-only origin master
test -z "$(git status --porcelain)"

VERSION="$(tr -d '[:space:]' < VERSION)"
test "$(node -p "require('./frontend/package.json').version")" = "${VERSION}"
grep -q "^## \[${VERSION}\]" CHANGELOG.md
test -f "docs/manual/blacklist-${VERSION}-release-notes.md"
test -f docs/manual/blacklist-offline-deployment-guide.pdf
```

다음 파일은 태그를 만들기 전에 내용을 직접 검토합니다.

| 확인 대상                              | 완료 기준                                     |
| -------------------------------------- | --------------------------------------------- |
| `VERSION`                              | 게시할 SemVer와 일치                          |
| `frontend/package.json`                | `version`이 `VERSION`과 일치                  |
| `CHANGELOG.md`                         | 해당 버전의 변경 사항과 날짜가 정확함         |
| 버전별 릴리스 노트                     | 설치 영향, 변경 사항, 알려진 문제를 포함      |
| 오프라인 배포 PDF                      | 현재 `install.sh`와 운영 절차를 반영          |
| `deploy/base.yml`                      | 포트, 볼륨, 필수 환경 변수가 운영 구성과 일치 |
| `deploy/docker-compose.release.yml`    | 5개 서비스 이미지가 모두 정의됨               |
| `deploy/install.sh`, `deploy/prereqs/` | 대상 운영체제에서 실행 가능한 구성임          |

이미지 압축 파일과 최종 번들은 `release.yml`이 생성합니다. 빌드 결과물을 저장소에
추가하지 않습니다.

#### 2. 버전 게시 방식 선택

현재 `VERSION`에서 새 버전을 계산해야 할 때만 자동 버전 상승을 사용합니다.
`release-dry` 출력에서 새 버전과 CHANGELOG 내용을 확인한 뒤 실제 명령을 실행합니다.

```bash
make release-dry TYPE=patch
make release TYPE=patch
```

`make release`는 `VERSION`, `frontend/package.json`, `CHANGELOG.md`를 수정하고 커밋,
태그, `master`를 원격에 게시합니다. `TYPE`은 `patch`, `minor`, `major` 중 하나입니다.

릴리스 준비 PR에서 대상 버전을 이미 반영했다면 `make release`를 실행하지 않습니다.
현재 `master` 커밋의 CI 성공과 태그 미존재를 확인한 뒤 태그만 게시합니다.

```bash
HEAD_SHA="$(git rev-parse HEAD)"
test "${HEAD_SHA}" = "$(git rev-parse origin/master)"
test "$(gh run list --workflow CI --commit "${HEAD_SHA}" --limit 1 \
  --json conclusion --jq '.[0].conclusion')" = "success"
test -z "$(git tag -l "v${VERSION}")"
test -z "$(git ls-remote --tags origin "refs/tags/v${VERSION}")"

git tag -a "v${VERSION}" -m "v${VERSION}"
git push origin "v${VERSION}"
```

#### 3. Release 워크플로 확인

태그 게시 후 GitHub Actions의 `Release` 실행을 엽니다. 아래 작업이 모두 성공해야
게시 완료입니다.

| 작업               | 확인 내용                                                  |
| ------------------ | ---------------------------------------------------------- |
| `validate`         | 태그, `VERSION`, CHANGELOG 버전이 일치                     |
| `build-images`     | frontend, app, collector, postgres, redis 이미지 빌드 성공 |
| `package`          | 릴리스 번들과 두 checksum 파일 생성                        |
| `create-release`   | 해당 태그의 GitHub Release와 첨부 파일 생성                |
| `push-to-registry` | 5개 이미지의 `${VERSION}`, `latest` 태그 게시              |

`create-release` 또는 `push-to-registry`가 실패한 상태에서는 배포 파일을 전달하지
않습니다. 같은 버전의 태그를 새 커밋으로 다시 만들지 말고, 실패 원인을 수정한 뒤 해당
워크플로를 다시 실행합니다.

#### 4. 릴리스 번들 인수 검사

GitHub Release에서 번들과 checksum 파일을 새 검증 디렉토리에 내려받습니다.

```bash
mkdir "release-${VERSION}-verify"
cd "release-${VERSION}-verify"
gh release download "v${VERSION}" \
  --pattern "blacklist-${VERSION}.tar.gz" \
  --pattern "blacklist-${VERSION}.tar.gz.sha256"

sha256sum -c "blacklist-${VERSION}.tar.gz.sha256"
tar tzf "blacklist-${VERSION}.tar.gz"
tar xzf "blacklist-${VERSION}.tar.gz"
cd "blacklist-${VERSION}"

test "$(cat VERSION)" = "${VERSION}"
test -f docker-compose.yml
test -f base.yml
test -x install.sh
test -f RELEASE_NOTES.md
test -f docs/blacklist-offline-deployment-guide.pdf
test -f images/checksums.sha256
test "$(find images -maxdepth 1 -name '*.tar.gz' | wc -l)" -eq 5
sha256sum -c images/checksums.sha256
```

검사에 실패한 파일은 운영 서버로 전달하지 않습니다. GitHub Release의 원본을 다시
내려받아 확인하고, 원본도 실패하면 Release 워크플로를 다시 실행합니다.

#### 5. 운영 배포 준비

운영 서버에서 다음 항목을 배포 전에 확인합니다.

- [ ] 점검 시작·종료 시각과 서비스 영향 범위를 공지했습니다.
- [ ] PostgreSQL 백업 파일이 생성됐고 복원 명령을 확인했습니다.
- [ ] 기존 `.env`를 별도 백업 위치에 복사했습니다.
- [ ] 현재 사용 중인 5개 이미지 태그를 기록했습니다.
- [ ] 새 번들의 외부 checksum과 `images/checksums.sha256` 검사가 성공했습니다.
- [ ] 디스크 여유 공간이 이미지 5개와 기존 이미지 보관에 충분합니다.

기존 배포 디렉토리에서 백업을 생성합니다. 데이터베이스 사용자와 이름은 실행 중인
컨테이너에서 읽으므로 운영 환경의 값을 명령에 다시 적지 않습니다.

```bash
VERSION="$(cat VERSION)"
BACKUP_DIR="$(pwd)/backup-${VERSION}-$(date +%Y%m%d-%H%M%S)"
mkdir -p "${BACKUP_DIR}"

POSTGRES_USER="$(docker exec blacklist-postgres printenv POSTGRES_USER)"
POSTGRES_DB="$(docker exec blacklist-postgres printenv POSTGRES_DB)"
docker exec blacklist-postgres \
  pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" \
  > "${BACKUP_DIR}/postgres.sql"
test -s "${BACKUP_DIR}/postgres.sql"

cp -p .env "${BACKUP_DIR}/.env"
test -f "${BACKUP_DIR}/.env"
docker images --format '{{.Repository}}:{{.Tag}} {{.ID}}' \
  | grep '^blacklist-' > "${BACKUP_DIR}/images.txt"
test -s "${BACKUP_DIR}/images.txt"
```

새 번들 디렉터리에 기존 `.env`를 복사합니다. 이 단계는 설치기 실행보다 먼저 끝나야 합니다.
설치기는 기존 `.env`를 재생성하거나 보정하지 않으며, 유효하지 않은 값이 있으면 중단합니다.

```bash
NEW_BUNDLE_DIR="/path/to/blacklist-${VERSION}"
test -d "${NEW_BUNDLE_DIR}"
cp -p "${BACKUP_DIR}/.env" "${NEW_BUNDLE_DIR}/.env"
test -f "${NEW_BUNDLE_DIR}/.env"
cd "${NEW_BUNDLE_DIR}"
./install.sh --check-secrets
```

검사를 통과해야 하며, 실패하면 기존 운영 백업에서 원래 값을 복원합니다.

`install.sh`는 호스트에서 실행 중인 Docker 컨테이너를 모두 중지합니다. 배포 대상이
아닌 컨테이너가 함께 실행 중이면 아래 목록을 확인해 별도 중지·기동 순서를 정한 후
작업합니다.

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
./install.sh
```

설치 출력에서 `All checksums verified`와 `Installation completed`를 확인합니다.
checksum 파일이 없어서 검증을 건너뛰었다는 경고가 나오면 배포를 중단합니다.

#### 6. 배포 완료 판정

설치가 끝난 디렉토리에서 서비스 상태, 이미지 버전, HTTP 응답을 확인합니다.

```bash
VERSION="$(cat VERSION)"
docker compose ps

for container in blacklist-app blacklist-collector blacklist-frontend \
  blacklist-postgres blacklist-redis; do
  deployed_version="$(docker inspect --format \
    '{{ index .Config.Labels "org.opencontainers.image.version" }}' "${container}")"
  test "${deployed_version}" = "${VERSION}"
done

curl -fsS http://127.0.0.1:2542/health
curl -fsS http://127.0.0.1:8545/health
curl -fkIs https://127.0.0.1:443/health
```

수집 관리 화면에서 REGTECH 인증정보가 **설정됨**으로 표시되는지 확인하고 **테스트**를
실행합니다. 테스트가 성공하면 **수집**을 한 번 실행하고 최근 실행 시각과 수집 건수가
갱신됐는지 확인합니다.

```bash
curl -fsS -X POST \
  http://127.0.0.1:8545/api/force-collection/REGTECH
curl -fsS http://127.0.0.1:8545/status
```

다음 조건을 모두 충족한 시각을 배포 완료 시각으로 기록합니다.

- 5개 서비스가 실행 중이며 health check가 정상입니다.
- 5개 이미지의 OCI version 라벨이 대상 버전과 일치합니다.
- API, Collector, Frontend가 정상 응답합니다.
- REGTECH 수동 수집이 성공하고 최근 실행 시각이 갱신됩니다.
- 설치 전에 중지한 다른 운영 컨테이너가 정상 상태로 복귀합니다.

#### 7. 실패 시 복구

헬스 체크, 버전 검사, 수동 수집 중 하나라도 실패하면 배포 완료로 처리하지 않습니다.
먼저 장애 시점의 상태와 로그를 보관합니다.

```bash
docker compose ps > "deploy-${VERSION}-status.txt"
docker compose logs --no-color > "deploy-${VERSION}-logs.txt" 2>&1
docker compose down
```

배포 전에 기록한 이미지 태그와 `.env`를 복원하고 서비스를 다시 시작합니다. 데이터
변경 때문에 이전 버전이 기동하지 못하는 경우에만 준비한 PostgreSQL 백업을 복원합니다.
복구 후에는 6절의 상태, HTTP, 수집 검사를 다시 수행합니다.

```bash
cp -p "${BACKUP_DIR}/.env" .env
while read -r image_ref image_id; do
  docker tag "${image_id}" "${image_ref}"
done < "${BACKUP_DIR}/images.txt"
docker compose up -d
```

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
