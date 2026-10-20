"""PRTS 数据门面：MediaWiki API → wikitext 解析 → `EnemyData`；调用方只依赖本模块。

分步实现在同包的 api_client / wikitext_templates / field_mapping / enemy_builder，顺序由本模块编排。
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Tuple

import httpx

from models import EnemyData

from utils.prts.api_client import (
    DEFAULT_HEADERS,
    DEFAULT_TIMEOUT_PARSE,
    PRTS_MEDIAWIKI_API,
    build_async_client,
    build_client,
    fetch_avatar_imageinfo,
    resolve_enemy_page_title,
    _fetch_parse_json,
)
from utils.prts.enemy_builder import strip_debug_keys, to_enemy_data
from utils.prts.field_mapping import (
    ABNORMAL_MAP,
    COMMON_KEY_MAP,
    COMMON_TEMPLATE,
    LEVEL_KEY_MAP,
    LEVEL_TEMPLATE,
    EnemyLevel,
    build_enemy_raw,
    parse_enemy_levels,
)

logger = logging.getLogger(__name__)

__all__ = [
    "DEFAULT_HEADERS",
    "PRTS_MEDIAWIKI_API",
    "LEVEL_TEMPLATE",
    "COMMON_TEMPLATE",
    "LEVEL_KEY_MAP",
    "COMMON_KEY_MAP",
    "ABNORMAL_MAP",
    "EnemyLevel",
    "build_enemy_raw",
    "parse_enemy_levels",
    "to_enemy_data",
    "strip_debug_keys",
    "build_async_client",
    "build_client",
    "fetch_enemy_from_prts_mediawiki",
    "fetch_enemy_from_prts_mediawiki_with_debug",
    "fetch_enemy_data",
    "fetch_enemy_data_raw",
    "error_message_for_raw",
]


async def _enemy_from_parse_response(
    client: httpx.AsyncClient, j: dict[str, Any], page_title: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    bundle: dict[str, Any] = {
        "parse_json": j,
        "html": "",
        "wikitext": "",
        "imageinfo_json": None,
    }
    if "error" in j:
        err = j["error"]
        code = err.get("code", "")
        info = err.get("info", str(err))
        et = "missing_page" if code == "missingtitle" else "api_error"
        return {"error": info, "error_type": et}, bundle

    p = j.get("parse") or {}
    wikitext = p.get("wikitext") or ""
    html = p.get("text") or ""
    bundle["html"] = html
    bundle["wikitext"] = wikitext

    wiki_merged = build_enemy_raw(wikitext)
    if wiki_merged is None:
        return {
            "error": "未找到敌人 wikitext 模板（common2 / levelcontent）",
            "error_type": "no_wiki_template",
            "_partial": {"name": page_title},
        }, bundle

    merged = wiki_merged
    merged["_source"] = "wikitext"

    if not merged.get("name"):
        merged["name"] = page_title
    merged.setdefault("skills", [])

    av, img_raw = await fetch_avatar_imageinfo(
        client, str(merged.get("name") or page_title)
    )
    bundle["imageinfo_json"] = img_raw
    if av:
        merged["avatar_path"] = av

    if merged.get("max_hp") in (None, 0) and merged.get("attack") in (None, 0):
        return {
            "error": "wikitext 中未能解析出有效数值属性（最大生命值 / 攻击力）",
            "error_type": "parse_empty",
            "_partial": merged,
        }, bundle
    return merged, bundle


async def _fetch_enemy_on_client(
    client: httpx.AsyncClient, enemy_name: str, timeout: float
) -> tuple[dict[str, Any], dict[str, Any]]:
    resolved_title, _resolve_err = await resolve_enemy_page_title(client, enemy_name)
    page_title = resolved_title or enemy_name

    j, err = await _fetch_parse_json(client, page_title, timeout)
    if err is not None:
        return {"error": err, "error_type": "network"}, {
            "parse_json": None,
            "html": "",
            "wikitext": "",
            "imageinfo_json": None,
        }

    result, bundle = await _enemy_from_parse_response(client, j, page_title)
    if "error" not in result and not result.get("name"):
        result["name"] = enemy_name
    return result, bundle


async def _fetch_enemy_resolved(
    enemy_name: str,
    timeout: float,
    *,
    client: httpx.AsyncClient | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """按敌人名称精确定位并拉取敌人页面。

    PRTS 的 `{{敌人信息/common2}}` 模板会为每个敌人页面写入 Semantic MediaWiki 属性
    `名称` 并归入 `分类:敌人`；因此先用 `action=ask` 的
    `[[分类:敌人]][[名称::<name>]]` 查询精确定位页面标题，一次命中，不依赖任何
    命名后缀猜测——PRTS 对敌我同名单位的消歧义后缀并不统一（`(敌方)`/`(敌人)`/
    `(我方)` 均在使用，如 弑君者(敌方)、变格博士(敌人)），猜测式重试无法覆盖全部情况。

    语义查询未命中、超时或出错时，退回直接按 enemy_name 拉取页面（多数敌人裸名本来就
    直接命中）。resolve / parse / imageinfo 串行。传入 client 则复用（GUI 拉取后再下头像）；
    否则自建并在返回前关闭。
    """
    if client is not None:
        return await _fetch_enemy_on_client(client, enemy_name, timeout)
    async with build_async_client() as owned:
        return await _fetch_enemy_on_client(owned, enemy_name, timeout)


async def fetch_enemy_from_prts_mediawiki(
    page_title: str,
    timeout: float = DEFAULT_TIMEOUT_PARSE,
    *,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """
    parse API → wikitext 合并 → 头像 imageinfo。
    成功返回可交给 to_enemy_data 的字典；失败返回 {"error", "error_type"}。

    先用 Semantic MediaWiki 语义属性精确定位敌人页面（见 _fetch_enemy_resolved），
    覆盖敌我同名单位（如 弑君者、W、变格博士）的消歧义，无需猜测页面后缀。
    """
    result, _ = await _fetch_enemy_resolved(page_title, timeout, client=client)
    return result


async def fetch_enemy_from_prts_mediawiki_with_debug(
    page_title: str,
    timeout: float = DEFAULT_TIMEOUT_PARSE,
    *,
    client: httpx.AsyncClient | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """同 fetch_enemy_from_prts_mediawiki，附带 {parse_json, html, wikitext, imageinfo_json}。

    wikitext 是级别切换的唯一数据源：调用方据此用 parse_enemy_levels 列出级别、用
    build_enemy_raw 按所选级别重新构造，无需二次联网。
    """
    return await _fetch_enemy_resolved(page_title, timeout, client=client)


def error_message_for_raw(raw: dict[str, Any], enemy_name: str) -> str:
    """把 fetch_enemy_from_prts_mediawiki 失败结果的 error_type 映射为面向用户的中文提示。"""
    err_type = raw.get("error_type", "")
    msg = raw.get("error", "未知错误")
    if err_type == "missing_page":
        return f"在PRTS中未找到敌人「{enemy_name}」，请检查名称是否正确。"
    if err_type == "parse_empty":
        return f"PRTS 页面无法解析出敌人属性：{msg}"
    if err_type == "network":
        return f"网络错误：{msg}"
    return f"获取PRTS数据失败：{msg}"


async def fetch_enemy_data(enemy_name: str) -> Tuple[Optional[EnemyData], Optional[str]]:
    """拉取 PRTS 并转为 EnemyData。grade、简评、三星评价仍由调用方填写。

    不预下载头像（渲染层职责，见 PrtsFetchThread）。这是 coroutine，须 await。
    """
    try:
        raw = await fetch_enemy_from_prts_mediawiki(enemy_name)
        if "error" in raw:
            return None, error_message_for_raw(raw, enemy_name)

        clean = strip_debug_keys(raw)
        enemy_data = to_enemy_data(clean, enemy_name)
        if enemy_data:
            return enemy_data, None
        return None, "PRTS数据格式不兼容，无法导入。"
    except Exception as e:
        logger.error("PRTS 数据获取失败: %s", e)
        return None, f"获取PRTS数据时发生错误：{str(e)}"


async def fetch_enemy_data_raw(enemy_name: str) -> dict[str, Any]:
    """合并后的扁平字典（无 _ 调试键）；失败时含 error / error_type。"""
    data = await fetch_enemy_from_prts_mediawiki(enemy_name)
    if "error" in data:
        return data
    return strip_debug_keys(data)
