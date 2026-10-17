#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""引用完整性 lint：发布前检查技能包的自洽性（维护者用）。

用法:
    python scripts/lint_references.py

规则:
    R1  路径引用存在性   扫描全部 Markdown 中对 assets/ / references/ / scripts/ 的相对路径引用，校验目标存在
    R2  占位符一致性     模板（assets/*.md 与脚本兜底常量）中的 {{KEY}} 必须由 render() 支持；
                        报告「未支持」（阻断发布）与「未使用」（仅提示）
    R3  资源索引一致性   已由 R1 覆盖（SKILL.md 亦在扫描范围内）

退出码: 存在 ✗ 时返回 1，否则返回 0。约定：每次发布前运行。
"""
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
PATH_REF = re.compile(r"(?<![A-Za-z0-9_])(assets|references|scripts)/[A-Za-z0-9_.\-]+")
PLACEHOLDER = re.compile(r"\{\{[A-Z_]+\}\}")
SUPPORTED = re.compile(r'\.replace\("(\{\{[A-Z_]+\}\})"')


def md_files():
    files = []
    for name in ("SKILL.md", "README.md"):
        p = ROOT / name
        if p.is_file():
            files.append(p)
    for sub in ("references", "assets"):
        d = ROOT / sub
        if d.is_dir():
            files.extend(sorted(d.glob("*.md")))
    return files


def check_r1(files):
    checked, missing = 0, []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in PATH_REF.finditer(text):
            token = m.group(0).rstrip(".")
            if "*" in token or "." not in Path(token).name:
                continue
            checked += 1
            if not (ROOT / token).exists():
                missing.append(f"{f.relative_to(ROOT)} → {token}")
    return checked, missing


def check_r2():
    src = (ROOT / "scripts" / "init_project.py").read_text(encoding="utf-8")
    supported = set(SUPPORTED.findall(src))
    used = set(PLACEHOLDER.findall(src))
    for f in sorted((ROOT / "assets").glob("*.md")):
        used.update(PLACEHOLDER.findall(f.read_text(encoding="utf-8")))
    return supported, sorted(used - supported), sorted(supported - used)


def main() -> int:
    files = md_files()
    print(f"扫描范围: {len(files)} 个 Markdown 文件")
    ok = True

    checked, missing = check_r1(files)
    if missing:
        ok = False
        print(f"[✗] R1 路径引用：{len(missing)} 处失效（共检查 {checked} 处）")
        for m in missing:
            print("      - " + m)
    else:
        print(f"[✓] R1 路径引用：{checked} 处全部有效")

    supported, unsupported, unused = check_r2()
    if unsupported:
        ok = False
        print(f"[✗] R2 占位符：存在未支持的键 {unsupported}（render() 未实现替换）")
    else:
        print(f"[✓] R2 占位符：全部已支持（{'、'.join(sorted(supported))}）")
    if unused:
        print(f"[ℹ] 未使用的占位符键: {'、'.join(unused)}")

    print("[i] R3 资源索引一致性：已由 R1 覆盖")
    print()
    print("结论：" + ("全部通过，可发布。" if ok else "存在失效项，请修复后再发布。"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
