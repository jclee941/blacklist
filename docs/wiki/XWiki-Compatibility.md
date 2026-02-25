# XWiki Compatibility Guide

Blacklist 문서를 XWiki로 이식할 때 깨지기 쉬운 Markdown 요소를 표준 패턴으로 정리합니다.

## Scope

- 대상: `docs/README.md`, `docs/wiki/*.md`, `docs/deliverables/*.md`
- 목적: 링크, 표, 코드블록, 다이어그램을 XWiki에서도 동일 의미로 렌더링

## Compatibility Rules

### 1) Links

- 기본: 표준 Markdown 링크 유지 (`[Text](Page.md)`).
- 위키 내부 링크: `wiki/` 접두사 대신 같은 디렉토리 상대 경로(`Architecture.md`) 우선.
- 상위 경로 링크(`../`)는 XWiki 공간 구조에 따라 깨질 수 있으므로, 이식 시 페이지 경로 기준으로 재매핑.

예시:

```text
Markdown: [시스템 아키텍처](Architecture.md)
XWiki 변환: [[시스템 아키텍처>>doc:Blacklist.Wiki.Architecture]]
```

### 2) Tables

- 다중 행 병합/중첩 표를 피하고 단순 2~4열 표를 유지.
- 셀 내부 줄바꿈/복잡한 마크업 대신 짧은 텍스트 + 보조 문단 구조 사용.

### 3) Code Blocks

- 펜스 코드블록(````lang`) 유지.
- XWiki 변환 시 `{{code language="..."}} ... {{/code}}` 매크로로 치환 가능.

예시:

````text
Markdown:
```bash
make dev
```

XWiki:
{{code language="bash"}}
make dev
{{/code}}

````

### 4) Mermaid Diagrams

- 현재 문서는 ` ```mermaid ` 구문 사용.
- XWiki에서는 Mermaid Macro 또는 Diagram Macro 확장 필요.
- 확장이 없으면 PNG/SVG 정적 이미지로 대체 첨부.

## Migration Checklist

1. 문서 내 `../` 링크를 XWiki 페이지 경로로 매핑
2. Mermaid 블록이 매크로 확장으로 렌더링되는지 확인
3. 긴 표(특히 API/스키마 표)가 열 너비 깨짐 없이 표시되는지 확인
4. 코드블록 언어 힌트가 유지되는지 확인
5. `.drawio` 원본 링크를 첨부파일 또는 외부 저장소 링크로 대체

## Repository-specific Notes

- `docs/wiki/Architecture.md`는 Mermaid 다이어그램과 대형 표가 많아 우선 검증 대상입니다.
- `docs/wiki/API-Reference.md`, `docs/wiki/Database-Schema.md`는 대형 표 중심 문서로 열 너비 확인이 필요합니다.
- `docs/README.md`는 허브 문서로, XWiki 이식 시 링크 경로 표준을 먼저 확정해야 전체 링크가 안정화됩니다.

```

```
