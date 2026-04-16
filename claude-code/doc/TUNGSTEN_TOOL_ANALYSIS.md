# Tungsten ai Tool 상세 분석

> Claude Code의 Anthropic 내부 전용 가상 터미널(tmux) 도구에 대한 심층 분석 문서

---

## 목차

1. [개요](#1-%EA%B0%9C%EC%9A%94)
2. [아키텍처](#2-%EC%95%84%ED%82%A4%ED%85%8D%EC%B2%98)
3. [AppState 상태 관리](#3-appstate-%EC%83%81%ED%83%9C-%EA%B4%80%EB%A6%AC)
4. [tmux 소켓 인프라](#4-tmux-%EC%86%8C%EC%BC%93-%EC%9D%B8%ED%94%84%EB%9D%BC)
5. [UI 컴포넌트](#5-ui-%EC%BB%B4%ED%8F%AC%EB%84%8C%ED%8A%B8)
6. [제약 사항 및 설계 결정](#6-%EC%A0%9C%EC%95%BD-%EC%82%AC%ED%95%AD-%EB%B0%8F-%EC%84%A4%EA%B3%84-%EA%B2%B0%EC%A0%95)
7. [관련 파일 맵](#7-%EA%B4%80%EB%A0%A8-%ED%8C%8C%EC%9D%BC-%EB%A7%B5)

---

## 1. 개요

TungstenTool은 Claude Code의 **Anthropic 내부 전용(**`ant-only`**) 가상 터미널 도구**다. tmux 기반의 인터랙티브 셸 세션을 관리하며, 일반 `BashTool`과 달리 **상태를 유지하는 터미널 세션**에서 명령을 실행한다.

| 항목 | 내용 |
| --- | --- |
| **도구 이름** | `TungstenTool` (UI에서는 "Tmux"로 표시) |
| **활성화 조건** | `process.env.USER_TYPE === 'ant'` (Anthropic 직원 전용) |
| **핵심 기술** | tmux 세션 멀티플렉싱 |
| **소스 위치** | `src/tools/TungstenTool/` (빌드에서 제외됨, 소스 미포함) |
| **카테고리** | ToolSelector에서 "Execution tools" 그룹 (BashTool과 동일) |

> **이름 유래**: Tungsten(텅스텐)은 원소 기호 W, 원자 번호 74의 금속 원소. 높은 융점과 경도로 유명. 내부 코드네임으로 사용.

---

## 2. 아키텍처

### BashTool vs TungstenTool

```
BashTool (일반 사용자)
┌─────────────────────────────────┐
│ 1회성 셸 실행                    │
│ ├── 명령 실행 → stdout/stderr   │
│ └── 프로세스 종료                │
│ (상태 비유지, 매번 새 셸)        │
└─────────────────────────────────┘

TungstenTool (Anthropic 내부)
┌─────────────────────────────────┐
│ tmux 세션 (상태 유지)            │
│ ├── 세션 생성 → 명령 실행        │
│ ├── 화면 캡처 (프레임) → 모델    │
│ ├── 키 입력 전송                 │
│ ├── 백그라운드 실행 지속          │
│ └── 패널로 실시간 모니터링        │
│ (싱글톤, 세션 간 유지)            │
└─────────────────────────────────┘
```

### 핵심 동작 방식

TungstenTool은 tmux의 **세션-윈도우-패인** 구조를 활용한다:

```
tmux 서버 (소켓 기반)
  │
  ├── 세션 (tungstenActiveSession.sessionName)
  │   └── 윈도우
  │       └── 패인 (tungstenActiveSession.target)
  │           ├── 명령 실행
  │           ├── 화면 캡처 → 모델에 전달
  │           └── 키 입력 수신
  │
  └── 다른 세션 (예: test, verify, hunter)
      └── 독립적인 작업 수행
```

### 실행 플로우

```
Claude (메인 모델) → TungstenTool.call() 호출
  │
  ├─ 1. 세션 초기화 (최초 1회)
  │   ├── markTmuxToolUsed()  → Shell.ts에 tmux 사용 알림
  │   ├── tmux 소켓 초기화
  │   └── 세션 생성 + AppState 등록
  │
  ├─ 2. 명령 실행
  │   ├── tmux send-keys → 터미널에 명령 전송
  │   └── tungstenLastCommand 갱신
  │
  ├─ 3. 화면 캡처
  │   ├── tmux capture-pane → 현재 화면 내용 캡처
  │   └── tungstenLastCapturedTime 갱신
  │
  └─ 4. 결과 반환
      └── 캡처된 프레임을 모델에 전달
```

---

## 3. AppState 상태 관리

TungstenTool은 `AppState`에 5개의 전용 상태 필드를 갖는다:

```typescript
// AppStateStore.ts

// 활성 tmux 세션 정보
tungstenActiveSession?: {
  sessionName: string    // tmux 세션 이름
  socketName: string     // tmux 소켓 이름
  target: string         // tmux 타겟 (예: "session:window.pane")
}

// 마지막 화면 캡처 시각
tungstenLastCapturedTime?: number

// 마지막 실행 명령
tungstenLastCommand?: {
  command: string        // 명령 문자열 (예: "echo hello", "Enter")
  timestamp: number      // 전송 시각
}

// 패널 표시 여부 (sticky, globalConfig에 영속화)
tungstenPanelVisible?: boolean

// 자동 숨김 상태 (턴 종료 시 임시, 영속화 안 됨)
tungstenPanelAutoHidden?: boolean
```

### 상태 전이 다이어그램

```
[세션 없음]
    │
    ▼  TungstenTool 최초 사용
[tungstenActiveSession 설정]
    │
    ├─ 명령 실행 → tungstenLastCommand 갱신
    ├─ 화면 캡처 → tungstenLastCapturedTime 갱신
    │
    ├─ 턴 종료 (정상)
    │   └─ tungstenPanelAutoHidden = true
    │      (세션은 유지, 패널만 숨김)
    │
    ├─ 사용자 토글 (Enter on tmux pill)
    │   ├─ autoHidden 상태 → autoHidden = false (패널 복원)
    │   └─ 일반 상태 → panelVisible 토글
    │
    ├─ 다음 TungstenTool 사용
    │   └─ tungstenPanelAutoHidden 해제 (패널 재표시)
    │
    └─ /clear 실행
        └─ clearSessionsWithTungstenUsage()
           resetInitializationState()
```

### 패널 가시성 관리 규칙

```
표시 조건:
  tungstenActiveSession !== undefined  (세션 존재)
  AND
  tungstenPanelVisible !== false       (사용자가 안 숨김)
  AND
  tungstenPanelAutoHidden !== true     (턴 종료 자동숨김 아님)

영속화:
  tungstenPanelVisible → globalConfig에 저장 (세션 간 유지)
  tungstenPanelAutoHidden → 메모리만 (재시작 시 리셋)
```

---

## 4. tmux 소켓 인프라

TungstenTool은 `src/utils/tmuxSocket.ts`의 tmux 소켓 관리 인프라를 사용한다.

### 소켓 초기화

```
TungstenTool 최초 사용
  │
  ├── markTmuxToolUsed()
  │   └── Shell.ts가 후속 Bash 명령에 tmux 격리 적용
  │
  └── tmux 소켓 초기화 (initializeTmuxSocket)
      ├── tmux new-session (base 세션 생성)
      ├── 환경변수 설정
      │   ├── CLAUDE_CODE_SKIP_PROMPT_HISTORY=1
      │   │   └── 테스트 세션이 사용자 히스토리 오염 방지
      │   └── WSL_INTEROP 고정 (WSL 환경)
      └── 소켓 경로 감지 (#{socket_path})
```

### 환경 격리

```
CLAUDE_CODE_SKIP_PROMPT_HISTORY=1
  │
  ├── history.ts: addToHistory() 건너뜀
  │   └── 테스트/검증 세션의 명령이 사용자 히스토리에 안 남음
  │
  └── sessionStorage.ts: shouldSkipPersistence() = true
      └── 트랜스크립트 저장 건너뜀 → --resume 목록 오염 방지
```

### tmux 명령 실행 (WSL 지원)

```typescript
// tmuxSocket.ts — WSL 환경에서 tmux 실행
// TungstenTool/utils.ts의 execTmuxCommand와 동일 구조
const result = await execFileNoThrow('wsl', ['-e', TMUX_COMMAND, ...args], {
  env: { ...process.env, WSL_UTF8: '1' },
})
```

> **WSL 주의사항**: tmux 명령을 bash로 전달하면 `#` 문자가 주석으로 해석되어 `#{socket_path}` 등의 tmux 포맷 문자열이 잘린다.

---

## 5. UI 컴포넌트

### TungstenLiveMonitor

`src/tools/TungstenTool/TungstenLiveMonitor.js`에서 import. REPL 화면에 실시간 tmux 패널을 렌더링한다.

```
REPL.tsx (L4584)
  └── TungstenLiveMonitor
      ├── tmux 패인의 현재 화면을 실시간 표시
      ├── ant-only 조건부 렌더링
      └── WebBrowserPanel과 동일 위치에 배치
```

### TungstenPill (Footer)

`PromptInputFooterLeftSide.tsx`에서 렌더링. 하단 상태바에 tmux 세션 존재를 알리는 알약형 배지.

```
Footer 좌측
  ├── [Tasks] 배지
  ├── [Tmux] 배지  ← TungstenPill (ant-only)
  ├── [Teams] 배지
  └── [PR Status] 배지
```

### 사용자 상호작용

```
사용자 액션: Enter 키 on Tmux pill
  │
  ├── autoHidden 상태인 경우
  │   └── autoHidden = false (패널 복원, visible 유지)
  │
  └── 일반 상태인 경우
      └── panelVisible 토글 (true ↔ false)
```

---

## 6. 제약 사항 및 설계 결정

### 서브에이전트 차단

```
constants/tools.ts:
  BLOCKED FOR ASYNC AGENTS:
  - TungstenTool: Uses singleton virtual terminal abstraction
    that conflicts between agents.
```

TungstenTool은 **싱글톤 가상 터미널**을 사용하기 때문에, 여러 에이전트가 동시에 같은 터미널 세션에 접근하면 충돌이 발생한다. 따라서 서브에이전트에서는 사용이 차단된다.

### outputSchema 미정의

```
Tool.ts:398:
  // Optional because TungstenTool doesn't define this.
  // TODO: Make it required.
  outputSchema?: z.ZodType<unknown>
```

TungstenTool은 `outputSchema`를 정의하지 않는 **유일한 도구**. 이 때문에 `outputSchema`가 `ToolDef`에서 optional로 남아 있다.

### 턴 종료 시 자동 숨김

```
REPL.tsx (L2936-2951):
  // Auto-hide tungsten panel content at turn end (ant-only), but keep
  // tungstenActiveSession set so the pill stays in the footer and the user
  // can reopen the panel.
```

턴 종료 시 패널 내용은 자동으로 숨겨지지만, 세션 자체는 유지된다. 이유:

- 백그라운드 tmux 작업(예: `/hunter`)이 몇 분간 실행될 수 있음
- 세션까지 지우면 pill이 사라져 사용자가 확인할 방법이 없음
- abort 시에는 숨기지 않음 (검사 목적으로 패널 유지)

### /clear 시 정리

```
commands/clear/caches.ts (L94-101):
  // Clear tungsten session usage tracking
  clearSessionsWithTungstenUsage()
  resetInitializationState()
```

`/clear` 명령 시 TungstenTool의 세션 사용 추적과 초기화 상태가 리셋된다.

---

## 7. 관련 파일 맵

### 핵심 파일 (소스 미포함)

```
src/tools/TungstenTool/
  ├── TungstenTool.ts           # 메인 도구 구현 (빌드에서 제외)
  ├── TungstenLiveMonitor.js    # 실시간 패널 UI 컴포넌트
  └── utils.ts                  # execTmuxCommand 등 유틸리티
```

### 참조 파일 (소스 포함)

```
src/
├── tools.ts                          # 도구 등록 (ant-only 조건부)
├── Tool.ts                           # outputSchema optional 이유
├── constants/tools.ts                # 서브에이전트 차단 목록
├── state/
│   ├── AppStateStore.ts              # 5개 tungsten 상태 필드
│   └── onChangeAppState.ts           # panelVisible 영속화
├── utils/
│   ├── tmuxSocket.ts                 # tmux 소켓 관리 인프라
│   ├── config.ts                     # tungstenPanelVisible 설정
│   ├── sessionStorage.ts             # 트랜스크립트 건너뛰기
│   └── transcriptSearch.ts           # args[] 검색 지원
├── screens/
│   └── REPL.tsx                      # LiveMonitor 렌더링, 자동숨김
├── components/
│   ├── PromptInput/
│   │   ├── PromptInput.tsx           # tmux pill 가시성, 토글
│   │   └── PromptInputFooterLeftSide.tsx  # TungstenPill 배지
│   └── agents/
│       └── ToolSelector.tsx          # "Execution tools" 그룹
├── history.ts                        # 히스토리 건너뛰기
└── commands/clear/caches.ts          # /clear 시 정리
```

---

## 부록: TungstenTool vs BashTool 비교

| 관심사 | BashTool | TungstenTool |
| --- | --- | --- |
| **대상** | 모든 사용자 | Anthropic 직원 (ant-only) |
| **실행 방식** | 1회성 셸 프로세스 | tmux 세션 (상태 유지) |
| **상태 유지** | 없음 (매번 새 셸) | 있음 (세션 간 지속) |
| **인터랙티브** | 제한적 | 완전 인터랙티브 (키 입력 전송) |
| **화면 캡처** | stdout/stderr 반환 | tmux capture-pane (프레임) |
| **백그라운드** | 제한적 | 지원 (세션 유지) |
| **서브에이전트** | 사용 가능 | 차단 (싱글톤 충돌) |
| **동시성** | 안전 | 싱글톤 (충돌 위험) |
| **UI** | 없음 (텍스트 결과만) | 실시간 패널 + Footer Pill |
| **히스토리** | 기록됨 | 건너뜀 (오염 방지) |
| **outputSchema** | 정의됨 | 미정의 (유일한 예외) |
