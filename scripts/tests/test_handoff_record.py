#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""handoff_record.py 回归测试（HR1–HR9）

运行方式（技能仓库根目录）:
    python -m unittest discover -s scripts/tests -v

用例:
    HR1  新项目：init 生成七节框架，未完成事项取自 MVP，模式 new-project，钩子安装
    HR2  新会话：仅依据项目目录与 Git 历史，模式 existing-new-session
    HR3  非新会话：合并 --context 摘要；缺上下文拒绝，新会话模式拒绝上下文
    HR4  提交门禁：未更新/未校验拦截；记录暂存或 --stamp 放行；HEAD 变化后签失效
    HR5  结构校验：缺小节 / 占位符被检出
    HR6  幂等与保留：重复刷新不重复条目，人工勾选与决策保留
    HR7  模板缺失降级：兜底产物与 assets 模板路径逐字一致
    HR8  钩子安全：不覆盖自定义钩子、--force 备份替换、真实 commit 被拦截后放行
    HR9  演练与重建：--dry-run 不落盘；init 已存在转刷新，--force 才重建
    HR10 统一框架：三种场景输出完全相同的小节结构（九节，顺序一致）
    HR11 模板残缺：生成结果未通过结构校验时中止写入，不落盘
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "handoff_record.py"
INIT = Path(__file__).resolve().parents[1] / "init_project.py"
SKILL_ROOT = SCRIPT.parents[1]

PRODUCT_ROWS = "| 记一笔 | 记录收支流水 | 必须 |\n| 月度报表 | 按分类汇总 | 必须 |"


def run_handoff(target, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, str(target)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
    )


def run_init(target, *extra):
    return subprocess.run(
        [sys.executable, str(INIT), str(target), "--name", "交接测试",
         "--commit-lang", "简体中文", *extra],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
    )


