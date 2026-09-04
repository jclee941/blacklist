# Blacklist 5.1.2 릴리즈 노트

5.1.2는 5.1.1 사후 검토에서 발견된 CI, 인증 상태, TLS, proxy, 요청 크기와 배포 이미지 취약점을 교정하는 보안 패치입니다.

## Breaking Changes

- 외부 frontend는 기본적으로 `FRONTEND_TLS_MODE=provided`를 사용하며 실제 접속 FQDN 또는 IP와 일치하는 `FRONTEND_TLS_SERVER_NAME`, `server.crt`, `server.key`가 필요합니다.
- 명시적인 `self-signed` mode는 `127.0.0.1`에만 바인딩되는 개발 전용 경로입니다.
- 기존 관리자 JWT는 PostgreSQL 기반 session generation으로 전환되므로 업그레이드 후 다시 로그인해야 합니다.

## 주요 변경 사항

- 관리자 password hash와 session generation을 하나의 PostgreSQL 트랜잭션으로 갱신합니다.
- 인증 DB 장애 시 이전 `ADMIN_PASSWORD` 환경값으로 fallback하지 않고 fail closed 합니다.
- client `Forwarded`와 모든 `X-Forwarded-*` 헤더를 제거하고 실제 frontend TLS socket 기준으로 재생성합니다.
- frontend와 Flask에 1 MiB request body 상한을 적용해 chunked body를 포함한 공개 로그인 OOM 경로를 차단합니다.
- `nanoid`, `browserslist`를 안전 버전으로 갱신하고 Python runtime 이미지에서 pip/setuptools/wheel을 제거합니다.
- CI가 전체 push range를 검사하고 release metadata 변경 시 backend, collector, integration, E2E와 image scan을 모두 실행합니다.
- 릴리스는 동일 이미지의 테스트·Trivy scan·E2E·서명 성공 후에만 GitHub Release와 GHCR을 게시합니다.
- GitHub Release에 전체 릴리스 노트, 공개키와 fingerprint를 함께 게시합니다.

## 업그레이드

1. 별도 인증 채널의 fingerprint와 `blacklist-release-signing-key-v1.fingerprint`를 비교합니다.
2. `FRONTEND_TLS_MODE=provided`, `FRONTEND_TLS_SERVER_NAME`, 외부 인증서와 개인키를 준비합니다.
3. 새 tarball의 detached signature와 SHA-256을 압축 해제 전에 검증합니다.
4. 기존 `/etc/blacklist/.env`, release keyring, Docker 볼륨을 유지한 채 installer를 실행합니다.

## 검증 결과

- Backend 단위 테스트: 1,756개 통과, coverage 85.53%
- Backend 통합 테스트: 6개 통과
- Collector 단위 테스트: 353개 통과
- Frontend 단위 테스트: 477개 통과
- Chromium E2E: 209개 통과, 1개 조건부 skip
- Frontend typecheck, lint, production build: 통과
- 5개 Docker 이미지 HIGH/CRITICAL Trivy scan: 통과
- WARP 경유 REGTECH 실인증과 20페이지 수집: 통과
- REGTECH 1,000개 항목 수집, 중복 정리 후 968개 IP와 성공 이력 DB 저장 확인
- GitHub Release는 exact-tag test, E2E, Trivy, package/sign gate가 모두 성공한 경우에만 게시
