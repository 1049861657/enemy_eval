"""models.EnemyData / models.SkillEntry 的字段校验规则单元测试。

不含 models.CardStyle：该模型已删除（全仓库零调用点，宽高与实际渲染生效的 RenderConfig 数值不符）。
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from models import EnemyData, SkillEntry


def _valid_enemy_kwargs(**overrides) -> dict:
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
        ratings=[
            {"name": "对策度", "score": 3},
            {"name": "创新度", "score": 3},
            {"name": "威胁度", "score": 3},
        ],
    )
    base.update(overrides)
    return base


class TestEnemyDataGradeValidation:
    @pytest.mark.parametrize("grade", ["S", "A", "B", "C", "D"])
    def test_accepts_valid_grades(self, grade):
        enemy = EnemyData(**_valid_enemy_kwargs(grade=grade))
        assert enemy.grade == grade

    def test_rejects_invalid_grade(self):
        with pytest.raises(ValidationError):
            EnemyData(**_valid_enemy_kwargs(grade="X"))

    def test_rejects_lowercase_grade(self):
        with pytest.raises(ValidationError):
            EnemyData(**_valid_enemy_kwargs(grade="c"))


class TestEnemyDataNumericRangeValidation:
    def test_rejects_negative_max_hp(self):
        with pytest.raises(ValidationError):
            EnemyData(**_valid_enemy_kwargs(max_hp=-1))

    def test_accepts_zero_max_hp(self):
        enemy = EnemyData(**_valid_enemy_kwargs(max_hp=0))
        assert enemy.max_hp == 0

    def test_rejects_rating_below_one(self):
        with pytest.raises(ValidationError):
            EnemyData(**_valid_enemy_kwargs(ratings=[{"name": "对策度", "score": 0}]))

    def test_rejects_rating_above_five(self):
        with pytest.raises(ValidationError):
            EnemyData(**_valid_enemy_kwargs(ratings=[{"name": "对策度", "score": 6}]))

    @pytest.mark.parametrize("rating", [1, 3, 5])
    def test_accepts_rating_within_one_to_five(self, rating):
        enemy = EnemyData(**_valid_enemy_kwargs(
            ratings=[{"name": "对策度", "score": rating}]
        ))
        assert enemy.ratings[0].score == rating

    def test_accepts_empty_ratings(self):
        enemy = EnemyData(**_valid_enemy_kwargs(ratings=[]))
        assert enemy.ratings == []

    def test_rejects_more_than_five_ratings(self):
        with pytest.raises(ValidationError):
            EnemyData(**_valid_enemy_kwargs(ratings=[
                {"name": f"维度{i}", "score": 3} for i in range(6)
            ]))


class TestEnemyDataAvatarPathValidation:
    """头像路径只做形状校验：文件存在性属运行期状态，缺失由渲染与界面降级处理。"""

    def test_none_avatar_path_is_allowed(self):
        enemy = EnemyData(**_valid_enemy_kwargs(avatar_path=None))
        assert enemy.avatar_path is None

    def test_empty_avatar_path_is_allowed(self):
        enemy = EnemyData(**_valid_enemy_kwargs(avatar_path=""))
        assert enemy.avatar_path == ""

    def test_valid_http_url_is_allowed(self):
        enemy = EnemyData(**_valid_enemy_kwargs(avatar_path="https://example.com/a.png"))
        assert enemy.avatar_path == "https://example.com/a.png"

    def test_url_without_host_is_rejected(self):
        with pytest.raises(ValidationError):
            EnemyData(**_valid_enemy_kwargs(avatar_path="https://"))

    def test_nonexistent_local_path_is_allowed(self):
        enemy = EnemyData(**_valid_enemy_kwargs(avatar_path="不存在的路径/不存在的文件.png"))
        assert enemy.avatar_path == "不存在的路径/不存在的文件.png"

    def test_relative_local_path_is_allowed(self):
        enemy = EnemyData(**_valid_enemy_kwargs(avatar_path=r"enemy\墟\头像.png"))
        assert enemy.avatar_path == r"enemy\墟\头像.png"

    def test_non_http_prefix_is_treated_as_local_path(self):
        enemy = EnemyData(**_valid_enemy_kwargs(avatar_path="ftp://example.com/a.png"))
        assert enemy.avatar_path == "ftp://example.com/a.png"


class TestEnemyDataDefaults:
    def test_skills_default_to_empty_list(self):
        enemy = EnemyData(**_valid_enemy_kwargs())
        assert enemy.skills == []

    def test_abnormal_resistances_default_to_empty_dict(self):
        enemy = EnemyData(**_valid_enemy_kwargs())
        assert enemy.abnormal_resistances == {}

    def test_talents_abilities_defaults_to_empty_string(self):
        enemy = EnemyData(**_valid_enemy_kwargs())
        assert enemy.talents_abilities == ""


class TestSkillEntry:
    def test_all_fields_default_to_empty_string(self):
        skill = SkillEntry()
        assert skill.名称 == ""
        assert skill.冷却时间 == ""
        assert skill.技力消耗 == ""
        assert skill.效果 == ""

    def test_is_nonempty_false_when_all_fields_blank(self):
        assert SkillEntry().is_nonempty() is False

    def test_is_nonempty_true_when_any_field_set(self):
        assert SkillEntry(名称="技能名").is_nonempty() is True
        assert SkillEntry(效果="效果描述").is_nonempty() is True
