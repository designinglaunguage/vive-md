# query.ts 심층 분석 — Claude Code CLI의 심장부

> **파일**: `src/query.ts` (1,729줄)\
> **역할**: 모든 대화의 핵심 루프. 컨텍스트 조립 → 압축 → API 스트리밍 → 도구 실행 → 에러 복구를 반복\
> **분석일**: 2026-03-31

---

## 1. 진입점 구조

```
query(params)              ← 외부 진입점 (line 219)
  └── yield* queryLoop()   ← 핵심 while(true) 루프 (line 241~1728)
```

`query()`는 얇은 래퍼로, `queryLoop()`에 위임한 뒤 소비된 명령의 라이프사이클을 `completed`로 통지합니다.

### QueryParams (line 181~199)

```ts
type QueryParams = {
  messages: Message[]              // 전체 대화 히스토리
  systemPrompt: SystemPrompt       // 시스템 프롬프트
  userContext: { [k: string]: string }    // CLAUDE.md, 날짜 등
  systemContext: { [k: string]: string }  // git status, cache breaker
  canUseTool: CanUseToolFn         // 도구 권한 판정 함수
  toolUseContext: ToolUseContext    // 도구 실행 환경 (tools, model, abort 등)
  fallbackModel?: string           // 폴백 모델 (고수요 시 전환)
  querySource: QuerySource         // 'repl_main_thread' | 'agent:xxx' | 'compact' 등
  maxOutputTokensOverride?: number // 출력 토큰 한도 오버라이드
  maxTurns?: number                // 최대 턴 수 제한
  skipCacheWrite?: boolean         // 캐시 쓰기 건너뛰기
  taskBudget?: { total: number }   // API task_budget (agentic turn 전체 예산)
  deps?: QueryDeps                 // 의존성 주입 (테스트용)
}
```

---

## 2. State 머신

루프는 매 반복마다 불변 `State` 객체를 통째로 교체하는 State 머신 패턴을 사용합니다.

### State 타입 (line 204~217)

```ts
type State = {
  messages: Message[]
  toolUseContext: ToolUseContext
  autoCompactTracking: AutoCompactTrackingState | undefined
  maxOutputTokensRecoveryCount: number       // max_output_tokens 복구 시도 횟수
  hasAttemptedReactiveCompact: boolean       // reactive compact 시도 여부
  maxOutputTokensOverride: number | undefined
  pendingToolUseSummary: Promise<ToolUseSummaryMessage | null> | undefined
  stopHookActive: boolean | undefined
  turnCount: number                          // 현재 턴 번호
  transition: Continue | undefined           // 이전 반복의 종료 사유
}
```

### Transition 종류

| transition.reason | 의미 | 발생 위치 |
|---|---|---|
| `next_turn` | 도구 결과 존재 → 다음 API 호출 | line 1725 |
| `reactive_compact_retry` | prompt_too_long 후 압축 재시도 | line 1162 |
| `collapse_drain_retry` | 컨텍스트 접기 후 재시도 | line 1110 |
| `max_output_tokens_escalate` | 8k→64k 에스컬레이션 | line 1217 |
| `max_output_tokens_recovery` | 출력 한도 도달 후 resume 메시지 | line 1245 |
| `stop_hook_blocking` | 스톱 훅이 차단 에러 반환 | line 1302 |
| `token_budget_continuation` | 예산 내 자동 계속 | line 1338 |

---

## 3. 루프 1회 사이클 상세

### Phase 1: 전처리 (Pre-processing)

5단계 컨텍스트 압축 파이프라인이 **순서대로** 적용됩니다.

#### 1-1. Tool Result Budget (line 379~394)

```
applyToolResultBudget(messagesForQuery, contentReplacementState, ...)
```

- 도구 결과의 **총 크기**가 한도를 초과하면 오래된 결과를 `"persisted to disk"`로 대체
- `contentReplacementState`에 교체 기록 저장 → 세션 재개 시에도 유지
- `agent:*` 또는 `repl_main_thread*` querySource만 디스크에 기록
- **microcompact보다 먼저** 실행 (MC는 tool_use_id 기반이라 내용 교체에 무관)

#### 1-2. Snip Compact (line 401~410)

```
snipCompactIfNeeded(messagesForQuery) → { messages, tokensFreed, boundaryMessage }
```

