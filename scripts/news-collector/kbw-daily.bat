@echo off
chcp 65001 >nul

:: =====================================================
:: KBW 일일 뉴스 수집 가이드 스크립트 (Windows)
:: 사용자가 직접 Kimi에 프롬프트를 입력하여 뉴스 브리프 생성
:: =====================================================

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%..\.."
set "NEWS_DIR=%PROJECT_DIR%\docs\news\kbw-daily"

:: 날짜 설정
for /f "tokens=1-3 delims=/" %%a in ("%date%") do (
    set "YEAR=%%a"
    set "MONTH=%%b"
    set "DAY=%%c"
)
set "DATE=%YEAR:~2,2%%MONTH%%DAY%"
set "FULL_DATE=%YEAR%-%MONTH%-%DAY%"

:: 버전 번호 계산
set "VERSION=01"
for /f "tokens=*" %%a in ('dir /b "%NEWS_DIR%\%YEAR%\%MONTH%\[KBW일간]*%DATE%*.md" 2^>nul ^| find /c /v ""') do (
    set /a COUNT=%%a+1
    if !COUNT! lss 10 (
        set "VERSION=0!COUNT!"
    ) else (
        set "VERSION=!COUNT!"
    )
)

set "FILENAME=[KBW일간]_%DATE%-%VERSION%.md"
set "OUTPUT_PATH=%NEWS_DIR%\%YEAR%\%MONTH%\%FILENAME%"

echo ==========================================
echo   KBW 일일 뉴스 수집 가이드
echo ==========================================
echo.
echo 날짜: %FULL_DATE%
echo 파일명: %FILENAME%
echo 저장 경로: %OUTPUT_PATH%
echo.

:: 디렉토리 생성
if not exist "%NEWS_DIR%\%YEAR%\%MONTH%" (
    mkdir "%NEWS_DIR%\%YEAR%\%MONTH%"
    echo [OK] 디렉토리 생성 완료
    echo.
)

echo ==========================================
echo    아래 프롬프트를 복사해서 Kimi에 입력하세요
echo ==========================================
echo.
echo 실행 방법:
echo 1. 명령 프롬프트에서 'kimi' 입력
echo 2. 아래 프롬프트 전체를 복사/붙여넣기
echo 3. Kimi가 뉴스를 수집하고 브리프를 작성
echo 4. 생성된 내용을 복사해서 저장
echo.
echo ------------------------------------------
echo.

type con << 'EOF'
KBW 일일 뉴스 브리프를 작성해주세요.

## 출력 형식
파일 시작에 반드시 다음 헤더 포함:
※ 출처에 표기된 언론사를 클릭하시면 원문을 조회할 수 있습니다.

## 섹션별 건수
- [정책/시장 동향]: 2~3건
- [전방산업 동향]: 3~4건  
- [업체/기술 동향]: 3~4건
- 총 8~11건

## 각 뉴스 항목 작성 규칙 (반드시 준수)

### 1. 제목
- 반드시 `□ `로 시작
- 한국어로 간결하게

### 2. 본문
- 3~5문장으로 핵심 요약
- 중요 수치/데이터 포함

### 3. 데이터
- 수치는 `• `로 bullet point
- YoY, MoM 등 비교 수치 명시
- 통화 단위 명확히

### 4. 출처 (반드시)
- `☞ 출처: ` 형식
- 언론사명 + 날짜 (YYYY/MM/DD)
- 원문 링크는 Markdown: [언론사](URL)

## 검색 대상
- 중국: 有驾, 36氪, 盖世汽车
- 미국: Reuters, Bloomberg, Electrek
- 한국: 전자신문, 머니투데이, 모터그래프, 디일렉
- 일본: 日経クロステック, Response.jp, MarkLines

## 작성 예시

□ 캐나다, 2035년까지 전기차 100%% 계획 철회
캐나다 마크 카니 총리는 5일 자동차 산업 개편 방안을 발표
2035년 신차 판매 100%% 전기차 의무화 계획을 폐기
2035년 75%%, 2040년 90%%를 새 목표치로 제시
• BEV 최대 5천캐나다달러, PHEV 최대 2500캐나다달러
• 보조금은 5년간 유지
☞ 출처: [electrive](https://www.electrive.com/...) 2026/2/6

## 주의사항
1. 모든 뉴스 반드시 출처 표기
2. 수치/데이터 정확히 인용
3. 각 지역(중국, 미국, 한국, 일본) 균형 맞추기
4. 최근 1~2일 내 뉴스 위주
5. KBW 형식(□, •, ☞) 반드시 준수

완성된 Markdown 문서 전체를 출력하세요.
EOF

echo.
echo ------------------------------------------
echo.
echo 생성된 내용을 아래 파일에 저장하세요:
echo   %OUTPUT_PATH%
echo.

:: 파일 열기 여부
set /p OPEN_FILE="파일을 지금 생성하고 메모장으로 열어보시겠습니까? (Y/N): "
if /i "%OPEN_FILE%"=="Y" (
    :: 빈 파일 생성
    type nul > "%OUTPUT_PATH%"
    start notepad "%OUTPUT_PATH%"
)

echo.
echo 완료!
echo.
pause
