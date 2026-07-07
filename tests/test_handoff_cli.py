from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VIVE_MD = REPO_ROOT / "vive-md"
P0_CHECK = REPO_ROOT / "scripts" / "p0_check.py"
SRS_REL = Path("01-요구사항분석") / "요구사항명세서-SRS.md"
HANDOFF_REL = Path("04-구현") / "CODING_HANDOFF-REQ-001.md"


def write_fixture_docs(project_root: Path) -> None:
    srs_path = project_root / SRS_REL
    srs_path.parent.mkdir(parents=True)
    (project_root / "04-구현").mkdir(parents=True)
    srs_path.write_text(
        "\n".join(
            [
                "# 테스트 SRS",
                "",
                "## 3. 기능 요구사항",
                "",
                "| 요구사항 ID | 이름 | 설명 |",
                "| --- | --- | --- |",
                "| REQ-001 | 할 일 생성 | 사용자는 제목을 입력해 할 일을 생성할 수 있다. |",
                "| REQ-002 | 할 일 완료 | 사용자는 생성된 할 일을 완료 상태로 바꿀 수 있다. |",
                "",
                "### 3.1 REQ-001: 할 일 생성",
                "",
                "| 항목 | 내용 |",
                "| --- | --- |",
                "| **REQ-ID** | REQ-001 |",
                "| **설명** | 사용자는 제목을 입력해 할 일을 생성할 수 있다. |",
                "",
                "### 3.2 REQ-002: 할 일 완료",
                "",
                "| 항목 | 내용 |",
                "| --- | --- |",
                "| **REQ-ID** | REQ-002 |",
                "| **설명** | 사용자는 생성된 할 일을 완료 상태로 바꿀 수 있다. |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    glossary_path = project_root / "00-기획" / "용어정의서.md"
    glossary_path.parent.mkdir(parents=True, exist_ok=True)
    glossary_path.write_text(
        "\n".join(
            [
                "# 용어정의서",
                "",
                "| 용어 | 별칭 | 정의 |",
                "| --- | --- | --- |",
                "| SRS | Software Requirements Specification | 소프트웨어 요구사항 명세서 |",
                "| RTM | Requirements Traceability Matrix | 요구사항 추적 매트릭스 |",
                "| 할 일 | Todo | 사용자가 생성하고 완료할 수 있는 작업 항목 |",
                "",
            ]
        ),
        encoding="utf-8",
    )


def replace_section(text: str, heading: str, body: str) -> str:
    pattern = re.compile(rf"(^## {re.escape(heading)}\n)(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)
    new_text, count = pattern.subn(lambda match: match.group(1) + body.rstrip() + "\n\n", text)
    if count != 1:
        raise AssertionError(heading)
    return new_text


def fill_human_required_sections(handoff_path: Path) -> None:
    text = handoff_path.read_text(encoding="utf-8")
    replacements = {
        "영향 범위": """
| 구분 | 대상 | 변경 목적 | 허용 작업 | 영향 없어야 하는 범위 |
| --- | --- | --- | --- | --- |
| 코드 | src/todos | 할 일 생성 동작 구현 | 파일 추가 및 수정 | 인증, 결제, 배포 설정 |
""",
        "금지 변경": """
| 구분 | 금지 대상 | 금지 이유 | 위반 시 처리 |
| --- | --- | --- | --- |
| 설정 | 배포 설정 | 이번 handoff 범위 밖 | 구현 중단 및 작성자 확인 |
""",
        "계약": """
| 계약 항목 | 계약 내용 | 변경 가능 여부 | 검증 방법 | 해당 없음 사유 |
| --- | --- | --- | --- | --- |
| 입력 | 제목 문자열을 받는다. | 불가 | 단위 테스트 | 해당 없음 아님 |
| 출력 | 생성된 할 일 식별자를 반환한다. | 불가 | 단위 테스트 | 해당 없음 아님 |
| 에러 | 제목이 없으면 검증 오류를 반환한다. | 불가 | 단위 테스트 | 해당 없음 아님 |
| 부작용 | 저장소에 할 일을 기록한다. | 불가 | 통합 확인 | 해당 없음 아님 |
| 호환성 | 기존 조회 계약을 유지한다. | 불가 | 회귀 테스트 | 해당 없음 아님 |
| idempotency/concurrency | 중복 제출은 별도 항목으로 저장한다. | 가능 | 동시성 테스트 | 해당 없음 아님 |
| 실패 동작 | 저장 실패 시 부분 기록을 남기지 않는다. | 불가 | 실패 주입 테스트 | 해당 없음 아님 |
""",
        "구현 단계": """
1. [ ] 요청 입력 검증을 구현한다.
2. [ ] 저장소 기록 경로를 연결한다.
3. [ ] 성공 및 실패 응답을 검증한다.
""",
        "필수 테스트": """
| 구분 | 요구사항 ID 또는 계약 항목 | 테스트 파일 또는 케이스 | 확인할 동작 | 통과 기준 |
| --- | --- | --- | --- | --- |
| 요구사항 | REQ-001 | tests/test_todos.py::CreateTodoTest::test_create_todo | 제목으로 할 일이 생성된다. | 식별자가 반환된다. |
| 계약 | 입력 | tests/test_todos.py::CreateTodoTest::test_create_todo_requires_title | 빈 제목을 거부한다. | 검증 오류가 반환된다. |
""",
        "보안 체크": """
| 보안 항목 | 점검 결과 | 근거 | 해당 없음 사유 |
| --- | --- | --- | --- |
| 인증/인가 | 확인 필요 없음 | 공개 로컬 기능 | 제품 범위상 계정 경계 없음 |
| 입력 검증 | 점검 완료 | 제목 입력 길이 제한 | 해당 없음 아님 |
| injection | 점검 완료 | 저장 전 이스케이프 확인 | 해당 없음 아님 |
| 비밀정보 | 영향 없음 | 비밀값을 읽지 않음 | 제품 범위상 비밀값 없음 |
| PII/logging | 영향 없음 | 제목 외 개인정보 없음 | 제품 범위상 PII 없음 |
| 파일/네트워크 경계 | 영향 없음 | 파일과 네트워크 사용 없음 | 제품 범위상 외부 경계 없음 |
| 의존성 취약점 | 영향 없음 | 새 의존성 없음 | 제품 범위상 의존성 추가 없음 |
| abuse case | 점검 완료 | 대량 생성 제한 확인 | 해당 없음 아님 |
""",
        "롤백 메모": """
| 롤백 항목 | 절차 | 검증 명령 | 통과 기준 | 해당 없음 사유 |
| --- | --- | --- | --- | --- |
| revert 방법 | 변경 커밋을 되돌린다. | `python3 -m unittest discover -s tests` | 테스트 성공 | 해당 없음 아님 |
| dependency pin rollback | 새 의존성이 없다. | `python3 -m compileall scripts` | 컴파일 성공 | 제품 범위상 의존성 없음 |
| migration rollback | 마이그레이션이 없다. | `python3 -m compileall scripts` | 컴파일 성공 | 제품 범위상 마이그레이션 없음 |
| data recovery | 생성 데이터는 백업에서 복원한다. | `python3 -m unittest discover -s tests` | 테스트 성공 | 해당 없음 아님 |
""",
    }
    for heading, body in replacements.items():
        text = replace_section(text, heading, body)
    handoff_path.write_text(text, encoding="utf-8")
def write_completed_release_artifacts(
    project_root: Path,
    handoff_id: str = "CODING_HANDOFF-REQ-001",
    req_id: str = "REQ-001",
    review_verdict: str = "통과",
) -> None:
    review_log = project_root / "08-검토" / "REVIEW_LOG.md"
    review_log.parent.mkdir(parents=True, exist_ok=True)
    review_log.write_text(
        "\n".join(
            [
                "# REVIEW_LOG",
                "",
                "| 날짜 | 핸드오프 ID | 리뷰어 | 발견 결함 | 판정 | 후속 조치 |",
                "| --- | --- | --- | --- | --- | --- |",
                f"| 2026-07-05 | {handoff_id} | reviewer | 없음 | {review_verdict} | 없음 |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    release = project_root / "06-배포" / "RELEASE_CHECKLIST.md"
    release.parent.mkdir(parents=True, exist_ok=True)
    release.write_text(
        "\n".join(
            [
                "# RELEASE_CHECKLIST",
                "",
                "## 1. 릴리스 식별",
                "",
                "| 항목 | 내용 |",
                "| --- | --- |",
                "| 릴리스 ID | REL-20260705-001 |",
                f"| 핸드오프 ID | {handoff_id} |",
                f"| 요구사항 ID | {req_id} |",
                "| 게이트 상태 | 완료 |",
                "| 작성일 | 2026-07-05 |",
                "",
                "## 2. 테스트 통과 증거",
                "",
                "| 검증 명령 | 실행 일시 | 결과 | 증거 링크/로그 |",
                "| --- | --- | --- | --- |",
                "| `python3 -m unittest discover -s tests` | 2026-07-05 10:00 | 통과 | smoke.log |",
                "",
                "## 3. REVIEW_LOG 참조",
                "",
                "| 핸드오프 ID | REVIEW_LOG 항목 날짜 | 리뷰어 | 판정 |",
                "| --- | --- | --- | --- |",
                f"| {handoff_id} | 2026-07-05 | reviewer | 통과 |",
                "",
                "## 4. 롤백 절차",
                "",
                "| 롤백 항목 | 롤백 명령 또는 절차 | 롤백 검증 명령 | 책임자 |",
                "| --- | --- | --- | --- |",
                "| 코드 변경 | `git revert abc123` | `python3 -m unittest discover -s tests` | reviewer |",
                "",
                "## 5. 릴리스 후 확인 항목",
                "",
                "| 확인 항목 | 확인 방법 | 기대 결과 | 확인 결과 |",
                "| --- | --- | --- | --- |",
                "| 핵심 기능 스모크 | smoke command | 정상 응답 | 통과 |",
                "",
                "## 6. 최종 게이트",
                "",
                "- [x] 모든 검증 명령이 통과했다.",
                "- [x] REVIEW_LOG에 같은 핸드오프 ID의 통과 항목이 있다.",
                "- [x] 롤백 명령과 롤백 검증 명령이 비어 있지 않다.",
                "",
            ]
        ),
        encoding="utf-8",
    )



class HandoffCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.project_root = Path(self.tmp.name)
        write_fixture_docs(self.project_root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @property
    def handoff_path(self) -> Path:
        return self.project_root / HANDOFF_REL

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(VIVE_MD), *args, "--project-root", str(self.project_root)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def run_checker(self, stage: str = "handoff") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(P0_CHECK), "--project-root", str(self.project_root), "--stage", stage],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def create_handoff(self) -> subprocess.CompletedProcess[str]:
        return self.run_cli("handoff", "new", "REQ-001")

    def test_handoff_new_creates_req_001(self) -> None:
        result = self.create_handoff()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.handoff_path.exists())
        text = self.handoff_path.read_text(encoding="utf-8")
        self.assertIn("REQ-001", text)
        self.assertIn("요구사항 원문 인용", text)
        self.assertIn("사용자는 제목을 입력해 할 일을 생성할 수 있다.", text)
        self.assertIn("python3 -m compileall scripts", text)
        self.assertIn("python3 -m unittest discover -s tests", text)
        self.assertNotIn("pytest", text)
        self.assertIn("{{하지않을것}}", text)
        self.assertIn("{{성능기준}}", text)
        self.assertIn("{{마이그레이션메모}}", text)
        self.assertIn("{{리뷰포인트}}", text)

    def test_generated_handoff_contains_generation_date_source_and_quote(self) -> None:
        self.assertEqual(self.create_handoff().returncode, 0)

        text = self.handoff_path.read_text(encoding="utf-8")

        self.assertRegex(text, r"- 생성일: \d{4}-\d{2}-\d{2}")
        self.assertIn("- 요구사항 원문 출처: `01-요구사항분석/요구사항명세서-SRS.md:line 10`", text)
        self.assertIn("- 요구사항 원문 인용:", text)
        self.assertIn("사용자는 제목을 입력해 할 일을 생성할 수 있다.", text)

    def test_generated_handoff_links_resolve_from_handoff_directory(self) -> None:
        self.assertEqual(self.create_handoff().returncode, 0)

        text = self.handoff_path.read_text(encoding="utf-8")
        self.assertIn("../01-요구사항분석/요구사항명세서-SRS.md", text)
        for href in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            with self.subTest(href=href):
                self.assertTrue((self.handoff_path.parent / href).resolve().exists())


    def test_existing_handoff_fails_without_force(self) -> None:
        self.assertEqual(self.create_handoff().returncode, 0)
        original = self.handoff_path.read_text(encoding="utf-8")

        result = self.create_handoff()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already exists", result.stderr)
        self.assertEqual(self.handoff_path.read_text(encoding="utf-8"), original)

    def test_force_overwrites_existing_handoff(self) -> None:
        self.assertEqual(self.create_handoff().returncode, 0)
        self.handoff_path.write_text("stale handoff\n", encoding="utf-8")

        result = self.run_cli("handoff", "new", "REQ-001", "--force")

        self.assertEqual(result.returncode, 0, result.stderr)
        text = self.handoff_path.read_text(encoding="utf-8")
        self.assertNotIn("stale handoff", text)
        self.assertIn("REQ-001", text)

    def test_invalid_requirement_id_shape_fails(self) -> None:
        result = self.run_cli("handoff", "new", "REQ-1")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid requirement ID shape", result.stderr)
        self.assertFalse((self.project_root / "04-구현" / "CODING_HANDOFF-REQ-1.md").exists())

    def test_p0_checker_fails_on_generated_human_placeholders(self) -> None:
        self.assertEqual(self.create_handoff().returncode, 0)

        result = self.run_checker()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("placeholder-like", result.stderr)
        self.assertIn("영향 범위", result.stderr)

    def test_p0_checker_passes_after_human_sections_are_filled(self) -> None:
        self.assertEqual(self.create_handoff().returncode, 0)
        fill_human_required_sections(self.handoff_path)

        result = self.run_checker()

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_p0_checker_fails_handoff_id_not_in_srs(self) -> None:
        self.assertEqual(self.create_handoff().returncode, 0)
        fill_human_required_sections(self.handoff_path)
        text = self.handoff_path.read_text(encoding="utf-8")
        text = text.replace("| REQ-001 | ../01-요구사항분석/요구사항명세서-SRS.md |", "| REQ-999 | ../01-요구사항분석/요구사항명세서-SRS.md |", 1)
        self.handoff_path.write_text(text, encoding="utf-8")

        result = self.run_checker()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requirement ID not found in SRS: REQ-999", result.stderr)

    def test_handoff_new_missing_requirement_fails(self) -> None:
        result = self.run_cli("handoff", "new", "REQ-999")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Requirement ID not found", result.stderr)
        self.assertFalse((self.project_root / "04-구현" / "CODING_HANDOFF-REQ-999.md").exists())

    def test_p0_checker_fails_glossary_section_without_canonical_link(self) -> None:
        planning = self.project_root / "00-기획" / "서비스기획서.md"
        planning.write_text(
            "\n".join(
                [
                    "# 서비스 기획서",
                    "",
                    "### 용어 정의",
                    "",
                    "| 용어 | 정의 |",
                    "| --- | --- |",
                    "| 새 용어 | 링크가 없는 정의 |",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_checker()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing 용어정의서 link", result.stderr)

    def test_p0_checker_passes_glossary_link_and_registered_term(self) -> None:
        planning = self.project_root / "00-기획" / "서비스기획서.md"
        planning.write_text(
            "\n".join(
                [
                    "# 서비스 기획서",
                    "",
                    "### 용어 정의",
                    "> 용어 정본은 [용어정의서](./용어정의서.md)를 참조한다.",
                    "",
                    "| 용어 | 정의 |",
                    "| --- | --- |",
                    "| 할 일 | 사용자가 생성하고 완료할 수 있는 작업 항목 |",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_checker()

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_p0_stage_release_excludes_handoff_placeholders(self) -> None:
        self.assertEqual(self.create_handoff().returncode, 0)
        write_completed_release_artifacts(self.project_root)

        release_only = self.run_checker("release")
        all_stages = self.run_checker("all")

        self.assertEqual(release_only.returncode, 0, release_only.stderr)
        self.assertNotEqual(all_stages.returncode, 0)
        self.assertIn("placeholder-like", all_stages.stderr)

    def test_p0_checker_fails_all_stage_with_review_log_placeholder_row(self) -> None:
        write_completed_release_artifacts(self.project_root)
        review_log = self.project_root / "08-검토" / "REVIEW_LOG.md"
        text = review_log.read_text(encoding="utf-8")
        concrete_row = "| 2026-07-05 | CODING_HANDOFF-REQ-001 | reviewer | 없음 | 통과 | 없음 |"
        placeholder_row = (
            "| [YYYY-MM-DD] | [CODING_HANDOFF-REQ-000] | [placeholder: 리뷰어] | "
            "[placeholder: 결함 또는 없음] | [통과/수정 필요/차단] | [placeholder: 조치 및 근거] |"
        )
        self.assertIn(concrete_row, text)
        review_log.write_text(
            text.replace(concrete_row, f"{concrete_row}\n{placeholder_row}", 1),
            encoding="utf-8",
        )

        result = self.run_checker("all")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("REVIEW_LOG active evidence row is scaffold-like", result.stderr)


    def test_p0_checker_fails_pending_security_check(self) -> None:
        self.assertEqual(self.create_handoff().returncode, 0)
        fill_human_required_sections(self.handoff_path)
        text = self.handoff_path.read_text(encoding="utf-8")
        text = text.replace("| 입력 검증 | 점검 완료 |", "| 입력 검증 | 점검 예정 |", 1)
        self.handoff_path.write_text(text, encoding="utf-8")

        result = self.run_checker()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("보안 체크 is not terminal", result.stderr)

    def test_p0_checker_fails_unrecognized_security_result(self) -> None:
        self.assertEqual(self.create_handoff().returncode, 0)
        fill_human_required_sections(self.handoff_path)
        text = self.handoff_path.read_text(encoding="utf-8")
        text = text.replace("| 입력 검증 | 점검 완료 |", "| 입력 검증 | 실패 |", 1)
        self.handoff_path.write_text(text, encoding="utf-8")

        result = self.run_checker()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("보안 체크 is not terminal", result.stderr)

    def test_p0_checker_fails_release_with_non_passing_substring(self) -> None:
        write_completed_release_artifacts(self.project_root)
        release = self.project_root / "06-배포" / "RELEASE_CHECKLIST.md"
        text = release.read_text(encoding="utf-8")
        text = text.replace("| `python3 -m unittest discover -s tests` | 2026-07-05 10:00 | 통과 | smoke.log |", "| `python3 -m unittest discover -s tests` | 2026-07-05 10:00 | 미통과 | smoke.log |", 1)
        release.write_text(text, encoding="utf-8")

        result = self.run_checker("release")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("only passing results", result.stderr)


    def test_p0_checker_fails_release_with_mixed_pass_and_fail_rows(self) -> None:
        write_completed_release_artifacts(self.project_root)
        release = self.project_root / "06-배포" / "RELEASE_CHECKLIST.md"
        text = release.read_text(encoding="utf-8")
        text = text.replace(
            "| `python3 -m unittest discover -s tests` | 2026-07-05 10:00 | 통과 | smoke.log |",
            "| `python3 -m unittest discover -s tests` | 2026-07-05 10:00 | 통과 | smoke.log |\n"
            "| `python3 -m compileall scripts` | 2026-07-05 10:01 | 미통과 | compile.log |",
            1,
        )
        release.write_text(text, encoding="utf-8")

        result = self.run_checker("release")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("only passing results", result.stderr)

    def test_p0_checker_fails_registered_link_with_unregistered_term(self) -> None:
        planning = self.project_root / "00-기획" / "서비스기획서.md"
        planning.write_text(
            "\n".join(
                [
                    "# 서비스 기획서",
                    "",
                    "### 용어 정의",
                    "> 용어 정본은 [용어정의서](./용어정의서.md)를 참조한다.",
                    "",
                    "| 용어 | 정의 |",
                    "| --- | --- |",
                    "| 미등록 용어 | 용어정의서에 없는 정의 |",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_checker()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("defined term is missing from 용어정의서: 미등록 용어", result.stderr)

    def test_p0_checker_fails_missing_release_checklist_in_all_stage(self) -> None:
        result = self.run_checker("all")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required RELEASE_CHECKLIST is missing", result.stderr)


    def test_p0_checker_fails_release_without_review_log_entry(self) -> None:
        release = self.project_root / "06-배포" / "RELEASE_CHECKLIST.md"
        release.parent.mkdir(parents=True)
        release.write_text(
            "\n".join(
                [
                    "# RELEASE_CHECKLIST",
                    "",
                    "## 1. 릴리스 식별",
                    "",
                    "| 항목 | 내용 |",
                    "| --- | --- |",
                    "| 릴리스 ID | REL-20260705-001 |",
                    "| 핸드오프 ID | CODING_HANDOFF-REQ-001 |",
                    "| 요구사항 ID | REQ-001 |",
                    "| 게이트 상태 | 완료 |",
                    "| 작성일 | 2026-07-05 |",
                    "",
                    "## 2. 테스트 통과 증거",
                    "",
                    "| 검증 명령 | 실행 일시 | 결과 | 증거 링크/로그 |",
                    "| --- | --- | --- | --- |",
                    "| `python3 -m unittest discover -s tests` | 2026-07-05 10:00 | 통과 | smoke.log |",
                    "",
                    "## 3. REVIEW_LOG 참조",
                    "",
                    "| 핸드오프 ID | REVIEW_LOG 항목 날짜 | 리뷰어 | 판정 |",
                    "| --- | --- | --- | --- |",
                    "| CODING_HANDOFF-REQ-001 | 2026-07-05 | reviewer | 통과 |",
                    "",
                    "## 4. 롤백 절차",
                    "",
                    "| 롤백 항목 | 롤백 명령 또는 절차 | 롤백 검증 명령 | 책임자 |",
                    "| --- | --- | --- | --- |",
                    "| 코드 변경 | `git revert abc123` | `python3 -m unittest discover -s tests` | reviewer |",
                    "",
                    "## 5. 릴리스 후 확인 항목",
                    "",
                    "| 확인 항목 | 확인 방법 | 기대 결과 | 확인 결과 |",
                    "| --- | --- | --- | --- |",
                    "| 핵심 기능 스모크 | smoke command | 정상 응답 | 통과 |",
                    "",
                    "## 6. 최종 게이트",
                    "",
                    "- [x] 모든 검증 명령이 통과했다.",
                    "- [x] REVIEW_LOG에 같은 핸드오프 ID의 통과 항목이 있다.",
                    "- [x] 롤백 명령과 롤백 검증 명령이 비어 있지 않다.",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_checker("all")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("REVIEW_LOG is missing", result.stderr)

    def test_p0_checker_requires_review_log_verdict_column_to_pass(self) -> None:
        self.assertEqual(self.create_handoff().returncode, 0)
        fill_human_required_sections(self.handoff_path)
        review_log = self.project_root / "08-검토" / "REVIEW_LOG.md"
        review_log.parent.mkdir(parents=True)
        review_log.write_text(
            "\n".join(
                [
                    "# REVIEW_LOG",
                    "",
                    "| 날짜 | 핸드오프 ID | 리뷰어 | 발견 결함 | 판정 | 후속 조치 |",
                    "| --- | --- | --- | --- | --- | --- |",
                    "| 2026-07-05 | CODING_HANDOFF-REQ-001 | reviewer | 결함 있음 | 차단 | 후속 조치 통과 대기 |",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        release = self.project_root / "06-배포" / "RELEASE_CHECKLIST.md"
        release.parent.mkdir(parents=True)
        release.write_text(
            "\n".join(
                [
                    "# RELEASE_CHECKLIST",
                    "",
                    "## 1. 릴리스 식별",
                    "",
                    "| 항목 | 내용 |",
                    "| --- | --- |",
                    "| 릴리스 ID | REL-20260705-001 |",
                    "| 핸드오프 ID | CODING_HANDOFF-REQ-001 |",
                    "| 요구사항 ID | REQ-001 |",
                    "| 게이트 상태 | 완료 |",
                    "| 작성일 | 2026-07-05 |",
                    "",
                    "## 2. 테스트 통과 증거",
                    "",
                    "| 검증 명령 | 실행 일시 | 결과 | 증거 링크/로그 |",
                    "| --- | --- | --- | --- |",
                    "| `python3 -m unittest discover -s tests` | 2026-07-05 10:00 | 통과 | smoke.log |",
                    "",
                    "## 3. REVIEW_LOG 참조",
                    "",
                    "| 핸드오프 ID | REVIEW_LOG 항목 날짜 | 리뷰어 | 판정 |",
                    "| --- | --- | --- | --- |",
                    "| CODING_HANDOFF-REQ-001 | 2026-07-05 | reviewer | 통과 |",
                    "",
                    "## 4. 롤백 절차",
                    "",
                    "| 롤백 항목 | 롤백 명령 또는 절차 | 롤백 검증 명령 | 책임자 |",
                    "| --- | --- | --- | --- |",
                    "| 코드 변경 | `git revert abc123` | `python3 -m unittest discover -s tests` | reviewer |",
                    "",
                    "## 5. 릴리스 후 확인 항목",
                    "",
                    "| 확인 항목 | 확인 방법 | 기대 결과 | 확인 결과 |",
                    "| --- | --- | --- | --- |",
                    "| 핵심 기능 스모크 | smoke command | 정상 응답 | 통과 |",
                    "",
                    "## 6. 최종 게이트",
                    "",
                    "- [x] 모든 검증 명령이 통과했다.",
                    "- [x] REVIEW_LOG에 같은 핸드오프 ID의 통과 항목이 있다.",
                    "- [x] 롤백 명령과 롤백 검증 명령이 비어 있지 않다.",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_checker("all")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("REVIEW_LOG has no release-eligible entry", result.stderr)

    def test_p0_checker_fails_mixed_review_log_reference_verdicts(self) -> None:
        self.assertEqual(self.create_handoff().returncode, 0)
        fill_human_required_sections(self.handoff_path)
        write_completed_release_artifacts(self.project_root)
        release = self.project_root / "06-배포" / "RELEASE_CHECKLIST.md"
        text = release.read_text(encoding="utf-8")
        text = text.replace(
            "| CODING_HANDOFF-REQ-001 | 2026-07-05 | reviewer | 통과 |",
            "| CODING_HANDOFF-REQ-001 | 2026-07-05 | reviewer | 통과 |\n"
            "| CODING_HANDOFF-REQ-001 | 2026-07-05 | reviewer | 차단 |",
            1,
        )
        release.write_text(text, encoding="utf-8")

        result = self.run_checker("all")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("only release-eligible verdicts", result.stderr)

    def test_p0_checker_fails_stale_review_log_reference_row(self) -> None:
        self.assertEqual(self.create_handoff().returncode, 0)
        fill_human_required_sections(self.handoff_path)
        write_completed_release_artifacts(self.project_root)
        review_log = self.project_root / "08-검토" / "REVIEW_LOG.md"
        review_log.write_text(
            review_log.read_text(encoding="utf-8").replace("| 2026-07-05 | CODING_HANDOFF-REQ-001 | reviewer |", "| 2026-07-05 | CODING_HANDOFF-REQ-001 | final reviewer |", 1),
            encoding="utf-8",
        )

        result = self.run_checker("all")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("REVIEW_LOG 참조 row has no matching REVIEW_LOG entry", result.stderr)

    def test_p0_checker_passes_completed_release_with_review_log_entry(self) -> None:
        self.assertEqual(self.create_handoff().returncode, 0)
        fill_human_required_sections(self.handoff_path)
        review_log = self.project_root / "08-검토" / "REVIEW_LOG.md"
        review_log.parent.mkdir(parents=True)
        review_log.write_text(
            "\n".join(
                [
                    "# REVIEW_LOG",
                    "",
                    "| 날짜 | 핸드오프 ID | 리뷰어 | 발견 결함 | 판정 | 후속 조치 |",
                    "| --- | --- | --- | --- | --- | --- |",
                    "| 2026-07-05 | CODING_HANDOFF-REQ-001 | reviewer | 없음 | 통과 | 없음 |",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        release = self.project_root / "06-배포" / "RELEASE_CHECKLIST.md"
        release.parent.mkdir(parents=True)
        release.write_text(
            "\n".join(
                [
                    "# RELEASE_CHECKLIST",
                    "",
                    "## 1. 릴리스 식별",
                    "",
                    "| 항목 | 내용 |",
                    "| --- | --- |",
                    "| 릴리스 ID | REL-20260705-001 |",
                    "| 핸드오프 ID | CODING_HANDOFF-REQ-001 |",
                    "| 요구사항 ID | REQ-001 |",
                    "| 게이트 상태 | 완료 |",
                    "| 작성일 | 2026-07-05 |",
                    "",
                    "## 2. 테스트 통과 증거",
                    "",
                    "| 검증 명령 | 실행 일시 | 결과 | 증거 링크/로그 |",
                    "| --- | --- | --- | --- |",
                    "| `python3 -m unittest discover -s tests` | 2026-07-05 10:00 | 통과 | smoke.log |",
                    "",
                    "## 3. REVIEW_LOG 참조",
                    "",
                    "| 핸드오프 ID | REVIEW_LOG 항목 날짜 | 리뷰어 | 판정 |",
                    "| --- | --- | --- | --- |",
                    "| CODING_HANDOFF-REQ-001 | 2026-07-05 | reviewer | 통과 |",
                    "",
                    "## 4. 롤백 절차",
                    "",
                    "| 롤백 항목 | 롤백 명령 또는 절차 | 롤백 검증 명령 | 책임자 |",
                    "| --- | --- | --- | --- |",
                    "| 코드 변경 | `git revert abc123` | `python3 -m unittest discover -s tests` | reviewer |",
                    "",
                    "## 5. 릴리스 후 확인 항목",
                    "",
                    "| 확인 항목 | 확인 방법 | 기대 결과 | 확인 결과 |",
                    "| --- | --- | --- | --- |",
                    "| 핵심 기능 스모크 | smoke command | 정상 응답 | 통과 |",
                    "",
                    "## 6. 최종 게이트",
                    "",
                    "- [x] 모든 검증 명령이 통과했다.",
                    "- [x] REVIEW_LOG에 같은 핸드오프 ID의 통과 항목이 있다.",
                    "- [x] 롤백 명령과 롤백 검증 명령이 비어 있지 않다.",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_checker("all")

        self.assertEqual(result.returncode, 0, result.stderr)

class FrozenBaselineTest(unittest.TestCase):
    def test_frozen_required_documents_and_index_links_exist(self) -> None:
        required = {
            Path("templates/waterfall/00-기획/용어정의서.md"): [
                "# 용어정의서",
                "## 2. 용어 목록",
                "| 용어 | 별칭 | 정의 |",
            ],
            Path("templates/waterfall/08-검토/REVIEW_LOG.md"): [
                "# REVIEW_LOG",
                "| 날짜 | 핸드오프 ID | 리뷰어 | 발견 결함 | 판정 | 후속 조치 |",
            ],
            Path("templates/waterfall/06-배포/RELEASE_CHECKLIST.md"): [
                "# RELEASE_CHECKLIST",
                "## 4. 롤백 절차",
                "## 6. 최종 게이트",
            ],
            Path("templates/waterfall/07-유지보수/운영-RUNBOOK.md"): [
                "# 운영-RUNBOOK",
                "## 1. 무엇을 감시하나",
                "## 2. 장애 나면 무엇을 하나",
                "## 3. 끝나면 무엇을 기록하나",
            ],
        }
        index = (REPO_ROOT / "DOCUMENTATION_INDEX.md").read_text(encoding="utf-8")

        for rel, expected_markers in required.items():
            with self.subTest(path=rel.as_posix()):
                text = (REPO_ROOT / rel).read_text(encoding="utf-8")
                self.assertIn(f"./{rel.as_posix()}", index)
                for marker in expected_markers:
                    self.assertIn(marker, text)

    def test_frozen_baseline_does_not_add_forbidden_documents(self) -> None:
        forbidden_patterns = (
            r"monitoring",
            r"incident",
            r"post[_-]?mortem",
            r"rollback",
            r"^adr$",
            r"environment[_-]?variables",
            r"data[_-]?retention.*privacy",
            r"customer[_-]?support.*runbook",
        )
        waterfall_root = REPO_ROOT / "templates" / "waterfall"
        found = []
        for path in waterfall_root.rglob("*.md"):
            normalized = path.stem.lower().replace(" ", "_")
            if any(re.search(pattern, normalized) for pattern in forbidden_patterns):
                found.append(path.relative_to(waterfall_root).as_posix())

        self.assertEqual(found, [])

    def test_frozen_glossary_link_targets_include_canonical_link(self) -> None:
        targets = {
            Path("templates/waterfall/00-기획/서비스기획서.md"): "./용어정의서.md",
            Path("templates/waterfall/00-기획/비즈니스정책서.md"): "./용어정의서.md",
            Path("templates/waterfall/01-요구사항분석/요구사항명세서-SRS.md"): "../00-기획/용어정의서.md",
            Path("templates/waterfall/02-시스템설계/시스템아키텍처설계서-SAD.md"): "../00-기획/용어정의서.md",
            Path("templates/waterfall/02-시스템설계/데이터베이스설계서.md"): "../00-기획/용어정의서.md",
            Path("templates/waterfall/05-테스트/테스트계획서.md"): "../00-기획/용어정의서.md",
            Path("templates/waterfall/CLAUDE.md"): "./00-기획/용어정의서.md",
        }

        for rel, href in targets.items():
            with self.subTest(path=rel.as_posix()):
                text = (REPO_ROOT / rel).read_text(encoding="utf-8")
                self.assertIn(f"[용어정의서]({href})", text)
                self.assertTrue((REPO_ROOT / rel.parent / href).resolve().exists())

    def test_frozen_coding_handoff_required_structure_is_preserved(self) -> None:
        text = (REPO_ROOT / "templates/waterfall/04-구현/CODING_HANDOFF.md").read_text(encoding="utf-8")
        required_headings = [
            "## 구현 목표",
            "## 요구사항 ID",
            "## 관련 문서 링크",
            "## 영향 범위",
            "## 금지 변경",
            "## 계약",
            "## 구현 단계",
            "## 필수 테스트",
            "## 보안 체크",
            "## 검증 명령",
            "## 완료 기준",
            "## 롤백 메모",
        ]

        for heading in required_headings:
            with self.subTest(heading=heading):
                self.assertIn(heading, text)

    def test_frozen_p0_stage_interface_is_available(self) -> None:
        result = subprocess.run(
            [sys.executable, str(P0_CHECK), "--help"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--stage", result.stdout)
        self.assertIn("handoff", result.stdout)
        self.assertIn("release", result.stdout)
        self.assertIn("all", result.stdout)

    def test_committed_waterfall_artifact_references_exist(self) -> None:
        docs = [
            REPO_ROOT / "docs" / "waterfall" / "06-배포" / "RELEASE_CHECKLIST.md",
            REPO_ROOT / "docs" / "waterfall" / "08-검토" / "REVIEW_LOG.md",
        ]

        for doc in docs:
            text = doc.read_text(encoding="utf-8")
            for ref in sorted(set(re.findall(r"artifacts/[A-Za-z0-9_./-]+", text))):
                with self.subTest(doc=doc.relative_to(REPO_ROOT).as_posix(), ref=ref):
                    self.assertTrue((REPO_ROOT / ref).exists(), ref)

if __name__ == "__main__":
    unittest.main()
