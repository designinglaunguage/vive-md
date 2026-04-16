# State Machine Patterns 분석

> Claude Code 소스에서 발견된 12개 상태 머신 패턴에 대한 종합 분석 문서

---

## 목차

1. [개요](#1-%EA%B0%9C%EC%9A%94)
2. [쿼리/제어 흐름](#2-%EC%BF%BC%EB%A6%AC%EC%A0%9C%EC%96%B4-%ED%9D%90%EB%A6%84)
   - [QueryGuard](#21-queryguard)
   - [LSP Server Instance](#22-lsp-server-instance)
   - [Session (Daemon)](#23-session-daemon)
3. [네트워크/연결](#3-%EB%84%A4%ED%8A%B8%EC%9B%8C%ED%81%AC%EC%97%B0%EA%B2%B0)
   - [Bridge Status](#31-bridge-status)
   - [Bridge Connection](#32-bridge-connection)
   - [Remote Connection](#33-remote-connection)
   - [FlushGate](#34-flushgate)
4. [사용자 입력](#4-%EC%82%AC%EC%9A%A9%EC%9E%90-%EC%9E%85%EB%A0%A5)
   - [Vim Input](#41-vim-input)
   - [Keyboard Parse](#42-keyboard-parse)
5. [권한 시스템](#5-%EA%B6%8C%ED%95%9C-%EC%8B%9C%EC%8A%A4%ED%85%9C)
   - [Permission Mode](#51-permission-mode)
6. [UI 상태](#6-ui-%EC%83%81%ED%83%9C)
   - [Terminal Focus](#61-terminal-focus)
   - [Speculation](#62-speculation)
7. [공통 패턴 분석](#7-%EA%B3%B5%ED%86%B5-%ED%8C%A8%ED%84%B4-%EB%B6%84%EC%84%9D)

---

## 1. 개요

Claude Code 소스에서 **12개의 독립적인 상태 머신**이 발견되었다. 이들은 쿼리 제어, 네트워크 연결, 사용자 입력, 권한, UI 등 다양한 영역에서 사용된다.

| 카테고리 | 상태 머신 | 위치 |
| --- | --- | --- |
| 쿼리/제어 | QueryGuard | `utils/QueryGuard.ts` |
| 쿼리/제어 | LSP Server Instance | `services/lsp/LSPServerInstance.ts` |
| 쿼리/제어 | Session (Daemon) | `server/types.ts` |
| 네트워크 | Bridge Status | `bridge/bridgeStatusUtil.ts` |
| 네트워크 | Bridge Connection | `bridge/replBridge.ts` |
| 네트워크 | Remote Connection | `state/AppStateStore.ts` |
| 네트워크 | FlushGate | `bridge/flushGate.ts` |
| 입력 | Vim Input | `vim/types.ts` |
| 입력 | Keyboard Parse | `ink/parse-keypress.ts` |
| 권한 | Permission Mode | `utils/permissions/` |
| UI | Terminal Focus | `ink/terminal-focus-state.ts` |
| UI | Speculation | `state/AppStateStore.ts` |

---

## 2. 쿼리/제어 흐름

### 2.1 QueryGuard

**위치**: `src/utils/QueryGuard.ts`**목적**: 쿼리 라이프사이클 동기 가드. React의 `useSyncExternalStore`와 호환.

```
           reserve()              tryStart()
  ┌─────┐ ────────► ┌─────────────┐ ────────► ┌─────────┐
  │ idle │           │ dispatching │           │ running │
  └──┬───┘ ◄──────── └─────────────┘           └────┬────┘
     │  cancelReservation()                          │
     │                                               │
     └───────────────── end() / forceEnd() ◄─────────┘
```

| 상태 | 설명 |
| --- | --- |
| `idle` | 쿼리 미활성, 큐 아이템 처리 가능 |
| `dispatching` | 아이템 디큐됨, onQuery 호출 전 비동기 체인 진행 중 |
| `running` | 쿼리 실행 중 |

**핵심 설계**: 비동기 갭(async gap) 동안 재진입(re-entry) 방지. `isActive`는 dispatching과 running 모두에 대해 true 반환.

---

### 2.2 LSP Server Instance

**위치**: `src/services/lsp/LSPServerInstance.ts`**목적**: 단일 LSP 서버 프로세스 라이프사이클 + 헬스 모니터링.

```
              start()                    초기화 성공
  ┌─────────┐ ────────► ┌──────────┐ ────────────► ┌─────────┐
  │ stopped │           │ starting │               │ running │
  └────┬────┘           └────┬─────┘               └────┬────┘
       │                     │                          │
       │  restart()          │ 실패                     │ stop()
       │  (max 3회)          │                          │
       │                     ▼                          ▼
       │               ┌─────────┐              ┌──────────┐
       └────────────── │  error  │              │ stopping │
                       └─────────┘              └────┬─────┘
                                                     │ 완료
                                                     ▼
                                                ┌─────────┐
                                                │ stopped │
                                                └─────────┘
```

| 상태 | 설명 |
| --- | --- |
| `stopped` | 서버 미실행 |
| `starting` | 초기화 진행 중 |
| `running` | 정상 작동, 요청 처리 가능 |
| `stopping` | 종료 진행 중 |
| `error` | 크래시 또는 초기화 실패 |

**크래시 복구**: 최대 3회 자동 재시작. 무한 자식 프로세스 스폰 방지.

---

### 2.3 Session (Daemon)

**위치**: `src/server/types.ts`**목적**: 데몬 모드 세션 라이프사이클.

```
  ┌──────────┐     ┌─────────┐     ┌──────────┐
  │ starting │ ──► │ running │ ──► │ stopping │ ──► ┌─────────┐
  └──────────┘     └────┬────┘     └──────────┘     │ stopped │
                        │                           └─────────┘
                        ▼
                   ┌──────────┐
                   │ detached │ (백그라운드/일시중단)
                   └──────────┘
```

---

## 3. 네트워크/연결

### 3.1 Bridge Status

**위치**: `src/bridge/bridgeStatusUtil.ts` + `bridgeUI.ts`**목적**: 브릿지 상태 표시 (터미널 UI).

```
  ┌──────┐     ┌──────────┐     ┌────────┐
  │ idle │ ──► │ attached │ ──► │ titled │
  └──┬───┘     └──────────┘     └────────┘
     │
     │ 연결 실패          재연결 시도
     ▼                    ▼
  ┌────────┐     ┌──────────────┐
  │ failed │     │ reconnecting │
  └────────┘     └──────────────┘
```

| 상태 | 설명 | UI 표시 |
| --- | --- | --- |
| `idle` | 미연결, QR 코드 표시 | 연결 URL + QR |
| `attached` | 사용자 연결됨 | "attached" |
| `titled` | 세션 제목 설정됨 | 제목 표시 |
| `reconnecting` | 일시적 끊김, 백오프 중 | 재연결 중... |
| `failed` | 영구 실패 | 에러 메시지 |

---

### 3.2 Bridge Connection

**위치**: `src/bridge/replBridge.ts`**목적**: claude.ai 상시 연결 브릿지.

```
AppState 플래그 조합으로 상태 표현:

  replBridgeEnabled       → 기능 활성 여부
  replBridgeConnected     → 등록 완료 여부
  replBridgeSessionActive → WebSocket 열림 여부
  replBridgeReconnecting  → 백오프 진행 중
```

| 상태 | enabled | connected | sessionActive | reconnecting |
| --- | --- | --- | --- | --- |
| 비활성 | false | — | — | — |
| 등록 중 | true | false | false | false |
| 준비 | true | true | false | false |
| 연결됨 | true | true | true | false |
| 재연결 중 | true | true | false | true |

---

### 3.3 Remote Connection

**위치**: `src/state/AppStateStore.ts`**목적**: 원격 세션 뷰어 WebSocket 연결 상태.

```
  ┌────────────┐     ┌───────────┐
  │ connecting │ ──► │ connected │
  └────────────┘     └─────┬─────┘
                           │
                    일시적 끊김 │ 영구 종료
                           ▼
                    ┌──────────────┐     ┌──────────────┐
                    │ reconnecting │     │ disconnected │
                    └──────────────┘     └──────────────┘
```

---

### 3.4 FlushGate

**위치**: `src/bridge/flushGate.ts`**목적**: 초기 히스토리 플러시 중 메시지 큐잉으로 인터리빙 방지.

```
  ┌──────────┐  start()   ┌────────┐  end()     ┌──────────┐
  │ inactive │ ─────────► │ active │ ─────────► │ inactive │
  └──────────┘            └────┬───┘  (큐 반환)  └──────────┘
                               │
                    enqueue()  │  drop() / deactivate()
                    (큐에 추가) │  (큐 폐기 / 비활성)
                               ▼
                          [큐잉된 메시지]
```

**제네릭**: `FlushGate<T>` — 타입 안전한 큐잉.

---

## 4. 사용자 입력

### 4.1 Vim Input

**위치**: `src/vim/types.ts` + `transitions.ts`**목적**: Vim 키바인딩 입력 처리. **가장 복잡한 상태 머신** (계층적).

```
최상위: 모드 전환
  ┌────────┐  i/a/o/A/I/O  ┌────────┐
  │ NORMAL │ ────────────► │ INSERT │
  └────┬───┘ ◄──────────── └────────┘
       │         Escape
       │
       ▼
NORMAL 모드 내부 (CommandState):

  ┌──────┐
  │ idle │ ← 기본 대기
  └──┬───┘
     │
     ├── d/c/y ──────────► ┌──────────┐
     │                     │ operator │
     │                     └────┬─────┘
     │                          │
     │                          ├── 1-9 ──► operatorCount
     │                          ├── f/F/t/T ► operatorFind
     │                          ├── i/a ──► operatorTextObj
     │                          ├── g ────► operatorG
     │                          └── motion ► [실행]
     │
     ├── 1-9 ────────────► ┌───────┐
     │                     │ count │
     │                     └───────┘
     │
     ├── f/F/t/T ────────► ┌──────┐
     │                     │ find │
     │                     └──────┘
     │
     ├── g ──────────────► ┌─────┐
     │                     │  g  │
     │                     └─────┘
     │
     ├── r ──────────────► ┌─────────┐
     │                     │ replace │
     │                     └─────────┘
     │
     └── > / < ──────────► ┌────────┐
                           │ indent │
                           └────────┘
```

**영속 상태**: 마지막 변경, 마지막 find, 레지스터 (dot-repeat/recall 지원).

---

### 4.2 Keyboard Parse

**위치**: `src/ink/parse-keypress.ts`**목적**: 터미널 입력을 키보드 이벤트로 파싱 + 붙여넣기 모드 처리.

```
  ┌────────┐  PASTE_START   ┌──────────┐
  │ NORMAL │ ─────────────► │ IN_PASTE │
  └────────┘ ◄───────────── └──────────┘
               PASTE_END
```

| 상태 | 설명 |
| --- | --- |
| `NORMAL` | 일반 키보드 입력 파싱 (incomplete 버퍼 + pasteBuffer) |
| `IN_PASTE` | PASTE_START\~PASTE_END 사이 데이터 수집 |

---

## 5. 권한 시스템

### 5.1 Permission Mode

**위치**: `src/utils/permissions/`**목적**: 사용자 권한 모드 순환 및 적용.

```
외부 사용자 순환:
  ┌─────────┐     ┌─────────────┐     ┌──────┐
  │ default │ ──► │ acceptEdits │ ──► │ plan │ ──┐
  └────┬────┘     └─────────────┘     └──────┘  │
       │                                         │
       └────────────────◄────────────────────────┘

Ant 사용자 순환 (추가 모드):
  ┌─────────┐     ┌───────────────────┐     ┌──────┐
  │ default │ ──► │ bypassPermissions │ ──► │ plan │ ──┐
  └────┬────┘     └───────────────────┘     └──────┘  │
       │                ▲                              │
       │                │ (TRANSCRIPT_CLASSIFIER)      │
       │           ┌────┴───┐                          │
       │           │  auto  │ ◄────────────────────────┘
       │           └────────┘
       └────────────────◄──────────────────────────────┘
```

| 상태 | 설명 |
| --- | --- |
| `default` | 모든 도구 사용 시 프롬프트 표시 |
| `acceptEdits` | 파일 편집 자동 허용 (mkdir, touch, rm, mv, cp, sed) |
| `plan` | 읽기 전용 (실행 불가) |
| `bypassPermissions` | 권한 검사 없이 실행 |
| `auto` | 분류기 기반 자동 승인 (ant-only, TRANSCRIPT_CLASSIFIER feature) |
| `dontAsk` | 프롬프트 건너뛰기 (UI 순환에 미노출) |
| `bubble` | 내부 전용 폴백 |

**전이 함수**: `transitionPermissionMode()` — auto 모드 진입 시 위험 규칙 정리 등 컨텍스트 클린업 수행.

---

## 6. UI 상태

### 6.1 Terminal Focus

**위치**: `src/ink/terminal-focus-state.ts`**목적**: DECSET 1004 포커스 이벤트 추적.

```
  ┌─────────┐
  │ unknown │ ← 초기값 (포커스 리포팅 미지원)
  └────┬────┘
       │
       ├── setTerminalFocused(true) ──► ┌─────────┐
       │                                │ focused │
       │                                └─────────┘
       │
       └── setTerminalFocused(false) ─► ┌─────────┐
                                        │ blurred │
                                        └─────────┘
```

### 6.2 Speculation

**위치**: `src/state/AppStateStore.ts`**목적**: 추측 메시지 생성 (모델 응답 대기 중 미리보기 제안).

```
  ┌──────────────────┐                    ┌───────────────────────────────┐
  │ { status: 'idle' }│  시작              │ { status: 'active',           │
  │                   │ ────────────────► │   id, abort, startTime,       │
  │                   │ ◄──────────────── │   messagesRef, boundary,      │
  └──────────────────┘  종료/취소          │   suggestionLength, ...       │
                                          │ }                             │
                                          └───────────────────────────────┘
```

---

## 7. 공통 패턴 분석

### 7.1 구현 패턴

| 패턴 | 사용 예 | 특징 |
| --- | --- | --- |
| **Union 타입** | QueryGuard, Vim, PermissionMode | TypeScript 문자열 리터럴 유니온으로 상태 표현 |
| **플래그 조합** | Bridge Connection | 여러 boolean 플래그 조합으로 상태 유추 |
| **active/inactive** | FlushGate | 단순 boolean 토글 + 큐 |
| **계층적 상태** | Vim (INSERT/NORMAL → CommandState) | 모드 안에 하위 상태 머신 |
| **이벤트 소싱** | Remote Connection, Speculation | AppState 변경으로 상태 전이 |
| **클로저 캡슐화** | QueryGuard, FlushGate | 모듈 수준 private 상태 |

### 7.2 안전 장치 패턴

| 패턴 | 사용 예 |
| --- | --- |
| **재진입 방지** | QueryGuard (dispatching 상태로 비동기 갭 보호) |
| **최대 재시도** | LSP Server (3회), Remote WS (5회) |
| **세대 추적** | QueryGuard (generation 번호로 stale 요청 무시) |
| **강제 종료** | QueryGuard (`forceEnd`), FlushGate (`drop`) |
| **컨텍스트 클린업** | PermissionMode (auto 진입 시 위험 규칙 제거) |

### 7.3 상태 머신 복잡도 스펙트럼

```
간단 ◄──────────────────────────────────────────────► 복잡

FlushGate    Terminal    Keyboard    Bridge     Vim
(2 상태)     Focus      Parse       Status    (12+ 상태,
             (3 상태)   (2 상태)    (5 상태)   계층적)

             Permission  QueryGuard  LSP Server
             Mode        (3 상태,    (5 상태,
             (7 상태,    세대 추적)   크래시 복구)
             순환)
```

### 7.4 라이브러리 사용

Claude Code는 **외부 상태 머신 라이브러리를 사용하지 않는다**. 모든 상태 머신이 순수 TypeScript로 구현되어 있으며, 주로 다음 패턴을 사용:

- **Union 타입 + switch/if**: 가장 일반적
- **클래스 내부 상태**: LSPServerInstance
- **제네릭 큐**: FlushGate
- **AppState 리듀서**: 이벤트 소싱 스타일