# MULTI-SOURCE COLLECTOR KNOWLEDGE BASE

**Generated:** 2026-02-27 00:00 Asia/Seoul
**Commit:** cd16ec1
**Branch:** master | **Version:** 3.6.8

## OVERVIEW

Async multi-source ingestion framework. Aggregates threat data from 14 source types.

## FILES

| File           | LOC | Role                                                           |
| -------------- | --- | -------------------------------------------------------------- |
| `collector.py` | 408 | async orchestration, source registry, `asyncio.gather` + merge |
| `parsers.py`   | 200 | text/JSON parser mixins for different feed formats             |
| `models.py`    | 47  | `SourceType` enum (14 types), `SourceConfig` dataclass         |

## SOURCE TYPES

14 types from `REGTECH` through `JSON_API`. 6 default sources configured with priorities and rate limits.

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

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `MultiSourceCollector` | class | `collector.py:15` | high | async orchestration + `asyncio.gather` merge |
| `SourceType` | enum | `models.py:*` | high | 14 source type definitions |
| `SourceConfig` | dataclass | `models.py:*` | med | per-source rate limit + priority config |