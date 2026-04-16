#!/usr/bin/env python3
"""
AIB 일일 뉴스 수집기 v1.0
Kimi CLI를 subprocess로 호출하여 AI 뉴스 브리프를 자동 생성합니다.

사전 준비:
    1. Kimi CLI 설치: pip install kimi-cli 또는 https://moonshotai.github.io/kimi-cli/
    2. 로그인: kimi login

사용법:
    python ai-daily.py                  # 기본 실행 (일일 뉴스)
    python ai-daily.py --weekly         # 주간 브리프
    python ai-daily.py --prompt-only    # 프롬프트만 생성 (Kimi 호출 안 함)
    python ai-daily.py --date 260308    # 특정 날짜로 생성
"""

import os
import sys
import argparse
import configparser
import re
import subprocess
import shutil
from datetime import datetime
from pathlib import Path


# ── 경로 설정 ──────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent.parent  # scripts/ai-news-collector → 프로젝트 루트
OUTPUT_DIR = PROJECT_DIR / "docs" / "news"
NEWS_DIR = OUTPUT_DIR / "ai-daily"
WEEKLY_DIR = OUTPUT_DIR / "ai-weekly"
CONFIG_PATH = SCRIPT_DIR / "config.ini"
NOTES_DIR = Path.home() / "Documents" / "octo-notes" / "사업비즈니스화"

KIMI_CREDENTIALS = Path.home() / ".kimi" / "credentials" / "kimi-code.json"


# ── 설정 파일 로드 ────────────────────────────────────────
def load_config():
    """config.ini에서 설정을 읽어옵니다."""
    cfg = configparser.ConfigParser()
    if CONFIG_PATH.exists():
        cfg.read(str(CONFIG_PATH), encoding="utf-8")
    return cfg


# ── 색상 출력 ──────────────────────────────────────────────
class Color:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    NC = "\033[0m"

    @staticmethod
    def supports_color():
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def cprint(color, text):
    if Color.supports_color():
        print(f"{color}{text}{Color.NC}")
    else:
        print(text)


def status(icon, msg):
    color = {
        "OK": Color.GREEN, "ERROR": Color.RED,
        "WARNING": Color.YELLOW, "INFO": Color.BLUE,
    }.get(icon, Color.NC)
    cprint(color, f"[{icon}] {msg}")


# ── 사전 점검 ──────────────────────────────────────────────
def check_kimi_cli():
    """Kimi CLI 설치 및 로그인 상태를 확인합니다."""
    kimi_path = shutil.which("kimi")
    if not kimi_path:
        status("ERROR", "Kimi CLI가 설치되어 있지 않습니다.")
        print()
        print("  설치 방법:")
        print("    pip install kimi-cli")
        print("    또는: https://moonshotai.github.io/kimi-cli/")
        return False

    status("OK", f"Kimi CLI 확인됨: {kimi_path}")

    if not KIMI_CREDENTIALS.exists():
        status("ERROR", "Kimi CLI에 로그인되어 있지 않습니다.")
        print("  로그인: kimi login")
        return False

    status("OK", "로그인 상태 확인됨")
    return True


# ── 파일명 및 경로 생성 ───────────────────────────────────
def get_output_info(date_str=None, weekly=False):
    """출력 파일 경로와 이름을 결정합니다."""
    now = datetime.now()

    if date_str:
        year = int("20" + date_str[:2])
        month = int(date_str[2:4])
        day = int(date_str[4:6])
        now = datetime(year, month, day)

    ymd = now.strftime("%y%m%d")
    year_full = now.strftime("%Y")
    month_str = now.strftime("%m")
    full_date = now.strftime("%Y-%m-%d")

    if weekly:
        base_dir = WEEKLY_DIR / year_full / month_str
        prefix = "[주간브리프]AIB"
    else:
        base_dir = NEWS_DIR / year_full / month_str
        prefix = "[AIB일간]"

    base_dir.mkdir(parents=True, exist_ok=True)

    version = 1
    existing = list(base_dir.glob(f"{prefix}*{ymd}*.md"))
    if existing:
        version = len(existing) + 1

    filename = f"{prefix}_{ymd}-{version:02d}.md"
    output_path = base_dir / filename

    return {
        "filename": filename,
        "output_path": output_path,
        "base_dir": base_dir,
        "full_date": full_date,
        "ymd": ymd,
        "version": version,
    }


