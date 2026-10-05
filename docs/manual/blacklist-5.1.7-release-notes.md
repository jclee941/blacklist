# Blacklist 5.1.7 릴리스 노트

## 요약

Blacklist 5.1.7은 설치기의 재실행·업그레이드 결함과 프론트엔드 인증서 이름 검증 결함을 수정하고, Python 의존성과 CI 실행 환경을 정비한 패치입니다.

## 수정 사항

- **반복 업그레이드 실패:** 설치기를 두 번째로 재실행하거나 업그레이드하면 collector 볼륨 권한 설정 단계에서 `Permission denied`로 항상 실패하던 문제를 수정했습니다.
- **특정 IP 바인드 헬스체크:** `FRONTEND_BIND_ADDRESS`를 특정 IP로 지정하면 모든 서비스가 정상이어도 마지막 헬스체크가 실패하던 문제를 수정했습니다. 이제 설정한 주소로 확인합니다.
- **프론트엔드 인증서 이름 검증:** 프론트엔드 컨테이너가 시작할 때 인증서가 `FRONTEND_TLS_SERVER_NAME`을 포함하는지 실제로 확인합니다. `openssl -checkhost`/`-checkip`가 불일치에도 0을 반환해 다른 이름의 인증서로도 시작되던 문제와, hex 문자만으로 된 호스트 이름을 IP로 잘못 판단하던 문제를 수정했습니다.

## 의존성과 빌드

- PyJWT 2.15.1, cryptography 50.0.2, Werkzeug 3.1.9, gunicorn 26.2.0, pandas 3.0.6 등 Python minor/patch 업데이트 13건을 반영했습니다. numpy는 Python 3.12가 필요한 2.5 대신 2.4.6을 유지합니다.
- CI와 릴리스 빌드 러너를 `ubuntu-24.04`로 고정해, GitHub의 `ubuntu-latest` 전환(Ubuntu 26.04)이 서명된 릴리스 빌드에 영향을 주지 않게 했습니다.

## 업그레이드

- 기존 `/etc/blacklist/.env`, release keyring, 프론트엔드 인증서를 그대로 사용하므로 새 패키지 디렉터리에서 `sudo bash install.sh`만 실행하면 됩니다.
- 5.1.6 이하에서 두 번째 업그레이드부터 실패하던 설치본도 5.1.7 설치기로 업그레이드할 수 있습니다.

## Breaking Changes

- 없음. 5.1.6 설치기는 이미 배포 전에 인증서 이름을 같은 기준으로 검사하므로, 설치기로 배포한 환경에는 영향이 없습니다.
