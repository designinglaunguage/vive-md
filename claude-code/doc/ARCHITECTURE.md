# Claude Code CLI — 소스 코드 아키텍처 문서

> **대상 코드베이스**: `/Users/hunsangjo/Downloads/src`\
> \*\***프로젝트 식별**: Anthropic Claude Code CLI (남부 에이전트/남부 전용 기능 포함)\
> \*\***언어/런타임**: TypeScript / React / Bun\
> \*\***규모**: 약 1,900개 파일, 300개 디렉토리, 핵심 파일만 합쳐도 10,000줄 이상

---

## 1. 개요 (Overview)

이 코드베이스는 **Claude Code CLI**의 전체 프론트엔드/애플리케이션 로직을 담고 있습니다. 터미널 기반 TUI(Terminal User Interface)로 동작하며, 다음을 핵심으로 합니다:

- **Ink 기반 React 렌더러**: 터미널에서 React 컴포넌트를 렌더링하는 커스텀 Ink 엔진(`src/ink/`)을 내장하고 있습니다.
- **대화형 REPL**: 사용자 입력을 받아 AI 모델(Claude)과 지속적으로 대화하는 루프(`src/screens/REPL.js`, `src/query.ts`)
- **도구 사용(Tool Use)**: 모델이 파일 읽기/쓰기, Bash 실행, 웹 검색, MCP 도구 등 40여 개의 도구를 호출할 수 있는 프레임워크
- **슬래시 명령 시스템**: `/clear`, `/compact`, `/cost`, `/mcp`, `/plan` 등 수십 개의 내장 명령과 동적 Skill/Plugin 명령
- **멀티 에이전트/태스크**: 로컬 셸 태스크, 로컬 에이전트, 원격 에이전트, In-Process Teammate, Coordinator Mode 등 다양한 실행 단위
- **컨텍스트 관리**: Auto-compact, Reactive compact, Context collapse, Snip, Microcompact 등 대화 맥락이 길어질때의 압축/정리 메커니즘

---

## 2. 기술 스택 및 빌드 특성

| 영역 | 기술 |
| --- | --- |
| 언어 | TypeScript (strict) |
| UI 프레임워크 | React 18+ (Ink 기반 터미널 렌더링) |
| 번들러/런타임 | Bun (`bun:bundle` 기반 Dead Code Elimination) |
| AI SDK | `@anthropic-ai/sdk` (Messages API, Tool Use, Streaming) |
| 상태 관리 | React Context + 중앙 `AppState` (`src/state/`) |
| MCP | `@modelcontextprotocol/sdk` (stdio/sse) |
| 테스트 | (추정) Jest/Vitest + VCR (`src/services/vcr.ts`) |

### 2.1 Feature Flag 시스템

코드 전반에 `feature('FLAG_NAME')` 패턴이 사용됩니다. 이는 `bun:bundle`의 DCE(Dead Code Elimination)와 연동되어, 외부 빌드에서는 남부 전용 기능(Ant-only)이 완전히 제거됩니다.

```ts
const proactive = feature('PROACTIVE')
  ? require('./commands/proactive.js').default
  : null
```

---

## 3. 디렉토리 구조 및 역할

