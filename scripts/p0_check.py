#!/usr/bin/env python3
"""P0 checks for vive-md waterfall delivery gates."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


DEFAULT_SRS = Path("01-요구사항분석") / "요구사항명세서-SRS.md"
DEFAULT_GLOSSARY = Path("00-기획") / "용어정의서.md"
HANDOFF_DIR = Path("04-구현")
HANDOFF_GLOB = "CODING_HANDOFF-*.md"
REVIEW_LOG = Path("08-검토") / "REVIEW_LOG.md"
RELEASE_DIR = Path("06-배포")
RELEASE_FILE = RELEASE_DIR / "RELEASE_CHECKLIST.md"
RELEASE_GLOB = "RELEASE_CHECKLIST*.md"

REQ_ID_RE = re.compile(r"(?<![A-Z0-9-])([A-Z][A-Z0-9]*-\d{3,})(?![A-Z0-9-])")
HANDOFF_ID_RE = re.compile(r"CODING_HANDOFF-[A-Z][A-Z0-9]*-\d{3,}")
TERM_HEADING_RE = re.compile(r"용어\s*(정의|사전)|공통\s*도메인\s*정의|Glossary", re.IGNORECASE)
TERM_LINK_RE = re.compile(r"\[[^\]]*용어정의서[^\]]*\]\([^)]*용어정의서\.md\)|용어정의서\.md")

HANDOFF_REQUIRED_SECTIONS = (
    "요구사항 ID",
    "금지 변경",
    "검증 명령",
    "롤백 메모",
)
HUMAN_REQUIRED_SECTIONS = (
    "영향 범위",
    "금지 변경",
    "계약",
    "구현 단계",
    "필수 테스트",
    "보안 체크",
    "롤백 메모",
)
RELEASE_REQUIRED_SECTIONS = (
    "릴리스 식별",
    "테스트 통과 증거",
    "REVIEW_LOG 참조",
    "롤백 절차",
    "릴리스 후 확인 항목",
    "최종 게이트",
)
REVIEW_RELEASE_VERDICTS = {"통과", "완료", "수정 완료", "결함 처리 완료"}
PLACEHOLDER_RE = re.compile(
    r"\{\{[^}]+\}\}|\[\s*placeholder\b|\bplaceholder\b|\bTODO\b|\bTBD\b|"
    r"작성\s*(필요|예정)|채워\s*넣|미정|추후\s*작성|확인\s*필요(?!\s*없음)",
    re.IGNORECASE,
)
RELEASE_SCAFFOLD_RE = re.compile(
    r"\[(?:REL-YYYYMMDD-000|CODING_HANDOFF-REQ-000|REQ-000|YYYY-MM-DD|"
    r"미완료/완료|대기/통과/실패|통과/수정 필요/차단)\]|"
    r"\[YYYY-MM-DD HH:MM\]|\[REL-[^\]]*000\]"
)

REVIEW_LOG_EVIDENCE_COLUMNS = {"날짜", "핸드오프 ID", "판정"}
REVIEW_LOG_SCAFFOLD_CELLS = {"YYYY-MM-DD", "CODING_HANDOFF-REQ-000", "통과/수정 필요/차단"}

class CheckError(Exception):
    """Raised when checker input files cannot be read."""


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CheckError(f"File not found: {path}") from exc


def strip_markdown(value: str) -> str:
    value = re.sub(r"<!--.*?-->", "", value, flags=re.DOTALL).strip()
    value = value.replace("\\|", "|")
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = value.strip("[] ")
    return re.sub(r"\s+", " ", value).strip()


def split_table_row(line: str) -> list[str]:
    raw = line.strip()
    if not raw.startswith("|") or not raw.endswith("|"):
        return []
    cells: list[str] = []
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


def is_table_separator(line_or_cells: str | list[str]) -> bool:
    if isinstance(line_or_cells, list):
        return bool(line_or_cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in line_or_cells)
    return re.fullmatch(r"\|?\s*:?-{3,}:?(\s*\|\s*:?-{3,}:?)*\s*\|?", line_or_cells) is not None


def extract_section(text: str, heading: str) -> str | None:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return None
    start = match.end()
    next_heading = re.search(r"^##\s+", text[start:], re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end]


def extract_numbered_section(text: str, label: str) -> str | None:
    pattern = re.compile(rf"^##\s+(?:\d+\.\s+)?{re.escape(label)}\s*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return None
    start = match.end()
    next_heading = re.search(r"^##\s+", text[start:], re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end]


def strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def substantive_lines(section_body: str) -> list[str]:
    lines: list[str] = []
    pending_table_header: str | None = None
    in_table = False

    for line in strip_comments(section_body).splitlines():
        stripped = line.strip()
        if not stripped or stripped == "---":
            continue
        if is_table_separator(stripped):
            if pending_table_header is not None:
                pending_table_header = None
                in_table = True
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            if not in_table:
                pending_table_header = stripped
                continue
            lines.append(stripped)
            continue
        if pending_table_header is not None:
            lines.append(pending_table_header)
            pending_table_header = None
            in_table = False
        lines.append(stripped)

    if pending_table_header is not None:
        lines.append(pending_table_header)
    return lines


def section_is_blank_or_placeholder(section_body: str) -> bool:
    lines = substantive_lines(section_body)
    if not lines:
        return True
    return PLACEHOLDER_RE.search("\n".join(lines)) is not None


def release_placeholder_like(text: str) -> bool:
    return PLACEHOLDER_RE.search(text) is not None or RELEASE_SCAFFOLD_RE.search(text) is not None


def has_exact_table_value(section_body: str, column_index: int, allowed_values: set[str]) -> bool:
    return any(len(row) > column_index and row[column_index] in allowed_values for row in table_data_rows(section_body))


def all_table_values(section_body: str, column_index: int, allowed_values: set[str]) -> bool:
    rows = table_data_rows(section_body)
    return bool(rows) and all(len(row) > column_index and row[column_index] in allowed_values for row in rows)


def table_data_rows(section_body: str) -> list[list[str]]:
    rows: list[list[str]] = []
    seen_header = False
    for line in strip_comments(section_body).splitlines():
        cells = split_table_row(line)
        if not cells:
            continue
        if is_table_separator(cells):
            seen_header = True
            continue
        if not seen_header:
            continue
        rows.append(cells)
    return rows


TERMINAL_SECURITY_RESULTS = {"확인 필요 없음", "확인 완료", "점검 완료", "영향 없음", "해당 없음"}


def security_check_errors(path: Path, section_body: str) -> list[str]:
    errors: list[str] = []
    for row in table_data_rows(section_body):
        if len(row) < 2:
            errors.append(f"{path}: 보안 체크 row is incomplete")
            continue
        result = row[1].strip()
        if result not in TERMINAL_SECURITY_RESULTS:
            item = row[0] if row else "unknown"
            errors.append(f"{path}: 보안 체크 is not terminal for {item}: {result}")
    return errors


def srs_requirement_ids(srs_text: str) -> set[str]:
    return set(REQ_ID_RE.findall(srs_text))


def handoff_requirement_ids(handoff_text: str) -> set[str]:
    section = extract_section(handoff_text, "요구사항 ID")
    if section is None:
        return set()
    return set(REQ_ID_RE.findall(section))


def check_handoff(path: Path, srs_ids: set[str]) -> list[str]:
    errors: list[str] = []
    text = read_text(path)
    req_ids = handoff_requirement_ids(text)

    if not req_ids:
        errors.append(f"{path}: 요구사항 ID section has no requirement ID")
    for req_id in sorted(req_ids):
        if req_id not in srs_ids:
            errors.append(f"{path}: requirement ID not found in SRS: {req_id}")

    for heading in HANDOFF_REQUIRED_SECTIONS:
        section = extract_section(text, heading)
        if section is None:
            errors.append(f"{path}: missing P0 handoff section: {heading}")
            continue
        if section_is_blank_or_placeholder(section):
            errors.append(f"{path}: P0 handoff section is blank or placeholder-like: {heading}")

    for heading in HUMAN_REQUIRED_SECTIONS:
        section = extract_section(text, heading)
        if section is None:
            errors.append(f"{path}: missing human-required section: {heading}")
            continue
        if section_is_blank_or_placeholder(section):
            errors.append(f"{path}: human-required section is blank or placeholder-like: {heading}")
        if heading == "보안 체크":
            errors.extend(security_check_errors(path, section))

    return errors


def has_term_heading(text: str) -> bool:
    return any(TERM_HEADING_RE.search(line.lstrip("# ").strip()) for line in text.splitlines() if line.startswith("#"))


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


def is_placeholder_term(term: str) -> bool:
    raw = term.strip()
    cleaned = strip_markdown(term)
    return (
        not cleaned
        or "placeholder" in cleaned.lower()
        or raw.startswith("[")
        or cleaned in {"용어", "항목"}
        or re.fullmatch(r"용어\d*", cleaned) is not None
        or cleaned == "추가 용어"
    )


def extract_terms_from_text(text: str) -> set[str]:
    lines = text.splitlines()
    terms: set[str] = set()
    for index, line in enumerate(lines):
        if not line.startswith("#") or not TERM_HEADING_RE.search(line.lstrip("# ").strip()):
            continue
        _, end = section_bounds(lines, index)
        in_term_table = False
        for body_line in lines[index + 1 : end]:
            cells = split_table_row(body_line)
            if not cells:
                continue
            if is_table_separator(cells):
                continue
            if not in_term_table:
                if cells and "용어" in cells[0]:
                    in_term_table = True
                continue
            term = cells[0].strip()
            if not is_placeholder_term(term):
                terms.add(strip_markdown(term))
    return terms


def normalize_term(term: str) -> str:
    return re.sub(r"\s+", " ", strip_markdown(term)).casefold()


def term_candidates(term: str) -> set[str]:
    cleaned = strip_markdown(term)
    candidates = {cleaned}
    if "(" in cleaned and ")" in cleaned:
        before = cleaned.split("(", 1)[0].strip()
        inside = cleaned.split("(", 1)[1].split(")", 1)[0].strip()
        if before:
            candidates.add(before)
        if inside:
            candidates.add(inside)
    return {candidate for candidate in candidates if candidate}


def glossary_terms(glossary_text: str) -> set[str]:
    terms: set[str] = set()
    for line in glossary_text.splitlines():
        cells = split_table_row(line)
        if not cells or is_table_separator(cells) or cells[0] == "용어":
            continue
        for value in cells[:2]:
            cleaned_value = strip_markdown(value)
            aliases = [cleaned_value, *re.split(r"[,/]", cleaned_value)]
            for alias in aliases:
                alias = alias.strip()
                if alias and not is_placeholder_term(alias) and alias != "해당 없음":
                    for candidate in term_candidates(alias):
                        terms.add(normalize_term(candidate))
    return terms


def markdown_files(root: Path) -> list[Path]:
    excluded_parts = {".git", ".gjc", "__pycache__"}
    return sorted(path for path in root.rglob("*.md") if not excluded_parts.intersection(path.parts))


def check_glossary(project_root: Path, glossary_path: Path) -> list[str]:
    errors: list[str] = []
    glossary_text = read_text(glossary_path)
    known_terms = glossary_terms(glossary_text)

    for path in markdown_files(project_root):
        if path.resolve() == glossary_path.resolve():
            continue
        text = read_text(path)
        if not has_term_heading(text):
            continue
        if TERM_LINK_RE.search(text) is None:
            errors.append(f"{path}: glossary-defining document is missing 용어정의서 link")
        for term in sorted(extract_terms_from_text(text)):
            if not any(normalize_term(candidate) in known_terms for candidate in term_candidates(term)):
                errors.append(f"{path}: defined term is missing from 용어정의서: {term}")

    return errors


def release_status(text: str) -> str | None:
    section = extract_numbered_section(text, "릴리스 식별") or text
    for line in section.splitlines():
        cells = split_table_row(line)
        if len(cells) >= 2 and cells[0] == "게이트 상태":
            return strip_markdown(cells[1])
    return None


def review_log_has_release_entry(review_log_text: str, handoff_id: str) -> bool:
    for line in review_log_text.splitlines():
        cells = split_table_row(line)
        if len(cells) < 5 or is_table_separator(cells):
            continue
        verdict = cells[4] if len(cells) > 4 else ""
        if handoff_id in cells and verdict in REVIEW_RELEASE_VERDICTS:
            return True
    return False


def is_review_log_evidence_header(cells: list[str]) -> bool:
    return REVIEW_LOG_EVIDENCE_COLUMNS.issubset(set(cells))


def review_log_cell_is_scaffold(value: str) -> bool:
    cleaned = strip_markdown(value)
    lowered = cleaned.lower()
    if cleaned in REVIEW_LOG_SCAFFOLD_CELLS:
        return True
    if lowered.startswith(("placeholder", "todo", "tbd")):
        return True
    return bool(re.fullmatch(r"작성\s*(필요|예정)|채워\s*넣.*|미정|추후\s*작성", cleaned))


def iter_review_log_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    pending_header: list[str] | None = None
    in_evidence_table = False

    for line in strip_comments(text).splitlines():
        cells = split_table_row(line)
        if not cells:
            pending_header = None
            in_evidence_table = False
            continue
        if is_table_separator(cells):
            in_evidence_table = pending_header is not None and is_review_log_evidence_header(pending_header)
            pending_header = None
            continue
        if in_evidence_table:
            rows.append(cells)
            continue
        pending_header = cells

    return rows


def review_log_placeholder_errors(path: Path, text: str) -> list[str]:
    errors: list[str] = []
    for cells in iter_review_log_rows(text):
        if any(review_log_cell_is_scaffold(cell) for cell in cells):
            errors.append(f"{path}: REVIEW_LOG active evidence row is scaffold-like: {' | '.join(cells)}")
    return errors


def review_log_release_entries(review_log_text: str) -> set[tuple[str, str, str, str]]:
    entries: set[tuple[str, str, str, str]] = set()
    for cells in iter_review_log_rows(review_log_text):
        if len(cells) < 5 or any(review_log_cell_is_scaffold(cell) for cell in cells):
            continue
        date, handoff_id, reviewer, verdict = cells[0], cells[1], cells[2], cells[4]
        if verdict in REVIEW_RELEASE_VERDICTS:
            entries.add((handoff_id, date, reviewer, verdict))
    return entries


def release_review_references(release_text: str) -> list[tuple[str, str, str, str]]:
    refs: list[tuple[str, str, str, str]] = []
    section = extract_numbered_section(release_text, "REVIEW_LOG 참조") or ""
    for row in table_data_rows(section):
        if len(row) >= 4:
            refs.append((row[0], row[1], row[2], row[3]))
    return refs


def check_release_structure(path: Path, text: str) -> list[str]:
    errors: list[str] = []
    for label in RELEASE_REQUIRED_SECTIONS:
        section = extract_numbered_section(text, label)
        if section is None:
            errors.append(f"{path}: missing RELEASE_CHECKLIST section: {label}")
            continue
        if not substantive_lines(section) or release_placeholder_like(section):
            errors.append(f"{path}: RELEASE_CHECKLIST section is blank or placeholder-like: {label}")

    if release_status(text) != "완료":
        errors.append(f"{path}: RELEASE_CHECKLIST gate status must be 완료")

    test_section = extract_numbered_section(text, "테스트 통과 증거") or ""
    if not all_table_values(test_section, 2, {"통과"}):
        errors.append(f"{path}: 테스트 통과 증거 must include only passing results")

    review_section = extract_numbered_section(text, "REVIEW_LOG 참조") or ""
    if not all_table_values(review_section, 3, REVIEW_RELEASE_VERDICTS):
        errors.append(f"{path}: REVIEW_LOG 참조 must include only release-eligible verdicts")

    rollback_rows = table_data_rows(extract_numbered_section(text, "롤백 절차") or "")
    if not rollback_rows or not any(len(row) >= 3 and row[1] and row[2] for row in rollback_rows):
        errors.append(f"{path}: 롤백 절차 must include rollback procedure and verification command")

    post_release = extract_numbered_section(text, "릴리스 후 확인 항목") or ""
    if not all_table_values(post_release, 3, {"통과"}):
        errors.append(f"{path}: 릴리스 후 확인 항목 must include passing confirmations")

    final_gate = extract_numbered_section(text, "최종 게이트") or ""
    if "- [ ]" in final_gate or "- [x]" not in final_gate.lower():
        errors.append(f"{path}: 최종 게이트 must have checked completion items only")

    return errors


def check_release_gate(project_root: Path) -> list[str]:
    release_path = project_root / RELEASE_FILE
    review_log_path = project_root / REVIEW_LOG
    errors: list[str] = []

    if not release_path.exists():
        errors.append(f"{release_path}: required RELEASE_CHECKLIST is missing")
        return errors
    if not review_log_path.exists():
        errors.append(f"{review_log_path}: required REVIEW_LOG is missing")
        review_log_text = ""
    else:
        review_log_text = read_text(review_log_path)
        errors.extend(review_log_placeholder_errors(review_log_path, review_log_text))

    release_files = sorted({release_path, *release_path.parent.glob(RELEASE_GLOB)})
    for release in release_files:
        text = read_text(release)
        errors.extend(check_release_structure(release, text))
        handoff_ids = {handoff_id for handoff_id in HANDOFF_ID_RE.findall(text) if handoff_id != "CODING_HANDOFF-REQ-000"}
        if not handoff_ids:
            errors.append(f"{release}: RELEASE_CHECKLIST has no concrete handoff ID")
        release_refs = release_review_references(text)
        review_entries = review_log_release_entries(review_log_text) if review_log_text else set()
        for ref in release_refs:
            if review_log_text and ref not in review_entries:
                handoff_id, date, reviewer, verdict = ref
                errors.append(
                    f"{release}: REVIEW_LOG 참조 row has no matching REVIEW_LOG entry: "
                    f"{handoff_id} / {date} / {reviewer} / {verdict}"
                )

        for handoff_id in sorted(handoff_ids):
            if not review_log_text:
                continue
            if not review_log_has_release_entry(review_log_text, handoff_id):
                errors.append(f"{release}: REVIEW_LOG has no release-eligible entry for {handoff_id}")

    return errors


def check_handoffs(project_root: Path, srs_path: Path) -> list[str]:
    srs_ids = srs_requirement_ids(read_text(srs_path))
    handoff_root = project_root / HANDOFF_DIR
    if not handoff_root.exists():
        return []
    errors: list[str] = []
    for handoff in sorted(handoff_root.glob(HANDOFF_GLOB)):
        errors.extend(check_handoff(handoff, srs_ids))
    return errors


def run_checks(
    project_root: Path,
    srs_path: Path | None = None,
    glossary_path: Path | None = None,
    stage: str = "all",
) -> list[str]:
    project_root = project_root.resolve()
    if srs_path is None:
        srs_path = project_root / DEFAULT_SRS
    elif not srs_path.is_absolute():
        srs_path = project_root / srs_path
    if glossary_path is None:
        glossary_path = project_root / DEFAULT_GLOSSARY
    elif not glossary_path.is_absolute():
        glossary_path = project_root / glossary_path

    srs_path = srs_path.resolve()
    glossary_path = glossary_path.resolve()

    errors: list[str] = []
    if stage in {"handoff", "all"}:
        errors.extend(check_handoffs(project_root, srs_path))
        errors.extend(check_glossary(project_root, glossary_path))
    if stage in {"release", "all"}:
        errors.extend(check_release_gate(project_root))
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run vive-md P0 waterfall checks")
    parser.add_argument("--project-root", type=Path, default=Path.cwd(), help="Project root containing waterfall docs")
    parser.add_argument("--srs", type=Path, default=None, help="Path to the SRS document (defaults under project root)")
    parser.add_argument("--glossary", type=Path, default=None, help="Path to 용어정의서.md (defaults under project root)")
    parser.add_argument(
        "--stage",
        choices=("handoff", "release", "all"),
        default="all",
        help="Gate scope: handoff checks pre-review work, release checks release artifacts, all runs both",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        errors = run_checks(args.project_root, args.srs, args.glossary, args.stage)
    except CheckError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
