"""头像路径的存储形式与使用形式互转；基准目录始终是配置文件所在目录。

存储形式（写进 JSON）尽量是相对路径，让配置能随图片目录一起搬动；使用形式（内存中）
始终是可直接渲染的路径。Windows 上跨盘无法表示相对路径（`os.path.relpath` 抛
`ValueError`），此时保留绝对路径。
"""

from __future__ import annotations

import os
from pathlib import Path

from models.media import is_url


def to_stored_path(path: str, base_dir: Path) -> str:
    """转为存储形式：同盘绝对路径转相对；跨盘保留绝对；URL 与相对路径原样。"""
    if not path or is_url(path):
        return path
    source = Path(path)
    if not source.is_absolute():
        return path
    try:
        return os.path.relpath(source, base_dir)
    except ValueError:
        return str(source)


def resolve_stored_path(stored: str, base_dir: Path) -> str:
    """转为使用形式：相对路径基于 base_dir 展开；绝对路径与 URL 原样。"""
    if not stored or is_url(stored):
        return stored
    candidate = Path(stored)
    if candidate.is_absolute():
        return stored
    return str((base_dir / candidate).resolve())
