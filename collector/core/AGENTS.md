# COLLECTOR CORE KNOWLEDGE BASE

**Generated:** 2026-02-08
**Commit:** 923a8ce | **Version:** 3.5.36
**Parent:** [../AGENTS.md](../AGENTS.md)

## OVERVIEW

핵심 ETL 파이프라인. 모듈형 파싱 + DB 기반 Rate Limiting + 데이터 정규화.

## STRUCTURE

```
core/
├── regtech_collector.py      # 메인 ETL (961L ⚠️ HIGH complexity)
├── regtech_parsers.py        # HTML/JSON 파싱 모듈
├── regtech_excel.py          # Excel/pandas 추출
├── multi_source_collector.py # 10+ 외부 피드 async (766L ⚠️)
├── database.py               # 독립 DB 풀 (maxconn=20)
├── authentication.py         # Fernet 자격증명 복호화
└── data_normalizer.py        # IP 형식 표준화
```

## HOW TO: 새 파서 추가

1. `regtech_parsers.py`에 파서 함수 작성 (`parse_X(html) -> list[dict]`)
2. `regtech_collector.py`에서 import 후 `_collect_X()` 메서드에서 호출
3. `ON CONFLICT DO UPDATE` 패턴으로 DB 저장

## CONVENTIONS

| 규약 | 내용 |
|------|------|
| 파싱 분리 | 파싱 → `regtech_parsers.py`, Excel → `regtech_excel.py` |
| Rate Limit | DB `SourceConfig` 기반 소스별 간격 |
| Idempotency | `ON CONFLICT DO UPDATE` 필수 |
| Error Recovery | Exponential Backoff (소스별 독립 실패) |

## ANTI-PATTERNS

| 금지 | 대안 |
|------|------|
| Collector 내 파싱 로직 | 별도 파서 모듈 |
| 직접 DB 쓰기 (트랜잭션 없이) | 트랜잭션 컨텍스트 사용 |
| 하드코딩 수집 간격 | DB `SourceConfig` 테이블 |
| 동기 HTTP 대량 호출 | `aiohttp` + semaphore |

## COMPLEXITY HOTSPOTS

| File | Lines | Issue |
|------|-------|-------|
| `regtech_collector.py` | 961 | Multi-stage auth, JWT refresh, 40+ magic numbers |
| `multi_source_collector.py` | 766 | Mixed sync/async, semaphore contention |
