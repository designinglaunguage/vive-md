# WebSearchTool & WebFetchTool 상세 분석

> Claude Code의 웹 검색 및 웹 페이지 가져오기 도구에 대한 심층 분석 문서

---

## 목차

1. [개요](#1-%EA%B0%9C%EC%9A%94)
2. [WebSearchTool — 웹 검색 도구](#2-websearchtool--%EC%9B%B9-%EA%B2%80%EC%83%89-%EB%8F%84%EA%B5%AC)
   - [아키텍처](#21-%EC%95%84%ED%82%A4%ED%85%8D%EC%B2%98)
   - [입출력 스키마](#22-%EC%9E%85%EC%B6%9C%EB%A0%A5-%EC%8A%A4%ED%82%A4%EB%A7%88)
   - [실행 흐름](#23-%EC%8B%A4%ED%96%89-%ED%9D%90%EB%A6%84)
   - [모델 호출 방식](#24-%EB%AA%A8%EB%8D%B8-%ED%98%B8%EC%B6%9C-%EB%B0%A9%EC%8B%9D)
   - [프로바이더별 활성화 조건](#25-%ED%94%84%EB%A1%9C%EB%B0%94%EC%9D%B4%EB%8D%94%EB%B3%84-%ED%99%9C%EC%84%B1%ED%99%94-%EC%A1%B0%EA%B1%B4)
   - [프롬프트 전략](#26-%ED%94%84%EB%A1%AC%ED%94%84%ED%8A%B8-%EC%A0%84%EB%9E%B5)
   - [UI 컴포넌트](#27-ui-%EC%BB%B4%ED%8F%AC%EB%84%8C%ED%8A%B8)
3. [WebFetchTool — 웹 페이지 가져오기 도구](#3-webfetchtool--%EC%9B%B9-%ED%8E%98%EC%9D%B4%EC%A7%80-%EA%B0%80%EC%A0%B8%EC%98%A4%EA%B8%B0-%EB%8F%84%EA%B5%AC)
   - [아키텍처](#31-%EC%95%84%ED%82%A4%ED%85%8D%EC%B2%98)
   - [입출력 스키마](#32-%EC%9E%85%EC%B6%9C%EB%A0%A5-%EC%8A%A4%ED%82%A4%EB%A7%88)
   - [실행 흐름](#33-%EC%8B%A4%ED%96%89-%ED%9D%90%EB%A6%84)
   - [권한 시스템](#34-%EA%B6%8C%ED%95%9C-%EC%8B%9C%EC%8A%A4%ED%85%9C)
   - [URL 유효성 검증](#35-url-%EC%9C%A0%ED%9A%A8%EC%84%B1-%EA%B2%80%EC%A6%9D)
   - [콘텐츠 처리 파이프라인](#36-%EC%BD%98%ED%85%90%EC%B8%A0-%EC%B2%98%EB%A6%AC-%ED%8C%8C%EC%9D%B4%ED%94%84%EB%9D%BC%EC%9D%B8)
   - [사전 승인 도메인](#37-%EC%82%AC%EC%A0%84-%EC%8A%B9%EC%9D%B8-%EB%8F%84%EB%A9%94%EC%9D%B8-preapproved)
   - [프롬프트 전략](#38-%ED%94%84%EB%A1%AC%ED%94%84%ED%8A%B8-%EC%A0%84%EB%9E%B5)
   - [UI 컴포넌트](#39-ui-%EC%BB%B4%ED%8F%AC%EB%84%8C%ED%8A%B8)
4. [두 도구의 비교](#4-%EB%91%90-%EB%8F%84%EA%B5%AC%EC%9D%98-%EB%B9%84%EA%B5%90)
5. [공통 패턴: buildTool 인터페이스](#5-%EA%B3%B5%ED%86%B5-%ED%8C%A8%ED%84%B4-buildtool-%EC%9D%B8%ED%84%B0%ED%8E%98%EC%9D%B4%EC%8A%A4)

---

## 1. 개요

| 도구 | 파일 수 | 핵심 역할 |
| --- | --- | --- |
| `WebSearchTool` | 3개 | Anthropic Web Search API를 통해 실시간 웹 검색 수행 |
| `WebFetchTool` | 5개 | URL에서 콘텐츠를 가져와 AI 모델로 요약/분석 |

두 도구 모두 `buildTool()` 팩토리로 생성되며, `ToolDef` 인터페이스를 구현한다. 읽기 전용(`isReadOnly: true`), 동시 실행 안전(`isConcurrencySafe: true`), 지연 로딩 대상(`shouldDefer: true`)이라는 공통 속성을 갖는다.

### 파일 구조

```
src/tools/
├── WebSearchTool/
│   ├── WebSearchTool.ts      # 메인 구현 (435줄)
│   ├── prompt.ts             # 프롬프트 정의 (34줄)
│   └── UI.tsx                # React UI 컴포넌트 (101줄)
│
└── WebFetchTool/
    ├── WebFetchTool.ts       # 메인 구현 (319줄)
    ├── prompt.ts             # 프롬프트 & 2차 모델 프롬프트 (55줄)
    ├── utils.ts              # 핵심 유틸리티 (531줄)
    ├── preapproved.ts        # 사전 승인 도메인 목록 (131개)
    └── UI.tsx                # React UI 컴포넌트 (72줄)
```

---

## 2. WebSearchTool — 웹 검색 도구

### 2.1 아키텍처

WebSearchTool은 Claude Code가 직접 웹을 검색하는 것이 아니라, **Anthropic의** `web_search_20250305` **서버 사이드 도구**를 활용하는 래퍼다. 내부적으로 별도의 모델 API 호출을 발행하여, 그 모델이 서버 도구(`web_search`)를 사용하도록 한다.

```
사용자 프롬프트
  │
  ▼
Claude (메인 모델) → WebSearchTool.call() 호출
  │
  ▼
별도 API 호출 (queryModelWithStreaming)
  ├── 시스템: "You are an assistant for performing a web search tool use"
  ├── 메시지: "Perform a web search for the query: {query}"
  └── extraToolSchemas: [web_search_20250305]
       │
       ▼
  서버 사이드 web_search 실행 (최대 8회)
       │
       ▼
  검색 결과 (server_tool_use → web_search_tool_result → text/citation)
       │
       ▼
  makeOutputFromSearchResponse() → 구조화된 Output
       │
       ▼
  메인 모델에 결과 반환 (Sources 포함 의무)
```

### 2.2 입출력 스키마

#### Input

```typescript
{
  query: string              // 검색 쿼리 (최소 2자)
  allowed_domains?: string[] // 허용 도메인 필터 (선택)
  blocked_domains?: string[] // 차단 도메인 필터 (선택)
}
```

> **제약**: `allowed_domains`와 `blocked_domains`를 동시에 지정할 수 없다.

#### Output

```typescript
{
  query: string                           // 실행된 검색 쿼리
  results: (SearchResult | string)[]      // 검색 결과 + 텍스트 해설
  durationSeconds: number                 // 소요 시간 (초)
}

// SearchResult 구조
{
  tool_use_id: string                     // 도구 사용 ID
  content: { title: string; url: string }[] // 검색 히트 목록
}
```

### 2.3 실행 흐름

```
WebSearchTool.call(input, context, _, _, onProgress)
  │
  ├─ 1. 입력 준비
  │   ├── createUserMessage("Perform a web search for: {query}")
  │   └── makeToolSchema(input) → BetaWebSearchTool20250305
  │       ├── type: 'web_search_20250305'
  │       ├── allowed_domains / blocked_domains
  │       └── max_uses: 8 (하드코딩)
  │
  ├─ 2. 모델 선택
  │   ├── tengu_plum_vx3 feature flag 체크
  │   ├── true  → Haiku (getSmallFastModel), thinking 비활성
  │   └── false → 메인 모델, 기존 thinking 설정 유지
  │
  ├─ 3. API 스트리밍 호출
  │   └── queryModelWithStreaming({
  │         messages, systemPrompt, tools: [],
  │         extraToolSchemas: [toolSchema],
  │         querySource: 'web_search_tool'
  │       })
  │
  ├─ 4. 스트리밍 이벤트 처리
  │   ├── assistant 메시지 → allContentBlocks에 수집
  │   ├── content_block_start (server_tool_use)
  │   │   └── currentToolUseId 추적 시작
  │   ├── content_block_delta (input_json_delta)
  │   │   └── JSON 파싱하여 query 추출 → onProgress('query_update')
  │   └── content_block_start (web_search_tool_result)
  │       └── onProgress('search_results_received')
  │
  ├─ 5. 결과 변환
  │   └── makeOutputFromSearchResponse(allContentBlocks, query, duration)
  │       ├── server_tool_use 블록 → 검색 경계 마커
  │       ├── web_search_tool_result 블록 → SearchResult 추출
  │       │   ├── 성공: { title, url } 배열
  │       │   └── 에러: "Web search error: {error_code}" 문자열
  │       └── text 블록 → 텍스트 해설 수집
  │
  └─ 6. 결과 포맷팅 (mapToolResultToToolResultBlockParam)
      └── "Web search results for query: "{query}"
           {텍스트 해설}
           Links: [{title, url}, ...]
           REMINDER: You MUST include the sources..."
```

### 2.4 모델 호출 방식

WebSearchTool은 **내부에서 별도의 모델 API 호출**을 수행한다. 이것이 일반 도구와의 핵심 차이점이다.

```typescript
const queryStream = queryModelWithStreaming({
  messages: [userMessage],
  systemPrompt: asSystemPrompt([
    'You are an assistant for performing a web search tool use'
  ]),
  thinkingConfig: useHaiku ? { type: 'disabled' } : context.options.thinkingConfig,
  tools: [],                          // Claude 도구는 없음
  options: {
    model: useHaiku ? getSmallFastModel() : context.options.mainLoopModel,
    toolChoice: useHaiku ? { type: 'tool', name: 'web_search' } : undefined,
    extraToolSchemas: [toolSchema],    // 서버 사이드 도구만 제공
    querySource: 'web_search_tool',
  },
})
```

| 설정 | Haiku 모드 (feature on) | 기본 모드 |
| --- | --- | --- |
| 모델 | `getSmallFastModel()` (Haiku) | 메인 루프 모델 |
| Thinking | 비활성 | 기존 설정 유지 |
| toolChoice | `{ type: 'tool', name: 'web_search' }` | undefined (자유) |

> **설계 의도**: Haiku 모드는 비용/속도 최적화. `toolChoice`로 web_search 강제 호출하여 불필요한 텍스트 생성을 방지한다.

### 2.5 프로바이더별 활성화 조건

```typescript
isEnabled() {
  const provider = getAPIProvider()
  const model = getMainLoopModel()

  if (provider === 'firstParty') return true        // Anthropic API: 항상
  if (provider === 'foundry') return true            // Foundry: 항상
  if (provider === 'vertex') {                       // Vertex AI: Claude 4.0+ 만
    return model.includes('claude-opus-4') ||
           model.includes('claude-sonnet-4') ||
           model.includes('claude-haiku-4')
  }
  return false                                       // 기타 (Bedrock 등): 비활성
}
```

### 2.6 프롬프트 전략

```
- 웹 검색 결과를 기반으로 정보 제공
- 응답 후 반드시 "Sources:" 섹션에 마크다운 하이퍼링크 포함 (CRITICAL REQUIREMENT)
- 현재 연월(${currentMonthYear})을 검색 쿼리에 반영 (IMPORTANT)
- 도메인 필터링 지원
- 미국 지역에서만 사용 가능
```

> **핵심**: Sources 섹션은 **MANDATORY**로 표시되어 있어, 모델이 검색 결과 출처를 반드시 포함하도록 강제한다.

### 2.7 UI 컴포넌트

| 함수 | 용도 | 표시 예시 |
| --- | --- | --- |
| `renderToolUseMessage` | 도구 호출 시 | `"React documentation 2026"` |
| `renderToolUseProgressMessage` | 진행 중 | `Searching: React docs` 또는 `Found 5 results for "React docs"` |
| `renderToolResultMessage` | 결과 표시 | `Did 3 searches in 2s` |
| `getToolUseSummary` | 요약 | 쿼리 텍스트 (truncated) |

---

## 3. WebFetchTool — 웹 페이지 가져오기 도구

### 3.1 아키텍처

WebFetchTool은 URL에서 콘텐츠를 가져와 HTML→Markdown 변환 후, **보조 모델(Haiku)로 요약/분석**하여 결과를 반환한다. 15분 캐시, 도메인 블록리스트, 사전 승인 도메인 등 다층 안전장치를 갖추고 있다.

```
사용자 프롬프트
  │
  ▼
Claude (메인 모델) → WebFetchTool.call(url, prompt) 호출
  │
  ▼
┌────────────────────────────────────────────────┐
│ URL 유효성 검증 (validateURL)                   │
│  ├── URL 길이, 프로토콜, 인증정보 체크            │
│  └── 호스트네임 구조 검증                        │
├────────────────────────────────────────────────┤
│ 캐시 확인 (LRU Cache)                           │
│  ├── 히트 → 캐시된 콘텐츠 반환                   │
│  └── 미스 → 다음 단계                           │
├────────────────────────────────────────────────┤
│ 도메인 블록리스트 확인 (checkDomainBlocklist)     │
│  └── api.anthropic.com 호출하여 도메인 안전성 검증 │
├────────────────────────────────────────────────┤
│ HTTP 요청 + 리다이렉트 처리                       │
│  ├── 동일 호스트 리다이렉트: 자동 추종 (최대 10회)  │
│  └── 다른 호스트 리다이렉트: REDIRECT 응답 반환    │
├────────────────────────────────────────────────┤
│ 콘텐츠 변환                                     │
│  ├── HTML → Markdown (Turndown)                 │
│  └── PDF/바이너리 → 디스크 저장 + 참조            │
├────────────────────────────────────────────────┤
│ 프롬프트 기반 분석 (applyPromptToMarkdown)       │
│  ├── 사전 승인 + text/markdown + 짧음 → 원본 반환 │
│  └── 그 외 → Haiku 모델로 요약/분석               │
└────────────────────────────────────────────────┘
  │
  ▼
Output { bytes, code, codeText, result, durationMs, url }
```

### 3.2 입출력 스키마

#### Input

```typescript
{
  url: string     // 가져올 URL (유효한 URL 형식)
  prompt: string  // 콘텐츠에 적용할 프롬프트 (추출/분석 지시)
}
```

#### Output

```typescript
{
  bytes: number       // 가져온 콘텐츠 크기 (바이트)
  code: number        // HTTP 응답 코드
  codeText: string    // HTTP 응답 코드 텍스트
  result: string      // 프롬프트 적용 후 처리된 결과
  durationMs: number  // 소요 시간 (밀리초)
  url: string         // 가져온 URL
}
```

### 3.3 실행 흐름

```
WebFetchTool.call({ url, prompt }, context)
  │
  ├─ 1. getURLMarkdownContent(url, abortController)
  │   ├── validateURL(url)
  │   │   ├── URL 길이 체크
  │   │   ├── 프로토콜 체크 (http/https만 허용)
  │   │   ├── 인증 정보 체크 (username:password 거부)
  │   │   └── 호스트네임 구조 검증
  │   │
  │   ├── LRU 캐시 확인 (15분 TTL, 50MB 한도)
  │   │   └── 히트 시 캐시된 FetchedContent 반환
  │   │
  │   ├── checkDomainBlocklist(hostname)
  │   │   └── api.anthropic.com에 도메인 안전성 질의
  │   │
  │   ├── HTTP 요청 + 리다이렉트 처리
  │   │   ├── getWithPermittedRedirects(url)
  │   │   │   └── 최대 10홉, 동일 호스트만 자동 추종
  │   │   └── 다른 호스트 → { type: 'redirect' } 반환
  │   │
  │   └── 콘텐츠 변환
  │       ├── HTML → Turndown → Markdown
  │       └── 바이너리 → 디스크 저장 + persistedPath
  │
  ├─ 2. 리다이렉트 응답 분기 (다른 호스트)
  │   └── "REDIRECT DETECTED: ..." 메시지 반환
  │       └── 사용자에게 새 URL로 재요청 안내
  │
  ├─ 3. 콘텐츠 분석
  │   ├── 사전 승인 도메인 + text/markdown + 짧음
  │   │   └── 원본 콘텐츠 그대로 반환
  │   └── 그 외
  │       └── applyPromptToMarkdown(prompt, content, ...)
  │           ├── makeSecondaryModelPrompt()로 프롬프트 생성
  │           └── Haiku 모델 호출하여 요약/분석
  │
  └─ 4. 바이너리 콘텐츠 보조 정보
      └── persistedPath 있으면 파일 경로 + 크기 추가
```

### 3.4 권한 시스템

WebFetchTool은 3단계 권한 체크를 수행한다:

```
checkPermissions(input, context)
  │
  ├─ 1단계: 사전 승인 도메인 체크
  │   └── isPreapprovedHost(hostname, pathname)
  │       └── 매칭 → { behavior: 'allow' } (즉시 허용)
  │
  ├─ 2단계: 규칙 기반 체크 (hostname 단위)
  │   ├── ruleContent = "domain:{hostname}"
  │   ├── deny 규칙 매칭  → { behavior: 'deny' }
  │   ├── ask 규칙 매칭   → { behavior: 'ask' }
  │   └── allow 규칙 매칭 → { behavior: 'allow' }
  │
  └─ 3단계: 기본값
      └── { behavior: 'ask' } + 도메인별 allow 규칙 제안
```

**규칙 생성**: 사용자가 허용하면 `domain:{hostname}` 단위로 `localSettings`에 allow 규칙이 저장된다. 이후 같은 도메인의 다른 URL은 자동 허용.

```typescript
// 규칙 제안 예시
{
  type: 'addRules',
  destination: 'localSettings',
  rules: [{ toolName: 'WebFetch', ruleContent: 'domain:docs.python.org' }],
  behavior: 'allow',
}
```

### 3.5 URL 유효성 검증

`utils.ts`의 `validateURL()` 함수:

| 검증 항목 | 설명 |
| --- | --- |
| URL 길이 | 과도하게 긴 URL 거부 |
| 프로토콜 | `http://`와 `https://`만 허용 (HTTP→HTTPS 자동 업그레이드) |
| 인증 정보 | `username:password@host` 형식 거부 |
| 호스트네임 | 유효한 도메인 구조 검증 |

### 3.6 콘텐츠 처리 파이프라인

#### 캐시 계층

```
LRU Cache (utils.ts)
  ├── TTL: 15분 (self-cleaning)
  ├── 최대 크기: 50MB
  └── 키: URL
```

#### HTML → Markdown 변환

Turndown 라이브러리를 lazy-load하여 HTML을 Markdown으로 변환한다.

#### 2차 모델 처리 (applyPromptToMarkdown)

콘텐츠가 너무 크거나 일반 웹페이지인 경우, Haiku 모델로 프롬프트 기반 요약/분석을 수행한다.

```typescript
// makeSecondaryModelPrompt 구조
`Web page content:
---
${markdownContent}
---

${prompt}

${guidelines}  // 사전 승인 여부에 따라 다른 가이드라인
`
```

| 도메인 유형 | 가이드라인 |
| --- | --- |
| **사전 승인** | 관련 세부사항, 코드 예시, 문서 발췌를 포함한 간결한 응답 |
| **일반** | 125자 인용 제한, 인용부호 사용 의무, 가사 재생산 금지, 법적 코멘트 금지 |

#### 바이너리 콘텐츠 (PDF 등)

바이너리 파일은 디스크에 mime 확장자로 저장하고, 결과에 파일 경로를 추가한다:

```
[Binary content (application/pdf, 2.5 MB) also saved to /tmp/...)
```

### 3.7 사전 승인 도메인 (Preapproved)

`preapproved.ts`에 131개 도메인이 카테고리별로 정리되어 있다:

| 카테고리 | 예시 도메인 |
| --- | --- |
| Anthropic | platform.claude.com, docs.anthropic.com |
| 프로그래밍 언어 | docs.python.org, doc.rust-lang.org, go.dev |
| 프레임워크 | react.dev, vuejs.org, angular.dev |
| 클라우드 | docs.aws.amazon.com, cloud.google.com |
| 데이터베이스 | postgresql.org, redis.io |
| 기타 | developer.mozilla.org, stackoverflow.com |

**사전 승인 효과**:

1. `checkPermissions()`: 권한 확인 없이 즉시 허용
2. `applyPromptToMarkdown()`: 인용 제한 없이 전체 콘텐츠 활용
3. `text/markdown` + 짧은 콘텐츠: Haiku 호출 없이 원본 그대로 반환

**경로 기반 승인**: 일부 도메인은 경로까지 체크한다 (예: `github.com/anthropics`는 허용, `github.com/other`는 일반 권한 체크).

### 3.8 프롬프트 전략

```
IMPORTANT: WebFetch WILL FAIL for authenticated or private URLs.
Before using this tool, check if the URL points to an authenticated service
(e.g. Google Docs, Confluence, Jira, GitHub).
If so, look for a specialized MCP tool that provides authenticated access.

- URL에서 콘텐츠를 가져와 AI 모델로 처리
- HTML → Markdown 변환
- 결과가 크면 요약 가능
- 15분 캐시 포함
- 리다이렉트 시 새 URL 안내
- GitHub URL은 gh CLI 사용 권장
- MCP 제공 fetch 도구가 있으면 그쪽 우선 사용
```

> **핵심 경고**: 인증이 필요한 URL은 실패한다. MCP 도구(GitHub MCP, Jira MCP 등)가 있으면 그쪽을 우선 사용하라는 안내가 포함된다.

### 3.9 UI 컴포넌트

| 함수 | 용도 | 표시 예시 |
| --- | --- | --- |
| `renderToolUseMessage` | 도구 호출 시 | URL + 프롬프트 (선택) |
| `renderToolUseProgressMessage` | 진행 중 | `Fetching…` |
| `renderToolResultMessage` | 결과 표시 | 응답 크기 + HTTP 상태 |
| `getToolUseSummary` | 요약 | URL (truncated) |

---

## 4. 두 도구의 비교

| 관심사 | WebSearchTool | WebFetchTool |
| --- | --- | --- |
| **목적** | 웹 검색 (키워드 기반) | 특정 URL 콘텐츠 가져오기 |
| **내부 모델 호출** | 서버 사이드 `web_search` 도구 활용 | Haiku로 콘텐츠 요약/분석 |
| **캐시** | 없음 | LRU 15분, 50MB |
| **권한** | passthrough (항상 묻기) | 도메인별 규칙 + 사전 승인 |
| **도메인 필터** | allowed/blocked_domains (입력) | 블록리스트 (API 서버 검증) |
| **입력** | `query` + 도메인 필터 | `url` + `prompt` |
| **출력** | 검색 결과 목록 + 해설 | 처리된 콘텐츠 요약 |
| **모델 선택** | 메인 모델 또는 Haiku (feature flag) | Haiku (2차 모델) |
| **max_uses** | 8회 (하드코딩) | 1회 (단일 URL) |
| **리다이렉트** | 서버 처리 | 동일 호스트만 자동 추종 |
| **프로바이더** | firstParty, Vertex (4.0+), Foundry | 모든 프로바이더 |
| **결과 크기 제한** | 100K chars | 100K chars |
| **Sources 의무** | MANDATORY | 해당 없음 |
| **인증 URL** | 서버에서 처리 | 실패 (MCP 도구 권장) |

### 사용 시나리오 가이드

```
"최신 React 19 변경사항이 뭐야?"
  → WebSearchTool (키워드 검색 → 최신 정보)

"이 URL의 문서 내용 요약해줘: https://react.dev/blog/..."
  → WebFetchTool (특정 URL → 콘텐츠 분석)

"GitHub 이슈 내용 확인해줘: https://github.com/org/repo/issues/123"
  → gh CLI 또는 GitHub MCP 도구 (인증 필요)
```

---

## 5. 공통 패턴: buildTool 인터페이스

두 도구 모두 `buildTool()` 팩토리 함수로 생성되며, `ToolDef<InputSchema, Output>` 인터페이스를 구현한다.

### ToolDef 필수 속성

```typescript
{
  // ── 메타데이터 ──
  name: string                    // 도구 이름 (고유 식별자)
  searchHint: string              // ToolSearch용 힌트
  maxResultSizeChars: number      // 결과 크기 제한
  shouldDefer: boolean            // 지연 로딩 여부

  // ── 스키마 ──
  inputSchema: ZodSchema          // 입력 유효성 검증 스키마
  outputSchema: ZodSchema         // 출력 구조 스키마

  // ── 실행 ──
  call(input, context, canUseTool, parentMessage, onProgress)
    → Promise<{ data: Output }>   // 핵심 실행 로직
  validateInput(input)            // 입력 사전 검증
  checkPermissions(input, context) // 권한 확인

  // ── 표시 ──
  description(input)              // 사용자 설명 (권한 프롬프트)
  userFacingName()                // UI 표시명
  prompt()                        // 모델에 제공할 도구 설명
  renderToolUseMessage()          // 도구 호출 UI
  renderToolUseProgressMessage()  // 진행 상태 UI
  renderToolResultMessage()       // 결과 UI
  getToolUseSummary()             // 요약 텍스트
  getActivityDescription()       // 활동 설명 (상태 표시줄)

  // ── 속성 ──
  isConcurrencySafe()             // 동시 실행 안전 여부
  isReadOnly()                    // 읽기 전용 여부
  toAutoClassifierInput()         // 자동 분류기 입력
  mapToolResultToToolResultBlockParam()  // API 결과 변환
  extractSearchText()             // 텍스트 검색용 추출 (선택)
}
```

### 두 도구의 buildTool 구현 비교

| 속성 | WebSearchTool | WebFetchTool |
| --- | --- | --- |
| `name` | `'WebSearch'` | `'WebFetch'` |
| `userFacingName` | `'Web Search'` | `'Fetch'` |
| `searchHint` | `'search the web for current information'` | `'fetch and extract content from a URL'` |
| `maxResultSizeChars` | `100_000` | `100_000` |
| `shouldDefer` | `true` | `true` |
| `isConcurrencySafe` | `true` | `true` |
| `isReadOnly` | `true` | `true` |
| `isEnabled` | 프로바이더별 분기 | 항상 활성 (기본값) |
| `checkPermissions` | passthrough | 3단계 (사전승인 → 규칙 → ask) |
| `extractSearchText` | `''` (빈 문자열) | 기본값 (구현 없음) |
