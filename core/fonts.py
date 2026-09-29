"""
字体管理器 - 处理中文字体加载 (Windows专用)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import skia
import structlog

logger = structlog.get_logger(__name__)

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
                logger.info("成功加载中文字体(已缓存，进程内复用)", font_path=font_path)
                return _shared_chinese_typeface
        except Exception as e:
            logger.warning("字体加载失败", font_path=font_path, error=str(e))

    logger.warning("未能加载中文字体，中文可能显示为方框")
    return None


class FontManager:
    """字体管理器 - Windows版本"""

    def __init__(self) -> None:
        self.chinese_font: Optional[skia.Typeface] = _ensure_shared_chinese_typeface()
        self._font_template_cache: dict[int, skia.Font] = {}

    def get_font(self, size: int) -> skia.Font:
        """获取指定大小的中文字体。

        调用方普遍会拿到返回值后自行 `setEmbolden(True)` 等原地修改（如两次以相同
        size 调用分别取正常体/粗体 `Font` 用于测量）。若直接缓存并复用同一个
        `skia.Font` 实例，后一次的 mutation 会污染前一次拿到的引用（两者是同一
        对象），导致同 size 的所有渲染/测量意外全部变为粗体。

        因此这里缓存的是每个 size 对应的"未修改模板"，每次调用通过
        `Font.makeWithSize()` 返回一个全新的独立实例（实测比直接
        `skia.Font(typeface, size)` 构造快约 7 倍，因为省去了 typeface 绑定的
        重复开销），调用方可以安全地对返回值做任意原地修改而不影响缓存模板或
        其他调用方。
        """
        template = self._font_template_cache.get(size)
        if template is None:
            template = (
                skia.Font(self.chinese_font, size)
                if self.chinese_font
                else skia.Font(None, size)
            )
            self._font_template_cache[size] = template
        return template.makeWithSize(size)


# 全局单例：EnemyCardGenerator 每次实例化复用同一 FontManager。
_global_font_manager: Optional[FontManager] = None


def get_font_manager() -> FontManager:
    """获取全局字体管理器单例"""
    global _global_font_manager
    if _global_font_manager is None:
        _global_font_manager = FontManager()
    return _global_font_manager
