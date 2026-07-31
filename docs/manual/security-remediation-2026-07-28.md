# 2026-07-28 보안 검토 후속 조치 운영 안내

## 범위와 상태

이 문서는 2026-07-29에 `origin/master..HEAD`에서 확인한 로컬 remediation 브랜치 상태를 기록합니다. 아래 항목은 아직 릴리즈 완료를 뜻하지 않습니다. 이전 번들에 적용하려면 새 번들을 배포해야 합니다.

'진행 중'은 커밋 제목에서 해당 ID를 직접 닫는 근거를 찾지 못한 상태이며, 이 표의 상태는 완료 주장이 아닙니다.

| 검토 항목 | 상태 | 브랜치에서 확인한 근거 |
| --- | --- | --- |
| C-01 | 진행 중 | ID를 직접 닫는 커밋 제목 미확인. |
| C-04 | 진행 중 | `8dbc596`, `f58b8b1`, `7217b76`이 브리지 네트워크, Redis 인증, frontend 포트 공개를 변경했습니다. |
| C-05 | 브랜치 조치 완료 | ADR-0002에 따라 Collector 제어 API에 공유 Bearer token 인증을 적용하고 app의 모든 Collector 요청에 자격증명을 연결했습니다. 실제 운영 효과는 새 번들 배포와 설치 프로그램의 token 생성 변경 적용 후 발생합니다. |
| C-06 | 진행 중 | ID를 직접 닫는 커밋 제목 미확인. |
| C-07 | 진행 중 | ID를 직접 닫는 커밋 제목 미확인. |
| M-02 | 브랜치 조치 완료 | `d7f61b5`, `499d3ae`, `de80d3d`, `76ee990`, `6fc8e06`, `7028ec6`, `b7d27c8`이 target-local PKI, TLS-only 서버, 인증서 검증 클라이언트를 적용했습니다. 실제 운영 효과는 새 번들 재배포 후 발생합니다. |
| M-04 | 진행 중 | ID를 직접 닫는 커밋 제목 미확인. |
| M-05 | 진행 중 | ID를 직접 닫는 커밋 제목 미확인. |
| M-06 | 진행 중 | ID를 직접 닫는 커밋 제목 미확인. |

설치 프로그램 관련 변경은 `a2df133`, `d4b7948`, `066ebe3`, `72fb13e`, `764c43f`, `07e00ba`에 있습니다. Redis 클라이언트 인증 변경은 `3f7dd74`에 있습니다. 이 커밋들은 현재 브랜치에 있으므로, 운영 환경에서 효과를 보려면 해당 번들로 재배포해야 합니다.

## 새 네트워크 모델

모든 서비스는 하나의 Docker bridge 네트워크인 `blacklist-net`에 연결됩니다. Host에 공개되는 포트는 frontend의 `443:3000`뿐입니다. PostgreSQL, Redis, Collector, Flask는 host port를 공개하지 않습니다.

서비스 간 연결은 포트 공개가 아니라 Compose 서비스 DNS 이름을 사용합니다. 예를 들어 app은 `blacklist-collector`, Collector와 app은 `blacklist-postgres` 및 `blacklist-redis`를 사용합니다. 이 구성은 C-04의 host network 노출을 제거하는 보상 통제입니다.

## 내부 전송 암호화

설치 프로그램은 target host의 `/etc/blacklist/tls`에 로컬 CA와 `app`, `collector`, `postgres`, `redis` 서비스 인증서를 생성합니다. CA 개인키와 서비스 개인키는 번들, 이미지, 저장소에 포함되지 않습니다. 기존 인증서 세트가 완전하면 재설치 시 그대로 사용하고 권한만 다시 강제합니다. 일부 파일만 남은 불완전한 세트는 자동 재생성하지 않고 배포를 중단합니다.

PostgreSQL은 `sslmode=verify-full`, Redis는 CA 검증이 활성화된 `rediss://`, app과 Collector HTTP API는 HTTPS를 사용합니다. 각 클라이언트는 `/run/blacklist/ca.crt`를 신뢰 기준으로 사용하며 Compose 서비스 DNS 이름과 인증서 SAN이 일치해야 합니다. PostgreSQL과 Redis는 평문 연결을 수락하지 않습니다. Flask와 Collector도 서비스 인증서가 없는 평문 HTTP 리스너를 제공하지 않습니다.

