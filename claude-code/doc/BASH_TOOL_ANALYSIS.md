# BashTool 상세 분석

> Claude Code의 셸 명령 실행 도구에 대한 심층 분석 문서

---

## 목차

 1. [개요](#1-%EA%B0%9C%EC%9A%94)
 2. [아키텍처](#2-%EC%95%84%ED%82%A4%ED%85%8D%EC%B2%98)
 3. [입출력 스키마](#3-%EC%9E%85%EC%B6%9C%EB%A0%A5-%EC%8A%A4%ED%82%A4%EB%A7%88)
 4. [실행 흐름](#4-%EC%8B%A4%ED%96%89-%ED%9D%90%EB%A6%84)
 5. [보안 계층 (6단계)](#5-%EB%B3%B4%EC%95%88-%EA%B3%84%EC%B8%B5-6%EB%8B%A8%EA%B3%84)
    - [1단계: 입력 유효성 검증](#51-1%EB%8B%A8%EA%B3%84-%EC%9E%85%EB%A0%A5-%EC%9C%A0%ED%9A%A8%EC%84%B1-%EA%B2%80%EC%A6%9D-validateinput)
    - [2단계: 권한 확인](#52-2%EB%8B%A8%EA%B3%84-%EA%B6%8C%ED%95%9C-%ED%99%95%EC%9D%B8-checkpermissions)
    - [3단계: 보안 분석](#53-3%EB%8B%A8%EA%B3%84-%EB%B3%B4%EC%95%88-%EB%B6%84%EC%84%9D-bashsecurityts)
    - [4단계: 경로 검증](#54-4%EB%8B%A8%EA%B3%84-%EA%B2%BD%EB%A1%9C-%EA%B2%80%EC%A6%9D-pathvalidationts)
    - [5단계: 읽기 전용 검증](#55-5%EB%8B%A8%EA%B3%84-%EC%9D%BD%EA%B8%B0-%EC%A0%84%EC%9A%A9-%EA%B2%80%EC%A6%9D-readonlyvalidationts)
    - [6단계: 샌드박스](#56-6%EB%8B%A8%EA%B3%84-%EC%83%8C%EB%93%9C%EB%B0%95%EC%8A%A4-shouldusesandboxts)
 6. [명령어 의미 해석](#6-%EB%AA%85%EB%A0%B9%EC%96%B4-%EC%9D%98%EB%AF%B8-%ED%95%B4%EC%84%9D-commandsemanticsts)
 7. [sed 편집 시스템](#7-sed-%ED%8E%B8%EC%A7%91-%EC%8B%9C%EC%8A%A4%ED%85%9C)
 8. [백그라운드 실행](#8-%EB%B0%B1%EA%B7%B8%EB%9D%BC%EC%9A%B4%EB%93%9C-%EC%8B%A4%ED%96%89)
 9. [프롬프트 전략](#9-%ED%94%84%EB%A1%AC%ED%94%84%ED%8A%B8-%EC%A0%84%EB%9E%B5)
10. [UI 컴포넌트](#10-ui-%EC%BB%B4%ED%8F%AC%EB%84%8C%ED%8A%B8)
11. [파일별 역할 요약](#11-%ED%8C%8C%EC%9D%BC%EB%B3%84-%EC%97%AD%ED%95%A0-%EC%9A%94%EC%95%BD)

---

## 1. 개요

BashTool은 Claude Code에서 **셸 명령을 실행하는 핵심 도구**로, 18개 파일(총 수천 줄)에 걸친 다층 보안 시스템과 실행 인프라를 갖추고 있다.

| 항목 | 내용 |
| --- | --- |
| **도구 이름** | `Bash` |
| **파일 수** | 18개 |
| **최대 결과 크기** | 30,000 chars (인라인), 64MB (디스크 영속화) |
| **기본 타임아웃** | 120,000ms (2분) |
| **최대 타임아웃** | 600,000ms (10분) |
| **동시 실행** | 읽기 전용 명령만 안전 (`isConcurrencySafe`) |
| **샌드박스** | 파일시스템/네트워크 격리 (설정 기반) |

### 파일 구조

```
src/tools/BashTool/
├── BashTool.tsx                    # 메인 구현 (buildTool, call, 분류)
├── prompt.ts                       # 프롬프트 생성 (370줄)
├── toolName.ts                     # 도구 이름 상수 ('Bash')
├── bashPermissions.ts              # 권한 시스템 (분류기 규칙)
├── bashSecurity.ts                 # 보안 검증 (23가지 체크)
├── bashCommandHelpers.ts           # 복합 명령 파싱/세그먼트
├── commandSemantics.ts             # 종료 코드 의미 해석
├── shouldUseSandbox.ts             # 샌드박스 결정 로직
├── modeValidation.ts               # 모드별 검증 (acceptEdits 등)
├── pathValidation.ts               # 경로 검증 (위험 삭제 차단)
├── readOnlyValidation.ts           # 읽기 전용 검증 (플래그 허용목록)
├── sedEditParser.ts                # sed -i 파싱 (파일 편집 UI)
├── sedValidation.ts                # sed 보안 검증 (허용/차단)
├── destructiveCommandWarning.ts    # 파괴적 명령 경고 (정보용)
├── commentLabel.ts                 # 주석 라벨 추출
├── utils.ts                        # 출력 포맷, 이미지, 경로 유틸
├── UI.tsx                          # React UI (명령 표시, 백그라운드)
└── BashToolResultMessage.tsx       # React UI (결과 표시)
```

---

## 2. 아키텍처

```
사용자 프롬프트 → Claude 모델 → BashTool.call() 호출
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│ 보안 계층 (실행 전)                                       │
│                                                          │
│  1. validateInput()          입력 유효성 (sleep 패턴 등)  │
│  2. checkPermissions()       권한 확인 (규칙, 분류기)      │
│     ├── bashPermissions.ts   명령 분류, 권한 규칙 매칭     │
│     ├── bashSecurity.ts      23가지 보안 체크             │
│     ├── modeValidation.ts    모드별 자동 허용             │
│     ├── pathValidation.ts    경로 위험도 검사             │
│     ├── readOnlyValidation.ts  읽기 전용 플래그 허용목록   │
│     └── sedValidation.ts     sed 명령 보안 검증           │
│  3. shouldUseSandbox()       샌드박스 적용 결정            │
├─────────────────────────────────────────────────────────┤
│ 실행 계층                                                 │
│                                                          │
│  runShellCommand() → exec() (Shell.ts)                   │
│  ├── 샌드박스 모드: 파일시스템/네트워크 격리               │
│  ├── 포그라운드: 동기 실행 + 진행 표시                    │
│  └── 백그라운드: LocalShellTask 등록                      │
├─────────────────────────────────────────────────────────┤
│ 후처리 계층                                               │
│                                                          │
│  commandSemantics.ts     종료 코드 의미 해석               │
│  utils.ts                출력 포맷팅/잘라내기/이미지 처리   │
│  toolResultStorage.ts    대형 출력 디스크 영속화            │
│  UI.tsx / Result.tsx     React UI 렌더링                   │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 입출력 스키마

### Input

```typescript
{
  command: string                      // 실행할 명령 (필수)
  timeout?: number                     // 타임아웃 ms (최대 600,000)
  description?: string                 // 명령 설명 (사용자 표시용)
  run_in_background?: boolean          // 백그라운드 실행
  dangerouslyDisableSandbox?: boolean  // 샌드박스 비활성화 (위험)
  // _simulatedSedEdit: 내부 전용 (모델 스키마에서 제외)
}
```

> **보안**: `_simulatedSedEdit`는 모델 스키마에서 `omit()`으로 제거되어, 모델이 이 필드를 통해 권한 검사를 우회할 수 없다.

### Output

```typescript
{
  stdout: string                       // 표준 출력
  stderr: string                       // 표준 에러
  interrupted: boolean                 // 중단 여부
  isImage?: boolean                    // 이미지 출력 여부
  backgroundTaskId?: string            // 백그라운드 태스크 ID
  backgroundedByUser?: boolean         // 사용자 수동 백그라운드 여부
  assistantAutoBackgrounded?: boolean  // 어시스턴트 자동 백그라운드 여부
  dangerouslyDisableSandbox?: boolean  // 샌드박스 비활성화 플래그
  returnCodeInterpretation?: string    // 종료 코드 의미 해석
  noOutputExpected?: boolean           // 출력 없음이 정상인지
  persistedOutputPath?: string         // 대형 출력 영속화 경로
  persistedOutputSize?: number         // 영속화 출력 크기 (바이트)
  structuredContent?: any[]            // 구조화 콘텐츠 (이미지 등)
}
```

---

## 4. 실행 흐름

```
BashTool.call(input, toolUseContext, _, parentMessage, onProgress)
  │
  ├─ 1. Simulated Sed Edit 분기
  │   └── input._simulatedSedEdit 있으면
  │       └── applySedEdit() → 파일 직접 쓰기 (sed 실행 안 함)
  │
  ├─ 2. runShellCommand() (AsyncGenerator)
  │   ├── exec(command, { timeout, sandbox, ... })
  │   ├── 진행 이벤트 yield (2초 후부터)
  │   │   └── onProgress({ output, elapsedTimeSeconds, totalLines })
  │   ├── 어시스턴트 모드 자동 백그라운드 (15초 초과 시)
  │   └── 최종 결과 return (ExecResult)
  │
  ├─ 3. 후처리
  │   ├── trackGitOperations() — git 명령 추적
  │   ├── interpretCommandResult() — 종료 코드 의미 해석
  │   ├── resetCwdIfOutsideProject() — 프로젝트 밖 cd 복원
  │   ├── SandboxManager.annotateStderrWithSandboxFailures()
  │   └── ShellError throw (에러 시)
  │
  ├─ 4. 대형 출력 처리
  │   ├── 64MB 초과 시 truncate
  │   ├── tool-results/ 디렉토리에 link/copy
  │   └── persistedOutputPath 설정
  │
  ├─ 5. 이미지 출력 처리
  │   ├── isImageOutput() — data URI 감지
  │   └── resizeShellImageOutput() — 고DPI 다운샘플 (20MB 제한)
  │
  ├─ 6. 코드 인덱싱 감지
  │   └── detectCodeIndexingFromCommand() — 힌트 기록
  │
  └─ 7. 결과 반환
      └── { data: Out }
```

---

## 5. 보안 계층 (6단계)

### 5.1 1단계: 입력 유효성 검증 (validateInput)

```
validateInput(input)
  │
  └── MONITOR_TOOL feature + !run_in_background
      └── detectBlockedSleepPattern(command)
          ├── "sleep 5" (단독) → 차단
          ├── "sleep 5 && check" → 차단 (Monitor 사용 권장)
          ├── "sleep 0.5" → 허용 (rate limiting)
          └── "sleep 1" → 허용 (2초 미만)
```

### 5.2 2단계: 권한 확인 (checkPermissions)

`bashPermissions.ts`가 중심.

```
bashToolHasPermission(input, context)
  │
  ├── 1. 복합 명령 분할 (최대 50개 서브커맨드)
  │   └── MAX_SUBCOMMANDS_FOR_SECURITY_CHECK = 50
  │       └── 초과 시 이벤트 루프 고갈 방지
  │
  ├── 2. 모드 검증 (modeValidation.ts)
  │   ├── acceptEdits → mkdir, touch, rm, rmdir, mv, cp, sed 자동 허용
  │   ├── bypassPermissions → 통과
  │   └── dontAsk → 통과
  │
  ├── 3. 안전 명령 빠른 통과
  │   ├── 안전 환경변수 (HOME, PATH, SHELL 등)
  │   └── 접두사 매칭 (npm run, git commit 등)
  │
  ├── 4. 위험 패턴 차단
  │   ├── 베어 셸 접두사 (sh, bash, zsh, fish) → -c 코드 주입 방지
  │   └── 안전하지 않은 래퍼 차단
  │
  └── 5. 규칙 기반 분류기 결과
      └── allow / deny / ask
```

### 5.3 3단계: 보안 분석 (bashSecurity.ts)

23가지 보안 체크 (`BASH_SECURITY_CHECK_IDS`):

| ID | 체크 항목 | 설명 |
| --- | --- | --- |
| 1-5 | 인용/이스케이프 | 따옴표 추출, 이스케이프 시퀀스 검증 |
| 6-8 | 명령 치환 | `$()`, `${}`, 프로세스 치환 `<()` `>()` 차단 |
| 9-11 | Zsh 공격 | EQUALS 확장(`=cmd`), glob 한정자, `always` 블록 |
| 12-14 | 토큰 분석 | 변형 토큰, IFS 주입, 제어 문자 |
| 15-17 | Unicode | Unicode 공백 트릭, 방향 제어 문자 |
| 18-20 | 패턴 | 위험한 셸 패턴, 리다이렉션 남용 |
| 21-23 | 고급 | 복합 명령 구조, 함수 정의, eval 패턴 |

```
방어 심층 전략:
  ├── 안전한 리다이렉션 제거 (2>&1, >/dev/null, </dev/null)
  ├── 안전한 heredoc 패턴 제거
  └── 나머지에 대해 23가지 체크 수행
```

### 5.4 4단계: 경로 검증 (pathValidation.ts)

```
checkPathConstraints(input)
  │
  ├── 24개 경로 인식 명령 (PATH_EXTRACTORS)
  │   ├── cd, ls, find, mkdir, rm, rmdir, chmod, chown
  │   ├── mv, cp, ln, touch, cat, head, tail, less
  │   ├── grep, git, docker, jq, python, node
  │   └── tar, zip, unzip
  │
  ├── 명령별 경로 추출
  │   ├── cd: 모든 인자 join
  │   ├── rm: 플래그 필터링 후 경로
  │   ├── grep: 패턴 + 파일 경로
  │   └── POSIX `--` 구분자 처리
  │
  └── 위험 경로 차단 (checkDangerousRemovalPaths)
      ├── / (루트)
      ├── /etc, /usr, /usr/bin, /usr/local
      ├── /System, /System/Library (macOS)
      ├── /var, /boot, /proc, /sys (Linux)
      └── 항상 승인 필요
```

### 5.5 5단계: 읽기 전용 검증 (readOnlyValidation.ts)

읽기 전용 컨텍스트에서 명령이 파일을 쓰지 않는지 검증:

```
checkReadOnlyConstraints(input, hasCd)
  │
  ├── 명령별 허용 플래그 목록 (COMMAND_ALLOWLIST)
  │   ├── git: status, log, diff, show, branch, tag ... (읽기 전용만)
  │   ├── rg: --glob, --type, -n, -l, -c ... (검색만)
  │   ├── docker: ps, images, logs, inspect ... (조회만)
  │   ├── gh: pr view, issue list, api ... (조회만)
  │   ├── xargs: -I (대문자만), -0, -n, -P ... (실행 제외)
  │   └── fd: -t, -e, --max-depth ... (-x/-X 제외)
  │
  └── validateFlags() — 플래그별 인자 소비 정확 검증
```

### 5.6 6단계: 샌드박스 (shouldUseSandbox.ts)

```
shouldUseSandbox(input)
  │
  ├── 샌드박스 비활성 → false
  ├── dangerouslyDisableSandbox=true + 정책 허용 → false
  ├── 제외 명령 목록 매칭 → false
  │   ├── GrowthBook 동적 설정 (tengu_sandbox_disabled_commands)
  │   └── 사용자 settings.json (sandbox.excludedCommands)
  └── 기본값 → true (샌드박스 적용)

샌드박스 제한:
  ├── Filesystem:
  │   ├── read.denyOnly: [차단 경로 목록]
  │   └── write.allowOnly: [허용 경로 목록]
  └── Network:
      ├── allowedHosts: [허용 호스트]
      └── deniedHosts: [차단 호스트]
```

---

## 6. 명령어 의미 해석 (commandSemantics.ts)

모든 비제로 종료 코드가 에러는 아니다. `interpretCommandResult()`가 명령별 의미를 해석:

| 명령 | 코드 0 | 코드 1 | 코드 2+ |
| --- | --- | --- | --- |
| `grep` / `rg` | 매칭 있음 | 매칭 없음 (정상) | 에러 |
| `find` | 성공 | 일부 접근 불가 (부분 성공) | 에러 |
| `diff` | 파일 동일 | 파일 다름 (정상) | 에러 |
| `test` / `[` | 조건 참 | 조건 거짓 (정상) | 에러 |
| 기타 | 성공 | 에러 | 에러 |

```typescript
// 파이프라인에서 마지막 세그먼트의 명령을 추출하여 의미 해석
// 예: "cat file | grep pattern" → grep의 의미 적용
COMMAND_SEMANTICS: Map<string, CommandSemantic>
```

---

## 7. sed 편집 시스템

BashTool은 `sed -i` 명령을 특별 처리하여 **파일 편집 UI**로 렌더링한다:

### 파싱 (sedEditParser.ts)

```
parseSedEditCommand(command)
  │
  ├── isSedInPlaceEdit() — sed -i 명령인지 확인
  ├── macOS/Linux -i 플래그 차이 처리
  │   ├── macOS: sed -i '' 's/...' (빈 접미사 필수)
  │   └── Linux: sed -i 's/...' (접미사 선택)
  ├── 패턴/대체/플래그 추출
  └── SedEditInfo { filePath, pattern, replacement, flags, extendedRegex }
```

### 보안 검증 (sedValidation.ts)

```
sedCommandIsAllowedByAllowlist(command, allowFileWrites)
  │
  ├── 허용 패턴 (allowlist)
  │   ├── sed -n '1p;2,3p' (줄 출력, -n 필수)
  │   └── sed 's/pattern/replacement/flags' (치환)
  │
  ├── 차단 패턴 (denylist)
  │   ├── w/W: 파일 쓰기 (address]w filename)
  │   ├── e/E: 명령 실행 (address]e command)
  │   ├── /w, /e, /W: 치환 플래그로 쓰기/실행
  │   ├── 비ASCII 문자
  │   ├── Unicode 트릭
  │   └── 중괄호, 주석
  │
  └── acceptEdits 모드: -i 허용 (파일 쓰기) + 위험 연산 차단
```

### Simulated Sed Edit

사용자가 sed 편집을 승인하면, 실제 sed를 실행하지 않고 **미리 계산된 결과를 직접 파일에 쓴다**:

```
1. 권한 다이얼로그: sed 결과 미리보기 표시
2. 사용자 승인 → _simulatedSedEdit { filePath, newContent } 설정
3. BashTool.call() → applySedEdit()
   ├── 원본 파일 읽기
   ├── fileHistory 기록 (undo 지원)
   ├── 줄 끝 감지 + 인코딩 보존
   ├── newContent 직접 쓰기
   └── VS Code 알림
```

> **보안**: `_simulatedSedEdit`는 모델 스키마에서 제거되어, 모델이 이 필드를 직접 설정할 수 없다. 오직 권한 다이얼로그에서만 설정 가능.

---

## 8. 백그라운드 실행

### 3가지 백그라운드 모드

| 모드 | 트리거 | 설명 |
| --- | --- | --- |
| **명시적 백그라운드** | `run_in_background: true` | 모델이 요청 |
| **사용자 수동** | Ctrl+B | 사용자가 실행 중 백그라운드 전환 |
| **어시스턴트 자동** | 15초 초과 | 어시스턴트 모드에서 자동 전환 |

```
어시스턴트 자동 백그라운드:
  ASSISTANT_BLOCKING_BUDGET_MS = 15_000 (15초)

  메인 에이전트에서 15초 초과 시:
  → backgroundExistingForegroundTask()
  → "Command exceeded the assistant-mode blocking budget..."
```

### 자동 백그라운드 제외

```typescript
DISALLOWED_AUTO_BACKGROUND_COMMANDS = ['sleep']
// sleep은 항상 포그라운드 (명시적 백그라운드만 허용)
```

### 백그라운드 태스크 결과

```
backgroundInfo:
  ├── 자동: "Command exceeded...15s...moved to background ID: {id}"
  ├── 수동: "Command was manually backgrounded...ID: {id}"
  └── 명시적: "Command running in background...ID: {id}"

  모든 경우: "Output is being written to: {outputPath}"
```

---

## 9. 프롬프트 전략

`prompt.ts`의 `getSimplePrompt()`가 BashTool의 모델 프롬프트를 생성 (370줄):

### 도구 우선순위 가이드

```
IMPORTANT: 전용 도구가 있으면 Bash 대신 사용:
  - 파일 검색: Glob (find/ls 대신)
  - 콘텐츠 검색: Grep (grep/rg 대신)
  - 파일 읽기: Read (cat/head/tail 대신)
  - 파일 편집: Edit (sed/awk 대신)
  - 파일 쓰기: Write (echo >/cat <<EOF 대신)
  - 출력: 직접 텍스트 출력 (echo/printf 대신)
```

### Git 안전 프로토콜 (외부 사용자)

```
Git Safety Protocol:
  - NEVER update git config
  - NEVER run destructive commands (push --force, reset --hard, ...)
  - NEVER skip hooks (--no-verify, --no-gpg-sign)
  - NEVER force push to main/master
  - ALWAYS create NEW commits (amend 금지)
  - 커밋 메시지는 HEREDOC으로 전달
  - Co-Authored-By 속성 포함
```

### 샌드박스 섹션

샌드박스가 활성화되면 프롬프트에 제한 사항이 포함:

```
## Command sandbox
  - 기본: 샌드박스 내 실행
  - Filesystem: { read.denyOnly, write.allowOnly }
  - Network: { allowedHosts, deniedHosts }
  - $TMPDIR 사용 (/tmp 직접 사용 금지)
  - dangerouslyDisableSandbox: 샌드박스 실패 증거 있을 때만
```

### sleep 가이드

```
Avoid unnecessary sleep:
  - 즉시 실행 가능하면 sleep 하지 말 것
  - 긴 명령은 run_in_background 사용
  - 실패 시 sleep 루프 대신 원인 진단
  - 백그라운드 대기 시 알림 수신 (폴링 금지)
  - sleep ≥ 2초 차단 (MONITOR_TOOL 활성 시)
```

---

## 10. UI 컴포넌트

### 명령 표시 (UI.tsx)

| 함수 | 용도 | 설명 |
| --- | --- | --- |
| `renderToolUseMessage` | 명령 호출 | 최대 2줄/160자, sed→파일편집 변환 |
| `renderToolUseProgressMessage` | 진행 중 | 경과 시간, 줄 수, 바이트 |
| `renderToolUseQueuedMessage` | 대기 중 | 큐에서 실행 대기 |
| `BackgroundHint` | 백그라운드 힌트 | Ctrl+B로 백그라운드 전환 안내 |

### 결과 표시 (BashToolResultMessage.tsx)

```
BashToolResultMessage
  ├── extractSandboxViolations() — <sandbox_violations> 태그 추출
  ├── extractCwdResetWarning() — "Shell cwd was reset" 경고 분리
  ├── 출력 렌더링 (OutputLine 컴포넌트)
  └── 실행 시간 표시
```

### 명령 분류 (UI 접기용)

```typescript
// 검색 명령 → 접기 가능
BASH_SEARCH_COMMANDS = [find, grep, rg, ag, ack, locate, which, whereis]

// 읽기 명령 → 접기 가능
BASH_READ_COMMANDS = [cat, head, tail, less, more, wc, stat, file, strings,
                      jq, awk, cut, sort, uniq, tr]

// 디렉토리 목록 → 접기 가능
BASH_LIST_COMMANDS = [ls, tree, du]

// 의미 중립 → 접기 판단에 영향 없음
BASH_SEMANTIC_NEUTRAL_COMMANDS = [echo, printf, true, false, :]

// 무출력 정상 → "Done" 표시 (No output 대신)
BASH_SILENT_COMMANDS = [mv, cp, rm, mkdir, rmdir, chmod, chown, chgrp,
                        touch, ln, cd, export, unset, wait]
```

---

## 11. 파일별 역할 요약

| 파일 | 줄 수 | 역할 |
| --- | --- | --- |
| `BashTool.tsx` | \~900+ | 메인 구현: buildTool, call, 명령 분류, 출력 처리 |
| `prompt.ts` | 370 | 프롬프트 생성: 도구 우선순위, Git 프로토콜, 샌드박스 |
| `toolName.ts` | 3 | 도구 이름 상수 (`'Bash'`) |
| `bashPermissions.ts` | \~200+ | 권한 시스템: 분류기 규칙, 접두사 매칭, 50 서브커맨드 제한 |
| `bashSecurity.ts` | \~200+ | 23가지 보안 체크: 주입, 치환, Zsh, Unicode, 제어문자 |
| `bashCommandHelpers.ts` | \~150 | 복합 명령 세그먼트 파싱, cd+git 교차 보안 |
| `commandSemantics.ts` | \~100 | 종료 코드 의미 해석 (grep:1=정상, diff:1=정상) |
| `shouldUseSandbox.ts` | \~100 | 샌드박스 결정: 정책, 제외 목록, 고정점 알고리즘 |
| `modeValidation.ts` | \~80 | 모드별 검증: acceptEdits→파일시스템 명령 자동 허용 |
| `pathValidation.ts` | \~200+ | 24개 명령의 경로 추출, 위험 경로 차단 (/, /etc 등) |
| `readOnlyValidation.ts` | \~150+ | 읽기 전용 플래그 허용목록: git, rg, docker, gh, xargs, fd |
| `sedEditParser.ts` | \~100 | sed -i 파싱: 파일경로, 패턴, 대체, 플래그 추출 |
| `sedValidation.ts` | \~150 | sed 보안: 허용 패턴(줄출력, 치환) + 차단 패턴(w,e,W) |
| `destructiveCommandWarning.ts` | \~80 | 20개 파괴적 패턴 경고 (git reset, rm -rf, DROP TABLE 등) |
| `commentLabel.ts` | \~20 | 주석 라벨 추출 (`# comment` → "comment") |
| `utils.ts` | \~150 | 출력 포맷, 이미지 감지/리사이즈 (20MB), 경로 리셋 |
| `UI.tsx` | \~100 | React: 명령 표시 (2줄/160자), BackgroundHint |
| `BashToolResultMessage.tsx` | \~80 | React: 결과 표시, 샌드박스 위반 추출, cwd 리셋 경고 |