```
src/
├── entrypoints/          # CLI 진입점, SDK 진입점, 초기화 로직
├── main.tsx              # 앱 부트스트랩 (4683줄). Commander CLI 파싱, REPL 실행
├── replLauncher.tsx      # REPL 화면을 Ink 루트에 마운트
├── ink/                  # 커스텀 Ink 엔진 (React → 터미널 ANSI 출력)
├── components/           # React UI 컴포넌트 (87개 이상)
├── hooks/                # React 훅 (useCanUseTool, useMergedTools 등)
├── screens/              # REPL, Onboarding 등 최상위 화면
├── commands/             # 슬래시 명령 구현 (146개 이상의 서브디렉토리/파일)
├── commands.ts           # 명령 레지스트리, Skill/Plugin 명령 통합
├── tools/                # AI가 사용하는 도구 구현 (40+ 개)
├── tools.ts              # 도구 레지스트리, 프리셋, MCP 도구 조립
├── Tool.ts               # 도구 타입 정의, `buildTool()` 헬퍼
├── tasks/                # 백그라운드/전경 태스크 구현
├── Task.ts               # 태스크 타입, ID 생성
├── query.ts              # 핵심 쿼리 루프 (1729줄). 모델 API 호출 → 스트리밍 → 도구 실행
├── QueryEngine.ts        # QueryEngine 클래스. 세션/에이전트/모델 상태 관리
├── context.ts            # 시스템/유저 컨텍스트 생성 (git status, CLAUDE.md)
├── state/                # 전역 상태 (AppState, Store, selectors)
├── services/             # 외부 API, 압축, MCP, 분석, 정책 등 비즈니스 로직
├── utils/                # 범용 유틸리티 (331개 이상의 파일/디렉토리)
├── bridge/               # 원격 제어(Remote Control) 및 브릿지 통신
├── [table]/               # 원격 세션 관련
├── types/                # 공유 타입 정의
├── constants/            # 상수, XML 태그, OAuth 설정 등
├── skills/               # Skill 로딩, 번들링, 검색
├── plugins/              # Plugin 시스템
├── migrations/           # 설정 마이그레이션
├── vim/                  # Vim 모션/오퍼레이터
├── memdir/               # 메모리/세션 저장소
├── coordinator/          # Coordinator Mode (멀티 에이전트 스웜)
├── assistant/            # Kairos/Assistant 모드 (Ant-only)
├── buddy/                # Buddy 기능 (Ant-only)
├── voice/                # 음성 입력/출력
└── cli/                  # 추가 CLI 유틸리티
```

---

## 4. 핵심 아키텍처 흐름

### 4.1 부트스트랩 → REPL 진입

1. `main.tsx`

   - `commander-js`로 CLI 인수 파싱 (`--remote`, `--bare`, `--tools`, `--model` 등)
   - GrowthBook 초기화, telemetry, auth, 설정 로딩
   - `launchRepl()` 호출 → `App` + `REPL` 컴포넌트를 Ink 루트에 렌더링

2. `screens/REPL.js` (추정)

   - 사용자 입력을 받는 메인 루프
   - 입력이 슬래시 명령이면 `commands.ts` → 해당 명령 실행
   - 일반 메시지면 `QueryEngine` 또는 `query.ts`로 전달

### 4.2 Query Loop (핵심)

\*\*`query.ts`\*\*의 `queryLoop` 제너레이터가 모든 대화의 심장입니다.

```
[사용자 입력]
    ↓
[Context 준비]
    ├── getSystemContext()  → git status, cache breaker
    ├── getUserContext()    → CLAUDE.md, current date
    └── Attachment 메시지 조립
    ↓
[Pre-processing]
    ├── applyToolResultBudget()  → 도구 결과 크기 제한
    ├── snipCompactIfNeeded()    → 오래된 메시지 snip
    ├── microcompact()           → 짧은 메시지 압축
    ├── applyCollapsesIfNeeded() → Context collapse
    └── autocompact()            → 토큰 한도 도달 시 요약
    ↓
[Model API Streaming]
    ├── callModel() → Anthropic Messages API 스트리밍
    ├── Assistant 메시지 수신 (thinking, text, tool_use)
    └── StreamingToolExecutor → 도구가 스트림 중에도 병렬 실행
    ↓
[Tool Execution]
    ├── runTools() / StreamingToolExecutor
    ├── canUseTool (권한 체크)
    ├── 도구별 call() 실행
    └── ToolResult → UserMessage/AttachmentMessage 변환
    ↓
[Loop Continue]
    → 도구 결과를 messages에 추가 후 다시 Model API 호출
    → stop_reason이 tool_use가 아니면 종료
```

### 4.3 도구 시스템 (Tool System)

\*\*`Tool.ts`\*\*에 정의된 인터페이스:

