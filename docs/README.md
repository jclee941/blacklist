# Blacklist Intelligence Platform — 문서 허브

**버전**: 3.6.9  
**최종 업데이트**: 2026-02

위협 인텔리전스 플랫폼(REGTECH)의 중앙 문서 인덱스입니다.

---

## 문서 구조

```
docs/
├── README.md                    ← 현재 문서 (중앙 허브)
├── wiki/                        # 운영 위키 (8페이지)
│   ├── Home.md                  # 위키 랜딩 페이지
│   ├── Architecture.md          # 시스템 아키텍처
│   ├── Service-Details.md       # 14개 서비스 상세
│   ├── Database-Schema.md       # DB 스키마 (15 테이블, 4 뷰)
│   ├── API-Reference.md         # REST API 레퍼런스
│   ├── Deployment-Guide.md      # 배포 가이드
│   ├── Security.md              # 보안 설계
│   └── XWiki-Compatibility.md   # XWiki 호환 가이드
├── deliverables/                # 납품 산출물 (공식 문서)
│   ├── index.md                 # 산출물 인덱스
│   └── 02-SYSTEM-DESIGN.md      # 시스템 설계서
├── architecture.drawio           # 아키텍처 다이어그램 (3탭)
├── CICD_PIPELINE.md             # CI/CD 파이프라인 설명
├── MONOREPO_STRUCTURE.md        # 모노레포 구조 설명
└── CLOUDFLARE_MIGRATION.md      # Cloudflare 마이그레이션 기록
```

---

## 빠른 참조

### 시스템 구성

| 서비스         | 기술 스택               | 포트 | 역할                          |
| -------------- | ----------------------- | ---- | ----------------------------- |
| **Frontend**   | Next.js 15 (App Router) | 443  | 대시보드 UI, SSL 내장         |
| **App**        | Flask (Raw SQL, DI)     | 2542 | REST API, 비즈니스 로직       |
| **Collector**  | Python 3.11 ETL         | 8545 | 위협 데이터 수집 파이프라인   |
| **PostgreSQL** | PostgreSQL 15           | 5432 | 영구 저장소 (15 테이블, 4 뷰) |
| **Redis**      | Redis 7                 | 6379 | 캐시, 메트릭                  |

### 핵심 명령어

```bash
make dev                     # 개발 환경 시작 (핫 리로드)
make build                   # 프로덕션 이미지 빌드
make test                    # 전체 테스트 (backend + frontend)
make test-backend-coverage   # pytest 커버리지 (≥80%)
make test-frontend-e2e       # Playwright E2E
make release TYPE=patch      # 릴리스 자동화
```

---

## 위키 (운영 문서)

운영 및 개발에 필요한 기술 문서입니다.

| 문서                                             | 설명                   | 주요 내용                                             |
| ------------------------------------------------ | ---------------------- | ----------------------------------------------------- |
| [시스템 아키텍처](wiki/Architecture.md)          | 전체 시스템 구성도     | 서비스 토폴로지, 데이터 흐름, 통신 패턴, Flask 초기화 |
| [서비스 상세](wiki/Service-Details.md)           | 14개 서비스 DI 구조    | ServiceFactory, 초기화 순서, 서비스별 책임            |
| [데이터베이스 스키마](wiki/Database-Schema.md)   | PostgreSQL 스키마 전체 | 15 테이블, 4 뷰, 인덱스, 마이그레이션                 |
| [API 레퍼런스](wiki/API-Reference.md)            | REST API 엔드포인트    | blacklist, collection, fortinet, ip-management        |
| [배포 가이드](wiki/Deployment-Guide.md)          | 배포 절차              | Docker Compose, 오프라인 설치, 환경 설정              |
| [보안](wiki/Security.md)                         | 보안 설계              | JWT (비활성), AES-256-GCM, 네트워크 보안              |
| [XWiki 호환 가이드](wiki/XWiki-Compatibility.md) | 위키 이식 기준         | 링크/테이블/코드블록/다이어그램 호환 규칙             |

---

## 산출물 (납품 문서)

공식 프로젝트 산출물입니다. [산출물 인덱스](deliverables/index.md) 참조.

| 문서 | 설명 |
|------|------|
| [01. 요구사항 명세서](deliverables/01-REQUIREMENTS-SPECIFICATION.md) | 기능/비기능 요구사항 33+19개 정의 |
| [02. 시스템 설계서](deliverables/02-SYSTEM-DESIGN.md) | 시스템 구성도, 설계 원칙, 컴포넌트 상세 |
| [03. API 레퍼런스](deliverables/03-API-REFERENCE.md) | REST API 48개 엔드포인트 상세 명세 |
| [04. 설치 가이드](deliverables/04-INSTALLATION-GUIDE.md) | 오프라인 패키지 설치·운영·복구 절차 |
| [05. 운영 가이드](deliverables/05-OPERATIONS-GUIDE.md) | 운영 절차, 모니터링, 장애대응 |
| [06. 장애 대응 매뉴얼](deliverables/06-RUNBOOK.md) | 장애대응, 정기점검, 백업/복구 |
| [07. 테스트 리포트](deliverables/07-TEST-REPORT.md) | 테스트 수행 결과 및 커버리지 |
| [08. 검증 체크리스트](deliverables/08-VERIFICATION-CHECKLIST.md) | 요구사항 검증 체크리스트 |
| [09. 환경 매트릭스](deliverables/09-ENVIRONMENT-MATRIX.md) | 환경별 설정, URL, 환경변수 |

