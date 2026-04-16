# query.ts & QueryEngine.ts 상세 분석

> Claude Code의 핵심 에이전트 루프와 세션 관리 엔진에 대한 심층 분석 문서

---

## 목차

1. [개요](#1-%EA%B0%9C%EC%9A%94)
2. [query.ts — 핵심 쿼리 루프 (1729줄)](#2-queryts--%ED%95%B5%EC%8B%AC-%EC%BF%BC%EB%A6%AC-%EB%A3%A8%ED%94%84-1729%EC%A4%84)
   - [역할](#21-%EC%97%AD%ED%95%A0)
   - [아키텍처: AsyncGenerator 패턴](#22-%EC%95%84%ED%82%A4%ED%85%8D%EC%B2%98-asyncgenerator-%ED%8C%A8%ED%84%B4)
   - [핵심 데이터 구조](#23-%ED%95%B5%EC%8B%AC-%EB%8D%B0%EC%9D%B4%ED%84%B0-%EA%B5%AC%EC%A1%B0)
   - [루프 한 바퀴의 흐름](#24-%EB%A3%A8%ED%94%84-%ED%95%9C-%EB%B0%94%ED%80%B4%EC%9D%98-%ED%9D%90%EB%A6%84)
   - [7가지 Continue 사유](#25-7%EA%B0%80%EC%A7%80-continue-%EC%82%AC%EC%9C%A0)
   - [10가지 Terminal 사유](#26-10%EA%B0%80%EC%A7%80-terminal-%EC%82%AC%EC%9C%A0)
   - [컨텍스트 관리 계층 (4단계 압축)](#27-%EC%BB%A8%ED%85%8D%EC%8A%A4%ED%8A%B8-%EA%B4%80%EB%A6%AC-%EA%B3%84%EC%B8%B5-4%EB%8B%A8%EA%B3%84-%EC%95%95%EC%B6%95)
   - [에러 복구 전략](#28-%EC%97%90%EB%9F%AC-%EB%B3%B5%EA%B5%AC-%EC%A0%84%EB%9E%B5)
   - [스트리밍 도구 실행](#29-%EC%8A%A4%ED%8A%B8%EB%A6%AC%EB%B0%8D-%EB%8F%84%EA%B5%AC-%EC%8B%A4%ED%96%89)
3. [QueryEngine.ts — 세션/에이전트 상태 관리 (1296줄)](#3-queryenginets--%EC%84%B8%EC%85%98%EC%97%90%EC%9D%B4%EC%A0%84%ED%8A%B8-%EC%83%81%ED%83%9C-%EA%B4%80%EB%A6%AC-1296%EC%A4%84)
   - [역할](#31-%EC%97%AD%ED%95%A0)
   - [클래스 구조](#32-%ED%81%B4%EB%9E%98%EC%8A%A4-%EA%B5%AC%EC%A1%B0)
   - [submitMessage() 흐름](#33-submitmessage-%ED%9D%90%EB%A6%84)
   - [SDK 메시지 타입](#34-sdk-%EB%A9%94%EC%8B%9C%EC%A7%80-%ED%83%80%EC%9E%85-sdkmessage)
   - [ask() 편의 래퍼](#35-ask-%ED%8E%B8%EC%9D%98-%EB%9E%98%ED%8D%BC)
4. [두 파일의 관계](#4-%EB%91%90-%ED%8C%8C%EC%9D%BC%EC%9D%98-%EA%B4%80%EA%B3%84)
5. [주요 의존성 맵](#5-%EC%A3%BC%EC%9A%94-%EC%9D%98%EC%A1%B4%EC%84%B1-%EB%A7%B5)
6. [Feature Flag 목록](#6-feature-flag-%EB%AA%A9%EB%A1%9D)

---

## 1. 개요

`query.ts`와 `QueryEngine.ts`는 Claude Code의 **에이전트 루프(agentic loop)** 를 구성하는 핵심 파일이다.

| 파일 | 줄 수 | 핵심 역할 |
| --- | --- | --- |
| `query.ts` | 1729 | 모델 API 호출 → 스트리밍 → 도구 실행의 무한 루프 |
| `QueryEngine.ts` | 1296 | 세션 라이프사이클, 상태 보존, SDK 인터페이스 |

사용자가 프롬프트를 입력하면 `QueryEngine.submitMessage()` → `query()` → `queryLoop()` 순으로 호출되어, 모델이 도구 호출 없이 응답을 완료할 때까지 반복 실행된다.

---

## 2. query.ts — 핵심 쿼리 루프 (1729줄)

### 2.1 역할

Claude Code의 **에이전트 루프** 구현체. 사용자 입력 → 모델 API 호출 → 스트리밍 응답 처리 → 도구 실행 → 다음 턴 반복의 전체 사이클을 담당한다. 이 파일은 모델 API와의 상호작용에만 집중하며, 세션 상태 보존은 `QueryEngine.ts`에 위임한다.

### 2.2 아키텍처: AsyncGenerator 패턴

```
query()          (L219-239)  — 엔트리포인트, lifecycle 알림
  └─ yield* queryLoop()  (L241-1728) — 실제 무한 루프
       └─ while(true) { ... continue/return }
```

두 함수 모두 `AsyncGenerator`로 구현되어, 스트리밍 소비자(REPL, SDK, Desktop)가 메시지를 실시간으로 처리할 수 있다.

- `query()` (L219): 엔트리포인트. `queryLoop()`에 `yield*`로 위임한 후, 정상 종료 시 소비된 커맨드의 lifecycle 알림(`completed`)을 처리한다. throw나 `.return()` 시에는 알림이 생략되어, 실패한 턴과 성공한 턴을 구분할 수 있다.
- `queryLoop()` (L241): 실제 무한 루프. `State` 객체로 반복 간 상태를 관리하며, `continue` 시 `state = next`로 전체 상태를 원자적으로 갱신한다.

### 2.3 핵심 데이터 구조

#### QueryParams (L181-198)

```typescript
export type QueryParams = {
  messages: Message[]                    // 대화 히스토리
  systemPrompt: SystemPrompt             // 시스템 프롬프트
  userContext: { [k: string]: string }   // 사용자 컨텍스트 (prepend)
  systemContext: { [k: string]: string } // 시스템 컨텍스트 (append)
  canUseTool: CanUseToolFn               // 도구 사용 권한 판별 함수
  toolUseContext: ToolUseContext          // 도구 실행 컨텍스트
  fallbackModel?: string                 // 장애 시 대체 모델
  querySource: QuerySource               // 호출 출처 (repl/sdk/compact 등)
  maxOutputTokensOverride?: number       // 출력 토큰 한도 오버라이드
  maxTurns?: number                      // 최대 턴 수 제한
  skipCacheWrite?: boolean               // 캐시 쓰기 건너뛰기
  taskBudget?: { total: number }         // API task_budget (토큰 한도)
  deps?: QueryDeps                       // 테스트용 의존성 주입
}
```

#### State (L204-217) — 루프 반복 간 가변 상태

```typescript
type State = {
  messages: Message[]                              // 현재까지의 메시지 배열
  toolUseContext: ToolUseContext                    // 도구 실행 컨텍스트
  autoCompactTracking: AutoCompactTrackingState     // 자동 압축 추적
  maxOutputTokensRecoveryCount: number              // 출력 토큰 초과 복구 횟수
  hasAttemptedReactiveCompact: boolean              // 반응형 압축 시도 여부
  maxOutputTokensOverride: number | undefined       // 출력 토큰 오버라이드
  pendingToolUseSummary: Promise<...> | undefined   // 비동기 도구 요약
  stopHookActive: boolean | undefined               // Stop Hook 활성 여부
  turnCount: number                                 // 현재 턴 번호
  transition: Continue | undefined                  // 이전 continue 사유
}
```

> **설계 포인트**: `state = next`로 원자적 갱신하여, 9개 필드를 개별 할당하는 것보다 안전하고 가독성이 높다.

### 2.4 루프 한 바퀴의 흐름

루프의 한 반복(iteration)은 5단계로 구성된다.

```
┌─────────────────────────────────────────────────────┐
│ 1단계: 전처리 (Pre-processing)         L307~L598    │
│    ├── Skill Discovery Prefetch 시작                │
│    ├── stream_request_start yield                   │
│    ├── Query Tracking (chainId, depth) 갱신         │
│    ├── Tool Result Budget 적용 (도구 결과 크기 제한)  │
│    ├── Snip Compact (오래된 히스토리 잘라내기)         │
│    ├── Microcompact (도구 결과 축소)                 │
│    ├── Context Collapse (컨텍스트 접기)              │
│    ├── Autocompact (LLM 기반 자동 요약 압축)         │
│    ├── 시스템 프롬프트 조합                           │
│    └── Blocking Limit 체크 (수동 /compact 여유 확보)  │
├─────────────────────────────────────────────────────┤
│ 2단계: API 호출 & 스트리밍              L654~L863    │
│    ├── deps.callModel() → for await 스트리밍 루프     │
│    ├── 어시스턴트 메시지 수집 (assistantMessages[])   │
│    ├── tool_use 블록 감지 → needsFollowUp = true     │
│    ├── StreamingToolExecutor로 도구 조기 병렬 실행    │
│    ├── backfillObservableInput (SDK 전달용 입력 보강) │
│    ├── 에러 위드홀딩 (PTL, max_output, media)        │
│    ├── Tombstone 처리 (스트리밍 중 fallback 전환 시)  │
│    └── Cached Microcompact 경계 메시지 yield          │
├─────────────────────────────────────────────────────┤
│ 3단계: 포스트 스트리밍 복구             L1062~L1357   │
│    ├── Prompt-too-long 복구                          │
│    │   ├── 1차: Context Collapse Drain               │
│    │   └── 2차: Reactive Compact                     │
│    ├── Media size error → Reactive Compact            │
│    ├── Max output tokens 복구                        │
│    │   ├── 1차: 8k→64k Escalation                    │
│    │   └── 2-4차: Recovery message (최대 3회)         │
│    ├── Stop Hooks 실행 (정상 종료 시만)               │
│    ├── Token Budget 연속 체크                        │
│    └── 종료 판정 (return) 또는 도구 실행 진행          │
├─────────────────────────────────────────────────────┤
│ 4단계: 도구 실행                        L1360~L1408  │
│    ├── StreamingToolExecutor.getRemainingResults()    │
│    │   또는 runTools() (비스트리밍 폴백)              │
│    ├── 도구 결과 수집 (toolResults[])                 │
│    ├── Hook 중단 감지 (hook_stopped_continuation)     │
│    └── abort 처리 (도구 실행 중 Ctrl+C)               │
├─────────────────────────────────────────────────────┤
│ 5단계: 후처리 & 다음 턴                 L1580~L1728  │
│    ├── Attachment 메시지 수집                         │
│    │   ├── getAttachmentMessages() (파일 변경 등)     │
│    │   ├── Memory Prefetch 소비                      │
│    │   └── Skill Discovery Prefetch 소비             │
│    ├── 큐 커맨드 소비 & lifecycle 알림                │
│    ├── MCP 도구 새로고침 (refreshTools)               │
│    ├── Task Summary 생성 (BG_SESSIONS)               │
│    ├── maxTurns 체크                                 │
│    └── state = next → continue (다음 턴으로)          │
└─────────────────────────────────────────────────────┘
```

### 2.5 7가지 Continue 사유

루프가 `return`하지 않고 `continue`로 재시작하는 7가지 경우:

| transition.reason | 설명 | 위치 |
| --- | --- | --- |
| `collapse_drain_retry` | Context Collapse 드레인 후 재시도 | L1099-1116 |
| `reactive_compact_retry` | 반응형 압축(RC) 후 재시도 | L1152-1165 |
| `max_output_tokens_escalate` | 8k→64k 출력 한도 에스컬레이션 | L1207-1220 |
| `max_output_tokens_recovery` | 출력 초과 시 "이어서 작성" 요청 (최대 3회) | L1231-1251 |
| `stop_hook_blocking` | Stop Hook이 차단 에러 반환 | L1283-1305 |
| `token_budget_continuation` | 토큰 예산 내 자동 계속 | L1321-1340 |
| `next_turn` | 도구 실행 후 다음 턴 (정상 흐름) | L1715-1727 |

> **설계 포인트**: `transition` 필드는 디버깅과 테스트를 위해 존재한다. 이전 반복에서 왜 `continue`했는지를 추적하여, 복구 경로가 올바르게 실행되었는지 검증할 수 있다.

### 2.6 10가지 Terminal 사유

루프가 `return`으로 종료하는 경우:

| reason | 설명 | 위치 |
| --- | --- | --- |
| `blocking_limit` | 토큰 블로킹 한도 도달 (수동 /compact 유도) | L646 |
| `image_error` | 이미지 크기/리사이즈 에러 | L977 |
| `prompt_too_long` | PTL 복구 실패 (RC 불가) | L1175-1182 |
| `model_error` | 모델 API 에러 (예외) | L996 |
| `aborted_streaming` | 스트리밍 중 사용자 중단 | L1051 |
| `aborted_tools` | 도구 실행 중 사용자 중단 | L1515 |
| `hook_stopped` | Hook이 도구 계속 진행 차단 | L1521 |
| `stop_hook_prevented` | Stop Hook이 continuation 차단 | L1279 |
| `completed` | 정상 완료 (도구 호출 없이 응답 종료) | L1357 |
| `max_turns` | 최대 턴 수 초과 | L1711 |

### 2.7 컨텍스트 관리 계층 (4단계 압축)

Claude Code는 긴 대화에서 컨텍스트 윈도우를 관리하기 위해 4단계 압축 파이프라인을 사용한다. 각 단계는 독립적이며, 앞 단계가 충분히 줄이면 뒷 단계는 no-op이 된다.

```
입력 메시지 (messagesForQuery)
  │
  ▼
┌────────────────────────────────────────────────┐
│ 1. Snip Compact (L401-410)                      │
│    HISTORY_SNIP feature flag                    │
│    토큰 기반으로 오래된 메시지를 잘라냄           │
│    tokensFreed 값을 반환하여 후속 단계에 전달     │
│    경계 메시지(boundaryMessage) yield            │
├────────────────────────────────────────────────┤
│ 2. Microcompact (L414-426)                      │
│    도구 결과 내 불필요 내용 축소                  │
│    CACHED_MICROCOMPACT: 캐시 편집 기반 압축       │
│    경계 메시지는 API 응답 후 deferred yield       │
├────────────────────────────────────────────────┤
│ 3. Context Collapse (L440-447)                  │
│    CONTEXT_COLLAPSE feature flag                │
│    읽기 전용 프로젝션 (원본 훼손 없음)            │
│    메시지를 접어서 토큰 사용 감소                 │
│    Autocompact보다 먼저 실행 (세밀한 컨텍스트 유지)│
├────────────────────────────────────────────────┤
│ 4. Autocompact (L454-543)                       │
│    LLM 호출로 전체 히스토리를 요약 압축           │
│    가장 비용이 크지만 가장 효과적                 │
│    성공 시 tracking 리셋, 실패 시 circuit breaker │
│    task_budget remaining 조정                    │
└────────────────────────────────────────────────┘
  │
  ▼
압축된 메시지 → API 호출
```

### 2.8 에러 복구 전략

#### Prompt-too-long (413) 복구

```
PTL 감지 (위드홀딩)
  │
  ├─ 1차: Context Collapse Drain
  │   └─ 대기 중인 collapse를 전부 커밋
  │   └─ 성공 시 → collapse_drain_retry continue
  │
  ├─ 2차: Reactive Compact
  │   └─ 긴급 LLM 요약 압축
  │   └─ 성공 시 → reactive_compact_retry continue
  │
  └─ 실패: 에러 메시지 yield + return prompt_too_long
```

#### Max Output Tokens 복구

```
max_output_tokens 감지 (위드홀딩)
  │
  ├─ 1차: Escalation (8k→64k)
  │   └─ 환경변수 미설정 + statsig 활성 시
  │   └─ max_output_tokens_escalate continue
  │
  ├─ 2-4차: Recovery Message
  │   └─ "이어서 작성" 메타 메시지 주입
  │   └─ 최대 3회 (MAX_OUTPUT_TOKENS_RECOVERY_LIMIT)
  │
  └─ 실패: 위드홀딩된 에러 메시지 yield
```

#### Model Fallback 복구

```
FallbackTriggeredError 발생
  │
  ├─ 스트리밍 중 fallback (streamingFallbackOccured)
  │   └─ Tombstone yield (orphaned 메시지 제거)
  │   └─ StreamingToolExecutor 재생성
  │   └─ 같은 while 루프에서 재시도
  │
  └─ catch 절 fallback (innerError)
      └─ 모델 전환 + 경고 메시지 yield
      └─ Thinking 시그니처 스트립 (ant only)
      └─ attemptWithFallback = true → 재시도
```

### 2.9 스트리밍 도구 실행

`StreamingToolExecutor`를 통해 모델 응답이 스트리밍되는 동안 도구를 병렬 실행한다.

```
모델 스트리밍 (for await)
  │
  ├─ tool_use 블록 감지
  │   └─ streamingToolExecutor.addTool(block, message)
  │       └─ 도구 실행 즉시 시작 (Promise)
  │
  ├─ 스트리밍 중 완료된 결과 수확
  │   └─ streamingToolExecutor.getCompletedResults()
  │       └─ yield result.message + toolResults push
  │
  └─ 스트리밍 종료 후 나머지 수확
      └─ streamingToolExecutor.getRemainingResults()
          └─ 모든 남은 도구 실행 대기 + yield
```

> **이점**: 모델이 여러 도구를 한 번에 호출할 때, 첫 번째 도구가 실행되는 동안 모델은 계속 스트리밍하고, 나머지 도구 블록도 도착 즉시 실행을 시작한다.

---

## 3. QueryEngine.ts — 세션/에이전트 상태 관리 (1296줄)

### 3.1 역할

대화 세션의 **라이프사이클 소유자**. `query.ts`의 루프를 감싸면서 세션 상태, 권한, 사용량 추적, 트랜스크립트 저장을 관리한다. 하나의 `QueryEngine` 인스턴스가 하나의 대화 세션에 대응하며, 여러 번의 `submitMessage()` 호출에 걸쳐 상태를 유지한다.

### 3.2 클래스 구조

```typescript
export class QueryEngine {
  // ── 설정 (불변) ──
  private config: QueryEngineConfig          // 생성 시 주입된 전체 설정

  // ── 세션 상태 (턴 간 유지) ──
  private mutableMessages: Message[]         // 대화 히스토리
  private readFileState: FileStateCache      // 파일 읽기 캐시
  private totalUsage: NonNullableUsage       // 누적 API 사용량 (input/output tokens)
  private permissionDenials: SDKPermissionDenial[]  // 권한 거부 기록 (SDK 보고용)
  private abortController: AbortController   // 중단 제어

  // ── 턴별 상태 (submitMessage 시작 시 리셋) ──
  private discoveredSkillNames: Set<string>  // 스킬 발견 추적
  private loadedNestedMemoryPaths: Set<string>  // 중첩 메모리 로드 추적
  private hasHandledOrphanedPermission: boolean // 고아 권한 처리 (1회)

  // ── 공개 메서드 ──
  async *submitMessage(prompt, options?)     // 턴 실행 (핵심)
  interrupt()                                // 중단
  getMessages(): readonly Message[]          // 읽기 전용 메시지 접근
  getReadFileState(): FileStateCache         // 파일 캐시 접근
  getSessionId(): string                     // 세션 ID
  setModel(model: string)                    // 런타임 모델 변경
}
```

#### QueryEngineConfig (L130-173)

```typescript
export type QueryEngineConfig = {
  cwd: string                          // 작업 디렉토리
  tools: Tools                         // 사용 가능한 도구 목록
  commands: Command[]                  // 슬래시 커맨드 목록
  mcpClients: MCPServerConnection[]    // MCP 서버 연결
  agents: AgentDefinition[]            // 에이전트 정의
  canUseTool: CanUseToolFn             // 권한 판별 함수
  getAppState: () => AppState          // 앱 상태 읽기
  setAppState: (f) => void             // 앱 상태 갱신
  initialMessages?: Message[]          // 초기 메시지 (세션 복원 등)
  readFileCache: FileStateCache        // 파일 읽기 캐시
  customSystemPrompt?: string          // 커스텀 시스템 프롬프트
  appendSystemPrompt?: string          // 추가 시스템 프롬프트
  userSpecifiedModel?: string          // 사용자 지정 모델
  fallbackModel?: string              // 대체 모델
  thinkingConfig?: ThinkingConfig      // Thinking 모드 설정
  maxTurns?: number                    // 최대 턴 수
  maxBudgetUsd?: number                // 최대 비용 한도 (USD)
  taskBudget?: { total: number }       // 토큰 예산
  jsonSchema?: Record<string, unknown> // Structured Output 스키마
  verbose?: boolean                    // 상세 로깅
  replayUserMessages?: boolean         // 사용자 메시지 에코
  handleElicitation?: (...)            // MCP elicitation 핸들러
  includePartialMessages?: boolean     // 스트림 이벤트 포함
  setSDKStatus?: (status) => void      // SDK 상태 콜백
  abortController?: AbortController    // 외부 abort 제어
  orphanedPermission?: OrphanedPermission // 고아 권한 처리
  snipReplay?: (msg, store) => ...     // Snip 경계 핸들러
}
```

### 3.3 submitMessage() 흐름

`submitMessage()`는 하나의 "턴"을 실행하는 핵심 메서드다. 사용자 입력을 받아 모델 응답이 완료될 때까지의 전체 과정을 관리한다.

```
submitMessage(prompt, options?)
  │
  ▼
┌──────────────────────────────────────────────────┐
│ 1. 설정 초기화                        L209~L334  │
│    ├── config 디스트럭처링                        │
│    ├── discoveredSkillNames.clear() (턴별 리셋)   │
│    ├── setCwd(cwd) (작업 디렉토리 설정)           │
│    ├── canUseTool 래핑 (권한 거부 추적)            │
│    ├── 모델 결정 (userSpecified → parseUser...)   │
│    ├── Thinking 설정 결정 (adaptive/disabled)     │
│    ├── 시스템 프롬프트 조합                        │
│    │   [default] + [memory] + [custom] + [append]│
│    └── Structured Output Hook 등록                │
├──────────────────────────────────────────────────┤
│ 2. 사용자 입력 처리                   L335~L463   │
│    ├── processUserInput() 호출                    │
│    │   ├── 슬래시 커맨드 파싱 & 실행              │
│    │   ├── 입력 변환 → messagesFromUserInput      │
│    │   └── shouldQuery 판정                      │
│    ├── mutableMessages.push(...messagesFromUserInput) │
│    ├── 트랜스크립트 저장 (recordTranscript)        │
│    │   ├── bare 모드: fire-and-forget             │
│    │   └── 일반: await (kill 시 복원 가능)         │
│    └── 권한 컨텍스트 갱신 (allowedTools)           │
├──────────────────────────────────────────────────┤
│ 3. shouldQuery = false 분기          L556~L639    │
│    ├── 로컬 슬래시 커맨드 결과 yield               │
│    │   ├── SDKUserMessageReplay (stdout/stderr)   │
│    │   └── SDKLocalCommandOutputMessage            │
│    ├── 트랜스크립트 저장                           │
│    └── result(success) yield → return              │
├──────────────────────────────────────────────────┤
│ 4. Skills & Plugins 로드             L529~L551    │
│    ├── getSlashCommandToolSkills(cwd)              │
│    ├── loadAllPluginsCacheOnly()                   │
│    └── buildSystemInitMessage() yield              │
├──────────────────────────────────────────────────┤
│ 5. query() 루프 실행 (for await)     L675~L1049   │
│    ├── assistant 메시지                            │
│    │   └─ mutableMessages push + normalizeMessage  │
│    ├── user 메시지                                 │
│    │   └─ mutableMessages push + turnCount++       │
│    ├── progress 메시지                             │
│    │   └─ mutableMessages push + transcript 저장   │
│    ├── stream_event                                │
│    │   ├── message_start → usage 리셋              │
│    │   ├── message_delta → usage 갱신 + stop_reason│
│    │   └── message_stop → totalUsage 누적          │
│    ├── attachment                                  │
│    │   ├── structured_output → 캡처                │
│    │   ├── max_turns_reached → error result        │
│    │   └── queued_command → replay                 │
│    ├── system                                      │
│    │   ├── compact_boundary → GC 해제 + SDK 전달   │
│    │   ├── snip_boundary → snipReplay 실행         │
│    │   └── api_retry → SDK 전달                    │
│    └── tool_use_summary → SDK 전달                 │
├──────────────────────────────────────────────────┤
│ 6. 종료 체크                         L972~L1049   │
│    ├── maxBudgetUsd 초과 → error_max_budget_usd    │
│    └── structuredOutput 재시도 초과 → error         │
├──────────────────────────────────────────────────┤
│ 7. 최종 결과 yield                   L1058~L1156  │
│    ├── transcript flush                            │
│    ├── isResultSuccessful 판정                     │
│    │   ├── false → error_during_execution          │
│    │   └── true → result(success)                  │
│    └── textResult / structuredOutput 추출           │
└──────────────────────────────────────────────────┘
```

### 3.4 SDK 메시지 타입 (SDKMessage)

`QueryEngine`이 yield하는 메시지 종류와 용도:

| type | subtype | 설명 |
| --- | --- | --- |
| `system` | `init` | 세션 초기화 정보 (도구, MCP, 모델, 권한, 스킬 등) |
| `user` | (replay) | 사용자 메시지 에코 (replayUserMessages 활성 시) |
| `assistant` | — | 모델 응답 (텍스트, 도구 호출, thinking) |
| `stream_event` | — | 스트리밍 이벤트 (includePartialMessages 활성 시) |
| `system` | `compact_boundary` | 압축 경계 신호 (UI에서 "요약됨" 표시) |
| `system` | `api_retry` | API 재시도 알림 (재시도 횟수, 대기 시간) |
| `tool_use_summary` | — | 도구 사용 요약 (Haiku로 비동기 생성) |
| `result` | `success` | 정상 완료 (비용, 사용량, 턴 수 포함) |
| `result` | `error_max_turns` | 최대 턴 초과 |
| `result` | `error_max_budget_usd` | 비용 한도 초과 |
| `result` | `error_during_execution` | 실행 중 에러 |
| `result` | `error_max_structured_output_retries` | 구조화 출력 재시도 초과 |

### 3.5 ask() 편의 래퍼

`ask()` (L1186-1295)는 `QueryEngine`을 1회용으로 생성하고 `submitMessage()`를 호출하는 편의 함수다.

```typescript
export async function* ask({
  prompt, cwd, tools, mcpClients, canUseTool,
  maxTurns, maxBudgetUsd, taskBudget,
  // ... 기타 설정
}) {
  const engine = new QueryEngine({
    cwd, tools, commands, mcpClients, agents,
    canUseTool, getAppState, setAppState,
    initialMessages: mutableMessages,
    readFileCache: cloneFileStateCache(getReadFileCache()),
    // ... snipReplay 등 feature-gated 설정
  })

  try {
    yield* engine.submitMessage(prompt, { uuid: promptUuid, isMeta })
  } finally {
    setReadFileCache(engine.getReadFileState())  // 파일 캐시 복원
  }
}
```

> **용도**: SDK/Headless 모드에서 단일 프롬프트를 실행할 때 사용. REPL은 `QueryEngine`을 직접 생성하여 여러 턴에 걸쳐 재사용한다.

---

## 4. 두 파일의 관계

```
┌──────────────────────────────────────────────────┐
│                 QueryEngine.ts                    │
│            (세션 소유자, SDK 인터페이스)             │
│                                                   │
│  ┌─ submitMessage(prompt) ──────────────────────┐ │
│  │                                               │ │
│  │  processUserInput()  →  메시지 준비           │ │
│  │          │                                    │ │
│  │          ▼                                    │ │
│  │  ┌─ query() ─────────────────────────────┐   │ │
│  │  │                                        │   │ │
│  │  │  ┌─ queryLoop() ──────────────────┐   │   │ │
│  │  │  │                                 │   │   │ │
│  │  │  │  while(true) {                  │   │   │ │
│  │  │  │    ┌──────────────────────┐     │   │   │ │
│  │  │  │    │ 1. 전처리 (압축 4단계) │     │   │   │ │
│  │  │  │    │ 2. API 호출 & 스트리밍 │     │   │   │ │
│  │  │  │    │ 3. 에러 복구          │     │   │   │ │
│  │  │  │    │ 4. 도구 실행          │     │   │   │ │
│  │  │  │    │ 5. 후처리 & 어태치먼트 │     │   │   │ │
│  │  │  │    └──────────────────────┘     │   │   │ │
│  │  │  │    → continue (다음 턴)         │   │   │ │
│  │  │  │    → return (종료)              │   │   │ │
│  │  │  │  }                              │   │   │ │
│  │  │  └─────────────────────────────────┘   │   │ │
│  │  │                                        │   │ │
│  │  │  yield ──→ StreamEvent | Message        │   │ │
│  │  └────────────────────────────────────────┘   │ │
│  │          │                                    │ │
│  │          ▼                                    │ │
│  │  for await (message of query()) {             │ │
│  │    ├─ mutableMessages.push()   (상태 보존)    │ │
│  │    ├─ totalUsage 누적          (비용 추적)    │ │
│  │    ├─ recordTranscript()       (영속화)       │ │
│  │    ├─ normalizeMessage()       (SDK 변환)     │ │
│  │    └─ yield → SDK 소비자       (실시간 전달)   │ │
│  │  }                                            │ │
│  │          │                                    │ │
│  │          ▼                                    │ │
│  │  yield result(success/error)                  │ │
│  └───────────────────────────────────────────────┘ │
│                                                   │
│  interrupt()  →  abortController.abort()          │
│  getMessages() →  readonly Message[]              │
│  setModel()   →  런타임 모델 변경                   │
└──────────────────────────────────────────────────┘
```

### 책임 분리 원칙

| 관심사 | query.ts | QueryEngine.ts |
| --- | --- | --- |
| 모델 API 호출 | O | X |
| 스트리밍 처리 | O | X (이벤트 소비만) |
| 도구 실행 오케스트레이션 | O | X |
| 컨텍스트 압축 | O | X |
| 에러 복구 (PTL, MOT) | O | X |
| 세션 상태 보존 | X | O |
| 트랜스크립트 저장 | X | O |
| API 사용량 누적 | X | O |
| 권한 거부 추적 | X | O |
| 사용자 입력 전처리 | X | O |
| SDK 메시지 변환 | X | O |
| 비용 한도 체크 | X | O |

> **핵심 원칙**: `query.ts`는 **stateless loop** — 모든 상태는 `State` 객체로 주고받는다. `QueryEngine.ts`는 **stateful session** — `mutableMessages`, `totalUsage` 등을 턴 간에 유지한다.

---

## 5. 주요 의존성 맵

### query.ts의 핵심 의존성

```
query.ts
  ├── services/
  │   ├── api/             → callModel, withRetry, errors, dumpPrompts
  │   ├── compact/         → autoCompact, reactiveCompact, snipCompact, compact
  │   ├── contextCollapse/ → applyCollapsesIfNeeded, recoverFromOverflow
  │   ├── tools/           → StreamingToolExecutor, toolOrchestration
  │   ├── toolUseSummary/  → generateToolUseSummary (Haiku)
  │   └── analytics/       → logEvent, growthbook
  ├── query/
  │   ├── config.ts        → buildQueryConfig (feature flags, gates)
  │   ├── deps.ts          → productionDeps (callModel, autocompact 등)
  │   ├── transitions.ts   → Terminal, Continue 타입
  │   ├── stopHooks.ts     → handleStopHooks
  │   └── tokenBudget.ts   → createBudgetTracker, checkTokenBudget
  ├── utils/
  │   ├── messages.ts      → createUserMessage, normalizeMessagesForAPI
  │   ├── attachments.ts   → getAttachmentMessages, memoryPrefetch
  │   ├── tokens.ts        → tokenCountWithEstimation
  │   ├── toolResultStorage.ts → applyToolResultBudget
  │   └── hooks.ts         → executeStopFailureHooks
  └── Tool.ts              → findToolByName, ToolUseContext
```

### QueryEngine.ts의 핵심 의존성

```
QueryEngine.ts
  ├── query.ts             → query() 함수 (핵심 루프)
  ├── utils/
  │   ├── processUserInput/→ processUserInput (슬래시 커맨드 등)
  │   ├── queryContext.ts  → fetchSystemPromptParts
  │   ├── sessionStorage.ts→ recordTranscript, flushSessionStorage
  │   ├── model/model.ts   → getMainLoopModel, parseUserSpecifiedModel
  │   ├── queryHelpers.ts  → handleOrphanedPermission, isResultSuccessful
  │   ├── messages/        → mappers, systemInit
  │   └── config.ts        → getGlobalConfig
  ├── services/
  │   ├── api/claude.ts    → accumulateUsage, updateUsage
  │   └── mcp/types.ts     → MCPServerConnection
  ├── commands.ts          → getSlashCommandToolSkills
  ├── cost-tracker.ts      → getTotalCost, getTotalAPIDuration
  ├── memdir/              → loadMemoryPrompt, hasAutoMemPathOverride
  └── state/AppState.ts    → AppState
```

---

## 6. Feature Flag 목록

`query.ts`와 `QueryEngine.ts`에서 사용하는 `feature()` 게이트:

| Feature Flag | 용도 | 파일 |
| --- | --- | --- |
| `REACTIVE_COMPACT` | 반응형 압축 (PTL/미디어 에러 복구) | query.ts |
| `CONTEXT_COLLAPSE` | 컨텍스트 접기 (읽기 전용 프로젝션) | query.ts |
| `HISTORY_SNIP` | 오래된 히스토리 잘라내기 | query.ts, QueryEngine.ts |
| `CACHED_MICROCOMPACT` | 캐시 편집 기반 마이크로압축 | query.ts |
| `EXPERIMENTAL_SKILL_SEARCH` | 스킬 발견 프리페치 | query.ts |
| `TEMPLATES` | Job Classifier (템플릿 매칭) | query.ts |
| `BG_SESSIONS` | 백그라운드 세션 (task summary) | query.ts |
| `TOKEN_BUDGET` | 토큰 예산 자동 계속 | query.ts |
| `CHICAGO_MCP` | Computer Use 정리 (auto-unhide, lock) | query.ts |
| `COORDINATOR_MODE` | 코디네이터 모드 (멀티에이전트) | QueryEngine.ts |

> **빌드 최적화**: `feature()`는 `bun:bundle`의 dead code elimination을 위한 게이트다. `if/ternary` 조건에서만 사용하며, false인 feature의 `require()` 코드는 빌드에서 제거된다.