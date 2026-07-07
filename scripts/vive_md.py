#!/usr/bin/env python3
"""Small stdlib CLI helpers for vive-md."""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import os
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_SRS = Path("01-요구사항분석") / "요구사항명세서-SRS.md"
HANDOFF_DIR = Path("04-구현")
HANDOFF_TEMPLATE = Path("templates") / "waterfall" / "04-구현" / "CODING_HANDOFF.md"
REQ_ID_RE = re.compile(r"(?<![A-Z0-9-])([A-Z][A-Z0-9]*-\d{3,})(?![A-Z0-9-])")


class HandoffError(Exception):
    """Raised for user-facing handoff generation errors."""


@dataclass(frozen=True)
class RequirementQuote:
    req_id: str
    quote: str
    source: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise HandoffError(f"File not found: {path}") from exc


def relative_posix(path: Path, start: Path) -> str:
    return os.path.relpath(path.resolve(), start.resolve()).replace(os.sep, "/")


def strip_markdown(value: str) -> str:
    value = value.strip()
    value = re.sub(r"<!--.*?-->", "", value)
    value = value.replace("\\|", "|")
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = value.replace("\\[", "[").replace("\\]", "]")
    return re.sub(r"\s+", " ", value).strip()


def split_table_row(line: str) -> list[str]:
    raw = line.strip()
    if not raw.startswith("|") or not raw.endswith("|"):
        return []
    cells = []
    content = raw.strip("|")
    cell_start = 0
    for index, char in enumerate(content):
        if char != "|":
            continue
        backslashes = 0
        cursor = index - 1
        while cursor >= 0 and content[cursor] == "\\":
            backslashes += 1
            cursor -= 1
        if backslashes % 2 == 0:
            cells.append(strip_markdown(content[cell_start:index]))
            cell_start = index + 1
    cells.append(strip_markdown(content[cell_start:]))
    return cells


def is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def id_in_text(req_id: str, text: str) -> bool:
    return re.search(rf"(?<![A-Z0-9-]){re.escape(req_id)}(?![A-Z0-9-])", text) is not None


def line_number_at(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def section_bounds(lines: list[str], start_index: int) -> tuple[int, int]:
    heading = lines[start_index]
    level = len(heading) - len(heading.lstrip("#"))
    end = len(lines)
    for index in range(start_index + 1, len(lines)):
        line = lines[index]
        if line.startswith("#"):
            next_level = len(line) - len(line.lstrip("#"))
            if next_level <= level:
                end = index
                break
    return start_index, end


def quote_from_section(req_id: str, lines: list[str], start: int, end: int) -> str | None:
    heading = strip_markdown(lines[start].lstrip("#").strip())
    preferred_labels = ("설명", "요구사항", "기능명", "내용")
    fallback_row: str | None = None

    for line in lines[start + 1 : end]:
        cells = split_table_row(line)
        if not cells or is_separator_row(cells):
            continue
        if any(id_in_text(req_id, cell) for cell in cells):
            fallback_row = fallback_row or " | ".join(cells)
        if len(cells) >= 2 and any(label in cells[0] for label in preferred_labels):
            return f"{heading} — {cells[0]}: {cells[1]}"

    if fallback_row:
        return fallback_row

    for line in lines[start + 1 : end]:
        cleaned = strip_markdown(line)
        if cleaned and not cleaned.startswith("---"):
            return f"{heading} — {cleaned}"
    return heading or None


def extract_requirement_quote(srs_text: str, srs_rel: str, req_id: str) -> RequirementQuote:
    matches = list(re.finditer(rf"(?<![A-Z0-9-]){re.escape(req_id)}(?![A-Z0-9-])", srs_text))
    if not matches:
        raise HandoffError(f"Requirement ID not found in SRS: {req_id}")

    lines = srs_text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("#") and id_in_text(req_id, line):
            start, end = section_bounds(lines, index)
            quote = quote_from_section(req_id, lines, start, end)
            if quote:
                return RequirementQuote(req_id=req_id, quote=quote, source=f"{srs_rel}:line {index + 1}")

    offset = matches[0].start()
    first_line = line_number_at(srs_text, offset)
    for index, line in enumerate(lines, start=1):
        if id_in_text(req_id, line):
            cells = split_table_row(line)
            if cells and not is_separator_row(cells):
                return RequirementQuote(req_id=req_id, quote=" | ".join(cells), source=f"{srs_rel}:line {index}")
            cleaned = strip_markdown(line)
            if cleaned:
                return RequirementQuote(req_id=req_id, quote=cleaned, source=f"{srs_rel}:line {index}")

    return RequirementQuote(req_id=req_id, quote=req_id, source=f"{srs_rel}:line {first_line}")


def default_related_link(label: str, srs_rel: str) -> tuple[str, str]:
    return (f"{label} 미지정 - SRS 원문 확인", srs_rel)


def fill_handoff_template(
    template: str,
    req: RequirementQuote,
    srs_link_rel: str,
    generated_date: str,
) -> str:
    system_name, system_path = default_related_link("시스템 설계", srs_link_rel)
    detail_name, detail_path = default_related_link("상세 설계", srs_link_rel)
    replacements = {
        "{{이번사이클구현목표}}": f"{req.req_id} 요구사항 구현을 위한 코딩 작업을 준비한다.",
        "{{요구사항ID}}": req.req_id,
        "{{요구사항문서상대경로}}": srs_link_rel,
        "{{구현범위요약}}": "요구사항 원문 인용 범위로 제한한다.",
        "{{요구사항중단조건}}": "SRS 원문과 계약/영향 범위가 충돌하거나 인간 작성 필수 섹션이 미완성인 경우",
        "{{기획문서명}}": "요구사항명세서-SRS.md",
        "{{기획문서상대경로}}": srs_link_rel,
        "{{시스템설계문서명}}": system_name,
        "{{시스템설계문서상대경로}}": system_path,
        "{{상세설계문서명}}": detail_name,
        "{{상세설계문서상대경로}}": detail_path,
        "{{검증명령1}}": "python3 -m compileall scripts",
        "{{검증명령1기대결과}}": "scripts 디렉터리의 Python 파일이 오류 없이 컴파일된다.",
        "{{검증명령1통과기준}}": "명령이 종료 코드 0으로 완료된다.",
        "{{검증명령2}}": "python3 -m unittest discover -s tests",
        "{{검증명령2기대결과}}": "tests 디렉터리의 unittest 테스트가 오류 없이 완료된다.",
        "{{검증명령2통과기준}}": "명령이 종료 코드 0으로 완료된다.",
        "{{완료기준1}}": f"{req.req_id} 요구사항 원문 인용이 구현 결과와 추적 가능하다.",
        "{{완료기준2}}": "검증 명령 표의 모든 명령이 성공 종료 코드로 완료된다.",
        "{{완료기준3}}": "필수 테스트와 보안 체크 결과가 handoff의 계약 항목을 모두 덮는다.",
    }

    rendered = template
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)

    requirement_row = (
        f"| {req.req_id} | {srs_link_rel} | 요구사항 원문 인용 범위로 제한한다. | "
        "SRS 원문과 계약/영향 범위가 충돌하거나 인간 작성 필수 섹션이 미완성인 경우 |"
    )
    requirement_notes = (
        f"\n- 생성일: {generated_date}\n"
        f"- 요구사항 원문 출처: `{req.source}`\n"
        f"- 요구사항 원문 인용: “{req.quote}”\n"
    )
    if requirement_row not in rendered:
        raise HandoffError("CODING_HANDOFF template is missing the requirement note insertion point")
    rendered = rendered.replace(requirement_row, requirement_row + requirement_notes, 1)

    return rendered