---

## 개발자 가이드 (AGENTS.md)

자동 생성되는 계층형 코드베이스 지식 베이스입니다. 각 모듈의 구조, 패턴, 주의사항을 기술합니다.

| 문서                                                                                          | 범위                                 |
| --------------------------------------------------------------------------------------------- | ------------------------------------ |
| [루트 AGENTS.md](../AGENTS.md)                                                                | SSoT 동기화 (qws941/.github) — 거버넌스 정책 |
| [app/AGENTS.md](../app/AGENTS.md)                                                             | Flask API 앱 팩토리, 미들웨어        |
| [app/core/AGENTS.md](../app/core/AGENTS.md)                                                   | app/core 패키지 경계, 교차 모듈 계약 |
| [app/core/services/AGENTS.md](../app/core/services/AGENTS.md)                                 | ServiceFactory DI, 14개 서비스       |
| [app/core/routes/AGENTS.md](../app/core/routes/AGENTS.md)                                     | API/Web 라우트 계층 분리 규칙        |
| [app/core/routes/api/AGENTS.md](../app/core/routes/api/AGENTS.md)                             | API 라우트 패턴                      |
| [app/core/routes/api/ip_management/AGENTS.md](../app/core/routes/api/ip_management/AGENTS.md) | IP 관리 API repository/handler 계약  |
| [app/core/auth/AGENTS.md](../app/core/auth/AGENTS.md)                                         | JWT 인증                             |
| [app/core/database/AGENTS.md](../app/core/database/AGENTS.md)                                 | DB 연결, 복구                        |
| [app/core/monitoring/AGENTS.md](../app/core/monitoring/AGENTS.md)                             | Prometheus 메트릭                    |
| [app/core/exceptions/AGENTS.md](../app/core/exceptions/AGENTS.md)                             | RFC 7807 에러 계층                   |
| [app/core/utils/AGENTS.md](../app/core/utils/AGENTS.md)                                       | 유틸리티                             |
| [collector/AGENTS.md](../collector/AGENTS.md)                                                 | Collector 런타임                     |
| [collector/core/AGENTS.md](../collector/core/AGENTS.md)                                       | ETL 파이프라인 코어                  |
| [collector/core/regtech/AGENTS.md](../collector/core/regtech/AGENTS.md)                       | REGTECH 수집                         |
| [collector/core/multi_source/AGENTS.md](../collector/core/multi_source/AGENTS.md)             | 멀티소스 수집                        |
| [frontend/AGENTS.md](../frontend/AGENTS.md)                                                   | Next.js 대시보드                     |
| [frontend/lib/AGENTS.md](../frontend/lib/AGENTS.md)                                           | API 클라이언트                       |
| [deploy/AGENTS.md](../deploy/AGENTS.md)                                                       | 배포 구성                            |
| [tests/AGENTS.md](../tests/AGENTS.md)                                                         | 테스트                               |
| [postgres/AGENTS.md](../postgres/AGENTS.md)                                                   | DB 스키마, 마이그레이션              |

---

## 기타 문서

| 문서                                               | 설명                      |
| -------------------------------------------------- | ------------------------- |
| [CI/CD 파이프라인](CICD_PIPELINE.md)               | GitHub Actions 워크플로우 |
| [모노레포 구조](MONOREPO_STRUCTURE.md)             | 프로젝트 디렉토리 구조    |
| [Cloudflare 마이그레이션](CLOUDFLARE_MIGRATION.md) | 마이그레이션 기록         |

---

## 아키텍처 다이어그램

상세 아키텍처 다이어그램은 [시스템 아키텍처](wiki/Architecture.md) 문서에서 확인할 수 있습니다.

포함 다이어그램:

- **시스템 토폴로지** — 5개 서비스 구성도 및 외부 연동
- **ETL 수집 흐름** — REGTECH 데이터 수집 시퀀스
- **IP 조회 흐름** — 캐시 포함 조회 시퀀스
- **FortiGate 연동** — Push/Pull 방식 시퀀스
- **Flask 초기화** — Application Factory 순서도
- **서비스 DI 그래프** — ServiceFactory 의존성 그래프
- **Collector 파이프라인** — ETL 컴포넌트 구성도
- **배포 파이프라인** — CI/CD 워크플로우
- **ER 다이어그램** — 데이터베이스 관계도

> 원본 drawio 파일: [architecture.drawio](architecture.drawio)

### XWiki 호환성

XWiki 이식 기준과 예시는 전용 문서로 정리했습니다.

- 가이드: [wiki/XWiki-Compatibility.md](wiki/XWiki-Compatibility.md)
- 핵심 규칙: 표준 Markdown 링크, 단순 표 구조, 펜스 코드블록, Mermaid 매크로 전환

---

## 프로젝트 정보

- **저장소**: [github.com/qws941/blacklist](https://github.com/qws941/blacklist)
- **버전**: 3.6.9
- **라이선스**: MIT
- **릴리스**: [GitHub Releases](https://github.com/qws941/blacklist/releases)
- **변경 이력**: [CHANGELOG.md](../CHANGELOG.md)
