# Claude in Chrome 상세 분석

> Claude Code의 Chrome 브라우저 자동화 시스템에 대한 심층 분석 문서

---

## 목차

1. [개요](#1-%EA%B0%9C%EC%9A%94)
2. [아키텍처](#2-%EC%95%84%ED%82%A4%ED%85%8D%EC%B2%98)
3. [통신 계층](#3-%ED%86%B5%EC%8B%A0-%EA%B3%84%EC%B8%B5)
   - [Chrome Native Messaging](#31-chrome-native-messaging)
   - [MCP 서버](#32-mcp-%EC%84%9C%EB%B2%84)
   - [소켓 통신](#33-%EC%86%8C%EC%BC%93-%ED%86%B5%EC%8B%A0)
4. [설치 및 설정](#4-%EC%84%A4%EC%B9%98-%EB%B0%8F-%EC%84%A4%EC%A0%95)
   - [setup.ts](#41-setupts)
   - [setupPortable.ts](#42-setupportablets)
   - [브라우저 감지](#43-%EB%B8%8C%EB%9D%BC%EC%9A%B0%EC%A0%80-%EA%B0%90%EC%A7%80)
5. [스킬 및 도구](#5-%EC%8A%A4%ED%82%AC-%EB%B0%8F-%EB%8F%84%EA%B5%AC)
   - [번들 스킬](#51-%EB%B2%88%EB%93%A4-%EC%8A%A4%ED%82%AC-claudeinchromets)
   - [17개 브라우저 도구](#52-17%EA%B0%9C-%EB%B8%8C%EB%9D%BC%EC%9A%B0%EC%A0%80-%EB%8F%84%EA%B5%AC)
   - [도구 렌더링](#53-%EB%8F%84%EA%B5%AC-%EB%A0%8C%EB%8D%94%EB%A7%81-toolrenderingtsx)
6. [프롬프트 전략](#6-%ED%94%84%EB%A1%AC%ED%94%84%ED%8A%B8-%EC%A0%84%EB%9E%B5)
7. [UI 컴포넌트](#7-ui-%EC%BB%B4%ED%8F%AC%EB%84%8C%ED%8A%B8)
   - [/chrome 커맨드](#71-chrome-%EC%BB%A4%EB%A7%A8%EB%93%9C)
   - [온보딩](#72-%EC%98%A8%EB%B3%B4%EB%94%A9)
   - [Hook: 알림](#73-hook-%EC%95%8C%EB%A6%BC)
   - [Hook: 프롬프트 수신](#74-hook-%ED%94%84%EB%A1%AC%ED%94%84%ED%8A%B8-%EC%88%98%EC%8B%A0)
8. [WebBrowserTool (Bagel)](#8-webbrowsertool-bagel)
9. [파일별 역할 요약](#9-%ED%8C%8C%EC%9D%BC%EB%B3%84-%EC%97%AD%ED%95%A0-%EC%9A%94%EC%95%BD)

---

## 1. 개요

**Claude in Chrome**은 Claude Code가 Chrome 브라우저를 직접 제어할 수 있게 해주는 시스템이다. Chrome 확장 프로그램과 Native Messaging 프로토콜을 통해 연결하며, MCP(Model Context Protocol) 서버를 통해 17개 브라우저 자동화 도구를 제공한다.

| 항목 | 내용 |
| --- | --- |
| **파일 수** | 13개 (utils 7 + commands 2 + hooks 2 + components 1 + skills 1) |
| **연결 방식** | Chrome Native Messaging → Unix Socket/Named Pipe → MCP |
| **도구 접두사** | `mcp__claude-in-chrome__*` |
| **도구 수** | 17개 (탭, 네비게이션, DOM, 스크린샷, 폼, 콘솔 등) |
| **요구 사항** | claude.ai 구독 + Chrome 확장 프로그램 설치 |
| **코드네임** | Bagel (WebBrowserTool), Chrome Yellow (테마 컬러) |

### 파일 구조

```
src/
├── utils/claudeInChrome/              # 핵심 유틸리티 (7개)
│   ├── mcpServer.ts                   # MCP 서버 (Chrome 브릿지 연결)
│   ├── chromeNativeHost.ts            # Chrome Native Messaging 호스트
│   ├── setup.ts                       # 설치/설정 오케스트레이션
│   ├── setupPortable.ts               # 포터블 확장 감지
│   ├── prompt.ts                      # 브라우저 자동화 프롬프트
│   ├── common.ts                      # 브라우저 감지, 경로, 소켓
│   └── toolRendering.tsx              # 도구 UI 렌더링 (17개)
├── commands/chrome/                   # /chrome 슬래시 커맨드
│   ├── chrome.tsx                     # 메뉴 UI 컴포넌트
│   └── index.ts                       # 커맨드 메타데이터
├── skills/bundled/
│   └── claudeInChrome.ts             # 번들 스킬 등록
├── hooks/
│   ├── useChromeExtensionNotification.tsx  # 확장 상태 알림
│   └── usePromptsFromClaudeInChrome.tsx   # 확장 → CLI 프롬프트 수신
└── components/
    └── ClaudeInChromeOnboarding.tsx   # 최초 사용 온보딩 다이얼로그
```

---

## 2. 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                     Chrome 브라우저                               │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │          Claude in Chrome 확장 프로그램                │       │
│  │  ├── 탭 관리, DOM 조작, 스크린샷                       │       │
│  │  ├── 폼 입력, 네비게이션, 콘솔 로그                    │       │
│  │  └── 사이트별 권한 관리                                │       │
│  └──────────┬───────────────────────────────────────────┘       │
│             │ Chrome Native Messaging (stdin/stdout)             │
│             │ 4바이트 길이 접두사 + UTF-8 JSON (최대 1MB)         │
└─────────────┼───────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│    Chrome Native Host 프로세스       │
│    (chromeNativeHost.ts)            │
│                                      │
│  ├── ChromeMessageReader (stdin)    │
│  ├── sendChromeMessage (stdout)     │
│  └── Unix Socket / Named Pipe 서버  │
└──────────┬──────────────────────────┘
           │ Unix Socket (macOS/Linux)
           │ Named Pipe (Windows)
           │ /tmp/claude-mcp-browser-bridge-{user}/{pid}.sock
           ▼
┌─────────────────────────────────────┐
│    MCP 서버 프로세스                  │
│    (mcpServer.ts)                   │
│                                      │
│  ├── ClaudeForChromeMcpServer       │
│  ├── 17개 브라우저 도구 제공          │
│  ├── 권한 모드 관리                  │
│  └── 분석/텔레메트리                  │
└──────────┬──────────────────────────┘
           │ MCP stdio 프로토콜
           ▼
┌─────────────────────────────────────┐
│    Claude Code CLI                   │
│                                      │
│  ├── 스킬 (claudeInChrome.ts)       │
│  ├── 프롬프트 수신 Hook              │
│  ├── 도구 렌더링 (toolRendering)     │
│  └── /chrome 커맨드                  │
└─────────────────────────────────────┘
```

### 통신 체인 요약

```
Chrome 확장 ←→ Native Messaging ←→ Native Host ←→ Socket ←→ MCP Server ←→ Claude Code
   (브라우저)     (stdin/stdout)      (프로세스)     (IPC)     (프로세스)     (CLI)
```

---

## 3. 통신 계층

### 3.1 Chrome Native Messaging

`chromeNativeHost.ts`가 Chrome Native Messaging 호스트 역할:

```
Chrome 확장 → stdin → ChromeMessageReader → 파싱 → 라우팅
                                                      │
                                                      ▼
                                              MCP 클라이언트(들)
                                                      │
                                                      ▼
Chrome 확장 ← stdout ← sendChromeMessage ← 응답 ← MCP 클라이언트
```

**바이너리 프로토콜**:

```
[4바이트 리틀엔디언 길이][UTF-8 JSON 페이로드]
최대 메시지 크기: 1MB (Chrome 제한)
```

**메시지 라우팅**:

| 메시지 타입 | 방향 | 설명 |
| --- | --- | --- |
| `tool_request` | Chrome → MCP | 도구 실행 요청 |
| `tool_response` | MCP → Chrome | 도구 실행 결과 |
| `notification` | 양방향 | 이벤트 알림 |
| `ping` / `pong` | 양방향 | 연결 상태 확인 |

### 3.2 MCP 서버

`mcpServer.ts`가 MCP 서버 로직 실행:

```
createChromeContext()
  │
  ├── 브릿지 URL 결정
  │   ├── 로컬 개발: localhost
  │   ├── 스테이징: staging URL
  │   └── 프로덕션: production URL
  │
  ├── 권한 모드 설정
  │   ├── 'ask': 기본 (사용자에게 묻기)
  │   ├── 'skip_all_permission_checks': bypassPermissions
  │   └── 'follow_a_plan': 계획 따르기
  │
  ├── Ant 전용: callAnthropicMessages 콜백
  │   └── browser_task + lightning_turn 도구 활성화
  │
  └── 분석 메타데이터 sanitize
      └── 페이지 콘텐츠/사용자 데이터 유출 방지
```

### 3.3 소켓 통신

`common.ts`가 크로스 플랫폼 소켓 관리:

| 플랫폼 | 소켓 타입 | 경로 |
| --- | --- | --- |
| macOS | Unix Socket | `/tmp/claude-mcp-browser-bridge-{user}/{pid}.sock` |
| Linux | Unix Socket | `/tmp/claude-mcp-browser-bridge-{user}/{pid}.sock` |
| Windows | Named Pipe | `\\.\pipe\claude-mcp-browser-bridge-{user}` |

```
소켓 디렉토리: 0o700 퍼미션 (소유자만 접근)
Stale 소켓 감지: PID 기반 (프로세스 종료 시 정리)
다중 MCP 클라이언트 → 단일 Chrome 확장 연결 지원
```

---

## 4. 설치 및 설정

### 4.1 setup.ts

설치 오케스트레이션:

```
shouldEnableClaudeInChrome()
  │
  ├── CLI 플래그: --chrome (활성) / --no-chrome (비활성)
  ├── 환경 변수 확인
  └── 설정 파일 (globalConfig)
  │
  ▼
setupClaudeInChrome()
  │
  ├── MCP 설정 생성
  ├── 허용 도구 목록 설정
  └── 시스템 프롬프트 주입
  │
  ▼
installChromeNativeHostManifest()
  │
  ├── 래퍼 스크립트 생성
  │   ├── Unix: bash 스크립트
  │   └── Windows: .bat 파일
  │   (Chrome manifest에 인자를 포함할 수 없어서 래퍼 필요)
  │
  ├── manifest.json 설치
  │   ├── Chrome, Brave, Edge, Arc, Chromium, Vivaldi, Opera
  │   └── 각 브라우저의 NativeMessagingHosts 디렉토리
  │
  ├── 확장 ID 허용
  │   ├── PROD_EXTENSION_ID
  │   ├── DEV_EXTENSION_ID
  │   └── ANT_EXTENSION_ID (내부용)
  │
  └── Windows: 레지스트리 등록 (reg.exe)
```

### 4.2 setupPortable.ts

확장 설치 감지 (VS Code 확장, TUI 등에서도 사용 가능한 포터블 버전):

```
detectExtensionInstallationPortable()
  │
  ├── 모든 브라우저 프로필 스캔
  │   ├── Default
  │   ├── Profile 1, Profile 2, ...
  │   └── Extensions/{extensionId}/ 존재 확인
  │
  ├── 첫 매칭 시 즉시 반환 (브라우저 타입 포함)
  └── 감지 실패 시 graceful 처리 (브라우저 미설치)
```

### 4.3 브라우저 감지

`common.ts`의 `CHROMIUM_BROWSERS` — 7개 브라우저 지원:

| 브라우저 | 우선순위 | macOS 경로 | Linux 바이너리 |
| --- | --- | --- | --- |
| Chrome | 1 | `~/Library/.../Google/Chrome` | `google-chrome` |
| Brave | 2 | `~/Library/.../BraveSoftware/Brave-Browser` | `brave-browser` |
| Arc | 3 | `~/Library/.../Arc` | — |
| Edge | 4 | `~/Library/.../Microsoft Edge` | `microsoft-edge` |
| Chromium | 5 | `~/Library/.../Chromium` | `chromium-browser` |
| Vivaldi | 6 | `~/Library/.../Vivaldi` | `vivaldi` |
| Opera | 7 | `~/Library/.../com.operasoftware.Opera` | `opera` |

---

## 5. 스킬 및 도구

### 5.1 번들 스킬 (claudeInChrome.ts)

```typescript
registerClaudeInChromeSkill()
  │
  ├── 이름: 'claude-in-chrome'
  ├── 설명: "Automates Chrome - clicking, forms, screenshots, console, navigation"
  ├── whenToUse: "When user wants to interact with web pages or automate browser"
  ├── userInvocable: true
  ├── allowedTools: 모든 mcp__claude-in-chrome__* 도구
  │
  └── 프롬프트:
      ├── BASE_CHROME_PROMPT (브라우저 자동화 가이드)
      └── SKILL_ACTIVATION_MESSAGE
          └── "Always call tabs_context_mcp first"
```

### 5.2 17개 브라우저 도구

`mcp__claude-in-chrome__` 접두사의 도구 목록:

| 도구 | 역할 |
| --- | --- |
| `tabs_context_mcp` | 현재 탭 상태 조회 (항상 먼저 호출) |
| `tabs_create_mcp` | 새 탭 생성 |
| `navigate` | URL 네비게이션 |
| `read_page` | 페이지 DOM 읽기 |
| `get_page_text` | 페이지 텍스트 추출 |
| `find` | 페이지 내 요소 검색 |
| `computer` | 클릭, 스크롤 등 마우스/키보드 액션 |
| `form_input` | 폼 필드 입력 |
| `javascript_tool` | JavaScript 코드 실행 |
| `read_console_messages` | 콘솔 로그 읽기 |
| `read_network_requests` | 네트워크 요청 읽기 |
| `shortcuts_list` | 키보드 단축키 목록 |
| `shortcuts_execute` | 키보드 단축키 실행 |
| `resize_window` | 브라우저 창 크기 조절 |
| `upload_image` | 이미지 업로드 |
| `gif_creator` | GIF 녹화 |
| `update_plan` | 작업 계획 업데이트 |
| `switch_browser` | 브라우저 전환 |

### 5.3 도구 렌더링 (toolRendering.tsx)

각 도구의 CLI 표시를 커스터마이징:

```
getClaudeInChromeMCPToolOverrides()
  │
  ├── navigate → 호스트네임 표시 (30자 제한)
  ├── find → 검색 패턴 표시 (20자 제한)
  ├── computer → 액션 상세 (click, scroll 등)
  ├── javascript_tool → verbose 시 전체 코드, 아니면 빈 문자열
  ├── form_input → 입력 필드 정보
  └── 공통: "[View Tab]" 하이퍼링크 (https://clau.de/chrome/tab/{tabId})
```

**탭 ID 추적**: 200개 항목 링 버퍼로 세션 내 사용 탭 관리.

---

## 6. 프롬프트 전략

`prompt.ts`의 `BASE_CHROME_PROMPT`:

### 필수 규칙

```
1. 세션 시작 시 반드시 tabs_context_mcp 먼저 호출
2. 이전 세션의 탭 ID 재사용 금지
3. 기존 탭은 사용자가 명시적으로 요청할 때만 재사용
4. 탭 에러 시 tabs_context_mcp로 새 ID 획득
```

### JavaScript Alert 경고

```
IMPORTANT: JavaScript alert, confirm, prompt, 브라우저 모달 다이얼로그를 트리거하지 말 것.
이런 다이얼로그는 모든 브라우저 이벤트를 차단하여 확장이 후속 명령을 수신할 수 없게 됨.

대안:
1. 다이얼로그 트리거 가능한 버튼/링크 클릭 회피
2. 불가피한 경우 사용자에게 경고
3. console.log + read_console_messages로 디버깅
```

### 에러 처리

```
다음 상황 시 중단하고 사용자에게 안내:
- 예상치 못한 복잡성 / 무관한 탐색
- 2-3회 시도 후 도구 호출 실패
- 브라우저 확장 무응답
- 페이지 요소 미반응
- 페이지 로딩 타임아웃
```

### GIF 녹화

```
반드시:
- 액션 전후에 추가 프레임 캡처 (부드러운 재생)
- 의미 있는 파일명 (예: "login_process.gif")
```

---

## 7. UI 컴포넌트

### 7.1 /chrome 커맨드

```
/chrome → ClaudeInChromeMenu 다이얼로그
  │
  ├── "Install Chrome extension" (미설치 시)
  │   └── https://claude.ai/chrome 열기
  │
  ├── "Manage permissions" (설치 완료 시)
  │   └── 사이트별 권한 관리 페이지 열기
  │
  ├── "Toggle default" (기본 활성화 전환)
  │   └── globalConfig에 저장
  │
  └── "Reconnect" (연결 끊김 시)
      └── 확장 설치 확인 + 재연결 URL 열기
```

**가용성**: `claude-ai` 모드에서만 (인터랙티브 세션)

### 7.2 온보딩

```
ClaudeInChromeOnboarding (최초 사용 시 1회)
  │
  ├── 기능 설명
  │   ├── 웹사이트 네비게이션
  │   ├── 폼 입력
  │   ├── 스크린샷 캡처
  │   ├── GIF 녹화
  │   └── 콘솔 로그 / 네트워크 요청 디버깅
  │
  ├── 미설치 시 → 설치 안내 (https://claude.ai/chrome)
  ├── 설치 완료 시 → 권한 안내 (https://clau.de/chrome/permissions)
  └── Enter로 닫기 → hasCompletedClaudeInChromeOnboarding = true
```

### 7.3 Hook: 알림

`useChromeExtensionNotification()`:

| 알림 | 조건 | 메시지 |
| --- | --- | --- |
| 구독 필요 | claude.ai 미구독 | "Claude in Chrome requires a claude.ai subscription" |
| 미설치 | 확장 미감지 | "Chrome extension not detected · https://claude.ai/chrome" |
| 기본 활성 | 자동 활성화 시 | "Claude in Chrome enabled · /chrome" |

### 7.4 Hook: 프롬프트 수신

`usePromptsFromClaudeInChrome()`:

```
Chrome 확장에서 프롬프트 수신
  │
  ├── JSON-RPC 2.0 메시지 파싱
  │   └── { method: "notifications/message",
  │         params: { prompt, image?, tabId? } }
  │
  ├── 탭 ID 추적 확인 (세션 내 사용 탭만)
  │
  ├── 콘텐츠 블록 변환
  │   ├── 텍스트만: [{ type: 'text', text: prompt }]
  │   └── 텍스트+이미지: [{ type: 'image', ... }, { type: 'text', ... }]
  │
  ├── 대기 알림으로 enqueue
  │
  └── 권한 모드 동기화
      ├── bypassPermissions → skip_all_permission_checks
      └── 기타 → ask
```

---

## 8. WebBrowserTool (Bagel)

Claude in Chrome과 별도로, **WebBrowserTool** (코드네임: Bagel)이 feature flag 뒤에 존재한다. Anthropic 내부 실험 기능으로, Chrome 없이 동작하는 **네이티브 내장 브라우저** 도구다.

### 개요

| 항목 | 내용 |
| --- | --- |
| **코드네임** | Bagel |
| **Feature Flag** | `WEB_BROWSER_TOOL` (빌드 타임, `feature()`) |
| **소스 위치** | `src/tools/WebBrowserTool/` (빌드에서 제외, 소스 미포함) |
| **활성 조건** | `feature('WEB_BROWSER_TOOL')` + Bun 런타임 + `Bun.WebView` 존재 |
| **상태** | 실험 (일반 사용자 비공개) |

### 아키텍처: Claude in Chrome vs Bagel

```
Claude in Chrome (공개 Beta)
  사용자의 Chrome 브라우저
    → Chrome 확장 프로그램
    → Native Messaging (stdin/stdout)
    → Unix Socket / Named Pipe
    → MCP 서버
    → Claude Code CLI
  (외부 프로세스 간 통신, MCP 도구 17개)

WebBrowserTool / Bagel (내부 실험)
  Bun 내장 WebView (프로세스 내)
    → 자체 도구 인터페이스
    → Claude Code CLI
  (프로세스 내 네이티브 브라우저, 자체 도구)
```

### 코드 참조

```typescript
// tools.ts — 조건부 import
const WebBrowserTool = feature('WEB_BROWSER_TOOL')
  ? require('./tools/WebBrowserTool/WebBrowserTool.js').WebBrowserTool
  : null

// tools 배열에 조건부 포함
...(WebBrowserTool ? [WebBrowserTool] : []),
```

```typescript
// REPL.tsx — 패널 UI (조건부 렌더링)
const WebBrowserPanelModule = feature('WEB_BROWSER_TOOL')
  ? require('../tools/WebBrowserTool/WebBrowserPanel.js')
  : null

// 렌더링
{feature('WEB_BROWSER_TOOL') ? WebBrowserPanelModule &&
  <WebBrowserPanelModule.WebBrowserPanel /> : null}
```

```typescript
// AppStateStore.ts — 3개 상태 필드
bagelActive?: boolean          // 활성 상태
bagelUrl?: string              // 현재 URL (Footer pill에 표시)
bagelPanelVisible?: boolean    // 패널 가시성 토글
```

```typescript
// main.tsx — Claude in Chrome과 공존 시 힌트 변경
const hint = feature('WEB_BROWSER_TOOL') && typeof Bun !== 'undefined'
  && 'WebView' in Bun
  ? CLAUDE_IN_CHROME_SKILL_HINT_WITH_WEBBROWSER  // 둘 다 사용 가능
  : CLAUDE_IN_CHROME_SKILL_HINT                   // Chrome만
```

### UI 구성

```
Footer 좌측 pill 순서:
  [Tasks] → [Tmux] → [Bagel] → [Teams] → [Bridge] → [Companion]
                        ↑
                  bagelActive 시 표시
                  bagelUrl로 현재 URL 표시

REPL 화면:
  ├── TungstenLiveMonitor (tmux 패널)
  └── WebBrowserPanel (Bagel 패널) ← feature flag 뒤
```

### 부가 기능

```typescript
// attachments.ts — 콘솔 로그 attachment 타입
type: 'bagel_console'  // WebBrowserTool 전용 콘솔 로그
```

### 상세 비교

| 관심사 | Claude in Chrome | WebBrowserTool (Bagel) |
| --- | --- | --- |
| **방식** | Chrome 확장 + MCP 프로토콜 | Bun 내장 WebView |
| **브라우저** | 사용자의 Chrome (7개 Chromium 지원) | Bun.WebView (자체 내장) |
| **외부 의존** | Chrome + 확장 설치 필요 | Bun WebView API만 필요 |
| **통신** | Native Messaging → Socket → MCP | 프로세스 내 직접 호출 |
| **도구 접두사** | `mcp__claude-in-chrome__*` | (자체 도구) |
| **도구 수** | 17개 | (소스 미포함으로 미확인) |
| **UI** | /chrome 커맨드, 온보딩, 알림 Hook | Footer pill + 패널 |
| **상태** | Beta (공개) | 실험 (feature flag 비공개) |
| **활성화** | claude.ai 구독 + 확장 설치 | `WEB_BROWSER_TOOL` + Bun.WebView |
| **콘솔** | `read_console_messages` MCP 도구 | `bagel_console` attachment 타입 |
| **사용자 데이터** | 사용자의 쿠키/세션 사용 가능 | 격리된 WebView (쿠키 없음) |

> **핵심 차이**: Claude in Chrome은 사용자의 실제 브라우저를 제어하므로 로그인 상태/쿠키를 활용할 수 있지만 확장 설치가 필요하다. Bagel은 자체 내장 브라우저로 외부 의존 없이 동작하지만, 사용자의 브라우저 세션에 접근할 수 없다.

---

## 9. 파일별 역할 요약

### 핵심 유틸리티 (utils/claudeInChrome/)

| 파일 | 역할 |
| --- | --- |
| `mcpServer.ts` | MCP 서버 메인: Chrome 브릿지 연결, 권한 모드, 분석 |
| `chromeNativeHost.ts` | Native Messaging 호스트: stdin/stdout 바이너리 프로토콜 + 소켓 서버 |
| `setup.ts` | 설치 오케스트레이션: manifest 설치, 래퍼 스크립트, 레지스트리 |
| `setupPortable.ts` | 확장 설치 감지 (포터블, VS Code에서도 사용 가능) |
| `prompt.ts` | 브라우저 자동화 프롬프트: 탭 규칙, alert 경고, GIF 가이드 |
| `common.ts` | 크로스플랫폼: 7개 브라우저 경로, 소켓 관리, 탭 ID 추적 |
| `toolRendering.tsx` | 17개 도구 UI 커스터마이즈: 요약, View Tab 링크 |

### 커맨드/스킬/Hook/컴포넌트

| 파일 | 역할 |
| --- | --- |
| `commands/chrome/chrome.tsx` | /chrome 메뉴 UI (설치, 권한, 재연결, 토글) |
| `commands/chrome/index.ts` | 커맨드 메타데이터 (claude-ai 전용) |
| `skills/bundled/claudeInChrome.ts` | 번들 스킬 등록 (17개 도구, 프롬프트) |
| `hooks/useChromeExtensionNotification.tsx` | 확장 상태 알림 (미설치, 구독 필요) |
| `hooks/usePromptsFromClaudeInChrome.tsx` | 확장 → CLI 프롬프트/이미지 수신 + 권한 동기화 |
| `components/ClaudeInChromeOnboarding.tsx` | 최초 사용 온보딩 다이얼로그 |
