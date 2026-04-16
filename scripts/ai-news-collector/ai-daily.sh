#!/bin/bash

# =====================================================
# AIB 일일 뉴스 수집 가이드 스크립트 (Mac/Linux)
# 사용자가 직접 Kimi에 프롬프트를 입력하여 AI 뉴스 브리프 생성
# =====================================================

# 색상 설정
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 스크립트 경로 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
NEWS_DIR="$PROJECT_DIR/docs/news/ai-daily"


# 날짜 설정
DATE=$(date +%y%m%d)
YEAR=$(date +%Y)
MONTH=$(date +%m)
FULL_DATE=$(date +%Y-%m-%d)

# 버전 번호 계산
VERSION="01"
if [ -d "$NEWS_DIR/$YEAR/$MONTH" ]; then
    COUNT=$(ls -1 "$NEWS_DIR/$YEAR/$MONTH"/[AIB일간]*"$DATE"*.md 2>/dev/null | wc -l)
    if [ $COUNT -gt 0 ]; then
        VERSION=$(printf "%02d" $((COUNT + 1)))
    fi
fi

FILENAME="[AIB일간]_${DATE}-${VERSION}.md"
OUTPUT_PATH="$NEWS_DIR/$YEAR/$MONTH/$FILENAME"

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}   AIB 일일 뉴스 수집 가이드${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""
echo "날짜: $FULL_DATE"
echo "파일명: $FILENAME"
echo "저장 경로: $OUTPUT_PATH"
echo ""

# 디렉토리 생성
mkdir -p "$NEWS_DIR/$YEAR/$MONTH"
echo -e "${GREEN}[OK]${NC} 디렉토리 생성 완료"
echo ""

# 프롬프트 출력
echo -e "${CYAN}==========================================${NC}"
echo -e "${CYAN}   아래 프롬프트를 복사해서 Kimi에 입력하세요${NC}"
echo -e "${CYAN}==========================================${NC}"
echo ""
echo -e "${YELLOW}실행 방법:${NC}"
echo "1. 터미널에서 'kimi' 입력"
echo "2. 아래 프롬프트 전체를 복사/붙여넣기"
echo "3. Kimi가 뉴스를 수집하고 브리프를 작성"
echo "4. 생성된 내용을 복사해서 저장"
echo ""
echo -e "${CYAN}------------------------------------------${NC}"
echo ""

cat << 'EOF'
AIB 일일 뉴스 브리프를 작성해주세요.

## 출력 형식
파일 시작에 반드시 다음 헤더 포함:
※ 출처에 표기된 언론사를 클릭하시면 원문을 조회할 수 있습니다.

## 섹션별 건수
- [AI 정책/시장 동향]: 2~3건
- [기업/서비스 동향]: 3~4건
- [연구/기술 동향]: 3~4건
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
- 미국: The Verge, TechCrunch, VentureBeat, Ars Technica, MIT Technology Review
- 중국: 36氪, 机器之心, 量子位
- 한국: 전자신문, AI타임스, 디지털데일리, ZDNet Korea
- 유럽/일본: Reuters, Bloomberg, 日経クロステック

## 작성 예시

□ EU, AI Act 시행 세부 가이드라인 발표
유럽연합(EU)이 AI Act의 구체적 시행 가이드라인을 공개
범용 AI 모델에 대한 투명성 의무와 고위험 AI 시스템 분류 기준을 확정
• AI Act 적용 대상: EU 내 서비스 제공 모든 AI 시스템
• 범용 AI 투명성 보고 의무: 2026년 8월부터 시행
☞ 출처: [Reuters](https://www.reuters.com/...) 2026/03/05

## 주의사항
1. 모든 뉴스 반드시 출처 표기
2. 수치/데이터 정확히 인용
3. 각 지역(미국, 중국, 한국, 유럽/일본) 균형 맞추기
4. 최근 1~2일 내 뉴스 위주
5. AIB 형식(□, •, ☞) 반드시 준수

완성된 Markdown 문서 전체를 출력하세요.
EOF

echo ""
echo -e "${CYAN}------------------------------------------${NC}"
echo ""
echo -e "${GREEN}생성된 내용을 아래 파일에 저장하세요:${NC}"
echo "  $OUTPUT_PATH"
echo ""
echo "팁: 파일을 바로 열어서 붙여넣기:"
echo "  code '$OUTPUT_PATH'  (VS Code 사용 시)"
echo "  vim '$OUTPUT_PATH'   (Vim 사용 시)"
echo ""

# 파일 열기 여부
read -p "파일을 지금 생성하고 열어보시겠습니까? (Y/N): " OPEN_FILE
if [[ $OPEN_FILE =~ ^[Yy]$ ]]; then
    touch "$OUTPUT_PATH"

    if [[ "$OSTYPE" == "darwin"* ]]; then
        open "$OUTPUT_PATH"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open "$OUTPUT_PATH" 2>/dev/null || echo "파일 생성됨: $OUTPUT_PATH"
    fi
fi

echo ""
echo -e "${GREEN}완료!${NC}"
echo ""
