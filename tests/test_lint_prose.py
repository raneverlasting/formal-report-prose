#!/usr/bin/env python3
"""Unit tests for lint_prose.py."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import lint_prose  # noqa: E402


class LintTextTests(unittest.TestCase):
    def errors(self, text: str) -> list[lint_prose.Finding]:
        return [f for f in lint_prose.lint_text(text) if f.severity == "error"]

    def test_clean_formal_text_has_no_errors(self) -> None:
        text = (
            "第三季度收入 2.4 亿元，同比增长 18%。毛利额 0.86 亿元，"
            "与上年同期的 0.85 亿元基本持平。毛利率从 42% 降至 36%，"
            "销售费用增长 31%，快于收入增速。下一阶段修复单位经济模型。"
        )
        self.assertEqual(self.errors(text), [])

    def test_detects_rhetorical_contrast(self) -> None:
        findings = self.errors("这次改版的关键，不是换界面，而是重做权限模型。")
        self.assertTrue(any(f.rule_id == "contrast.buzhi" for f in findings))

    def test_detects_erfei(self) -> None:
        findings = self.errors("收入增长由投入驱动，而非效率改善。")
        self.assertTrue(any(f.rule_id == "contrast.erfei" for f in findings))

    def test_detects_boundary_negation(self) -> None:
        findings = self.errors("这个方案不能看作最终版本。")
        self.assertTrue(any(f.rule_id == "boundary.kanzuo" for f in findings))

    def test_detects_boundary_with_ba(self) -> None:
        findings = self.errors("不能简单地把试点结果看作全面推广的依据。")
        self.assertTrue(any(f.rule_id == "boundary.kanzuo" for f in findings))

    def test_detects_chat_filler(self) -> None:
        findings = self.errors("好问题！当然可以。希望这对你有帮助。")
        ids = {f.rule_id for f in findings}
        self.assertIn("chat.sycophancy", ids)

    def test_detects_generic_closer(self) -> None:
        findings = self.errors("综上所述，这次改革意义重大，未来可期。")
        ids = {f.rule_id for f in findings}
        self.assertIn("closer.generic", ids)

    def test_ignores_fenced_code(self) -> None:
        text = "示例：\n```\n不是 A，而是 B。\n```\n正文结束。"
        self.assertEqual(self.errors(text), [])

    def test_ignores_inline_code(self) -> None:
        text = "写作时禁用 `不是 A，而是 B` 这类句式。"
        self.assertEqual(self.errors(text), [])

    def test_skip_quotes(self) -> None:
        text = "> 不是 A，而是 B。\n\n正文没有这个问题。"
        self.assertTrue(
            any(
                f.rule_id == "contrast.buzhi"
                for f in lint_prose.lint_text(text)
            )
        )
        skipped = [
            f
            for f in lint_prose.lint_text(text, skip_quotes=True)
            if f.severity == "error"
        ]
        self.assertEqual(skipped, [])

    def test_reports_line_and_column(self) -> None:
        findings = [f for f in lint_prose.lint_text("第一行。\n不是 A，而是 B。") if f.severity == "error"]
        self.assertTrue(findings)
        self.assertEqual(findings[0].line, 2)
        self.assertGreaterEqual(findings[0].column, 1)


class CliTests(unittest.TestCase):
    def run_cli(self, text: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "lint_prose.py"), "-", *args],
            input=text,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )

    def test_json_output(self) -> None:
        result = self.run_cli("不是 A，而是 B。", "--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["errors"], 1)
        self.assertTrue(payload["findings"])

    def test_strict_fails_on_warning(self) -> None:
        text = "综上所述，项目已经完成。"
        relaxed = self.run_cli(text)
        strict = self.run_cli(text, "--strict")
        self.assertEqual(relaxed.returncode, 0)
        self.assertEqual(strict.returncode, 1)

    def test_clean_text_exits_zero(self) -> None:
        result = self.run_cli("第三季度收入 2.4 亿元，同比增长 18%。")
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
