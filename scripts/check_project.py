#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DoD 可执行校验器：检查项目的「护栏就绪度」信号。

用法:
    python scripts/check_project.py [项目目录] [--commits N]

检查项（逐项 ✓ / ✗）:
    G1  版本护栏   存在 .git 目录
    G2  版本基线   至少 1 个 commit
    G3  纳入管理   AGENTS.md 与 docs/ 已跟踪且无未提交改动
    A1  交付规则   AGENTS.md 含 commit / 测试 / 语种 三类硬规则
    D1  规格文档   docs 双文档存在且表格已填写（启发式）
    V1  验收清单   docs/acceptance-checklist.md 存在
    A2  自测命令   技术方案填写后，AGENTS.md 的运行/测试命令已填写
    V2  验收结论   验收开始后，验收结论与验收人已填写

提示项（ℹ，不计入通过率）:
    C1  提交粒度   最近 N 次提交的文件数分布（>15 个文件视为「一锅烩」信号）
    A2/V2 未到对应阶段时以提示项出现，不参与通过率

退出码: 存在 ✗ 时返回 1，否则返回 0。
边界: 本脚本只提供「信号」，通过 ≠ 满足验收——人工验证不可省。
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def run_git(args, cwd):
    return subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def extract_command(text: str, labels) -> str:
    """从 AGENTS.md 中提取「运行命令 / 测试命令」的值。"""
    for label in labels:
        m = re.search(rf"^\s*[-*]?\s*{re.escape(label)}\s*[:：]\s*(.*)$", text, re.M)
        if m:
            return m.group(1).strip()
    return ""


def command_is_pending(value: str) -> bool:
    return (not value) or any(x in value for x in ("填写后更新", "（如", "(如", "TODO", "TBD"))


def acceptance_progress(text: str) -> bool:
    """验收清单是否已经开始填写（至少勾选一项）。"""
    return bool(re.search(r"^\s*-\s*\[[xX]\]", text, re.M))


def acceptance_conclusion(text: str) -> tuple:
    """返回 (验收结论, 验收人)；未填写时为空串。"""
    m = re.search(r"^\s*-\s*结论\s*[:：]\s*(.*)$", text, re.M)
    conclusion = m.group(1).strip() if m else ""
    if conclusion in {"通过 / 有条件通过 / 不通过", "通过/有条件通过/不通过"}:
        conclusion = ""
    m = re.search(r"^\s*-\s*验收人[^\n:：]*[:：]\s*(.*)$", text, re.M)
    reviewer = m.group(1).strip() if m else ""
    return conclusion, reviewer


