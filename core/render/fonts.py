"""中文字体加载：随包字体优先，系统字体族兜底。

卡片渲染始终使用随包 HarmonyOS Sans SC，保证同一份数据在不同机器上的字形、测量与换行一致。
随包文件缺失或损坏时才按族名匹配系统中文字体；仍找不到时 `chinese_font` 为 None、
中文按方框渲染，不抛异常（只记一条 warning）。
"""

from __future__ import annotations

from typing import Optional

import skia
import structlog

from utils.app.resources import resource_manager

logger = structlog.get_logger(__name__)

_BUNDLED_FONT_PATH = "resource/fonts/HarmonyOS_Sans_SC_Regular.ttf"

# 随包字体不可用时的兜底顺序；只做族名匹配，不再依赖固定的字体文件路径。
_SYSTEM_FAMILIES = (
    "Microsoft YaHei UI",
    "Microsoft YaHei",
    "SimHei",
    "HarmonyOS Sans SC",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
)

_shared_chinese_typeface: Optional[skia.Typeface] = None
_load_attempted: bool = False


def _load_bundled_typeface() -> Optional[skia.Typeface]:
    """从随包资源加载字体；失败时返回 None，由调用方回退系统字体。"""
    font_path = resource_manager.get_resource_path(_BUNDLED_FONT_PATH)
    try:
        face = skia.Typeface.MakeFromFile(font_path)
    except Exception as error:
        logger.warning("随包字体加载失败", font_path=font_path, error=str(error))
        return None
    if face:
        logger.info("成功加载随包中文字体(已缓存，进程内复用)", font_path=font_path)
    else:
        logger.warning("随包字体无法解析", font_path=font_path)
    return face


def _match_system_typeface() -> Optional[skia.Typeface]:
    """按族名匹配系统中文字体；用于随包字体不可用的兜底路径。"""
    manager = skia.FontMgr()
    for family in _SYSTEM_FAMILIES:
        try:
            face = manager.matchFamilyStyle(family, skia.FontStyle.Normal())
        except Exception as error:
            logger.warning("系统字体匹配失败", family=family, error=str(error))
            continue
        if face:
            logger.info("回退到系统中文字体", family=family)
            return face
    return None


def _ensure_shared_chinese_typeface() -> Optional[skia.Typeface]:
    """进程内只加载一次 Typeface；每次预览新建 FontManager 时复用。"""
    global _shared_chinese_typeface, _load_attempted

    if _shared_chinese_typeface is not None:
        return _shared_chinese_typeface
    if _load_attempted:
        return None
    _load_attempted = True

    _shared_chinese_typeface = _load_bundled_typeface() or _match_system_typeface()
    if _shared_chinese_typeface is None:
        logger.warning("未能加载中文字体，中文可能显示为方框")
    return _shared_chinese_typeface


class FontManager:

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
    global _global_font_manager
    if _global_font_manager is None:
        _global_font_manager = FontManager()
    return _global_font_manager
