# Blacklist 관리자 가이드

**버전:** 저장소 루트 `VERSION` 기준

이 문서는 Blacklist 운영 관리자를 위한 안내서입니다. 조회는 사용자 가이드, 설치는 오프라인 가이드를 참조하십시오.

## 1. 관리자 계정

- 설치 프로그램은 관리자 자격증명(`ADMIN_USERNAME`/`ADMIN_PASSWORD`)을 한 번만 표시합니다. 안전하게 보관하십시오.
- 대시보드와 API는 JWT 인증이 기본입니다. Fortinet feed는 관리자 JWT 대신 feed token과 network 검사를 사용합니다.
- 관리자 password hash와 session generation은 PostgreSQL `system_settings`에서 한 트랜잭션으로 갱신됩니다. 환경변수는 DB 행이 없을 때만 bootstrap에 사용되며 DB 오류에서는 fail closed 합니다.

## 2. 데이터 수집 관리

![데이터 수집](screenshots/collection.png){ width=45% }

`데이터 수집` 페이지에서 수집기를 등록·점검·실행합니다.

### 수집기 카드 항목

- 수집된 IP: 해당 소스에서 누적 수집한 IP 수
- 수집 간격: 스케줄 주기 (REGTECH 기본 1일)
- 마지막 수집: 최근 수집 완료 시각
- 인증정보: 소스 자격증명 등록 여부

### 작업

- `테스트`: 등록된 자격증명으로 소스 인증을 시험합니다. `인증 성공`이 나와야 수집이 가능합니다.
- `수집`: 전체 기간 수집을 즉시 실행합니다. 장시간(수십 분) 소요되며 진행 상태는 카드와 이력에서 확인합니다.
- `설정 및 저장`: 소스 자격증명·수집 간격·활성화 여부를 변경합니다.
- `수집 이력` 탭: 실행 시각, 신규/중복 건수, 성공 여부를 확인합니다.

### 수집 페이싱 (REGTECH WAF 대응)

원격 WAF는 IP당 요청 쿼터를 적용합니다. 기본값은 5초마다 1페이지(0.2 req/s)이며 환경변수로 조정합니다.

| 변수                                    | 기본값    | 의미                                              |
| --------------------------------------- | --------- | ------------------------------------------------- |
| `REGTECH_RATE_INITIAL`                  | 0.2       | 초기 요청 속도 (req/s)                            |
| `REGTECH_RATE_MIN` / `REGTECH_RATE_MAX` | 0.1 / 0.5 | 적응형 속도 하한·상한                             |
| `REGTECH_RATE_BURST`                    | 1         | 버스트 허용량                                     |
| `REGTECH_BLOCK_THRESHOLD`               | 3         | 연속 차단 신호 한계. 도달하면 실행 중단 후 쿨다운 |

빈 응답·403·429가 연속되면 수집을 중단합니다. 쿨다운 후 재실행하고, 반복되면 속도를 낮추거나 WARP를 검토합니다.

## 3. FortiGate 연동

![FortiGate](screenshots/fortinet.png){ width=45% }

FortiGate에 외부 위협 피드를 연동합니다. 장치 상태와 푸시 결과를 관리하며 인증정보는 암호화되어 저장됩니다.

## 4. Cloudflare 연동

![Cloudflare 연동](screenshots/cloudflare.png){ width=45% }

Cloudflare IP 리스트로 블랙리스트를 푸시합니다. API 토큰, 리스트 매핑, 푸시 이력과 오류를 확인합니다.

## 5. 데이터베이스

![데이터베이스](screenshots/database.png){ width=45% }

테이블과 저장 상태를 확인합니다. 운영 DB는 PostgreSQL입니다. 업그레이드할 때 암호화 키를 유지해 자격증명을 복호화합니다.

## 6. 운영 점검

### 일상 점검

```bash
# 5개 서비스가 모두 healthy인지 확인
docker compose ps

# 수집기 로그 확인 (차단 신호·백오프 여부)
docker logs blacklist-collector --tail 100
```

### 상태 확인 포인트

- 대시보드 우측 배지 `정상`과 수집 카드의 `수집 상태`
- 수집 직후 최대 5분간 `수집 중`으로 표시될 수 있습니다. 실제 상태는 수집기 로그에서 확인합니다.
- Collector 포트는 내부 전용입니다. `/health` 외의 API에는 `COLLECTOR_AUTH_TOKEN` Bearer 토큰이 필요합니다.

### 백업 권장 대상

- `/etc/blacklist/.env` (비밀값·암호화 키)
- PostgreSQL 볼륨 (`blacklist-pgdata`) — 블랙리스트·설정·수집 이력
- `/etc/blacklist/tls/` (내부 TLS 인증서)

## 7. 장애 대응 요약

| 증상                      | 조치                                                                                        |
| ------------------------- | ------------------------------------------------------------------------------------------- |
| 수집이 0건으로 기록됨     | 수집기 로그의 HTTP 상태 확인. 빈 응답 연속이면 WAF 차단 — 쿨다운 후 재시도                  |
| `인증 성공`인데 수집 실패 | 소스 페이지 구조 변경 또는 쿼터 차단 가능. 수집기 로그와 아카이브(`/app/data/archive`) 확인 |
| 대시보드 접속 불가        | `docker compose ps`로 frontend 상태 확인, 443 포트 점유 여부 확인                           |
| 자격증명 복호화 실패      | `.env`의 암호화 키가 초기 설치 값과 다른지 확인. 키 교체 시 저장 자격증명 재등록 필요       |
