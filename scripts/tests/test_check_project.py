#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_project.py 回归测试（C1–C5）

运行方式（技能仓库根目录）:
    python -m unittest discover -s scripts/tests -v

用例:
    C1  全新初始化：D1 未通过、A2/V2 以提示项出现
    C2  填写文档/命令：A2 纳入检查并通过
    C3  已跟踪文件有未提交改动：G3 失败
    C4  英文 AGENTS.md：A1 仍能识别 commit/test/language
    C5  技术方案已填写但命令缺失：A2 失败
    C6  验收开始后：V2 纳入检查并通过
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "check_project.py"
INIT = Path(__file__).resolve().parents[1] / "init_project.py"


def run_script(script: Path, target: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), str(target), *extra],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
    )


def init_project(target: Path) -> None:
    r = run_script(INIT, target, "--name", "检查器测试", "--commit-lang", "简体中文")
    if r.returncode != 0:
        raise AssertionError(r.stdout + r.stderr)


def commit_all(target: Path, message: str = "test: update") -> None:
    subprocess.run(["git", "-C", str(target), "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", str(target), "-c", "user.name=T", "-c", "user.email=t@t",
                    "commit", "-m", message], capture_output=True)


def fill_docs(target: Path, commands: bool = True) -> None:
    product = target / "docs" / "product-design.md"
    text = product.read_text(encoding="utf-8").replace("| | | 必须 |", "| 记一笔 | 记录收支 | 必须 |")
    product.write_text(text, encoding="utf-8")

    tech = target / "docs" / "tech-design.md"
    text = tech.read_text(encoding="utf-8")
    text = (text.replace("| 语言 | | |", "| 语言 | TypeScript | 生态成熟 |")
                .replace("| 框架 | | |", "| 框架 | React | 团队熟悉 |")
                .replace("| 构建工具 | | |", "| 构建工具 | Vite | 启动快 |"))
    tech.write_text(text, encoding="utf-8")

    if commands:
        agents = target / "AGENTS.md"
        text = agents.read_text(encoding="utf-8")
        text = (text.replace("运行命令：（如 npm start，填写后更新）", "运行命令：npm run dev")
                    .replace("测试命令：（如 npm test，填写后更新）", "测试命令：npm test"))
        agents.write_text(text, encoding="utf-8")


class TestCheckProject(unittest.TestCase):
    def test_c1_fresh_project(self):
        """C1 全新初始化：D1 未通过，A2/V2 以提示项出现。"""
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "app"
            init_project(target)
            r = run_script(SCRIPT, target)
            self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
            self.assertIn("[✗] D1", r.stdout)
            self.assertIn("[ℹ] A2", r.stdout)
            self.assertIn("[ℹ] V2", r.stdout)
            self.assertIn("刚初始化的项目 D1 未通过属预期", r.stdout)

    def test_c2_filled_docs_enable_a2(self):
        """C2 填写文档与命令：A2 纳入检查并通过。"""
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "app"
            init_project(target)
            fill_docs(target)
            commit_all(target)
            r = run_script(SCRIPT, target)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertIn("[✓] A2", r.stdout)
            self.assertIn("通过 7/7", r.stdout)

    def test_c3_dirty_tracked_file_fails_g3(self):
        """C3 已跟踪文件有未提交改动：G3 失败。"""
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "app"
            init_project(target)
            with (target / "AGENTS.md").open("a", encoding="utf-8") as f:
                f.write("\n- wip\n")
            r = run_script(SCRIPT, target)
            self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
            self.assertIn("[✗] G3", r.stdout)
            self.assertIn("未提交: AGENTS.md", r.stdout)

    def test_c4_english_agents_rules(self):
        """C4 英文 AGENTS.md：A1 仍能识别 commit/test/language。"""
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "app"
            init_project(target)
            (target / "AGENTS.md").write_text(
                "# AGENTS.md\n\n"
                "1. Commit every change.\n"
                "2. Update tests and ensure they pass.\n"
                "3. Use English for all commit messages.\n\n"
                "- Run command: npm test\n"
                "- Test command: npm test\n",
                encoding="utf-8",
            )
            commit_all(target)
            r = run_script(SCRIPT, target)
            self.assertIn("[✓] A1", r.stdout, msg=r.stdout + r.stderr)

    def test_c5_a2_fails_when_commands_missing(self):
        """C5 技术方案已填写但运行/测试命令缺失：A2 失败。"""
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "app"
            init_project(target)
            fill_docs(target, commands=False)
            commit_all(target)
            r = run_script(SCRIPT, target)
            self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
            self.assertIn("[✗] A2", r.stdout)

    def test_c6_acceptance_conclusion(self):
        """C6 验收开始后：V2 纳入检查并通过。"""
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "app"
            init_project(target)
            checklist = target / "docs" / "acceptance-checklist.md"
            text = checklist.read_text(encoding="utf-8")
            text = text.replace("- [ ] 按文档中的运行命令可正常启动",
                                "- [x] 按文档中的运行命令可正常启动")
            text = text.replace("- 结论：通过 / 有条件通过 / 不通过", "- 结论：通过")
            text = text.replace("- 验收人 / 日期：", "- 验收人 / 日期：测试者 / 2026-10-20")
            checklist.write_text(text, encoding="utf-8")
            commit_all(target)
            r = run_script(SCRIPT, target)
            self.assertIn("[✓] V2", r.stdout, msg=r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