def create_handoff(req_id: str, project_root: Path, srs_path: Path | None, force: bool) -> Path:
    if REQ_ID_RE.fullmatch(req_id) is None:
        raise HandoffError(f"Invalid requirement ID shape: {req_id}")
    project_root = project_root.resolve()
    if srs_path is None:
        srs_path = project_root / DEFAULT_SRS
    elif not srs_path.is_absolute():
        srs_path = project_root / srs_path
    srs_path = srs_path.resolve()
    srs_source_rel = relative_posix(srs_path, project_root)
    srs_text = read_text(srs_path)
    req = extract_requirement_quote(srs_text, srs_source_rel, req_id)

    template_path = repo_root() / HANDOFF_TEMPLATE
    template = read_text(template_path)

    target_dir = project_root / HANDOFF_DIR
    target = target_dir / f"CODING_HANDOFF-{req_id}.md"
    if target.exists() and not force:
        raise HandoffError(f"Handoff already exists (use --force to overwrite): {target}")

    target_dir.mkdir(parents=True, exist_ok=True)
    rendered = fill_handoff_template(
        template,
        req,
        relative_posix(srs_path, target_dir),
        _dt.date.today().isoformat(),
    )
    target.write_text(rendered, encoding="utf-8")
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vive-md")
    subcommands = parser.add_subparsers(dest="command", required=True)

    handoff = subcommands.add_parser("handoff", help="Manage coding handoff documents")
    handoff_commands = handoff.add_subparsers(dest="handoff_command", required=True)

    new = handoff_commands.add_parser("new", help="Create a coding handoff from an SRS requirement")
    new.add_argument("req_id", help="Requirement ID to hand off, for example REQ-001 or FR-001")
    new.add_argument("--force", action="store_true", help="Overwrite an existing handoff")
    new.add_argument("--project-root", type=Path, default=Path.cwd(), help="Project root containing waterfall docs")
    new.add_argument("--srs", type=Path, default=None, help="Path to the SRS document (defaults under project root)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "handoff" and args.handoff_command == "new":
            target = create_handoff(args.req_id, args.project_root, args.srs, args.force)
            print(target)
            return 0
    except HandoffError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    parser.error("unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