# ── 프롬프트 생성 ─────────────────────────────────────────
def build_prompt(full_date, output_path, weekly=False):
    """Kimi CLI에 전달할 프롬프트를 생성합니다.
    config.ini 설정을 읽어 검색 대상, 키워드, 건수를 반영합니다."""

    cfg = load_config()

    if weekly:
        mode = "주간브리프"
        total = cfg.get(mode, "총건수", fallback="12~18건")
        period = cfg.get(mode, "수집범위", fallback="최근 1주일")
        sc_policy = cfg.get(mode, "AI정책시장", fallback="3~5건")
        sc_biz = cfg.get(mode, "기업서비스", fallback="4~6건")
        sc_tech = cfg.get(mode, "연구기술", fallback="4~6건")
    else:
        mode = "일일뉴스"
        total = cfg.get(mode, "총건수", fallback="8~11건")
        period = cfg.get(mode, "수집범위", fallback="최근 1~2일")
        sc_policy = cfg.get(mode, "AI정책시장", fallback="2~3건")
        sc_biz = cfg.get(mode, "기업서비스", fallback="3~4건")
        sc_tech = cfg.get(mode, "연구기술", fallback="3~4건")

    section_counts = f"AI 정책/시장 {sc_policy}, 기업/서비스 {sc_biz}, 연구/기술 {sc_tech}"

    # 검색 사이트/키워드
    us_sites = cfg.get("미국사이트", "사이트", fallback="The Verge(theverge.com), TechCrunch(techcrunch.com), VentureBeat(venturebeat.com), Ars Technica(arstechnica.com), MIT Technology Review(technologyreview.com)")
    us_kw = cfg.get("미국사이트", "키워드", fallback="AI, artificial intelligence, LLM, machine learning, GPT, Claude")
    cn_sites = cfg.get("중국사이트", "사이트", fallback="36氪(36kr.com), 机器之心(jiqizhixin.com), 量子位(qbitai.com)")
    cn_kw = cfg.get("중국사이트", "키워드", fallback="人工智能, 大模型, AI芯片, 机器学习")
    kr_sites = cfg.get("한국사이트", "사이트", fallback="전자신문(etnews.com), AI타임스(aitimes.com), 디지털데일리(ddaily.co.kr), ZDNet Korea(zdnet.co.kr)")
    kr_kw = cfg.get("한국사이트", "키워드", fallback="인공지능, AI, 생성AI, LLM, 거대언어모델")
    eu_sites = cfg.get("유럽일본사이트", "사이트", fallback="Reuters(reuters.com), Bloomberg(bloomberg.com), 日経クロステック(xtech.nikkei.com)")
    eu_kw = cfg.get("유럽일본사이트", "키워드", fallback="artificial intelligence, generative AI, 人工知能")

    # 지역 균형
    bal_us = cfg.get("지역균형", "미국", fallback="3~4건")
    bal_cn = cfg.get("지역균형", "중국", fallback="2~3건")
    bal_kr = cfg.get("지역균형", "한국", fallback="2~3건")
    bal_eu = cfg.get("지역균형", "유럽일본", fallback="1~2건")

    # 섹션 분류 기준
    sec_policy_inc = cfg.get("AI정책시장동향", "포함", fallback="AI 규제/정책, 시장 전망/보고서, 투자/펀딩, AI 윤리/안전, 국가 AI 전략")
    sec_policy_exc = cfg.get("AI정책시장동향", "제외", fallback="개별 기업 제품 출시")
    sec_biz_inc = cfg.get("기업서비스동향", "포함", fallback="AI 제품/서비스 출시, 기업 AI 전략, M&A/파트너십, AI 스타트업, 플랫폼 업데이트")
    sec_biz_exc = cfg.get("기업서비스동향", "제외", fallback="순수 연구 논문")
    sec_tech_inc = cfg.get("연구기술동향", "포함", fallback="AI 모델/아키텍처, 벤치마크 결과, 오픈소스 모델, AI 칩/하드웨어, 새로운 기법/알고리즘")
    sec_tech_exc = cfg.get("연구기술동향", "제외", fallback="정부 정책")

    prompt = f"""당신은 글로벌 인공지능(AI) 산업 전문 저널리스트입니다.
AIB(AI Brief) 형식에 맞춰 AI/LLM/ML 뉴스를 수집하고 한국어로 브리핑합니다.

## 작업 순서

1단계: 아래 검색 대상 사이트에서 {period} 내 최신 AI/LLM/생성AI/머신러닝 뉴스를 {total} 검색합니다.
2단계: 각 뉴스의 원문 페이지를 방문하여 실제 내용을 읽습니다.
3단계: 읽은 원문 내용만을 기반으로 아래 출력 형식에 맞게 3개 섹션으로 분류하여 정리합니다.
4단계: 정리된 결과를 다음 경로에 Markdown 파일로 저장합니다.

파일 경로: {output_path}
오늘 날짜: {full_date}

## 검색 대상 사이트

미국: {us_sites} → "{us_kw}"
중국: {cn_sites} → "{cn_kw}"
한국: {kr_sites} → "{kr_kw}"
유럽/일본: {eu_sites} → "{eu_kw}"

지역 균형: 미국 {bal_us}, 중국 {bal_cn}, 한국 {bal_kr}, 유럽/일본 {bal_eu}

## 문서 구조 (반드시 준수)

파일은 반드시 아래 3개 섹션 구조로 작성합니다.
각 섹션 건수: {section_counts}

### 섹션 분류 기준

| 섹션 | 포함 내용 | 제외 내용 |
|------|----------|----------|
| [AI 정책/시장 동향] | {sec_policy_inc} | {sec_policy_exc} |
| [기업/서비스 동향] | {sec_biz_inc} | {sec_biz_exc} |
| [연구/기술 동향] | {sec_tech_inc} | {sec_tech_exc} |

## 출력 형식 (반드시 준수)

```
※ 출처에 표기된 언론사를 클릭하시면 원문을 조회할 수 있습니다.

[AI 정책/시장 동향]

□ 한국어 제목 (명사형)
내용 요약 3~5문장 (평문, 서술어는 명사형 통일)
수치/데이터가 있으면 bullet point로 정리:
• 수치/데이터 1
• 수치/데이터 2
• 수치/데이터 3
☞ 출처: [언론사명](원문URL) YYYY/MM/DD

□ 다음 뉴스 제목
...
☞ 출처: [언론사명](원문URL) YYYY/MM/DD

[기업/서비스 동향]

□ 뉴스 제목
...
☞ 출처: [언론사명](원문URL) YYYY/MM/DD

[연구/기술 동향]

□ 뉴스 제목
...
☞ 출처: [언론사명](원문URL) YYYY/MM/DD
```

## 작성 규칙 (반드시 준수)

1. 파일 첫 줄: 반드시 "※ 출처에 표기된 언론사를 클릭하시면 원문을 조회할 수 있습니다." 로 시작
2. 3개 섹션: [AI 정책/시장 동향], [기업/서비스 동향], [연구/기술 동향] 순서로 작성
3. 제목: □ (사각형 기호 + 공백)로 시작, 한국어 명사형으로 간결하게
4. 본문: 3~5문장으로 핵심 요약 (평문으로, Markdown 굵게/기울임 사용 금지)
5. 수치/데이터: • (bullet dot)로 정리
6. 출처: 반드시 ☞ 출처: [언론사명](원문URL) YYYY/MM/DD 형식
7. 서술어는 모두 명사형 통일 (예: ~발표, ~공개, ~출시, ~달성 등)
8. 내용은 해당 기사에 있는 내용으로만 작성 (추측이나 외부 정보 추가 금지)
9. 한국 회사 외의 회사명은 영어로 작성 (예: OpenAI, Google, Anthropic, Meta)
10. 수치 정보가 있다면 정확히 기재
11. ## ### ** 등 Markdown 헤딩/굵게 기호 사용 금지 (□, •, ☞ 기호만 사용)

## 작성 예시

```
※ 출처에 표기된 언론사를 클릭하시면 원문을 조회할 수 있습니다.

[AI 정책/시장 동향]

□ EU, AI Act 시행 세부 가이드라인 발표
유럽연합(EU)이 AI Act의 구체적 시행 가이드라인을 공개
범용 AI 모델에 대한 투명성 의무와 고위험 AI 시스템 분류 기준을 확정
기업들은 2027년까지 단계적으로 규정을 준수해야 하며, 위반 시 최대 매출의 7% 과징금 부과
• AI Act 적용 대상: EU 내 서비스 제공 모든 AI 시스템
• 범용 AI 투명성 보고 의무: 2026년 8월부터 시행
• 고위험 AI 시스템 등록 의무: 2027년 2월부터 적용
☞ 출처: [Reuters](https://www.reuters.com/...) 2026/03/05

[기업/서비스 동향]

□ OpenAI, GPT-5 Turbo 모델 공개 및 API 제공 시작
OpenAI가 GPT-5 Turbo를 공개하며 API를 통한 개발자 접근을 시작
멀티모달 성능이 대폭 향상되었으며, 128K 컨텍스트 윈도우와 함수 호출 정확도 95% 달성
가격은 GPT-4 Turbo 대비 40% 인하, 초당 처리 토큰 수 3배 증가
• 컨텍스트 윈도우: 128K 토큰
• API 가격: 입력 $5/1M 토큰, 출력 $15/1M 토큰 (GPT-4 대비 -40%)
• MMLU 벤치마크: 92.1% (GPT-4 대비 +4.3%p)
☞ 출처: [TechCrunch](https://techcrunch.com/...) 2026/03/04

[연구/기술 동향]

□ Google DeepMind, 새로운 추론 아키텍처 'Gemini Ultra 2' 논문 공개
Google DeepMind가 Gemini Ultra 2의 핵심 아키텍처를 설명하는 기술 보고서를 발표
Mixture-of-Experts 구조를 확장한 새로운 라우팅 메커니즘으로 추론 효율성 2배 향상
수학 추론(MATH 벤치마크) 94.2%, 코딩(HumanEval) 91.5%로 최고 성능 기록
• 파라미터 수: 공개되지 않음 (MoE 활성 파라미터 기준 효율성 강조)
• 추론 비용: Gemini Ultra 1 대비 50% 절감
• 학습 데이터: 2026년 1월까지의 데이터 포함
☞ 출처: [VentureBeat](https://venturebeat.com/...) 2026/03/03
```

## 주의사항
1. {period} 내 뉴스 위주로 수집
2. 반드시 원문 페이지를 방문하여 내용을 읽은 후 요약
3. 파일 시작에 Markdown 코드블록(```)을 쓰지 마세요
4. 출처 URL은 실제 원문 링크
5. 위 출력 형식(□, •, ☞)을 정확히 따라서 작성. ## ### ** 등 Markdown 기호 사용 금지

위 규칙에 맞게 웹에서 뉴스를 검색하고, 원문을 읽은 뒤, 내용 기반으로 요약하여 파일을 생성해주세요."""

    return prompt