```ts
interface Tool<Input, Output, Progress> {
  name: string
  aliases?: string[]
  call(args, context, canUseTool, parentMessage, onProgress): Promise<ToolResult<Output>>
  description(input, options): Promise<string>
  inputSchema: z.ZodType
  prompt(options): Promise<string>
  // UI 렌더링
  renderToolUseMessage(input, options): React.ReactNode
  renderToolResultMessage(content, progress, options): React.ReactNode
  renderToolUseProgressMessage(...): React.ReactNode
  // 동작 특성
  isConcurrencySafe(input): boolean
  isReadOnly(input): boolean
  isDestructive?(input): boolean
  interruptBehavior?(): 'cancel' | 'block'
  checkPermissions(input, context): Promise<PermissionResult>
  // 기타
  toAutoClassifierInput(input): unknown
  mapToolResultToToolResultBlockParam(content, toolUseID): ToolResultBlockParam
}
```

\*\*`buildTool()`\*\*을 통해 기본값을 자동으로 채워 안전한(fail-closed) 도구 정의를 지원합니다.

#### 주요 도구 목록

| 도구 | 역할 |
| --- | --- |
| `BashTool` | 셸 명령 실행 |
| `FileReadTool` | 파일 읽기 |
| `FileEditTool` | 파일 수정 (diff 기반) |
| `FileWriteTool` | 파일 쓰기 |
| `GlobTool` / `GrepTool` | 파일 검색 |
| `WebSearchTool` | 웹 검색 |
| `WebFetchTool` | URL 콘텐츠 가져오기 |
| `AgentTool` | 서브에이전트 생성/재개 |
| `TaskCreateTool` / `TaskGetTool` / `TaskUpdateTool` / `TaskListTool` | Todo/태스크 관리 |
| `TodoWriteTool` | Todo 패널 업데이트 |
| `AskUserQuestionTool` | 사용자에게 선택지 질문 |
| `EnterPlanModeTool` / `ExitPlanModeV2Tool` | 계획 모드 전환 |
| `SkillTool` | Skill(슬래시 명령) 실행 |
| `MCPTool` | MCP 서버 도구 호출 |
| `ListMcpResourcesTool` / `ReadMcpResourceTool` | MCP 리소스 접근 |
| `NotebookEditTool` | ㅇ 노트북 편집 |
| `SendMessageTool` | 팀원/에이전트 간 메시지 |
| `TeamCreateTool` / `TeamDeleteTool` | 에이전트 스웜 팀 관리 |
| `ScheduleCronTool` | 주기적 작업 예약 |
| `REPLTool` | REPL 모드 래퍼 |
| `BriefTool` | 요약 생성 |
| `TungstenTool` | Ant-only 고급 도구 |

---

## 5. 주요 서브시스템 상세

### 5.1 Ink 기반 TUI (`src/ink/`)

Claude Code는 터미널에서 React 컴포넌트를 렌더링하기 위해 **커스텀 Ink**를 사용합니다.

- `ink/root.js`: React 루트 생성, 렌더링 루프
- `ink/renderer.ts`: React reconciler → 터미널 출력 노드 트리
- `ink/render-to-screen.ts`: 최종 ANSI 출력 생성
- `ink/termio/`: ANSI escape sequence 파서/생성기 (CSI, OSC, SGR, DEC)
- `ink/components/`: `Box`, `Text`, `App`, `ScrollBox`, `Button`, `Spacer` 등
- `ink/hooks/`: `useInput`, `useApp`, `useTerminalFocus`, `useSelection` 등
- `ink/events/`: 키보드, 마우스(클릭), 포커스, 터미널 크기 변경 이벤트 처리

특이사항:

- `ink/layout/yoga.js`: Yoga 레이아웃 엔진을 사용한 Flexbox 레이아웃
- `ink/bidi.ts`: 양방향 텍스트(아랍어/히브리어) 지원
- `ink/searchHighlight.ts`: 터미널 내 검색 하이라이트

### 5.2 상태 관리 (`src/state/`)

