"""PRTS MediaWiki API 客户端：Session 管理、超时、重试、原始 JSON 拉取。

只负责网络层：不理解 wikitext 语义（见 utils/wiki_template_parser.py /
utils/prts_field_mapping.py），也不组装 Pydantic 模型（见 utils/prts_enemy_builder.py）。
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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

# 统一超时常量：原实现里 12.0/22.0/10/30.0 四处不同数值散落在函数默认参数中。
DEFAULT_TIMEOUT_PARSE = 22.0
DEFAULT_TIMEOUT_IMAGEINFO = 12.0
# resolve_enemy_page_title 是精确定位页面标题的“加分项”而非必需项：失败/超时直接退回
# 裸名 parse 即可（多数敌人裸名本来就命中）。给它更短的超时+零重试，避免 PRTS 源站
# 瞬时抖动（Varnish 502/503）时，因 session 级重试的指数退避把单次查询拖到 10+ 秒，
# 拖累整条串行链路（ask → parse → imageinfo）。
RESOLVE_TIMEOUT = 4.0

_RETRY_TOTAL = 2
_RETRY_BACKOFF_FACTOR = 0.5
_RETRY_STATUS_FORCELIST = (502, 503, 504)


def _build_session_with_retry(retry_total: int, backoff_factor: float) -> requests.Session:
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    retry = Retry(
        total=retry_total,
        backoff_factor=backoff_factor,
        status_forcelist=_RETRY_STATUS_FORCELIST,
        allowed_methods=frozenset({"GET"}),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def build_session() -> requests.Session:
    """创建带默认 headers + 有限重试策略的 Session，消除单次网络抖动即整体失败的脆弱性。"""
    return _build_session_with_retry(_RETRY_TOTAL, _RETRY_BACKOFF_FACTOR)


def _fetch_parse_json(
    session: requests.Session, page_title: str, timeout: float = DEFAULT_TIMEOUT_PARSE
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """请求 MediaWiki `action=parse`，返回 `(json, None)` 或 `(None, error_message)`。"""
    try:
        r = session.get(
            PRTS_MEDIAWIKI_API,
            params={
                "action": "parse",
                "page": page_title,
                "prop": "text|wikitext",
                "format": "json",
                "formatversion": "2",
            },
            timeout=timeout,
        )
        r.raise_for_status()
        return r.json(), None
    except requests.RequestException as e:
        return None, str(e)


def resolve_enemy_page_title(
    enemy_name: str, timeout: float = RESOLVE_TIMEOUT
) -> tuple[Optional[str], Optional[str]]:
    """用 Semantic MediaWiki 的 `action=ask` 按敌人信息模板写入的语义属性 `名称` 精确定位页面标题。

    PRTS 的 `{{敌人信息/common2}}` 模板对每个敌人页面执行 `{{#set:名称=...}}[[分类:敌人]]`，
    因此 `[[分类:敌人]][[名称::<name>]]` 能唯一命中敌人页——无论该页面是否需要用
    `(敌方)`/`(敌人)`/`(我方)` 等后缀与同名干员/道具页消歧义（PRTS 对此并无统一规则，
    猜测后缀会漏掉如 `变格博士(敌人)` 这类情况）。

    这只是精确定位页面标题的“加分项”而非必需项——多数敌人裸名本来就直接命中页面。
    因此这里用独立的零重试、短超时 Session：PRTS 源站偶发 502/503 抖动时快速失败，
    交由调用方退回裸名 parse，而不是吃满 session 级重试的指数退避（可能长达数秒到
    十余秒），拖累 ask → parse → imageinfo 这条串行链路的整体延迟。

    返回 `(page_title, None)`；未命中返回 `(None, None)`；网络错误返回 `(None, error_message)`。
    """
    query = f"[[分类:敌人]][[名称::{enemy_name}]]"
    session = _build_session_with_retry(retry_total=0, backoff_factor=0)
    try:
        r = session.get(
            PRTS_MEDIAWIKI_API,
            params={
                "action": "ask",
                "query": query,
                "format": "json",
            },
            timeout=timeout,
        )
        r.raise_for_status()
        j = r.json()
    except requests.RequestException as e:
        return None, str(e)
    finally:
        session.close()

    if "error" in j:
        return None, None

    results = j.get("query", {}).get("results")
    if not results:
        return None, None
    if isinstance(results, dict):
        titles = list(results.keys())
        return (titles[0], None) if titles else (None, None)
    return None, None


def fetch_avatar_imageinfo(
    session: requests.Session, enemy_name: str, timeout: float = DEFAULT_TIMEOUT_IMAGEINFO
) -> tuple[Optional[str], dict[str, Any]]:
    """查询敌人头像文件的 imageinfo，返回 `(去除查询串的 URL 或 None, 原始响应/错误)`。"""
    file_title = f"文件:头像_敌人_{enemy_name}.png"
    try:
        r = session.get(
            PRTS_MEDIAWIKI_API,
            params={
                "action": "query",
                "titles": file_title,
                "prop": "imageinfo",
                "iiprop": "url",
                "format": "json",
                "formatversion": "2",
            },
            timeout=timeout,
        )
        r.raise_for_status()
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