# ── Kimi CLI 실행 ─────────────────────────────────────────
def run_kimi_cli(prompt, work_dir):
    """Kimi CLI를 subprocess로 실행합니다."""

    cmd = [
        "kimi",
        "--yolo",
        "-p", prompt,
        "-w", str(work_dir),
        "--max-steps-per-turn", "50",
    ]

    status("INFO", "Kimi CLI 실행 중... (웹 검색 → 뉴스 수집 → 파일 생성)")
    print("  예상 소요 시간: 3~5분")
    print()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10분 타임아웃
            cwd=str(work_dir),
        )

        if result.stdout:
            for line in result.stdout.split("\n"):
                line_stripped = line.strip()
                if line_stripped and not line_stripped.startswith("╭") and not line_stripped.startswith("╰") and not line_stripped.startswith("│"):
                    print(f"  {line_stripped}")

        if result.returncode != 0:
            status("WARNING", f"Kimi CLI 종료 코드: {result.returncode}")
            if result.stderr:
                for line in result.stderr.split("\n")[-5:]:
                    if line.strip():
                        print(f"  {line.strip()}")

        return result.returncode

    except subprocess.TimeoutExpired:
        status("ERROR", "Kimi CLI 실행 시간 초과 (10분)")
        return -1
    except FileNotFoundError:
        status("ERROR", "kimi 명령을 찾을 수 없습니다. PATH를 확인하세요.")
        return -1
    except Exception as e:
        status("ERROR", f"Kimi CLI 실행 오류: {e}")
        return -1