- `AppState.tsx` **/** `AppStateStore.ts`: 전역 상태 타입 및 초기 상태
- `store.ts`: 상태 업데이트 로직
- `selectors.ts`: 파생 상태 선택자
- `onChangeAppState.ts`: 상태 변경 구독/부수효과

주요 상태:

- `messages`: 대화 메시지 배열
- `tasks`: 실행 중인 태스크 목록
- `toolPermissionContext`: 권한 규칙 (allow/deny/ask)
- `mcp`: MCP 클라이언트/도구/명령/리소스
- `fastMode`, `advisorModel`, `effortValue`: 모델 설정
- `theme`, `agentColor`: UI 설정

### 5.3 명령 시스템 (`src/commands/`)

\*\*`commands.ts`\*\*가 중앙 허브입니다.

- **Built-in Commands**: `COMMANDS()` 함수가 메모이제이션된 내장 명령 배열 반환
- **Skills**: `getSkillDirCommands()`, `getBundledSkills()`, `getPluginSkills()`
- **Dynamic Skills**: 파일 작업 중 동적으로 발견된 Skill
- **MCP Commands**: MCP 서버에서 제공하는 prompt-type 명령
- **Workflows**: `feature('WORKFLOW_SCRIPTS')` 조걶

명령 타입:

- `prompt`: 모델에게 텍스트 프롬프트로 전달 (예: `/review`)
- `local`: 로컬에서 즉시 실행, 텍스트 결과 반환 (예: `/cost`)
- `local-jsx`: Ink UI를 렌더링하는 대화형 명령 (예: `/config`)

### 5.4 태스크 시스템 (`src/tasks/`)

\*\*`Task.ts`\*\*에서 정의하는 태스크는 백그라운드/전경 작업 단위입니다.

| 태스크 타입 | 설명 |
| --- | --- |
| `local_bash` | 로컬 셸 명령 (`LocalShellTask`) |
| `local_agent` | 로컬 서브에이전트 (`LocalAgentTask`) |
| `remote_agent` | 원격 에이전트 (`RemoteAgentTask`) |
| `in_process_teammate` | 동일 프로세스 내 팀원 (`InProcessTeammateTask`) |
| `local_workflow` | 워크플로우 실행 |
| `monitor_mcp` | MCP 모니터링 |
| `dream` | 자율 백그라운드 에이전트 (`DreamTask`) |

태스크는 `AppState.tasks`에 등록되고, `taskId`로 관리됩니다. `kill()` 메서드로 중단 가능합니다.

### 5.5 컨텍스트 압축 시스템 (`src/services/compact/`)

긴 대화 맥락을 관리하기 위해 여러 계층의 압축 메커니즘이 존재합니다:

1. `snipCompact.ts` (`HISTORY_SNIP`)

   - 오래된 메시지를 완전히 제거하여 토큰을 확보
   - 보호된 tail(최근 N턴)은 유지

2. `microCompact.ts`

   - 짧은 연속 메시지를 하나로 압축
   - 캐시 효율성 향상

3. `autoCompact.ts`

   - 토큰 한도에 도달하면 별도의 "압축 에이전트"를 호출하여 대화를 요약
   - `buildPostCompactMessages()`로 요약 메시지 + 첨부물 재구성

4. `reactiveCompact.ts` (`REACTIVE_COMPACT`)

   - API가 `prompt_too_long` 또는 `max_output_tokens` 오류를 반환했을 때
   - 실시간으로 recover: collapse drain, truncation retry, snip fallback

5. `contextCollapse/index.ts` (`CONTEXT_COLLAPSE`)

   - 메시지를 "collapse" 단위로 묶어서 읽기 전용 뷰로 투영
   - 실제 메시지 배열에서는 제거하지 않고, API 호출 시에만 필터링

### 5.6 MCP (Model Context Protocol) (`src/services/mcp/`)

- `client.ts`: MCP 클라이언트 연결 관리, 도구/리소스/명령 동기화
- `MCPConnectionManager.tsx`: React 훅 기반 연결 상태 관리
- `elicitationHandler.ts`: MCP 서버의 OAuth/URL elicitation 처리
- `officialRegistry.ts`: 공식 MCP 서버 레지스트리 프리페치
- `types.ts`: `MCPServerConnection`, `McpSdkServerConfig` 등

MCP 도구는 `tools.ts`의 `assembleToolPool()`에서 내장 도구와 병합됩니다. 이름 충돌 시 내장 도구가 우선합니다.

### 5.7 권한 시스템 (`src/utils/permissions/`)

- `permissions.ts`: 도구 실행 전 `canUseTool` / `checkPermissions` 판정
- **Permission Modes**: `default` | `bypass` | `plan`
- **Rules**: `alwaysAllowRules`, `alwaysDenyRules`, `alwaysAskRules`
- **Auto Mode**: 분류기(classifier)가 안전한 도구를 자동 승인
- **Denial Tracking**: 연속 거부 시 자동으로 프롬프팅으로 폴백

### 5.8 브릿지 & 원격 제어 (`src/bridge/`)

- `replBridge.ts` **/** `initReplBridge.ts`: 로컬 REPL과 원격 세션 간 메시지 브릿지
- `remoteBridgeCore.ts`: 원격 제어 핵심 로직
- `sessionRunner.ts`: 원격 세션 실행기
- `bridgeApi.ts`: 브릿지 REST/WebSocket API 클라이언트
- `trustedDevice.ts`: 신뢰 기기 관리

