# MULTI-SOURCE COLLECTOR KNOWLEDGE BASE

## OVERVIEW

Async multi-source ingestion framework. Aggregates threat data from 14 source types.

## FILES

| File           | LOC | Role                                                           |
| -------------- | --- | -------------------------------------------------------------- |
| `collector.py` | 410 | async orchestration, source registry, `asyncio.gather` + merge |
| `parsers.py`   | 200 | text/JSON parser mixins for different feed formats             |
| `models.py`    | 47  | `SourceType` enum (14 types), `SourceConfig` dataclass         |

## SOURCE TYPES

14 types from `REGTECH` through `JSON_API`. Seven default sources are configured with priorities and rate limits.

## CONVENTIONS

- Async I/O only (`aiohttp`).
- Bounded concurrency via semaphore (default 5).
- Normalize + dedupe before persistence.
- Parser mixins composed into collector class.

## ANTI-PATTERNS

- Synchronous HTTP calls (use `aiohttp`).
- Unbounded concurrency (always use semaphore).
- Persisting before normalization/deduplication.

## CODE MAP

| Symbol                 | Type      | Location       | Refs | Role                                         |
| ---------------------- | --------- | -------------- | ---- | -------------------------------------------- |
| `MultiSourceCollector` | class     | `collector.py` | high | async orchestration + `asyncio.gather` merge |
| `SourceType`           | enum      | `models.py:*`  | high | 14 source type definitions                   |
| `SourceConfig`         | dataclass | `models.py:*`  | med  | per-source rate limit + priority config      |