# ── 출력 검증 ──────────────────────────────────────────────
def validate_output(filepath):
    """생성된 파일이 AIB 브리프 형식을 따르는지 검증합니다."""
    if not filepath.exists():
        return ["파일이 생성되지 않았습니다"], []

    content = filepath.read_text(encoding="utf-8")
    warnings = []
    errors = []

    if len(content) < 500:
        errors.append(f"파일이 너무 짧습니다 ({len(content)}자)")
        return errors, warnings

    if "※ 출처에 표기된 언론사를 클릭하시면" not in content:
        warnings.append("헤더 문구 누락: '※ 출처에 표기된 언론사를 클릭하시면...'")

    sections = {
        "[AI 정책/시장 동향]": False,
        "[기업/서비스 동향]": False,
        "[연구/기술 동향]": False,
    }
    for section in sections:
        if section in content:
            sections[section] = True
        else:
            warnings.append(f"섹션 누락: {section}")

    article_count = len(re.findall(r"^□\s+", content, re.MULTILINE))
    if article_count == 0:
        article_count = len(re.findall(r"^##\s+\d+\.", content, re.MULTILINE))
        if article_count == 0:
            article_count = len(re.findall(r"^\d+\.\s+", content, re.MULTILINE))
        if article_count > 0:
            warnings.append(f"제목 형식 불일치: □ 기호 대신 다른 형식 사용 중 ({article_count}건)")

    if article_count < 3:
        warnings.append(f"뉴스 건수가 적습니다: {article_count}건 (8건 이상 권장)")

    source_count = len(re.findall(r"☞\s*출처:", content))
    if source_count == 0:
        alt_source = len(re.findall(r"\*\*주요 출처\*\*", content))
        if alt_source > 0:
            warnings.append(f"출처 형식 불일치: ☞ 출처: 대신 **주요 출처** 사용 중 ({alt_source}건)")
    elif source_count < article_count:
        warnings.append(f"출처 누락: {article_count}건 중 {source_count}건만 있음")

    url_count = len(re.findall(r"https?://", content))
    if url_count < article_count:
        warnings.append(f"원문 링크 부족: {article_count}건 중 URL {url_count}개")

    return errors, warnings


