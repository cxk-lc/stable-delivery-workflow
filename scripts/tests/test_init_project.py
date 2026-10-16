#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""init_project.py 最小回归测试（T1 / T2）

运行方式（在技能仓库根目录）:
    python -m unittest discover -s scripts/tests -v

说明：本测试为 v1.1.1 批次引入的最小防护网（迭代计划 R4）——
任何脚本改动前后均应运行，确保「完整初始化」与「不覆盖已存在文件」
两条核心行为不被破坏。完整用例（T3~T7）将在 v1.3.0 批次补齐。
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "init_project.py"


def run_init(target: Path, *extra_args: str) -> subprocess.CompletedProcess:
    """以子进程方式运行初始化脚本（显式指定语种，保证测试确定性）。"""
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(target), "--commit-lang", "简体中文", *extra_args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


class TestInitProject(unittest.TestCase):
    def test_t1_fresh_full_init(self):
        """T1 全新目录：完整初始化成功，产出全部骨架文件与首次提交。"""
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "app"
            r = run_init(target, "--name", "回归测试")
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)

            for rel in (
                "AGENTS.md",
                "docs/product-design.md",
                "docs/tech-design.md",
                "docs/acceptance-checklist.md",
                ".gitignore",
            ):
                self.assertTrue((target / rel).is_file(), msg=f"缺少骨架文件: {rel}")

            self.assertTrue((target / ".git").exists(), msg="未初始化 Git 仓库")
            log = subprocess.run(
                ["git", "-C", str(target), "rev-list", "--count", "HEAD"],
                capture_output=True,
                text=True,
            )
            self.assertGreaterEqual(int((log.stdout or "0").strip()), 1, msg="缺少首次提交")

    def test_t2_no_overwrite_existing(self):
        """T2 已有文件：不覆盖（哨兵内容保留），同时补建缺失的验收清单。"""
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "app"
            (target / "docs").mkdir(parents=True)
            sentinel_agents = "# AGENTS.md\n\n哨兵内容-不得覆盖\n"
            sentinel_product = "# 产品设计文档\n\n哨兵内容-不得覆盖\n"
            (target / "AGENTS.md").write_text(sentinel_agents, encoding="utf-8")
            (target / "docs" / "product-design.md").write_text(sentinel_product, encoding="utf-8")

            r = run_init(target)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)

            self.assertEqual(
                (target / "AGENTS.md").read_text(encoding="utf-8"), sentinel_agents,
                msg="AGENTS.md 被覆盖",
            )
            self.assertEqual(
                (target / "docs" / "product-design.md").read_text(encoding="utf-8"), sentinel_product,
                msg="product-design.md 被覆盖",
            )
            self.assertTrue(
                (target / "docs" / "acceptance-checklist.md").is_file(),
                msg="未补建缺失的验收清单",
            )


if __name__ == "__main__":
    unittest.main()
