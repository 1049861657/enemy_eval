"""AI 评价提示词：内置默认提示词、消息组装与请求预览。纯函数，不发网络请求、不做解析。

默认人设来自 PRTS 剧情原文（孤岛风云 MB-5 / MB-8，说话人为杰斯顿·威廉姆斯的台词行），
归纳见 `todos/feat-20261006/03-persona-draft.md`。提示词可由用户在「AI 评价」面板里改写，
偏好里为空表示沿用内置默认（`DEFAULT_PROMPT`），这样默认文案升级能自动生效。
"""

from __future__ import annotations

import json
from typing import Any

from .app_settings_store import load_app_settings

# 默认提示词：人设、任务、输出契约与数据语义，四段合一。
DEFAULT_PROMPT = """你是《明日方舟》的杰斯顿·威廉姆斯，受邀点评一名敌人的战斗表现。
口吻：礼貌的敬语外壳下是居高临下的嘲弄；自称「我」；下结论干脆、不留余地，可自得、可打趣，但不粗俗、不辱骂、不煽情。
句式：以中短句为主，可排比递进；可用「啧啧」「很遗憾」「不得不」这类口头语。
立场：点评这名敌人的战斗表现（威胁、长处、短板、机制观感、在什么场合难缠），不评价设计好坏、不谈新旧、不比较其他敌人、不提作者。

输出要求：
1. 只输出一个 JSON 对象，形如 {"comment": "简评正文"}；前后不要有别的内容，也不要把输入数据、思考过程或任何其它 JSON 一并输出。
2. comment 不超过 100 字，且是对这名敌人的评价——作为对手意味着什么，而不是与你自己的数据做逐项对照：
   - 先给整体印象，再说战斗用途：够不够硬、打人疼不疼、跑得快不快、机制是否棘手、放进什么场合难缠。
   - 你的数据只作参照物，最多自比一次（如「比我还能扛」）；不要把双方的数值成对列出来。
   - 数字最多出现一两处，且必须服务于评价：「防御薄得像纸」优于「防御仅百」，「出手慢得可怜」优于「攻击间隔四秒」。
   - 禁止逐字段复述或清单式罗列（如「血量 X、防御 Y、法抗 Z」）；也禁止只点出巧合而不下结论（如「攻击间隔与我同为四秒」）。
3. comment 为纯正文：不带「简评：」之类前缀、不带引号、不带署名、不换行、不用 [[...]] 或 {{...}} 等 wiki 标记。
4. 不出现人称代词指代被评价对象（不写「它」「他」），直接以「血量」「防御」「攻击间隔」这类主语成句；可以用第一人称。
5. 只依据给定的两份数据，不得引入数据中不存在的机制或数值。

数据语义（两份数据的键名相同；用来读懂数据，不要逐项复述）：
- 数值越大越强：max_hp 最大生命值、attack 攻击力、defense 防御力、magic_resistance 法术抗性（百分比减伤）、damage_resistance 损伤抗性（对应类型减伤）、element_resistance 元素抗性（对应类型减伤）、hp_recovery_speed 生命自回速度（越大回血越快）、attack_range_radius 攻击范围半径（单位为格）、weight_level 重量等级（越大越难被推动）、base_taunt_level 基础嘲讽等级、target_value 目标价值（计分权重）。
- 反直觉的两项：attack_interval 是攻击间隔，数值越大出手越慢；move_speed 是移动速度，数值越大移动越快。
- 零值语义：weight_level=0 表示无重量、base_taunt_level=0 表示无嘲讽、target_value=0 表示不计分、attack_range_radius=0 表示无额外范围、hp_recovery_speed=0 表示无自回、damage_resistance=0 与 element_resistance=0 表示无对应抗性。
- 枚举：attack_type 攻击方式、damage_type 伤害类型、action_type 行动方式、position 地位、category 种类。"""


def _dump(data: dict[str, Any]) -> str:
    """紧凑序列化：键值不被改写，仅去空白。"""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def _user_content(baseline: dict[str, Any], current: dict[str, Any]) -> str:
    """user 消息正文：两段带小标题的数据，``build_messages`` 与 ``render_preview`` 共用。"""
    return (
        f"【你（杰斯顿）自己的数据（仅作参照，不必逐项对照）】\n{_dump(baseline)}\n\n"
        f"【要点评的敌人的数据】\n{_dump(current)}"
    )


def build_messages(
    prompt: str, baseline: dict[str, Any], current: dict[str, Any]
) -> list[dict[str, str]]:
    """组装 OpenAI 兼容 chat 消息：system 为提示词，user 为两份数据。

    ``prompt`` 为界面上的提示词正文（空则回落内置默认）；``baseline`` 只作说话人的参照，
    ``current`` 是点评对象。两份数据均为已筛过的外发字段字典，直接嵌入、不改形状。
    """
    return [
        {"role": "system", "content": prompt.strip() or DEFAULT_PROMPT},
        {"role": "user", "content": _user_content(baseline, current)},
    ]


def render_preview(
    endpoint: str,
    model: str,
    prompt: str,
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> str:
    """可读预览：端点、模型名与两条 message；拼装方式与 `build_messages` 完全一致。"""
    return "\n".join(
        (
            "── system ──",
            prompt.strip() or DEFAULT_PROMPT,
            "",
            "── user ──",
            _user_content(baseline, current),
        )
    )


def effective_prompt() -> str:
    """当前生效的提示词：偏好里的自定义值优先，为空则用内置默认。"""
    return load_app_settings().ai_prompt.strip() or DEFAULT_PROMPT


def prompt_for_storage(text: str) -> str:
    """把界面文本折算成偏好里该存的值：与内置默认相同则存空串（跟随默认文案演进）。"""
    text = text.strip()
    return "" if text == DEFAULT_PROMPT.strip() else text
