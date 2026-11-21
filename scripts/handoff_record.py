#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""开发进度交接记录（Handoff Record）· 生成 / 刷新 / 校验 / 提交门禁

用途:
    为阶段四（产品实现）提供跨会话的进度交接载体 docs/handoff-record.md。
    阶段四流程与「独立调用生成交接文档」共用本脚本的同一套生成逻辑。

用法:
    python handoff_record.py init <项目目录> [选项]
    python handoff_record.py update <项目目录> [选项]
    python handoff_record.py check <项目目录> [--staged] [--stamp] [--quiet]
    python handoff_record.py install-hook <项目目录> [--force]

init / update 选项:
    --mode auto|new-project|continue|new-session
                      场景判定（默认 auto，见下）
    --context FILE    非新会话的上下文摘要（Markdown，按 ## 小节归类）
    --no-hook         不安装 pre-commit 钩子
    --force           init 时重建记录（丢弃人工维护内容）；install-hook 时备份后替换
    --dry-run         只输出将执行的动作，不写文件、不装钩子

场景判定（两级，对应 methodology 阶段四）:
    第一级 · 是否新项目？
        new-project           新项目：阶段四开始，基于 docs 双文档创建交接框架
    第二级 · 已有项目，按当前会话状态二选一
        existing-continue     非新会话（保留了上文）：上下文摘要 + 项目目录内容
        existing-new-session  新会话（从零开始）：只根据项目目录内容与 Git 历史总结

统一框架:
    无论新项目还是已有项目，三种场景都输出同一套模板（assets/handoff-record-template.md）
    与同样的九节结构（七节必填 + 更新记录 + 交接提示）；差异只在内容取证来源与 mode 标记。

commit 门禁（二选一，缺一不可）:
    1) 更新记录：本次提交包含 docs/handoff-record.md 的改动；
    2) 执行校验：check <项目> --stamp，写入本次 HEAD 的校验签。
    install-hook 会安装 pre-commit 钩子自动执行 check --staged。

退出码: 0 成功 / 通过；1 失败 / 校验不通过（含提交门禁拦截）。
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SCRIPT_DIR = Path(__file__).resolve().parent
ASSETS_DIR = SCRIPT_DIR.parent / "assets"
RECORD_REL = Path("docs") / "handoff-record.md"
TEMPLATE_NAME = "handoff-record-template.md"
HOOK_MARKER = "stable-delivery-workflow: handoff-record gate"

MODE_LABELS = {
    "new-project": "新项目 · 阶段四开工",
    "existing-continue": "已有项目 · 非新会话（上下文 + 目录）",
    "existing-new-session": "已有项目 · 新会话（仅目录事实）",
}

# 小节别名：标题命中任一别名即归入该键（顺序影响匹配优先级）
SECTION_ALIASES = (
    ("completed", ("已完成内容", "已完成")),
    ("scope", ("变更范围", "变更清单")),
    ("decisions", ("关键决策", "决策记录")),
    ("pending", ("未完成事项", "未完成", "待办事项")),
    ("risks", ("风险或阻塞", "风险与阻塞", "风险", "阻塞")),
    ("next", ("下一步计划", "下一步", "后续计划")),
    ("design", ("关联设计文档", "设计文档")),
    ("history", ("更新记录", "变更历史")),
    ("notes", ("交接提示", "交接说明")),
)

REQUIRED_SECTIONS = (
    ("completed", "已完成内容"),
    ("scope", "变更范围"),
    ("decisions", "关键决策"),
    ("pending", "未完成事项"),
    ("risks", "风险或阻塞"),
    ("next", "下一步计划"),
    ("design", "关联设计文档"),
)

BAD_TOKENS = ("{{", "}}", "待填写", "待补充", "TODO", "TBD", "<!-- AUTO:")
EMPTY_HINTS = ("（尚无", "（尚未", "（暂无", "阶段四尚未开始")

EMPTY_COMPLETED = "- （尚无已完成内容）"
EMPTY_DECISIONS = "- （尚无关键决策：技术选型确认后在此记录）"
EMPTY_RISKS = "- （暂无已知风险）"
EMPTY_NOTES = "- （无）"

SKIP_DIRS = {".git", ".github", "node_modules", "venv", ".venv", "env", "dist",
             "build", "__pycache__", ".pytest_cache", ".idea", ".vscode"}

