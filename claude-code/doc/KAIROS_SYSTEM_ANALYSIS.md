# KAIROS 시스템 상세 분석

> Claude Code의 미공개 상시 실행 에이전트 데몬 시스템에 대한 심층 분석 문서

---

## 목차

1. [개요](#1-개요)
2. [Feature Flag 체계](#2-feature-flag-체계)
3. [어시스턴트 모드](#3-어시스턴트-모드)
4. [KAIROS 전용 도구](#4-kairos-전용-도구)
5. [크론/스케줄링 시스템](#5-크론스케줄링-시스템)
6. [채널 알림 시스템](#6-채널-알림-시스템)
7. [메모리 시스템 (Daily Log + Dream)](#7-메모리-시스템-daily-log--dream)
8. [PROACTIVE와의 관계](#8-proactive와의-관계)
9. [상태 및 설정](#9-상태-및-설정)
10. [텔레메트리](#10-텔레메트리)
11. [파일별 역할 요약](#11-파일별-역할-요약)

---

## 1. 개요

KAIROS는 Claude Code를 **1회성 CLI 도구**에서 **항상 실행되는 자율 에이전트 데몬**으로 변환하는 미공개 시스템이다. "어시스턴트 모드"라고도 불리며, 사용자 입력 없이도 외부 이벤트에 반응하고, 크론 작업을 실행하며, 장기 메모리를 유지한다.

| 항목 | 내용 |
|---|---|
| **코드네임** | KAIROS |
| **활성화** | `--assistant` CLI 플래그 또는 `feature('KAIROS')` 빌드 게이트 |
| **상태** | 미공개 (feature flag 뒤, Anthropic 내부 테스트 중) |
| **핵심 변화** | 트랜잭션 → 데몬, 수동 → 자율, 휘발 → 영속 |

### 패러다임 전환

```
현재 Claude Code (트랜잭션):
  사용자 프롬프트 → 응답 → 종료
  ├── 상태 비유지 (세션 종료 시 소멸)
  ├── 사용자 주도 (입력 없으면 아무것도 안 함)
  └── 1회성 (매번 새로 시작)

KAIROS (상시 데몬):
  Claude가 계속 실행 → 외부 이벤트 수신 → 자율 작업 → 알림 전송
  ├── 영속 메모리 (일일 로그 + 야간 통합)
  ├── 자율 행동 (크론, 채널 반응, 웹훅)
  └── 세션 간 연속성 (durable cron, 메모리 이월)
```

---

## 2. Feature Flag 체계

KAIROS는 6개 이상의 feature flag로 서브시스템을 독립적으로 제어한다:

### 빌드 타임 게이트 (`feature()`)

| 플래그 | 역할 | 비고 |
|---|---|---|
| **`KAIROS`** | 마스터 게이트 (어시스턴트 모드 전체) | 빌드에서 코드 제거 |
| `KAIROS_DREAM` | Dream 스킬 (야간 메모리 통합) | KAIROS 하위 |
| `KAIROS_CHANNELS` | MCP 채널 알림 (Slack, Discord 등) | KAIROS 없이도 활성 가능 |
| `KAIROS_GITHUB_WEBHOOKS` | GitHub PR 웹훅 구독 | SubscribePRTool |
| `KAIROS_PUSH_NOTIFICATION` | 사용자 디바이스 알림 | KAIROS 없이도 활성 가능 |
| `KAIROS_BRIEF` | Brief 도구 (상태 체크포인트) | KAIROS 없이도 활성 가능 |
| `AGENT_TRIGGERS` | 크론 스케줄링 시스템 | KAIROS와 독립 출시 가능 |

### 런타임 게이트 (GrowthBook)

| 게이트 | 역할 |
|---|---|
| `tengu_kairos_cron` | 크론 기능 런타임 활성/비활성 |
| `tengu_kairos_cron_config` | 크론 설정 (CLI 세션 vs 데몬) |
| `tengu_harbor` | 채널 알림 런타임 게이트 |
| `tengu_onyx_plover` | Dream 통합 설정 (minHours, minSessions) |

### 의존성 계층

```
KAIROS (마스터)
├── AGENT_TRIGGERS (크론 + 스케줄러)
├── KAIROS_BRIEF (상태 체크포인트)
├── KAIROS_CHANNELS (인바운드 채널 푸시)
├── KAIROS_GITHUB_WEBHOOKS (PR 구독)
├── KAIROS_PUSH_NOTIFICATION (디바이스 알림)
└── KAIROS_DREAM (메모리 통합)

PROACTIVE (경량, KAIROS 없이도 동작)
├── SleepTool
└── 일부 텔레메트리/Brief 기능

AGENT_TRIGGERS (독립)
├── CronCreateTool
├── CronDeleteTool
├── CronListTool
└── /loop 스킬
```

---

## 3. 어시스턴트 모드

### 활성화 경로

```
CLI: claude --assistant
  │
  ▼
main.tsx
  ├── feature('KAIROS') 빌드 게이트
  ├── assistant/gate.ts → 설정 + GrowthBook + 신뢰 체크
  └── setKairosActive(true) → bootstrap/state.ts
      └── AppState.kairosEnabled = true
```

### 동작 변경

| 영역 | 일반 모드 | KAIROS 모드 |
|---|---|---|
| **수명** | 프롬프트 → 응답 → 종료 | 데몬으로 계속 실행 |
| **메모리** | MEMORY.md 갱신 | 추가 전용 일일 로그 + 야간 통합 |
| **이벤트** | 사용자 입력만 | 크론, 채널, 웹훅, 알림 |
| **크론** | 세션 내 only | Durable (디스크 영속, 재시작 후 복원) |
| **알림** | 없음 | 디바이스 푸시 알림 |
| **스케줄러** | 비활성 | useScheduledTasks Hook 마운트 |
| **어시스턴트 모드 자동 백그라운드** | 15초 예산 | 활성 (BashTool) |

---

## 4. KAIROS 전용 도구

### 도구 등록 (`tools.ts`)

```typescript
// KAIROS 마스터 게이트
const SendUserFileTool = feature('KAIROS')
  ? require('./tools/SendUserFileTool/SendUserFileTool.js').SendUserFileTool
  : null

// KAIROS 또는 개별 플래그
feature('KAIROS') || feature('KAIROS_PUSH_NOTIFICATION')
  ? PushNotificationTool : null

// GitHub 웹훅 전용
const SubscribePRTool = feature('KAIROS_GITHUB_WEBHOOKS')
  ? require('./tools/SubscribePRTool/SubscribePRTool.js').SubscribePRTool
  : null

// PROACTIVE 또는 KAIROS
feature('PROACTIVE') || feature('KAIROS')
  ? SleepTool : null
```

### 도구 목록

| 도구 | Feature Flag | 역할 |
|---|---|---|
| `SendUserFileTool` | `KAIROS` | 외부 시스템에 파일 전송 |
| `PushNotificationTool` | `KAIROS` \| `KAIROS_PUSH_NOTIFICATION` | 사용자 디바이스에 알림 발송 |
| `SubscribePRTool` | `KAIROS_GITHUB_WEBHOOKS` | GitHub PR 웹훅 구독/수신 |
| `SleepTool` | `PROACTIVE` \| `KAIROS` | 외부 이벤트 대기 후 재개 |
| `BriefTool` | `KAIROS` \| `KAIROS_BRIEF` | 긴 작업 중 사용자에게 상태 체크포인트 |
| `CronCreateTool` | `AGENT_TRIGGERS` | 크론 작업 생성 |
| `CronDeleteTool` | `AGENT_TRIGGERS` | 크론 작업 삭제 |
| `CronListTool` | `AGENT_TRIGGERS` | 크론 작업 목록 조회 |

> **참고**: SendUserFileTool, PushNotificationTool, SubscribePRTool의 소스 파일은 이 빌드에 포함되지 않음.

---

## 5. 크론/스케줄링 시스템

### 아키텍처

```
사용자: /loop 5m "PR 상태 체크"
  │
  ▼
/loop 스킬 (skills/bundled/loop.ts)
  ├── 크론 표현식 파싱 (5m → "*/5 * * * *")
  ├── CronCreateTool 호출 → 작업 생성
  └── 즉시 첫 실행
  │
  ▼
스케줄러 (hooks/useScheduledTasks.ts)
  ├── 매 틱마다 작업 파일/타이머 체크
  ├── 파이어 시 → 커맨드 큐에 'later' 우선순위로 enqueue
  └── 턴 사이에 drain (useCommandQueue)
  │
  ▼
쿼리 루프에서 실행
  └── 프롬프트 처리 → 도구 호출 → 결과
```

### 게이트 시스템

```
isKairosCronEnabled()
  │
  ├── 빌드 타임: feature('AGENT_TRIGGERS')
  ├── 런타임: tengu_kairos_cron GrowthBook (5분 갱신)
  ├── 로컬 오버라이드: CLAUDE_CODE_DISABLE_CRON 환경변수
  └── 기본값: true (GA 기능, KAIROS 없이도 동작)
```

### 작업 타입

| 타입 | 영속성 | 재시작 후 |
|---|---|---|
| **Session-only** | 메모리 | 소멸 |
| **Durable** | `.claude/scheduled_tasks.json` | 복원 |

### 작업 수명

```
생성 → 실행 (반복) → 만료/삭제
  │
  ├── 1회성 작업: 실행 후 자동 삭제
  ├── 반복 작업: DEFAULT_MAX_AGE_DAYS (31일) 후 자동 만료
  └── 수동 삭제: CronDeleteTool (작업 ID)
```

### KAIROS 모드 특수 처리

```
일반 모드:
  크론 파이어 → isLoading() 체크 → 쿼리 완료 후 실행

KAIROS 모드:
  크론 파이어 → assistantMode: true → isLoading() 무시
  → 스트리밍 중에도 enqueue 가능 (지연 최소화)
```

---

## 6. 채널 알림 시스템

### 개요

MCP 서버(Slack, Discord, SMS 등)가 Claude Code 세션에 **인바운드 메시지를 푸시**할 수 있는 시스템.

### 6단계 게이트 스택

```
1. 능력:  MCP 서버가 claude/channel 선언
2. 런타임: isChannelsEnabled() (KAIROS || KAIROS_CHANNELS)
3. 인증:  OAuth 필수 (API 키 사용자 차단)
4. 정책:  Teams/Enterprise는 channelsEnabled: true 필요
5. 세션:  --channels CLI 플래그에 서버 명시
6. 허용:  플러그인 마켓플레이스 검증 + 승인 목록
```

### 메시지 흐름

```
Slack MCP 서버
  │
  ├── notifications/claude/channel (JSON-RPC)
  │   └── { content: "새 메시지", metadata: {...} }
  │
  ▼
channelNotification.ts (핸들러)
  │
  ├── 6단계 게이트 통과
  ├── <channel source="slack-mcp"> 내용 </channel> XML 래핑
  └── 대화에 주입
  │
  ▼
Claude (메인 모델)
  │
  ├── 메시지 분석 + 응답 결정
  ├── 채널 도구로 응답 (Slack에 답장)
  ├── SendUserMessage (사용자에게 알림)
  └── 또는 둘 다
```

### 권한 선언

```
MCP 서버 capabilities:
  experimental: {
    'claude/channel': {}              // 채널 메시지 수신 가능
    'claude/channel/permission': {}   // 구조화 권한 응답 가능 (선택)
  }
```

---

## 7. 메모리 시스템 (Daily Log + Dream)

### 일반 모드 vs KAIROS 모드

```
일반 모드:                         KAIROS 모드:
┌──────────────────────┐          ┌──────────────────────────┐
│ MEMORY.md (인덱스)    │          │ logs/2026/03/            │
│ ├── user_role.md     │          │ ├── 2026-03-29.md        │
│ ├── feedback_*.md    │          │ ├── 2026-03-30.md        │
│ └── project_*.md     │          │ └── 2026-03-31.md        │
│                       │          │   ├── 09:00 PR 리뷰 시작  │
│ 매 턴마다 갱신 가능    │          │   ├── 10:30 테스트 통과   │
│ MEMORY.md 직접 수정    │          │   └── 14:00 배포 완료    │
└──────────────────────┘          │                           │
                                   │ 추가 전용 (수정 금지)     │
                                   └──────────────────────────┘
```

### 디렉토리 구조

```
~/.claude/memory/
├── MEMORY.md              (통합 인덱스, 항상 로드)
├── logs/
│   └── YYYY/MM/
│       └── YYYY-MM-DD.md  (추가 전용 일일 로그)
├── user_*.md              (사용자 프로필)
├── feedback_*.md          (피드백)
├── project_*.md           (프로젝트 정보)
└── reference_*.md         (참조)
```

### Dream 통합 (야간 자동)

```
autoDream 서비스 (services/autoDream/)
  │
  ├── 게이트: isAutoDreamEnabled()
  │   ├── feature('KAIROS_DREAM')
  │   ├── 시간 임계값: 24시간 경과
  │   └── 세션 임계값: 5회 이상
  │
  ├── 잠금: consolidationLock.ts (동시 실행 방지)
  │
  ├── 실행: 포크된 서브에이전트
  │   ├── 읽기 전용 Bash + 파일 쓰기 제한
  │   ├── 마지막 통합 이후 로그 읽기
  │   ├── 주제별 파일 생성/갱신
  │   └── MEMORY.md 재생성
  │
  └── 추적: DreamTask (백그라운드 태스크로 표시)
```

### 통합 프로세스

```
일일 로그 (원본)
  │
  ▼
Dream 서브에이전트
  ├── 로그 분석
  ├── 중복 제거
  ├── 주제 분류
  ├── 기존 메모리 파일과 병합
  └── MEMORY.md 인덱스 재생성
  │
  ▼
통합된 메모리 (결과)
  ├── user_role.md (갱신됨)
  ├── project_current.md (갱신됨)
  └── MEMORY.md (재생성됨)
```

---

## 8. PROACTIVE와의 관계

| 기능 | PROACTIVE | KAIROS |
|---|---|---|
| SleepTool | O | O |
| 크론 스케줄링 | X (AGENT_TRIGGERS) | O |
| 채널 수신 | X | O |
| GitHub 웹훅 | X | O |
| 디바이스 알림 | X | O |
| Durable 크론 | X | O |
| 메모리 통합 (Dream) | X | O |
| 세션 간 연속성 | X | O |
| 팀 조율 | X | O |

> **PROACTIVE**: SleepTool로 대기할 수 있지만, 세션 종료 시 상태 소멸. 경량.
> **KAIROS**: 전체 데몬 모드. Durable 크론, 팀 조율, 메모리 통합, 채널 푸시.

---

## 9. 상태 및 설정

### Bootstrap State

```typescript
// src/bootstrap/state.ts
let kairosActive: boolean = false

export function getKairosActive(): boolean
export function setKairosActive(value: boolean): void
```

### AppState

```typescript
// src/state/AppStateStore.ts
kairosEnabled: boolean  // 단일 진실 원천 (Single Source of Truth)
```

### 게이트 함수들

| 함수 | 용도 |
|---|---|
| `getKairosActive()` | Bootstrap 상태 체크 |
| `isKairosCronEnabled()` | 크론 빌드+런타임 통합 게이트 |
| `isDurableCronEnabled()` | Durable 크론 킬 스위치 |
| `isChannelsEnabled()` | 채널 알림 런타임 게이트 |
| `isAutoDreamEnabled()` | Dream 통합 게이트 (시간+세션 임계값) |

---

## 10. 텔레메트리

| 이벤트 | 설명 |
|---|---|
| `tengu_auto_dream_fired` | 메모리 통합 시작 |
| `tengu_auto_dream_completed` | 통합 성공 (캐시 메트릭 포함) |
| `tengu_auto_dream_failed` | 통합 실패/중단 |
| `tengu_memdir_loaded` | 메모리 디렉토리 로드 (파일 수) |
| `kairosActive: true` | 메타데이터에 어시스턴트 모드 활성 표시 |

---

## 11. 파일별 역할 요약

### 스킬 및 도구

| 파일 | 역할 |
|---|---|
| `skills/bundled/index.ts` | KAIROS dream 스킬 조건부 등록 |
| `skills/bundled/dream.ts` | /dream 스킬 (디스크 기반 메모리 통합) |
| `skills/bundled/loop.ts` | /loop 스킬 (크론 작업 생성 + 즉시 실행) |
| `tools.ts` | KAIROS 도구 조건부 등록 (6개+) |
| `tools/SendUserFileTool/` | 파일 전송 (소스 미포함) |
| `tools/PushNotificationTool/` | 디바이스 알림 (소스 미포함) |
| `tools/SubscribePRTool/` | PR 웹훅 구독 (소스 미포함) |
| `tools/SleepTool/` | 외부 이벤트 대기 |
| `tools/ScheduleCronTool/` | CronCreate/Delete/List + isKairosCronEnabled |

### 메모리 시스템

| 파일 | 역할 |
|---|---|
| `memdir/memdir.ts` | 일일 로그 프롬프트 (L319+), KAIROS 분기 (L427-432) |
| `memdir/paths.ts` | 일일 로그 경로 (`getAutoMemDailyLogPath`) |
| `services/autoDream/autoDream.ts` | 백그라운드 통합 실행기 |
| `services/autoDream/consolidationLock.ts` | 동시 실행 방지 잠금 |
| `services/autoDream/config.ts` | Dream 설정 (시간/세션 임계값) |

### 채널 및 이벤트

| 파일 | 역할 |
|---|---|
| `services/mcp/channelNotification.ts` | 채널 푸시 핸들러 + 6단계 게이트 |
| `hooks/useScheduledTasks.ts` | REPL에 크론 스케줄러 마운트 |
| `interactiveHelpers.tsx` | KAIROS/채널 인터랙티브 설정 (L241) |

### 상태 및 부트스트랩

| 파일 | 역할 |
|---|---|
| `bootstrap/state.ts` | kairosActive get/set |
| `state/AppStateStore.ts` | kairosEnabled boolean |
| `assistant/gate.ts` | 어시스턴트 모드 활성화 게이트 로직 |
| `assistant/index.ts` | 어시스턴트 모드 초기화 |
| `main.tsx` | --assistant 플래그, KAIROS 시작 오케스트레이션 |

### 분석

| 파일 | 역할 |
|---|---|
| `services/analytics/metadata.ts` | kairosActive 텔레메트리 |
| `services/analytics/datadog.ts` | kairosActive DataDog 전달 |
| `entrypoints/agentSdkTypes.ts` | tengu_kairos_cron_config 참조 |