- `feature('HISTORY_SNIP')` 게이트
- **오래된 메시지를 완전히 제거**하여 토큰 확보
- 보호된 tail(최근 N턴)은 유지
- `tokensFreed`를 autocompact에 전달 (stale usage 보정용)

#### 1-3. Microcompact (line 414~426)

```
deps.microcompact(messagesForQuery, toolUseContext, querySource)
```

- 짧은 연속 메시지를 하나로 압축
- **캐시 효율성 향상** — cached microcompact는 API의 `cache_deleted_input_tokens`로 실제 삭제량 추적
- boundary message는 API 응답 이후에 yield (실제 캐시 삭제량 반영)

#### 1-4. Context Collapse (line 440~447)

```
contextCollapse.applyCollapsesIfNeeded(messagesForQuery, toolUseContext, querySource)
```

- `feature('CONTEXT_COLLAPSE')` 게이트
- 메시지를 "collapse" 단위로 묶어서 **읽기 전용 뷰로 투영**
- 실제 메시지 배열에서는 제거하지 않음 — API 호출 시에만 필터링
- **autocompact보다 먼저** 실행 → collapse로 충분히 줄어들면 autocompact 불필요

#### 1-5. Autocompact (line 454~543)

```
deps.autocompact(messagesForQuery, toolUseContext, cacheSafeParams, querySource, tracking, snipTokensFreed)
```

- 토큰 한도에 도달하면 **별도의 "압축 에이전트"를 호출**하여 대화를 요약
- `buildPostCompactMessages()`로 요약 메시지 + 첨부물 재구성
- 성공 시 `tracking`을 리셋 (turnCounter=0, consecutiveFailures=0)
- `taskBudgetRemaining` 갱신 — compact 전 최종 context window를 차감

### Phase 2: Blocking Limit 체크 (line 628~648)

autocompact가 OFF이고 토큰이 blocking limit에 도달하면 즉시 종료:

```ts
if (isAtBlockingLimit) {
  yield createAssistantAPIErrorMessage({ content: PROMPT_TOO_LONG_ERROR_MESSAGE })
  return { reason: 'blocking_limit' }
}
```

다음 조건에서는 체크를 **건너뜀**:
- compaction 방금 완료 (stale usage)
- `querySource === 'compact'` (압축 에이전트 자체가 deadlock)
- reactive compact 또는 context collapse가 활성 (자체 복구 가능)

### Phase 3: API 스트리밍 (line 652~953)

#### 3-1. Model 호출

```ts
for await (const message of deps.callModel({
  messages: prependUserContext(messagesForQuery, userContext),
  systemPrompt: fullSystemPrompt,
  thinkingConfig, tools, signal, options: { ... }
}))
```

`callModel`에 전달되는 주요 옵션:
- `model`: `getRuntimeMainLoopModel()`로 결정
- `fastMode`: `appState.fastMode` (같은 모델, 빠른 출력)
- `effortValue`: 노력 수준
- `advisorModel`: 어드바이저 모델
- `taskBudget`: `{ total, remaining? }` — remaining은 compact 후에만 설정
- `fallbackModel`: 폴백 모델 (고수요 시)
- `fetchOverride`: `dumpPromptsFetch` (Ant-only 디버깅)

#### 3-2. Streaming Tool Execution (line 838~862)

```ts
if (streamingToolExecutor && !aborted) {
  for (const toolBlock of msgToolUseBlocks) {
    streamingToolExecutor.addTool(toolBlock, message)  // 완성된 tool_use 즉시 등록
  }
  for (const result of streamingToolExecutor.getCompletedResults()) {
    yield result.message  // 완료된 도구 결과 즉시 yield
    toolResults.push(...)
  }
}
```

**핵심**: 모델이 아직 스트리밍 중인데 이미 완성된 tool_use 블록의 도구는 **병렬로 실행**됨. API 지연과 도구 실행 지연이 겹치지 않음.

#### 3-3. Withheld 에러 (line 799~825)

복구 가능한 에러는 yield하지 않고 보류:

| 에러 타입 | 보류 조건 | 복구 방식 |
|---|---|---|
| `prompt_too_long` (413) | context collapse 또는 reactive compact 활성 | collapse drain → reactive compact |
| `max_output_tokens` | 항상 보류 | escalate 8k→64k → recovery 메시지 3회 |
| `media_size_error` | `mediaRecoveryEnabled` | reactive compact의 strip-retry |

