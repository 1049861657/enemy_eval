"""wikitext → Skia 绘制用片段 + 按宽度换行。

卡片 JSON 存原文；本模块是渲染时的唯一展开点（属渲染域，见 `core/render/text/`）。已知模板走
`_TEMPLATE_HANDLERS`，未知模板只展示末尾无名参数、永不展开命名参数。纯字符串处理：
不导入 Skia、不读偏好文件。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, replace
from typing import Any, Callable

logger = logging.getLogger(__name__)


def _extract_balanced(s: str, start: int, open_s: str, close_s: str) -> tuple[int, str]:
    if not s.startswith(open_s, start):
        return start, ""
    ol, cl = len(open_s), len(close_s)
    depth = 1
    i = start + ol
    inner_start = i
    n = len(s)
    while i < n:
        if i + ol <= n and s.startswith(open_s, i):
            depth += 1
            i += ol
            continue
        if i + cl <= n and s.startswith(close_s, i):
            depth -= 1
            if depth == 0:
                return i + cl, s[inner_start:i]
            i += cl
            continue
        i += 1
    return n, s[inner_start:]


def _unwrap_bracket_template(inner: str) -> str:
    inner = inner.strip()
    if len(inner) >= 2 and inner[0] == "[" and inner[-1] == "]":
        return inner[1:-1].strip()
    return inner


# [[词条]] / 特殊机制 / 异常效果 — PRTS 超链接展示色
_LINK_TERM_RGBA = (0.14, 0.48, 0.74, 1.0)
# PRTS {{popup}} 默认图标色（模板:Popup 的 --darkblue）
_POPUP_HINT_RGBA = _LINK_TERM_RGBA
# 圆圈问号占位宽度相对正文字号；与 core/render/text/wikitext_renderer.py 绘制口径共用
_HINT_MARK_ADVANCE_RATIO = 0.82
# MediaWiki 把 <br>、<br/>、</br> 都渲成换行（parse HTML 里是 <br />）
_BR_TAG = re.compile(r"</?br\s*/?>", re.IGNORECASE)

# 模板:异常效果 名称别名（PRTS 页面现网）
_STATUS_ALIASES: dict[str, str] = {
    "眩晕": "晕眩",
    "不能阻挡": "不可阻挡",
    "无法阻挡": "不可阻挡",
    "冷冻": "冻结",
    "冰冻": "冻结",
    "隐形": "隐匿",
    "隐型": "隐匿",
    "隐身": "隐匿",
    "睡眠": "沉睡",
    "无法使用技能": "静默",
    "免疫失衡": "失衡免疫",
    "传送": "被传送",
}


def hint_mark_advance(font_size: float) -> float:
    """{{popup}} 圆圈问号的水平步进，须与绘制直径一致，避免换行测算与落笔错位。"""
    return font_size * _HINT_MARK_ADVANCE_RATIO


@dataclass(frozen=True)
class WikiStyle:
    color: tuple[float, float, float, float] | None = None
    bold: bool = False
    dim: bool = False
    underline: bool = False
    hint: bool = False


@dataclass(frozen=True)
class _TemplateCall:
    """一次 {{name|...}}：无名参数按出现顺序；命名参数不进入可见正文。"""

    name: str
    positionals: tuple[str, ...]
    named: dict[str, str]


@dataclass
class TextSpan:
    text: str
    style: WikiStyle


_TemplateHandler = Callable[[_TemplateCall, WikiStyle], list[TextSpan]]


def _style_with(base: WikiStyle, **overrides: Any) -> WikiStyle:
    return replace(base, **overrides)


def _css_color(spec: str) -> tuple[float, float, float, float]:
    s = spec.strip()
    if s.startswith("#") and len(s) >= 7:
        return (
            int(s[1:3], 16) / 255.0,
            int(s[3:5], 16) / 255.0,
            int(s[5:7], 16) / 255.0,
            1.0,
        )
    sl = s.lower()
    if sl == "red":
        return (0.92, 0.25, 0.12, 1.0)
    if sl == "cyan":
        return (0.0, 0.92, 0.92, 1.0)
    if sl == "blue":
        return (0.15, 0.45, 0.85, 1.0)
    logger.debug("_css_color: 未识别的颜色名 %r，回退为默认蓝灰色", spec)
    return (0.2, 0.45, 0.75, 1.0)


def _merge_spans(spans: list[TextSpan]) -> list[TextSpan]:
    if not spans:
        return []
    out: list[TextSpan] = [spans[0]]
    for sp in spans[1:]:
        if sp.style == out[-1].style:
            out[-1] = TextSpan(out[-1].text + sp.text, out[-1].style)
        else:
            out.append(sp)
    return out


def _top_level_eq(chunk: str) -> int:
    """第一个不在嵌套 `{{ }}` / `[[ ]]` 里的 `=`。没有则 -1。"""
    tpl = 0
    link = 0
    i = 0
    n = len(chunk)
    while i < n:
        if chunk.startswith("{{", i):
            tpl += 1
            i += 2
            continue
        if chunk.startswith("}}", i) and tpl:
            tpl -= 1
            i += 2
            continue
        if chunk.startswith("[[", i):
            link += 1
            i += 2
            continue
        if chunk.startswith("]]", i) and link:
            link -= 1
            i += 2
            continue
        if chunk[i] == "=" and tpl == 0 and link == 0:
            return i
        i += 1
    return -1


def _split_top_level_pipes(s: str) -> list[str]:
    """按顶层 `|` 切开，嵌套的 `{{ }}` / `[[ ]]` 内部分隔符不算。"""
    parts: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(s)
    tpl_depth = 0
    link_depth = 0
    while i < n:
        if s.startswith("{{", i):
            tpl_depth += 1
            buf.append("{{")
            i += 2
            continue
        if s.startswith("}}", i) and tpl_depth:
            tpl_depth -= 1
            buf.append("}}")
            i += 2
            continue
        if s.startswith("[[", i):
            link_depth += 1
            buf.append("[[")
            i += 2
            continue
        if s.startswith("]]", i) and link_depth:
            link_depth -= 1
            buf.append("]]")
            i += 2
            continue
        if s[i] == "|" and tpl_depth == 0 and link_depth == 0:
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(s[i])
        i += 1
    parts.append("".join(buf))
    return parts


def _parse_template_call(inner: str) -> _TemplateCall:
    raw = _unwrap_bracket_template(inner.strip())
    chunks = [c.strip() for c in _split_top_level_pipes(raw)]
    if not chunks or not chunks[0]:
        return _TemplateCall(name="", positionals=(), named={})
    name = chunks[0].lstrip("[").strip()
    positionals: list[str] = []
    named: dict[str, str] = {}
    for chunk in chunks[1:]:
        if not chunk:
            continue
        eq = _top_level_eq(chunk)
        if eq > 0:
            key = chunk[:eq].strip()
            if key and " " not in key and "\n" not in key:
                named[key] = chunk[eq + 1 :].strip()
                continue
        positionals.append(chunk)
    return _TemplateCall(name=name, positionals=tuple(positionals), named=named)


def _parse_body(text: str, style: WikiStyle) -> list[TextSpan]:
    if not text:
        return []
    return _parse_inline_spans(text, style)


def _link_term_style(base: WikiStyle) -> WikiStyle:
    return _style_with(base, color=_LINK_TERM_RGBA, bold=True)


def _handle_color(call: _TemplateCall, base: WikiStyle) -> list[TextSpan]:
    spec = call.named.get("1") or (call.positionals[0] if call.positionals else "")
    body = call.named.get("2")
    if body is None:
        body = "|".join(call.positionals[1:]) if len(call.positionals) > 1 else ""
    if not spec or not body:
        return _parse_body(body, base) if body else []
    return _parse_body(body, _style_with(base, color=_css_color(spec)))


def _handle_term(call: _TemplateCall, base: WikiStyle) -> list[TextSpan]:
    display = call.named.get("术语") or (
        call.positionals[1]
        if len(call.positionals) > 1
        else (call.positionals[0] if call.positionals else "")
    )
    if not display:
        return []
    return _parse_body(display, _style_with(base, underline=True))


def _handle_status(call: _TemplateCall, base: WikiStyle) -> list[TextSpan]:
    raw_name = call.named.get("名称") or (
        call.positionals[0] if call.positionals else "未知"
    )
    canonical = _STATUS_ALIASES.get(raw_name, raw_name)
    suffix = call.positionals[1] if len(call.positionals) > 1 else ""
    override = call.named.get("显示名称")
    if override is None and len(call.positionals) > 2:
        override = call.positionals[2]
    label = override if override else f"{canonical}{suffix}"
    return [TextSpan(label, _link_term_style(base))]


def _handle_special(call: _TemplateCall, base: WikiStyle) -> list[TextSpan]:
    label = call.named.get("名称") or (
        call.positionals[0] if call.positionals else "未知"
    )
    if "color" in call.named:
        st = _style_with(base, color=_css_color(call.named["color"]), bold=True)
    else:
        st = _link_term_style(base)
    return [TextSpan(label, st)]


def _handle_delta(call: _TemplateCall, base: WikiStyle) -> list[TextSpan]:
    value = call.named.get("1") or (call.positionals[0] if call.positionals else "")
    if not value:
        return []
    return _parse_body(value, base)


def _handle_popup(_call: _TemplateCall, _base: WikiStyle) -> list[TextSpan]:
    return [TextSpan("?", WikiStyle(color=_POPUP_HINT_RGBA, hint=True))]


def _handle_popup_range(_call: _TemplateCall, _base: WikiStyle) -> list[TextSpan]:
    """范围图是 Widget:Range/<代号> 的 SVG，只在悬停弹层里。卡片不展示代号。"""
    return []


def _handle_unknown(call: _TemplateCall, base: WikiStyle) -> list[TextSpan]:
    """未知模板：只展示末尾无名参数（常见「标识|可见名」），永不展开命名参数。"""
    if call.positionals:
        visible = call.positionals[-1]
        logger.debug(
            "_handle_unknown: 模板 %r 无专用处理器，展示末尾无名参数", call.name
        )
        return _parse_body(visible, base)
    logger.debug("_handle_unknown: 模板 %r 仅有命名参数，跳过", call.name)
    return []


_TEMPLATE_HANDLERS: dict[str, _TemplateHandler] = {
    "color": _handle_color,
    "术语": _handle_term,
    "异常效果": _handle_status,
    "特殊机制": _handle_special,
    "变动数值": _handle_delta,
    "popup": _handle_popup,
    "popup/range": _handle_popup_range,
}


def _render_template_spans(inner: str, base: WikiStyle) -> list[TextSpan]:
    call = _parse_template_call(inner)
    if not call.name:
        return [TextSpan(inner, base)]
    handler = _TEMPLATE_HANDLERS.get(call.name.casefold())
    if handler is None:
        return _handle_unknown(call, base)
    return handler(call, base)


def _render_link_spans(inner: str, base: WikiStyle) -> list[TextSpan]:
    inner = inner.strip()
    parts = inner.split("|")
    display = parts[-1].strip() if len(parts) > 1 else parts[0].strip()
    return [TextSpan(display, _link_term_style(base))]


def _flush_plain_spans(s: str, start: int, end: int, base: WikiStyle) -> list[TextSpan]:
    if start >= end:
        return []
    raw = s[start:end]
    parts = re.split(r"(※[^\n]*)", raw)
    out: list[TextSpan] = []
    for part in parts:
        if not part:
            continue
        if part.startswith("※"):
            out.append(TextSpan(part, _style_with(base, dim=True)))
        else:
            out.append(TextSpan(part, base))
    return out


def _parse_inline_spans(s: str, base: WikiStyle) -> list[TextSpan]:
    out: list[TextSpan] = []
    i = 0
    n = len(s)
    start = 0

    while i < n:
        if s.startswith("'''", i):
            out.extend(_flush_plain_spans(s, start, i, base))
            end = s.find("'''", i + 3)
            if end < 0:
                i += 1
                continue
            out.extend(_parse_inline_spans(s[i + 3 : end], _style_with(base, bold=True)))
            i = end + 3
            start = i
            continue

        if s.startswith("{{", i):
            out.extend(_flush_plain_spans(s, start, i, base))
            i, body = _extract_balanced(s, i, "{{", "}}")
            out.extend(_render_template_spans(body, base))
            start = i
            continue

        if s.startswith("[[", i):
            out.extend(_flush_plain_spans(s, start, i, base))
            i, body = _extract_balanced(s, i, "[[", "]]")
            out.extend(_render_link_spans(body, base))
            start = i
            continue

        br = _BR_TAG.match(s, i)
        if br is not None:
            out.extend(_flush_plain_spans(s, start, i, base))
            out.append(TextSpan("\n", base))
            i = br.end()
            start = i
            continue

        if s[i] == "\n":
            out.extend(_flush_plain_spans(s, start, i, base))
            out.append(TextSpan("\n", base))
            i += 1
            start = i
            continue

        i += 1

    out.extend(_flush_plain_spans(s, start, n, base))
    return _merge_spans(out)


def parse_wikitext_to_spans(text: str, base: WikiStyle = WikiStyle()) -> list[TextSpan]:
    """整段 wikitext → 扁平片段列表。

    `<br>`、`<br/>`、`</br>` 与裸换行在模板/链接外部才拆行；模板内部（含 `{{popup|内容=...}}`）
    由对应处理器决定可见文本，不会把注释后半段漏到正文。
    """
    if not text:
        return []
    return _parse_inline_spans(text.replace("\r\n", "\n"), base)


def wrap_spans_to_lines(
    spans: list[TextSpan],
    max_width: float,
    measure: Callable[[str, WikiStyle], float],
) -> list[list[TextSpan]]:
    """按像素宽度硬换行；保留片段样式。"""
    flat: list[tuple[str, WikiStyle]] = []
    for sp in spans:
        for ch in sp.text:
            flat.append((ch, sp.style))

    lines_chars: list[list[tuple[str, WikiStyle]]] = []
    cur: list[tuple[str, WikiStyle]] = []
    wsum = 0.0

    for ch, st in flat:
        if ch == "\n":
            lines_chars.append(cur)
            cur = []
            wsum = 0.0
            continue
        cw = measure(ch, st)
        if wsum + cw > max_width and cur:
            lines_chars.append(cur)
            cur = [(ch, st)]
            wsum = cw
        else:
            cur.append((ch, st))
            wsum += cw
    lines_chars.append(cur)

    def merge_chars(chars: list[tuple[str, WikiStyle]]) -> list[TextSpan]:
        if not chars:
            return []
        buf = chars[0][0]
        st = chars[0][1]
        row: list[TextSpan] = []
        for ch, s in chars[1:]:
            if s == st:
                buf += ch
            else:
                row.append(TextSpan(buf, st))
                buf = ch
                st = s
        row.append(TextSpan(buf, st))
        return row

    return [merge_chars(L) for L in lines_chars]
