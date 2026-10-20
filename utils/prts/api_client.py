"""PRTS MediaWiki API 客户端：端点、请求参数与原始 JSON 拉取。

只负责网络层：不理解 wikitext 语义（见 utils/prts/wikitext_templates.py /
utils/prts/field_mapping.py），也不组装 Pydantic 模型（见 utils/prts/enemy_builder.py）。
超时与重试策略取自 utils/net/transport.py。
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from ..net.transport import (
    CONNECT_TIMEOUT,
    build_retry_transport,
    build_timeout,
    log_http_version,
)

logger = logging.getLogger(__name__)

PRTS_MEDIAWIKI_API = "https://prts.wiki/api.php"

# PRTS 前置 Tengine 会拦截「Mozilla UA 但缺少 Accept-Language」的请求（403）。
# 不携带项目名、版本或仓库地址。
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}

DEFAULT_TIMEOUT_PARSE = 22.0
DEFAULT_TIMEOUT_IMAGEINFO = 12.0
# resolve 是精确定位页面标题的加分项：失败/超时直接退回裸名 parse。
RESOLVE_TIMEOUT = 4.0


def request_timeout(read: float) -> httpx.Timeout:
    """PRTS 三档 read 超时（parse 22 / imageinfo 12 / ask 4）；connect 与 pool 固定 CONNECT_TIMEOUT。"""
    return build_timeout(connect=CONNECT_TIMEOUT, read=read)


def build_async_client() -> httpx.AsyncClient:
    """带默认 headers、超时、连接重试与 502/503/504 重试的异步客户端。"""
    return httpx.AsyncClient(
        http2=True,
        headers=DEFAULT_HEADERS,
        timeout=request_timeout(DEFAULT_TIMEOUT_PARSE),
        transport=build_retry_transport(async_mode=True),
        follow_redirects=True,
    )


def build_client() -> httpx.Client:
    """同步客户端，headers/超时/重试与异步客户端一致（smoke 脚本使用）。"""
    return httpx.Client(
        http2=True,
        headers=DEFAULT_HEADERS,
        timeout=request_timeout(DEFAULT_TIMEOUT_PARSE),
        transport=build_retry_transport(async_mode=False),
        follow_redirects=True,
    )


async def _fetch_parse_json(
    client: httpx.AsyncClient,
    page_title: str,
    timeout: float = DEFAULT_TIMEOUT_PARSE,
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """请求 MediaWiki `action=parse`，返回 `(json, None)` 或 `(None, error_message)`。"""
    try:
        r = await client.get(
            PRTS_MEDIAWIKI_API,
            params={
                "action": "parse",
                "page": page_title,
                "prop": "text|wikitext",
                "format": "json",
                "formatversion": "2",
            },
            timeout=request_timeout(timeout),
        )
        r.raise_for_status()
        log_http_version(r)
        return r.json(), None
    except httpx.HTTPError as e:
        return None, str(e)


async def resolve_enemy_page_title(
    client: httpx.AsyncClient,
    enemy_name: str,
    timeout: float = RESOLVE_TIMEOUT,
) -> tuple[Optional[str], Optional[str]]:
    """用 Semantic MediaWiki 的 `action=ask` 按敌人信息模板写入的语义属性 `名称` 精确定位页面标题。

    PRTS 的 `{{敌人信息/common2}}` 模板对每个敌人页面执行 `{{#set:名称=...}}[[分类:敌人]]`，
    因此 `[[分类:敌人]][[名称::<name>]]` 能唯一命中敌人页——无论该页面是否需要用
    `(敌方)`/`(敌人)`/`(我方)` 等后缀与同名干员/道具页消歧义（PRTS 对此并无统一规则，
    猜测后缀会漏掉如 `变格博士(敌人)` 这类情况）。

    这只是精确定位页面标题的加分项而非必需项——多数敌人裸名本来就直接命中页面。
    单次请求用短 read 超时，避免 ask 抖动拖累 ask → parse → imageinfo 串行链路。

    返回 `(page_title, None)`；未命中返回 `(None, None)`；网络错误返回 `(None, error_message)`。
    """
    query = f"[[分类:敌人]][[名称::{enemy_name}]]"
    try:
        r = await client.get(
            PRTS_MEDIAWIKI_API,
            params={
                "action": "ask",
                "query": query,
                "format": "json",
            },
            timeout=request_timeout(timeout),
        )
        r.raise_for_status()
        log_http_version(r)
        j = r.json()
    except httpx.HTTPError as e:
        return None, str(e)

    if "error" in j:
        return None, None

    results = j.get("query", {}).get("results")
    if not results:
        return None, None
    if isinstance(results, dict):
        titles = list(results.keys())
        return (titles[0], None) if titles else (None, None)
    return None, None


async def fetch_avatar_imageinfo(
    client: httpx.AsyncClient,
    enemy_name: str,
    timeout: float = DEFAULT_TIMEOUT_IMAGEINFO,
) -> tuple[Optional[str], dict[str, Any]]:
    """查询敌人头像文件的 imageinfo，返回 `(去除查询串的 URL 或 None, 原始响应/错误)`。"""
    file_title = f"文件:头像_敌人_{enemy_name}.png"
    try:
        r = await client.get(
            PRTS_MEDIAWIKI_API,
            params={
                "action": "query",
                "titles": file_title,
                "prop": "imageinfo",
                "iiprop": "url",
                "format": "json",
                "formatversion": "2",
            },
            timeout=request_timeout(timeout),
        )
        r.raise_for_status()
        log_http_version(r)
        data = r.json()
        pages = data.get("query", {}).get("pages", [])
        if not pages or pages[0].get("missing"):
            return None, data
        infos = pages[0].get("imageinfo") or []
        if not infos:
            return None, data
        url = infos[0].get("url")
        clean = url.split("?")[0] if url else None
        return clean, data
    except Exception as e:
        logger.debug("imageinfo 头像查询失败: %s", e)
        return None, {"error": str(e)}