보류된 에러는 복구 성공하면 버리고, 실패하면 그때 yield.

#### 3-4. Fallback 처리 (line 894~953)

```ts
catch (innerError) {
  if (innerError instanceof FallbackTriggeredError && fallbackModel) {
    currentModel = fallbackModel
    attemptWithFallback = true
    // orphaned 메시지 tombstone 처리
    // streamingToolExecutor 재생성
    yield createSystemMessage(`Switched to ${renderModelName(fallbackModel)}...`)
    continue  // 같은 요청 재시도
  }
}
```

- 고수요로 원래 모델 사용 불가 시 폴백 모델로 자동 전환
- orphaned assistant 메시지는 tombstone으로 표시 → UI/트랜스크립트에서 제거
- thinking 서명이 모델에 종속되므로 `stripSignatureBlocks()` 실행 (Ant-only)

### Phase 4: 에러 복구 (line 1062~1256)

`needsFollowUp === false`일 때 (모델이 도구를 호출하지 않고 종료) 실행되는 복구 로직.

#### 4-1. Prompt Too Long 복구

```
1단계: Context Collapse drain (line 1090~1117)
  → 이전 transition이 collapse_drain이 아니면 시도
  → 접힌 컨텍스트를 커밋하여 토큰 확보
  → 성공 시 transition: 'collapse_drain_retry'

2단계: Reactive Compact (line 1119~1183)
  → hasAttemptedReactiveCompact가 false일 때만
  → 전체 대화를 요약하여 토큰 확보
  → 성공 시 transition: 'reactive_compact_retry'

실패: yield withheld error → return { reason: 'prompt_too_long' }
```

#### 4-2. Max Output Tokens 복구

```
1단계: Escalate 8k → 64k (line 1195~1221)
  → maxOutputTokensOverride가 undefined일 때만 (1회)
  → 환경변수 CLAUDE_CODE_MAX_OUTPUT_TOKENS 미설정 시
  → transition: 'max_output_tokens_escalate'

2단계: Recovery 메시지 (line 1223~1252)
  → 최대 3회 (MAX_OUTPUT_TOKENS_RECOVERY_LIMIT)
  → "Output token limit hit. Resume directly — no apology, no recap..."
  → transition: 'max_output_tokens_recovery'

소진: yield withheld error → 계속 진행 (stop hooks로)
```

### Phase 5: Stop Hooks (line 1267~1306)

```ts
const stopHookResult = yield* handleStopHooks(
  messagesForQuery, assistantMessages, systemPrompt, userContext,
  systemContext, toolUseContext, querySource, stopHookActive,
)
```

- `preventContinuation: true` → `return { reason: 'stop_hook_prevented' }`
- `blockingErrors.length > 0` → 에러를 메시지에 추가하고 재시도 (transition: `stop_hook_blocking`)
- API 에러 메시지일 때는 stop hooks **스킵** (death spiral 방지)

### Phase 6: Token Budget (line 1308~1355)

```ts
const decision = checkTokenBudget(budgetTracker, agentId, budget, turnTokens)
// decision.action: 'continue' | 'stop'
```

- `feature('TOKEN_BUDGET')` 게이트
- +500k auto-continue 기능 (task_budget과는 별개)
- `continue` → nudge 메시지 주입 후 루프 계속
- diminishing returns 감지 시 조기 종료

### Phase 7: 도구 실행 (line 1360~1409)

```ts
const toolUpdates = streamingToolExecutor
  ? streamingToolExecutor.getRemainingResults()  // 스트리밍 중 미완료 도구
  : runTools(toolUseBlocks, assistantMessages, canUseTool, toolUseContext)  // 전통적 순차 실행

for await (const update of toolUpdates) {
  if (update.message) yield update.message
  if (update.newContext) updatedToolUseContext = { ...update.newContext, queryTracking }
}
```

- `streamingToolExecutor` 활성 시: 스트리밍 중 시작된 도구의 **나머지 결과** 수집
- 비활성 시: `runTools()`로 전통적 순차 실행
- `hook_stopped_continuation` 첨부 발견 시 `shouldPreventContinuation = true`

### Phase 8: 후처리 (line 1411~1671)

