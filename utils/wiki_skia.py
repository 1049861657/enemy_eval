"""wikitext → Skia 绘制用片段 + 按宽度换行（仅供卡片渲染）。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable


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


# [[词条]] — PRTS 式专有名词 / 超链接展示色（与正文区分）
_LINK_TERM_RGBA = (0.14, 0.48, 0.74, 1.0)


@dataclass(frozen=True)
class WikiStyle:
    color: tuple[float, float, float, float] | None = None
    bold: bool = False
    dim: bool = False
    underline: bool = False


@dataclass
class TextSpan:
    text: str
    style: WikiStyle


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


def _render_template_spans(inner: str, base: WikiStyle) -> list[TextSpan]:
    inner_u = _unwrap_bracket_template(inner.strip())
    parts = inner_u.split("|")
    if not parts:
        return [TextSpan(inner, base)]

    key = parts[0].strip().lower().lstrip("[")

    if key == "color" and len(parts) >= 3:
        col = _css_color(parts[1])
        body = "|".join(parts[2:])
        sub = _parse_inline_spans(
            body,
            WikiStyle(
                color=col,
                bold=base.bold,
                dim=base.dim,
                underline=base.underline,
            ),
        )
        return sub

    if key == "术语" and len(parts) >= 2:
        display = parts[-1].strip()
        st = WikiStyle(
            color=base.color,
            bold=base.bold,
            dim=base.dim,
            underline=True,
        )
        return [TextSpan(display, st)]

    if key == "异常效果" and len(parts) >= 3:
        t = f"{parts[1].strip()}{parts[2].strip()}"
        return [TextSpan(t, base)]

    if key == "变动数值" and len(parts) >= 2:
        return [TextSpan(parts[1].strip(), base)]

    if len(parts) >= 2:
        return _parse_inline_spans("|".join(parts[1:]), base)

    return [TextSpan(inner_u, base)]


def _render_link_spans(inner: str, base: WikiStyle) -> list[TextSpan]:
    inner = inner.strip()
    parts = inner.split("|")
    display = parts[-1].strip() if len(parts) > 1 else parts[0].strip()
    st = WikiStyle(
        color=_LINK_TERM_RGBA, bold=True, dim=base.dim, underline=base.underline
    )
    return [TextSpan(display, st)]


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
            out.append(
                TextSpan(
                    part,
                    WikiStyle(
                        dim=True,
                        bold=base.bold,
                        color=base.color,
                        underline=base.underline,
                    ),
                )
            )
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
            inner_base = WikiStyle(
                color=base.color,
                bold=True,
                dim=base.dim,
                underline=base.underline,
            )
            out.extend(_parse_inline_spans(s[i + 3 : end], inner_base))
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

        i += 1

    out.extend(_flush_plain_spans(s, start, n, base))
    return _merge_spans(out)


def wikitext_logical_lines(text: str) -> list[str]:
    if not text:
        return []
    t = text.replace("\r\n", "\n")
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.IGNORECASE)
    return t.split("\n")


def parse_wikitext_to_spans(text: str, base: WikiStyle = WikiStyle()) -> list[TextSpan]:
    """整段 wikitext → 扁平片段列表（含换行符前的行分别解析后拼接）。"""
    lines = wikitext_logical_lines(text)
    acc: list[TextSpan] = []
    for li, line in enumerate(lines):
        if li > 0:
            acc.append(TextSpan("\n", base))
        acc.extend(_parse_inline_spans(line, base))
    return _merge_spans(acc)


def wrap_spans_to_lines(
    spans: list[TextSpan],
    max_width: float,
    measure: Callable[[str, bool], float],
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
        cw = measure(ch, st.bold)
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
