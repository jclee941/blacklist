# Blacklist Intelligence Platform

[![CI](https://github.com/qws941/blacklist/actions/workflows/ci.yml/badge.svg)](https://github.com/qws941/blacklist/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/qws941/blacklist)](https://github.com/qws941/blacklist/releases/latest)
[![Tests](https://img.shields.io/badge/Tests-2201%20passing-brightgreen)](#테스트)
[![Docker](https://img.shields.io/badge/Docker-5%20Services-blue)](#아키텍처)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

REGTECH (한국금융보안원) 위협 인텔리전스 데이터를 수집, 관리, 배포하는 IP 블랙리스트 플랫폼.
FortiGate 외부 커넥터 및 Cloudflare WAF와 연동하여 네트워크/엣지 레벨 차단을 자동화합니다.

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
| **2,201 자동화 테스트** | Backend (pytest 1,776), Frontend (vitest 425), E2E (Playwright) |

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

### Cloudflare WAF (운영 중)

서버에서 Cloudflare Lists API로 IP를 자동 push합니다.
Enterprise 플랜 (500K IP 한도). DB 변경 시 LISTEN/NOTIFY로 실시간 감지 후 bulk replace.

| 항목 | 값 |
|------|-----|
| API | PUT /accounts/{id}/rules/lists/{list_id}/items |
| 인증 | Settings UI에서 관리 (DB 암호화 저장) |
| 방식 | 전체 교체 (bulk replace, 비동기) |
| 한도 | Enterprise 500K items |

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
gh release download --repo qws941/blacklist
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
| 백엔드 Unit (App) | pytest | 1,486 |
| 백엔드 Unit (Collector) | pytest | 290 |
| 프론트엔드 Unit | Vitest | 425 |
| E2E | Playwright | Chromium + WebKit |
| **합계** | | **2,201** |

```bash
make test                   # 전체 테스트
make test-backend-unit      # 백엔드 전용 (pytest)
make test-collector-unit    # 수집기 전용
make test-frontend          # 프론트엔드 전용 (vitest)
make test-e2e               # E2E (Playwright)
```

## API 엔드포인트

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /health` | 서비스 상태 확인 |
| `GET /api/stats` | 대시보드 통계 |
| `GET /api/blacklist/list` | 블랙리스트 목록 (페이징) |
| `GET /api/collection/status` | 수집기 상태 |
| `GET /api/fortinet/threat-feed` | FortiGate 위협 피드 (공개) |
| `GET /api/fortinet/json-connector` | FortiGate JSON 커넥터 (공개) |
| `PUT /api/collection/credentials/{source}` | 자격증명 저장 |
| `POST /api/collection/credentials/{source}/test` | 연결 테스트 |

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

[릴리즈](https://github.com/qws941/blacklist/releases) · [변경 이력](CHANGELOG.md)
