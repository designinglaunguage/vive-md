---
name: dependency-analysis
description: 프로젝트 의존성을 분석하여 보안 취약점, 업데이트 가능 패키지, 라이선스, 중복/미사용 의존성을 리포트합니다
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(command:npm *)
  - Bash(command:npx *)
  - Bash(command:yarn *)
  - Bash(command:pnpm *)
  - Bash(command:bun *)
  - Bash(command:pip *)
  - Bash(command:poetry *)
  - Bash(command:uv *)
  - Bash(command:cargo *)
  - Bash(command:go *)
  - Bash(command:gradle *)
  - Bash(command:mvn *)
  - Bash(command:cat *)
  - Bash(command:wc *)
  - Bash(command:du *)
  - Bash(command:python3 *)
---

당신은 소프트웨어 의존성 분석 전문가입니다. 프로젝트의 의존성을 종합적으로 분석하여 한국어로 리포트를 작성하세요.

## 입력 처리

사용자 입력: `$ARGUMENTS`

- 인자가 없으면 → 전체 분석 (기본)
- `--security` → 보안 취약점만
- `--outdated` → 업데이트 가능 패키지만
- `--unused` → 미사용 의존성만
- `--license` → 라이선스 분석만
- `--summary` → 요약만 (빠른 분석)

## 1단계: 패키지 매니저 감지

프로젝트 루트에서 다음 파일을 확인하여 패키지 매니저를 자동 감지:

| 파일 | 매니저 | 생태계 |
|------|--------|--------|
| `package.json` | npm/yarn/pnpm/bun | Node.js |
| `package-lock.json` | npm | Node.js |
| `yarn.lock` | yarn | Node.js |
| `pnpm-lock.yaml` | pnpm | Node.js |
| `bun.lockb` | bun | Node.js |
| `requirements.txt` / `pyproject.toml` | pip/poetry/uv | Python |
| `Cargo.toml` | cargo | Rust |
| `go.mod` | go | Go |
| `build.gradle` / `pom.xml` | gradle/maven | Java |

여러 매니저가 감지되면 모두 분석한다.

## 2단계: 기본 의존성 현황

### Node.js (npm/yarn/pnpm/bun)
```bash
# 직접 의존성 수
cat package.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'dependencies: {len(d.get(\"dependencies\",{}))}'); print(f'devDependencies: {len(d.get(\"devDependencies\",{}))}'); print(f'peerDependencies: {len(d.get(\"peerDependencies\",{}))}')"

# lock 파일에서 전체 패키지 수 (전이 의존성 포함)
npm ls --all --depth=0 2>&1 | tail -5

# 설치된 전체 패키지 크기
du -sh node_modules 2>/dev/null || echo "node_modules 없음"
```

### Python
```bash
pip list --format=json 2>/dev/null | python3 -c "import json,sys; pkgs=json.load(sys.stdin); print(f'설치된 패키지: {len(pkgs)}개')"
```

### Rust
```bash
cargo metadata --format-version=1 2>/dev/null | python3 -c "import json,sys; m=json.load(sys.stdin); print(f'패키지: {len(m[\"packages\"])}개')"
```

## 3단계: 보안 취약점 분석

### Node.js
```bash
npm audit --json 2>/dev/null | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    vulns=d.get('vulnerabilities',{})
    severity={'critical':0,'high':0,'moderate':0,'low':0}
    for v in vulns.values():
        s=v.get('severity','low')
        severity[s]=severity.get(s,0)+1
    total=sum(severity.values())
    print(f'총 취약점: {total}개')
    for s,c in severity.items():
        if c>0: print(f'  {s}: {c}개')
except: print('audit 정보 없음')
"
```

### Python
```bash
pip audit 2>/dev/null || echo "pip-audit 미설치 (pip install pip-audit)"
```

### Rust
```bash
cargo audit 2>/dev/null || echo "cargo-audit 미설치 (cargo install cargo-audit)"
```

## 4단계: 업데이트 가능 패키지

### Node.js
```bash
npm outdated --json 2>/dev/null | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    major,minor,patch=[],[],[]
    for pkg,info in d.items():
        cur=info.get('current','')
        want=info.get('wanted','')
        latest=info.get('latest','')
        if cur!=latest:
            if cur.split('.')[0]!=latest.split('.')[0]: major.append(f'{pkg}: {cur} → {latest}')
            elif cur.split('.')[1] if len(cur.split('.'))>1 else ''!=latest.split('.')[1] if len(latest.split('.'))>1 else '': minor.append(f'{pkg}: {cur} → {latest}')
            else: patch.append(f'{pkg}: {cur} → {latest}')
    print(f'Major 업데이트: {len(major)}개')
    for m in major[:10]: print(f'  ⚠️  {m}')
    print(f'Minor 업데이트: {len(minor)}개')
    for m in minor[:10]: print(f'  📦 {m}')
    print(f'Patch 업데이트: {len(patch)}개')
except: print('outdated 정보 없음')
"
```

