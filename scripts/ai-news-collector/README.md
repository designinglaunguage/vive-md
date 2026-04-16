# AIB 뉴스 수집기

글로벌 AI/LLM/생성AI 뉴스를 자동 수집하여 AIB(AI Brief) 형식 브리프를 생성합니다.

## 새 PC 설정

```bash
# Kimi CLI 설치
pip install kimi-cli

# 로그인
kimi login
```

## 뉴스 생성

```bash
# Mac/Linux
python ai-daily.py                     # 일일 뉴스 (8~11건)
python ai-daily.py --weekly            # 주간 브리프 (12~18건)
python ai-daily.py --prompt-only       # 프롬프트만 출력 (Kimi 웹 붙여넣기용)
python ai-daily.py --auto --no-git     # 자동 모드

# Windows
ai-daily.bat                           # 일일 뉴스 (더블클릭)
ai-daily.bat --weekly                  # 주간 브리프
ai-daily.bat --prompt-only             # 프롬프트만 출력
```

## 전체 옵션

| 옵션 | 설명 |
|------|------|
| (없음) | 일일 뉴스 8~11건 |
| `--weekly` | 주간 브리프 12~18건 |
| `--prompt-only` | 프롬프트만 출력 (Kimi 웹 붙여넣기용) |
| `--date 260308` | 특정 날짜로 생성 |
| `--auto` | 자동 모드 (대화형 프롬프트 없이) |
| `--no-git` | Git 커밋 안 함 |

## 출력 형식

```
※ 출처에 표기된 언론사를 클릭하시면 원문을 조회할 수 있습니다.

[AI 정책/시장 동향]

□ 한국어 제목
3~5문장 요약
• 수치/데이터
☞ 출처: [언론사](URL) YYYY/MM/DD

[기업/서비스 동향]
...

[연구/기술 동향]
...
```

## 출력 경로

```
docs/news/
├── ai-daily/YYYY/MM/
│   ├── [AIB일간]_YYMMDD-NN.md          전체 브리프
│   └── YYMMDD-articles/                 뉴스별 개별 파일
│       ├── 01_정책_제목.txt
│       ├── 02_기업_제목.txt
│       └── 03_기술_제목.txt
└── ai-weekly/YYYY/MM/
    └── [주간브리프]AIB_YYMMDD-NN.md
```

## 검색 대상 사이트

| 지역 | 사이트 |
|------|--------|
| 미국 | The Verge, TechCrunch, VentureBeat, Ars Technica, MIT Technology Review |
| 중국 | 36氪, 机器之心, 量子位 |
| 한국 | 전자신문, AI타임스, 디지털데일리, ZDNet Korea |
| 유럽/일본 | Reuters, Bloomberg, 日経クロステック |

설정 변경은 `config.ini`를 편집하세요.

## 파일 구조

```
scripts/ai-news-collector/
├── ai-daily.py        ← 메인 스크립트
├── ai-daily.sh        ← Mac/Linux 가이드 스크립트
├── ai-daily.bat       ← Windows 실행 (더블클릭)
├── config.ini         ← 설정 파일
├── README.md
└── output/            ← 생성된 뉴스 저장
    ├── ai-daily/      ← 일일 뉴스 + 개별 파일
    └── ai-weekly/     ← 주간 브리프
```

## 문제 해결

| 증상 | 해결 |
|------|------|
| Python 없음 | https://www.python.org/downloads/ 에서 설치 |
| kimi 명령 못 찾음 | `pip install kimi-cli` 후 터미널 재시작 |
| kimi login 실패 | 인터넷 연결 확인 후 재시도 |
| 뉴스 0건 생성 | `kimi login` 재실행 (토큰 만료) |
| Kimi 없이 사용 | `--prompt-only`로 프롬프트 복사 후 kimi.moonshot.cn 붙여넣기 |
