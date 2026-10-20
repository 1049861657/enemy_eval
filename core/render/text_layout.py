"""纯文本按宽度换行与布局缓存：中文避头尾、制表符（按 4 空格展开）、主动换行符。

只服务渲染；wikitext 富文本的解析与绘制见 `core/render/text/`。
换行规则只在本模块维护一处，`EnemyCardGenerator._wrap_text` 是唯一对外委托点。
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import List, Optional

import skia

from .config import RenderConfig
from .font_cache import get_font

_CONFIG = RenderConfig()
_text_layout_cache: dict[str, TextLayoutResult] = {}
_text_cache_hits: int = 0


@dataclass
class TextLayoutResult:
    """文本布局结果缓存"""
    lines: List[str]
    total_height: float
    max_width: float
    line_height: float
    timestamp: float = field(default_factory=time.time)


def get_text_layout(
    text: str,
    max_width: int,
    font_size: int,
    typeface: Optional[skia.Typeface] = None,
) -> TextLayoutResult:
    """取文本布局：命中未过期缓存直接返回，否则按 `max_width` 换行后缓存。

    `line_height` 取字号 × 1.2；缓存条数超 `RenderConfig.text_cache_size` 时淘汰最旧一项。
    """
    global _text_cache_hits
    # 生成缓存键
    cache_key = hashlib.md5(
        f"{text}_{max_width}_{font_size}_{id(typeface)}".encode()
    ).hexdigest()

    # 检查缓存
    if cache_key in _text_layout_cache:
        result = _text_layout_cache[cache_key]
        # 检查是否过期
        if time.time() - result.timestamp < _CONFIG.cache_expire_seconds:
            _text_cache_hits += 1
            return result
        else:
            # 过期清理
            del _text_layout_cache[cache_key]

    # 缓存未命中，重新计算
    font = get_font(font_size, typeface)
    lines = wrap_text_optimized(text, max_width, font)

    # 计算布局信息
    line_height = font_size * 1.2  # 行高系数
    total_height = len(lines) * line_height
    max_actual_width = max((font.measureText(line) for line in lines), default=0)

    result = TextLayoutResult(
        lines=lines,
        total_height=total_height,
        max_width=max_actual_width,
        line_height=line_height,
    )

    # 缓存结果（LRU清理）
    if len(_text_layout_cache) >= _CONFIG.text_cache_size:
        # 清理最旧的缓存项
        oldest_key = min(_text_layout_cache.keys(), key=lambda k: _text_layout_cache[k].timestamp)
        del _text_layout_cache[oldest_key]

    _text_layout_cache[cache_key] = result
    return result


def wrap_text_optimized(text: str, max_width: int, font: skia.Font) -> List[str]:
    """文本换行：中文避头尾规则、主动换行符、制表符。"""
    if not text:
        return [""]

    # 处理制表符 - 转换为4个空格
    if '\t' in text:
        text = text.replace('\t', '    ')

    # 处理主动换行符
    if '\n' in text:
        manual_lines = text.split('\n')
        result_lines = []
        for line in manual_lines:
            if line:
                result_lines.extend(wrap_text_optimized(line, max_width, font))
            else:
                result_lines.append("")
        return result_lines

    if font.measureText(text) <= max_width:
        return [text]

    # 避头尾规则定义
    cannot_start_line = "，。！？；、）】｝\"'》』"  # 不能在行首的字符
    cannot_end_line = "\"'（【｛《「"  # 不能在行尾的字符

    lines = []
    current_line = ""
    i = 0

    while i < len(text):
        char = text[i]
        test_line = current_line + char

        # 检查当前字符是否能放在当前行
        if font.measureText(test_line) <= max_width:
            current_line = test_line
            i += 1
        else:
            # 当前字符放不下，需要换行
            if current_line:
                # 检查避头尾规则
                final_line = current_line
                next_char = char

                # 如果下一个字符不能在行首，尝试将其挤到当前行
                if next_char in cannot_start_line:
                    # 尝试移动当前行最后的一些字符到下一行
                    if len(current_line) > 1:
                        # 找到合适的断点
                        for j in range(len(current_line) - 1, 0, -1):
                            split_char = current_line[j-1]
                            if split_char not in cannot_end_line:
                                # 在这里分割
                                final_line = current_line[:j]
                                remaining = current_line[j:] + next_char
                                if font.measureText(remaining) <= max_width:
                                    lines.append(final_line)
                                    current_line = remaining
                                    i += 1
                                    break
                        else:
                            # 找不到合适断点，强制换行
                            lines.append(current_line)
                            current_line = next_char
                            i += 1
                    else:
                        # 当前行只有一个字符，强制换行
                        lines.append(current_line)
                        current_line = next_char
                        i += 1
                else:
                    # 正常换行
                    lines.append(current_line)
                    current_line = next_char
                    i += 1
            else:
                # 当前行为空，单个字符就超宽，强制添加
                current_line = char
                i += 1

    if current_line:
        lines.append(current_line)

    return lines if lines else [""]


def clear_text_layout_cache() -> None:
    """清空文本布局缓存；应用退出前经 `core/render/canvas_pool.py::clear_caches` 调用一次。"""
    _text_layout_cache.clear()