# ── 模板降级兜底（权威源：assets/handoff-record-template.md） ──────────────
# 仅在 assets 缺失时使用；修改模板时必须同步本常量（反向亦然），保持逐字一致。
HANDOFF_FALLBACK = """---
record: handoff
project: {{PROJECT_NAME}}
mode: {{MODE_KEY}}
mode_label: {{MODE_LABEL}}
branch: {{BRANCH}}
head: {{HEAD}}
updated_at: {{UPDATED_AT}}
---

# 开发进度交接记录 · {{PROJECT_NAME}}

> 用途：跨会话交接的唯一进度接口——新会话先读本文件，再读关联设计文档，不要依赖聊天记忆。
> 生成：`python scripts/handoff_record.py update <项目目录>`（阶段四流程与独立调用共用同一套生成逻辑）。
> 门禁：每次 commit 前更新本记录，或执行 `python scripts/handoff_record.py check <项目目录> --stamp`；pre-commit 钩子会强制校验。
> 必填七节：已完成内容 / 变更范围 / 关键决策 / 未完成事项 / 风险或阻塞 / 下一步计划 / 关联设计文档。

## 1. 已完成内容

<!-- AUTO:COMPLETED -->

## 2. 变更范围

<!-- AUTO:SCOPE -->

## 3. 关键决策

<!-- AUTO:DECISIONS -->

## 4. 未完成事项

<!-- AUTO:PENDING -->

## 5. 风险或阻塞

<!-- AUTO:RISKS -->

## 6. 下一步计划

<!-- AUTO:NEXT -->

## 7. 关联设计文档

<!-- AUTO:DESIGN -->

## 8. 更新记录

<!-- AUTO:HISTORY -->

## 9. 交接提示

<!-- AUTO:NOTES -->
"""


# ── 基础工具 ───────────────────────────────────────────────

def run_git(args, cwd):
    return subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )


def git_out(args, cwd):
    r = run_git(args, cwd)
    return (r.stdout or "").strip() if r.returncode == 0 else ""


def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return ""


