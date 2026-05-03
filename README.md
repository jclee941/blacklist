# Blacklist Intelligence Platform

[![CI](https://github.com/jclee941/blacklist/actions/workflows/ci.yml/badge.svg)](https://github.com/jclee941/blacklist/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/jclee941/blacklist)](https://github.com/jclee941/blacklist/releases/latest)
[![Tests](https://img.shields.io/badge/Tests-2175%20passing-brightgreen)](#테스트)
[![Docker](https://img.shields.io/badge/Docker-5%20Services-blue)](#아키텍처)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

REGTECH (한국금융보안원) 위협 인텔리전스 데이터를 수집, 관리, 배포하는 IP 블랙리스트 플랫폼.
FortiGate 외부 커넥터 및 Cloudflare WAF와 연동하여 네트워크/엣지 레벨 차단을 자동화합니다.

> **v3.6.9 BREAKING**: FortiManager 통합이 완전히 제거되었습니다. FortiGate Threat Feed (pull) 또는 Cloudflare WAF (push)를 사용하세요.

## 데이터 흐름

```
┌─────────────┐
│   REGTECH   │
│ (자동 수집)  │
└──────┬──────┘
       │
┌──────▼──────┐
│  Collector  │ :8545
│ (Python ETL)│
└──────┬──────┘
       │
┌──────▼──────┐     ┌────────┐
│ PostgreSQL  │────▶│ Redis  │
│ (15 tables) │     │(Cache) │
└──────┬──────┘     └────────┘
       │
┌──────▼──────┐
│  Flask API  │ :2542
│(Threat Feed)│
└───┬─────┬───┘
    │     │
┌───▼──┐ ┌▼───────────┐
│Forti │ │ Cloudflare  │
│Gate  │ │  WAF (push) │
│(pull)│ │             │
└──────┘ └─────────────┘
```

## 주요 기능

| 기능 | 설명 |
|------|------|
| **자동 수집** | REGTECH 포털에서 위협 IP를 스케줄링 기반으로 자동 수집 |
| **실시간 대시보드** | Next.js 15 기반 분석 대시보드 (통계, 추이, 필터링) |
| **FortiGate 연동** | Threat Feed API를 통한 FortiGate 외부 커넥터 연동 (pull 방식) |
| **Cloudflare WAF** | Lists API를 통한 IP 자동 push (Enterprise, 500K 한도) |
| **오프라인 배포** | 에어갭 환경을 위한 Docker 번들 배포 지원 |
| **자격증명 암호화** | AES-256-GCM 기반 DB 암호화 저장 (Settings UI 관리) |
| **2,175 자동화 테스트** | Backend (pytest 1,754), Frontend (vitest 421), E2E (Playwright) |

## 아키텍처

| 서비스 | 기술 스택 | 포트 | 볼륨 |
|--------|----------|------|------|
| `blacklist-frontend` | Next.js 15 (standalone, SSL 내장) | 443 | — |
| `blacklist-app` | Flask API (Raw SQL, 수동 DI) | 2542 | `blacklist-app-data` |
| `blacklist-collector` | Python 3.11 ETL | 8545 | `blacklist-collector-data` |
| `blacklist-postgres` | PostgreSQL 15 | 5432 | `blacklist-pgdata` |
| `blacklist-redis` | Redis 7 Alpine | 6379 | `blacklist-redis-data` |

모든 서비스는 `network_mode: host`와 Docker named volume을 사용합니다.

## 연동

### FortiGate (운영 중)

FortiGate 장비가 서버의 공개 Threat Feed 엔드포인트를 폴링하여 차단 IP를 가져갑니다.
인증 불필요 — FortiGate 7.2+ 외부 커넥터와 호환됩니다.

| 엔드포인트 | 형식 | 설명 |
|-----------|------|------|
| `GET /api/fortinet/threat-feed` | JSON / Text | IP 블록리스트 (snapshot/add/remove) |
| `GET /api/fortinet/json-connector` | JSON | IP + 메타데이터 (위험도, 국가, 신뢰도) |

### Cloudflare WAF

CloudflarePushService가 PostgreSQL LISTEN/NOTIFY로 블랙리스트 변경을 감지하고,
Cloudflare Lists API로 IP를 자동 push합니다. Enterprise 플랜 (500K IP 한도).

| 항목 | 값 |
|------|-----|
| 동기화 | DB 변경 감지 시 전체 교체 (PUT bulk replace, 비동기) |
| 인증 | Settings > Cloudflare 탭에서 관리 (DB 암호화 저장) |
| 폴링 | operation_id 반환 후 completed/failed까지 polling |
| 한도 | Enterprise 500K items across all lists |

## 빠른 시작

### 개발 환경

```bash
make dev          # 전체 서비스 시작 (핫 리로드)
make test         # 전체 테스트 실행 (백엔드 + 프론트엔드)
make logs         # 로그 확인
make down         # 서비스 종료
```

### 오프라인 설치

```bash
gh release download --repo jclee941/blacklist
tar -xzf blacklist-*.tar.gz && ./install.sh
```

## 프로젝트 구조

```
blacklist/
├── app/                    # Flask API (수동 DI, Raw SQL)          :2542
│   ├── core/services/      # 15개 서비스 (ServiceFactory DI)
│   ├── core/routes/        # REST API + 웹 관리자
│   └── core/auth/          # JWT 인증
├── collector/              # ETL 서비스 (독립 프로세스)            :8545
│   └── core/               # REGTECH 수집기
├── frontend/               # Next.js 15 대시보드                  :443
│   ├── app/                # App Router 페이지
│   ├── lib/api.ts          # API 클라이언트
│   └── e2e/                # Playwright E2E 테스트
├── deploy/
│   ├── docker-compose.yml  # 개발용 Compose
│   └── base.yml            # 공통 서비스 정의
├── postgres/migrations/    # Raw SQL 마이그레이션 (ORM 미사용)
└── tests/                  # 백엔드 테스트 (pytest)
```

## 테스트

| 유형 | 프레임워크 | 테스트 수 |
|------|-----------|----------|
| 백엔드 Unit (App) | pytest | 1,460 |
| 백엔드 Unit (Collector) | pytest | 290 |
| 백엔드 Integration | pytest | 4 |
| 프론트엔드 Unit | Vitest | 421 |
| E2E | Playwright | Chromium + WebKit |
| **합계** | | **2,175** |

```bash
make test                   # 전체 테스트
make test-backend-unit      # 백엔드 전용 (pytest)
make test-collector-unit    # 수집기 전용
make test-frontend          # 프론트엔드 전용 (vitest)
make test-e2e               # E2E (Playwright)
```

## API 엔드포인트

### 핵심 API

| Method | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET | `/health` | 서비스 헬스체크 |
| GET | `/api/stats` | 대시보드 통계 (총 IP 수, 소스별 현황, 추이) |
| GET | `/api/status` | 시스템 상태 (서비스, DB, Redis 연결) |

### 블랙리스트 관리

| Method | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET | `/api/blacklist/list` | 블랙리스트 목록 (페이징, 필터링) |
| GET | `/api/blacklist/check` | IP 등록 여부 확인 |
| GET | `/api/blacklist/export-raw` | 전체 IP 내보내기 (CSV/JSON) |
| POST | `/api/blacklist/manual-add` | IP 수동 등록 |
| DELETE | `/api/blacklist/remove/{ip}` | IP 삭제 |
| POST | `/api/blacklist/batch/add` | 일괄 등록 |
| POST | `/api/blacklist/batch/remove` | 일괄 삭제 |

### IP 관리 (화이트리스트 포함)

| Method | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET | `/api/ip-management/unified` | 블랙+화이트 통합 목록 |
| GET | `/api/ip-management/statistics` | IP 관리 통계 |
| GET | `/api/ip-management/whitelist` | 화이트리스트 목록 |
| POST | `/api/ip-management/whitelist` | 화이트리스트 등록 |
| PUT | `/api/ip-management/whitelist/{id}` | 화이트리스트 수정 |
| DELETE | `/api/ip-management/whitelist/{id}` | 화이트리스트 삭제 |

### 수집 관리

| Method | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET | `/api/collection/status` | 수집기 상태 및 통계 |
| GET | `/api/collection/health` | 수집기 헬스체크 |
| POST | `/api/collection/trigger/{source}` | 수집 수동 트리거 |
| GET | `/api/collection/sources` | 등록된 소스 목록 |
| GET | `/api/collection/credentials` | 전체 자격증명 상태 |
| GET | `/api/collection/credentials/{source}` | 소스별 자격증명 조회 |
| PUT | `/api/collection/credentials/{source}` | 자격증명 저장 (AES-256 암호화) |
| POST | `/api/collection/credentials/{source}/test` | 연결 테스트 |

### FortiGate 연동 (공개, 인증 불필요)

| Method | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET | `/api/fortinet/threat-feed` | IP 블록리스트 (JSON/Text, snapshot 지원) |
| GET | `/api/fortinet/json-connector` | IP + 메타데이터 (위험도, 국가, 신뢰도) |
| GET | `/api/fortinet/active-ips` | 활성 차단 IP 목록 |
| GET | `/api/fortinet/blocklist` | FortiGate 형식 블록리스트 |
| GET | `/api/fortinet/config` | FortiGate 연동 설정 조회 |
| GET | `/api/fortinet/devices` | 등록된 FortiGate 장비 목록 |
| POST | `/api/fortinet/register` | FortiGate 장비 등록 |

### 분석

| Method | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET | `/api/analytics/overview` | 탐지 현황 개요 |
| GET | `/api/analytics/detection-timeline` | 시간대별 탐지 추이 |
| GET | `/api/analytics/real-time-log` | 실시간 탐지 로그 |

### 시스템 관리

| Method | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET | `/api/settings` | 전체 설정 조회 |
| GET | `/api/settings/grouped` | 그룹별 설정 조회 |
| PUT | `/api/settings/{key}` | 설정 값 변경 |
| PUT | `/api/settings/batch` | 설정 일괄 변경 |
| GET | `/api/logs` | 시스템 로그 |
| GET | `/api/system-stats` | 시스템 리소스 통계 |
| GET | `/api/database/schema` | DB 스키마 조회 |
| GET | `/api/monitoring/metrics` | Prometheus 메트릭 |
| GET | `/api/monitoring/cache/stats` | Redis 캐시 통계 |

### 인증

| Method | 엔드포인트 | 설명 |
|--------|-----------|------|
| POST | `/api/auth/login` | 로그인 (JWT 발급) |
| GET | `/api/auth/me` | 현재 사용자 정보 |
| GET | `/api/auth/verify` | 토큰 검증 |

## CI/CD 파이프라인

| 워크플로우 | 트리거 | 단계 |
|-----------|--------|------|
| `ci.yml` | Push/PR to master | Lint → Test → Build → Scan → E2E → Push |
| `release.yml` | 태그 `v*` | Build → Package → GitHub Release → GHCR |

## 문서

| 문서 | 경로 |
|------|------|
| **문서 허브** | [`docs/README.md`](docs/README.md) |
| 개발자 가이드 | [`AGENTS.md`](AGENTS.md) |
| 시스템 아키텍처 | [`docs/wiki/Architecture.md`](docs/wiki/Architecture.md) |
| API 레퍼런스 | [`docs/wiki/API-Reference.md`](docs/wiki/API-Reference.md) |
| 배포 가이드 | [`docs/wiki/Deployment-Guide.md`](docs/wiki/Deployment-Guide.md) |

## 버전

**v3.6.9** (2026년 4월) — Production Stable

### 최근 주요 변경 (v3.6.9)

- **BREAKING**: FortiManager 통합 완전 제거 — FortiGate Threat Feed 또는 Cloudflare WAF 사용
- 500+ LOC 파일을 모듈로 분할 (app/, collector/)
- Dead 패키지 정리: Flask-Login, marshmallow, jsonschema, xlrd 제거
- 중복 라우트 정리: `/blacklist/list` alias, BACKEND_API_URL legacy 제거
- 모든 Dockerfile 보안 업그레이드 적용
- Redis 네임스페이스 충돌 및 테스트 인프라 안정화

[릴리즈](https://github.com/jclee941/blacklist/releases) · [변경 이력](CHANGELOG.md)


<!-- LLM review probe 1777811213 — auto-removed after verification -->
