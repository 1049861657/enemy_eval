#!/usr/bin/env python3
"""AI 评价冒烟脚本：审计外发字段、打印请求摘要，并覆盖可制造的失败路径。

不接入 pytest。用法：
    uv run python scripts/smoke_ai_review.py                      # 用偏好里的 AI 配置跑一次真实调用
    uv run python scripts/smoke_ai_review.py --dry-run            # 只审计外发字段与消息，不发请求
    uv run python scripts/smoke_ai_review.py --offline            # 离线失败路径：解析失败 + 连接失败
    uv run python scripts/smoke_ai_review.py --base-url URL --model M --api-key K   # 覆盖偏好
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models import AiEvaluationResult, EnemyData  # noqa: E402
from utils.ai_baseline import load_baseline  # noqa: E402
from utils.ai_client import build_current_payload, evaluate, extract_comment  # noqa: E402
from utils.ai_prompt import CONTRACT, build_messages, effective_persona  # noqa: E402
from utils.app_settings_store import AiRequestConfig, ai_request_config  # noqa: E402
from utils.error_handler import (  # noqa: E402
    AiCredentialError,
    AiNetworkError,
    AiServiceError,
)

DEFAULT_ENEMY_CONFIG = ROOT / "data" / "小杂毛_config.json"

# 一律不得外发的字段：头像本地路径、作者已给的评分与等级、旧简评。
FORBIDDEN_KEYS = ("avatar_path", "ratings", "grade", "brief_comment")

# 连接必然失败的地址，用于离线制造网络类失败。
UNREACHABLE_BASE_URL = "http://127.0.0.1:9/v1"

_passed = 0
_failed = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global _passed, _failed
    if ok:
        _passed += 1
        print(f"[PASS] {label}{f' — {detail}' if detail else ''}")
    else:
        _failed += 1
        print(f"[FAIL] {label}{f' — {detail}' if detail else ''}")


def load_enemy(path: Path) -> EnemyData:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return EnemyData(**raw)


def audit_payload(current: EnemyData) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """构造外发 payload 并核对白名单；返回 payload 与 messages。"""
    baseline = load_baseline()
    payload = build_current_payload(current)
    messages = build_messages(effective_persona(), baseline, payload)

    print("--- 外发字段审计 ---")
    print(f"人设：{len(effective_persona())} 字符（偏好自定义优先，否则内置默认）")
    print(f"基准键（{len(baseline)}）：{', '.join(baseline)}")
    print(f"当前卡键（{len(payload)}）：{', '.join(payload)}")
    leaked = [key for key in FORBIDDEN_KEYS if key in payload]
    check("当前卡不含 avatar_path / ratings / grade / brief_comment", not leaked, f"泄漏：{leaked}")
    leaked = [key for key in FORBIDDEN_KEYS if key in baseline]
    check("基准不含 avatar_path / ratings / grade / brief_comment", not leaked, f"泄漏：{leaked}")

    missing = [
        f"第 {index} 项缺 {key}"
        for index, skill in enumerate(payload["skills"])
        for key in ("名称", "冷却时间", "技力消耗", "效果")
        if key not in skill
    ]
    check("skills 每项四键齐全", not missing, "、".join(missing))
    check(
        "skills 无多余键",
        all(set(skill) == {"名称", "冷却时间", "技力消耗", "效果"} for skill in payload["skills"]),
    )
    print(f"messages：{len(messages)} 条，system {len(messages[0]['content'])} 字符，"
          f"user {len(messages[1]['content'])} 字符")
    check("system 段即固定契约", messages[0]["content"] == CONTRACT)
    check("人设不进 system 段", effective_persona() not in messages[0]["content"])
    body = messages[1]["content"]
    check(
        "user 段数据顺序：参照在前、点评对象在后",
        body.index("【参照数据") < body.index("【点评对象的数据】"),
    )
    return payload, messages


def run_offline_checks(baseline: dict[str, Any], enemy: EnemyData) -> None:
    print("\n--- 离线失败路径 ---")
    try:
        comment = extract_comment('{"comment":"血量偏低"}')
        check("不解包 JSON：响应正文原样成为简评", comment == '{"comment":"血量偏低"}', comment)
    except Exception as error:  # noqa: BLE001 - 冒烟脚本，如实记录任何异常
        check("不解包 JSON：响应正文原样成为简评", False, f"{type(error).__name__}: {error}")

    try:
        extract_comment("   \n\t ")
        check("空响应抛 AiServiceError", False, "未抛异常")
    except AiServiceError as error:
        check("空响应抛 AiServiceError", True, str(error))
    except Exception as error:  # noqa: BLE001
        check("空响应抛 AiServiceError", False, f"{type(error).__name__}: {error}")

    config = AiRequestConfig(base_url=UNREACHABLE_BASE_URL, model="smoke", api_key="sk-smoke")
    try:
        evaluate(config, effective_persona(), baseline, enemy)
        check("连接失败抛 AiNetworkError", False, "未抛异常")
    except AiNetworkError as error:
        check("连接失败抛 AiNetworkError", True, str(error))
    except Exception as error:  # noqa: BLE001
        check("连接失败抛 AiNetworkError", False, f"{type(error).__name__}: {error}")

    print("错误密钥（AiCredentialError）与 5xx（AiServiceError）需真实端点：")
    print("  错误密钥：加 --api-key 传一个错值后重跑")
    print("  5xx：端点自身故障时观察，或改装本地桩服务")


def run_live_call(
    baseline: dict[str, Any], enemy: EnemyData, config: AiRequestConfig | None
) -> None:
    print("\n--- 真实调用 ---")
    if config is None:
        print("未配置 AI（偏好或 --base-url/--model/--api-key 至少缺一项），跳过真实调用。")
        raise SystemExit(1)
    print(f"端点：{config.base_url.rstrip('/')}/chat/completions")
    print(f"模型：{config.model}（密钥不打印）")
    try:
        result: AiEvaluationResult = evaluate(
            config, effective_persona(), baseline, enemy
        )
    except AiCredentialError as error:
        print(f"凭证类失败（AiCredentialError）：{error}")
        raise SystemExit(1)
    except AiServiceError as error:
        print(f"服务类失败（AiServiceError）：{error}")
        raise SystemExit(1)
    except AiNetworkError as error:
        print(f"网络类失败（AiNetworkError）：{error}")
        raise SystemExit(1)
    comment = result.comment
    print(f"简评（{len(comment)} 字）：{comment}")
    check("简评不含「简评：」前缀", not comment.startswith("简评："))
    check("简评无换行", "\n" not in comment)
    check("简评无 wiki 标记", "[[" not in comment and "{{" not in comment)
    check("简评无「它 / 他」指代", "它" not in comment and "他" not in comment)
    check("简评无引号包裹", not (comment.startswith(("「", '"')) and comment.endswith(("」", '"'))))


def main() -> int:
    parser = argparse.ArgumentParser(description="AI 评价冒烟脚本")
    parser.add_argument("enemy_config", nargs="?", default=str(DEFAULT_ENEMY_CONFIG),
                        help="敌人配置 JSON 路径")
    parser.add_argument("--dry-run", action="store_true", help="只审计外发字段与消息，不发请求")
    parser.add_argument("--offline", action="store_true", help="只跑离线失败路径")
    parser.add_argument("--base-url", default="", help="覆盖偏好里的 Base URL")
    parser.add_argument("--model", default="", help="覆盖偏好里的模型名")
    parser.add_argument("--api-key", default="", help="覆盖偏好里的密钥")
    args = parser.parse_args()

    path = Path(args.enemy_config)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        print(f"找不到敌人配置：{path}")
        return 2

    enemy = load_enemy(path)
    print(f"敌人：{enemy.name}（{path}）")
    baseline = load_baseline()

    if args.offline:
        run_offline_checks(baseline, enemy)
    else:
        audit_payload(enemy)
        if not args.dry_run:
            settings = ai_request_config()
            config = AiRequestConfig(
                base_url=args.base_url.strip() or (settings.base_url if settings else ""),
                model=args.model.strip() or (settings.model if settings else ""),
                api_key=args.api_key.strip() or (settings.api_key if settings else ""),
            )
            run_live_call(baseline, enemy, config if all((config.base_url, config.model, config.api_key)) else None)

    print(f"\n结果：通过 {_passed} 项，失败 {_failed} 项")
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
