#!/usr/bin/env python3
"""Validate the waterfall CODING_HANDOFF markdown template.

Scope: P0 structural checks for templates/waterfall/04-구현/CODING_HANDOFF.md.
The checker is read-only: it does not write files, stage changes, or call git.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_TARGET = Path("templates/waterfall/04-구현/CODING_HANDOFF.md")

REQUIRED_SECTIONS = [
    "구현 목표",
    "요구사항 ID",
    "관련 문서 링크",
    "영향 범위",
    "금지 변경",
    "계약",
    "구현 단계",
    "필수 테스트",
    "보안 체크",
    "검증 명령",
    "완료 기준",
    "롤백 메모",
]

OPTIONAL_TAIL_SECTIONS = [
    "하지 않을 것 (선택)",
    "성능 기준 (선택)",
    "마이그레이션 메모 (선택)",
    "리뷰 포인트 (선택)",
]

CONTRACT_ITEMS = [
    "입력",
    "출력",
    "에러",
    "부작용",
    "호환성",
    "idempotency/concurrency",
    "실패 동작",
]

SECURITY_ITEMS = [
    "인증/인가",
    "입력 검증",
    "injection",
    "비밀정보",
    "PII/logging",
    "파일/네트워크 경계",
    "의존성 취약점",
    "abuse case",
]

ROLLBACK_ITEMS = [
    "revert 방법",
    "dependency pin rollback",
    "migration rollback",
    "data recovery",
]

DISCRETIONARY_PHRASES = ["가능하면", "적절히", "필요시", "나중에"]
DISCRETIONARY_WORDS = ["관련", "등"]

REQUIRED_TABLE_COLUMNS = {
    "영향 범위": ["대상", "변경 목적", "허용 작업", "영향 없어야 하는 범위"],
    "금지 변경": ["금지 대상", "금지 이유", "위반 시 처리"],
    "계약": ["계약 항목", "계약 내용", "변경 가능 여부", "검증 방법", "해당 없음 사유"],
    "필수 테스트": ["구분", "요구사항 ID 또는 계약 항목", "테스트 파일 또는 케이스", "확인할 동작", "통과 기준"],
    "보안 체크": ["보안 항목", "점검 결과", "근거", "해당 없음 사유"],
    "검증 명령": ["실행 명령", "기대 결과", "통과 기준"],
    "롤백 메모": ["롤백 항목", "절차", "검증 명령", "통과 기준", "해당 없음 사유"],
}

STOP_CONDITION_SECTIONS = ["요구사항 ID", "영향 범위", "금지 변경", "계약"]
STOP_CONDITION_TERMS = ["중단", "추측"]

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
PLACEHOLDER_RE = re.compile(r"{{[^{}\n]+}}")
HTML_COMMENT_RE = re.compile(r"^<!--.*-->$")


class Section:
    def __init__(self, name: str, line_index: int, body: list[str]) -> None:
        self.name = name
        self.line_index = line_index
        self.body = body

    @property
    def body_text(self) -> str:
        return "\n".join(self.body)


def _is_section_heading(line: str) -> str | None:
    match = HEADING_RE.match(line)
    if not match:
        return None
    level, name = match.groups()
    if level != "##":
        return None
    return name.strip()


def parse_sections(text: str) -> list[Section]:
    lines = text.splitlines()
    starts: list[tuple[str, int]] = []
    for index, line in enumerate(lines):
        name = _is_section_heading(line)
        if name is not None:
            starts.append((name, index))

    sections: list[Section] = []
    for pos, (name, start) in enumerate(starts):
        end = starts[pos + 1][1] if pos + 1 < len(starts) else len(lines)
        sections.append(Section(name, start, lines[start + 1 : end]))
    return sections


def _table_header(section: Section) -> list[str] | None:
    for line in section.body:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells and any(cell and set(cell) != {"-"} for cell in cells):
            return cells
    return None


def _section_has_row_label(section: Section, label: str) -> bool:
    pattern = re.compile(rf"^\|\s*{re.escape(label)}\s*\|")
    return any(pattern.search(line.strip()) for line in section.body)


def _line_after_heading_comments(text: str, section: Section) -> int:
    lines = text.splitlines()
    count = 0
    index = section.line_index + 1
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            index += 1
            continue
        if HTML_COMMENT_RE.match(stripped):
            count += 1
            index += 1
            continue
        break
    return count


def _find_malformed_placeholder(text: str) -> list[str]:
    cleaned = PLACEHOLDER_RE.sub("", text)
    failures: list[str] = []
    if "{{" in cleaned or "}}" in cleaned:
        failures.append("P0 placeholder braces are malformed; use {{이름}} form only.")
    for token in ["TODO", "TBD", "FIXME", "PLACEHOLDER", "<TODO>"]:
        if token in text:
            failures.append(f"P0 forbidden placeholder token remains: {token}")
    return failures


def _forbidden_discretionary_phrases(text: str) -> list[str]:
    failures: list[str] = []
    for phrase in DISCRETIONARY_PHRASES:
        if phrase in text:
            failures.append(f"P0 discretionary phrase is forbidden: {phrase}")
    scan_text = "\n".join(
        line for line in text.splitlines() if _is_section_heading(line) is None
    )
    for word in DISCRETIONARY_WORDS:
        # Korean word boundary is unreliable; this catches independent table/list prose,
        # while avoiding words such as 멱등성 because there are no whitespace/punctuation boundaries.
        pattern = re.compile(rf"(?<![가-힣A-Za-z0-9]){re.escape(word)}(?![가-힣A-Za-z0-9])")
        if pattern.search(scan_text):
            failures.append(f"P0 discretionary standalone word is forbidden: {word}")
    return failures


def check_coding_handoff(text: str) -> list[str]:
    failures: list[str] = []
    sections = parse_sections(text)
    names = [section.name for section in sections]
    allowed_names = REQUIRED_SECTIONS + OPTIONAL_TAIL_SECTIONS

    for section in REQUIRED_SECTIONS:
        count = names.count(section)
        if count == 0:
            failures.append(f"P0 missing required section: {section}")
        elif count > 1:
            failures.append(f"P0 duplicate required section: {section}")

    required_names = [name for name in names if name in REQUIRED_SECTIONS]
    if required_names != REQUIRED_SECTIONS:
        failures.append(
            "P0 required sections must appear in order: " + " > ".join(REQUIRED_SECTIONS)
        )

    optional_names = [name for name in names if name in OPTIONAL_TAIL_SECTIONS]
    if optional_names != OPTIONAL_TAIL_SECTIONS:
        failures.append(
            "P0 optional sections must be final and ordered: " + " > ".join(OPTIONAL_TAIL_SECTIONS)
        )
    elif names[-len(OPTIONAL_TAIL_SECTIONS) :] != OPTIONAL_TAIL_SECTIONS:
        failures.append(
            "P0 optional sections must be final and ordered: " + " > ".join(OPTIONAL_TAIL_SECTIONS)
        )

    for name in names:
        if name not in allowed_names:
            failures.append(f"P0 unknown section heading: {name}")

    by_name = {section.name: section for section in sections}

    for section in sections:
        comment_count = _line_after_heading_comments(text, section)
        if comment_count < 1 or comment_count > 3:
            failures.append(
                f"P0 section must have 1-3 HTML guidance comments immediately below heading: {section.name}"
            )

    failures.extend(_find_malformed_placeholder(text))
    failures.extend(_forbidden_discretionary_phrases(text))

    if "추측" not in text:
        failures.append("P0 global no-guess rule is missing: 추측")
    for section_name in STOP_CONDITION_SECTIONS:
        section = by_name.get(section_name)
        if not section:
            continue
        body = section.body_text
        if "중단" not in body:
            failures.append(
                f"P0 stop condition term '중단' missing from section: {section_name}"
            )

    for section_name, columns in REQUIRED_TABLE_COLUMNS.items():
        section = by_name.get(section_name)
        if not section:
            continue
        header = _table_header(section)
        if not header:
            failures.append(f"P0 table header missing in section: {section_name}")
            continue
        for column in columns:
            if column not in header:
                failures.append(f"P0 table column missing in {section_name}: {column}")

    contract = by_name.get("계약")
    if contract:
        for item in CONTRACT_ITEMS:
            if not _section_has_row_label(contract, item):
                failures.append(f"P0 contract item missing: {item}")

    tests = by_name.get("필수 테스트")
    if tests:
        for item in ["요구사항", "계약"]:
            if not _section_has_row_label(tests, item):
                failures.append(f"P0 required test row missing: {item}")

    security = by_name.get("보안 체크")
    if security:
        for item in SECURITY_ITEMS:
            if not _section_has_row_label(security, item):
                failures.append(f"P0 security item missing: {item}")

    rollback = by_name.get("롤백 메모")
    if rollback:
        for item in ROLLBACK_ITEMS:
            if not _section_has_row_label(rollback, item):
                failures.append(f"P0 rollback item missing: {item}")

    return failures


def _replace_section_heading(text: str, old: str, new: str) -> str:
    return re.sub(rf"^##\s+{re.escape(old)}\s*$", f"## {new}", text, count=1, flags=re.MULTILINE)


def _remove_section(text: str, section_name: str) -> str:
    pattern = re.compile(
        rf"^##\s+{re.escape(section_name)}\s*$.*?(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    return pattern.sub("", text, count=1)


def _remove_security_row(text: str) -> str:
    return re.sub(r"^\|\s*abuse case\s*\|.*$\n?", "", text, count=1, flags=re.MULTILINE)


def _swap_sections(text: str, first: str, second: str) -> str:
    pattern = re.compile(r"^##\s+.+?\s*$.*?(?=^##\s+|\Z)", re.MULTILINE | re.DOTALL)
    match = pattern.search(text)
    if not match:
        return text
    blocks = pattern.findall(text)
    first_index = next((index for index, block in enumerate(blocks) if block.startswith(f"## {first}\n")), None)
    second_index = next((index for index, block in enumerate(blocks) if block.startswith(f"## {second}\n")), None)
    if first_index is None or second_index is None:
        return text
    blocks[first_index], blocks[second_index] = blocks[second_index], blocks[first_index]
    return text[: match.start()] + "".join(blocks)


def run_self_test(text: str) -> list[str]:
    failures: list[str] = []
    cases = [
        (
            "required section order",
            _swap_sections(text, "영향 범위", "금지 변경"),
            "P0 required sections must appear in order",
        ),
        (
            "forbidden discretionary phrase",
            text + "\n<!-- 가능하면 -->\n",
            "P0 discretionary phrase is forbidden: 가능하면",
        ),
        (
            "security item missing",
            _remove_security_row(text),
            "P0 security item missing: abuse case",
        ),
        (
            "missing required section",
            _remove_section(text, "요구사항 ID"),
            "P0 missing required section: 요구사항 ID",
        ),
    ]
    for label, mutated, expected in cases:
        messages = check_coding_handoff(mutated)
        if not any(expected in message for message in messages):
            failures.append(f"self-test failed for {label}: expected '{expected}'")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the CODING_HANDOFF markdown template.")
    parser.add_argument("target", nargs="?", default=str(DEFAULT_TARGET), help="Markdown file to validate")
    parser.add_argument("--self-test", action="store_true", help="Run in-memory negative mutation checks")
    args = parser.parse_args(argv)

    target = Path(args.target)
    if not target.exists():
        print(f"P0 target file does not exist: {target}", file=sys.stderr)
        return 1

    text = target.read_text(encoding="utf-8")
    failures = check_coding_handoff(text)
    if args.self_test:
        failures.extend(run_self_test(text))

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print(f"CODING_HANDOFF P0 check passed: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