def write_text_lf(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def repo_info(target):
    """返回分支 / HEAD / 提交数；非仓库或空仓库时给出可读占位。"""
    target = Path(target)
    info = {
        "is_repo": (target / ".git").exists(),
        "branch": "（无仓库）",
        "head": "（无提交）",
        "head_full": "",
        "commits": 0,
    }
    if not info["is_repo"]:
        return info
    branch = git_out(["rev-parse", "--abbrev-ref", "HEAD"], target)
    if branch:
        info["branch"] = branch
    head = git_out(["rev-parse", "--short", "HEAD"], target)
    full = git_out(["rev-parse", "HEAD"], target)
    if head:
        info["head"] = head
        info["head_full"] = full
    count = git_out(["rev-list", "--count", "HEAD"], target)
    try:
        info["commits"] = int(count or 0)
    except ValueError:
        info["commits"] = 0
    return info


def git_dir(target):
    raw = git_out(["rev-parse", "--git-dir"], target)
    p = Path(raw) if raw else Path(".git")
    return p if p.is_absolute() else Path(target) / p


def hooks_dir(target):
    raw = git_out(["rev-parse", "--git-path", "hooks"], target)
    if raw:
        p = Path(raw)
        return p if p.is_absolute() else Path(target) / p
    return git_dir(target) / "hooks"


def commit_entries(target, since=None, limit=10):
    """读取提交列表；since 无效时自动回退到最近 limit 条。"""
    args = ["log", f"-{limit}", "--date=short", "--pretty=%h\t%ad\t%s"]
    if since:
        verify = run_git(["rev-parse", "--verify", "--quiet", f"{since}^{{commit}}"], target)
        if verify.returncode == 0:
            args = ["log", f"{since}..HEAD", "--date=short", "--pretty=%h\t%ad\t%s"]
    r = run_git(args, target)
    if r.returncode != 0:
        return []
    entries = []
    for line in (r.stdout or "").splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            entries.append({"hash": parts[0], "date": parts[1], "subject": parts[2]})
    return entries


def tracked_files(target):
    """受控文件清单；非 Git 项目回退为目录扫描。"""
    target = Path(target)
    r = run_git(["ls-files"], target)
    if r.returncode == 0 and (r.stdout or "").strip():
        return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
    files = []
    for path in target.rglob("*"):
        rel = path.relative_to(target)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.is_file():
            files.append(rel.as_posix())
    return sorted(files)


def working_tree_changes(target):
    raw = git_out(["status", "--porcelain"], target)
    return [ln for ln in raw.splitlines() if ln.strip()]


def is_test_path(rel):
    return bool(re.search(r"(^|/)(tests?|__tests__)/|(^|/)test_[^/]*\.py$|_test\.|\.test\.|\.spec\.", rel))


# ── Markdown 解析 ──────────────────────────────────────────

def parse_frontmatter(text):
    m = re.match(r"^---\r?\n(.*?)\r?\n---\s*\r?\n", text or "", re.S)
    if not m:
        return {}
    data = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t", "-")):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def section_key(title):
    for key, aliases in SECTION_ALIASES:
        if any(alias in title for alias in aliases):
            return key
    return None


def split_sections(text):
    """按二级标题切分，返回 {键: 正文}。未知标题对应键为 None，跳过。"""
    sections = {}
    current = None
    buf = []
    for line in (text or "").splitlines():
        m = re.match(r"^##[ \t]+(?!#)(.+?)\s*$", line)
        if m:
            if current:
                sections[current] = "\n".join(buf).strip("\n")
            current = section_key(m.group(1))
            buf = []
            continue
        if current:
            buf.append(line)
    if current:
        sections[current] = "\n".join(buf).strip("\n")
    return sections


def section_lines(sections, key):
    body = sections.get(key, "")
    return [ln.strip() for ln in body.splitlines() if ln.strip()]


def doc_sections(text):
    """按二级标题切分任意设计文档，返回 [(标题, 正文)]。"""
    out = []
    title, buf = None, []
    for line in (text or "").splitlines():
        if re.match(r"^##[ \t]+(?!#)", line):
            if title is not None:
                out.append((title, "\n".join(buf)))
            title = re.sub(r"^##[ \t]+", "", line).strip()
            buf = []
        elif title is not None:
            buf.append(line)
    if title is not None:
        out.append((title, "\n".join(buf)))
    return out


def body_under(text, keyword):
    for title, body in doc_sections(text):
        if keyword in title:
            return body
    return ""


def table_rows_under(text, keyword):
    rows = []
    for line in body_under(text, keyword).splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not cells or all(set(c) <= set("-: ") for c in cells):
            continue
        rows.append(cells)
    return rows


def bullets_under(text, keyword):
    items = []
    for line in body_under(text, keyword).splitlines():
        s = line.strip()
        if re.match(r"^[-*+]\s+", s):
            value = re.sub(r"^[-*+]\s+", "", s).strip()
            if value:
                items.append("- " + value)
    return items


def doc_meta(text):
    meta = {"version": "", "status": ""}
    if not text:
        return meta
    head = "\n".join(text.splitlines()[:8])
    m = re.search(r"版本[:：]\s*v?([0-9][0-9A-Za-z.\-]*)", head)
    if m:
        meta["version"] = m.group(1)
    m = re.search(r"状态[:：]\s*([^｜|\n]+)", head)
    if m:
        status = m.group(1).strip().rstrip("。 ")
        if "二选一" in status or "待确认" in status:
            status = "未确认"
        meta["status"] = status
    return meta


def parse_context(text):
    """解析上下文摘要：按 ## 小节归类，未加列表符号的行自动补 '- '。"""
    data = {}
    current = None
    for line in (text or "").splitlines():
        m = re.match(r"^#{1,3}[ \t]+(.+?)\s*$", line)
        if m:
            current = section_key(m.group(1))
            continue
        if current is None:
            continue
        s = line.strip()
        if not s:
            continue
        if not re.match(r"^([-*+]|\d+\.)\s+", s):
            s = "- " + s
        data.setdefault(current, []).append(s)
    return data


# ── 内容生成 ───────────────────────────────────────────────

def project_name(target):
    agents = read_text(Path(target) / "AGENTS.md")
    m = re.search(r"^\s*[-*]?\s*项目名称[:：]\s*(.+)$", agents, re.M)
    if m:
        name = m.group(1).strip()
        if name and "{{" not in name:
            return name
    return Path(target).name


def dedupe_lines(lines):
    seen, out = set(), []
    for line in lines:
        s = (line or "").strip()
        if not s:
            continue
        key = re.sub(r"^([-*+]|\d+\.)\s+", "", s)
        key = re.sub(r"^\[[ xX]\]\s*", "", key).strip()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def drop_empty_markers(lines):
    if len(lines) <= 1:
        return lines
    return [ln for ln in lines if not any(hint in ln for hint in EMPTY_HINTS)]


def top_level_summary(files):
    counts = {}
    for rel in files:
        top = rel.split("/")[0] if "/" in rel else "（根目录）"
        counts[top] = counts.get(top, 0) + 1
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return ordered


def feature_items(product_text):
    items, names = [], []
    seen = set()
    for cells in table_rows_under(product_text, "功能清单"):
        name = cells[0] if cells else ""
        if not name or name in ("功能", "功能名称") or name in seen:
            continue
        seen.add(name)
        desc = cells[1] if len(cells) > 1 else ""
        priority = cells[2] if len(cells) > 2 else ""
        text = "- [ ] " + name
        if desc:
            text += "：" + desc
        if priority:
            text += f"（优先级：{priority}）"
        items.append(text)
        names.append(name)
    return items, names


PENDING_NOTE = "> 说明：条目来自产品设计文档"


def decision_items(tech_text):
    items = []
    for cells in table_rows_under(tech_text, "技术栈"):
        if len(cells) < 2:
            continue
        layer, choice = cells[0], cells[1]
        if not layer or not choice or layer in ("层面", "层"):
            continue
        reason = cells[2] if len(cells) > 2 else ""
        items.append(f"- {layer}：{choice}" + (f"（{reason}）" if reason else ""))
    return items


def build_completed(target, info, mode, context, previous):
    lines = []
    if mode == "new-project":
        lines.append(f"- （阶段四尚未开始：交接框架已建立，基线 {info['branch']} @ {info['head']}）")
    else:
        lines.extend(section_lines(previous, "completed"))
        lines.extend(context.get("completed", []))
        since = parse_frontmatter(read_text(Path(target) / RECORD_REL)).get("head") or None
        if not since:
            since = None
        entries = commit_entries(target, since=since, limit=10)
        for e in entries:
            lines.append(f"- [x] {e['hash']} {e['subject']}（{e['date']}）")
        if not info["commits"]:
            lines.append("- （仓库暂无提交记录，进度依据目录内容估计）")
    lines = dedupe_lines(lines)
    lines = drop_empty_markers(lines)
    return lines or [EMPTY_COMPLETED]


def build_scope(target, info, product_meta, tech_meta, context, have_product, have_tech):
    files = tracked_files(target)
    dirty = working_tree_changes(target)
    tops = top_level_summary(files)
    top_text = "、".join(f"{name}/({count})" for name, count in tops[:6]) or "（暂无受控文件）"
    tests = [f for f in files if is_test_path(f)]
    test_text = f"{len(tests)} 个测试文件" if tests else "未检测到测试文件"
    prod_status = product_meta.get("status") or ("未确认" if have_product else "缺失")
    tech_status = tech_meta.get("status") or ("未确认" if have_tech else "缺失")
    lines = [
        "| 范围 | 内容 | 说明 |",
        "|---|---|---|",
        f"| 版本基线 | {info['branch']} @ {info['head']} | 受控文件 {len(files)} 个；未提交改动 {len(dirty)} 个 |",
        f"| 模块分布 | {top_text} | 按顶层目录统计受控文件数 |",
        f"| 测试 | {test_text} | 与功能同步维护，交付前须全部通过 |",
        f"| 设计输入 | docs/product-design.md、docs/tech-design.md | 产品设计：{prod_status}；技术方案：{tech_status} |",
    ]
    extra = context.get("scope", [])
    if extra:
        lines.append("")
        lines.extend(extra)
    return lines


def build_design(target, product_text, tech_text):
    rows = ["| 文档 | 状态 | 本次引用内容 |", "|---|---|---|"]

    p_meta = doc_meta(product_text)
    if product_text:
        features, _ = feature_items(product_text)
        acceptance = bullets_under(product_text, "验收要点")
        rows.append(
            "| docs/product-design.md | "
            + (p_meta["status"] or "未确认")
            + f" | MVP 功能 {len(features)} 项、验收要点 {len(acceptance)} 条 |"
        )
    else:
        rows.append("| docs/product-design.md | 缺失 | 需在阶段二补齐（模板：assets/product-design-template.md） |")

    t_meta = doc_meta(tech_text)
    if tech_text:
        stack = decision_items(tech_text)
        risks = bullets_under(tech_text, "已知风险")
        rows.append(
            "| docs/tech-design.md | "
            + (t_meta["status"] or "未确认")
            + f" | 技术栈 {len(stack)} 项、已知风险 {len(risks)} 条 |"
        )
    else:
        rows.append("| docs/tech-design.md | 缺失 | 需在阶段三补齐（模板：assets/tech-design-template.md） |")
    return rows


def build_pending(product_text, context, previous):
    features, _ = feature_items(product_text)
    lines = section_lines(previous, "pending") + context.get("pending", []) + features
    if features:
        # 已有真实功能清单时，去掉此前生成的兜底占位与重复说明行
        lines = [ln for ln in lines if "按 docs/product-design.md 的功能清单逐项实现" not in ln]
        lines = [ln for ln in lines if not ln.startswith(PENDING_NOTE)]
    lines = dedupe_lines(lines)
    lines = drop_empty_markers(lines)
    if not lines:
        return ["- [ ] 按 docs/product-design.md 的功能清单逐项实现"]
    if features:
        lines.insert(0, PENDING_NOTE + "；完成状态以实际代码为准，完成后改为 [x]。")
    return lines


def build_decisions(tech_text, context, previous):
    human = [ln for ln in section_lines(previous, "decisions") + context.get("decisions", [])
             if not any(hint in ln for hint in EMPTY_HINTS)]
    return dedupe_lines(human) or decision_items(tech_text) or [EMPTY_DECISIONS]


def build_risks(tech_text, context, previous):
    tech_risks = []
    for item in bullets_under(tech_text, "已知风险"):
        tech_risks.append(item + "（来源：docs/tech-design.md「已知风险」）")
    lines = section_lines(previous, "risks") + context.get("risks", []) + tech_risks
    lines = dedupe_lines(lines)
    lines = drop_empty_markers(lines)
    return lines or [EMPTY_RISKS]


AUTO_NEXT_HINTS = ("完成「按 docs/", "按 docs/tech-design.md 搭建项目骨架",
                   "按关联设计文档实现剩余功能", "每个可验证功能一个 commit")


def renumber_steps(lines):
    out, n = [], 0
    for line in lines:
        s = line.strip()
        m = re.match(r"^(?:\d+\.|[-*+])\s+(.*)$", s)
        if not m:
            out.append(s)
            continue
        n += 1
        out.append(f"{n}. {m.group(1)}")
    return out


def is_auto_next(line):
    s = line.strip()
    if any(hint in s for hint in AUTO_NEXT_HINTS):
        return True
    return bool(re.match(r"^\d+\.\s*完成「.+」$", s))


def build_next(context, previous, feature_names, mode):
    # 丢弃上一版自动生成的计划行，保留人工补充的计划
    prev_next = [ln for ln in section_lines(previous, "next") if not is_auto_next(ln)]
    human = dedupe_lines(prev_next + context.get("next", []))
    human = drop_empty_markers(human)
    if human:
        steps = renumber_steps(human)
        if not any(("commit" in s.lower()) or ("提交" in s) for s in steps):
            steps.append(f"{len(steps) + 1}. 每个可验证功能一个 commit；提交前更新本记录（或 check --stamp 校验）")
        return steps
    names = []
    for name in feature_names:
        clean = (name or "").strip()
        if clean and "功能清单" not in clean and clean not in names:
            names.append(clean)
    names = names[:3]
    if mode == "new-project" and not names:
        return [
            "1. 按 docs/tech-design.md 搭建项目骨架，跑通运行与测试命令",
            "2. 按 MVP 清单实现第一个「必须」功能",
            "3. 每个可验证功能一个 commit；提交前更新本记录",
        ]
    if names:
        out = [f"{i}. 完成「{name}」" for i, name in enumerate(names, 1)]
        out.append(f"{len(out) + 1}. 每个可验证功能一个 commit；提交前更新本记录（或 check --stamp 校验）")
        return out
    return [
        "1. 按关联设计文档实现剩余功能",
        "2. 每个可验证功能一个 commit；提交前更新本记录（或 check --stamp 校验）",
    ]


def mode_note(mode, context_path):
    if mode == "new-project":
        return "- 阶段四开始：框架已基于设计文档建立；实现过程中每完成一个可验证功能，更新第 1 / 4 / 6 节并提交。"
    if mode == "existing-continue":
        source = context_path or "（上下文摘要）"
        return f"- 本次为已有项目的非新会话：已合并上下文摘要（{source}）与项目目录事实；两者冲突时以代码与设计文档为准。"
    return "- 本次为已有项目的新会话：仅依据项目目录与 Git 历史总结，未纳入任何对话上下文；有疑问先查设计文档与代码，不要凭猜测继续。"


def build_history(previous, info, mode, reason, now):
    lines = section_lines(previous, "history")
    # 同一 HEAD + 同一原因的重跑不重复记流水
    suffix = f"· HEAD {info['head']} · {reason}"
    lines = [ln for ln in lines if suffix not in ln]
    lines.append(f"- {now} · {MODE_LABELS[mode]} · HEAD {info['head']} · {reason}")
    return dedupe_lines(lines)


def load_template():
    path = ASSETS_DIR / TEMPLATE_NAME
    if path.is_file():
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            pass
    return HANDOFF_FALLBACK


def render_record(data, blocks):
    text = load_template()
    text = text.replace("{{PROJECT_NAME}}", data["project"])
    text = text.replace("{{MODE_KEY}}", data["mode"])
    text = text.replace("{{MODE_LABEL}}", data["mode_label"])
    text = text.replace("{{BRANCH}}", data["branch"])
    text = text.replace("{{HEAD}}", data["head"])
    text = text.replace("{{UPDATED_AT}}", data["updated_at"])
    for key, body in blocks.items():
        text = text.replace(f"<!-- AUTO:{key} -->", body)
    return text.rstrip() + "\n"


def build_notes(context, previous, mode, context_path):
    # 模式提示按本次场景重写，避免新旧场景说明叠加
    prev_notes = [ln for ln in section_lines(previous, "notes")
                  if not ln.startswith("- 本次为")
                  and "框架已基于设计文档建立" not in ln]
    lines = dedupe_lines(prev_notes + context.get("notes", []) + [mode_note(mode, context_path)])
    return lines or [EMPTY_NOTES]


def build_record(target, mode, context, previous_text, context_path, reason):
    target = Path(target)
    info = repo_info(target)
    product_text = read_text(target / "docs" / "product-design.md")
    tech_text = read_text(target / "docs" / "tech-design.md")
    previous = split_sections(previous_text) if previous_text else {}
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    pending = build_pending(product_text, context, previous)
    _, feature_names = feature_items(product_text)
    blocks = {
        "COMPLETED": "\n".join(build_completed(target, info, mode, context, previous)),
        "SCOPE": "\n".join(build_scope(target, info, doc_meta(product_text), doc_meta(tech_text),
                                      context, bool(product_text), bool(tech_text))),
        "DECISIONS": "\n".join(build_decisions(tech_text, context, previous)),
        "PENDING": "\n".join(pending),
        "RISKS": "\n".join(build_risks(tech_text, context, previous)),
        "NEXT": "\n".join(build_next(context, previous, feature_names, mode)),
        "DESIGN": "\n".join(build_design(target, product_text, tech_text)),
        "HISTORY": "\n".join(build_history(previous, info, mode, reason, now)),
        "NOTES": "\n".join(build_notes(context, previous, mode, context_path)),
    }
    data = {
        "project": project_name(target),
        "mode": mode,
        "mode_label": MODE_LABELS[mode],
        "branch": info["branch"],
        "head": info["head"],
        "updated_at": now,
    }
    return render_record(data, blocks), info, blocks


# ── 校验与提交门禁 ─────────────────────────────────────────

def validate_text(text):
    problems = []
    fm = parse_frontmatter(text)
    if not fm:
        problems.append("缺少 frontmatter（需 record / project / mode / branch / head / updated_at）")
    else:
        for key in ("record", "project", "mode", "branch", "head", "updated_at"):
            if not fm.get(key):
                problems.append(f"frontmatter 缺字段：{key}")
    if fm.get("record") and fm.get("record") != "handoff":
        problems.append("frontmatter record 应为 handoff")
    sections = split_sections(text)
    for key, label in REQUIRED_SECTIONS:
        body = sections.get(key)
        if body is None:
            problems.append(f"缺少小节：{label}")
            continue
        if not body.strip():
            problems.append(f"小节内容为空：{label}")
            continue
        if any(token in body for token in BAD_TOKENS):
            problems.append(f"小节含未填写占位：{label}")
    return problems


def token_path(target):
    return git_dir(target) / "handoff-verified"


def read_token(target):
    text = read_text(token_path(target))
    data = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip()
    return data


def write_token(target, info, staged_count):
    content = (
        f"head={info['head_full']}\n"
        f"head_short={info['head']}\n"
        f"at={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"staged={staged_count}\n"
    )
    write_text_lf(token_path(target), content)


def staged_files(target):
    raw = git_out(["diff", "--cached", "--name-only"], target)
    return [ln.strip() for ln in raw.splitlines() if ln.strip()]


def sh_quote(value):
    return "'" + str(value).replace("'", "'\\''") + "'"


def install_hook(target, force=False):
    target = Path(target).resolve()
    hooks = hooks_dir(target)
    hook = hooks / "pre-commit"
    try:
        hooks.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, f"无法创建钩子目录: {exc}"

    if hook.exists():
        old = read_text(hook)
        if HOOK_MARKER not in old:
            if not force:
                return False, "已存在自定义 pre-commit 钩子，未覆盖（确认后加 --force 备份并替换）"
            backup = hook.with_name("pre-commit.bak." + datetime.now().strftime("%Y%m%d%H%M%S"))
            try:
                shutil.copy2(hook, backup)
            except OSError as exc:
                return False, f"备份已有钩子失败: {exc}"

    content = (
        "#!/bin/sh\n"
        f"# {HOOK_MARKER}\n"
        "# 提交前强制：更新交接记录，或执行 check --stamp 校验。\n"
        'PYTHON="${HANDOFF_PYTHON:-python}"\n'
        'if ! command -v "$PYTHON" >/dev/null 2>&1; then PYTHON=python3; fi\n'
        f"exec \"$PYTHON\" {sh_quote(SCRIPT_DIR / 'handoff_record.py')} "
        f"check {sh_quote(target)} --staged --quiet\n"
    )
    try:
        write_text_lf(hook, content)
        os.chmod(hook, 0o755)
    except OSError as exc:
        return False, f"写入钩子失败: {exc}"
    return True, f"已安装 pre-commit 钩子：{hook}"


# ── 场景判定 ───────────────────────────────────────────────

def has_implementation(target):
    for rel in tracked_files(target):
        if rel in ("AGENTS.md", ".gitignore", "README.md"):
            continue
        if rel.startswith("docs/"):
            continue
        return True
    return False


def detect_mode(target, context):
    """两级判定：先判断是否新项目；已有项目再按会话状态二选一。

    新项目与"新会话"不是并列关系：新项目也可能处在新会话中，
    因此先看项目阶段（提交数 / 是否已有实现），再看当前会话是否保留上文。
    记录是否已存在不参与判定——重复执行 init 不应把新项目改判为已有项目。
    """
    info = repo_info(target)
    if info["commits"] <= 1 and not has_implementation(target):
        return "new-project"
    return "existing-continue" if context else "existing-new-session"


def count_items(body):
    return sum(1 for ln in body.splitlines() if re.match(r"^\s*([-*+]|\d+\.)\s+", ln))


# ── 命令实现 ───────────────────────────────────────────────

def cmd_write(args, refresh):
    target = Path(args.target).expanduser().resolve()
    if not target.is_dir():
        print(f"[x] 目录不存在: {target}")
        return 1

    record = target / RECORD_REL
    old_text = read_text(record) if record.is_file() else ""

    context = {}
    context_text = ""
    if args.context:
        ctx_path = Path(args.context).expanduser()
        if not ctx_path.is_file():
            print(f"[x] 上下文文件不存在: {ctx_path}")
            return 1
        context_text = read_text(ctx_path)
        context = parse_context(context_text)
        if not context:
            print("[x] 上下文文件没有可识别的小节。")
            print("    请用 ## 已完成内容 / ## 关键决策 / ## 未完成事项 / ## 风险或阻塞 / ## 下一步计划 分节。")
            return 1

    mode = args.mode
    if mode == "auto":
        mode = detect_mode(target, context)
    if mode == "continue":
        if not context:
            print("[x] 已有项目的「非新会话」模式必须提供 --context：把当前对话里的进度摘要写成文件再执行。")
            print("    若确实没有上文（新会话），请用 --mode new-session（仅依据项目目录总结）。")
            return 1
        mode = "existing-continue"
    if mode == "new-session":
        if context:
            print("[x] 已有项目的「新会话」模式不接受 --context：该场景只根据项目目录内容总结。")
            print("    若当前对话保留了上文，说明不是新会话，请改用 --mode continue。")
            return 1
        mode = "existing-new-session"
    if mode not in MODE_LABELS:
        print(f"[x] 未知模式: {mode}")
        return 1

    previous_text = "" if args.force else old_text
    if old_text and args.force:
        print("[!] 按 --force 重建记录：原有人工维护内容将被丢弃。")

    if refresh and old_text and not args.force:
        reason = "刷新记录（按目录与设计文档重新取证）"
    elif refresh:
        reason = "创建交接记录（update 首次生成）"
    elif old_text:
        reason = "刷新记录（init 检测到已有记录，转为刷新）"
    elif mode == "new-project":
        reason = "阶段四开工：基于设计文档建立交接框架"
    elif mode == "existing-continue":
        reason = "非新会话首次生成（上下文摘要 + 目录内容）"
    else:
        reason = "新会话首次生成（仅依据项目目录与 Git 历史）"

    text, info, blocks = build_record(
        target, mode, context, previous_text,
        args.context if args.context else "", reason,
    )

    # 统一框架保障：任何场景生成的结果都必须通过同一套结构校验
    problems = validate_text(text)
    if problems:
        print("[x] 生成结果未通过结构校验，已中止（模板可能被改动或不完整）：")
        for problem in problems:
            print("      - " + problem)
        print("     请检查 assets/handoff-record-template.md 的九节结构与 AUTO 标记。")
        return 1

    if args.dry_run:
        print("=" * 60)
        print(f"【演练模式】将生成交接记录 · {target.name}（未写入任何文件）")
        print("=" * 60)
        print(f"  · 模式: {MODE_LABELS[mode]}")
        print(f"  · 文件: {RECORD_REL.as_posix()}")
        print(f"  · 基线: {info['branch']} @ {info['head']}")
        print(f"  · 条目: 已完成 {count_items(blocks['COMPLETED'])} · "
              f"未完成 {count_items(blocks['PENDING'])} · 风险 {count_items(blocks['RISKS'])}")
        print("  · 钩子: 将安装 pre-commit（除非 --no-hook）")
        print()
        print(text)
        return 0

    write_text_lf(record, text)

    hook_msg = "按 --no-hook 要求未安装钩子"
    if not args.no_hook:
        if not info["is_repo"]:
            hook_msg = "非 Git 仓库，跳过钩子安装（先 git init）"
        else:
            ok, hook_msg = install_hook(target, force=args.force)

    print("=" * 60)
    print(("交接记录已刷新" if old_text and not args.force else "交接记录已生成") + f" · {project_name(target)}")
    print("=" * 60)
    print(f"  · 模式: {MODE_LABELS[mode]}（{mode}）")
    print(f"  · 文件: {RECORD_REL.as_posix()}")
    print(f"  · 基线: {info['branch']} @ {info['head']}")
    print(f"  · 条目: 已完成 {count_items(blocks['COMPLETED'])} · "
          f"未完成 {count_items(blocks['PENDING'])} · 风险 {count_items(blocks['RISKS'])}")
    print(f"  · 钩子: {hook_msg}")
    print()
    print("下一步:")
    print("  1. 让实现 Agent 先读本记录与 docs 双文档，再继续开发")
    print("  2. 每完成一个可验证功能：更新本记录 → 提交（钩子会校验）")
    print(f"  3. 仅需校验时：python scripts/handoff_record.py check {target} --stamp")
    return 0


def cmd_check(args):
    target = Path(args.target).expanduser().resolve()
    if not target.is_dir():
        print(f"[x] 目录不存在: {target}")
        return 1
    record = target / RECORD_REL
    failed = False

    if not record.is_file():
        print(f"[✗] 未找到交接记录：{RECORD_REL.as_posix()}")
        print(f"     先运行：python scripts/handoff_record.py init {target}")
        return 1

    text = read_text(record)
    problems = validate_text(text)
    if problems:
        failed = True
        print("[✗] 交接记录结构校验未通过：")
        for problem in problems:
            print("      - " + problem)
        print("     修复：python scripts/handoff_record.py update " + str(target))
    elif not args.quiet:
        print("[✓] 交接记录结构完整（7 个必填小节齐全）")

    info = repo_info(target)
    if args.stamp:
        if failed:
            return 1
        if not info["is_repo"]:
            print("[x] 非 Git 仓库，无法写入校验签")
            return 1
        write_token(target, info, len(staged_files(target)))
        print(f"[✓] 已写入校验签：HEAD {info['head']}（本次提交有效，下次提交需重新校验）")
        return 0

    if args.staged:
        if failed:
            return 1
        if not info["is_repo"]:
            print("[x] 非 Git 仓库，无法执行提交门禁")
            return 1
        if info["commits"] == 0:
            if not args.quiet:
                print("[ℹ] 首次提交：无 HEAD 基线，跳过门禁（结构校验已通过）")
            return 0
        staged = staged_files(target)
        record_staged = RECORD_REL.as_posix() in staged
        token = read_token(target)
        token_ok = token.get("head") == info["head_full"]
        if record_staged:
            if not args.quiet:
                print("[✓] 提交门禁：交接记录已随本次提交更新")
            return 0
        if token_ok:
            if not args.quiet:
                print(f"[✓] 提交门禁：已执行校验（HEAD {info['head']}）")
            return 0
        print("[✗] 提交门禁：交接记录未更新，也未执行本次校验")
        print(f"     本次暂存文件：{len(staged)} 个" + (f"（如 {staged[0]}）" if staged else ""))
        print("     二选一后再提交：")
        print(f"       1) 更新记录：python scripts/handoff_record.py update {target}")
        print(f"       2) 仅校验：  python scripts/handoff_record.py check {target} --stamp")
        print("     说明：pre-commit 钩子由 stable-delivery-workflow 安装；不建议用 --no-verify 绕过。")
        return 1

    if not args.quiet:
        rec_commit = git_out(["log", "-1", "--format=%h", "--", RECORD_REL.as_posix()], target)
        if rec_commit and info["head"] != rec_commit:
            behind = git_out(["rev-list", "--count", f"{rec_commit}..HEAD"], target)
            if behind and behind != "0":
                print(f"[ℹ] 记录最后更新于 {rec_commit}，其后已有 {behind} 个提交——提交前需刷新或校验。")
        if not rec_commit:
            print("[ℹ] 记录尚未纳入版本管理：与代码一起提交，钩子才会认可「已更新」。")
    return 1 if failed else 0


def cmd_install_hook(args):
    target = Path(args.target).expanduser().resolve()
    if not target.is_dir():
        print(f"[x] 目录不存在: {target}")
        return 1
    if not (target / RECORD_REL).is_file():
        print(f"[x] 未找到 {RECORD_REL.as_posix()}，请先执行 init 生成交接记录。")
        return 1
    ok, msg = install_hook(target, force=args.force)
    print(("[✓] " if ok else "[!] ") + msg)
    return 0 if ok else 1


def build_parser():
    parser = argparse.ArgumentParser(
        description="开发进度交接记录：生成 / 刷新 / 校验 / 提交门禁（阶段四）"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p):
        p.add_argument("target", nargs="?", default=".", help="项目目录（默认当前目录）")
        p.add_argument("--mode", default="auto",
                       choices=["auto", "new-project", "continue", "new-session"],
                       help="场景（默认 auto）：new-project＝新项目；"
                            "continue＝已有项目的非新会话；new-session＝已有项目的新会话")
        p.add_argument("--context", default=None,
                       help="上下文摘要文件（已有项目的非新会话必填；新会话禁止）")
        p.add_argument("--no-hook", action="store_true", help="不安装 pre-commit 钩子")
        p.add_argument("--force", action="store_true", help="init 时重建记录；install-hook 时备份后替换")
        p.add_argument("--dry-run", action="store_true", help="只输出将执行的动作，不写文件")

    add_common(sub.add_parser("init", help="创建交接记录框架（已存在则转为刷新）"))
    add_common(sub.add_parser("update", help="刷新交接记录（保留人工维护的小节）"))

    p_check = sub.add_parser("check", help="校验结构 / 提交门禁")
    p_check.add_argument("target", nargs="?", default=".", help="项目目录（默认当前目录）")
    p_check.add_argument("--staged", action="store_true", help="作为 pre-commit 门禁检查本次暂存改动")
    p_check.add_argument("--stamp", action="store_true", help="写入本次 HEAD 的校验签（不修改记录）")
    p_check.add_argument("--quiet", action="store_true", help="通过时不输出")

    p_hook = sub.add_parser("install-hook", help="安装 pre-commit 钩子")
    p_hook.add_argument("target", nargs="?", default=".", help="项目目录（默认当前目录）")
    p_hook.add_argument("--force", action="store_true", help="备份后替换已有自定义钩子")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    if args.command in ("init", "update"):
        return cmd_write(args, refresh=(args.command == "update"))
    if args.command == "check":
        return cmd_check(args)
    if args.command == "install-hook":
        return cmd_install_hook(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