`REMOTE_SAFE_COMMANDS`와 `BRIDGE_SAFE_COMMANDS`를 통해 원격/모바일 환경에서 안전한 명령만 노출됩니다.

---

## 6. 데이터 흐름 다이어그램 (텍스트)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         TERMINAL (User)                             │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Ink Renderer (src/ink/)                                            │
│  ├── Event Dispatcher (keyboard, resize, focus)                     │
│  ├── React Reconciler                                               │
│  └── ANSI Output Generator                                          │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  REPL Screen (src/screens/REPL.js)                                  │
│  ├── Prompt Input Handling                                          │
│  ├── Slash Command Routing → commands.ts                            │
│  └── User Message → QueryEngine / query.ts                          │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  QueryEngine (src/QueryEngine.ts)                                   │
│  ├── Session State Management                                       │
│  ├── Model Selection & Configuration                                │
│  └── Delegates to query.ts generator                                │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  query.ts :: queryLoop()                                            │
│  ├── Context Assembly (git, claude.md, attachments)                 │
│  ├── Compaction (snip → microcompact → collapse → autocompact)      │
│  ├── API Streaming (callModel)                                      │
│  │   └── Anthropic Messages API                                     │
│  ├── Assistant Message Parsing (text, thinking, tool_use)           │
│  └── Tool Execution (runTools / StreamingToolExecutor)              │
│      ├── Permission Check (canUseTool)                              │
│      ├── Tool.call() (Bash, Read, Edit, Agent, MCP...)              │
│      └── ToolResult → UserMessage                                   │
│  ←── Loop back to API call if tool results exist                    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  AppState Update (src/state/store.ts)                               │
│  ├── messages append                                                │
│  ├── tasks spawn/kill                                               │
│  ├── tool permissions update                                        │
│  └── mcp clients/tools sync                                         │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  React Re-render → Ink → Terminal                                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 7. 고급 기능 및 설계 패턴

### 7.1 Streaming Tool Execution

`query.ts` 난내 `StreamingToolExecutor`는 모델의 스트리밍 응답 중에 `tool_use` 블록이 완성되는 즉시 도구를 실행합니다. 이를 통해:

- 도구 실행이 병렬화됩니다.
- UI에서 도구 진행 상황을 실시간으로 볼 수 있습니다.
- API 응답 지연과 도구 실행 지연이 중첩되지 않습니다.

### 7.2 Tool Result Budget & Content Replacement

- `applyToolResultBudget()`: 도구 결과의 총 크기가 한도를 초과하면 오래된 결과를 "persisted to disk"로 대체합니다.
- `ContentReplacementState`: 세션/사이드체인 파일에 기록되어 재개 시에도 유지됩니다.

### 7.3 Task Budget (API-level)

`params.taskBudget`을 통해 Anthropic API의 `task_budget` 파라미터를 지원합니다. `remaining` 값은 compaction 경계를 넘어서도 누적 차감되어 정확한 예산 추적이 가능합니다.

### 7.4 Coordinator Mode (`feature('COORDINATOR_MODE')`)

