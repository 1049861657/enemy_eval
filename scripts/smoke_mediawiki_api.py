#!/usr/bin/env python3
"""
MediaWiki API 人工联网冒烟脚本（非自动化测试，不接入 CI/pytest discovery）。

连通性探测 + utils.prts_mediawiki_pipeline 管线人工核对；需要真实访问 https://prts.wiki。
自动化单元测试见 tests/（覆盖同一管线的纯函数部分，无需联网）。

用法（项目根目录）:
  uv run python scripts/smoke_mediawiki_api.py
  uv run python scripts/smoke_mediawiki_api.py 格罗莫夫
  uv run python scripts/smoke_mediawiki_api.py 浮士德 --dump   # → data/prts_debug/浮士德/
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.filenames import safe_filename  # noqa: E402
from utils.prts_api_client import build_client, request_timeout  # noqa: E402
from utils.prts_mediawiki_pipeline import (  # noqa: E402
    PRTS_MEDIAWIKI_API,
    fetch_enemy_from_prts_mediawiki_with_debug,
    strip_debug_keys,
    to_enemy_data,
)
DEFAULT_DEBUG_DIR = ROOT / "data" / "prts_debug"


def api_get_json(params: dict[str, str], timeout: float = 30.0) -> dict:
    with build_client() as client:
        r = client.get(
            PRTS_MEDIAWIKI_API,
            params=params,
            timeout=request_timeout(timeout),
        )
        r.raise_for_status()
        return r.json()


def run_smoke() -> int:
    print(f"请求端点: {PRTS_MEDIAWIKI_API}\n")

    siteinfo = api_get_json(
        {
            "action": "query",
            "meta": "siteinfo",
            "siprop": "general",
            "format": "json",
            "formatversion": "2",
        },
    )
    if "error" in siteinfo:
        print("API 返回 error:\n", json.dumps(siteinfo["error"], ensure_ascii=False, indent=2))
        return 1
    general = siteinfo.get("query", {}).get("general", {})
    print("[OK] action=query&meta=siteinfo")
    print(f"  sitename: {general.get('sitename')}")
    print(f"  lang: {general.get('lang')}")
    print(f"  mainpage: {general.get('mainpage')}")

    parse_title = "首页"
    parsed = api_get_json(
        {
            "action": "parse",
            "page": parse_title,
            "prop": "wikitext",
            "format": "json",
            "formatversion": "2",
        },
    )
    if "error" in parsed:
        print(f"\n[WARN] action=parse&page={parse_title!r} 失败:")
        print(json.dumps(parsed["error"], ensure_ascii=False, indent=2))
        return 0

    wikitext = (parsed.get("parse", {}) or {}).get("wikitext", "") or ""
    preview = wikitext[:200].replace("\n", " ")
    print(f"\n[OK] action=parse&page={parse_title!r} (wikitext)")
    print(f"  wikitext 长度: {len(wikitext)} 字符")
    print(f"  片段: {preview}{'…' if len(wikitext) > 200 else ''}")
    print("\n结论: MediaWiki API 连通性正常。")
    return 0


def dump_mediawiki_debug(enemy_name: str, extracted: dict, raw: dict, out_dir: Path) -> None:
    """
    out_dir 一般为 data/prts_debug/<敌人名>/ ，由调用方拼好子目录。
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    html_path = out_dir / "rendered.html"
    wiki_path = out_dir / "page.wikitext"
    extracted_path = out_dir / "extracted.json"

    html_path.write_text(raw.get("html") or "", encoding="utf-8")
    wiki_path.write_text(raw.get("wikitext") or "", encoding="utf-8")

    extracted_path.write_text(
        json.dumps(strip_debug_keys(extracted), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    parse_j = copy.deepcopy(raw.get("parse_json") or {})
    if isinstance(parse_j.get("parse"), dict):
        slim = parse_j["parse"]
        slim.pop("text", None)
        slim.pop("wikitext", None)
        slim["_note"] = "大段正文见本目录 rendered.html 与 page.wikitext"
        slim["_rendered_html_file"] = html_path.name
        slim["_wikitext_file"] = wiki_path.name

    slim_parse_path = out_dir / "api_parse.json"
    slim_parse_path.write_text(
        json.dumps(parse_j, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    img_path = out_dir / "api_imageinfo.json"
    img_path.write_text(
        json.dumps(raw.get("imageinfo_json") or {}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    readme = out_dir / "README.txt"
    readme.write_text(
        "\n".join(
            [
                f"敌人条目标题: {enemy_name}",
                "",
                "文件说明:",
                f"  {html_path.name}      — parse 渲染 HTML",
                f"  {wiki_path.name}   — 页面 wikitext 源码",
                f"  {extracted_path.name}   — 管线合并结果（含 skills，已去 _ 调试键）",
                f"  {slim_parse_path.name}  — parse API JSON（无 text/wikitext 大字段）",
                f"  {img_path.name} — 头像 imageinfo",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"\n[dump] 已写入目录: {out_dir.resolve()}")
    for p in (readme, html_path, wiki_path, extracted_path, slim_parse_path, img_path):
        print(f"       {p.name}")


def run_enemy_experiment(enemy_name: str, dump_dir: Path | None) -> int:
    print(f"\n--- 新管线 prts_mediawiki_pipeline: 「{enemy_name}」---\n")
    api_raw, raw_bundle = asyncio.run(
        fetch_enemy_from_prts_mediawiki_with_debug(enemy_name)
    )
    if "error" in api_raw:
        print("[失败]", api_raw.get("error_type"), api_raw.get("error"))
        if dump_dir is not None:
            err_dir = dump_dir / safe_filename(enemy_name)
            err_dir.mkdir(parents=True, exist_ok=True)
            err_path = err_dir / "error.json"
            err_path.write_text(
                json.dumps(
                    {"extracted_attempt": api_raw, "parse_json": raw_bundle.get("parse_json")},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            print(f"[dump] 失败上下文已写入: {err_path}")
        return 1

    if dump_dir is not None:
        per_enemy_dir = dump_dir / safe_filename(enemy_name)
        dump_mediawiki_debug(enemy_name, api_raw, raw_bundle, per_enemy_dir)

    interesting = strip_debug_keys(api_raw)
    print(f"[OK] 数据源: {api_raw.get('_source', '?')}")
    print("结果摘要:")
    for k in sorted(interesting.keys()):
        v = interesting[k]
        s = str(v)
        if len(s) > 120:
            s = s[:120] + "…"
        print(f"  {k}: {s}")

    ed = to_enemy_data(api_raw, enemy_name)
    if ed:
        print("\n[OK] to_enemy_data → EnemyData 成功。")
    else:
        print("\n[WARN] to_enemy_data 失败。")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="PRTS MediaWiki API 实验脚本")
    parser.add_argument("enemy", nargs="?", default=None, help="敌人条目标题")
    parser.add_argument("--smoke", action="store_true", help="拉取敌人前先做连通性探测")
    parser.add_argument(
        "--dump",
        nargs="?",
        default=None,
        const="",
        metavar="DIR",
        help="导出到 data/prts_debug/<敌人名>/（默认根为 data/prts_debug）",
    )
    args = parser.parse_args()

    dump_dir: Path | None = None
    if args.dump is not None:
        dump_dir = Path(args.dump) if args.dump else DEFAULT_DEBUG_DIR

    code = 0
    if args.smoke or not args.enemy:
        code = run_smoke()
    if args.enemy:
        code = max(code, run_enemy_experiment(args.enemy, dump_dir))
    return code


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except httpx.HTTPError as exc:
        print("网络或 HTTP 错误:", exc, file=sys.stderr)
        raise SystemExit(2)
