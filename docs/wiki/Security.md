# 보안

## 개요

Blacklist Platform의 보안 아키텍처는 다음 계층으로 구성됩니다:

1. **인증/인가** — JWT 기반 (현재 비활성화)
2. **크레덴셜 암호화** — AES-256-GCM
3. **네트워크 보안** — HTTPS (Self-signed), Host 네트워크
4. **FortiGate 연동** — 위협 IP 방화벽 정책 자동 적용
5. **관리자 접근 제어** — Admin Key, Rate Limiting

---

## JWT 인증

### 구성

| 항목         | 값                                       |
| ------------ | ---------------------------------------- |
| **알고리즘** | HS256 (HMAC-SHA256)                      |
| **만료**     | 8시간 (환경변수 `JWT_EXPIRY_HOURS`)      |
| **시크릿**   | 환경변수 `JWT_SECRET_KEY`                |
| **저장**     | `localStorage` 키 `blacklist_auth_token` |

### 토큰 페이로드

```json
{
  "sub": "user_id",
  "role": "admin",
  "iat": 1700000000,
  "exp": 1700028800
}
```

### 파일 구조

| 파일                           | 역할                                                        |
| ------------------------------ | ----------------------------------------------------------- |
| `app/core/auth/jwt_service.py` | 토큰 생성/검증 (encode_token, decode_token, validate_token) |
| `app/core/auth/middleware.py`  | before_request 후크 (Authorization 헤더 검사)               |
| `app/core/auth/decorators.py`  | `@public` 데코레이터 (인증 면제)                            |

### 현재 상태

> **주의**: JWT 인증 미들웨어는 `app/core/app.py:156`에서 주석 처리되어 **비활성화** 상태입니다.  
> 모든 엔드포인트가 인증 없이 접근 가능합니다. 이는 내부 폐쇄망 배포 환경을 위한 의도적 설정입니다.

### `@public` 데코레이터

인증이 필요 없는 엔드포인트에 사용:

```python
from core.auth.decorators import public

@public
@bp.route("/health")
def health():
    return jsonify({"status": "ok"})
```

**기본 공개 엔드포인트**: `/health`, `/api/health`, `/metrics`, `/api/auth/login`, `/api/fortinet/*`

---

## 크레덴셜 암호화

### AES-256-GCM

수집 소스 (REGTECH)의 인증정보는 AES-256-GCM으로 암호화되어 DB에 저장됩니다.

| 항목           | 환경변수                    |
| -------------- | --------------------------- |
| 마스터 키      | `CREDENTIAL_MASTER_KEY`     |
| 암호화 키      | `CREDENTIAL_ENCRYPTION_KEY` |
| 솔트           | `ENCRYPTION_SALT`           |
| 설정 암호화 키 | `SETTINGS_ENCRYPTION_KEY`   |

### 키 생성

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 서비스 구조

```
SecureCredentialService (560줄)
├── encrypt(plaintext) → ciphertext + nonce + tag
├── decrypt(ciphertext, nonce, tag) → plaintext
├── store_credential(service_name, username, password)
└── get_credential(service_name) → decrypted credential
```

### 암호화 대상

| 테이블                         | 컬럼             | 설명               |
| ------------------------------ | ---------------- | ------------------ |
| `collection_credentials`       | `password`       | 수집 소스 비밀번호 |
| `settings` / `system_settings` | 암호화 플래그 값 | 민감한 설정 값     |

---

## 네트워크 보안

### HTTPS

- Frontend (Next.js)에 Self-signed SSL 인증서가 Docker 이미지에 내장
- 포트 443에서 HTTPS 서비스
- 내부 서비스 간 통신은 HTTP (Host 네트워크, 외부 노출 없음)

### Host Network

모든 서비스가 `network_mode: host`로 동작합니다:

- Docker 네트워크 격리 없음 (호스트 네트워크 공유)
- 서비스 간 `localhost`로 직접 통신
- 외부 노출 포트: **443** (Frontend) 만 공개 권장

### 방화벽 권장 설정

```
# 외부 허용
443/tcp  → Frontend (HTTPS)

# 내부 전용 (외부 차단)
2542/tcp → App (Flask API)
8545/tcp → Collector
5432/tcp → PostgreSQL
6379/tcp → Redis
```

---

## FortiGate 연동

### 환경변수

| 변수       | 기본값 | 설명                       |
| ---------- | ------ | -------------------------- |
| `FMG_HOST` | —      | FortiManager 호스트 (필수) |
| `FMG_USER` | admin  | FortiManager 사용자        |
| `FMG_PASS` | —      | FortiManager 비밀번호      |
| `FMG_ADOM` | root   | FortiManager ADOM          |

### Push 방식 (App → FortiManager)

