# Blacklist 5.1.1 릴리즈 노트

5.1.1은 인증, 데이터베이스, 외부 연동, 컨테이너 격리와 오프라인 배포 공급망을 강화하는 보안 패치입니다.

## 주요 변경 사항

| 영역 | 변경 내용 |
| --- | --- |
| 관리자 인증 | 로그인 속도 제한과 계정 잠금, bcrypt 전환, JWT `jti` 폐기 및 사용자별 세션 버전을 적용했습니다. |
| 세션 종료 | UI 로그아웃이 서버 토큰을 폐기하며, 비밀번호 변경 시 기존 세션이 모두 무효화됩니다. |
| Redis | 인증 폐기 상태를 AOF/RDB로 유지하고 `noeviction` 정책을 적용했습니다. |
| 데이터베이스 | 연결 풀 반환 경로를 통합하고 기존 볼륨에 IP 상태 컬럼과 upsert 고유 인덱스를 자동 적용합니다. |
| API 입력 | IP, batch, CSV 입력 크기와 형식을 검증하고 CSV formula injection 및 cache stale-data 경로를 차단했습니다. |
| FortiGate | 허용 네트워크, 등록 장비, CA와 SSH `known_hosts` 검증을 필수화했습니다. |
| 프론트엔드 | 정적 파일 path traversal, 신뢰되지 않은 forwarding header, 공개 metrics proxy를 제거했습니다. |
| 컨테이너 | 외부 포트를 HTTPS 443 하나로 제한하고 non-root 실행, 내부 TLS, SCRAM과 capability 축소를 적용했습니다. |
| 오프라인 릴리스 | 내부 manifest와 최종 tarball을 fingerprint 고정 GPG 키로 서명하며, 압축 해제 전에 tarball 서명을 검증합니다. |

## 업그레이드 주의사항

- 기존 JWT에는 세션 버전 claim이 없으므로 업그레이드 후 관리자는 다시 로그인해야 합니다.
- `FLASK_SECRET_KEY`, `JWT_SECRET_KEY`, `SETTINGS_ENCRYPTION_KEY`를 서로 다른 값으로 설정해야 합니다.
- FortiGate 연동 환경은 `FORTIGATE_ALLOWED_NETWORKS`, CA 파일과 SSH `known_hosts`를 준비해야 합니다.
- 오프라인 설치 호스트는 별도 인증 채널로 받은 릴리스 공개키를 `/etc/blacklist/release-pubkey.gpg`에 등록해야 합니다.
- 기존 PostgreSQL 볼륨은 앱 시작 시 idempotent 스키마 정렬을 수행합니다. 중복 IP 데이터가 있으면 고유 인덱스 생성이 안전하게 실패하므로 업그레이드 전에 중복을 정리해야 합니다.

## 확인 결과

- Backend 단위 테스트: 1,737개 통과, coverage 85.69%
- Backend 통합 테스트: 6개 통과
- Collector 단위 테스트: 353개 통과
- Frontend 단위 테스트: 476개 통과
- Chromium E2E: 209개 통과, 1개 조건부 skip
- Frontend typecheck, lint, production build: 통과
- Docker Compose 5개 서비스 health 및 HTTPS 실사용 검증: 통과
- 최종 tarball 서명 검증과 변조 거부: 통과
- 독립 보안 재검토: SHIP
