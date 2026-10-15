#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""稳定交付工作流 · 项目初始化脚本（阶段一：环境搭建）

用法:
    python init_project.py <目标目录> [--name 项目名] [--commit-lang 语种]
                           [--commit-msg 首次提交信息] [--remote 远端URL] [--no-commit]

执行内容:
    1. 创建项目目录（已存在则复用）
    2. git init（分支 main；已是仓库则跳过）
    3. 写入 AGENTS.md（交付硬规则 + 项目信息骨架；已存在则不覆盖）
    4. 创建 docs/product-design.md、docs/tech-design.md 骨架（已存在则不覆盖）
    5. 写入基础 .gitignore（已存在则跳过）
    6. git add + 首次 commit（--no-commit 可跳过）

commit 信息语种:
    - 创建首次提交前，先询问用户后续所有 commit 信息使用的语种：
      默认「简体中文」，支持用户自行指定（如 English）。
    - 交互终端下未传 --commit-lang 时会提示输入；非交互场景直接采用默认值。
    - 语种会写入 AGENTS.md 的交付规则，约束后续所有 commit。
    - 首次提交信息默认跟随语种（中 / 英内置模板）；其他语种可用 --commit-msg 指定。

安全约定:
    - 不删除、不覆盖任何已存在的文件
    - 不重复初始化已有仓库
    - 不修改全局 git 配置（如缺少身份，仅为本仓库设置占位身份）

退出码: 0 成功；1 失败
"""
import argparse
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SCRIPT_DIR = Path(__file__).resolve().parent
ASSETS_DIR = SCRIPT_DIR.parent / "assets"

DEFAULT_COMMIT_LANG = "简体中文"

AGENTS_FALLBACK = """# AGENTS.md

> 本文件是 AI 编程代理的项目值班手册。进入本项目开启新会话时，先读取本文件并遵守以下规则。

## 交付规则（必须遵守）

1. **每次改动后必须创建 Git commit**，保留可追踪的版本快照，便于随时回退。
2. **每次改动后必须编写或更新相关测试**，并在交付前确保所有测试与验收全部通过。
3. **所有 Git commit 信息统一使用{{COMMIT_LANG}}**（初始化时确认，如需变更请同步修改本文件）。

## 项目信息

- 项目名称：{{PROJECT_NAME}}
- 技术栈：（技术设计阶段填写）
- 运行命令：（填写后更新）
- 测试命令：（填写后更新）
- 目录说明：
  - `docs/`：产品设计文档（product-design.md）与技术方案文档（tech-design.md）

## 边界约定

- 不擅自扩大需求范围；"暂时不做"的功能清单见 `docs/product-design.md`。
- 遇到规格不明确的情况：先提问或停下，不要猜测后直接实现。
- 重大架构调整前，先给出方案并等待确认。
"""

PRODUCT_FALLBACK = """# 产品设计文档 · {{PROJECT_NAME}}

> 版本：v0.1 ｜ 日期：{{DATE}} ｜ 状态：草稿
> 用途：确定本版本"做什么 / 暂时不做什么"，作为技术设计与实现开发的统一依据。

## 1. 一句话定位

## 2. 核心用户路径（主流程）

1. 

## 3. 本版本功能清单（MVP）

| 功能 | 说明 | 优先级 |
|---|---|---|
| | | 必须 |

## 4. 明确不做的事（推迟清单）

- 

## 5. 边界条件与约束

- 

## 6. 验收要点

- [ ] 

## 7. 待确认问题

- 
"""

TECH_FALLBACK = """# 技术方案文档 · {{PROJECT_NAME}}

> 版本：v0.1 ｜ 日期：{{DATE}} ｜ 状态：草稿
> 原则：只锁定技术栈与架构大方向，细节在实现中校准。

## 1. 技术栈

| 层面 | 选型 | 理由 |
|---|---|---|
| 语言 | | |
| 框架 | | |
| 构建工具 | | |

## 2. 架构方向

## 3. 备选方案与取舍记录

| 候选方案 | 优点 | 缺点 | 结论 |
|---|---|---|---|

