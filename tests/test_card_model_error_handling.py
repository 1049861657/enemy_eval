"""CardModel 的错误处理与撤销栈契约测试。

字段写入非法值时发 validationFailed 且保留旧值；配置读写失败时抛 FileOperationError 且内存数据不变；
未变化或失败的写入不发 dataChanged。撤销栈按编辑步进：攻击方式与攻击范围合并为一步、技能替换不单独
入栈、整卡应用为一步，载入与整卡设置清空栈。
"""

from __future__ import annotations

import json
from unittest.mock import Mock

import pytest

from gui.card_model import CardModel
from models import SkillEntry
from utils.error_handler import FileOperationError


@pytest.fixture
def card_model(qapp):
    """A clean CardModel with default enemy data."""
    return CardModel()


def _write_enemy_config(path, card_model: CardModel, **overrides) -> dict:
    data = card_model.enemy_data.model_dump()
    data.update(overrides)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


class TestUpdatePropertyErrorHandling:
    def test_valid_update_emits_data_changed_once(self, card_model):
        data_changed = Mock()
        validation_failed = Mock()
        card_model.dataChanged.connect(data_changed)
        card_model.validationFailed.connect(validation_failed)

        result = card_model.update_property("grade", "A")

        assert result is None
        assert card_model.enemy_data.grade == "A"
        assert data_changed.call_count == 1
        assert card_model.undo_stack().count() == 1
        validation_failed.assert_not_called()

    def test_invalid_update_emits_validation_failed_and_keeps_old_value(self, card_model):
        data_changed = Mock()
        validation_failed = Mock()
        card_model.dataChanged.connect(data_changed)
        card_model.validationFailed.connect(validation_failed)
        old_dump = card_model.enemy_data.model_dump()

        result = card_model.update_property("grade", "invalid-xyz")

        assert result is None
        assert card_model.enemy_data.model_dump() == old_dump
        data_changed.assert_not_called()
        assert card_model.undo_stack().count() == 0
        assert validation_failed.call_count == 1
        property_name, error_message = validation_failed.call_args.args
        assert property_name == "grade"
        assert isinstance(error_message, str)
        assert error_message


class TestLoadFromFileErrorHandling:
    def test_success_loads_config_returns_none_and_emits_data_changed_once(
        self, card_model, tmp_path
    ):
        config_path = tmp_path / "enemy.json"
        expected = _write_enemy_config(
            config_path,
            card_model,
            name="加载后的敌人",
            grade="S",
            max_hp=4321,
        )
        data_changed = Mock()
        card_model.dataChanged.connect(data_changed)

        result = card_model.load_from_file(str(config_path))

        assert result is None
        assert card_model.enemy_data.model_dump() == expected
        assert data_changed.call_count == 1

    def test_json_syntax_error_raises_file_operation_error_and_preserves_data(
        self, card_model, tmp_path
    ):
        config_path = tmp_path / "broken.json"
        config_path.write_text("{not valid json", encoding="utf-8")
        old_dump = card_model.enemy_data.model_dump()
        data_changed = Mock()
        card_model.dataChanged.connect(data_changed)

        with pytest.raises(FileOperationError) as exc_info:
            card_model.load_from_file(str(config_path))

        assert card_model.enemy_data.model_dump() == old_dump
        data_changed.assert_not_called()
        message = str(exc_info.value)
        assert isinstance(message, str)
        assert message
        assert "加载文件失败" in message

    def test_validation_error_raises_file_operation_error_and_preserves_data(
        self, card_model, tmp_path
    ):
        config_path = tmp_path / "invalid-grade.json"
        _write_enemy_config(config_path, card_model, grade="invalid-xyz")
        old_dump = card_model.enemy_data.model_dump()
        data_changed = Mock()
        card_model.dataChanged.connect(data_changed)

        with pytest.raises(FileOperationError) as exc_info:
            card_model.load_from_file(str(config_path))

        assert card_model.enemy_data.model_dump() == old_dump
        data_changed.assert_not_called()
        message = str(exc_info.value)
        assert isinstance(message, str)
        assert message
        assert "加载文件失败" in message

    def test_missing_file_raises_file_operation_error(self, card_model, tmp_path):
        missing_path = tmp_path / "missing.json"

        with pytest.raises(FileOperationError) as exc_info:
            card_model.load_from_file(str(missing_path))

        message = str(exc_info.value)
        assert isinstance(message, str)
        assert message
        assert "加载文件失败" in message


