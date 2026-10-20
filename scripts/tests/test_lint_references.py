#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lint_references.py 回归测试（L1–L5）

运行方式（技能仓库根目录）:
    python -m unittest discover -s scripts/tests -v

用例:
    L1  干净副本：全部通过
    L2  嵌套路径死链：可检出
    L3  CHANGELOG 死链：可检出
    L4  frontmatter name 非法：可检出
    L5  frontmatter name 与目录名不一致：警告但不阻断
"""
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "lint_references.py"
IGNORE = shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".pytest_cache")


def copy_skill(dst: Path) -> Path:
    shutil.copytree(ROOT, dst, ignore=IGNORE)
    return dst


def run_lint(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(root / "scripts" / "lint_references.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
    )


class TestLintReferences(unittest.TestCase):
    def test_l1_clean_copy(self):
        """L1 干净副本：R1–R3 全部通过。"""
        with tempfile.TemporaryDirectory() as td:
            root = copy_skill(Path(td) / "skill")
            r = run_lint(root)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertIn("全部通过", r.stdout)
            self.assertIn("[✓] R3", r.stdout)

    def test_l2_nested_dead_path(self):
        """L2 嵌套路径死链：不再被跳过。"""
        with tempfile.TemporaryDirectory() as td:
            root = copy_skill(Path(td) / "skill")
            with (root / "README.md").open("a", encoding="utf-8") as f:
                f.write("\n[bad](scripts/tests/does-not-exist.py)\n")
            r = run_lint(root)
            self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
            self.assertIn("scripts/tests/does-not-exist.py", r.stdout)

    def test_l3_changelog_dead_path(self):
        """L3 CHANGELOG 死链：已纳入扫描。"""
        with tempfile.TemporaryDirectory() as td:
            root = copy_skill(Path(td) / "skill")
            with (root / "CHANGELOG.md").open("a", encoding="utf-8") as f:
                f.write("\n- 旧记录：`references/does-not-exist.md`\n")
            r = run_lint(root)
            self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
            self.assertIn("references/does-not-exist.md", r.stdout)

    def test_l4_invalid_frontmatter_name(self):
        """L4 frontmatter name 非法 / description 为空：R3 失败。"""
        with tempfile.TemporaryDirectory() as td:
            root = copy_skill(Path(td) / "skill")
            skill = root / "SKILL.md"
            text = skill.read_text(encoding="utf-8").replace(
                "name: stable-delivery-workflow", "name: Bad Name", 1)
            skill.write_text(text, encoding="utf-8")
            r = run_lint(root)
            self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
            self.assertIn("[✗] R3", r.stdout)

            root2 = copy_skill(Path(td) / "skill2")
            skill2 = root2 / "SKILL.md"
            text = re.sub(r"^description:.*$", "description:", skill2.read_text(encoding="utf-8"), count=1, flags=re.M)
            skill2.write_text(text, encoding="utf-8")
            r2 = run_lint(root2)
            self.assertEqual(r2.returncode, 1, msg=r2.stdout + r2.stderr)
            self.assertIn("description 为空", r2.stdout)

    def test_l5_directory_name_mismatch_warns_only(self):
        """L5 name 与目录名不一致：警告但不阻断。"""
        with tempfile.TemporaryDirectory() as td:
            root = copy_skill(Path(td) / "custom-folder-name")
            r = run_lint(root)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertIn("[!] R3 目录名", r.stdout)


if __name__ == "__main__":
    unittest.main()