- 메인 에이전트가 "Coordinator"가 되어 하위 Worker 에이전트들에게 작업을 분배
- `AgentTool` + `TaskCreateTool` + `SendMessageTool` 조합으로 구현
- `filterToolsForAgent`를 통해 Worker에게는 제한된 도구만 노출

### 7.5 Agent Swarms & Teammates

- `InProcessTeammateTask`: 동일 프로세스 내에서 실행되는 팀원
- `RemoteAgentTask`: 원격 머신에서 실행되는 팀원
- `LocalAgentTask`: 로컬 서브프로세스/스레드에서 실행되는 에이전트
- `computeInitialTeamContext()`로 팀 재연결 시 컨텍스트 복원

### 7.6 CLAUDE.md & Memory System

- \*\*`context.ts`\*\*의 `getUserContext()`가 `getClaudeMds()`를 호출
- `src/utils/claudemd.js`: CWD 및 `--add-dir`로 지정된 디렉토리를 순회하며 `CLAUDE.md`, `AGENTS.md` 수집
- `src/memdir/`: 세션별 메모리 파일 관리

### 7.7 VCR & 테스트

- `src/services/vcr.ts`: API 호출을 녹화/재생하여 테스트 시 실제 네트워크 없이도 deterministic하게 실행

---

## 8. 핵심 파일 요약표

| 파일 | 라인수 | 역할 |
| --- | --- | --- |
| `main.tsx` | \~4,683 | CLI 부트스트랩, 전체 앱 생명주기 관리 |
| `query.ts` | \~1,729 | 모델 API 쿼리 루프, 스트리밍, 도구 실행 오케스트레이션 |
| `QueryEngine.ts` | \~1,295 | 세션/에이전트 상태 관리, Query 래퍼 |
| `commands.ts` | \~754 | 슬래시 명령 레지스트리, Skill/Plugin 통합 |
| `Tool.ts` | \~792 | 도구 인터페이스 정의, `buildTool()` 팩토리 |
| `tools.ts` | \~389 | 도구 풀 조립, 프리셋, MCP 병합 |
| `context.ts` | \~189 | 시스템/유저 컨텍스트 (git, CLAUDE.md) |
| `Task.ts` | \~125 | 태스크 타입, ID 생성, 기본 상태 |
| `interactiveHelpers.tsx` | \~2,000+ | 대화형 UI 헬퍼, 다이얼로그 런처 |

---

## 9. 보안 및 안전성 설계

1. **Fail-Closed Defaults**: `buildTool()`에서 `isConcurrencySafe: false`, `isReadOnly: false`를 기본값으로 설정
2. **Permission Layers**: 도구 → `validateInput` → `checkPermissions` → `canUseTool` → 실행
3. **Auto-Classifier**: Yolo/Auto 모드에서 도구 입력을 분류하여 위험도 평가
4. **Sandbox Awareness**: `sandboxTypes.ts`, `sandboxToggle` 명령으로 샌드박스 위반 모니터링
5. **Deny Rules**: MCP 서버 단위(`mcp__server`) 또는 도구 이름 단위로 블랙리스트 지원
6. **Bridge Safety**: 원격 명령은 `BRIDGE_SAFE_COMMANDS`와 `REMOTE_SAFE_COMMANDS`로 화이트리스트 관리

---

## 10. 확장 포인트

- **새로운 도구 추가**: `src/tools/{ToolName}/` 디렉토리 생성 → `Tool.ts` 인터페이스 구현 → `src/tools.ts`에 등록
- **새로운 슬래시 명령 추가**: `src/commands/{command}/index.ts` 생성 → `src/commands.ts`의 `COMMANDS()`에 추가
- **새로운 Skill 추가**: `~/.claude/skills/` 또는 프로젝트 내 `.claude/skills/`에 markdown 파일 배치
- **새로운 Plugin 추가**: `src/plugins/` 또는 외부 plugin manifest 등록
- **새로운 MCP 서버**: `~/.claude/mcp.json` 또는 프로젝트 `.mcp.json`에 서버 설정 추가

---

*문서 작성일: 2026-03-31*\
*분석 대상:* `/Users/hunsangjo/Downloads/src`