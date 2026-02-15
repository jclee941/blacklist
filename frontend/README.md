# Blacklist Frontend

Next.js 15 + TypeScript + Tailwind CSS v4 대시보드 애플리케이션

## 기술 스택

- **Next.js 15** - React 19 프레임워크 (App Router)
- **TypeScript** - Strict 타입 안정성
- **Tailwind CSS v4** - 유틸리티 CSS 프레임워크
- **Radix UI / shadcn** - 컴포넌트 라이브러리
- **React Query** - 서버 상태 관리
- **Zustand** - 클라이언트 상태 관리
- **Recharts** - 차트 라이브러리
- **Lucide React** - 아이콘

## 프로젝트 구조

```
frontend/
├── app/                    # Next.js App Router 페이지
│   ├── page.tsx            # Dashboard (메인 페이지)
│   ├── ip-management/      # IP 관리
│   ├── collection/         # 수집 제어
│   ├── analytics/          # 분석 대시보드
│   ├── monitoring/         # 시스템 모니터링
│   ├── settings/           # 설정
│   └── fortinet/           # Fortinet 통합
├── components/             # 재사용 컴포넌트
│   └── ui/                 # Radix UI / shadcn 컴포넌트
├── lib/
│   └── api.ts              # API 클라이언트 (모든 API 호출 여기를 통해)
├── hooks/                  # Custom React Hooks
├── types/                  # TypeScript 타입 정의
├── __tests__/              # 단위 테스트 (Vitest) — 44개 파일, 207+ 테스트
├── e2e/                    # E2E 테스트 (Playwright)
├── package.json
├── next.config.ts          # /api/* → :2542 rewrite
└── Dockerfile              # Standalone + SSL 임베드
```

## 시작하기

### 1. 의존성 설치

```bash
npm install
```

### 2. 개발 서버 실행

```bash
npm run dev
```

### 3. 프로덕션 빌드

```bash
npm run build
npm start
```

## 배포

### Docker (스탠드얼론 + SSL)

Frontend는 `output: 'standalone'` 모드로 빌드되며, SSL 인증서가 Docker 이미지에 임베드됩니다.

| 항목         | 설명                 |
| ------------ | -------------------- |
| **포트**     | 443 (HTTPS)          |
| **출력**     | Next.js standalone   |
| **SSL**      | 이미지 내 임베드     |
| **베이스**   | node:20-alpine       |
| **네트워크** | `network_mode: host` |

## Flask API 통합

`next.config.ts`의 `rewrites` 설정을 통해 Flask API (포트 2542)와 통합:

```typescript
async rewrites() {
  return [
    {
      source: '/api/:path*',
      destination: 'http://localhost:2542/api/:path*',
    },
  ];
}
```

## 테스트

| 유형        | 프레임워크 | 파일 수 | 테스트 수 |
| ----------- | ---------- | ------- | --------- |
| 단위 테스트 | Vitest     | 44      | 207+      |
| E2E         | Playwright | —       | Chromium  |

```bash
npm run test              # Vitest 단위 테스트
npm run test:coverage     # 커버리지 보고서
npx tsc --noEmit          # TypeScript 타입 검사
npx playwright test       # E2E 테스트
```

## 개발 가이드

### API 호출 규칙

모든 API 호출은 `lib/api.ts`를 통해서만 수행:

```typescript
import { api } from '@/lib/api';
const data = await api.get('/blacklist');

import { authApi } from '@/lib/api';
const { token } = await authApi.login(username, password);
```

### 새 페이지 추가

1. `app/<feature>/page.tsx` (Server Component) + `*Client.tsx` (Client Component) 생성
2. `lib/api.ts`에 API 메서드 추가
3. `types/`에 타입 정의

## 문제 해결

### TypeScript 에러

```bash
npx tsc --noEmit
```

### 의존성 문제

```bash
rm -rf node_modules package-lock.json
npm install
```

### CORS 에러

- `next.config.ts`의 rewrites 설정 확인
- Flask API 실행 상태 확인
