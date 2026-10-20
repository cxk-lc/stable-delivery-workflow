#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_release_zip.py 回归测试（B1）

运行方式（技能仓库根目录）:
    python -m unittest discover -s scripts/tests -v

用例:
    B1  发布包固定排除 .gitignore，顶层目录为包名，且不含 .git / .github
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build_release_zip.py"
IGNORE = shutil.ignore_patterns(".git", ".github", "__pycache__", "*.pyc", ".pytest_cache")


class TestBuildReleaseZip(unittest.TestCase):
    def test_b1_excludes_gitignore(self):
        """B1 发布包：不含 .gitignore，顶层目录为包名。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "skill"
            shutil.copytree(ROOT, root, ignore=IGNORE)
            output = Path(td) / "stable-delivery-workflow.zip"

            r = subprocess.run(
                [sys.executable, str(root / "scripts" / "build_release_zip.py"),
                 "--output", str(output)],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
            )
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertTrue(output.is_file())
            self.assertIn("SHA256:", r.stdout)

            with zipfile.ZipFile(output) as z:
                names = z.namelist()

            self.assertTrue(names)
            self.assertTrue(all(n.startswith("stable-delivery-workflow/") for n in names))
            self.assertIn("stable-delivery-workflow/SKILL.md", names)
            self.assertFalse(any(n.endswith("/.gitignore") for n in names),
                             msg="发布包不应包含 .gitignore")
            self.assertFalse(any(n.startswith("stable-delivery-workflow/.git/") for n in names))
            self.assertFalse(any(n.startswith("stable-delivery-workflow/.github/") for n in names))


if __name__ == "__main__":
    unittest.main()
