# Blacklist Intelligence Platform

**REGTECH 블랙리스트 인텔리전스 플랫폼** — 위협 IP 관리 및 자동 수집 시스템

| 항목            | 값                                                                        |
| --------------- | ------------------------------------------------------------------------- |
| **버전**        | 3.6.9                                                                     |
| **기술 스택**   | Flask 3.x (Python 3.11) + Next.js 15 (React 19) + PostgreSQL 15 + Redis 7 |
| **라이선스**    | Private                                                                   |
| **데이터 소스** | REGTECH (한국금융보안원)                                             |

---

## 주요 기능

- **IP 블랙리스트 관리** — 위협 IP 등록, 조회, 만료 처리, 화이트리스트 관리
- **자동 수집 (ETL)** — REGTECH 소스에서 주기적 데이터 수집
- **FortiGate 연동** — Threat Feed 제공
- **분석 대시보드** — 탐지 타임라인, 국가별/소스별 통계, 트렌드 분석
- **모니터링** — Prometheus 메트릭, 서비스 헬스체크, 시스템 로그
- **보안** — AES-256-GCM 크레덴셜 암호화, JWT 인증 (선택적)

---

## 문서 목차

| 문서                                          | 설명                                                      |
| --------------------------------------------- | --------------------------------------------------------- |
| [Architecture](Architecture.md)               | 시스템 아키텍처, 서비스 토폴로지, 데이터 흐름             |
| [Service-Details](Service-Details.md)         | 14개 애플리케이션 서비스, DI 컨테이너, 라이프사이클       |
| [Database-Schema](Database-Schema.md)         | 데이터베이스 스키마, 테이블/뷰 정의, 인덱스, 마이그레이션 |
| [API-Reference](API-Reference.md)             | REST API 엔드포인트 레퍼런스 (80+ 엔드포인트)             |
| [Deployment-Guide](Deployment-Guide.md)       | Docker 배포, 오프라인 설치, CI/CD 파이프라인              |
| [Security](Security.md)                       | 인증/인가, 암호화, FortiGate 연동, 환경변수               |
| [XWiki-Compatibility](XWiki-Compatibility.md) | XWiki 이식 규칙, Mermaid/표/링크 변환 가이드              |

---

## 빠른 시작

```bash
# 개발 환경 실행
make dev

# 테스트 실행
make test

# 프로덕션 빌드
make build
```

## 서비스 포트

| 서비스             | 포트 | 설명                |
| ------------------ | ---- | ------------------- |
| PostgreSQL         | 5432 | 데이터베이스        |
| Redis              | 6379 | 캐시/세션           |
| Collector          | 8545 | ETL 수집 서비스     |
| App (Flask)        | 2542 | REST API 서버       |
| Frontend (Next.js) | 443  | 웹 대시보드 (HTTPS) |

## 프로젝트 구조

```
blacklist/
├── app/                    # Flask API (Python 3.11)           :2542
│   ├── core/app.py         #   Application Factory
│   ├── core/services/      #   14개 서비스 (ServiceFactory DI)
│   ├── core/routes/api/    #   REST API 엔드포인트
│   └── core/routes/web/    #   Web Admin (Jinja2, 한국어 UI)
├── collector/              # ETL 수집 서비스 (독립 프로세스)    :8545
│   └── core/               #   REGTECH 수집기
├── frontend/               # Next.js 15 대시보드               :443
│   ├── app/                #   App Router 페이지
│   └── lib/api.ts          #   API 클라이언트 (Axios)
├── postgres/               # PostgreSQL 15 스키마/마이그레이션
├── deploy/                 # Docker Compose, 오프라인 설치
└── tests/                  # 992+ 테스트 (pytest + vitest + Playwright)
```
