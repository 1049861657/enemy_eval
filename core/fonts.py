"""
字体管理器 - 处理中文字体加载 (Windows专用)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import skia

_FONT_PATHS = (
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/SIMHEI.TTF",
)

_shared_chinese_typeface: Optional[skia.Typeface] = None
_load_attempted: bool = False


def _ensure_shared_chinese_typeface() -> Optional[skia.Typeface]:
    """进程内只从磁盘加载一次 Typeface；每次预览新建 FontManager 时复用。"""
    global _shared_chinese_typeface, _load_attempted

    if _shared_chinese_typeface is not None:
        return _shared_chinese_typeface
    if _load_attempted:
        return None
    _load_attempted = True

    for font_path in _FONT_PATHS:
        p = Path(font_path)
        if not p.exists():
            continue
        try:
            face = skia.Typeface.MakeFromFile(str(p))
            if face:
                _shared_chinese_typeface = face
                print(f"成功加载中文字体(已缓存，进程内复用): {font_path}")
                return _shared_chinese_typeface
        except Exception as e:
            print(f"字体加载失败 {font_path}: {e}")

    print("警告: 未能加载中文字体，中文可能显示为方框")
    return None


class FontManager:
    """字体管理器 - Windows版本"""

    def __init__(self) -> None:
        self.chinese_font: Optional[skia.Typeface] = _ensure_shared_chinese_typeface()

    def get_font(self, size: int) -> skia.Font:
        """获取指定大小的中文字体"""
        if self.chinese_font:
            return skia.Font(self.chinese_font, size)
        return skia.Font(None, size)
