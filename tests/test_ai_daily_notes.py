from __future__ import annotations

import configparser
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
AI_DAILY_PATH = REPO_ROOT / "scripts" / "ai-news-collector" / "ai-daily.py"


def load_ai_daily():
    spec = importlib.util.spec_from_file_location("ai_daily", AI_DAILY_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class AiDailyNotesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_ai_daily()

    def test_get_notes_dir_uses_configured_relative_path(self) -> None:
        cfg = configparser.ConfigParser()
        cfg.add_section("저장")
        cfg.set("저장", "notes_dir", "tmp/notes")

        self.assertEqual(self.module.get_notes_dir(cfg), self.module.PROJECT_DIR / "tmp" / "notes")
    def test_committed_config_sets_project_notes_dir(self) -> None:
        cfg = self.module.load_config()

        self.assertEqual(
            self.module.get_notes_dir(cfg),
            self.module.PROJECT_DIR / "docs" / "news" / "ai-notes",
        )

    def test_save_to_notes_uses_configured_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "brief.md"
            source.write_text("brief", encoding="utf-8")
            notes_dir = root / "notes"

            result = self.module.save_to_notes(source, "2026-07-05", notes_dir=notes_dir)

            self.assertEqual(result, notes_dir / "AIB-brief_20260705.md")
            self.assertEqual(result.read_text(encoding="utf-8"), "brief")

    def test_save_to_notes_warns_and_skips_when_path_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "brief.md"
            source.write_text("brief", encoding="utf-8")
            with mock.patch.object(self.module.Path, "mkdir", side_effect=OSError("denied")):
                with mock.patch.object(self.module, "status") as status_mock:
                    result = self.module.save_to_notes(source, "2026-07-05", notes_dir=Path(tmp) / "notes")

            self.assertIsNone(result)
            status_mock.assert_called_once()
            self.assertEqual(status_mock.call_args.args[0], "WARNING")
            self.assertIn("노트 저장 건너뜀", status_mock.call_args.args[1])

    def test_no_notes_skips_all_note_copies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            brief = root / "brief.md"
            thread = root / "thread.md"
            brief.write_text("brief", encoding="utf-8")
            thread.write_text("thread", encoding="utf-8")
            with mock.patch.object(self.module, "save_to_notes") as save_mock:
                with mock.patch.object(self.module, "status"):
                    result = self.module.save_notes_outputs(brief, thread, "2026-07-05", no_notes=True)

            self.assertEqual(result, [])
            save_mock.assert_not_called()

    def test_main_wires_no_notes_to_save_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "brief.md"
            output.write_text("## 1. item\ncontent\n", encoding="utf-8")
            thread = root / "brief_thread.md"
            info = {
                "full_date": "2026-07-05",
                "filename": "brief.md",
                "output_path": output,
                "version": 1,
                "base_dir": root,
                "ymd": "260705",
            }
            with mock.patch.object(self.module.sys, "argv", ["ai-daily.py", "--no-notes", "--no-git"]):
                with mock.patch.object(self.module, "get_output_info", return_value=info), \
                    mock.patch.object(self.module, "build_prompt", return_value="prompt"), \
                    mock.patch.object(self.module, "check_kimi_cli", return_value=True), \
                    mock.patch.object(self.module, "run_kimi_cli", return_value=0), \
                    mock.patch.object(self.module, "validate_output", return_value=([], [])), \
                    mock.patch.object(self.module, "split_articles", return_value=(root / "articles", [])), \
                    mock.patch.object(self.module, "generate_thread_summary", return_value=thread), \
                    mock.patch.object(self.module, "get_notes_dir", return_value=root / "notes"), \
                    mock.patch.object(self.module, "save_notes_outputs", return_value=[]) as save_outputs_mock, \
                    mock.patch.object(self.module, "cprint"), \
                    mock.patch.object(self.module, "status"), \
                    mock.patch("builtins.input", return_value="n"):
                    result = self.module.main()

            self.assertEqual(result, 0)
            save_outputs_mock.assert_called_once_with(output, thread, "2026-07-05", no_notes=True, notes_dir=root / "notes")


if __name__ == "__main__":
    unittest.main()
