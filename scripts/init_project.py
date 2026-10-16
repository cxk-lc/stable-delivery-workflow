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
    4. 创建 docs/ 三份骨架：product-design.md、tech-design.md、acceptance-checklist.md
       （已存在则不覆盖）
    5. 写入基础 .gitignore（已存在则跳过）
    6. git add + 首次 commit（--no-commit 可跳过）

commit 信息语种:
    - 创建首次提交前，先询问用户后续所有 commit 信息使用的语种。
    - 默认值：用户当前系统所使用的语言（脚本自动检测，判断依据：
        · Windows：系统 UI 语言（GetUserDefaultUILanguage）
        · macOS / Linux：环境变量 LC_ALL / LC_MESSAGES / LANG
        · 以上均无法识别时：回退「简体中文」）。
    - 生效范围：该默认值仅在用户未手动指定时生效。用户手动指定优先——
      用 --commit-lang 显式传入，或交互终端下输入自定义语种，
      任一存在时一律以用户指定为准。
    - 交互终端下未传 --commit-lang 时会提示输入（回车即采用默认值）；
      非交互场景直接采用检测结果。
    - 语种会写入 AGENTS.md 的交付规则，约束后续所有 commit。
    - 首次提交信息默认跟随语种（中 / 英内置模板）；其他语种可用 --commit-msg 指定。

安全约定:
    - 不删除、不覆盖任何已存在的文件
    - 不重复初始化已有仓库
    - 不修改全局 git 配置（如缺少身份，仅为本仓库设置占位身份）

退出码: 0 成功；1 失败
"""
import argparse
import locale
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Optional

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SCRIPT_DIR = Path(__file__).resolve().parent
ASSETS_DIR = SCRIPT_DIR.parent / "assets"

# commit 语种回退值：仅在用户未指定且系统语言检测失败时使用
FALLBACK_COMMIT_LANG = "简体中文"

# ── 模板与降级兜底（权威源：assets/） ─────────────────────────
# assets/ 目录为模板的唯一权威源。下列 *_FALLBACK 常量仅在 assets 缺失时降级使用，
# 修改任何模板时必须同步本处（反向亦然），保持两者内容逐字一致；
# 可用占位符：{{PROJECT_NAME}} / {{COMMIT_LANG}} / {{DATE}}。

AGENTS_FALLBACK = """# AGENTS.md

> 本文件是 AI 编程代理的项目值班手册。进入本项目开启新会话时，先读取本文件并遵守以下规则。
> 保持精简：高频规则放在这里，细节按需引用其他文档。

## 交付规则（必须遵守）

1. **每次改动后必须创建 Git commit**，保留可追踪的版本快照，便于随时回退。
2. **每次改动后必须编写或更新相关测试**，并在交付前确保所有测试与验收全部通过。
3. **所有 Git commit 信息统一使用{{COMMIT_LANG}}**（初始化时确认，如需变更请同步修改本文件）。

## 项目信息

- 项目名称：{{PROJECT_NAME}}
- 技术栈：（技术设计阶段填写）
- 运行命令：（如 npm start，填写后更新）
- 测试命令：（如 npm test，填写后更新）
- 目录说明：
  - `docs/`：产品设计文档（product-design.md）与技术方案文档（tech-design.md）
  - 其他目录：（按需补充）

## 边界约定

- 不擅自扩大需求范围；"暂时不做"的功能清单见 `docs/product-design.md`。
- 遇到规格不明确的情况：先提问或停下，不要猜测后直接实现。
- 重大架构调整前，先给出方案并等待确认。
"""

PRODUCT_FALLBACK = """# 产品设计文档 · {{PROJECT_NAME}}

> 版本：v0.1 ｜ 日期：{{DATE}} ｜ 状态：草稿 / 已确认（二选一）
> 用途：确定本版本"做什么 / 暂时不做什么"，作为技术设计与实现开发的统一依据（施工图）。
> 原则：简短优先——梳理整体方向与主要功能即可，细节留给迭代。

## 1. 一句话定位

（这个产品是什么、给谁用、解决什么问题）

## 2. 核心用户路径（主流程）

1. 用户打开产品 → ……
2. ……
3. ……

## 3. 本版本功能清单（MVP）

| 功能 | 说明 | 优先级 |
|---|---|---|
| | | 必须 |
| | | 必须 |

## 4. 明确不做的事（推迟清单）

> 明确"不做什么"与"做什么"同等重要，用于防止范围膨胀。

- 
- 

## 5. 边界条件与约束

> 主动让 AI 列出隐含边界（编码格式、滚动方式、异常提示等）后逐项确认。

- 
- 

## 6. 验收要点

> 从"做什么 / 不做"提炼为可检查的验收条件（"完成" = 全部满足）。

- [ ] 
- [ ] 

## 7. 待确认问题

- 
"""

TECH_FALLBACK = """# 技术方案文档 · {{PROJECT_NAME}}