1. App이 활성 IP 목록을 DB에서 조회
2. FortiManager에 JSON-RPC로 Address Object 생성
3. 방화벽 정책 할당
4. FortiManager가 FortiGate 장비에 정책 배포

### Pull 방식 (FortiGate → App)

1. FortiGate 장비가 주기적으로 App에 접속
2. `GET /api/fortinet/threat-feed` — Plain text IP 목록 반환
3. FortiGate가 자체 차단 목록에 반영

### 서비스

```
FortiManagerPushService (208줄)
├── Persistent LISTEN 커넥션
├── create_address_objects(ips)
├── assign_policy(objects)
└── push_to_device(device_id)
```

---

## 관리자 접근 제어

### Admin Key

DB 초기화 등 위험 작업에는 `X-Admin-Key` 헤더가 필요합니다:

```bash
curl -X POST http://localhost:2542/api/reset-database \
  -H "X-Admin-Key: ${ADMIN_RESET_KEY}"
```

### Rate Limiting

- Redis 기반 Rate Limiter
- 3개 인스턴스: REGTECH 인증, Auth 로그인, Flask-Limiter

### 관리자 계정

| 변수              | 기본값                 |
| ----------------- | ---------------------- |
| `ADMIN_USERNAME`  | **SET_ADMIN_USERNAME** |
| `ADMIN_PASSWORD`  | **SET_ADMIN_PASSWORD** |
| `ADMIN_RESET_KEY` | —                      |

> **주의**: 프로덕션 배포 전 `ADMIN_USERNAME`/`ADMIN_PASSWORD`를 반드시 강한 값으로 설정하세요.

---

## 환경변수 전체 목록

### 필수

| 변수                        | 설명                  |
| --------------------------- | --------------------- |
| `CREDENTIAL_MASTER_KEY`     | AES-256-GCM 마스터 키 |
| `SECRET_KEY`                | Flask 시크릿 키       |
| `CREDENTIAL_ENCRYPTION_KEY` | 크레덴셜 암호화 키    |
| `ENCRYPTION_SALT`           | 암호화 솔트           |

### 데이터베이스

| 변수                | 기본값             |
| ------------------- | ------------------ |
| `POSTGRES_HOST`     | blacklist-postgres |
| `POSTGRES_PORT`     | 5432               |
| `POSTGRES_DB`       | blacklist          |
| `POSTGRES_USER`     | postgres           |
| `POSTGRES_PASSWORD` | postgres           |
| `DATABASE_URL`      | — (우선순위 1)     |
| `POSTGRES_URL`      | — (우선순위 2)     |

### Redis

| 변수         | 기본값          |
| ------------ | --------------- |
| `REDIS_HOST` | blacklist-redis |
| `REDIS_PORT` | 6379            |

### 인증

| 변수               | 기본값                 |
| ------------------ | ---------------------- |
| `JWT_SECRET_KEY`   | —                      |
| `JWT_EXPIRY_HOURS` | 8                      |
| `DISABLE_JWT_AUTH` | —                      |
| `ADMIN_USERNAME`   | **SET_ADMIN_USERNAME** |
| `ADMIN_PASSWORD`   | **SET_ADMIN_PASSWORD** |
| `ADMIN_RESET_KEY`  | —                      |

### 수집

| 변수                      | 기본값                          |
| ------------------------- | ------------------------------- |
| `COLLECTOR_URL`           | http://blacklist-collector:8545 |
| `COLLECTION_INTERVAL`     | 3600                            |
| `DISABLE_AUTO_COLLECTION` | —                               |
| `REGTECH_BASE_URL`        | https://regtech.fsec.or.kr      |
| `REGTECH_ID`              | — (Deprecated, DB 우선)         |
| `REGTECH_PW`              | — (Deprecated, DB 우선)         |

### FortiGate

| 변수       | 기본값 |
| ---------- | ------ |
| `FMG_HOST` | —      |
| `FMG_USER` | admin  |
| `FMG_PASS` | —      |
| `FMG_ADOM` | root   |

### 시스템

| 변수                 | 기본값        |
| -------------------- | ------------- |
| `APP_PORT`           | 2542          |
| `LOG_LEVEL`          | INFO          |
| `LOG_DIR`            | /app/logs     |
| `FLASK_ENV`          | production    |
| `FLASK_DEBUG`        | false         |
| `ENVIRONMENT`        | production    |
| `SERVICE_NAME`       | blacklist-app |
| `DB_CONNECT_RETRIES` | 10            |
| `DB_BACKOFF_DELAY`   | 2.0           |

### 빌드

| 변수          | 설명           |
| ------------- | -------------- |
| `APP_VERSION` | 앱 버전        |
| `GIT_COMMIT`  | 커밋 해시      |
| `BUILD_DATE`  | 빌드 날짜      |
| `VERSION`     | 버전 (runtime) |
| `VCS_REF`     | VCS 레퍼런스   |
