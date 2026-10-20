"""保存/导出用的文件名消毒。"""

from __future__ import annotations

_UNSAFE_CHARS = '\\/:*?"<>|'


def safe_filename(name: str) -> str:
    """把不能出现在文件名中的字符换成 `_`；全空则 `untitled`。"""
    cleaned = "".join("_" if ch in _UNSAFE_CHARS else ch for ch in name).strip()
    return cleaned or "untitled"
