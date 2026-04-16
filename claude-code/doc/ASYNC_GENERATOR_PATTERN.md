# AsyncGenerator 패턴 분석

> Claude Code가 핵심 쿼리 루프에 AsyncGenerator를 채택한 이유와 설계 근거

---

## 목차

1. [개요](#1-개요)
2. [채택 이유 5가지](#2-채택-이유-5가지)
   - [실시간 스트리밍](#21-실시간-스트리밍)
   - [소비자 독립성](#22-소비자-독립성)
   - [무한 루프 + 자연스러운 종료](#23-무한-루프--자연스러운-종료)
   - [중단(abort) 지원](#24-중단abort-지원)
   - [yield* 위임으로 계층 분리](#25-yield-위임으로-계층-분리)
3. [대안 패턴과의 비교](#3-대안-패턴과의-비교)
4. [Claude Code에서의 실제 사용](#4-claude-code에서의-실제-사용)
5. [AsyncGenerator 기본 문법](#5-asyncgenerator-기본-문법)

---

## 1. 개요

Claude Code의 핵심 에이전트 루프(`query.ts`, `QueryEngine.ts`)는 전부 `AsyncGenerator`로 구현되어 있다. 일반적인 `async/await` 함수 대신 이 패턴을 채택한 이유는 **스트리밍 + 양방향 제어 + 즉시 중단**이라는 복합 요구사항 때문이다.

```typescript
// query.ts — 에이전트 루프
export async function* query(params: QueryParams):
  AsyncGenerator<StreamEvent | Message, Terminal> { ... }

// QueryEngine.ts — 세션 관리
async *submitMessage(prompt: string):
  AsyncGenerator<SDKMessage, void> { ... }
```

---

## 2. 채택 이유 5가지

### 2.1 실시간 스트리밍

모델 API 응답은 **토큰 단위로 스트리밍**된다. 완료까지 기다리면 수십 초간 화면이 멈춤.

```typescript
// 일반 async 함수 — 전부 끝나야 반환
async function query(): Promise<Result> {
  // 30초 동안 아무것도 안 보이다가...
  return finalResult  // 한 번에 쿵
}

// AsyncGenerator — 중간 결과를 즉시 전달
async function* query(): AsyncGenerator<StreamEvent, Terminal> {
  yield { type: 'stream_event', ... }   // 토큰 1개 도착 즉시
  yield { type: 'assistant', ... }      // 메시지 도착 즉시
  yield { type: 'user', ... }           // 도구 결과 즉시
  return { reason: 'completed' }        // 최종 결과
}
```

`yield`로 즉시 내보내면 REPL/SDK/Desktop이 **실시간 렌더링** 가능. 사용자는 모델이 "생각하는" 과정을 토큰 단위로 볼 수 있다.

### 2.2 소비자 독립성

하나의 generator를 **여러 소비자가 동일한 방식**으로 `for await`로 소비.

```
query() AsyncGenerator
  │
  ├─ yield ──→ REPL (터미널 UI 렌더링)
  ├─ yield ──→ SDK (JSON 스트림 출력, -p 모드)
  ├─ yield ──→ Desktop App (Electron/Tauri UI)
  └─ yield ──→ Bridge (claude.ai로 전달)
```

소비자별 코드 분기가 불필요하다. QueryEngine.ts의 `submitMessage()`가 yield하면, REPL이든 SDK든 Bridge든 같은 `for await` 루프로 소비한다:

```typescript
// SDK 소비자 (QueryEngine.ts)
for await (const message of query({ messages, systemPrompt, ... })) {
  switch (message.type) {
    case 'assistant': this.mutableMessages.push(message); yield* normalize(message); break;
    case 'stream_event': this.totalUsage = accumulate(currentUsage); break;
    case 'user': this.mutableMessages.push(message); break;
    // ...
  }
}

// REPL 소비자 (동일한 패턴)
for await (const message of engine.submitMessage(prompt)) {
  render(message)  // React UI 업데이트
}
```

### 2.3 무한 루프 + 자연스러운 종료

에이전트 루프는 **도구 호출이 있는 한 계속 반복**해야 하고, 다양한 이유로 종료될 수 있다. AsyncGenerator는 이를 자연스럽게 표현:

```typescript
async function* queryLoop(): AsyncGenerator<Event, Terminal> {
  while (true) {
    // 1. API 호출 + 스트리밍
    for await (const event of callModel(...)) {
      yield event  // 중간 이벤트 방출 (멈추지 않음)
    }

    // 2. 도구 호출 없으면 종료
    if (!needsFollowUp) {
      return { reason: 'completed' }  // return = 종료 + 이유 전달
    }

    // 3. 도구 실행
    for await (const result of runTools(...)) {
      yield result.message  // 도구 결과 즉시 방출
    }

    // 4. 다음 턴 (continue = 자동)
    state = { messages: [...messages, ...results], turnCount: turnCount + 1 }
  } // while(true) → 다음 반복
}
```

**세 가지 제어 흐름**:
- `yield`: 중간 이벤트 방출 (루프 계속)
- `return { reason }`: 루프 종료 + 종료 사유 전달 (`Terminal` 타입)
- `continue`: 다음 턴 (while 자체가 처리)

Promise 체인이나 콜백으로는 이 "무한 루프 + 10가지 종료 사유 + 7가지 계속 사유" 패턴이 매우 복잡해진다.

### 2.4 중단(abort) 지원

```typescript
const gen = query(params)

// 정상 소비
for await (const event of gen) {
  if (event.type === 'assistant') render(event)
}

// 사용자가 Ctrl+C →
abortController.abort()  // 신호 전파
gen.return()             // generator 즉시 종료, finally 블록 실행
```

**즉시 중단이 가능한 이유**: generator는 `yield` 지점에서 일시 정지 상태이므로, `.return()`을 호출하면 그 지점에서 즉시 종료된다. 콜백 체인에서는 이미 실행 중인 콜백을 취소할 수 없고, Promise 체인에서는 취소 전파가 훨씬 어렵다.

```typescript
// query.ts의 실제 중단 처리
if (toolUseContext.abortController.signal.aborted) {
  if (streamingToolExecutor) {
    // 실행 중인 도구의 합성 결과 수확
    for await (const update of streamingToolExecutor.getRemainingResults()) {
      if (update.message) yield update.message
    }
  }
  yield createUserInterruptionMessage({ toolUse: true })
  return { reason: 'aborted_tools' }  // 즉시 종료
}
```

### 2.5 `yield*` 위임으로 계층 분리

```typescript
// query() → queryLoop() 완전 위임
async function* query(params) {
  const consumedCommandUuids: string[] = []
  const terminal = yield* queryLoop(params, consumedCommandUuids)
  // yield*가 queryLoop의 모든 yield를 투명하게 전달
  // queryLoop이 return하면 여기서 받음

  // 사후 처리 (queryLoop 정상 종료 시만 실행)
  for (const uuid of consumedCommandUuids) {
    notifyCommandLifecycle(uuid, 'completed')
  }
  return terminal
}
```

**`yield*`의 의미**:
- 하위 generator의 모든 `yield`를 상위 소비자에게 **투명하게 전달**
- 하위의 `return` 값을 상위에서 **받을 수 있음**
- 하위에서 `throw`하면 상위로 **전파**
- 상위에서 `.return()`하면 하위도 **함께 종료**

이를 통해 `query()`는 라이프사이클 관리만, `queryLoop()`는 실제 루프 로직만 담당하는 깔끔한 계층 분리가 가능.

---

## 3. 대안 패턴과의 비교

| 패턴 | 스트리밍 | 종료 제어 | 중단 | 타입 안전 | 외부 의존 |
|---|---|---|---|---|---|
| **Promise** | X (완료까지 대기) | return만 | 어려움 | O | 없음 |
| **콜백** | O (매 이벤트) | 수동 상태 관리 | 어려움 | 약함 | 없음 |
| **EventEmitter** | O | 수동 | `removeAllListeners` | X (any 타입) | Node.js |
| **Observable (RxJS)** | O | O (complete/error) | O (unsubscribe) | O | RxJS 패키지 |
| **ReadableStream** | O | O (cancel) | O (cancel) | 약함 | Web API |
| **AsyncGenerator** | **O (yield)** | **O (return + 타입)** | **O (.return())** | **O** | **없음 (네이티브)** |

### 왜 RxJS/Observable이 아닌가

```
RxJS 장점: 강력한 연산자 (map, filter, merge, switchMap 등)
RxJS 단점:
  ├── 외부 의존성 (번들 크기 증가)
  ├── 러닝 커브 (팀 전체가 이해해야)
  ├── return 값 없음 (complete은 값을 전달하지 않음)
  └── yield* 위임 불가 (generator 계층 구조 불가능)
```

Claude Code는 연산자 조합보다 **무한 루프 + 조건부 종료 + 계층 위임**이 핵심이므로, Observable보다 AsyncGenerator가 더 자연스럽다.

### 왜 ReadableStream이 아닌가

```
ReadableStream 장점: 웹 표준, 백프레셔 내장
ReadableStream 단점:
  ├── return 값 없음 (종료 사유 전달 불가)
  ├── while(true) 루프를 reader.read()로 수동 구현
  ├── 계층 구조 (pipeTo/pipeThrough) 는 있지만 return 전달 불가
  └── TypeScript 제네릭 지원 약함 (yield 타입 + return 타입 분리 불가)
```

---

## 4. Claude Code에서의 실제 사용

### query.ts의 AsyncGenerator 시그니처

```typescript
export async function* query(params: QueryParams):
  AsyncGenerator<
    StreamEvent | RequestStartEvent | Message | TombstoneMessage | ToolUseSummaryMessage,
    // ↑ yield 타입: 중간에 방출되는 모든 이벤트/메시지

    Terminal
    // ↑ return 타입: 종료 시 사유 ({ reason: 'completed' | 'aborted' | ... })
  >
```

**두 가지 타입 채널**:
1. **yield 채널** (5가지 유니온): 스트리밍 이벤트, 메시지, 도구 요약 등
2. **return 채널** (`Terminal`): 종료 사유 (completed, aborted, prompt_too_long 등 10가지)

이 분리는 Promise(`Promise<Result>`)나 EventEmitter로는 불가능. AsyncGenerator만이 **yield 타입과 return 타입을 별도로 지정** 가능.

### QueryEngine.ts의 소비 패턴

```typescript
for await (const message of query({
  messages, systemPrompt, userContext, systemContext,
  canUseTool, toolUseContext, fallbackModel, querySource,
})) {
  // yield된 메시지를 타입별로 분기 처리
  switch (message.type) {
    case 'assistant':
      this.mutableMessages.push(message)
      yield* normalizeMessage(message)  // SDK 포맷으로 변환 + 재yield
      break
    case 'stream_event':
      if (message.event.type === 'message_stop')
        this.totalUsage = accumulateUsage(this.totalUsage, currentMessageUsage)
      break
    case 'user':
      this.mutableMessages.push(message)
      turnCount++
      break
    case 'system':
      // compact_boundary → GC 해제
      if (message.subtype === 'compact_boundary')
        this.mutableMessages.splice(0, boundaryIdx)
      break
  }
}
// for await 종료 = query()가 return함 = 턴 완료
```

### 7가지 continue + 10가지 return

AsyncGenerator의 `while(true)` + `continue` + `return` 조합으로 표현:

```typescript
// query.ts queryLoop() 내부
while (true) {
  // ... API 호출, 도구 실행 ...

  // 7가지 continue 사유
  if (reactiveCompacted) { state = next; continue }        // reactive_compact_retry
  if (collapseDrained) { state = next; continue }          // collapse_drain_retry
  if (maxOutputEscalated) { state = next; continue }       // max_output_tokens_escalate
  if (maxOutputRecovery) { state = next; continue }        // max_output_tokens_recovery
  if (stopHookBlocking) { state = next; continue }         // stop_hook_blocking
  if (tokenBudgetContinue) { state = next; continue }      // token_budget_continuation
  // 기본: next_turn continue

  // 10가지 return 사유
  if (blockingLimit) return { reason: 'blocking_limit' }
  if (imageError) return { reason: 'image_error' }
  if (promptTooLong) return { reason: 'prompt_too_long' }
  if (modelError) return { reason: 'model_error', error }
  if (abortedStreaming) return { reason: 'aborted_streaming' }
  if (abortedTools) return { reason: 'aborted_tools' }
  if (hookStopped) return { reason: 'hook_stopped' }
  if (stopHookPrevented) return { reason: 'stop_hook_prevented' }
  if (maxTurns) return { reason: 'max_turns', turnCount }
  return { reason: 'completed' }
}
```

이 패턴은 Promise 체인이나 콜백으로 구현하면 상태 변수와 분기 로직이 폭발적으로 증가한다.

---

## 5. AsyncGenerator 기본 문법

```typescript
// 정의
async function* myGenerator(): AsyncGenerator<YieldType, ReturnType> {
  yield value1        // 중간 값 방출 (일시 정지)
  yield value2
  return finalValue   // 종료 + 최종 값
}

// 소비 (for await)
for await (const value of myGenerator()) {
  console.log(value)  // value1, value2 (return 값은 안 나옴)
}

// 소비 (수동)
const gen = myGenerator()
const { value, done } = await gen.next()   // yield 값
const { value: final, done: true } = await gen.next()  // return 값

// 위임
async function* parent() {
  const returnValue = yield* child()  // child의 모든 yield를 투명 전달
  // child가 return한 값을 받음
}

// 중단
gen.return()   // 즉시 종료 (finally 블록 실행)
gen.throw(err) // 에러 주입 (catch 블록으로)
```

### 핵심 특성 요약

| 특성 | 설명 |
|---|---|
| `yield` | 값 방출 + 일시 정지 (소비자가 `.next()` 호출 시 재개) |
| `return` | 종료 + 최종 값 전달 (for await에서는 무시됨) |
| `yield*` | 하위 generator에 완전 위임 (투명 전달) |
| `.return()` | 외부에서 강제 종료 (finally 실행) |
| `.throw()` | 외부에서 에러 주입 |
| 두 타입 채널 | `AsyncGenerator<YieldType, ReturnType>` — yield와 return 타입 분리 |
| 네이티브 | 외부 라이브러리 불필요 (ES2018+) |
