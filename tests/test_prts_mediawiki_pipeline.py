"""PRTS 数据管线纯函数（无网络依赖）单元测试。

覆盖拆分后的三个纯函数模块：wiki_template_parser（模板字符串解析）、
prts_field_mapping（字段映射）、prts_enemy_builder（EnemyData 组装）。
"""

from __future__ import annotations

from utils.prts.enemy_builder import to_enemy_data
from utils.prts.field_mapping import _map_common_block, _map_level_block, build_enemy_raw
from utils.prts.wikitext_templates import (
    _extract_all_template_bodies,
    _extract_template_body,
    _parse_template_params,
)


class TestExtractTemplateBody:
    def test_extracts_simple_template(self):
        wikitext = "前文{{敌人信息/common2|名称=测试敌人|地位级别=普通}}后文"
        body = _extract_template_body(wikitext, "敌人信息/common2")
        assert body == "|名称=测试敌人|地位级别=普通"

    def test_returns_none_when_template_absent(self):
        assert _extract_template_body("没有模板的文本", "敌人信息/common2") is None

    def test_handles_nested_braces_by_tracking_depth(self):
        # 参数值内部还有一层 {{...}}（如内嵌其他模板调用），必须按深度匹配到最外层收尾
        wikitext = "{{敌人信息/common2|描述={{术语|概述|杂兵}}结束}}"
        body = _extract_template_body(wikitext, "敌人信息/common2")
        assert body == "|描述={{术语|概述|杂兵}}结束"

    def test_rejects_prefix_match_with_longer_template_name(self):
        # 模板名后紧跟的字符必须是 "|{ \t\n\r" 之一，否则不算真正匹配
        # 例如查找 "敌人信息/common2" 时，页面里实际是 "敌人信息/common2extra"，不应误匹配
        wikitext = "{{敌人信息/common2extra|名称=x}}"
        assert _extract_template_body(wikitext, "敌人信息/common2") is None

    def test_unclosed_template_returns_none(self):
        wikitext = "{{敌人信息/common2|名称=测试"
        assert _extract_template_body(wikitext, "敌人信息/common2") is None


class TestExtractAllTemplateBodies:
    def test_finds_multiple_occurrences_in_order(self):
        wikitext = (
            "{{敌人信息/levelcontent|index=0|名称=一}}"
            "中间文本"
            "{{敌人信息/levelcontent|index=1|名称=二}}"
        )
        bodies = _extract_all_template_bodies(wikitext, "敌人信息/levelcontent")
        assert len(bodies) == 2
        assert "index=0" in bodies[0]
        assert "index=1" in bodies[1]

    def test_empty_list_when_none_found(self):
        assert _extract_all_template_bodies("无模板", "敌人信息/levelcontent") == []

    def test_skips_false_prefix_match_and_continues_scanning(self):
        # 第一个是误匹配前缀（后接字母），第二个是真正的模板，必须能跳过第一个继续找到第二个
        wikitext = "{{敌人信息/levelcontentX}}后面{{敌人信息/levelcontent|index=0}}"
        bodies = _extract_all_template_bodies(wikitext, "敌人信息/levelcontent")
        assert len(bodies) == 1
        assert "index=0" in bodies[0]


class TestParseTemplateParams:
    def test_parses_simple_key_value_pairs(self):
        params = _parse_template_params("|名称=测试|地位级别=普通")
        assert params == {"名称": "测试", "地位级别": "普通"}

    def test_value_may_contain_pipe_inside_double_bracket_link(self):
        # 值内的 [[链接|显示文本]] 含有竖线，不应被当作字段分隔符
        params = _parse_template_params("|描述=参见[[某某条目|显示名]]结束")
        assert params["描述"] == "参见[[某某条目|显示名]]结束"

    def test_value_may_contain_pipe_inside_nested_template(self):
        params = _parse_template_params("|描述={{术语|概述|文本}}结束")
        assert params["描述"] == "{{术语|概述|文本}}结束"

    def test_value_may_contain_pipe_inside_html_comment(self):
        params = _parse_template_params("|备注=<!-- 内部|注释 -->正文")
        assert params["备注"] == "<!-- 内部|注释 -->正文"

    def test_strips_whitespace_around_key_and_value(self):
        params = _parse_template_params("| 名称 = 带空格的值 ")
        assert params == {"名称": "带空格的值"}

    def test_empty_input_yields_empty_dict(self):
        assert _parse_template_params("") == {}


    def test_map_level_block_converts_numeric_and_string_fields(self):
        zh = {
            "最大生命值": "1000",
            "攻击力": "350",
            "移动速度": "1.5",
            "地位": "普通",
            "眩晕抗性": "无",
            "沉默抗性": "有",
        }
        out = _map_level_block(zh)
        assert out["max_hp"] == 1000
        assert out["attack"] == 350
        assert out["move_speed"] == 1.5
        assert out["position"] == "普通"
        assert out["abnormal_resistances"] == {"晕眩": 0.0, "沉默": 1.0}

    def test_map_level_block_ignores_unknown_keys(self):
        assert _map_level_block({"未知字段": "值"}) == {}

    def test_map_common_block_only_maps_known_keys(self):
        zh = {"名称": "测试敌人", "伤害类型": "法术", "未知字段": "忽略"}
        out = _map_common_block(zh)
        assert out == {"name": "测试敌人", "damage_type": "法术"}


