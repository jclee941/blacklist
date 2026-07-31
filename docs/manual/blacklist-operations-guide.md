# Blacklist 운영 가이드

아래 명령은 압축을 푼 릴리즈 패키지 루트에서 실행합니다.

```bash
export BLACKLIST_ENV_FILE=/etc/blacklist/.env
```

## 1. 서비스 상태

```bash
sudo docker compose --env-file "$BLACKLIST_ENV_FILE" -f docker-compose.yml ps
curl --insecure --fail https://localhost/health
```

5개 서비스가 모두 healthy여야 합니다. 외부에서는 HTTPS 443만 접근 가능해야 합니다.

## 2. 로그 확인

```bash
sudo docker compose --env-file "$BLACKLIST_ENV_FILE" -f docker-compose.yml logs --since 30m blacklist-app
sudo docker compose --env-file "$BLACKLIST_ENV_FILE" -f docker-compose.yml logs --since 30m blacklist-collector
sudo docker compose --env-file "$BLACKLIST_ENV_FILE" -f docker-compose.yml logs --since 30m blacklist-frontend
```

로그를 공유하기 전에 토큰, 관리자 자격증명, 외부 시스템 계정이 포함되지 않았는지 확인합니다.

## 3. 서비스 재시작

전체 서비스를 재기동하려면 다음 명령을 사용합니다.

```bash
sudo docker compose --env-file "$BLACKLIST_ENV_FILE" -f docker-compose.yml up -d --pull never
```

단일 서비스를 재생성할 때는 의존 서비스를 불필요하게 교체하지 않습니다.

```bash
sudo docker compose --env-file "$BLACKLIST_ENV_FILE" -f docker-compose.yml up -d --pull never --no-deps --force-recreate blacklist-collector
```

## 4. 데이터베이스 백업

업그레이드나 호스트 작업 전 PostgreSQL과 `/etc/blacklist`를 함께 백업합니다.

```bash
sudo docker exec blacklist-postgres sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' \
  > blacklist-postgres.dump
sudo tar -czf blacklist-host-config.tar.gz -C /etc blacklist
```

백업 파일에는 민감정보가 포함되므로 암호화하고 접근 권한을 제한합니다.

## 5. 인증 확인

```bash
curl --insecure --output /dev/null --write-out '%{http_code}\n' https://localhost/api/auth/me
```

토큰 없이 실행한 결과는 401이어야 합니다. 로그인 자격증명과 JWT를 명령 기록이나 운영 문서에 직접 입력하지 않습니다.

## 6. WARP 상태 확인

```bash
sudo docker exec blacklist-collector sh -c \
  'printf "WARP_ENABLED=%s\nWARP_PROXY_URL=%s\n" "$WARP_ENABLED" "$WARP_PROXY_URL"'
```

`WARP_ENABLED=true`인 경우 Collector에서 설정된 프록시 URL로 실제 연결되는지 확인합니다. 호스트에서만 연결되고 Docker 브리지에서 실패하면 프록시를 비활성화하거나 Docker gateway에만 접근 가능한 릴레이를 구성합니다.

## 7. 장애 대응 순서

1. `sudo docker compose --env-file "$BLACKLIST_ENV_FILE" -f docker-compose.yml ps`에서 unhealthy 또는 exited 서비스를 확인합니다.
2. 해당 서비스와 직접 의존 서비스의 최근 로그를 확인합니다.
3. `/health`와 내부 TLS 인증서 마운트 상태를 확인합니다.
4. 디스크 여유 공간과 Docker daemon 상태를 확인합니다.
5. 설정 또는 이미지가 손상됐으면 같은 버전의 검증된 오프라인 패키지로 `install.sh`를 다시 실행합니다.

문제 해결을 위해 `/etc/blacklist/.env`나 데이터 볼륨을 삭제하지 않습니다.