#### 8-1. Tool Use Summary (line 1412~1482)

```ts
nextPendingToolUseSummary = generateToolUseSummary({
  tools: toolInfoForSummary, signal, isNonInteractiveSession, lastAssistantText,
})
```

- **Haiku 모델**로 도구 사용 요약 생성 (~1초)
- 다음 턴의 API 스트리밍 중에 resolve됨 (5~30초)
- 서브에이전트에서는 생성하지 않음 (모바일 UI에 표시 안 되므로)

#### 8-2. 명령 큐 드레인 (line 1566~1578)

```ts
const queuedCommandsSnapshot = getCommandsByMaxPriority(sleepRan ? 'later' : 'next')
  .filter(cmd => {
    if (isSlashCommand(cmd)) return false                    // 슬래시 명령 제외
    if (isMainThread) return cmd.agentId === undefined       // 메인 스레드: agentId 없는 것만
    return cmd.mode === 'task-notification' && cmd.agentId === currentAgentId  // 서브에이전트: 자기 것만
  })
```

- Sleep 도구가 실행됐으면 `'later'` 우선순위까지 포함
- 프로세스 전역 큐에서 에이전트 ID로 필터링

#### 8-3. Attachment Messages (line 1580~1628)

```ts
for await (const attachment of getAttachmentMessages(
  null, updatedToolUseContext, null, queuedCommandsSnapshot,
  [...messagesForQuery, ...assistantMessages, ...toolResults], querySource,
)) {
  yield attachment
  toolResults.push(attachment)
}
```

추가되는 첨부물:
- **메모리 프리페치** (line 1599~1614): `startRelevantMemoryPrefetch()`가 턴 시작 시 비동기 시작, 여기서 소비
- **스킬 발견** (line 1620~1628): `collectSkillDiscoveryPrefetch()`
- **파일 변경 알림**: `edited_text_file` 타입 첨부

#### 8-4. 도구 새로고침 (line 1660~1671)

```ts
if (updatedToolUseContext.options.refreshTools) {
  const refreshedTools = updatedToolUseContext.options.refreshTools()
  // 새로 연결된 MCP 서버의 도구가 다음 턴에 반영
}
```

### Phase 9: 루프 계속/종료 (line 1679~1728)

```ts
// maxTurns 체크
if (maxTurns && nextTurnCount > maxTurns) {
  yield createAttachmentMessage({ type: 'max_turns_reached', ... })
  return { reason: 'max_turns', turnCount: nextTurnCount }
}

// 다음 턴으로 계속
state = {
  messages: [...messagesForQuery, ...assistantMessages, ...toolResults],
  toolUseContext: toolUseContextWithQueryTracking,
  turnCount: nextTurnCount,
  transition: { reason: 'next_turn' },
  ...
}
// → while(true) 처음으로
```

---

## 4. 종료 사유 (Terminal Reasons)

| reason | 의미 | 위치 |
|---|---|---|
| `completed` | 정상 종료 (도구 호출 없이 끝남) | line 1357 |
| `blocking_limit` | 토큰 blocking limit 도달 | line 646 |
| `prompt_too_long` | 413 에러, 복구 실패 | line 1175, 1182 |
| `image_error` | 이미지 크기/리사이즈 에러 | line 977, 1175 |
| `model_error` | API/모델 에러 | line 996 |
| `aborted_streaming` | 스트리밍 중 사용자 중단 | line 1051 |
| `aborted_tools` | 도구 실행 중 사용자 중단 | line 1515 |
| `hook_stopped` | 훅이 계속 진행 차단 | line 1520 |
| `stop_hook_prevented` | 스톱 훅이 계속 차단 | line 1279 |
| `max_turns` | maxTurns 한도 초과 | line 1711 |

---

## 5. 핵심 설계 패턴

### 5.1 AsyncGenerator + yield*

`query()`와 `queryLoop()` 모두 `AsyncGenerator`입니다. `yield`로 메시지를 하나씩 내보내서:
- UI가 **실시간으로** 업데이트됨
- 호출자가 `.return()`으로 언제든 중단 가능
- 에러가 `yield*`를 통해 자연스럽게 전파

### 5.2 Immutable State 교체

```ts
const next: State = { ...현재상태, 변경된필드들 }
state = next
continue  // while(true) 처음으로
```

