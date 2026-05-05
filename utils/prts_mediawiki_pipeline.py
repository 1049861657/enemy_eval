"""
PRTS 敌人数据：MediaWiki API → wikitext 模板解析 → EnemyData。
数据源仅为 {{敌人信息/common2}} / {{敌人信息/levelcontent}}；parse 仍可取 text 供调试导出。
levelcontent 中 技能N* 会合并为 skills；对外入口为 fetch_enemy_data / fetch_enemy_data_raw。
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional, Tuple

import requests
import skia

from core.optimization import _GLOBAL_IMAGE_CACHE
from models import EnemyData
from utils.network_image import download_image_data, get_url_cache_key, is_url

logger = logging.getLogger(__name__)

PRTS_MEDIAWIKI_API = "https://prts.wiki/api.php"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

LEVEL_TEMPLATE = "敌人信息/levelcontent"
COMMON_TEMPLATE = "敌人信息/common2"

LEVEL_KEY_MAP: dict[str, str] = {
    "名称": "name",
    "地位": "position",
    "种类": "category",
    "描述": "brief_description",
    "攻击方式": "attack_type",
    "行动方式": "action_type",
    "最大生命值": "max_hp",
    "攻击力": "attack",
    "防御力": "defense",
    "法术抗性": "magic_resistance",
    "攻击范围半径": "attack_range_radius",
    "移动速度": "move_speed",
    "攻击间隔": "attack_interval",
    "生命恢复速度": "hp_recovery_speed",
    "重量等级": "weight_level",
    "损伤抵抗": "damage_resistance",
    "元素抗性": "element_resistance",
    "基础嘲讽等级": "base_taunt_level",
    "数量": "target_value",
    "天赋": "talents_abilities",
}

COMMON_KEY_MAP: dict[str, str] = {
    "名称": "name",
    "地位级别": "position",
    "描述": "brief_description_common",
    "伤害类型": "damage_type",
    "攻击方式": "attack_type",
    "行动方式": "action_type",
}

ABNORMAL_MAP: dict[str, str] = {
    "眩晕抗性": "晕眩",
    "沉默抗性": "沉默",
    "沉睡抗性": "沉睡",
    "冻结抗性": "冻结",
    "浮空抗性": "浮空",
    "战栗抗性": "战栗",
    "恐惧抗性": "恐惧",
    "麻痹抗性": "麻痹",
    "诱导抗性": "诱导",
}


def _extract_template_body(wikitext: str, template_name: str) -> Optional[str]:
    prefix = "{{" + template_name
    idx = wikitext.find(prefix)
    if idx < 0:
        return None
    tail = idx + len(prefix)
    if tail < len(wikitext) and wikitext[tail] not in "|{ \t\n\r":
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
        if tail < len(wikitext) and wikitext[tail] not in "|{ \t\n\r":
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


def _clean_num_text(text: str) -> str:
    t = re.sub(r"\s+", "", (text or "").strip())
    if t in ("", "—", "-", "无"):
        return ""
    return t


def _to_float(text: str) -> float:
    s = _clean_num_text(text)
    if not s:
        return 0.0
    m = re.search(r"-?\d+\.?\d*", s)
    return float(m.group(0)) if m else 0.0


def _to_int(text: str) -> int:
    return int(round(_to_float(text)))


def _strip_wiki_html_comments(text: str) -> str:
    """去掉 wikitext 里误带入的 <!-- ... -->（如 PRTS 模板内嵌 JSON 注释）。"""
    return re.sub(r"<!--[\s\S]*?-->", "", text)


_SKILL_FIELD_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^技能(\d+)$"), "名称"),
    (re.compile(r"^技能(\d+)初始$"), "初始"),
    (re.compile(r"^技能(\d+)消耗$"), "消耗"),
    (re.compile(r"^技能(\d+)效果$"), "效果"),
    (re.compile(r"^技能(\d+)技力消耗$"), "技力消耗"),
    (re.compile(r"^技能(\d+)技力$"), "技力消耗"),
]


def _skill_slots_from_level_zh(zh: dict[str, str]) -> dict[int, dict[str, str]]:
    """从单个 levelcontent 参数表抽取 技能0/技能0初始/… 等到按槽位索引的字典。"""
    slots: dict[int, dict[str, str]] = {}
    for k, v in zh.items():
        val = (v or "").strip()
        if not val:
            continue
        for rx, dest in _SKILL_FIELD_PATTERNS:
            m = rx.match(k)
            if m:
                idx = int(m.group(1))
                slots.setdefault(idx, {})[dest] = val
                break
    return slots


def _merge_skill_slots(
    acc: dict[int, dict[str, str]], delta: dict[int, dict[str, str]]
) -> None:
    for idx, part in delta.items():
        acc.setdefault(idx, {})
        acc[idx].update(part)


def _skill_slots_to_card_skills(slots: dict[int, dict[str, str]]) -> list[dict[str, str]]:
    """
    转为 EnemyData / GUI 使用的技能列表：
    名称、冷却时间（初动/回转）、技力消耗、效果。
    """
    out: list[dict[str, str]] = []
    for i in sorted(slots.keys()):
        d = slots[i]
        name = (d.get("名称") or "").strip()
        effect = _strip_wiki_html_comments(d.get("效果") or "").strip()
        if not name and not effect:
            continue
        chu, hui = d.get("初始"), d.get("消耗")
        if chu is not None and hui is not None:
            cool = f"{chu}/{hui}"
        elif chu is not None:
            cool = str(chu)
        elif hui is not None:
            cool = str(hui)
        else:
            cool = ""
        sp = (d.get("技力消耗") or "").strip()
        out.append(
            {
                "名称": name or f"技能{i}",
                "冷却时间": cool,
                "技力消耗": sp,
                "效果": effect,
            }
        )
    return out


def _resistance_val(raw: str) -> float:
    s = (raw or "").strip()
    if not s or s == "无":
        return 0.0
    return 1.0


def _map_level_block(zh: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    abnormal: dict[str, float] = {}
    for zk, vv in zh.items():
        if zk in ABNORMAL_MAP:
            abnormal[ABNORMAL_MAP[zk]] = _resistance_val(vv)
            continue
        en = LEVEL_KEY_MAP.get(zk)
        if not en:
            continue
        if en in (
            "max_hp",
            "attack",
            "defense",
            "magic_resistance",
            "weight_level",
            "damage_resistance",
            "element_resistance",
            "base_taunt_level",
            "target_value",
        ):
            out[en] = _to_int(vv)
        elif en in ("move_speed", "attack_interval", "attack_range_radius", "hp_recovery_speed"):
            out[en] = _to_float(vv)
        elif en == "talents_abilities":
            out[en] = vv.strip()
        else:
            out[en] = vv.strip()
    if abnormal:
        out["abnormal_resistances"] = abnormal
    return out


def _map_common_block(zh: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for zk, vv in zh.items():
        en = COMMON_KEY_MAP.get(zk)
        if not en:
            continue
        out[en] = vv.strip()
    return out


def merge_wikitext_enemy(wikitext: str) -> Optional[dict[str, Any]]:
    """从 wikitext 合并 common2 + 全部 levelcontent（按 index 升序覆盖）。"""
    common_body = _extract_template_body(wikitext, COMMON_TEMPLATE)
    level_bodies = _extract_all_template_bodies(wikitext, LEVEL_TEMPLATE)
    if not common_body and not level_bodies:
        return None

    merged: dict[str, Any] = {}
    if common_body:
        merged.update(_map_common_block(_parse_template_params(common_body)))

    level_dicts: list[tuple[int, dict[str, str]]] = []
    for body in level_bodies:
        p = _parse_template_params(body)
        try:
            idx = int((p.get("index") or "0").strip() or "0")
        except ValueError:
            idx = 0
        level_dicts.append((idx, p))
    level_dicts.sort(key=lambda x: x[0])

    ab_acc: dict[str, float] = dict(merged.get("abnormal_resistances") or {})
    skill_slots: dict[int, dict[str, str]] = {}
    for _, zh in level_dicts:
        _merge_skill_slots(skill_slots, _skill_slots_from_level_zh(zh))
        part = _map_level_block(zh)
        ab = part.pop("abnormal_resistances", None)
        if ab:
            ab_acc.update(ab)
        merged.update(part)
    if ab_acc:
        merged["abnormal_resistances"] = ab_acc
    merged["skills"] = _skill_slots_to_card_skills(skill_slots)

    if merged.get("brief_description_common") and not merged.get("brief_description"):
        merged["brief_description"] = merged.pop("brief_description_common")
    elif merged.get("brief_description_common"):
        merged.pop("brief_description_common")

    if "talents_abilities" not in merged:
        merged["talents_abilities"] = ""

    if isinstance(merged.get("brief_description"), str):
        merged["brief_description"] = _strip_wiki_html_comments(merged["brief_description"]).strip()
    if isinstance(merged.get("talents_abilities"), str):
        merged["talents_abilities"] = _strip_wiki_html_comments(merged["talents_abilities"]).strip()

    cat = merged.get("category", "")
    if isinstance(cat, str) and not cat.strip():
        merged["category"] = "其他"

    return merged if merged else None


def _avatar_query(session: requests.Session, enemy_name: str) -> tuple[Optional[str], dict[str, Any]]:
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
            timeout=12.0,
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
        logger.debug("imageinfo 头像失败: %s", e)
        return None, {"error": str(e)}


def _enemy_from_parse_response(
    session: requests.Session, j: dict[str, Any], page_title: str
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

    wiki_merged = merge_wikitext_enemy(wikitext)
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

    av, img_raw = _avatar_query(session, str(merged.get("name") or page_title))
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


def fetch_enemy_from_prts_mediawiki(page_title: str, timeout: float = 22.0) -> dict[str, Any]:
    """
    parse API → wikitext 合并 → 头像 imageinfo。
    成功返回可交给 to_enemy_data 的字典；失败返回 {"error", "error_type"}。
    """
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
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
        j = r.json()
    except requests.RequestException as e:
        return {"error": str(e), "error_type": "network"}

    result, _ = _enemy_from_parse_response(session, j, page_title)
    return result


def fetch_enemy_from_prts_mediawiki_with_debug(
    page_title: str, timeout: float = 22.0
) -> tuple[dict[str, Any], dict[str, Any]]:
    """同 fetch_enemy_from_prts_mediawiki，附带 {parse_json, html, wikitext, imageinfo_json} 供调试导出。"""
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
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
        j = r.json()
    except requests.RequestException as e:
        return {"error": str(e), "error_type": "network"}, {
            "parse_json": None,
            "html": "",
            "wikitext": "",
            "imageinfo_json": None,
        }

    return _enemy_from_parse_response(session, j, page_title)


def to_enemy_data(raw: dict[str, Any], fallback_name: str) -> Optional[EnemyData]:
    """将管线合并字典转为 EnemyData（缺省字段用卡片编辑默认值）。"""
    if "error" in raw:
        return None
    ab = raw.get("abnormal_resistances")
    if not isinstance(ab, dict):
        ab = {}
    try:
        return EnemyData(
            name=str(raw.get("name") or fallback_name),
            grade=str(raw.get("grade") or "C"),
            attack_type=str(raw.get("attack_type") or "近战"),
            damage_type=str(raw.get("damage_type") or "物理"),
            action_type=str(raw.get("action_type") or "地面"),
            hp_recovery_speed=float(raw.get("hp_recovery_speed") or 0),
            position=str(raw.get("position") or "普通"),
            category=str(raw.get("category") or "其他"),
            max_hp=int(raw.get("max_hp") or 1000),
            attack=int(raw.get("attack") or 100),
            defense=int(raw.get("defense") or 50),
            magic_resistance=int(raw.get("magic_resistance") or 10),
            attack_range_radius=float(raw.get("attack_range_radius") or 0),
            weight_level=int(raw.get("weight_level") or 1),
            move_speed=float(raw.get("move_speed") or 1.0),
            attack_interval=float(raw.get("attack_interval") or 2.0),
            damage_resistance=int(raw.get("damage_resistance") or 0),
            element_resistance=int(raw.get("element_resistance") or 0),
            base_taunt_level=int(raw.get("base_taunt_level") or 0),
            target_value=int(raw.get("target_value") or 1),
            brief_description=str(
                raw.get("brief_description") or f"来自PRTS的{fallback_name}数据"
            ),
            brief_comment=str(raw.get("brief_comment") or "待评价"),
            abnormal_resistances={k: float(v) for k, v in ab.items()},
            hostility_rating=int(raw.get("hostility_rating") or 3),
            innovation_rating=int(raw.get("innovation_rating") or 3),
            threat_rating=int(raw.get("threat_rating") or 3),
            avatar_path=raw.get("avatar_path"),
            skills=_normalize_skills_payload(raw.get("skills")),
            talents_abilities=str(raw.get("talents_abilities") or ""),
        )
    except Exception as e:
        logger.error("EnemyData 构建失败: %s", e)
        return None


def _normalize_skills_payload(raw: Any) -> list[dict[str, str]]:
    """保证 skills 为 list[{名称, 冷却时间, 技力消耗, 效果}]，值均为 str。"""
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "名称": str(item.get("名称", "") or ""),
                "冷却时间": str(item.get("冷却时间", "") or ""),
                "技力消耗": str(item.get("技力消耗", "") or ""),
                "效果": str(item.get("效果", "") or ""),
            }
        )
    return out


def strip_debug_keys(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if not k.startswith("_")}


def preload_prts_avatar_image(avatar_path: str) -> None:
    """预下载网络头像到全局图像缓存，减轻首次渲染阻塞。"""
    if not avatar_path:
        return
    try:
        if not is_url(avatar_path):
            return
        image_data = download_image_data(avatar_path)
        if not image_data:
            return

        cache_key = f"{get_url_cache_key(avatar_path)}_{(330, 330)}"
        original_image = skia.Image.MakeFromEncoded(image_data)
        if not original_image:
            return
        target_w, target_h = 330, 330
        if (original_image.width(), original_image.height()) != (target_w, target_h):
            scaled_surface = skia.Surface(target_w, target_h)
            scaled_canvas = scaled_surface.getCanvas()
            sampling = skia.SamplingOptions(skia.CubicResampler.Mitchell())
            paint = skia.Paint()
            paint.setAntiAlias(True)
            src_rect = skia.Rect(0, 0, original_image.width(), original_image.height())
            dst_rect = skia.Rect(0, 0, target_w, target_h)
            scaled_canvas.drawImageRect(original_image, src_rect, dst_rect, sampling, paint)
            scaled_image = scaled_surface.makeImageSnapshot()
        else:
            scaled_image = original_image
        _GLOBAL_IMAGE_CACHE[cache_key] = scaled_image
        logger.info("成功预缓存 PRTS 头像: %s", avatar_path)
    except Exception as e:
        logger.warning("预加载头像失败: %s", e)


def fetch_enemy_data(enemy_name: str) -> Tuple[Optional[EnemyData], Optional[str]]:
    """
    GUI / CLI 使用：拉取 PRTS 并转为 EnemyData。
    grade、简评、三星评价仍由用户在界面中填写。
    """
    try:
        raw = fetch_enemy_from_prts_mediawiki(enemy_name)
        if "error" in raw:
            err_type = raw.get("error_type", "")
            msg = raw.get("error", "未知错误")
            if err_type == "missing_page":
                return None, f"在PRTS中未找到敌人「{enemy_name}」，请检查名称是否正确。"
            if err_type == "parse_empty":
                return None, f"PRTS 页面无法解析出敌人属性：{msg}"
            if err_type == "network":
                return None, f"网络错误：{msg}"
            return None, f"获取PRTS数据失败：{msg}"

        clean = strip_debug_keys(raw)
        if clean.get("avatar_path"):
            preload_prts_avatar_image(clean["avatar_path"])

        enemy_data = to_enemy_data(clean, enemy_name)
        if enemy_data:
            return enemy_data, None
        return None, "PRTS数据格式不兼容，无法导入。"
    except Exception as e:
        logger.error("PRTS 数据获取失败: %s", e)
        return None, f"获取PRTS数据时发生错误：{str(e)}"


def fetch_enemy_data_raw(enemy_name: str) -> dict[str, Any]:
    """合并后的扁平字典（无 _ 调试键）；失败时含 error / error_type。"""
    data = fetch_enemy_from_prts_mediawiki(enemy_name)
    if "error" in data:
        return data
    return strip_debug_keys(data)
