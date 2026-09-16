# 2026-09-16 보안 검토 후속 조치

## 범위

`Blacklist 5.1.3 보안 취약점 검토 결과`(2026-09-16, 오프라인 배포 번들 정적 분석) 5장 "조치 우선순위" 1~6번을 운영 소스에 반영한 기록입니다. 보고서가 지적한 항목은 모두 운영 소스에서 재확인했고, 지적 내용이 현재 코드에도 그대로 존재함을 확인한 뒤 수정했습니다.

이 문서는 저장소 반영 상태를 기록합니다. 운영 서버에 효과가 생기려면 새 번들을 빌드해 재배포해야 합니다.

## 조치 내역

| 순서 | 보고서 항목               | 조치                                                                                                                                                                               | 반영 위치                                                                                                                             |
| ---- | ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | M-1 전량 교체 가드 부재   | 푸시 직전 Cloudflare 리스트의 실제 항목 수를 읽어 증감률이 30%를 넘으면 중단하고 `critical` 로그를 남깁니다. 기준 항목 수가 50건 미만이면 가드를 적용하지 않습니다.                | `app/core/services/cloudflare_push_service.py`                                                                                        |
| 1    | M-1 rate limit 폐기       | 제한 구간에 들어온 변경을 버리지 않고 dirty 플래그로 유지한 뒤 재시도합니다. 실패·조회 불가도 동일하게 재시도 대상이며, 가드 위반만 재시도하지 않습니다.                           | `app/core/services/cloudflare_push_service.py`                                                                                        |
| 1    | M-1 재시작 시 상태 초기화 | rate limit 판정에 로컬 시각과 Cloudflare 리스트의 `modified_on`을 함께 사용합니다. 원격 시각이 기준이므로 프로세스가 재시작해도 유지됩니다.                                        | `app/core/services/cloudflare_push_service.py`                                                                                        |
| 2    | A-1 Cloudflare 배선 미완  | 실행 경로 네 가지를 모두 연결했습니다. 앱 컨테이너가 데몬 스레드로 리스너를 실행하고, DB 트리거가 `blacklist_changes` 알림을 발행합니다.                                           | `app/core/app_lifecycle.py`, `postgres/migrations/009_add_blacklist_change_notify.sql`                                                |
| 3    | M-3 미등록 위험 라우트    | 평문 자격증명 저장 라우트와 해당 화면, 프리픽스 하한 없는 CIDR 검증기를 삭제했습니다.                                                                                              | `app/core/routes/web/settings.py`, `app/templates/settings.html`, `collector/core/validators.py` (삭제)                               |
| 4    | M-2 평문 토큰 수용 분기   | `encrypted=false` 자격증명 행을 거부하고 오류 로그를 남깁니다. 복호화 경로만 남았습니다.                                                                                           | `app/core/services/cloudflare_push_service.py`                                                                                        |
| 5    | M-4 토큰 저장 위치        | JWT를 `localStorage`에서 `HttpOnly`·`SameSite=Strict` 쿠키로 옮겼습니다. 브라우저 코드가 토큰을 읽지 못합니다. `Authorization` 헤더 경로는 비브라우저 클라이언트용으로 유지합니다. | `app/core/auth/middleware.py`, `app/core/routes/api/auth_routes.py`, `frontend/lib/api.ts`, `frontend/components/AuthGate.tsx`        |
| 5    | M-4 CSP unsafe-inline     | 응답 CSP의 `script-src`에서 `unsafe-inline`을 제거하고 요청마다 nonce를 발급합니다. Next.js가 인라인 스크립트에 같은 nonce를 찍도록 페이지를 요청 단위 렌더링으로 전환했습니다.    | `frontend/server.js`, `frontend/server-routing.js`, `frontend/app/layout.tsx`                                                         |
| 6    | L-1 수집기 fail-open 인증 | 목록에 있는 경로만 인증하던 방식을 기본 거부로 뒤집었습니다. `/health`만 공개이고 이후 추가되는 경로는 자동으로 인증 대상입니다.                                                   | `collector/core/control_auth.py`                                                                                                      |
| 6    | L-2 예외 메시지 노출      | 라우트 응답 47곳의 `str(e)`를 `safe_error_message()`로 교체했습니다. 상세 내용은 로그에만 남습니다.                                                                                | `app/core/utils/response_utils.py` 및 라우트 22개 파일                                                                                |
| 6    | L-3 캐시 키 해시          | REGTECH 인증 캐시 키를 내장 `hash()`에서 프로세스별 난수 키를 사용하는 HMAC-SHA256으로 바꿨습니다.                                                                                 | `collector/core/regtech/auth.py`                                                                                                      |
| 6    | L-4 DB 제약               | 옥텟 범위를 검사하는 제약을 `blacklist_ips`와 `whitelist_ips`에 추가했습니다. 기존 행이 위반하면 `NOT VALID`로 남고 경고를 출력합니다.                                             | `postgres/migrations/010_tighten_ip_format_constraints.sql`                                                                           |
| 6    | L-5 CSV 수식 접두사       | 탭과 캐리지리턴을 무력화 대상에 추가했습니다.                                                                                                                                      | `app/core/utils/csv_security.py`                                                                                                      |
| 6    | L-6 무력화된 XFF 참조     | `X-Forwarded-For` 직접 읽기를 제거하고 `remote_addr`를 사용합니다. 신뢰 프록시 미들웨어가 해당 헤더를 이미 제거합니다.                                                             | `app/core/routes/api/fortinet/utils.py`                                                                                               |
| 6    | L-7 PBKDF2 반복 횟수      | 100,000회에서 600,000회로 올렸습니다. 기존 암호문을 계속 읽도록 앱과 수집기 네 곳 모두 새 키로 암호화하고 구 키로도 복호화하는 `MultiFernet`을 사용합니다.                         | `app/core/services/credential/crypto.py`, `app/core/utils/encryption.py`, `collector/config.py`, `collector/core/database/service.py` |
| 6    | L-8 관리자 비밀번호 평문  | 설치 프로그램이 최초 로그인 후 비밀번호 교체와 `.env` 초기값 무효화를 안내합니다. 아래 운영 절차를 참고하십시오.                                                                   | `deploy/install.sh`                                                                                                                   |