# ── 뉴스별 개별 파일 분리 ─────────────────────────────────
def split_articles(filepath):
    """생성된 브리프를 뉴스별 개별 텍스트 파일로 분리합니다."""
    content = filepath.read_text(encoding="utf-8")
    ymd = filepath.stem.split("_")[-1].split("-")[0]

    articles_dir = filepath.parent / f"{ymd}-articles"
    articles_dir.mkdir(parents=True, exist_ok=True)

    section_map = {
        "[AI 정책/시장 동향]": "정책",
        "[기업/서비스 동향]": "기업",
        "[연구/기술 동향]": "기술",
    }

    current_section = ""
    current_section_full = ""
    articles = []
    current_article_lines = []
    prev_section = ""
    prev_section_full = ""

    for line in content.split("\n"):
        for sec_full, sec_short in section_map.items():
            if line.strip() == sec_full:
                current_section = sec_short
                current_section_full = sec_full
                break

        if line.startswith("□ "):
            if current_article_lines:
                articles.append((current_article_lines, prev_section, prev_section_full))
            current_article_lines = [line]
            prev_section = current_section
            prev_section_full = current_section_full
        elif current_article_lines:
            current_article_lines.append(line)

    if current_article_lines:
        articles.append((current_article_lines, prev_section, prev_section_full))

    created = []
    for i, (lines, sec, sec_full) in enumerate(articles, 1):
        title = lines[0].replace("□ ", "").strip()
        safe_title = re.sub(r'[\\/:*?"<>|]', '', title)
        safe_title = safe_title.replace(" ", "-").replace(",", "")[:40]

        filename = f"{i:02d}_{sec}_{safe_title}.txt"
        article_path = articles_dir / filename

        article_content = f"{sec_full}\n\n" + "\n".join(lines).rstrip() + "\n"
        article_path.write_text(article_content, encoding="utf-8")
        created.append(filename)

    return articles_dir, created


