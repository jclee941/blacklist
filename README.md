아래는 제공하신 프로젝트 정보를 바탕으로 작성한 완전한 `README.md`입니다. 기존에 작성하신 내용의 톤과 형식을 유지하면서 설치, 사용법, 프로젝트 구조, 테스트, 기여 가이드 등을 자연스럽게 연결했습니다.

```markdown
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
| `blacklist-collector` | Python ETL Scheduler / Parser | 8545 | `blacklist-collector-data` |
| `blacklist-postgres` | PostgreSQL 15 | 5432 | `blacklist-postgres-data` |
| `blacklist-redis` | Redis 7 (캐싱/메트릭 버퍼) | 6379 | — |

## 설치 요구사항

- **Docker** & **Docker Compose** (v2 이상 권장)
- **Make** (GNU Make)
- **Python** 3.11+ (로컬 개발 및 테스트 실행 시)
- **Node.js** 20+ (프론트엔드 Git Hooks 설치 시)

## 빠른 시작

### 1. 저장소 클론 및 환경 설정

```bash
git clone https://github.com/jclee941/blacklist.git
cd blacklist
cp deploy/.env.example deploy/.env
# deploy/.env 파일을 실제 환경에 맞게 수정
```

### 2. 개발 환경 실행 (Docker)

```bash
# 전체 개발 환경 빌드 및 실행 (hot reload)
make dev

# 기존 이미지 재사용 (더 빠름)
make dev-no-build

# 프로덕션 유사 환경
make dev-prod
```

실행 후 다음 주소로 접속할 수 있습니다.
- **애플리케이션**: https://localhost (또는 `https://localhost:${PORT:-2542}`)
- **API 문서**: `/api/docs` 또는 `/api/health`

### 3. Git Hooks 설정 (선택)

커밋 전 자동 린팅(Ruff, mypy), 시크릿 탐지, 그리고 Conventional Commit 검증을 활성화합니다.

```bash
make setup-hooks
```

## 사용법

### Makefile 주요 명령어

```bash
make help              # 전체 명령어 도움말
make dev               # 개발 환경 실행 (빌드 포함)
make dev-no-build      # 개발 환경 실행 (빌드 생략)
make down              # 전체 서비스 종료
make logs              # 실시간 로그 확인
make restart           # 서비스 재시작
make health            # 헬스체크
make clean             # 미사용 Docker 리소스 정리
```

### 백엔드 테스트 실행

프로젝트는 `pytest`를 사용하며, `pyproject.toml`에 설정이 중앙 관리되어 있습니다.

```bash
# 전체 테스트 실행
pytest

# 마커별 실행
pytest -m unit         # 유닛 테스트 (외부 의존성 없음)
pytest -m integration  # 통합 테스트 (DB/서비스 필요)
pytest -m security     # 보안 관련 테스트
pytest -m db           # 데이터베이스 테스트
pytest -m api          # API 엔드포인트 테스트

# 커버리지 포함
pytest --cov=app --cov-report=term-missing
```

### 코드 검증 (로컬)

```bash
# 린트 (Ruff)
ruff check app tests

# 타입 검사 (mypy)
mypy app

# 전체 검증 파이프라인
make verify-all
```

## 프로젝트 구조

```
/
├── AGENTS.md              # AI 에이전트 컨텍스트 가이드
├── CHANGELOG.md           # 버전별 변경 이력
├── CONTRIBUTING.md        # 기여 가이드
├── LICENSE                # MIT 라이선스
├── Makefile               # 개발/배포 자동화
├── OWNERS                 # 코드 오너십 정의
├── VERSION                # 현재 버전
├── pyproject.toml         # Python 프로젝트 설정 (pytest, ruff, mypy)
├── commitlint.config.js   # 커밋 메시지 린트 설정
├── mypy.ini               # 타입 체크 설정
├── deploy/                # Docker Compose, 환경 변수, 배포 매니페스트
└── tests/                 # 테스트 코드
    ├── integration/       # 통합 테스트 (외부 서비스 연동)
    ├── unit/              # 유닛 테스트
    │   ├── routes/        # API/웹 라우트 테스트
    │   ├── auth/          # 인증/인가 (JWT, 미들웨어, 데코레이터)
    │   ├── collector/     # 수집기 (파서, 스케줄러, 아카이브)
    │   ├── errors/        # 예외 핸들러 테스트
    │   └── utils/         # 유틸리티 (암호화, 캐시, DB 유틸)
    └── AGENTS.md          # 테스트 관련 AI 가이드
```

> **참고**: 실제 애플리케이션 소스(`app/`)는 별도로 관리되며, 위 구조는 테스트 및 설정 중심의 저장소 루트 구조입니다. 주요 도메인은 `blacklist`, `collection`, `fortinet`, `auth`, `analytics`, `dashboard` 등으로 구성되어 있습니다.

## 테스트 전략

총 **2,175개** 이상의 테스트가 자동화되어 있습니다.

| 유형 | 프레임워크 | 범위 |
|------|-----------|------|
| **Backend Unit** | pytest | 1,754개 — 비즈니스 로직, 라우트, 유틸리티 |
| **Frontend Unit** | Vitest | 421개 — 컴포넌트, 스토어, 유틸 |
| **E2E** | Playwright | 주요 사용자 시나리오 |

`pyproject.toml`에 정의된 마커를 활용하여 환경에 맞는 테스트만 선택적으로 실행할 수 있습니다.

```toml
markers = [
    "unit: Unit tests (no external dependencies)",
    "integration: Integration tests (require services)",
    "security: Security-related tests",
    "db: Database tests",
    "api: API endpoint tests",
]
```

## 기여 방법

이 프로젝트에 기여하고 싶으시다면 [`CONTRIBUTING.md`](CONTRIBUTING.md)를 먼저 읽어주세요.

1. **Issue 생성**: 버그 리포트 또는 기능 제안을 먼저 등록합니다.
2. **브랜치 생성**: `feature/`, `fix/`, `refactor/` 접두어를 사용합니다.
3. **커밋 메시지**: [Conventional Commits](https://www.conventionalcommits.org/) 규격을 준수합니다.
4. **코드 검증**: `make verify-all`을 통과해야 합니다.
5. **Pull Request**: `OWNERS`에 명시된 코드 오너의 리뷰를 받습니다.

## 라이선스

이 프로젝트는 [MIT License](LICENSE) 하에 배포됩니다.
```

이 `README.md`는 기존에 작성하신 데이터 흐름, 기능, 아키텍처 표와 자연스럽게 연결되며, 개발자가 clone 후 바로 개발 환경을 구성하고 테스트를 실행할 수 있도록 필요한 명령어와 구조를 모두 담고 있습니다. 추가로 특정 내부 도메인(`app/`) 구조나 프론트엔드 상세 내용이 필요하시면 해당 섹션만 확장하시면 됩니다.