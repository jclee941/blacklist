# Blacklist 오프라인 설치 가이드

## 1. 설치 전 요구사항

- Linux x86_64 호스트
- root 또는 sudo 권한
- Docker Engine과 Docker Compose v2
- HTTPS 443 포트 사용 가능
- Docker 데이터 디렉터리에 충분한 여유 공간
- `sha256sum`, `openssl`, `python3`, `curl`, `tar`, `gpg`, `gpgv`
- 조직의 인증된 별도 채널로 받은 릴리스 공개키와 40자리 fingerprint

현재 패키지는 Docker와 Compose가 이미 설치된 호스트를 기본 전제로 합니다. `prereqs/`에 Docker tarball과 Compose 바이너리가 모두 들어 있는 패키지만 베어 호스트 설치를 지원합니다.

## 2. 릴리스 공개키 등록

일반 설치와 업그레이드는 detached signature를 필수 검증합니다. 공개키는 패키지와 같은 채널에서 신뢰하지 말고, 조직의 변경관리 시스템이나 별도 인증된 채널로 받아 fingerprint를 독립적으로 대조합니다.

```bash
gpg --batch --dearmor --output release-pubkey.gpg release-public-key.asc
gpg --show-keys --with-colons release-public-key.asc | awk -F: '$1 == "fpr" { print $10; exit }'
sudo install -d -o root -g root -m 0755 /etc/blacklist
sudo install -o root -g root -m 0644 release-pubkey.gpg /etc/blacklist/release-pubkey.gpg
rm -f release-pubkey.gpg
```

출력된 fingerprint가 별도 인증 채널의 값과 정확히 일치하지 않으면 설치하지 않습니다. 패키지 내부 파일이나 릴리스와 함께 전달된 값만으로 fingerprint를 신뢰해서는 안 됩니다.

## 3. 최종 패키지 서명과 체크섬 확인

배포 시 받은 tarball, `.tar.gz.asc`, `.tar.gz.sha256` 파일을 같은 디렉터리에 둡니다. 압축을 풀거나 패키지 내부 스크립트를 실행하기 전에 호스트 keyring으로 최종 tarball 서명을 먼저 검증합니다.

```bash
gpgv --keyring /etc/blacklist/release-pubkey.gpg blacklist-5.0.0.tar.gz.asc blacklist-5.0.0.tar.gz
sha256sum -c blacklist-5.0.0.tar.gz.sha256
tar -xzf blacklist-5.0.0.tar.gz
cd blacklist-5.0.0
```

서명 또는 체크섬 검증이 실패하면 압축을 풀거나 설치기를 실행하지 않습니다.

## 4. 최초 설치

설치기는 호스트의 `/etc/blacklist/release-pubkey.gpg`로 패키지 매니페스트 서명을 검증하고 이미지 체크섬을 다시 확인한 뒤, 대상 호스트에서 관리자 비밀번호와 필수 암호화 키를 생성합니다.

```bash
sudo bash install.sh
```

관리자 비밀번호는 최초 설치 완료 시 한 번만 출력됩니다. 즉시 비밀번호 관리자에 저장하십시오. 원본은 권한이 제한된 `/etc/blacklist/.env`에 보관됩니다.

설치 전에 읽기 전용 검증을 별도로 실행하려면 먼저 대상 호스트 설정을 생성해야 합니다.

```bash
sudo bash install.sh --check-secrets
sudo bash install.sh --verify-only
sudo bash install.sh
```

`--verify-only`에서 설치와 동일한 서명 검증을 강제하려면 다음 명령을 사용합니다.

```bash
sudo bash install.sh --verify-only --require-signature
```

## 5. 설치 결과 확인

```bash
sudo docker compose --env-file /etc/blacklist/.env -f docker-compose.yml ps
curl --insecure --fail https://localhost/health
```

정상 상태는 다음과 같습니다.

- `blacklist-app`, `blacklist-collector`, `blacklist-frontend`, `blacklist-postgres`, `blacklist-redis`가 모두 healthy
- 호스트 공개 포트는 frontend의 443 하나
- PostgreSQL 5432, Redis 6379, Collector 8545, Flask 2542는 호스트에 미공개
- 미인증 보호 API는 HTTP 401 반환

## 6. WARP 프록시

설치기는 Docker 브리지에서 접근 가능한 호스트 40000 포트를 감지합니다. 접근 가능하면 Collector에 다음 값을 설정합니다.

```text
WARP_ENABLED=true
WARP_PROXY_URL=http://host.docker.internal:40000
```

WARP가 `127.0.0.1`에만 바인딩되어 Docker에서 접근할 수 없으면 안전하게 비활성화합니다. 운영자가 강제로 `true`로 바꾸기 전에 Collector 컨테이너에서 프록시 연결을 확인해야 합니다.

## 7. 업그레이드

새 패키지를 별도 디렉터리에 풀고 새 `install.sh`를 실행합니다. 기존 `/etc/blacklist/.env`, `/etc/blacklist/release-pubkey.gpg`, Docker 볼륨을 유지해야 저장된 자격증명을 계속 복호화하고 릴리스 서명을 검증할 수 있습니다.

```bash
cd blacklist-<새 버전>
sudo bash install.sh
```

`--stop-all-containers`는 호스트의 모든 컨테이너를 중지하므로 일반 설치와 업그레이드에서 사용하지 않습니다.