9개 필드를 개별 재할당하는 대신 객체를 통째로 교체. `transition` 필드로 왜 계속했는지 추적 가능.

### 5.3 Feature Flag + DCE (Dead Code Elimination)

```ts
const snipModule = feature('HISTORY_SNIP')
  ? require('./services/compact/snipCompact.js')
  : null
```

`bun:bundle`의 DCE와 연동되어 외부 빌드에서는 Ant-only 기능이 **완전히 제거**됩니다. `feature()`는 `if`/삼항 조건에서만 사용 가능 (tree-shaking 제약).

### 5.4 Dependency Injection

```ts
const deps = params.deps ?? productionDeps()
deps.callModel(...)
deps.microcompact(...)
deps.autocompact(...)
deps.uuid()
```

테스트에서 `deps`를 주입하여 API 호출 없이 deterministic 실행 가능.

### 5.5 Withheld Message 패턴

복구 가능한 에러를 즉시 UI에 보여주지 않고 보류:

```ts
let withheld = false
if (contextCollapse?.isWithheldPromptTooLong(message, ...)) withheld = true
if (reactiveCompact?.isWithheldPromptTooLong(message)) withheld = true
if (isWithheldMaxOutputTokens(message)) withheld = true
if (!withheld) yield yieldMessage  // 보류 안 되면 즉시 yield
```

복구 성공 → 에러 메시지 폐기 → 사용자는 에러를 전혀 모름\
복구 실패 → 뒤늦게 yield → 사용자에게 표시

### 5.6 Prefetch & Parallel Computation

| 프리페치 | 시작 시점 | 소비 시점 | 숨겨지는 지연 |
|---|---|---|---|
| Memory prefetch | 턴 시작 (line 301) | 도구 실행 후 (line 1599) | ~200ms |
| Skill discovery | 루프 반복 시작 (line 331) | 도구 실행 후 (line 1620) | ~250ms |
| Tool use summary | 도구 실행 후 (line 1469) | **다음 턴** API 스트리밍 후 (line 1056) | ~1s (Haiku) |

### 5.7 Task Budget 추적 (line 291)

```ts
// compact 발생 시:
const preCompactContext = finalContextTokensFromLastResponse(messagesForQuery)
taskBudgetRemaining = Math.max(0, (taskBudgetRemaining ?? total) - preCompactContext)
```

compact 전에는 서버가 전체 히스토리를 보므로 자체 카운트다운. compact 후에는 서버가 요약만 보므로 클라이언트가 `remaining`을 계산하여 전달.

---

## 6. 에러 복구 흐름도

```
API 응답 수신
  │
  ├─ 정상 응답 (tool_use 있음) → Phase 7: 도구 실행 → Phase 8: 후처리 → Phase 9: 다음 턴
  │
  ├─ 정상 응답 (tool_use 없음) → Phase 5: Stop Hooks → Phase 6: Token Budget → 종료
  │
  ├─ prompt_too_long (413)
  │   ├─ 1차: Context Collapse drain → 재시도
  │   ├─ 2차: Reactive Compact → 재시도
  │   └─ 실패: 에러 표시 → 종료
  │
  ├─ max_output_tokens
  │   ├─ 1차: Escalate 8k→64k → 재시도
  │   ├─ 2~4차: Recovery 메시지 주입 → 재시도
  │   └─ 소진: 에러 표시 → Stop Hooks → 종료
  │
  ├─ media_size_error
  │   ├─ Reactive Compact strip-retry → 재시도
  │   └─ 실패: 에러 표시 → 종료
  │
  ├─ FallbackTriggeredError
  │   └─ 폴백 모델로 전환 → 같은 요청 재시도
  │
  └─ 기타 에러
      └─ orphaned tool_result 생성 → 에러 표시 → 종료
```

---

## 7. Abort 처리

### 스트리밍 중 중단 (line 1015~1052)

```ts
if (toolUseContext.abortController.signal.aborted) {
  // StreamingToolExecutor: synthetic tool_result 생성 (queued/in-progress 도구용)
  // 또는 yieldMissingToolResultBlocks: 모든 tool_use에 에러 tool_result 생성
  //
  // submit-interrupt: interruption 메시지 스킵 (큐잉된 사용자 메시지가 충분한 컨텍스트 제공)
  // chicago MCP: computer use cleanup (auto-unhide + lock release)
  return { reason: 'aborted_streaming' }
}
```