인증서 디렉터리와 개인키를 환경 파일과 함께 안전하게 백업하십시오. 현재 설치 프로그램은 자동 만료 갱신을 수행하지 않습니다. 인증서 교체가 필요하면 유지보수 창에 스택을 중지하고 `/etc/blacklist/tls` 전체를 하나의 단위로 백업한 뒤 다른 위치로 이동하고 설치 프로그램을 다시 실행합니다. 새 CA와 모든 서비스 인증서를 함께 생성한 후 컨테이너를 재생성하고 아래 검증을 완료해야 합니다. 개별 서비스 인증서나 CA만 교체하면 신뢰 체인이 불일치하므로 금지합니다.

## Redis 암호

`REDIS_PASSWORD`는 필수 secret입니다. 설치 프로그램이 로컬에서 자동 생성하며, 배포 번들에 값이 들어가면 안 됩니다. Redis 서버는 이 값을 요구하고, app과 Collector도 같은 값을 받아 Redis에 연결합니다.

암호가 비어 있거나 없으면 배포 검사가 실패해야 합니다. 값은 로그, 문서, 티켓에 붙여 넣지 마십시오.

## 환경 파일 위치와 업그레이드

환경 파일의 기본 위치는 `/etc/blacklist/.env`입니다. 디렉터리 권한은 `700`, 파일 권한은 `600`이어야 합니다. 기본 위치를 바꿔야 하는 경우에만 `BLACKLIST_ENV_FILE`로 경로를 지정합니다.

기존 운영자는 번들 디렉터리에 `.env`가 있으면 설치 전에 `/etc/blacklist/.env`로 옮겨야 합니다. 이 단계를 건너뛰면 설치 프로그램의 기존 배포 보호 장치가 새 secret 생성을 거부합니다. 이동한 뒤 권한을 확인하고 설치를 진행하십시오.

```bash
install -d -m 700 /etc/blacklist
mv .env /etc/blacklist/.env
chmod 600 /etc/blacklist/.env
```

## 관리자 최초 부트스트랩과 교체

새 설치에서는 설치 프로그램이 target host에서 `ADMIN_USERNAME`과 `ADMIN_PASSWORD`를 생성해 `/etc/blacklist/.env`에 저장합니다. Username은 비밀값이 아닌 고정값 `admin`이고, password는 256-bit 무작위 값입니다. 이 값들은 고객별로 설치 시 생성되며 배포 tarball, manifest 또는 vendor 시스템에 포함되지 않습니다.

전체 설치에서는 health check와 설치 완료 메시지 뒤에 최초 password를 한 번만 표시합니다. 새 환경 파일을 만드는 `--check-secrets` 실행도 생성 직후 한 번 표시합니다. 기존 환경 파일을 사용하는 재설치와 업그레이드에서는 다시 표시하지 않습니다. 이 화면에서 즉시 password manager에 보관하고, 첫 로그인 후 아래 절차로 교체하십시오. 다른 secret 값은 화면에 표시되지 않습니다.

Password를 교체하려면 target host의 password manager에서 새 고엔트로피 값을 만든 뒤 `/etc/blacklist/.env`의 `ADMIN_PASSWORD`를 안전하게 수정합니다. Username을 교체해야 할 때는 같은 파일의 `ADMIN_USERNAME`도 수정합니다. 파일 권한을 `600`으로 유지하고 app 컨테이너를 재생성해 변경된 환경을 적용합니다. 단순 `docker compose restart`는 변경된 환경 파일을 다시 읽지 않으므로 사용하지 않습니다.

```bash
chmod 600 /etc/blacklist/.env
docker compose --env-file /etc/blacklist/.env up -d --force-recreate blacklist-app
```

최초 password를 잃어버린 경우에도 같은 복구 절차를 사용합니다. 이 제품에는 사용자 테이블이나 별도 password reset 저장소가 없으므로 `/etc/blacklist/.env`에 새 `ADMIN_PASSWORD`를 기록하고 app 컨테이너를 재생성해야 합니다. `system_settings`에 `admin_username` 또는 `admin_password` override가 이미 존재하는 환경에서는 해당 값이 환경 파일보다 우선하므로 override도 함께 교체하거나 제거하십시오.

## 설치 프로그램 옵션

`--verify-only`는 번들을 설치하지 않고 검사합니다. root 권한 없이 실행할 수 있어 배포 전 감사에 적합합니다.

`--stop-all-containers`는 명시적으로 요청했을 때만 Blacklist와 관계없는 컨테이너도 중지합니다. 기본 동작은 다른 컨테이너를 건드리지 않습니다.