## 운영 절차

### Cloudflare 동기화 확인

연결 테스트 성공은 동기화 동작의 근거가 아닙니다. 보고서 지적대로 테스트는 자격증명만 확인합니다. 배포 후에는 다음을 확인하십시오.

1. 앱 컨테이너 로그에 `PostgreSQL LISTEN started: blacklist_changes`가 있는지 확인합니다.
2. 블랙리스트를 변경한 뒤 로그에 `Cloudflare push completed`가 남는지 확인합니다.
3. Cloudflare 콘솔에서 리스트의 실제 항목 수와 갱신 시각을 확인합니다.

`Cloudflare sync blocked` 로그는 증감률 가드가 동작한 것입니다. 데이터가 정상임을 확인한 뒤 다시 변경을 발생시키면 동기화가 재개됩니다. 자격증명이 없으면 리스너는 60초마다 재확인만 하며 아무것도 전송하지 않습니다.

### 관리자 비밀번호 교체

`ADMIN_PASSWORD`는 관리자 계정을 최초 생성할 때만 쓰입니다. 계정이 DB에 생성된 뒤에는 DB의 bcrypt 해시가 기준이며 환경변수 값으로 되돌아가지 않습니다. 다만 값 자체는 `.env`와 컨테이너 환경변수에 남아 `docker inspect`로 조회되므로, 설치 후 다음을 수행하십시오.

1. 최초 비밀번호로 로그인한 뒤 대시보드에서 비밀번호를 교체합니다.
2. `.env`의 `ADMIN_PASSWORD`를 사용하지 않는 새 난수 값으로 덮어씁니다.
3. 설치 프로그램이 만든 초기 비밀번호 파일을 비밀번호 관리자에 옮기고 삭제합니다.

### 마이그레이션

마이그레이션 009와 010은 `configure-runtime-roles.sh`가 적용합니다. 이 스크립트는 최초 `initdb`와 설치 프로그램 실행 시 동작하며, 단순 재시작에서는 실행되지 않습니다. 기존 설치에 반영하려면 설치 프로그램을 다시 실행해야 합니다.

기존 데이터에 옥텟 범위를 위반하는 IP가 있으면 010은 제약을 `NOT VALID` 상태로 남기고 위반 건수를 경고로 출력합니다. 이 경우 해당 행을 정리한 뒤 `ALTER TABLE ... VALIDATE CONSTRAINT`를 수동으로 실행하십시오.

## 후속 조치 (같은 날 추가 반영)

최초 반영 시 범위 밖으로 미뤘던 항목을 모두 닫았습니다.

| 항목                | 조치                                                                                                                                                                                                                        | 반영 위치                                                           |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| 개발 서버 CSP 중복  | `next.config.ts`의 CSP를 개발 서버에서만 내보내도록 한정했습니다. 운영에서 이 헤더가 적용되면 nonce 없는 정책이 `server.js`의 nonce 정책을 덮어써 인라인 스크립트가 차단되므로, 운영 CSP의 소유자를 한 곳으로 고정했습니다. | `frontend/next.config.ts`, `frontend/__tests__/next-config.test.ts` |
| 죽은 설정 화면 링크 | 레거시 템플릿의 `/settings` 링크를 제거했습니다. 해당 라우트는 이번 조치로 삭제되었습니다.                                                                                                                                  | `app/templates/collection.html`, `app/templates/integrations.html`  |
| `npm audit`         | 취약점 5건을 모두 해소했습니다(0건). `next` 15.5.21 → 15.5.25(미인증 RCE 2건), `sharp` 0.35.3 → 0.35.4(libheif), `vitest`/`@vitest/coverage-v8` 4.1.8 → 4.1.11(경로 탐색).                                                  | `frontend/package.json`, `frontend/package-lock.json`               |
| `pip-audit`         | `app/requirements.txt`, `app/requirements-dev.txt`, `collector/requirements.txt`에 실행했고 알려진 취약점은 없었습니다.                                                                                                     | 변경 없음                                                           |

`sharp`가 취약 버전에 머물러 있던 원인은 `package.json`의 `overrides`가 `next.sharp`를 `0.35.3`으로 **고정**하고 있었기 때문입니다. 고정값을 올려야 해소되므로, 이후 `sharp` 관련 권고가 나오면 이 `overrides` 항목을 먼저 확인하십시오.

## 조치하지 않은 항목

- Flask 응답 CSP(`app/core/app.py`)는 변경하지 않았습니다. 확인 결과 이미 `script-src 'self'`로 인라인 스크립트를 허용하지 않으며, `unsafe-inline`은 `style-src`에만 있습니다. 이번 보고서 M-4의 지적 대상은 프론트엔드 응답 헤더였고, 그쪽은 nonce로 처리했습니다.