### 도구 실행 중 중단 (line 1485~1516)

```ts
if (toolUseContext.abortController.signal.aborted) {
  // chicago MCP cleanup
  // submit-interrupt 체크
  // maxTurns 체크 (중단돼도 턴 카운트)
  return { reason: 'aborted_tools' }
}
```

**중요**: abort 시 orphaned `tool_use` 블록에 대한 `tool_result`를 반드시 생성해야 합니다. 그렇지 않으면 API가 다음 호출에서 에러를 반환합니다.

---

## 8. Thinking Rules (주석, line 151~163)

```
"The rules of thinking are lengthy and fortuitous..."

1. thinking/redacted_thinking 블록이 있는 메시지
   → max_thinking_length > 0인 쿼리 소속이어야 함
2. thinking 블록은 메시지의 마지막 블록이 될 수 없음
3. thinking 블록은 assistant trajectory 동안 보존되어야 함
   (단일 턴, 또는 tool_use가 있으면 후속 tool_result + 다음 assistant 메시지까지)
```

---

## 9. 전체 흐름 다이어그램

```
┌─────────────────────────────────────────────────────────┐
│                    query(params)                         │
│  └─ yield* queryLoop(params, consumedCommandUuids)      │
│     ┌───────── while (true) ─────────┐                  │
│     │                                │                  │
│     │  ┌─ Phase 1: Pre-processing ─┐ │                  │
│     │  │  toolResultBudget         │ │                  │
│     │  │  snipCompact              │ │                  │
│     │  │  microcompact             │ │                  │
│     │  │  contextCollapse          │ │                  │
│     │  │  autocompact              │ │                  │
│     │  └───────────────────────────┘ │                  │
│     │              │                 │                  │
│     │  ┌─ Phase 2: Blocking Limit ─┐ │                  │
│     │  │  토큰 한도 체크            │ │                  │
│     │  └───────────────────────────┘ │                  │
│     │              │                 │                  │
│     │  ┌─ Phase 3: API Streaming ──┐ │                  │
│     │  │  callModel() → for await  │ │                  │
│     │  │  ├─ assistant 메시지 수집  │ │                  │
│     │  │  ├─ streaming tool exec   │ │                  │
│     │  │  ├─ withheld 에러 보류    │ │                  │
│     │  │  └─ fallback 처리         │ │                  │
│     │  └───────────────────────────┘ │                  │
│     │              │                 │                  │
│     │      needsFollowUp?            │                  │
│     │       ╱         ╲              │                  │
│     │    false        true           │                  │
│     │      │            │            │                  │
│     │  ┌─ Phase 4 ─┐   │            │                  │
│     │  │ 에러 복구  │   │            │                  │
│     │  │ 413/MOT   │   │            │                  │
│     │  └───────────┘   │            │                  │
│     │      │            │            │                  │
│     │  ┌─ Phase 5 ─┐   │            │                  │
│     │  │ Stop Hooks │   │            │                  │
│     │  └───────────┘   │            │                  │
│     │      │            │            │                  │
│     │  ┌─ Phase 6 ─┐   │            │                  │
│     │  │ Token Budg │   │            │                  │
│     │  └───────────┘   │            │                  │
│     │      │          ┌─┴──────────┐ │                  │
│     │   return     │ Phase 7: 도구 │ │                  │
│     │   Terminal   │ 실행          │ │                  │
│     │              └──────────────┘ │                  │
│     │                    │           │                  │
│     │              ┌─────┴─────────┐ │                  │
│     │              │ Phase 8: 후처리│ │                  │
│     │              │ summary, attach│ │                  │
│     │              │ memory, skills │ │                  │
│     │              └───────────────┘ │                  │
│     │                    │           │                  │
│     │              ┌─────┴─────────┐ │                  │
│     │              │ Phase 9: 계속  │ │                  │
│     │              │ state = next   │ │                  │
│     │              │ continue       │ │                  │
│     │              └───────────────┘ │                  │
│     │                    │           │                  │
│     └────────────────────┘───────────┘                  │
└─────────────────────────────────────────────────────────┘
```

---

*이 문서는 `src/query.ts` 1,729줄을 줄 단위로 분석하여 작성되었습니다.*