> 版本：v0.1 ｜ 日期：{{DATE}} ｜ 状态：草稿 / 已确认（二选一）
> 原则：只锁定技术栈与架构大方向，细节在实现中校准——过早写满细节，会把未验证的猜测包装成约束。

## 1. 技术栈

| 层面 | 选型 | 理由 |
|---|---|---|
| 语言 | | |
| 框架 | | |
| 构建工具 | | |
| 其他 | | |

## 2. 架构方向

（模块划分的大方向，1~3 段即可；不要求覆盖每个类与接口）

## 3. 备选方案与取舍记录

| 候选方案 | 优点 | 缺点 | 结论 |
|---|---|---|---|
| | | | 采用 |
| | | | 备选 |

## 4. 已知风险

- 
- 

## 5. 运行与测试方式

- 运行命令：
- 测试命令：
- 验证工具（AI 自测所需）：

> 填写后请同步更新 `AGENTS.md` 的"项目信息"一节。
"""

ACCEPTANCE_FALLBACK = """# 人工验收清单 · {{PROJECT_NAME}}

> 原则：AI 自测通过 ≠ 无 Bug；验收单只能由人签。
> 使用：每个版本交付前逐项走查，全部通过后再进入下一轮迭代。

## 1. 冒烟测试（能不能跑）

- [ ] 按文档中的运行命令可正常启动
- [ ] 主流程可以走通

## 2. 主流程走查（好不好用）

- [ ] 用户核心路径完整可用
- [ ] 交互体验符合预期（操作流畅、反馈明确）

## 3. 边界与异常（稳不稳）

- [ ] 空输入 / 非法输入有合理提示
- [ ] 大文件 / 大数据量场景可接受
- [ ] 上次出过问题的地方已回归验证

## 4. 交付物检查

- [ ] 所有改动均有对应 Git commit
- [ ] 测试全部通过（含 Agent 提交的证据）
- [ ] 文档已同步更新（规格变化已回写）

## 5. 验收结论

- 结论：通过 / 有条件通过 / 不通过
- 遗留问题：
- 验收人 / 日期：
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


# ── 系统语言检测（commit 语种默认值的判断依据） ───────────────
# Windows LANGID 主语言 ID → 语言代码（winnt.h 常用项）
_WIN_LANGID_TO_CODE = {
    0x01: "ar", 0x04: "zh", 0x05: "cs", 0x06: "da", 0x07: "de", 0x08: "el",
    0x09: "en", 0x0A: "es", 0x0B: "fi", 0x0C: "fr", 0x0D: "he", 0x0E: "hu",
    0x10: "it", 0x11: "ja", 0x12: "ko", 0x13: "nl", 0x14: "no", 0x15: "pl",
    0x16: "pt", 0x18: "ro", 0x19: "ru", 0x1B: "sk", 0x1D: "sv", 0x1E: "th",
    0x1F: "tr", 0x21: "id", 0x22: "uk", 0x2A: "vi", 0x39: "hi", 0x3E: "ms",
}

# 语言代码 → 语种名（用于写入 AGENTS.md 规则、选择首次提交信息模板）
_LANG_CODE_TO_NAME = {
    "ar": "العربية", "cs": "Čeština", "da": "Dansk", "de": "Deutsch",
    "el": "Ελληνικά", "en": "English", "es": "Español", "fi": "Suomi",
    "fr": "Français", "he": "עברית", "hi": "हिन्दी", "hu": "Magyar",
    "id": "Bahasa Indonesia", "it": "Italiano", "ja": "日本語", "ko": "한국어",
    "ms": "Bahasa Melayu", "nl": "Nederlands", "no": "Norsk", "pl": "Polski",
    "pt": "Português", "ro": "Română", "ru": "Русский", "sk": "Slovenčina",
    "sv": "Svenska", "th": "ไทย", "tr": "Türkçe", "uk": "Українська",
    "vi": "Tiếng Việt",
}

# 繁体中文的地区 / 字形标识（用于中文细分，其余中文一律视为简体）
_TRADITIONAL_ZH_MARKERS = {"tw", "hk", "mo", "hant"}


def _lang_name_from_code(code: str) -> Optional[str]:
    """语言代码 → 语种名（zh 默认简体）；无法识别返回 None。"""
    if code == "zh":
        return "简体中文"
    return _LANG_CODE_TO_NAME.get(code)


def _lang_name_from_locale(raw: str) -> Optional[str]:
    """解析 locale 表达（如 zh_CN.UTF-8 / zh-TW / en_US / C）→ 语种名。

    C / POSIX 及无法识别者返回 None；中文按地区（tw/hk/mo）或字形（Hant）
    细分；同时兼容 Windows 下的描述性名称（如 "Chinese (Simplified)_China"）。
    """
    if not raw:
        return None
    base = raw.strip().replace("-", "_").split(".")[0].split("@")[0]
    parts = [p.lower() for p in base.split("_") if p]
    if not parts or parts[0] in {"c", "posix"}:
        return None
    if parts[0] == "zh" or "chinese" in base.lower():
        traditional = "traditional" in base.lower() or any(
            p in _TRADITIONAL_ZH_MARKERS for p in parts[1:]
        )
        return "繁体中文" if traditional else "简体中文"
    return _lang_name_from_code(parts[0])