def git(target, *args):
    return subprocess.run(
        ["git", "-c", "user.name=T", "-c", "user.email=t@t", "-C", str(target), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
    )


def make_project(td, fill=True):
    target = Path(td) / "app"
    r = run_init(target)
    if r.returncode != 0:
        raise AssertionError(r.stdout + r.stderr)
    if fill:
        product = target / "docs" / "product-design.md"
        text = product.read_text(encoding="utf-8")
        text = text.replace("| | | 必须 |", PRODUCT_ROWS, 1)
        product.write_text(text, encoding="utf-8")
        tech = target / "docs" / "tech-design.md"
        text = tech.read_text(encoding="utf-8")
        text = (text.replace("| 语言 | | |", "| 语言 | Python | 团队熟悉 |")
                    .replace("| 框架 | | |", "| 框架 | FastAPI | 轻量 |")
                    .replace("| 构建工具 | | |", "| 构建工具 | 无 | 脚本即可 |"))
        tech.write_text(text, encoding="utf-8")
    return target


def write_context(td):
    path = Path(td) / "context.md"
    path.write_text(
        "## 已完成内容\n- 已完成登录与列表页\n\n"
        "## 关键决策\n- 数据先本地存储，暂不接后端\n\n"
        "## 风险或阻塞\n- 时区处理方案未定\n\n"
        "## 下一步计划\n1. 补齐月度报表\n2. 补充边界用例测试\n",
        encoding="utf-8",
    )
    return path


def record_path(target):
    return target / "docs" / "handoff-record.md"


def headings_of(text):
    return re.findall(r"^##[ \t]+(?!#)(.+?)\s*$", text, re.M)


class TestHandoffRecord(unittest.TestCase):
    def test_hr1_new_project(self):
        """HR1 新项目：七节齐全、MVP 条目、new-project、钩子安装。"""
        with tempfile.TemporaryDirectory() as td:
            target = make_project(td)
            r = run_handoff(target, "init", "--mode", "new-project")
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            text = record_path(target).read_text(encoding="utf-8")
            for title in ("已完成内容", "变更范围", "关键决策", "未完成事项",
                          "风险或阻塞", "下一步计划", "关联设计文档"):
                self.assertIn(title, text, msg=f"缺少小节: {title}")
            self.assertIn("mode: new-project", text)
            self.assertIn("记一笔", text)
            self.assertIn("尚未开始", text)
            self.assertIn("Python", text, msg="技术栈未写入关键决策")
            self.assertTrue((target / ".git" / "hooks" / "pre-commit").is_file(),
                            msg="未安装 pre-commit 钩子")
            self.assertIn("handoff-record gate",
                          (target / ".git" / "hooks" / "pre-commit").read_text(encoding="utf-8"))

            # 重复 init（auto 判定）不应把新项目改判为已有项目
            again = run_handoff(target, "init", "--no-hook")
            self.assertEqual(again.returncode, 0, msg=again.stdout + again.stderr)
            self.assertIn("mode: new-project",
                          record_path(target).read_text(encoding="utf-8"),
                          msg="记录已存在不应参与场景判定")

    def test_hr2_new_session_uses_directory_only(self):
        """HR2 新会话：仅目录与 Git 历史，不含上下文措辞。"""
        with tempfile.TemporaryDirectory() as td:
            target = make_project(td)
            (target / "app.py").write_text("print('hi')\n", encoding="utf-8")
            git(target, "add", "-A")
            git(target, "commit", "-m", "feat: 初始实现")
            r = run_handoff(target, "update", "--mode", "new-session", "--no-hook")
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            text = record_path(target).read_text(encoding="utf-8")
            self.assertIn("mode: existing-new-session", text)
            self.assertIn("已有项目 · 新会话", text)
            self.assertIn("feat: 初始实现", text, msg="未从 Git 历史提取已完成项")
            self.assertIn("仅依据项目目录与 Git 历史", text)
            self.assertNotIn("非新会话", text)

            # 已有项目 + 无上下文：auto 应判为「新会话」
            auto = run_handoff(target, "update", "--no-hook")
            self.assertEqual(auto.returncode, 0, msg=auto.stdout + auto.stderr)
            self.assertIn("mode: existing-new-session",
                          record_path(target).read_text(encoding="utf-8"))

            ctx = write_context(td)
            bad = run_handoff(target, "update", "--mode", "new-session", "--context", str(ctx))
            self.assertEqual(bad.returncode, 1)
            self.assertIn("不接受 --context", bad.stdout)

    def test_hr3_continue_merges_context(self):
        """HR3 非新会话：合并上下文摘要；缺上下文时拒绝。"""
        with tempfile.TemporaryDirectory() as td:
            target = make_project(td)
            (target / "app.py").write_text("print('hi')\n", encoding="utf-8")
            git(target, "add", "-A")
            git(target, "commit", "-m", "feat: 初始实现")

            missing = run_handoff(target, "update", "--mode", "continue")
            self.assertEqual(missing.returncode, 1)
            self.assertIn("必须提供 --context", missing.stdout)

            ctx = write_context(td)
            r = run_handoff(target, "update", "--mode", "continue",
                            "--context", str(ctx), "--no-hook")
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            text = record_path(target).read_text(encoding="utf-8")
            self.assertIn("mode: existing-continue", text)
            self.assertIn("已有项目 · 非新会话", text)
            self.assertIn("已完成登录与列表页", text)
            self.assertIn("数据先本地存储", text)
            self.assertIn("时区处理方案未定", text)
            self.assertIn("补齐月度报表", text)

            # 已有项目 + 提供上下文：auto 应判为「非新会话」
            auto = run_handoff(target, "update", "--context", str(ctx), "--no-hook")
            self.assertEqual(auto.returncode, 0, msg=auto.stdout + auto.stderr)
            self.assertIn("mode: existing-continue",
                          record_path(target).read_text(encoding="utf-8"))

    def test_hr4_commit_gate(self):
        """HR4 提交门禁：未更新/未校验拦截；暂存记录或校验签放行；签按 HEAD 失效。"""
        with tempfile.TemporaryDirectory() as td:
            target = make_project(td)
            run_handoff(target, "init", "--mode", "new-project")
            git(target, "add", "-A")
            ok = git(target, "commit", "-m", "docs: 建立交接记录")
            self.assertEqual(ok.returncode, 0, msg=ok.stdout + ok.stderr)

            (target / "app.py").write_text("print('hi')\n", encoding="utf-8")
            git(target, "add", "app.py")
            blocked = run_handoff(target, "check", "--staged")
            self.assertEqual(blocked.returncode, 1, msg=blocked.stdout)
            self.assertIn("交接记录未更新", blocked.stdout)

            stamp = run_handoff(target, "check", "--stamp")
            self.assertEqual(stamp.returncode, 0, msg=stamp.stdout + stamp.stderr)
            passed = run_handoff(target, "check", "--staged")
            self.assertEqual(passed.returncode, 0, msg=passed.stdout)
            self.assertIn("已执行校验", passed.stdout)

            commit = git(target, "commit", "-m", "feat: 新增入口")
            self.assertEqual(commit.returncode, 0, msg=commit.stdout + commit.stderr)

            (target / "lib.py").write_text("X = 1\n", encoding="utf-8")
            git(target, "add", "lib.py")
            expired = run_handoff(target, "check", "--staged")
            self.assertEqual(expired.returncode, 1, msg="旧校验签不应放行新提交")

            upd = run_handoff(target, "update", "--mode", "new-session", "--no-hook")
            self.assertEqual(upd.returncode, 0, msg=upd.stdout + upd.stderr)
            git(target, "add", "docs/handoff-record.md")
            updated = run_handoff(target, "check", "--staged")
            self.assertEqual(updated.returncode, 0, msg=updated.stdout)
            self.assertIn("已随本次提交更新", updated.stdout)

    def test_hr5_structure_validation(self):
        """HR5 结构校验：缺小节与占位符被检出。"""
        with tempfile.TemporaryDirectory() as td:
            target = make_project(td)
            run_handoff(target, "init", "--mode", "new-project", "--no-hook")
            path = record_path(target)

            broken = re.sub(r"## 5\. 风险或阻塞.*?(?=## 6\.)", "", path.read_text(encoding="utf-8"), flags=re.S)
            path.write_text(broken, encoding="utf-8")
            r = run_handoff(target, "check")
            self.assertEqual(r.returncode, 1)
            self.assertIn("缺少小节：风险或阻塞", r.stdout)

            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "## 3. 关键决策\n", "## 3. 关键决策\n\n- 待补充\n"),
                encoding="utf-8",
            )
            r2 = run_handoff(target, "check")
            self.assertEqual(r2.returncode, 1)
            self.assertIn("未填写占位", r2.stdout)

    def test_hr6_idempotent_and_preserve(self):
        """HR6 幂等与保留：重复刷新不重复条目，人工勾选/决策保留。"""
        with tempfile.TemporaryDirectory() as td:
            target = make_project(td)
            run_handoff(target, "init", "--mode", "new-project", "--no-hook")
            path = record_path(target)
            text = path.read_text(encoding="utf-8")
            text = text.replace("- [ ] 记一笔", "- [x] 记一笔")
            text = text.replace("- 语言：Python（团队熟悉）",
                                "- 语言：Python（团队熟悉）\n- 自定决策：先做本地版")
            path.write_text(text, encoding="utf-8")

            for _ in range(2):
                r = run_handoff(target, "update", "--mode", "new-session", "--no-hook")
                self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)

            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count("- [x] 记一笔"), 1, msg="人工勾选被丢失或重复")
            self.assertEqual(text.count("- [ ] 记一笔"), 0, msg="已勾选条目被重置")
            self.assertEqual(text.count("自定决策：先做本地版"), 1, msg="人工决策被重复/丢失")
            self.assertEqual(len(re.findall(r"· 刷新记录（按目录与设计文档重新取证）", text)), 1,
                             msg="同一 HEAD 的重复刷新不应重复记流水")

    def test_hr7_template_fallback_parity(self):
        """HR7 模板缺失降级：产物与 assets 路径逐字一致。"""
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            normal = td / "normal"
            degrade = td / "degrade"
            (normal / "scripts").mkdir(parents=True)
            shutil.copytree(SKILL_ROOT / "assets", normal / "assets")
            shutil.copy(SCRIPT, normal / "scripts" / "handoff_record.py")
            (degrade / "scripts").mkdir(parents=True)
            shutil.copy(SCRIPT, degrade / "scripts" / "handoff_record.py")

            outputs = {}
            for name, script in (("normal", normal / "scripts" / "handoff_record.py"),
                                 ("degrade", degrade / "scripts" / "handoff_record.py")):
                base = td / (name + "-proj")
                base.mkdir()
                target = make_project(base)
                r = subprocess.run(
                    [sys.executable, str(script), "update", str(target),
                     "--mode", "new-project", "--no-hook"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=120,
                )
                self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
                outputs[name] = record_path(target).read_text(encoding="utf-8")

            def normalize(text):
                text = re.sub(r"^updated_at:.*$", "", text, flags=re.M)
                text = re.sub(r"^head:.*$", "", text, flags=re.M)
                return re.sub(r"\b[0-9a-f]{7,40}\b", "<hash>", text)

            self.assertEqual(normalize(outputs["normal"]), normalize(outputs["degrade"]),
                             msg="兜底模板与 assets 模板产物不一致")

    def test_hr8_hook_safety_and_real_commit(self):
        """HR8 钩子安全：不覆盖自定义钩子；--force 备份替换；真实 commit 被拦截后可放行。"""
        with tempfile.TemporaryDirectory() as td:
            target = make_project(td)
            hooks = target / ".git" / "hooks"
            hooks.mkdir(parents=True, exist_ok=True)
            custom = hooks / "pre-commit"
            custom.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            try:
                os.chmod(custom, 0o755)
            except OSError:
                pass

            r = run_handoff(target, "init", "--mode", "new-project")
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertIn("未覆盖", r.stdout)
            self.assertEqual(custom.read_text(encoding="utf-8"), "#!/bin/sh\nexit 0\n")

            forced = run_handoff(target, "install-hook", "--force")
            self.assertEqual(forced.returncode, 0, msg=forced.stdout + forced.stderr)
            self.assertIn("handoff-record gate", custom.read_text(encoding="utf-8"))
            backups = list(hooks.glob("pre-commit.bak.*"))
            self.assertTrue(backups, msg="--force 未备份原钩子")

            git(target, "add", "-A")
            git(target, "reset", "--", "docs/handoff-record.md")
            (target / "app.py").write_text("print('hi')\n", encoding="utf-8")
            git(target, "add", "app.py")
            blocked = git(target, "commit", "-m", "feat: 未更新记录")
            self.assertNotEqual(blocked.returncode, 0, msg="钩子未拦截未更新记录的提交")
            self.assertIn("提交门禁", blocked.stdout + blocked.stderr)

            stamp = run_handoff(target, "check", "--stamp")
            self.assertEqual(stamp.returncode, 0, msg=stamp.stdout + stamp.stderr)
            passed = git(target, "commit", "-m", "feat: 校验后提交")
            self.assertEqual(passed.returncode, 0, msg=passed.stdout + passed.stderr)

    def test_hr9_dry_run_and_rebuild(self):
        """HR9 演练不落盘；init 已存在转刷新；--force 重建。"""
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "empty"
            target.mkdir()
            dry = run_handoff(target, "init", "--mode", "new-project", "--dry-run")
            self.assertEqual(dry.returncode, 0, msg=dry.stdout + dry.stderr)
            self.assertIn("演练模式", dry.stdout)
            self.assertIn("## 1. 已完成内容", dry.stdout)
            self.assertFalse((target / "docs").exists(), msg="dry-run 不应写入文件")

            target2 = make_project(td)
            run_handoff(target2, "init", "--mode", "new-project", "--no-hook")
            path = record_path(target2)
            path.write_text(path.read_text(encoding="utf-8") + "\n手工补充：仅本行\n", encoding="utf-8")

            again = run_handoff(target2, "init", "--mode", "new-project", "--no-hook")
            self.assertEqual(again.returncode, 0, msg=again.stdout + again.stderr)
            self.assertIn("手工补充：仅本行", path.read_text(encoding="utf-8"),
                          msg="init 已存在时应转为刷新并保留人工内容")

            rebuilt = run_handoff(target2, "init", "--mode", "new-project", "--no-hook", "--force")
            self.assertEqual(rebuilt.returncode, 0, msg=rebuilt.stdout + rebuilt.stderr)
            self.assertNotIn("手工补充：仅本行", path.read_text(encoding="utf-8"),
                             msg="--force 应重建记录")

    def test_hr10_same_framework_across_modes(self):
        """HR10 统一框架：三种场景输出的九节结构与顺序完全一致。"""
        expected = [
            "1. 已完成内容", "2. 变更范围", "3. 关键决策", "4. 未完成事项",
            "5. 风险或阻塞", "6. 下一步计划", "7. 关联设计文档",
            "8. 更新记录", "9. 交接提示",
        ]
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)

            new_target = make_project(td / "new")
            run_handoff(new_target, "init", "--mode", "new-project", "--no-hook")

            existing = make_project(td / "existing")
            (existing / "app.py").write_text("print('hi')\n", encoding="utf-8")
            git(existing, "add", "-A")
            git(existing, "commit", "-m", "feat: 初始实现")
            run_handoff(existing, "update", "--mode", "new-session", "--no-hook")

            cont = make_project(td / "cont")
            (cont / "app.py").write_text("print('hi')\n", encoding="utf-8")
            git(cont, "add", "-A")
            git(cont, "commit", "-m", "feat: 初始实现")
            ctx = write_context(td)
            run_handoff(cont, "update", "--mode", "continue",
                        "--context", str(ctx), "--no-hook")

            texts = {
                "new-project": record_path(new_target).read_text(encoding="utf-8"),
                "existing-new-session": record_path(existing).read_text(encoding="utf-8"),
                "existing-continue": record_path(cont).read_text(encoding="utf-8"),
            }
            for name, text in texts.items():
                self.assertEqual(headings_of(text), expected,
                                 msg=f"{name} 的小节结构与其他场景不一致")
            modes = {re.search(r"^mode: (.+)$", text, re.M).group(1) for text in texts.values()}
            self.assertEqual(modes, {"new-project", "existing-new-session", "existing-continue"},
                             msg="三种场景的 mode 标记应各自保留")

    def test_hr11_broken_template_aborts_write(self):
        """HR11 模板残缺：生成结果未通过结构校验时中止写入。"""
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            skill = td / "skill"
            (skill / "scripts").mkdir(parents=True)
            shutil.copytree(SKILL_ROOT / "assets", skill / "assets")
            shutil.copy(SCRIPT, skill / "scripts" / "handoff_record.py")
            template = skill / "assets" / "handoff-record-template.md"
            template.write_text(
                template.read_text(encoding="utf-8").replace("<!-- AUTO:NEXT -->", ""),
                encoding="utf-8",
            )

            target = make_project(td / "proj")
            r = subprocess.run(
                [sys.executable, str(skill / "scripts" / "handoff_record.py"),
                 "init", str(target), "--mode", "new-project", "--no-hook"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=120,
            )
            self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
            self.assertIn("未通过结构校验", r.stdout)
            self.assertFalse(record_path(target).exists(), msg="校验失败不应写入记录")


if __name__ == "__main__":
    unittest.main()
