"""wikitext 模板手写递归下降解析器 —— 纯字符串处理，零外部依赖。

只负责从原始 wikitext 中抠出 `{{模板名|...}}` 的文本边界与参数键值对，
不理解任何业务字段含义（字段名映射见 utils/prts_field_mapping.py）。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# 模板名之后允许紧跟的字符：`|`（带参数）、`{`（罕见，模板名本身以此开头是不合法输入）、
# `}`（无参数模板 `{{名称}}`）、空白/换行。其余字符说明是"更长模板名的前缀误匹配"。
_TEMPLATE_NAME_BOUNDARY = "|{ \t\n\r"


def _extract_template_body(wikitext: str, template_name: str) -> str | None:
    prefix = "{{" + template_name
    idx = wikitext.find(prefix)
    if idx < 0:
        return None
    tail = idx + len(prefix)
    if tail < len(wikitext) and wikitext[tail] not in _TEMPLATE_NAME_BOUNDARY:
        logger.debug(
            "模板名 %r 后紧跟字符 %r 不在允许边界集合内，判定为更长模板名的前缀误匹配",
            template_name, wikitext[tail],
        )
        return None
    start = tail
    i = start
    depth = 1
    n = len(wikitext)
    while i < n - 1:
        if wikitext[i : i + 2] == "{{":
            depth += 1
            i += 2
            continue
        if wikitext[i : i + 2] == "}}":
            depth -= 1
            i += 2
            if depth == 0:
                return wikitext[start : i - 2]
            continue
        i += 1
    logger.debug("模板 %r 未找到匹配的闭合 '}}'，视为未闭合模板", template_name)
    return None


def _extract_all_template_bodies(wikitext: str, template_name: str) -> list[str]:
    bodies: list[str] = []
    prefix = "{{" + template_name
    pos = 0
    while True:
        idx = wikitext.find(prefix, pos)
        if idx < 0:
            break
        tail = idx + len(prefix)
        if tail < len(wikitext) and wikitext[tail] not in _TEMPLATE_NAME_BOUNDARY:
            pos = idx + 1
            continue
        start = tail
        i = start
        depth = 1
        n = len(wikitext)
        ok = False
        while i < n - 1:
            if wikitext[i : i + 2] == "{{":
                depth += 1
                i += 2
                continue
            if wikitext[i : i + 2] == "}}":
                depth -= 1
                i += 2
                if depth == 0:
                    bodies.append(wikitext[start : i - 2])
                    pos = i
                    ok = True
                    break
                continue
            i += 1
        if not ok:
            logger.debug(
                "模板 %r 第 %d 个匹配位置起未找到闭合 '}}'，停止继续扫描", template_name, len(bodies) + 1
            )
            break
    return bodies


def _parse_template_params(inner: str) -> dict[str, str]:
    params: dict[str, str] = {}
    i = 0
    n = len(inner)
    while i < n:
        while i < n and inner[i] in " \t\n\r":
            i += 1
        if i >= n:
            break
        if inner[i] != "|":
            i += 1
            continue
        i += 1
        key_start = i
        while i < n and inner[i] != "=":
            i += 1
        if i >= n:
            break
        key = inner[key_start:i].strip()
        i += 1
        val_start = i
        depth_sq = 0
        depth_br = 0
        com = 0
        while i < n:
            if com > 0:
                if inner[i : i + 3] == "-->":
                    com -= 1
                    i += 3
                    continue
                if inner[i : i + 4] == "<!--":
                    com += 1
                    i += 4
                    continue
                i += 1
                continue
            if inner[i : i + 4] == "<!--":
                com += 1
                i += 4
                continue
            if inner[i : i + 2] == "[[":
                depth_sq += 1
                i += 2
                continue
            if inner[i : i + 2] == "]]":
                depth_sq = max(0, depth_sq - 1)
                i += 2
                continue
            if inner[i : i + 2] == "{{":
                depth_br += 1
                i += 2
                continue
            if inner[i : i + 2] == "}}":
                depth_br = max(0, depth_br - 1)
                i += 2
                continue
            if inner[i] == "|" and depth_sq == 0 and depth_br == 0:
                break
            i += 1
        val = inner[val_start:i].strip()
        if key:
            params[key] = val
    return params