def main() -> int:
    parser = argparse.ArgumentParser(description="检查项目的交付护栏就绪度信号")
    parser.add_argument("target", nargs="?", default=".", help="项目目录（默认当前目录）")
    parser.add_argument("--commits", type=int, default=5, help="C1 统计的最近提交数（默认 5）")
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    if not target.is_dir():
        print(f"[x] 目录不存在: {target}")
        return 1

    results = []  # (编号, 是否通过, 描述, 修复提示)
    infos = []    # (编号, 说明)，不计入通过率
    is_repo = (target / ".git").exists()
    results.append(("G1", is_repo, "版本护栏：.git 目录存在",
                    "见 risk-playbook D3 → 先执行 git init 建立仓库"))

    commit_count = 0
    if is_repo:
        r = run_git(["rev-list", "--count", "HEAD"], target)
        try:
            commit_count = int((r.stdout or "0").strip())
        except ValueError:
            commit_count = 0
    results.append(("G2", commit_count >= 1, f"版本基线：提交数 = {commit_count}",
                    "见 risk-playbook D3 → 创建首次 commit"))

    required = ("AGENTS.md", "docs/product-design.md", "docs/tech-design.md",
                "docs/acceptance-checklist.md")
    if is_repo:
        st = run_git(["status", "--porcelain", "--", "AGENTS.md", "docs"], target)
        lines = [ln for ln in (st.stdout or "").splitlines() if ln.strip()]
        untracked = [ln[3:].strip() for ln in lines if ln.startswith("??")]
        modified = [ln[3:].strip() for ln in lines if not ln.startswith("??")]
        missing = [rel for rel in required if not (target / rel).is_file()]
        not_tracked = []
        for rel in required:
            if (target / rel).is_file():
                r = run_git(["ls-files", "--error-unmatch", rel], target)
                if r.returncode != 0:
                    not_tracked.append(rel)
        notes = []
        if missing:
            notes.append(f"缺少: {'、'.join(missing[:5])}")
        if untracked:
            notes.append(f"未跟踪: {'、'.join(untracked[:5])}")
        if modified:
            notes.append(f"未提交: {'、'.join(modified[:5])}")
        if not_tracked:
            notes.append(f"未纳入版本管理: {'、'.join(not_tracked[:5])}")
        g3_ok = not (missing or untracked or modified or not_tracked)
        note = f"（{'；'.join(notes)}）" if notes else ""
        results.append(("G3", g3_ok, "纳入管理：AGENTS.md / docs 已跟踪且无未提交改动" + note,
                        "见 risk-playbook D3/D9 → git add 并提交；确认文件未被 .gitignore 忽略"))
    else:
        results.append(("G3", False, "纳入管理：AGENTS.md / docs 已跟踪且无未提交改动（无仓库）",
                        "见 risk-playbook D3 → 先建立仓库"))

    agents = read_text(target / "AGENTS.md")
    has_commit = ("commit" in agents.lower()) or ("提交" in agents)
    has_test = ("测试" in agents) or ("test" in agents.lower())
    has_lang = (("语种" in agents) or ("统一使用" in agents) or ("提交信息" in agents)
                or ("language" in agents.lower()) or ("commit message" in agents.lower()))
    missing = [n for n, ok in (("commit 规则", has_commit), ("测试规则", has_test), ("语种规则", has_lang)) if not ok]
    a1_ok = bool(agents.strip()) and not missing
    note = f"（缺: {'、'.join(missing)}）" if missing else ""
    results.append(("A1", a1_ok, "交付规则：AGENTS.md 含 commit / 测试 / 语种" + note,
                    "见 risk-playbook D2/D4 → 按 assets/AGENTS.template.md 补齐规则"))

    d_ok, d_note = True, []
    empty_row = re.compile(r"^\|\s*\|\s*\|\s*(必须|采用|备选)\s*\|", re.M)
    empty_field = re.compile(r"^\|\s*(语言|框架|构建工具)\s*\|\s*\|\s*\|", re.M)
    doc_filled = {}
    for rel in ("docs/product-design.md", "docs/tech-design.md"):
        text = read_text(target / rel)
        filled = bool(text.strip()) and not (empty_row.search(text) or empty_field.search(text))
        doc_filled[rel] = filled
        if not text:
            d_ok = False
            d_note.append(f"缺少 {rel}")
        elif not filled:
            d_ok = False
            d_note.append(f"{rel} 表格疑似未填写")
    results.append(("D1", d_ok, "规格文档：docs 双文档存在且表格已填写" + (f"（{'；'.join(d_note)}）" if d_note else ""),
                    "见 risk-playbook D1/D8 → 补做文档（模板见 assets/）"))

    v1_ok = (target / "docs" / "acceptance-checklist.md").is_file()
    results.append(("V1", v1_ok, "验收清单：docs/acceptance-checklist.md 存在",
                    "见 risk-playbook D11 → 从 assets/acceptance-checklist.md 复制"))

    # A2：技术方案填写后，运行/测试命令必须就绪（阶段四 AI 自测的前提）
    tech_filled = doc_filled.get("docs/tech-design.md", False)
    run_cmd = extract_command(agents, ("运行命令", "Run command", "run command"))
    test_cmd = extract_command(agents, ("测试命令", "Test command", "test command"))
    cmd_missing = [n for n, ok in (("运行命令", not command_is_pending(run_cmd)),
                                   ("测试命令", not command_is_pending(test_cmd))) if not ok]
    a2_ok = not cmd_missing
    if tech_filled:
        cmd_note = f"（缺/未填: {'、'.join(cmd_missing)}）" if cmd_missing else ""
        results.append(("A2", a2_ok, "自测命令：AGENTS.md 的运行/测试命令已填写" + cmd_note,
                        "见 risk-playbook D4 → 在 AGENTS.md 填写运行/测试命令"))
    else:
        infos.append(("A2", "自测命令：技术方案尚未填写，暂不检查"))

    # V2：验收开始后，结论与验收人必须落字
    acceptance = read_text(target / "docs" / "acceptance-checklist.md")
    if acceptance_progress(acceptance):
        conclusion, reviewer = acceptance_conclusion(acceptance)
        v2_ok = bool(conclusion and reviewer)
        results.append(("V2", v2_ok, "验收结论：结论与验收人已填写",
                        "见 risk-playbook D11 → 完成验收清单并签署结论"))
    else:
        infos.append(("V2", "验收结论：验收尚未开始，暂不检查"))

    c1_info = ""
    if is_repo and commit_count > 0:
        r = run_git(["log", f"-{args.commits}", "--pretty=format:@@%h", "--name-only"], target)
        counts, cur = {}, None
        for line in (r.stdout or "").splitlines():
            if line.startswith("@@"):
                cur = line[2:]
                counts[cur] = 0
            elif line.strip() and cur:
                counts[cur] += 1
        if counts:
            dist = "、".join(f"{h}={n}" for h, n in counts.items())
            big = [h for h, n in counts.items() if n > 15]
            c1_info = f"最近 {len(counts)} 次提交的文件数：{dist}"
            if big:
                c1_info += f"（{ '、'.join(big) } 超过 15 个文件，可能是「一锅烩」提交）"

    print(f"项目目录: {target}")
    print("=" * 60)
    passed = 0
    for cid, ok, text, hint in results:
        passed += 1 if ok else 0
        print(f"[{'✓' if ok else '✗'}] {cid}  {text}")
        if not ok:
            print(f"      ↳ {hint}")
    if c1_info:
        print(f"[ℹ] C1  {c1_info}")
    for cid, text in infos:
        print(f"[ℹ] {cid}  {text}")
    print("=" * 60)
    print(f"通过 {passed}/{len(results)} 项。")
    print("提示：本脚本仅提供「护栏信号」；通过 ≠ 满足验收——人工验证不可省。")
    if not d_ok:
        print("提示：刚初始化的项目 D1 未通过属预期；填写 docs 后复查。")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
