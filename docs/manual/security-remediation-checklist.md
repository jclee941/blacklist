# 취약점 이행 체크리스트

**검토:** 정보보호팀 코드검토 (2026-07-28)
**대상:** Blacklist 오프라인 배포 패키지
**조치 버전:** 5.1.2
**검증일:** 2026-09-04

검증은 오프라인 번들 `blacklist-5.0.0.tar.gz`를 실제로 압축 해제해 `install.sh`로 설치한 배포에서 수행했습니다. 아래 "검증 방법"은 운영자가 자기 환경에서 그대로 재현할 수 있는 명령입니다.

---

## 심각 (Critical)

### C-01 · 체크섬 검증 fail-open — 이행

목록 파일이 없거나, 목록에 있는 파일이 디스크에 없거나, 검증 건수가 0이어도 성공으로 처리되던 경로를 모두 치명적 오류로 바꿨습니다. `./` 접두사와 `*` 바이너리 표기를 정규화해 두 종류의 생성기 출력을 모두 수용합니다.

```bash
bash install.sh --verify-only          # 정상 번들 → 통과
truncate -s 0 images/checksums.sha256  # 빈 목록
bash install.sh --verify-only          # → 중단
```

**확인됨:** 목록 삭제·빈 목록·이미지 1바이트 변조 모두 거부.

### C-02 · 무검증 특권 바이너리 설치 — 이행

`docker-*.tgz`와 compose 바이너리를 root로 전개·복사하기 **직전에** 매니페스트 항목별로 재해시합니다. 매니페스트에 등재되지 않은 파일도 거부합니다.

```bash
printf 'x' >> prereqs/docker-29.2.1.tgz
bash install.sh --verify-only          # → 추출 이전 중단
```

**확인됨:** 변조 시 `tar` 실행 이전에 중단(`tar-invoked=no`).

### C-03 · 매니페스트 미검증·미서명 — 이행

`MANIFEST.sha256` 부재를 치명적으로 처리하고 번들 전체를 검증합니다. 일반 설치는 내부 manifest와 최종 tarball의 detached signature를 필수 검증하며, 공개키 fingerprint는 별도 인증 채널에서 확인합니다.

```bash
rm MANIFEST.sha256 && bash install.sh --verify-only   # → 중단
bash install.sh --require-signature                    # 키링 없으면 중단
```

**확인됨:** CI가 내부 manifest와 최종 tarball을 전용 GPG 키로 서명하며, 공개키·fingerprint·릴리스 노트를 Release 자산으로 게시합니다.

### C-04 · 호스트 네트워킹 노출 — 이행

5개 서비스를 내부 bridge(`blacklist-net`)로 옮기고 호스트 공개 포트를 frontend `443` 하나로 줄였습니다. Redis에 비밀번호를 요구하고 app·collector 클라이언트에 배선했습니다.

```bash
ss -tuln | grep -E ':(5432|6379|8545|2542)\b'   # 출력 없어야 정상
docker ps --format '{{.Names}} {{.Ports}}'
```

**확인됨:** 실제 설치에서 5432·6379·8545·2542 호스트 리스너 0건, `0.0.0.0:443->3000` 하나만 존재.

### C-05 · Collector 제어 API 무인증 — 이행

제어 엔드포인트(`/trigger`, `/api/test-auth/<source>`, `/api/force-collection/<source>`)에 베어러 토큰 검증을 구현했습니다. `/health`, `/status`, `/logs`는 Docker 헬스체크가 사용하므로 의도적으로 개방합니다.

```bash
docker exec blacklist-app curl -sk --cacert /run/blacklist/ca.crt \
  -X POST https://blacklist-collector:8545/trigger        # → 401
```

**확인됨:** 무토큰 401, 유효 토큰 200.

**부수 조치:** 릴리즈 노트의 "container-internal loopback 제한" 문구는 host 네트워킹 하에서 사실이 아니었으므로 실제 상태로 정정했습니다.

### C-06 · root 권한 미검사 — 이행

`--help`, `--check-secrets`, `--verify-only` 이후, 첫 특권 작업 직전에 `id -u` 검사를 배치했습니다.

```bash
bash install.sh          # 일반 계정 → 즉시 중단
```

**확인됨:** 이미지 로드 이전 중단, 부분 작업 없음.

### C-07 · 호스트 전체 컨테이너 중지 — 이행

기본 경로는 `blacklist-*`만 다루고, 호스트 전체 중지는 `--stop-all-containers` 옵트인으로 분리했습니다.

**확인됨:** 무관 컨테이너 5개 실행 중 설치 → 전부 Up 유지.

---

## 중간 (Medium)

| 항목 | 상태 | 조치 |
| --- | --- | --- |
| M-01 헬스 응답 오판정 | 이행 | 상태값을 정규식으로 엄격 판정. `{"status":"error"}`는 실패로 처리 |
| M-02 내부 구간 평문 | 이행 | 대상 호스트 생성 CA로 PostgreSQL·Redis·Flask·Collector 전 구간 TLS. 클라이언트는 CA와 hostname 검증 |
| M-03 `:latest` 재태깅·죽은 롤백 | 이행 | 이미지 태그를 배포 버전으로 고정, 동작하지 않던 `.rollback-images` 제거 |
| M-04 디스크 검사 대상 오류 | 이행 | `docker info DockerRootDir` 기준으로 검사, 파싱 실패 시 안전 처리 |
| M-05 포트 점유 경고 | 이행 | 실제 공개 포트(443) 점유를 치명적으로 처리 |
| M-06 번들 내 `.env` | 이행 | `/etc/blacklist/.env`(700/600), `BLACKLIST_ENV_FILE` 오버라이드 |
| M-07 PCRE 의존 | 이행 | `grep -oP` → POSIX `sed`. 무매치 시 명시적 실패 |
| M-08 고정 대기 | 이행 | `docker inspect` 상태 폴링(5초 간격, 180초 한도) |

