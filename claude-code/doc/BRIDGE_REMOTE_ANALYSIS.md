# Bridge & Remote 상세 분석

> Claude Code의 원격 제어(Remote Control), 브릿지 통신, 원격 세션 관리 시스템에 대한 심층 분석 문서

---

## 목차

1. [개요](#1-%EA%B0%9C%EC%9A%94)
2. [아키텍처 개관](#2-%EC%95%84%ED%82%A4%ED%85%8D%EC%B2%98-%EA%B0%9C%EA%B4%80)
3. [Bridge 시스템 — 원격 제어 브릿지](#3-bridge-%EC%8B%9C%EC%8A%A4%ED%85%9C--%EC%9B%90%EA%B2%A9-%EC%A0%9C%EC%96%B4-%EB%B8%8C%EB%A6%BF%EC%A7%80)
   - [두 가지 브릿지 아키텍처](#31-%EB%91%90-%EA%B0%80%EC%A7%80-%EB%B8%8C%EB%A6%BF%EC%A7%80-%EC%95%84%ED%82%A4%ED%85%8D%EC%B2%98)
   - [메시지 흐름](#32-%EB%A9%94%EC%8B%9C%EC%A7%80-%ED%9D%90%EB%A6%84)
   - [Transport 추상화](#33-transport-%EC%B6%94%EC%83%81%ED%99%94)
   - [인증 및 보안](#34-%EC%9D%B8%EC%A6%9D-%EB%B0%8F-%EB%B3%B4%EC%95%88)
   - [세션 관리](#35-%EC%84%B8%EC%85%98-%EA%B4%80%EB%A6%AC)
   - [권한 시스템](#36-%EA%B6%8C%ED%95%9C-%EC%8B%9C%EC%8A%A4%ED%85%9C)
   - [UI 및 상태 표시](#37-ui-%EB%B0%8F-%EC%83%81%ED%83%9C-%ED%91%9C%EC%8B%9C)
   - [장애 복구 및 디버깅](#38-%EC%9E%A5%EC%95%A0-%EB%B3%B5%EA%B5%AC-%EB%B0%8F-%EB%94%94%EB%B2%84%EA%B9%85)
4. [Remote 시스템 — 원격 세션 관리](#4-remote-%EC%8B%9C%EC%8A%A4%ED%85%9C--%EC%9B%90%EA%B2%A9-%EC%84%B8%EC%85%98-%EA%B4%80%EB%A6%AC)
   - [아키텍처](#41-%EC%95%84%ED%82%A4%ED%85%8D%EC%B2%98)
   - [SessionsWebSocket](#42-sessionswebsocket)
   - [RemoteSessionManager](#43-remotesessionmanager)
   - [sdkMessageAdapter](#44-sdkmessageadapter)
   - [remotePermissionBridge](#45-remotepermissionbridge)
5. [Bridge vs Remote 비교](#5-bridge-vs-remote-%EB%B9%84%EA%B5%90)
6. [파일별 역할 요약](#6-%ED%8C%8C%EC%9D%BC%EB%B3%84-%EC%97%AD%ED%95%A0-%EC%9A%94%EC%95%BD)

---

## 1. 개요

Claude Code의 원격 통신 시스템은 두 디렉토리로 구성된다:

| 디렉토리 | 파일 수 | 핵심 역할 |
| --- | --- | --- |
| `bridge/` | 30개 | 원격 제어(Remote Control) 브릿지 — claude.ai/Desktop에서 로컬 CLI 제어 |
| `remote/` | 4개 | 원격 CCR 세션 관리 — 로컬 REPL에서 원격 컨테이너 세션 구독/제어 |

### 핵심 차이

```
Bridge (bridge/)
  claude.ai / Desktop → [인터넷] → 로컬 CLI
  "웹에서 내 컴퓨터의 Claude Code를 원격 조종"

Remote (remote/)
  로컬 REPL → [인터넷] → CCR 컨테이너
  "내 터미널에서 원격 컨테이너의 세션을 구독/관찰"
```

---

## 2. 아키텍처 개관

```
┌─────────────────────────────────────────────────────────────┐
│                    claude.ai / Desktop App                   │
│                     (웹 UI / 데스크톱 앱)                     │
└──────────┬──────────────────────────────────┬───────────────┘
           │                                  │
     Bridge (송신)                      Remote (수신)
           │                                  │
           ▼                                  ▼
┌──────────────────────┐         ┌──────────────────────────┐
│   Anthropic API 서버  │         │     CCR 컨테이너 서버     │
│  (Environments API)   │         │  (Code Session Runtime)  │
│  /v1/code/sessions    │         │  /v1/sessions/ws/        │
└──────────┬───────────┘         └──────────┬───────────────┘
           │                                 │
           ▼                                 ▼
┌──────────────────────┐         ┌──────────────────────────┐
│   bridge/ (30개 파일)  │         │   remote/ (4개 파일)      │
│                       │         │                          │
│  로컬 CLI (Worker)     │         │  로컬 REPL (Viewer)       │
│  ├── 폴링/SSE 수신     │         │  ├── WebSocket 구독       │
│  ├── 도구 실행          │         │  ├── 메시지 변환          │
│  ├── 결과 전송          │         │  ├── 권한 요청 처리       │
│  └── 권한 프록시        │         │  └── HTTP 메시지 전송     │
└──────────────────────┘         └──────────────────────────┘
```

---

## 3. Bridge 시스템 — 원격 제어 브릿지

### 3.1 두 가지 브릿지 아키텍처

Bridge 시스템은 두 가지 독립적인 아키텍처를 제공한다:

#### Env-based Bridge (환경 기반)

```
bridgeMain.ts → bridgeApi.ts → Environments API
  │
  ├── Poll: 작업 대기열에서 새 작업 폴링
  ├── Register: 워커 등록
  ├── Heartbeat: 주기적 생존 신호
  ├── Ack: 작업 완료 확인
  └── Stop: 작업 중단
```

| 파일 | 역할 |
| --- | --- |
| `bridgeMain.ts` | 멀티세션 오케스트레이터 (worktree 관리) |
| `bridgeApi.ts` | Environments API HTTP 클라이언트 |
| `replBridge.ts` | 단일 세션 메시지 라우팅 |
| `sessionRunner.ts` | 자식 CLI 프로세스 스폰 + 모니터링 |

#### Env-less Bridge (환경 비의존)

```
remoteBridgeCore.ts → codeSessionApi.ts → /v1/code/sessions API
  │
  ├── createSession: 세션 생성
  ├── POST /bridge: OAuth → worker_jwt 교환
  └── SSETransport: 실시간 메시지 스트림
```

| 파일 | 역할 |
| --- | --- |
| `remoteBridgeCore.ts` | 직접 OAuth→JWT 연결 |
| `codeSessionApi.ts` | CCR v2 세션 API 래퍼 |
| `envLessBridgeConfig.ts` | 설정 (재시도, 타임아웃, heartbeat) |

### 3.2 메시지 흐름

#### 인바운드 (웹 → 로컬)

```
claude.ai에서 사용자 입력
  │
  ▼
Anthropic API 서버 (메시지 큐)
  │
  ▼
Transport (SSE 또는 Hybrid)
  │
  ▼
bridgeMessaging.ts
  ├── handleIngressMessage()
  │   ├── 사용자 메시지 파싱
  │   └── 이미지 블록 정규화
  ├── handleServerControlRequest()
  │   ├── 권한 요청 처리
  │   └── stdout 요청 처리
  └── BoundedUUIDSet (중복 제거)
       └── 에코/재전송 메시지 필터링
  │
  ▼
inboundMessages.ts
  ├── extractInboundMessageFields()
  │   └── 메시지 내용 + UUID 추출
  └── normalizeImageBlocks()
      └── camelCase → snake_case 변환
  │
  ▼
inboundAttachments.ts
  └── resolveAllAttachments()
      └── file_uuid → 실제 파일 다운로드 (~/.claude/uploads/)
```

#### 아웃바운드 (로컬 → 웹)

```
로컬 CLI 응답 (assistant/tool_result/system)
  │
  ▼
bridgeMessaging.ts
  ├── isEligibleBridgeMessage()
  │   └── 전송 대상 메시지 필터링
  └── makeResultMessage()
      └── 결과 프레임 생성
  │
  ▼
replBridgeTransport.ts
  ├── write() / writeBatch()
  └── reportState() / reportMetadata()
  │
  ▼
Transport → Anthropic API → claude.ai
```

### 3.3 Transport 추상화

`replBridgeTransport.ts`가 v1/v2 트랜스포트를 통합 인터페이스로 추상화한다:

```typescript
interface ReplBridgeTransport {
  write(msg)              // 단일 메시지 전송
  writeBatch(msgs)        // 배치 전송
  connect()               // 연결 수립
  isConnectedStatus()     // 연결 상태 확인
  getLastSequenceNum()    // 시퀀스 번호 (재전송용)
  reportState(state)      // 상태 보고
  reportMetadata(meta)    // 메타데이터 보고
  reportDelivery(info)    // 전송 확인
}
```

| 버전 | 팩토리 함수 | 내부 구현 |
| --- | --- | --- |
| v1 | `createV1ReplTransport()` | HybridTransport (HTTP 폴링 + WebSocket) |
| v2 | `createV2ReplTransport()` | SSETransport + CCRClient (Server-Sent Events) |

### 3.4 인증 및 보안

#### 인증 체인

```
bridgeConfig.ts
  ├── getBridgeAccessToken()
  │   ├── 환경변수 오버라이드 (ant-only)
  │   └── OAuth 키체인 토큰
  │
  └── getBridgeBaseUrl()
      ├── CLAUDE_BRIDGE_BASE_URL (ant-only)
      └── 프로덕션 OAuth URL
```

#### 토큰 관리

```
jwtUtils.ts
  ├── decodeJwtPayload()     → 페이로드 추출 (검증 없이)
  ├── decodeJwtExpiry()      → exp 클레임 추출
  └── createTokenRefreshScheduler()
      ├── 만료 5분 전 사전 갱신
      └── 최대 3회 실패 허용
```

#### 신뢰 디바이스 (Trusted Device)

```
trustedDevice.ts
  ├── getTrustedDeviceToken()   → 보안 스토리지/환경변수에서 읽기
  ├── enrollTrustedDevice()     → POST /auth/trusted_devices (로그인 시)
  └── clearTrustedDeviceToken() → 로그아웃 시 정리

게이트: tengu_sessions_elevated_auth_enforcement (GrowthBook)
```

#### Work Secret (세션 접근 자격증명)

```
workSecret.ts
  ├── decodeWorkSecret()     → base64url 디코딩 + 버전 검증
  ├── buildSdkUrl()          → ws(s):// 인그레스 URL 생성
  ├── buildCCRv2SdkUrl()     → HTTP(S) SDK URL 생성
  ├── registerWorker()       → POST /register → worker JWT 획득
  └── sameSessionId()        → cse_ / session_ 태그 무시 비교
```

### 3.5 세션 관리

#### 세션 생성

```
createSession.ts
  └── createBridgeSession()
      ├── POST /v1/sessions
      ├── 제목 + Git 컨텍스트 + 이벤트
      └── GitSource, GitOutcome (저장소 메타데이터)

codeSessionApi.ts
  ├── createCodeSession()
  │   └── POST /v1/code/sessions (CCR v2)
  └── fetchRemoteCredentials()
      └── POST /v1/code/sessions/{id}/bridge → worker JWT
```

#### 세션 ID 호환성

```
sessionIdCompat.ts
  ├── toCompatSessionId()   → cse_* → session_* (v1 호환)
  └── toInfraSessionId()    → session_* → cse_* (인프라)

같은 UUID, 다른 태그 (API 계층마다 다른 접두사)
```

#### 크래시 복구

```
bridgePointer.ts
  ├── BridgePointer: { sessionId, environmentId, source }
  ├── BRIDGE_POINTER_TTL_MS: 4시간 (유효 기간)
  ├── writeBridgePointer()  → 포인터 파일 + mtime 갱신
  └── readBridgePointer()   → 읽기 + 유효성 + 신선도 검증

용도: `claude remote-control --session-id` 재개 플로우
```

#### 활성화 조건

```
bridgeEnabled.ts
  ├── isBridgeEnabled()          → GrowthBook 캐시 (빠름)
  ├── isBridgeEnabledBlocking()  → GrowthBook 새로고침 대기
  ├── getBridgeDisabledReason()  → 비활성 이유 진단 메시지
  └── isClaudeAISubscriber()     → OAuth 토큰 존재 확인

필수 조건: claude.ai 구독 + tengu_ccr_bridge GrowthBook 플래그
```

### 3.6 권한 시스템

```
bridgePermissionCallbacks.ts

BridgePermissionCallbacks {
  sendRequest(req)    → 권한 요청 전송
  sendResponse(res)   → 권한 응답 전송
  cancelRequest(id)   → 요청 취소
  onResponse(cb)      → 응답 수신 콜백
}

BridgePermissionResponse {
  behavior: 'allow' | 'deny'
  updatedInput?       → 수정된 도구 입력
  updatedPermissions? → 갱신된 권한 규칙
  message?            → 거부 사유
}
```

### 3.7 UI 및 상태 표시

#### Bridge Logger (터미널 UI)

```
bridgeUI.ts → createBridgeLogger(options) → BridgeLogger

BridgeLogger {
  printBanner()    → QR 코드 + 연결 URL 표시
  updateState()    → 상태 전이 (idle → attached → titled → ...)
  setActivity()    → 현재 도구 활동 표시
  clearActivity()  → 활동 정리
  shutdown()       → UI 종료
}
```

#### 상태 머신

```
StatusState: 'idle' → 'attached' → 'titled' → 'reconnecting' → 'failed'

idle:          연결 대기 중 (QR 코드 표시)
attached:      클라이언트 연결됨
titled:        세션 제목 설정됨 (작업 시작)
reconnecting:  일시적 연결 끊김, 재연결 중
failed:        연결 실패
```

#### 상태 표시 유틸리티

```
bridgeStatusUtil.ts
  ├── buildBridgeConnectUrl()     → QR/표시용 연결 URL
  ├── buildBridgeSessionUrl()     → 세션 직접 URL
  ├── timestamp()                 → 시간 포맷
  ├── formatDuration()            → 경과 시간 포맷
  ├── abbreviateActivity()        → 활동 텍스트 축약
  ├── computeShimmerSegments()    → Grapheme 인식 애니메이션
  └── computeGlimmerIndex()       → 역방향 스윕 반짝임 인덱스
```

### 3.8 장애 복구 및 디버깅

#### FlushGate (메시지 큐잉)

```
flushGate.ts → FlushGate<T>

초기 히스토리 플러시 중 새 메시지가 도착하면 큐잉하여
인터리빙(메시지 뒤섞임) 방지.

라이프사이클: start() → enqueue() → end() → deactivate()
```

#### CapacityWake (용량 대기)

```
capacityWake.ts → createCapacityWake(outerSignal)

세션 한도에 도달했을 때 sleep하고, 용량이 확보되면 wake.
외부 abort 신호와 내부 wake를 병합.
```

#### 폴링 설정

```
pollConfigDefaults.ts → DEFAULT_POLL_CONFIG

비용량: 2초 간격
용량초과: 10분 간격
하트비트: 20초
```

#### 디버그 도구 (ant-only)

```
bridgeDebug.ts
  ├── BridgeDebugHandle
  │   ├── fireClose()        → 강제 연결 끊기
  │   ├── forceReconnect()   → 강제 재연결
  │   ├── injectFault()      → 다음 N회 API 호출에 장애 주입
  │   └── describe()         → 현재 상태 설명
  └── wrapApiForFaultInjection()
      └── BridgeApiClient를 감싸 장애 큐 확인

사용: /bridge-kick 슬래시 커맨드

debugUtils.ts
  ├── redactSecrets()        → 인증 토큰 마스킹
  ├── debugTruncate()        → 줄바꿈 축약 + 잘라내기
  ├── debugBody()            → JSON 직렬화 + 마스킹
  └── describeAxiosError()   → axios 에러 메시지 추출
```

---

## 4. Remote 시스템 — 원격 세션 관리

### 4.1 아키텍처

Remote 시스템은 4개 파일로 구성된 깔끔한 계층 구조다:

```
┌────────────────────────────────────┐
│       RemoteSessionManager         │  ← 최상위 오케스트레이터
│  (세션 조율, 권한 플로우 관리)       │
├────────┬───────────────────────────┤
│        │                           │
│        ▼                           ▼
│  SessionsWebSocket          remotePermissionBridge
│  (WebSocket 클라이언트)      (권한 어댑터)
│  ├── 재연결 로직              ├── 합성 AssistantMessage
│  ├── Ping/Pong               └── 도구 스텁 생성
│  └── 메시지 라우팅
├────────────────────────────────────┤
│        sdkMessageAdapter           │  ← 메시지 변환기
│  (SDKMessage → REPL Message)       │
│  20개+ SDK 타입 → 로컬 포맷 변환    │
└────────────────────────────────────┘
         │
         ▼
      REPL UI / Display
```

### 4.2 SessionsWebSocket

**역할**: CCR 세션 메시지 스트림에 대한 저수준 WebSocket 클라이언트.

#### 연결 대상

```
wss://api.anthropic.com/v1/sessions/ws/{sessionId}/subscribe
```

#### 재연결 전략

| 상황 | 동작 |
| --- | --- |
| 코드 4003 (Unauthorized) | 즉시 종료 (영구) |
| 코드 4001 (Session Not Found) | 최대 3회 재시도 (서버 압축 중 일시적) |
| 기타 일시적 에러 | 최대 5회 재시도, 지수 백오프 (2초 기반) |
| Ping/Pong | 30초 간격 연결 유지 |

#### 메시지 타입

```typescript
type SessionsMessage =
  | SDKMessage              // 모델 응답, 도구 결과 등
  | SDKControlRequest       // 권한 요청 (can_use_tool)
  | SDKControlResponse      // 권한 응답 확인
  | SDKControlCancelRequest // 권한 요청 취소
```

#### 런타임 호환

```
WebSocket 선택:
  ├── Bun 환경 → globalThis.WebSocket
  └── Node.js 환경 → ws 라이브러리
```

### 4.3 RemoteSessionManager

**역할**: 원격 CCR 세션의 최상위 조율자. WebSocket 구독(수신), HTTP 전송(송신), 권한 플로우를 관리.

#### 핵심 상태

```typescript
class RemoteSessionManager {
  private ws: SessionsWebSocket
  private pendingPermissionRequests: Map<string, SDKControlPermissionRequest>
  private config: RemoteSessionConfig
  private callbacks: RemoteSessionCallbacks
}
```

#### 메시지 플로우

```
[인바운드] CCR → WebSocket → handleMessage()
  │
  ├── SDKMessage
  │   └── callbacks.onMessage(msg) → REPL 표시
  │
  ├── SDKControlRequest (can_use_tool)
  │   ├── pendingPermissionRequests.set(id, req)
  │   └── callbacks.onPermissionRequest(req)
  │       └── REPL이 사용자에게 권한 묻기
  │
  ├── SDKControlCancelRequest
  │   ├── pendingPermissionRequests.delete(id)
  │   └── callbacks.onPermissionCancelled(id)
  │
  └── SDKControlResponse
      └── (서버 확인, 보통 무시)

[아웃바운드] REPL → sendMessage() → HTTP POST
  └── sendEventToRemoteSession() → Teleport API

[권한 응답] REPL → respondToPermissionRequest()
  └── SDKControlResponse → WebSocket 전송
      └── { behavior: 'allow' | 'deny', updatedInput? }
```

#### 세션 제어

```typescript
connect()       // WebSocket 연결 수립
disconnect()    // 연결 종료 + 권한 맵 정리
reconnect()     // 강제 재연결 (컨테이너 재시작 후)
cancelSession() // 인터럽트 컨트롤 요청 전송
sendMessage()   // HTTP POST로 메시지 전송
```

### 4.4 sdkMessageAdapter

**역할**: CCR의 SDK 메시지 포맷을 로컬 REPL의 내부 Message 포맷으로 변환.

#### 변환 결과 타입

```typescript
type ConvertedMessage =
  | { type: 'message', message: Message }    // 변환 성공
  | { type: 'stream_event', event: StreamEvent } // 스트리밍 이벤트
  | { type: 'ignored' }                      // 무시 (호환용)
```

#### SDK 타입별 변환 규칙

| SDK 타입 | 변환 결과 | 비고 |
| --- | --- | --- |
| `assistant` | `AssistantMessage` | 전체 내용 포함 |
| `user` | `UserMessage` (조건부) | convertToolResults/convertUserTextMessages 플래그 |
| `stream_event` | `StreamEvent` | 스트리밍 청크 래핑 |
| `result` (에러) | `SystemMessage` | 성공은 무시 (멀티턴 노이즈) |
| `system` (init) | `SystemMessage` | 모델 이름 표시 |
| `system` (status) | `SystemMessage` | 'compacting' 특수 처리 |
| `system` (compact_boundary) | `SystemMessage` | compactMetadata 포함 |
| `system` (hook_response 등) | `{ type: 'ignored' }` | 디버그 로깅만 |
| `tool_progress` | `SystemMessage` | 경과 시간 표시 |
| `auth_status` | `{ type: 'ignored' }` | 별도 처리 |
| `tool_use_summary` | `{ type: 'ignored' }` | SDK 전용 |
| `rate_limit_event` | `{ type: 'ignored' }` | SDK 전용 |
| 알 수 없는 타입 | `{ type: 'ignored' }` | 전방 호환 (크래시 방지) |

#### 변환 옵션

```typescript
type ConvertOptions = {
  convertToolResults?: boolean     // 도구 결과 포함 (direct 모드)
  convertUserTextMessages?: boolean // 사용자 텍스트 포함 (히스토리 이벤트)
}
```

### 4.5 remotePermissionBridge

**역할**: 원격 도구 권한 요청을 로컬 REPL의 권한 시스템에서 처리할 수 있도록 어댑터 역할.

#### 합성 메시지 생성

```typescript
createSyntheticAssistantMessage(request, requestId)
  → AssistantMessage {
      id: 'remote-{requestId}'
      container: null           // 로컬 도구 사용과 구분
      content: [tool_use 블록]  // 원격 요청을 로컬 포맷으로 래핑
    }
```

#### 도구 스텁 생성

```typescript
createToolStub(toolName)
  → Tool {
      inputSchema: empty
      enabled: true
      needsPermissions: true
      renderToolUseMessage: 입력 파라미터 상위 3개 표시
      call: 빈 데이터 반환
    }
```

> **용도**: 로컬에 존재하지 않는 MCP 도구(CCR에서 실행 중인)의 권한 요청을 처리. 스텁이 없으면 "tool not found" 에러 발생.

---

## 5. Bridge vs Remote 비교

| 관심사 | Bridge (`bridge/`) | Remote (`remote/`) |
| --- | --- | --- |
| **방향** | 웹 → 로컬 (인바운드 제어) | 로컬 → 원격 (아웃바운드 구독) |
| **역할** | 로컬 CLI가 워커 (명령 실행) | 로컬 REPL이 뷰어 (결과 관찰) |
| **파일 수** | 30개 | 4개 |
| **통신** | Environments API (폴링/SSE) | WebSocket (실시간 구독) |
| **인증** | OAuth + JWT + Work Secret | OAuth Bearer 토큰 |
| **세션 관리** | 멀티세션 (worktree) | 단일 세션 |
| **메시지 전송** | Transport 추상화 (v1/v2) | HTTP POST (Teleport API) |
| **메시지 수신** | SSE/HybridTransport | WebSocket |
| **권한** | 양방향 (요청+응답) | 원격 요청 → 로컬 처리 |
| **UI** | QR 코드, 상태 배너, 활동 표시 | 없음 (REPL UI에 위임) |
| **크래시 복구** | BridgePointer 파일 | 없음 (재연결) |
| **디버깅** | 장애 주입, /bridge-kick | 없음 |
| **활성화 조건** | claude.ai 구독 + GrowthBook | (Bridge 의존 없음) |
| **bridge/ 의존** | — | 없음 (독립적) |

---

## 6. 파일별 역할 요약

### bridge/ (30개 파일)

#### 핵심 (Core)

| 파일 | 역할 |
| --- | --- |
| `types.ts` | 핵심 타입 정의 (WorkData, SessionActivity, SpawnMode 등) |
| `bridgeMain.ts` | Env-based 멀티세션 오케스트레이터 |
| `remoteBridgeCore.ts` | Env-less 직접 연결 브릿지 |
| `replBridge.ts` | 단일 세션 REPL 브릿지 (메시지 라우팅) |
| `initReplBridge.ts` | REPL 전용 초기화 래퍼 |

#### 통신 (Transport & Messaging)

| 파일 | 역할 |
| --- | --- |
| `replBridgeTransport.ts` | v1/v2 Transport 추상화 계층 |
| `bridgeMessaging.ts` | 인바운드 메시지 파싱, 중복 제거, 결과 프레임 |
| `inboundMessages.ts` | 메시지 필드 추출, 이미지 블록 정규화 |
| `inboundAttachments.ts` | 파일 UUID → 실제 파일 다운로드 |
| `flushGate.ts` | 히스토리 플러시 중 메시지 큐잉 |
| `capacityWake.ts` | 용량 대기 + wake 프리미티브 |

#### 인증 & 보안 (Auth & Security)

| 파일 | 역할 |
| --- | --- |
| `bridgeConfig.ts` | 인증 토큰/URL 중앙 관리 |
| `jwtUtils.ts` | JWT 디코딩, 사전 토큰 갱신 스케줄러 |
| `trustedDevice.ts` | 신뢰 디바이스 등록/관리 |
| `workSecret.ts` | Work Secret 디코딩, SDK URL 생성, 워커 등록 |
| `bridgeEnabled.ts` | 런타임 활성화 조건 (GrowthBook + OAuth) |

#### 세션 (Session)

| 파일 | 역할 |
| --- | --- |
| `createSession.ts` | POST /v1/sessions (세션 생성) |
| `codeSessionApi.ts` | CCR v2 세션 API (code/sessions) |
| `sessionRunner.ts` | 자식 CLI 프로세스 스폰 + 활동 추적 |
| `sessionIdCompat.ts` | cse\_ ↔ session\_ 태그 변환 |
| `bridgePointer.ts` | 크래시 복구 상태 파일 (4시간 TTL) |
| `pollConfigDefaults.ts` | 폴링 간격 기본값 (2s/10min/20s) |
| `envLessBridgeConfig.ts` | Env-less 브릿지 설정 (재시도, heartbeat) |

#### 권한 (Permissions)

| 파일 | 역할 |
| --- | --- |
| `bridgePermissionCallbacks.ts` | 권한 요청/응답 타입 + 콜백 인터페이스 |
| `replBridgeHandle.ts` | 활성 브릿지 전역 포인터 |

#### UI & 디버깅

| 파일 | 역할 |
| --- | --- |
| `bridgeUI.ts` | 터미널 UI (QR, 스피너, 활동 트레일) |
| `bridgeStatusUtil.ts` | URL 빌더, 포맷터, 애니메이션 유틸리티 |
| `bridgeDebug.ts` | 장애 주입 (ant-only, /bridge-kick) |
| `debugUtils.ts` | 시크릿 마스킹, 에러 추출 |

### remote/ (4개 파일)

| 파일 | 역할 |
| --- | --- |
| `SessionsWebSocket.ts` | WebSocket 클라이언트 (재연결, Ping/Pong, 메시지 라우팅) |
| `RemoteSessionManager.ts` | 최상위 오케스트레이터 (WebSocket + HTTP + 권한) |
| `sdkMessageAdapter.ts` | SDKMessage → REPL Message 변환기 (20개+ 타입) |
| `remotePermissionBridge.ts` | 원격 권한 요청 → 로컬 권한 시스템 어댑터 |
