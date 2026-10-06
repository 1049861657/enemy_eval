"""core.render.layout：卡片纵向占位测算的单元测试。"""

from __future__ import annotations

from core.fonts import FontManager
from core.render.layout import measure_grade_block_height, measure_render_height
from models import EnemyData


def _make_enemy(**overrides) -> EnemyData:
    base = dict(
        name="测试敌人",
        grade="C",
        attack_type="近战",
        damage_type="物理",
        action_type="地面",
        hp_recovery_speed=0.0,
        position="普通",
        category="其他",
        max_hp=1000,
        attack=100,
        defense=50,
        magic_resistance=10,
        attack_range_radius=0.0,
        weight_level=1,
        move_speed=1.0,
        attack_interval=2.0,
        damage_resistance=0,
        element_resistance=0,
        base_taunt_level=0,
        target_value=1,
        brief_description="简要描述",
        brief_comment="简评内容",
        abnormal_resistances={},
        ratings=[
            {"name": "对策度", "score": 3},
            {"name": "创新度", "score": 3},
            {"name": "威胁度", "score": 3},
        ],
        avatar_path=None,
        skills=[],
        talents_abilities="",
    )
    base.update(overrides)
    return EnemyData(**base)


def _simple_wrap_text(text: str, max_width: int, font_size: int) -> list[str]:
    # 与真实换行算法解耦：固定按 20 字符一行切分，用于验证测量函数对行数的响应
    if not text:
        return [""]
    chunk = 20
    return [text[i : i + chunk] for i in range(0, len(text), chunk)] or [""]


class TestMeasureGradeBlockHeight:
    def test_empty_comment_uses_minimum_height(self):
        enemy = _make_enemy(brief_comment="")
        height = measure_grade_block_height(enemy, _simple_wrap_text)
        assert height >= 210.0  # GRADE_BLOCK_MIN_H

    def test_longer_comment_increases_height(self):
        short_enemy = _make_enemy(brief_comment="短评语")
        long_enemy = _make_enemy(brief_comment="很长的评语内容" * 20)
        short_h = measure_grade_block_height(short_enemy, _simple_wrap_text)
        long_h = measure_grade_block_height(long_enemy, _simple_wrap_text)
        assert long_h > short_h


class TestMeasureRenderHeight:
    def test_returns_at_least_config_height_for_minimal_enemy(self):
        enemy = _make_enemy()
        font_manager = FontManager()
        height = measure_render_height(
            enemy, config_height=1500, font_manager=font_manager, wrap_text=_simple_wrap_text
        )
        assert height >= 1500

    def test_more_skills_increase_required_height(self):
        from models import SkillEntry

        font_manager = FontManager()
        no_skills = _make_enemy(skills=[])
        many_skills = _make_enemy(
            skills=[
                SkillEntry(名称=f"技能{i}", 效果="较长的技能效果描述文本" * 5)
                for i in range(5)
            ]
        )
        h_no_skills = measure_render_height(
            no_skills, config_height=100, font_manager=font_manager, wrap_text=_simple_wrap_text
        )
        h_many_skills = measure_render_height(
            many_skills, config_height=100, font_manager=font_manager, wrap_text=_simple_wrap_text
        )
        assert h_many_skills > h_no_skills

    def test_never_returns_less_than_config_height(self):
        # config_height 故意设置得很大，实际内容远小于它时，返回值不能被内容测算值下拉
        enemy = _make_enemy()
        font_manager = FontManager()
        height = measure_render_height(
            enemy, config_height=99999, font_manager=font_manager, wrap_text=_simple_wrap_text
        )
        assert height >= 99999
