# Blacklist Collector

독립적인 블랙리스트 IP 수집 ETL 서비스

## 개요

`blacklist-collector`는 REGTECH 및 Secudium/ISAP 소스에서 블랙리스트 IP를 자동으로 수집하는 독립 서비스입니다. 메인 애플리케이션(`app/`)과 분리되어 있어 수집 작업이 웹 서비스에 영향을 주지 않습니다.

## 주요 기능

- **REGTECH 통합**: 한국금융보안원(REGTECH) 포털 연동
- **Secudium/ISAP 통합**: SK쉰더스 Secudium 위협 정보 수집
- **자동 스케줄링**: APScheduler 기반 자동 수집
- **데이터베이스 통합**: PostgreSQL에 직접 저장
- **헬스체크**: 모니터링을 위한 REST API 제공
- **독립 실행**: `app/`과 DB/Redis로만 통신, 코드 공유 없음

## 서비스 구조

```
collector/
├── run_collector.py         # 메인 실행 스크립트 (Entry Point, :8545)
├── config.py                # 환경 설정
├── scheduler.py             # APScheduler 스케줄링 관리
├── scheduler_api.py         # 수집 트리거 REST API
├── health_server.py         # 헬스체크 서버
├── monitoring_scheduler.py  # 모니터링 스케줄
├── core/                    # 핵심 로직
│   ├── regtech/             # REGTECH 수집 패키지
│   ├── secudium/            # Secudium/ISAP 수집 패키지
│   ├── multi_source/        # 멀티소스 수집
│   └── database.py          # 수집기 데이터베이스 서비스
├── api/                     # 수집 상태 API
├── utils/                   # 유틸리티
├── Dockerfile               # 컨테이너 빌드
└── requirements.txt         # Python 의존성
```

## 환경 변수

### 필수 설정
```bash
# 데이터베이스
POSTGRES_HOST=blacklist-postgres
POSTGRES_PORT=5432
POSTGRES_DB=blacklist
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

# REGTECH 인증
REGTECH_ID=your_regtech_id
REGTECH_PW=your_regtech_password
REGTECH_BASE_URL=https://regtech.fsec.or.kr

# Secudium/ISAP 인증
SECUDIUM_API_KEY=your_api_key
SECUDIUM_BASE_URL=your_base_url
```

### 선택적 설정
```bash
COLLECTION_INTERVAL=3600    # 수집 간격 (초)
BATCH_SIZE=1000             # 배치 처리 크기
MAX_RETRY_ATTEMPTS=3        # 재시도 횟수
HEALTH_CHECK_PORT=8545      # 헬스체크 포트
LOG_LEVEL=INFO              # 로그 레벨
```

## API 엔드포인트

| 엔드포인트 | 설명 |
|------------|------|
| `GET /health` | 서비스 상태 확인 |
| `GET /status` | 상세 서비스 정보 및 통계 |
| `POST /trigger` | 수동 수집 작업 시작 |
| `POST /api/force-collection/REGTECH` | REGTECH 수집 강제 실행 |
| `POST /api/force-collection/SECUDIUM` | Secudium 수집 강제 실행 |
| `GET /metrics` | Prometheus 형식 메트릭 |
| `GET /config` | 현재 설정 정보 |

## Docker

### Docker Compose (개발)

```yaml
blacklist-collector:
  build: ./collector
  container_name: blacklist-collector
  network_mode: host
  volumes:
    - blacklist-collector-data:/app/data
  environment:
    POSTGRES_HOST: localhost
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    REGTECH_ID: ${REGTECH_ID}
    REGTECH_PW: ${REGTECH_PW}
  depends_on:
    - blacklist-postgres
    - blacklist-redis
  restart: unless-stopped
```

## 모니터링

```bash
# 상태 확인
curl http://localhost:8545/health

# 수집 통계
curl http://localhost:8545/status | jq

# 로그 확인
docker logs blacklist-collector --tail 100
```

## 데이터 흐름

1. **스케줄러**: 설정된 간격으로 수집 작업 시작
2. **인증**: REGTECH/Secudium 포털에 로그인
3. **데이터 수집**: API를 통해 블랙리스트 IP 데이터 조회
4. **데이터 처리**: 중복 제거 및 형식 변환
5. **데이터베이스 저장**: PostgreSQL에 배치 저장
6. **히스토리 기록**: 수집 결과 기록

## 버전 정보

- **Version**: 3.5.68
- **Python**: 3.11
- **Dependencies**: requirements.txt 참조
