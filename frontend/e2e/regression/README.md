# Regression Tests

이 디렉토리는 GitHub Issue와 연동된 회귀 테스트를 포함합니다.

## 목적

버그가 수정된 후, 동일한 버그가 재발하지 않도록 테스트를 작성합니다.

## 파일 명명 규칙

```text
issue-{NUMBER}-{short-description}.spec.ts
```

예시:

- `issue-123-login-timeout.spec.ts`
- `issue-456-api-error-handling.spec.ts`
- `issue-789-mobile-navigation.spec.ts`

## 테스트 실행

```bash
# 모든 회귀 테스트 실행
npm run test:e2e -- e2e/regression/

# 특정 이슈 테스트 실행
npm run test:e2e -- --grep "Issue #123"

# @regression 태그로 실행
npm run test:e2e -- --grep "@regression"
```

## 새 회귀 테스트 작성

1. `_template-issue-XXX.spec.ts` 파일을 복사
2. 파일명을 `issue-{번호}-{설명}.spec.ts`로 변경
3. 모든 XXX 플레이스홀더를 실제 이슈 번호로 교체
4. PROBLEM, ROOT CAUSE, FIX 섹션 작성
5. 테스트 케이스 구현

## 테스트 구조

```typescript
test.describe('Regression: Issue #123 - 간단한 설명', () => {
  /**
   * GitHub Issue: https://github.com/jclee941/blacklist/issues/123
   *
   * PROBLEM: 원래 버그가 무엇이었는지
   * ROOT CAUSE: 왜 발생했는지
   * FIX: 어떻게 수정했는지
   */

  test('should [수정된 동작] @regression', async ({ page }) => {
    // 버그를 재현하는 시나리오 테스트
  });
});
```

## 태그

- `@regression` - 회귀 테스트 표시
- `@smoke` - 배포 검증 테스트

## GitHub Issue 링크

모든 회귀 테스트는 해당 GitHub Issue를 문서화 주석에 링크해야 합니다:

```typescript
/**
 * GitHub Issue: https://github.com/jclee941/blacklist/issues/XXX
 */
```

## 베스트 프랙티스

1. **하나의 이슈 = 하나의 파일**: 관련 이슈별로 파일 분리
2. **명확한 문서화**: 버그, 원인, 수정사항 모두 기록
3. **독립적 실행**: 다른 테스트에 의존하지 않음
4. **빠른 실행**: 회귀 테스트는 빠르게 실행되어야 함
