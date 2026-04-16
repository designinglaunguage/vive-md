# Voice Mode 분석

> Claude Code의 음성 모드 활성화 시스템 분석

---

## 개요

| 항목 | 내용 |
| --- | --- |
| **디렉토리** | `src/voice/` |
| **파일 수** | 1개 (`voiceModeEnabled.ts`, 55줄) |
| **기능** | 음성 모드 활성화 조건 체크 |
| **Feature Flag** | `VOICE_MODE` (빌드 타임) + `tengu_amber_quartz_disabled` (GrowthBook 런타임) |
| **인증 요구** | Anthropic OAuth 필수 (API 키, Bedrock, Vertex, Foundry 불가) |

---

## 아키텍처

Voice Mode는 claude.ai의 `voice_stream` 엔드포인트를 사용하며, 활성화 여부만 이 파일에서 관리한다. 실제 음성 스트리밍 로직은 다른 모듈에 위치.

```
Voice Mode 활성화 체크
  │
  ├── 1. 빌드 타임 게이트
  │   └── feature('VOICE_MODE')
  │       ├── true → 내부/지원 빌드
  │       └── false → 외부 빌드 (코드 제거)
  │
  ├── 2. GrowthBook Kill Switch
  │   └── tengu_amber_quartz_disabled
  │       ├── false (기본) → 활성
  │       └── true → 긴급 비활성
  │
  └── 3. 인증 체크
      ├── isAnthropicAuthEnabled() → OAuth 프로바이더 확인
      └── getClaudeAIOAuthTokens() → 실제 토큰 존재 확인
```

---

## 3가지 체크 함수

### isVoiceGrowthBookEnabled()

```typescript
// GrowthBook kill switch 체크
// 기본값 false → 캐시 없어도 "활성"으로 판단 (신규 설치 즉시 사용 가능)
function isVoiceGrowthBookEnabled(): boolean {
  return feature('VOICE_MODE')
    ? !getFeatureValue_CACHED_MAY_BE_STALE('tengu_amber_quartz_disabled', false)
    : false
}
```

**용도**: UI 표시 여부 판단 (커맨드 등록, 설정 화면)

### hasVoiceAuth()

```typescript
// OAuth 인증 체크
function hasVoiceAuth(): boolean {
  if (!isAnthropicAuthEnabled()) return false  // 프로바이더 확인
  const tokens = getClaudeAIOAuthTokens()       // 토큰 존재 확인
  return Boolean(tokens?.accessToken)
}
```

**용도**: 인증 상태만 확인. `getClaudeAIOAuthTokens()`는 memoized (\~1시간 갱신, macOS에서 첫 호출 시 20-50ms)

### isVoiceModeEnabled()

```typescript
// 전체 런타임 체크 (인증 + kill switch)
function isVoiceModeEnabled(): boolean {
  return hasVoiceAuth() && isVoiceGrowthBookEnabled()
}
```

**용도**: `/voice` 커맨드, ConfigTool, VoiceModeNotice 등 실행 시점 체크

---

## 사용처

| 호출자 | 사용 함수 | 컨텍스트 |
| --- | --- | --- |
| `/voice` 커맨드 | `isVoiceModeEnabled()` | 커맨드 실행 시 |
| ConfigTool | `isVoiceModeEnabled()` | 설정 변경 시 |
| VoiceModeNotice | `isVoiceModeEnabled()` | 알림 표시 시 |
| React 렌더 | `useVoiceEnabled()` (별도 hook) | 렌더 주기 (memoized) |
| 커맨드 등록/UI | `isVoiceGrowthBookEnabled()` | 표시 여부만 |

---

## 제약 사항

- **Anthropic OAuth 전용**: API 키, Bedrock, Vertex, Foundry에서는 사용 불가
- **claude.ai 엔드포인트**: `voice_stream` 엔드포인트가 claude.ai에서만 제공
- **Kill Switch**: `tengu_amber_quartz_disabled` 플래그로 긴급 비활성화 가능
- **빌드 제거**: `feature('VOICE_MODE')` false인 빌드에서는 관련 문자열까지 제거