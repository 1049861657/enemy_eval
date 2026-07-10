"""QML bridge 的离线行为回归测试。"""

from __future__ import annotations

import json
from unittest.mock import Mock

import pytest

from gui.card_model import CardModel
from gui.qml_bridge import CardImageProvider, QmlBridge
from gui.render_coordinator import RenderCoordinator


@pytest.fixture
def bridge(qapp):
    model = CardModel()
    render = RenderCoordinator()
    return QmlBridge(model, render, CardImageProvider()), model, render


class TestQmlBridgeModelUpdates:
    def test_update_property_uses_pydantic_model_and_publishes_snapshot(self, bridge):
        controller, model, _ = bridge
        changed = Mock()
        controller.enemyDataChanged.connect(changed)

        controller.updateProperty("max_hp", "2345")

        assert model.enemy_data.max_hp == 2345
        payload = json.loads(changed.call_args.args[0])
        assert payload["max_hp"] == 2345

    def test_invalid_property_forwards_field_error_and_keeps_model_value(self, bridge):
        controller, model, _ = bridge
        field_error = Mock()
        controller.fieldError.connect(field_error)

        controller.updateProperty("grade", '"X"')

        assert model.enemy_data.grade == "C"
        assert field_error.call_args.args[0] == "grade"

    def test_resistance_and_rating_updates_use_explicit_slots(self, bridge):
        controller, model, _ = bridge

        controller.updateResistance("冻结", 1.0)
        controller.updateRatingScore(0, 5)

        assert model.enemy_data.abnormal_resistances["冻结"] == 1.0
        assert model.enemy_data.rating_scores[0] == 5

    def test_skill_slots_add_update_and_remove(self, bridge):
        controller, model, _ = bridge

        controller.addSkill()
        controller.updateSkill(
            0,
            json.dumps(
                {"名称": "冲锋", "冷却时间": "3", "技力消耗": "10", "效果": "造成伤害"},
                ensure_ascii=False,
            ),
        )
        controller.removeSkill(0)

        assert model.enemy_data.skills == []


class TestQmlBridgeLifecycle:
    def test_replacing_model_rebinds_snapshot_source(self, bridge):
        controller, _, _ = bridge
        replacement = CardModel()
        replacement.update_property("name", "替换后的敌人")
        published = Mock()
        controller.enemyDataChanged.connect(published)

        controller.set_card_model(replacement)
        replacement.update_property("max_hp", 5000)

        assert json.loads(published.call_args.args[0])["name"] == "替换后的敌人"

    def test_command_signals_are_exposed_to_qml(self, bridge):
        controller, _, _ = bridge
        export_requested = Mock()
        refresh_requested = Mock()
        controller.exportRequested.connect(export_requested)
        controller.refreshRequested.connect(refresh_requested)

        controller.requestExport()
        controller.requestRefresh()

        export_requested.assert_called_once_with()
        refresh_requested.assert_called_once_with()

    def test_prts_query_ignores_blank_input(self, bridge):
        controller, _, _ = bridge
        requested = Mock()
        controller.prtsQueryRequested.connect(requested)

        controller.requestPrtsQuery("   ")
        controller.requestPrtsQuery("  测试敌人  ")

        requested.assert_called_once_with("测试敌人")