class TestSaveToFileErrorHandling:
    def test_success_saves_config_returns_none_and_emits_no_signals(
        self, card_model, tmp_path
    ):
        output_path = tmp_path / "saved.json"
        data_changed = Mock()
        validation_failed = Mock()
        card_model.dataChanged.connect(data_changed)
        card_model.validationFailed.connect(validation_failed)

        result = card_model.save_to_file(str(output_path))

        assert result is None
        with output_path.open("r", encoding="utf-8") as f:
            saved = json.load(f)
        assert saved == card_model.enemy_data.model_dump()
        data_changed.assert_not_called()
        validation_failed.assert_not_called()

    def test_missing_parent_directory_raises_file_operation_error(
        self, card_model, tmp_path
    ):
        output_path = tmp_path / "missing-parent" / "saved.json"

        with pytest.raises(FileOperationError) as exc_info:
            card_model.save_to_file(str(output_path))

        message = str(exc_info.value)
        assert isinstance(message, str)
        assert message
        assert "保存文件失败" in message


class TestUndoStack:
    def test_undo_and_redo_restore_one_step_at_a_time(self, card_model):
        card_model.update_property("name", "甲")
        card_model.update_property("max_hp", 2000)
        data_changed = Mock()
        card_model.dataChanged.connect(data_changed)

        card_model.undo_stack().undo()

        assert card_model.enemy_data.max_hp == 1000
        assert card_model.enemy_data.name == "甲"
        assert data_changed.call_count == 1
        assert card_model.undo_stack().canRedo()

        card_model.undo_stack().redo()

        assert card_model.enemy_data.max_hp == 2000
        assert card_model.undo_stack().canUndo()
        assert not card_model.undo_stack().canRedo()

    def test_attack_type_and_range_share_one_step(self, card_model):
        card_model.update_property("attack_type", "远程")
        card_model.update_property("attack_range_radius", 2.5)
        card_model.update_properties(
            {"attack_type": "近战", "attack_range_radius": 0.0}
        )

        assert card_model.undo_stack().count() == 3

        card_model.undo_stack().undo()

        assert card_model.enemy_data.attack_type == "远程"
        assert card_model.enemy_data.attack_range_radius == 2.5

    def test_skill_replace_skips_snapshot_and_undoes(self, card_model):
        snapshot = Mock()
        card_model.snapshotChanged.connect(snapshot)

        assert card_model.replace_skills([SkillEntry(名称="冲锋")]) is True
        snapshot.assert_not_called()

        card_model.undo_stack().undo()

        assert card_model.enemy_data.skills == []
        snapshot.assert_not_called()

    def test_apply_enemy_data_is_one_undo_step(self, card_model):
        card_model.update_property("name", "改过")
        original = card_model.enemy_data.ratings[0].name

        card_model.apply_enemy_data(card_model.enemy_data)

        assert card_model.enemy_data.name == "改过"
        assert card_model.undo_stack().count() == 1

        names = [item.name for item in card_model.enemy_data.ratings]
        scores = [item.score for item in card_model.enemy_data.ratings]
        names[0] = "难度"
        card_model.apply_enemy_data(card_model.enemy_with_ratings(names, scores))

        assert card_model.enemy_data.ratings[0].name == "难度"
        assert card_model.undo_stack().count() == 2

        card_model.undo_stack().undo()

        assert card_model.enemy_data.ratings[0].name == original
        assert card_model.enemy_data.name == "改过"

    def test_load_and_set_enemy_data_clear_stack(self, card_model, tmp_path):
        card_model.update_property("name", "甲")
        config_path = tmp_path / "enemy.json"
        _write_enemy_config(config_path, card_model, name="乙")

        card_model.load_from_file(str(config_path))

        assert card_model.enemy_data.name == "乙"
        assert card_model.undo_stack().count() == 0

        card_model.update_property("name", "丙")
        card_model.set_enemy_data(card_model.enemy_data.model_copy(update={"name": "丁"}))

        assert card_model.enemy_data.name == "丁"
        assert card_model.undo_stack().count() == 0
