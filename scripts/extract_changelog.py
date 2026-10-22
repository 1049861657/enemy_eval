#!/usr/bin/env python3
"""从 CHANGELOG.md 提取指定版本的发布说明。

版本标题精确匹配 `## [X.Y.Z]`，可带日期后缀；正文截取到下一个二级标题，
去掉版本标题与末尾分隔线。找不到版本节或正文为空时以非零状态退出。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG_PATH = ROOT / "CHANGELOG.md"


def extract_version_section(markdown: str, version: str) -> str:
    """返回版本节正文；不含版本标题，保留分类标题与条目。"""
    normalized = version.strip().removeprefix("v")
    if re.fullmatch(r"\d+\.\d+\.\d+", normalized) is None:
        raise ValueError(f"版本号格式应为 X.Y.Z：{version}")

    heading = re.compile(
        rf"^## \[{re.escape(normalized)}\](?:\s*-\s*\d{{4}}-\d{{2}}-\d{{2}})?\s*$"
    )
    lines = markdown.splitlines()
    start = None
    for index, line in enumerate(lines):
        if heading.match(line.strip()):
            start = index + 1
            break
    if start is None:
        raise ValueError(f"CHANGELOG.md 缺少 ## [{normalized}] 版本节")

    end = len(lines)
    for index in range(start, len(lines)):
        if re.match(r"^##\s+", lines[index]):
            end = index
            break

    body = lines[start:end]
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()
    while body and body[-1].strip() in {"---", "***", "___"}:
        body.pop()
        while body and not body[-1].strip():
            body.pop()
    if not any(line.strip() for line in body):
        raise ValueError(f"CHANGELOG.md 的 ## [{normalized}] 版本节为空")
    return "\n".join(body).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="提取 CHANGELOG 指定版本的正文")
    parser.add_argument("version", help="版本号，例如 0.6.0；也接受 v0.6.0")
    parser.add_argument("--output", type=Path, help="写入文件；省略时输出到标准输出")
    args = parser.parse_args()

    try:
        markdown = CHANGELOG_PATH.read_text(encoding="utf-8")
        notes = extract_version_section(markdown, args.version)
    except (OSError, ValueError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1

    if args.output is None:
        sys.stdout.write(notes)
        return 0

    try:
        args.output.write_text(notes, encoding="utf-8", newline="\n")
    except OSError as error:
        print(f"错误：写入 {args.output} 失败：{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