# ── 스레드 요약 생성 ──────────────────────────────────────
def generate_thread_summary(filepath, full_date):
    """원본 브리프에서 스레드 형식 요약을 생성합니다."""
    content = filepath.read_text(encoding="utf-8")

    section_map = {
        "[AI 정책/시장 동향]": "정책",
        "[기업/서비스 동향]": "기업",
        "[연구/기술 동향]": "기술",
    }

    # 기사 파싱
    current_section = ""
    articles = []
    current_lines = []

    for line in content.split("\n"):
        for sec_full, sec_short in section_map.items():
            if line.strip() == sec_full:
                current_section = sec_short
                break

        if line.startswith("□ "):
            if current_lines:
                articles.append((current_lines, prev_sec))
            current_lines = [line]
            prev_sec = current_section
        elif current_lines:
            current_lines.append(line)

    if current_lines:
        articles.append((current_lines, prev_sec))

    total = len(articles)
    thread_lines = [f"# AIB 일간 브리프 | {full_date} ({total}건)", "", "---"]

    for i, (lines, sec) in enumerate(articles, 1):
        title = lines[0].replace("□ ", "").strip()

        # 본문에서 핵심 1~2문장 추출
        body_parts = []
        bullets = []
        source = ""
        for line in lines[1:]:
            line_s = line.strip()
            if line_s.startswith("☞ 출처:"):
                # 출처에서 [언론사](URL) 추출
                m = re.search(r'\[([^\]]+)\]\(([^)]+)\)', line_s)
                if m:
                    source = f"([{m.group(1)}]({m.group(2)}))"
            elif line_s.startswith("• "):
                bullets.append(line_s[2:])
            elif line_s:
                body_parts.append(line_s)

        # 본문 압축: 첫 문장 + 핵심 불릿 2~3개
        summary = body_parts[0] if body_parts else title
        # 불릿에서 핵심 수치만 추출 (최대 3개)
        key_bullets = bullets[:3]
        bullet_str = ". ".join(key_bullets)
        if bullet_str:
            summary = f"{summary}. {bullet_str}."

        thread_lines.append("")
        thread_lines.append(f"**{i}/{total}** [{sec}] {title}. {summary} {source}")
        thread_lines.append("")
        thread_lines.append("---")

    # 스레드 파일 저장
    thread_path = filepath.with_name(filepath.stem + "_thread.md")
    thread_path.write_text("\n".join(thread_lines) + "\n", encoding="utf-8")
    return thread_path