## 4. 已知风险

- 

## 5. 运行与测试方式

- 运行命令：
- 测试命令：
- 验证工具（AI 自测所需）：
"""

GITIGNORE = """# 依赖
node_modules/
venv/
.venv/

# 构建产物
dist/
build/

# 环境与密钥
.env
.env.local

# 系统与编辑器
.DS_Store
Thumbs.db
.idea/
.vscode/

# 日志
*.log
"""


def resolve_commit_lang(cli_value):
    """确定 commit 信息语种；返回 (语种, 是否采用默认值)。

    - 显式传入 --commit-lang 时直接采用；
    - 交互终端下（未传参）会询问用户，回车即采用默认值；
    - 非交互场景（如自动化调用）直接采用默认值。
    """
    if cli_value and cli_value.strip():
        return cli_value.strip(), False
    if sys.stdin.isatty():
        try:
            resp = input(f"后续所有 commit 信息使用语种 [默认: {DEFAULT_COMMIT_LANG}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            resp = ""
        if resp:
            return resp, False
    return DEFAULT_COMMIT_LANG, True


def is_english(lang: str) -> bool:
    low = lang.strip().lower()
    return "英" in lang or "english" in low or low in {"en", "en-us", "en_us"}


def is_chinese(lang: str) -> bool:
    low = lang.strip().lower()
    return "中" in lang or "chinese" in low or low in {"zh", "zh-cn", "zh_cn"}


def build_first_commit_msg(lang: str) -> str:
    """按语种生成首次提交信息（中 / 英内置模板；其他语种回退中文模板）。"""
    if is_english(lang):
        return "chore: init project (AGENTS.md + docs skeleton)"
    return "chore: 初始化项目（AGENTS.md + docs 骨架）"


def load_template(filename: str, fallback: str) -> str:
    """优先读取 assets/ 下的模板文件，缺失时使用内置兜底模板。"""
    path = ASSETS_DIR / filename
    if path.is_file():
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            pass
    return fallback


def render(text: str, project_name: str, commit_lang: str) -> str:
    # 语种名为拉丁字母开头时（如 English），与前文中文之间补一个空格
    first = commit_lang.strip()[:1]
    lang_display = (" " + commit_lang) if (first and first.isascii() and first.isalpha()) else commit_lang
    return (
        text.replace("{{PROJECT_NAME}}", project_name)
        .replace("{{COMMIT_LANG}}", lang_display)
        .replace("{{DATE}}", date.today().isoformat())
    )


def run_git(args, cwd) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="初始化 AI 编程项目环境（Git + AGENTS.md + docs 骨架）"
    )
    parser.add_argument("target", help="项目目录（不存在则自动创建）")
    parser.add_argument("--name", default=None, help="项目名称（默认取目录名）")
    parser.add_argument(
        "--commit-lang",
        default=None,
        help=f"commit 信息使用的语种（默认：{DEFAULT_COMMIT_LANG}；交互终端下未指定会提示输入）",
    )
    parser.add_argument(
        "--commit-msg",
        default=None,
        help="覆盖首次提交信息原文（用于非中 / 英语种或自定义文案）",
    )
    parser.add_argument("--remote", default=None, help="可选：关联远端仓库 URL（git remote add origin）")
    parser.add_argument("--no-commit", action="store_true", help="只搭建环境，不创建首次 commit")
    args = parser.parse_args()

    if shutil.which("git") is None:
        print("[x] 未检测到 git，请先安装 Git: https://git-scm.com/")
        return 1

    # ── 0. 首次提交前先确认 commit 信息语种 ────────────────────
    commit_lang, lang_is_default = resolve_commit_lang(args.commit_lang)
    commit_msg = (args.commit_msg or "").strip() or build_first_commit_msg(commit_lang)

    target = Path(args.target).expanduser().resolve()
    project_name = args.name or target.name
    steps = []

    if lang_is_default:
        steps.append(f"commit 信息语种: {commit_lang}（默认；可用 --commit-lang 指定其他语种）")
    else:
        steps.append(f"commit 信息语种: {commit_lang}")
    if not (is_chinese(commit_lang) or is_english(commit_lang)) and not (args.commit_msg or "").strip():
        steps.append("首次提交信息暂用中文模板；如需其他语种，可加 --commit-msg 指定")

    # ── 1. 目录 ──────────────────────────────────────────────
    if target.exists():
        if not target.is_dir():
            print(f"[x] 目标已存在且不是目录: {target}")
            return 1
        steps.append(f"目录已存在，复用: {target}")
    else:
        target.mkdir(parents=True)
        steps.append(f"已创建项目目录: {target}")

    # ── 2. git init ──────────────────────────────────────────
    if (target / ".git").exists():
        steps.append("已是 Git 仓库，跳过 git init")
    else:
        r = run_git(["init", "-b", "main"], target)
        if r.returncode != 0:
            r = run_git(["init"], target)
        if r.returncode != 0:
            print("[x] git init 失败:\n" + (r.stderr or r.stdout or ""))
            return 1
        steps.append("已初始化 Git 仓库（分支 main）")

    # ── 3~5. 写入骨架文件（不覆盖已存在） ─────────────────────
    files = [
        (target / "AGENTS.md",
         render(load_template("AGENTS.md.template", AGENTS_FALLBACK), project_name, commit_lang)),
        (target / "docs" / "product-design.md",
         render(load_template("product-design-template.md", PRODUCT_FALLBACK), project_name, commit_lang)),
        (target / "docs" / "tech-design.md",
         render(load_template("tech-design-template.md", TECH_FALLBACK), project_name, commit_lang)),
        (target / ".gitignore", GITIGNORE),
    ]
    for path, content in files:
        rel = path.relative_to(target)
        if path.exists():
            steps.append(f"已存在，跳过: {rel}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        steps.append(f"已创建: {rel}")

    # ── 远端（可选） ─────────────────────────────────────────
    if args.remote:
        existing = run_git(["remote"], target)
        remotes = (existing.stdout or "").split()
        if "origin" in remotes:
            steps.append("origin 远端已存在，跳过 remote add")
        else:
            r = run_git(["remote", "add", "origin", args.remote], target)
            if r.returncode == 0:
                steps.append(f"已关联远端 origin: {args.remote}")
            else:
                steps.append("远端关联失败: " + (r.stderr or "").strip())

    # ── 6. 首次提交（使用已确认的语种） ───────────────────────
    if args.no_commit:
        steps.append("按 --no-commit 要求，未创建首次提交")
    else:
        run_git(["add", "-A"], target)
        status = run_git(["status", "--porcelain"], target)
        if not (status.stdout or "").strip():
            steps.append("没有需要提交的改动，跳过提交")
        else:
            r = run_git(["commit", "-m", commit_msg], target)
            if r.returncode != 0:
                run_git(["config", "user.name", "Stable Delivery Workflow"], target)
                run_git(["config", "user.email", "stable-delivery@local"], target)
                steps.append("检测到未配置 git 身份，已为本仓库设置占位身份（可用 git config 修改）")
                r = run_git(["commit", "-m", commit_msg], target)
            if r.returncode == 0:
                rev = run_git(["rev-parse", "--short", "HEAD"], target)
                steps.append(f"已创建首次提交: {(rev.stdout or '').strip()}（{commit_msg}）")
            else:
                steps.append("提交失败（可稍后手动提交）: " + (r.stderr or r.stdout or "").strip())

    # ── 输出摘要 ─────────────────────────────────────────────
    print("=" * 56)
    print(f"AI 编程项目初始化完成 · {project_name}")
    print("=" * 56)
    for s in steps:
        print("  · " + s)
    print()
    print("下一步（进入阶段二 · 产品设计）:")
    print("  1. 打开你的 AI 编程工具（Codex / Claude Code 等），加载本项目目录")
    print("  2. 粘贴提示词（见 skill stable-delivery-workflow 的 references/prompt-templates.md C-1）")
    print("  3. 讨论出 MVP 后，填好 docs/product-design.md 并请用户确认")
    return 0


if __name__ == "__main__":
    sys.exit(main())
