"""CardModel error-handling contract tests.

Covers the error-handling consistency changes from
``todos/fix-20260706/04-error-handling-consistency.md``.
"""

from __future__ import annotations

import json
from unittest.mock import Mock

import pytest

from gui.card_model import CardModel
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
