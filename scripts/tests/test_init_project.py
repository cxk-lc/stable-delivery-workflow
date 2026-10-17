#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""init_project.py 回归测试（T1–T8）

运行方式（技能仓库根目录）:
    python -m unittest discover -s scripts/tests -v

用例:
    T1  全新目录：完整初始化 + 5 件套 + 首次提交
    T2  已有文件：不覆盖（哨兵保留）+ 补建缺失的验收清单
    T3  已有 Git 仓库：不重复 init、不破坏历史
    T4  语种优先级：手动指定 > 交互输入 > 系统检测 > 简体中文（进程内单元测试）
    T5  非交互（stdin 非 tty）：不阻塞，直接采用默认值
    T6  参数组合：--no-commit / --commit-msg / --remote
    T7  assets 缺失：降级兜底，产物与正常路径逐字一致
    T8  --dry-run：不落盘，输出"将执行"步骤
"""
import builtins
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "init_project.py"
SKILL_ROOT = SCRIPT.parents[1]


def run_init(target: Path, *extra_args: str, stdin=None) -> subprocess.CompletedProcess:
    """以子进程方式运行初始化脚本（显式指定语种，保证测试确定性）。"""
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(target), "--commit-lang", "简体中文", *extra_args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        stdin=stdin,
    )


def git_out(target: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(target), *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "").strip()


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
            self.assertGreaterEqual(int(git_out(target, "rev-list", "--count", "HEAD") or 0), 1,
                                    msg="缺少首次提交")

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
            self.assertEqual((target / "AGENTS.md").read_text(encoding="utf-8"), sentinel_agents,
                             msg="AGENTS.md 被覆盖")
            self.assertEqual((target / "docs" / "product-design.md").read_text(encoding="utf-8"),
                             sentinel_product, msg="product-design.md 被覆盖")
            self.assertTrue((target / "docs" / "acceptance-checklist.md").is_file(),
                            msg="未补建缺失的验收清单")

    def test_t3_existing_repo(self):
        """T3 已有 Git 仓库：不重复 init，不破坏历史，新增提交。"""
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "app"
            target.mkdir(parents=True)
            subprocess.run(["git", "init", "-b", "main"], cwd=target, capture_output=True)
            subprocess.run(["git", "config", "user.name", "T"], cwd=target, capture_output=True)
            subprocess.run(["git", "config", "user.email", "t@t"], cwd=target, capture_output=True)
            (target / "README.md").write_text("原有内容", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=target, capture_output=True)
            subprocess.run(["git", "commit", "-m", "initial-commit"], cwd=target, capture_output=True)
            self.assertEqual(git_out(target, "rev-list", "--count", "HEAD"), "1")

            r = run_init(target)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertGreaterEqual(int(git_out(target, "rev-list", "--count", "HEAD") or 0), 2,
                                    msg="未在现有仓库上新增提交")
            self.assertIn("initial-commit", git_out(target, "log", "--oneline"),
                          msg="原有历史丢失")
            self.assertTrue((target / "AGENTS.md").is_file())

    def test_t4_language_priority(self):
        """T4 语种优先级：手动指定 > 交互输入 > 系统检测 > 简体中文。"""
        spec = importlib.util.spec_from_file_location("init_project_under_test", SCRIPT)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)

        class FakeTTY:
            def isatty(self):
                return True

        class FakePipe:
            def isatty(self):
                return False

        orig_stdin, orig_input = sys.stdin, builtins.input
        try:
            # 1) 手动指定最优先（即使系统检测可用）
            self.assertEqual(m.resolve_commit_lang("English")[0], "English")
            # 2) 交互输入次之（模拟 TTY）
            sys.stdin = FakeTTY()
            builtins.input = lambda prompt="": " 繁體中文 "
            self.assertEqual(m.resolve_commit_lang(None)[0], "繁體中文")
            # 3) 交互直接回车 → 采用系统检测值
            m.detect_system_language = lambda: ("English", "mock")
            builtins.input = lambda prompt="": ""
            self.assertEqual(m.resolve_commit_lang(None)[0], "English")
            # 4) 系统检测失败 → 回退简体中文
            m.detect_system_language = lambda: (None, None)
            self.assertEqual(m.resolve_commit_lang(None)[0], "简体中文")
            # 5) 非交互（非 tty）→ 不提示，直接采用检测值
            sys.stdin = FakePipe()
            m.detect_system_language = lambda: ("English", "mock")
            self.assertEqual(m.resolve_commit_lang(None)[0], "English")
        finally:
            sys.stdin, builtins.input = orig_stdin, orig_input

    def test_t5_non_interactive(self):
        """T5 非交互（stdin 非 tty）：不阻塞、不提示，直接采用默认值。"""
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "app"
            r = subprocess.run([sys.executable, str(SCRIPT), str(target)],
                               stdin=subprocess.DEVNULL, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=120)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            agents = (target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("统一使用", agents, msg="AGENTS.md 未写入语种规则")

    def test_t6_flag_combinations(self):
        """T6 参数组合：--no-commit / --commit-msg / --remote。"""
        with tempfile.TemporaryDirectory() as td:
            # --no-commit：搭建环境但不提交
            p1 = Path(td) / "a"
            r = run_init(p1, "--no-commit")
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertTrue((p1 / "AGENTS.md").is_file())
            self.assertEqual(git_out(p1, "rev-list", "--count", "HEAD") or "0", "0")

            # --commit-msg：自定义首次提交信息
            p2 = Path(td) / "b"
            r = run_init(p2, "--commit-msg", "chore: 自定义首提")
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertEqual(git_out(p2, "log", "-1", "--pretty=%s"), "chore: 自定义首提")

            # --remote：关联远端
            p3 = Path(td) / "c"
            r = run_init(p3, "--remote", "https://example.com/x.git")
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertIn("origin", git_out(p3, "remote"))

    def test_t7_assets_missing_fallback(self):
        """T7 assets 缺失：降级兜底，产物与正常路径逐字一致。"""
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            normal = td / "normal" / "skill"
            (normal / "scripts").mkdir(parents=True)
            shutil.copytree(SKILL_ROOT / "assets", normal / "assets")
            shutil.copy(SCRIPT, normal / "scripts" / "init_project.py")

            degrade = td / "degrade" / "skill"
            (degrade / "scripts").mkdir(parents=True)
            shutil.copy(SCRIPT, degrade / "scripts" / "init_project.py")

            projects = {}
            for name, script in (("normal", normal / "scripts" / "init_project.py"),
                                 ("degrade", degrade / "scripts" / "init_project.py")):
                proj = td / f"{name}_proj"
                r = subprocess.run([sys.executable, str(script), str(proj),
                                    "--name", "一致性", "--commit-lang", "简体中文"],
                                   capture_output=True, text=True, encoding="utf-8",
                                   errors="replace", timeout=120)
                self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
                projects[name] = proj

            for rel in ("AGENTS.md", "docs/product-design.md", "docs/tech-design.md",
                        "docs/acceptance-checklist.md", ".gitignore"):
                self.assertEqual((projects["normal"] / rel).read_bytes(),
                                 (projects["degrade"] / rel).read_bytes(), msg=f"双路径不一致: {rel}")

    def test_t8_dry_run(self):
        """T8 --dry-run：不落盘，仅输出将执行步骤。"""
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "app"
            r = run_init(target, "--dry-run")
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertIn("演练模式", r.stdout)
            self.assertIn("将", r.stdout)
            self.assertFalse(target.exists(), msg="dry-run 不应创建目录")

            target.mkdir()
            r2 = run_init(target, "--dry-run")
            self.assertEqual(r2.returncode, 0, msg=r2.stdout + r2.stderr)
            self.assertEqual(list(target.iterdir()), [], msg="dry-run 不应写入任何文件")
            self.assertFalse((target / ".git").exists(), msg="dry-run 不应初始化仓库")


if __name__ == "__main__":
    unittest.main()