`--skip-posture-check`는 긴급 상황용 탈출구입니다. 사용하면 설치 프로그램이 크게 경고를 남기므로, 사유와 후속 조치를 운영 기록에 남기고 가능한 한 빨리 일반 검사를 다시 실행하십시오.

## 즉시 재배포할 수 없을 때의 임시 방화벽 안내

이 절은 문서 안내일 뿐입니다. 설치 프로그램은 이 규칙을 적용하지 않습니다. bridge migration이 배포되면 아래 임시 조치는 더 이상 주된 통제가 아닙니다.

기존 host network 배포를 잠시 유지해야 한다면 PostgreSQL, Redis, Collector 포트가 loopback 외부에서 수신되지 않도록 다음 규칙을 적용할 수 있습니다.

```bash
iptables -A INPUT -p tcp --dport 5432 ! -i lo -j DROP
iptables -A INPUT -p tcp --dport 6379 ! -i lo -j DROP
iptables -A INPUT -p tcp --dport 8545 ! -i lo -j DROP
```

배포 환경의 방화벽 관리 방식과 충돌하지 않는지 먼저 확인하십시오. 이 규칙은 bridge migration을 대체하지 않습니다.

## 남은 위험

M-02의 내부 평문 전송은 브랜치에서 제거했습니다. 다만 target-local CA의 백업, 만료 감시, 계획된 전체 PKI 교체는 운영 책임으로 남습니다.

Collector의 `POST /trigger`, `POST /api/test-auth/<source>`, `POST /api/force-collection/<source>` 제어 경로는 `COLLECTOR_AUTH_TOKEN` 기반 Bearer 인증을 요구합니다. `GET /health`, `GET /status`, `GET /logs`는 Docker healthcheck와 읽기 전용 운영 조회를 위해 인증 없이 유지합니다.

app과 Collector에는 동일한 `COLLECTOR_AUTH_TOKEN`이 필요합니다. 현재 Compose의 빈 기본값은 인증 강제 상태에서 모든 제어 요청을 401로 거부하는 fail-closed 동작을 만들지만, 설치 프로그램이 token을 생성하는 한 줄이 적용되기 전에는 정상 제어 요청도 사용할 수 없습니다. `DISABLE_JWT_AUTH=true`를 사용하면 제어 API가 다시 인증 없이 열리므로 긴급 상황에서만 제한적으로 사용하고 즉시 원복해야 합니다.

## 롤백

기존 `.rollback-images` 방식은 파일만 쓰고 이를 읽는 코드가 없어 작동하지 않았습니다. 롤백은 이전 번들을 다시 배포하는 방식으로 수행해야 합니다. 배포 전에 이전 번들과 검증 자료를 보관하십시오.

## 운영자 검증

번들 디렉터리에서 다음 검사를 실행합니다.

```bash
bash install.sh --verify-only
```

bridge migration이 적용된 host에서는 다음 출력에 `5432`, `6379`, `8545` 수신 소켓이 없어야 합니다.

```bash
ss -tuln
```

frontend의 `443`만 host 공개 포트인지도 함께 확인하십시오.

설치된 스택에서 인증서 검증이 포함된 연결이 성공하는지 확인합니다.

```bash
docker compose exec -T blacklist-app \
  curl --fail --cacert /run/blacklist/ca.crt \
  https://blacklist-collector:8545/health

docker compose exec -T blacklist-collector \
  curl --fail --cacert /run/blacklist/ca.crt \
  https://blacklist-app:2542/health

docker compose exec -T blacklist-postgres sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" PGSSLMODE=verify-full \
   PGSSLROOTCERT=/run/blacklist/ca.crt \
   psql -h blacklist-postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1"'

docker compose exec -T blacklist-redis sh -c \
  'REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli --tls \
   --cacert /run/blacklist/ca.crt -h blacklist-redis ping'
```

다음 평문 연결은 모두 실패해야 합니다. 하나라도 성공하면 배포를 승인하지 마십시오.

```bash
! docker compose exec -T blacklist-app curl --fail http://blacklist-collector:8545/health
! docker compose exec -T blacklist-collector curl --fail http://blacklist-app:2542/health
! docker compose exec -T blacklist-postgres sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" PGSSLMODE=disable \
   psql -h blacklist-postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1"'
! docker compose exec -T blacklist-redis sh -c \
  'REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli -h blacklist-redis ping'
```