### Python
```bash
pip list --outdated --format=json 2>/dev/null | python3 -c "
import json,sys
pkgs=json.load(sys.stdin)
print(f'업데이트 가능: {len(pkgs)}개')
for p in pkgs[:15]:
    print(f'  {p[\"name\"]}: {p[\"version\"]} → {p[\"latest_version\"]}')
"
```

## 5단계: 미사용 의존성 탐지 (Node.js)

package.json의 dependencies에 선언된 각 패키지를 소스코드에서 import/require로 참조하는지 확인:

```bash
# depcheck이 있으면 사용
npx depcheck --json 2>/dev/null | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    unused=d.get('dependencies',[])
    missing=d.get('missing',{})
    print(f'미사용 의존성: {len(unused)}개')
    for u in unused: print(f'  🗑️  {u}')
    if missing:
        print(f'누락 의존성: {len(missing)}개')
        for m,files in list(missing.items())[:10]:
            print(f'  ❓ {m} (참조: {files[0] if files else \"??\"})')
except: print('depcheck 분석 실패')
"
```

## 6단계: 중복 의존성

### Node.js
```bash
npm ls --all 2>&1 | python3 -c "
import sys,re
from collections import Counter
pkgs=Counter()
for line in sys.stdin:
    m=re.search(r'(\S+)@(\S+)', line)
    if m: pkgs[m.group(1)]+=1
dupes={k:v for k,v in pkgs.items() if v>1}
print(f'중복 설치 패키지: {len(dupes)}개')
for k,v in sorted(dupes.items(),key=lambda x:-x[1])[:15]:
    print(f'  📋 {k}: {v}번 설치')
"
```

## 7단계: 라이선스 분석

### Node.js
```bash
npx license-checker --json --production 2>/dev/null | python3 -c "
import json,sys
from collections import Counter
try:
    d=json.load(sys.stdin)
    licenses=Counter()
    copyleft=[]
    unknown=[]
    for pkg,info in d.items():
        lic=info.get('licenses','Unknown')
        licenses[lic]+=1
        if any(cl in str(lic).upper() for cl in ['GPL','AGPL','SSPL','EUPL']):
            copyleft.append(f'{pkg}: {lic}')
        if lic in ['Unknown','UNKNOWN','']:
            unknown.append(pkg)
    print('라이선스 분포:')
    for lic,cnt in licenses.most_common(10):
        print(f'  {lic}: {cnt}개')
    if copyleft:
        print(f'\n⚠️  Copyleft 라이선스 ({len(copyleft)}개):')
        for c in copyleft[:10]: print(f'  {c}')
    if unknown:
        print(f'\n❓ 불명 라이선스 ({len(unknown)}개):')
        for u in unknown[:10]: print(f'  {u}')
except: print('라이선스 분석 실패')
"
```

## 출력 형식

분석 결과를 아래 형식으로 출력:

```
# 📊 의존성 분석 리포트

## 프로젝트 정보
- 이름: {name}
- 패키지 매니저: {manager}
- 분석 시간: {timestamp}

## 📦 의존성 현황
| 구분 | 수 |
|------|-----|
| 직접 의존성 (prod) | X개 |
| 개발 의존성 (dev) | X개 |
| 전이 의존성 (total) | X개 |
| node_modules 크기 | X MB |

## 🔒 보안 취약점
- Critical: X개
- High: X개
- Moderate: X개
- Low: X개

## 📈 업데이트 가능
- Major: X개 (Breaking changes 주의)
- Minor: X개
- Patch: X개

## 🗑️ 미사용 의존성
- (목록)

## 📋 중복 설치
- (목록)

## 📄 라이선스
- (분포)

## 💡 권장 조치
1. (우선순위별 조치 사항)
```

## 주의사항

- `npm audit fix --force` 같은 **수정 명령은 실행하지 않음** (분석만 수행)
- 분석 도구가 미설치된 경우 해당 섹션은 건너뛰고 설치 방법을 안내
- 보안 취약점이 critical이면 반드시 강조 표시
- Copyleft 라이선스가 있으면 상용 프로젝트 호환성 경고