**M-02 검증**

```bash
docker exec blacklist-app sh -c 'curl -s --max-time 5 http://blacklist-app:2542/health'   # → 거부
docker exec blacklist-postgres psql "sslmode=verify-full ..." -c 'SELECT ssl FROM pg_stat_ssl'
```

**확인됨:** PostgreSQL `ssl=t`, Redis TLS `PONG`, app→collector HTTPS 200. 네 링크 모두 평문 접속과 CA 미신뢰 접속 거부.

---

## 가이드 밖 발견 사항

검토 범위에 없었으나 조치 과정에서 발견한 항목입니다.

### X-01 · 공개 소스 관리자 인증 우회 — 이행 (심각도 C 상당)

`ADMIN_USERNAME`/`ADMIN_PASSWORD` 미설정 시 기본값 `__SET_ADMIN_USERNAME__`/`__SET_ADMIN_PASSWORD__`가 **실제 관리자 로그인을 통과**했습니다. 두 문자열은 공개 소스에 있고, 설치기는 이 값들을 생성하지 않았습니다.

미설정 시 로그인 불가로 fail-closed 전환하고, 대상 호스트에서 생성해 최초 설치 1회만 표시합니다.

```bash
curl -sk -X POST https://localhost:443/api/auth/login \
  -d '{"username":"__SET_ADMIN_USERNAME__","password":"__SET_ADMIN_PASSWORD__"}' \
  -H 'Content-Type: application/json'                     # → 401
```

**확인됨:** 센티널 401, 생성된 비밀번호로 200.

### X-02 · Flask Redis 무인증 — 이행

C-04로 Redis에 비밀번호를 걸었으나 Flask 클라이언트가 `REDIS_PASSWORD`를 읽지 않아, 캐시가 죽은 채 DB 조회로 조용히 degrade될 상태였습니다. 배선을 추가했습니다.

### X-03 · 포스처 게이트 기본값 오류 — 이행

배포 게이트가 ADR 파일 부재 시 `defer`를 기본값으로 사용했는데, 오프라인 번들에는 `docs/decisions/`가 포함되지 않습니다. 모든 실설치가 거부될 상태였습니다. 기본값을 실제 결정으로 맞추고 드리프트 검사를 양방향으로 만들었습니다.

### X-04 · 이미지 태그 불일치 — 이행

`:latest` 재태깅 제거 후 compose가 존재하지 않는 이미지를 참조했고, 업그레이드 시 `BLACKLIST_VERSION`이 갱신되지 않아 이전 버전이 재배포됐습니다.

### X-05 · 번들 마운트 자산 누락 — 이행

`base.yml`이 상대경로로 바인드 마운트하는 파일이 번들에 포함되지 않아, Docker가 같은 이름의 빈 디렉터리를 만들고 frontend가 기동 실패했습니다. 마운트 목록을 compose에서 도출하도록 바꿔 재발을 차단했습니다.

### X-06 · 인증 상태 엔드포인트 상시 500 — 이행

`/api/auth/me`, `/api/auth/verify`, `/api/auth/status`가 모든 호출에서 500을 반환했습니다. 앞 둘은 등록되지 않은 훅의 `g.current_user`를 참조했고, 오류 처리기가 지원하지 않는 인자를 넘겨 진짜 원인을 은폐했으며, 마지막은 존재하지 않는 메서드를 호출했습니다. master에도 동일하게 존재하던 선행 결함입니다.

---

## 잔여 위험

| 항목 | 내용 | 대응 |
| --- | --- | --- |
| 번들 서명 | GPG signing key 수명주기 | private key는 1Password와 GitHub production environment에 보관하고 만료 전에 별도 변경 절차로 교체 |
| 오프라인 Docker 페이로드 | `prereqs/`에 Docker 바이너리 미포함 | Docker 사전 설치 전제. 베어 호스트 대상이면 두 파일을 넣어야 하며, 일부만 넣으면 패키저가 경고 |
| 개발기 WARP 프록시 | 프록시가 `127.0.0.1` 전용이면 브리지에서 도달 불가 | 게이트웨이에서 접근 가능한 주소로 리스닝 필요. 운영 오버레이는 무관 |

---

## 배포 전 확인 절차

```bash
# 1. 번들 무결성 (설치 없이)
bash install.sh --verify-only

# 2. 설치
sudo bash install.sh          # 최초 설치 시 관리자 비밀번호가 1회 표시됨

# 3. 노출 면 확인
ss -tuln | grep -E ':(5432|6379|8545|2542)\b'   # 출력 없어야 정상

# 4. 서비스 상태
docker compose ps                                # 5개 서비스 healthy
```