class TestBuildEnemyRaw:
    def test_returns_none_when_no_templates_present(self):
        assert build_enemy_raw("没有任何模板的普通文本") is None

    def test_merges_common_and_level_templates(self):
        wikitext = (
            "{{敌人信息/common2|名称=测试敌人|伤害类型=法术}}"
            "{{敌人信息/levelcontent|index=0|最大生命值=1000|攻击力=100}}"
        )
        merged = build_enemy_raw(wikitext)
        assert merged is not None
        assert merged["name"] == "测试敌人"
        assert merged["damage_type"] == "法术"
        assert merged["max_hp"] == 1000
        assert merged["attack"] == 100

    def test_multiple_level_blocks_merge_by_ascending_index(self):
        # index 较大的 levelcontent 后覆盖 index 较小的同名字段
        wikitext = (
            "{{敌人信息/levelcontent|index=1|最大生命值=2000}}"
            "{{敌人信息/levelcontent|index=0|最大生命值=1000}}"
        )
        merged = build_enemy_raw(wikitext)
        assert merged is not None
        assert merged["max_hp"] == 2000

    def test_missing_index_defaults_to_zero_without_raising(self):
        wikitext = "{{敌人信息/levelcontent|最大生命值=500}}"
        merged = build_enemy_raw(wikitext)
        assert merged is not None
        assert merged["max_hp"] == 500

    def test_skill_slots_are_collected_into_skills_list(self):
        wikitext = (
            "{{敌人信息/levelcontent|index=0"
            "|技能0=迅捷攻击|技能0效果=造成150%伤害|技能0技力消耗=10}}"
        )
        merged = build_enemy_raw(wikitext)
        assert merged is not None
        assert len(merged["skills"]) == 1
        assert merged["skills"][0]["名称"] == "迅捷攻击"
        assert merged["skills"][0]["效果"] == "造成150%伤害"
        assert merged["skills"][0]["技力消耗"] == "10"

    def test_empty_category_defaults_to_qita(self):
        wikitext = "{{敌人信息/levelcontent|index=0|最大生命值=100|种类=}}"
        merged = build_enemy_raw(wikitext)
        assert merged is not None
        assert merged["category"] == "其他"

    def test_strips_html_comments_from_description_fields(self):
        wikitext = (
            "{{敌人信息/levelcontent|index=0"
            "|描述=正文<!-- 内部注释 -->结尾|天赋=能力说明<!-- 备注 -->}}"
        )
        merged = build_enemy_raw(wikitext)
        assert merged is not None
        assert merged["brief_description"] == "正文结尾"
        assert merged["talents_abilities"] == "能力说明"


class TestToEnemyData:
    def test_builds_enemy_data_with_provided_fields(self):
        raw = {
            "name": "测试敌人",
            "grade": "B",
            "max_hp": 5000,
            "attack": 200,
        }
        enemy = to_enemy_data(raw, fallback_name="兜底名称")
        assert enemy is not None
        assert enemy.name == "测试敌人"
        assert enemy.grade == "B"
        assert enemy.max_hp == 5000
        assert enemy.attack == 200

    def test_uses_fallback_name_when_name_missing(self):
        enemy = to_enemy_data({}, fallback_name="兜底名称")
        assert enemy is not None
        assert enemy.name == "兜底名称"
        assert "兜底名称" in enemy.brief_description

    def test_applies_default_values_for_missing_numeric_fields(self):
        enemy = to_enemy_data({}, fallback_name="x")
        assert enemy is not None
        assert enemy.max_hp == 1000
        assert enemy.attack == 100
        assert enemy.grade == "C"

    def test_returns_none_when_raw_contains_error_key(self):
        raw = {"error": "网络超时", "error_type": "network"}
        assert to_enemy_data(raw, fallback_name="x") is None

    def test_returns_none_when_grade_invalid(self):
        # EnemyData 的 grade 校验只接受 S/A/B/C/D；构建失败应返回 None 而非抛异常
        raw = {"grade": "不合法等级"}
        assert to_enemy_data(raw, fallback_name="x") is None

    def test_normalizes_skills_from_dict_list(self):
        raw = {
            "skills": [
                {"名称": "技能A", "效果": "效果描述"},
            ]
        }
        enemy = to_enemy_data(raw, fallback_name="x")
        assert enemy is not None
        assert len(enemy.skills) == 1
        assert enemy.skills[0].名称 == "技能A"

    def test_non_dict_abnormal_resistances_falls_back_to_empty(self):
        raw = {"abnormal_resistances": "不是字典"}
        enemy = to_enemy_data(raw, fallback_name="x")
        assert enemy is not None
        assert enemy.abnormal_resistances == {}
