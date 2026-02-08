# FRONTEND KNOWLEDGE BASE

**Generated:** 2026-02-08
**Role:** Dashboard UI (관리 인터페이스)
**Parent:** [../AGENTS.md](../AGENTS.md)

## OVERVIEW

Next.js 15 기반 관리 대시보드. **Air-Gap 호환** — 모든 API 호출은 프록시를 통해 수행.
Tailwind CSS v4 + Radix UI 컴포넌트 시스템.

## STRUCTURE

```
app/                    # App Router
├── (auth)/             # 인증 필요 라우트
├── ip-management/      # IP 관리
│   ├── IPManagementClient.tsx  # 메인 클라이언트 (893L)
│   └── components/     # ✅ 추출된 하위 컴포넌트 (v3.5.37)
│       ├── IPManagementTable, IPManagementTabs, IPManagementFilters
│       ├── IPManagementFormModal, DeleteConfirmModal
│       └── useIPManagement (hook)
├── collection/         # 수집 관리
│   ├── components/     # 7 하위 컴포넌트
│   └── hooks/          # 커스텀 훅
├── globals.css         # Tailwind v4
└── page.tsx            # 대시보드 루트
components/{ui/,features/}  # Radix UI 기반
lib/api.ts              # ⚠️ 필수: 모든 API 호출 경유
types/                  # TypeScript 타입
next.config.ts          # /api/* → :2542 리라이트
```

## HOW TO: 새 페이지 추가

1. `app/<feature>/page.tsx` (Server Component) + `*Client.tsx` (Client Component)
2. `lib/api.ts`에 API 메서드 추가
3. `types/`에 타입 정의

**패턴**: `page.tsx` → Server (데이터 페칭), `*Client.tsx` → Client (인터랙션, hooks)

## CONVENTIONS

| 규약      | 내용                                        |
| --------- | ------------------------------------------- |
| API 호출  | `lib/api.ts` 통해서만 (직접 fetch 금지)     |
| 컴포넌트  | `page.tsx` = Server, `*Client.tsx` = Client |
| 상태 관리 | Zustand (전역 UI), React Query (서버 상태)  |
| 스타일링  | Tailwind Utility만 (커스텀 CSS 금지)        |
| 빌드      | `output: 'standalone'` (Docker 최적화)      |

## KNOWN ISSUES

| 파일                     | 문제                                                      |
| ------------------------ | --------------------------------------------------------- |
| `next.config.ts:7`       | Hardcoded API URL → `API_URL` 환경변수 사용               |
| `IPManagementClient.tsx` | 893L — 컴포넌트 추출 완료, 메인 파일 리팩토링 여전히 필요 |
| Dashboard + Collection   | 이중 폴링 (30s + 5s 동시)                                 |

## DEPLOYMENT

단일 컨테이너: Nginx(프록시) + Next.js(standalone) + supervisord.
SSL: 프로덕션 Traefik, 개발 `frontend/ssl/` 인증서.

## NOTES

- `components/ui/` — Radix UI primitives, 직접 수정 금지
- E2E 테스트: `tests/e2e/` (Playwright) — UI 변경 시 필수 실행
- Prettier(100), single quotes, semicolons required