def _lang_name_from_langid(langid: int) -> Optional[str]:
    """Windows LANGID → 语种名；中文按子语言细分（TW / HK / MO 为繁体）。"""
    code = _WIN_LANGID_TO_CODE.get(langid & 0x3FF)
    if code is None:
        return None
    if code == "zh":
        return "繁体中文" if (langid >> 10) in {0x01, 0x03, 0x05} else "简体中文"
    return _lang_name_from_code(code)


def _get_windows_ui_langid() -> Optional[int]:
    """读取 Windows 系统 UI 语言 LANGID；不可用时返回 None。"""
    try:
        import ctypes
        return int(ctypes.windll.kernel32.GetUserDefaultUILanguage())
    except Exception:
        return None


def detect_system_language():
    """检测「用户当前系统所使用的语言」，返回 (语种名, 判断依据说明)。

    判断依据（按优先级）：
    1. Windows：系统 UI 语言（GetUserDefaultUILanguage）；
    2. 环境变量 LC_ALL / LC_MESSAGES / LANG（macOS、Linux 及显式设置的环境）；
    3. Python locale 查询（兼容 Windows 描述性名称）。
    无法识别时返回 (None, None)，由调用方回退 FALLBACK_COMMIT_LANG。
    """
    if sys.platform == "win32":
        langid = _get_windows_ui_langid()
        if langid is not None:
            name = _lang_name_from_langid(langid)
            if name:
                return name, f"Windows 系统 UI 语言（LANGID 0x{langid:04X}）"
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        raw = (os.environ.get(var) or "").strip()
        if raw:
            name = _lang_name_from_locale(raw)
            if name:
                return name, f"环境变量 {var}={raw}"
    try:
        loc = locale.getlocale()[0]
    except Exception:
        loc = None
    if loc:
        name = _lang_name_from_locale(loc)
        if name:
            return name, f"系统 locale（{loc}）"
    return None, None


def resolve_commit_lang(cli_value):
    """确定 commit 信息语种；返回 (语种, 来源说明)。

    生效规则（优先级从高到低，先命中者生效）：
    1. 用户手动指定：--commit-lang 传入值，或交互终端下用户输入的值；
    2. 用户未指定：默认采用「用户当前系统所使用的语言」（自动检测，
       判断依据见 detect_system_language）；
    3. 系统语言无法识别：回退 FALLBACK_COMMIT_LANG（简体中文）。
    来源说明用于输出摘要，标明取值方式与默认值的判断依据。
    """
    if cli_value and cli_value.strip():
        return cli_value.strip(), "用户手动指定（--commit-lang）"
    detected, source = detect_system_language()
    default_lang = detected or FALLBACK_COMMIT_LANG
    if detected:
        default_note = f"未指定，默认跟随系统语言；判断依据: {source}"
        prompt_hint = f"默认 {default_lang}；未指定将跟随系统语言（判断依据: {source}）"
    else:
        default_note = "未指定且系统语言检测失败，已回退内置默认；可用 --commit-lang 指定"
        prompt_hint = f"默认 {default_lang}（系统语言检测失败，回退内置默认）"
    if sys.stdin.isatty():
        try:
            resp = input(f"后续所有 commit 信息使用语种 [{prompt_hint}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            resp = ""
        if resp:
            return resp, "用户手动指定（交互输入）"
    return default_lang, default_note


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
        help="commit 信息使用的语种（未指定时默认跟随用户当前系统语言，脚本自动检测；"
             f"检测失败回退{FALLBACK_COMMIT_LANG}；交互终端下未指定会提示输入）",
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

    # ── 0. 首次提交前先确认 commit 信息语种（未指定时跟随系统语言） ──
    commit_lang, lang_note = resolve_commit_lang(args.commit_lang)
    commit_msg = (args.commit_msg or "").strip() or build_first_commit_msg(commit_lang)

    target = Path(args.target).expanduser().resolve()
    project_name = args.name or target.name
    steps = []

    steps.append(f"commit 信息语种: {commit_lang} — {lang_note}")
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
         render(load_template("AGENTS.template.md", AGENTS_FALLBACK), project_name, commit_lang)),
        (target / "docs" / "product-design.md",
         render(load_template("product-design-template.md", PRODUCT_FALLBACK), project_name, commit_lang)),
        (target / "docs" / "tech-design.md",
         render(load_template("tech-design-template.md", TECH_FALLBACK), project_name, commit_lang)),
        (target / "docs" / "acceptance-checklist.md",
         render(load_template("acceptance-checklist.md", ACCEPTANCE_FALLBACK), project_name, commit_lang)),
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
