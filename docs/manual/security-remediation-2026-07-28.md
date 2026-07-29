# 2026-07-28 보안 검토 후속 조치 운영 안내

## 범위와 상태

이 문서는 2026-07-29에 `origin/master..HEAD`에서 확인한 로컬 remediation 브랜치 상태를 기록합니다. 아래 항목은 아직 릴리즈 완료를 뜻하지 않습니다. 이전 번들에 적용하려면 새 번들을 배포해야 합니다.

| 검토 항목 | 상태 | 브랜치에서 확인한 근거 |
| --- | --- | --- |
| C-01 | 진행 중 | 해당 ID를 직접 닫는 커밋 제목은 확인되지 않았습니다. 이 문서는 완료를 주장하지 않습니다. |
| C-04 | 진행 중 | `8dbc596`, `f58b8b1`, `7217b76`이 브리지 네트워크, Redis 인증, frontend 포트 공개를 변경했습니다. |
| C-05 | 진행 중 | ADR-0002는 Collector JWT 적용을 보류했고, 이 문서는 그 보상 통제와 한계를 기록합니다. |
| C-06 | 진행 중 | 해당 ID를 직접 닫는 커밋 제목은 확인되지 않았습니다. 이 문서는 완료를 주장하지 않습니다. |
| C-07 | 진행 중 | 해당 ID를 직접 닫는 커밋 제목은 확인되지 않았습니다. 이 문서는 완료를 주장하지 않습니다. |
| M-04 | 진행 중 | 해당 ID를 직접 닫는 커밋 제목은 확인되지 않았습니다. 이 문서는 완료를 주장하지 않습니다. |
| M-05 | 진행 중 | 해당 ID를 직접 닫는 커밋 제목은 확인되지 않았습니다. 이 문서는 완료를 주장하지 않습니다. |
| M-06 | 진행 중 | 해당 ID를 직접 닫는 커밋 제목은 확인되지 않았습니다. 이 문서는 완료를 주장하지 않습니다. |

설치 프로그램 관련 변경은 `a2df133`, `d4b7948`, `066ebe3`, `72fb13e`, `764c43f`, `07e00ba`에 있습니다. Redis 클라이언트 인증 변경은 `3f7dd74`에 있습니다. 이 커밋들은 현재 브랜치에 있으므로, 운영 환경에서 효과를 보려면 해당 번들로 재배포해야 합니다.

## 새 네트워크 모델

모든 서비스는 하나의 Docker bridge 네트워크인 `blacklist-net`에 연결됩니다. Host에 공개되는 포트는 frontend의 `443:3000`뿐입니다. PostgreSQL, Redis, Collector, Flask는 host port를 공개하지 않습니다.

서비스 간 연결은 포트 공개가 아니라 Compose 서비스 DNS 이름을 사용합니다. 예를 들어 app은 `blacklist-collector`, Collector와 app은 `blacklist-postgres` 및 `blacklist-redis`를 사용합니다. 이 구성은 C-04의 host network 노출을 제거하는 보상 통제입니다.

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

내부 서비스 트래픽은 `SSL_ENABLED: "false"`이며, M-02는 해결되지 않았습니다. 이 선택은 bridge 네트워크가 외부에 공개되지 않는다는 전제에서만 허용할 수 있습니다.

Collector JWT 강제 적용도 보류 상태입니다. ADR-0002에 따라 Collector에는 요청 JWT 검증 코드가 없고 app 측 호출도 Authorization header를 보내지 않습니다. `DISABLE_JWT_AUTH`를 `false`로 바꾸는 것만으로는 보호가 생기지 않습니다.

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
