# Blacklist 오프라인 패키지 문서

이 디렉터리의 문서는 인터넷에 연결되지 않은 설치 대상에서도 Blacklist를 설치하고 운영할 수 있도록 릴리즈 패키지에 함께 제공됩니다.

## 문서 목록

| 문서 | 용도 |
| --- | --- |
| `blacklist-offline-installation-guide.md` | 최초 설치, 무결성 확인, 업그레이드와 설치 검증 |
| `blacklist-operations-guide.md` | 서비스 상태, 로그, 재시작, 백업과 장애 확인 |
| `blacklist-offline-deployment-guide.pdf` | 배포 절차 PDF |
| `security-remediation-2026-07-28.md` | 정보보호 검토 원문과 조치 요구사항 |
| `security-remediation-checklist.md` | 취약점 항목별 이행 상태와 재현 명령 |
| `security-remediation-validation-report.md` | 무볼륨 설치 및 보안 E2E 검증 결과 |

## 중요 운영 원칙

- 설치와 업그레이드는 패키지 루트의 `install.sh`만 사용합니다.
- `/etc/blacklist/.env`와 Docker 볼륨을 백업 없이 삭제하지 않습니다.
- 외부 공개 포트는 HTTPS 443만 허용합니다.
- 관리자 비밀번호와 내부 암호화 키를 문서, 이슈, 로그에 기록하지 않습니다.
- `MANIFEST.sha256` 또는 이미지 체크섬 검증이 실패하면 설치를 진행하지 않습니다.
- 릴리스 공개키는 패키지에 포함하지 않습니다. 별도 인증 채널에서 공개키와 fingerprint를 확인한 뒤 호스트의 `/etc/blacklist/release-pubkey.gpg`에 등록합니다.
- 일반 설치와 업그레이드는 `MANIFEST.sha256.asc`를 호스트 keyring으로 필수 검증합니다.
- 최종 `.tar.gz.asc`는 압축 해제와 `install.sh` 실행 전에 검증하며, 내부 manifest 서명은 압축 해제 후 두 번째 신뢰 경계로 검증합니다.
