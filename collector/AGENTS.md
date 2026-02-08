# COLLECTOR KNOWLEDGE BASE

**Generated:** 2026-02-08
**Commit:** 923a8ce | **Version:** 3.5.36
**Role:** ETL 서비스 (데이터 수집)
**Parent:** [../AGENTS.md](../AGENTS.md)

## OVERVIEW

독립 ETL 서비스. 외부 소스에서 블랙리스트 수집, 정규화, DB 저장.
`app/`과 완전 분리 — 별도 DB 풀, 별도 프로세스. Port 8545.

## STRUCTURE

```
run_collector.py        # 진입점 (:8545)
config.py               # 환경 설정
scheduler.py            # APScheduler 기반 스케줄링
scheduler_api.py        # 수집 트리거 REST API
health_server.py        # K8s liveness/readiness
monitoring_scheduler.py # 모니터링 스케줄
core/                   # 수집 로직 (→ core/AGENTS.md)
```

## HOW TO: 새 수집 소스 추가

1. `core/` 에 수집기 클래스 생성 (`CollectorDatabase` DI)
2. `scheduler.py`에 스케줄 등록
3. (선택) `scheduler_api.py`에 `/api/force-collection/SOURCE` 추가

## ANTI-PATTERNS

| 금지 | 대안 | 이유 |
|------|------|------|
| `from app.* import` | 독립 구현 | 서비스 경계 위반 |
| `time.sleep()` 루프 | APScheduler | 메인 스레드 블로킹 |
| 무한 재시도 | Backoff + 최대 횟수 | 리소스 고갈 |
| 동기 HTTP 대량 호출 | `aiohttp` / ThreadPool | 성능 |
| Hardcoded URLs | 환경변수 | Docker 호환성 |

## KNOWN ISSUES

| 이슈 | 위치 | 심각도 |
|------|------|--------|
| Hardcoded app URL | `fortimanager_uploader.py:36,77` | CRITICAL |
| Magic numbers, hardcoded intervals | `core/regtech_collector.py` (961L) | HIGH |
| Mixed sync/async, 데드락 위험 | `core/multi_source_collector.py` (766L) | HIGH |
| `time.sleep()` 블로킹 | `scheduler.py` | MEDIUM |
| Single-stage Dockerfile | `Dockerfile` — Playwright 포함 bloat | MEDIUM |

## COMMUNICATION

```bash
# 수집 트리거
curl -X POST http://blacklist-collector:8545/api/force-collection/REGTECH
# 헬스체크
curl http://blacklist-collector:8545/health
```

## NOTES

- DB/Redis로만 `app/`과 통신. 코드 공유 없음.
- `app/core/collectors/`는 삭제됨 (8bcad163) — 이 서비스가 후속.
- 테스트: `tests/unit/collector/`, `tests/integration/collector/`