# ── octo-notes에 저장 ─────────────────────────────────────
def save_to_notes(filepath, full_date, is_thread=False):
    """octo-notes/사업비즈니스화 폴더에 문서를 복사합니다."""
    import shutil as _shutil

    NOTES_DIR.mkdir(parents=True, exist_ok=True)

    label = "thread" if is_thread else "brief"
    dest_name = f"AIB-{label}_{full_date.replace('-', '')}.md"
    dest_path = NOTES_DIR / dest_name

    _shutil.copy2(str(filepath), str(dest_path))
    status("OK", f"노트 저장 완료: {dest_path}")
    return dest_path


# ── 메인 실행 ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="AIB 뉴스 수집기 v1.0 (Kimi CLI 자동화)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python ai-daily.py                   일일 뉴스 생성
  python ai-daily.py --weekly          주간 브리프 생성
  python ai-daily.py --prompt-only     프롬프트만 출력
  python ai-daily.py --date 260308     특정 날짜로 생성
  python ai-daily.py --auto            자동 모드 (cron 용)
        """,
    )
    parser.add_argument("--weekly", action="store_true", help="주간 브리프 생성")
    parser.add_argument("--date", type=str, help="날짜 (YYMMDD, 예: 260308)")
    parser.add_argument("--prompt-only", action="store_true", help="프롬프트만 출력")
    parser.add_argument("--no-git", action="store_true", help="Git 커밋 안 함")
    parser.add_argument("--auto", action="store_true", help="자동 모드")

    args = parser.parse_args()

    # ── 배너 ──
    print()
    cprint(Color.BLUE, "==========================================")
    cprint(Color.BLUE, "   AIB 뉴스 수집 시스템 v1.0")
    cprint(Color.BLUE, "==========================================")
    print()

    # ── 파일 경로 결정 ──
    info = get_output_info(args.date, args.weekly)
    print(f"  날짜:     {info['full_date']}")
    print(f"  파일명:   {info['filename']}")
    print(f"  출력경로: {info['output_path']}")
    print(f"  버전:     v{info['version']:02d}")
    print()

    # ── 프롬프트 생성 ──
    cprint(Color.BLUE, "[1/4] 프롬프트 생성...")
    prompt = build_prompt(info["full_date"], info["output_path"], args.weekly)
    status("OK", f"프롬프트 생성 완료 ({len(prompt)}자)")

    if args.prompt_only:
        print()
        cprint(Color.CYAN, "── 생성된 프롬프트 ────────────────────────")
        print(prompt)
        cprint(Color.CYAN, "──────────────────────────────────────────")
        print()
        print("이 프롬프트를 Kimi 웹(kimi.moonshot.cn)에 붙여넣으세요.")
        print(f"결과물 저장 경로: {info['output_path']}")
        return 0

    # ── Kimi CLI 확인 ──
    print()
    cprint(Color.BLUE, "[2/4] Kimi CLI 확인...")
    if not check_kimi_cli():
        print()
        print("  대안: --prompt-only 로 프롬프트를 생성하고 수동으로 실행")
        print(f"    python {__file__} --prompt-only")
        return 1

    # ── Kimi CLI 실행 ──
    print()
    cprint(Color.BLUE, "[3/4] Kimi CLI로 뉴스 수집 중...")

    returncode = run_kimi_cli(prompt, OUTPUT_DIR)

    # ── 결과 검증 ──
    print()
    cprint(Color.BLUE, "[4/4] 결과 검증...")

    if not info["output_path"].exists():
        status("ERROR", f"파일이 생성되지 않았습니다: {info['output_path']}")
        print()

        possible_files = list(info["base_dir"].glob(f"*{info['ymd']}*.md"))
        if possible_files:
            status("INFO", "다른 경로에서 파일 발견:")
            for f in possible_files:
                print(f"  {f}")
        else:
            print("  Kimi CLI가 파일을 생성하지 못했습니다.")
            print("  다시 시도하거나 --prompt-only로 수동 실행하세요.")
        return 1

    errors, warnings = validate_output(info["output_path"])

    if errors:
        for err in errors:
            status("ERROR", err)
        return 1

    for warn in warnings:
        status("WARNING", warn)

    # 통계
    content = info["output_path"].read_text(encoding="utf-8")
    article_count = len(re.findall(r"^□\s+", content, re.MULTILINE))
    if article_count == 0:
        article_count = len(re.findall(r"^##\s+\d+\.", content, re.MULTILINE))
    if article_count == 0:
        article_count = len(re.findall(r"^\d+\.\s+", content, re.MULTILINE))
    file_size = info["output_path"].stat().st_size
    line_count = content.count("\n") + 1

    status("OK", f"수집된 뉴스: {article_count}건")
    status("OK", "파일 저장 완료")

    print()
    cprint(Color.GREEN, "==========================================")
    cprint(Color.GREEN, "   완료!")
    cprint(Color.GREEN, "==========================================")
    print()
    print(f"  파일 경로: {info['output_path']}")
    print(f"  파일 크기: {file_size:,} bytes")
    print(f"  라인 수:   {line_count}")
    print(f"  뉴스 건수: {article_count}건")
    print()

    # ── 뉴스별 분리 ──
    articles_dir, created_files = split_articles(info["output_path"])
    status("OK", f"뉴스별 개별 파일: {len(created_files)}개 → {articles_dir}")

    # ── 스레드 요약 생성 ──
    thread_path = generate_thread_summary(info["output_path"], info["full_date"])
    status("OK", f"스레드 요약 생성: {thread_path.name}")

    # ── octo-notes 저장 ──
    save_to_notes(info["output_path"], info["full_date"], is_thread=False)
    save_to_notes(thread_path, info["full_date"], is_thread=True)

    # ── 미리보기 ──
    cprint(Color.BLUE, "[미리보기 - 처음 40줄]")
    print("─" * 50)
    lines = content.split("\n")
    for line in lines[:40]:
        print(line)
    if len(lines) > 40:
        print("─" * 50)
        print(f"... (이하 {len(lines) - 40}줄 생략)")
    print()

    # ── 파일 열기 ──
    if not args.auto:
        try:
            answer = input("파일을 열어보시겠습니까? (Y/N): ").strip().lower()
            if answer in ("y", "yes"):
                if sys.platform == "darwin":
                    subprocess.run(["open", str(info["output_path"])])
                elif sys.platform == "linux":
                    subprocess.run(["xdg-open", str(info["output_path"])])
                elif sys.platform == "win32":
                    os.startfile(str(info["output_path"]))
        except (EOFError, KeyboardInterrupt):
            print()

    # ── Git 커밋 ──
    if not args.no_git:
        print()
        do_commit = args.auto
        if not args.auto:
            try:
                answer = input("Git에 커밋하시겠습니까? (Y/N): ").strip().lower()
                do_commit = answer in ("y", "yes")
            except (EOFError, KeyboardInterrupt):
                print()

        if do_commit:
            try:
                subprocess.run(
                    ["git", "add", str(info["output_path"])],
                    cwd=str(SCRIPT_DIR), check=True, capture_output=True,
                )
                subprocess.run(
                    ["git", "commit", "-m", f"Add AIB news: {info['filename']}"],
                    cwd=str(SCRIPT_DIR), check=True, capture_output=True,
                )
                status("OK", "Git 커밋 완료")
            except subprocess.CalledProcessError:
                status("WARNING", "Git 커밋 실패")
            except FileNotFoundError:
                status("WARNING", "Git이 설치되어 있지 않습니다")

    print()
    cprint(Color.GREEN, "모든 작업이 완료되었습니다!")
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n작업이 취소되었습니다.")
        sys.exit(130)
