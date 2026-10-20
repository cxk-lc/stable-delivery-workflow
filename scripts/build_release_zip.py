#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建发布用技能包 zip（维护者用）。

固定规则:
    - 顶层目录 = SKILL.md frontmatter 的 name（如 stable-delivery-workflow/）
    - 固定排除 .git/、.github/、.gitignore、__pycache__/、.pytest_cache/、*.pyc 等
    - 默认输出 <包名>.zip（通用名，如 stable-delivery-workflow.zip）

用法:
    python scripts/build_release_zip.py [--output PATH]
"""
import argparse
import hashlib
import os
import re
import sys
import zipfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {".git", ".github", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
EXCLUDE_FILES = {".gitignore", ".DS_Store", "Thumbs.db"}
EXCLUDE_SUFFIXES = (".pyc", ".pyo")


def package_name() -> str:
    """读取 SKILL.md 的 name 作为包名；失败时回退目录名。"""
    try:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    except OSError:
        return ROOT.name
    m = re.search(r"^name:[ \t]*([a-z0-9-]+)[ \t]*$", text, re.M)
    return m.group(1) if m else ROOT.name


def build(output: Path) -> tuple:
    """生成 zip；返回 (包名, 文件数, SHA256)。"""
    name = package_name()
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS)
            for fn in sorted(filenames):
                if fn in EXCLUDE_FILES or fn.endswith(EXCLUDE_SUFFIXES):
                    continue
                full = Path(dirpath) / fn
                if full.resolve() == output:
                    continue
                rel = full.relative_to(ROOT).as_posix()
                z.write(full, f"{name}/{rel}")
                count += 1
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return name, count, digest


def main() -> int:
    parser = argparse.ArgumentParser(description="构建发布用技能包 zip（固定排除 .gitignore）")
    parser.add_argument("--output", default=None, help="输出 zip 路径（默认：仓库上级目录/<包名>.zip）")
    args = parser.parse_args()

    name = package_name()
    output = Path(args.output).expanduser() if args.output else ROOT.parent / f"{name}.zip"
    try:
        name, count, digest = build(output)
    except OSError as exc:
        print(f"[x] 构建失败: {exc}")
        return 1

    print(f"包名: {name}")
    print(f"文件数: {count}")
    print(f"输出: {output.resolve()}")
    print(f"SHA256: {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
