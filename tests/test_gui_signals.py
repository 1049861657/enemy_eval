"""GUI 信号相关回归测试（todos/fix-20260706/02-gui-signal-bugs.md 批次2）。

覆盖三类修复：
1. CombatStatsPanel._refresh_from_model 的信号风暴保护（blockSignals 包裹刷新过程）。
2. 6 个面板 `_connect_signals()` 的幂等性保护（`_signals_connected` 标志位）。
3. MainWindow._new_card() 不再重复连接 preview_widget.exportRequested。

全部测试离线、无头运行（QT_QPA_PLATFORM=offscreen，见 tests/conftest.py），
不弹出真实对话框、不产生真实文件 I/O、不启动真实渲染线程。
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from gui.card_model import CardModel
from gui.panels.basic_info_panel import BasicInfoPanel
from gui.panels.combat_stats_panel import CombatStatsPanel
from gui.panels.rating_panel import RatingPanel
from gui.panels.resistance_panel import ResistancePanel
from gui.panels.skill_editor_panel import SkillEditorPanel
from gui.property_panel import PropertyPanel


@pytest.fixture
def card_model(qapp):
    """一个干净的、带默认敌人数据的 CardModel。"""
    return CardModel()


class TestCombatStatsPanelSignalStormGuard:
    """修复1：_refresh_from_model 在刷新期间必须屏蔽 12 个 spinbox 的信号。"""

    def test_refresh_from_model_emits_no_property_changed(self, qapp, card_model):
        panel = CombatStatsPanel(card_model)
        mock_slot = Mock()
        panel.propertyChanged.connect(mock_slot)

        panel._refresh_from_model()

        mock_slot.assert_not_called()

    def test_public_refresh_from_model_emits_no_property_changed(self, qapp, card_model):
        """外部调用入口 refresh_from_model() 同样不应该触发信号风暴。"""
        panel = CombatStatsPanel(card_model)
        mock_slot = Mock()
        panel.propertyChanged.connect(mock_slot)

        panel.refresh_from_model()

        mock_slot.assert_not_called()

    def test_set_card_model_refresh_emits_no_property_changed(self, qapp, card_model):
        """set_card_model 内部也会调用 _refresh_from_model，同样不应该风暴式发出信号。"""
        panel = CombatStatsPanel()
        mock_slot = Mock()
        panel.propertyChanged.connect(mock_slot)

        panel.set_card_model(card_model)

        mock_slot.assert_not_called()


class TestPanelConnectSignalsIdempotent:
    """修复2：_connect_signals() 幂等 —— 重复调用不应重复连接底层控件信号。"""

    def test_combat_stats_panel_double_connect_emits_once(self, qapp, card_model):
        panel = CombatStatsPanel(card_model)
        panel._connect_signals()
        panel._connect_signals()

        mock_slot = Mock()
        panel.propertyChanged.connect(mock_slot)
        panel.max_hp_spin.setValue(panel.max_hp_spin.value() + 1)

        assert mock_slot.call_count == 1

    def test_basic_info_panel_double_connect_emits_once(self, qapp, card_model):
        panel = BasicInfoPanel(card_model)
        panel._connect_signals()
        panel._connect_signals()

        mock_slot = Mock()
        panel.propertyChanged.connect(mock_slot)
        # 下拉框切换是非防抖的直接信号路径，用来做确定性触发
        current = panel.grade_combo.currentText()
        other = next(
            panel.grade_combo.itemText(i)
            for i in range(panel.grade_combo.count())
            if panel.grade_combo.itemText(i) != current
        )
        panel.grade_combo.setCurrentText(other)

        assert mock_slot.call_count == 1

    def test_basic_info_panel_set_card_model_twice_emits_once(self, qapp, card_model):
        """set_card_model() 内部调用 _connect_signals()，重复调用同样不应重复连接。"""
        panel = BasicInfoPanel()
        panel.set_card_model(card_model)
        panel.set_card_model(card_model)

        mock_slot = Mock()
        panel.propertyChanged.connect(mock_slot)
        current = panel.grade_combo.currentText()
        other = next(
            panel.grade_combo.itemText(i)
            for i in range(panel.grade_combo.count())
            if panel.grade_combo.itemText(i) != current
        )
        panel.grade_combo.setCurrentText(other)

        assert mock_slot.call_count == 1

    def test_resistance_panel_double_connect_emits_once(self, qapp, card_model):
        panel = ResistancePanel(card_model)
        panel._connect_signals()
        panel._connect_signals()

        mock_slot = Mock()
        panel.resistanceChanged.connect(mock_slot)
        checkbox = next(iter(panel.resistance_checkboxes.values()))
        checkbox.setChecked(not checkbox.isChecked())

        assert mock_slot.call_count == 1

    def test_skill_editor_panel_double_connect_talents_emits_once(self, qapp, card_model):
        """talentsChanged 走防抖定时器，直接调用 flush 槽而不是真实等待计时器。"""
        panel = SkillEditorPanel(card_model)
        panel._connect_signals()
        panel._connect_signals()

        mock_slot = Mock()
        panel.talentsChanged.connect(mock_slot)
        panel.talents_edit.setPlainText("新的天赋描述")
        # 跳过真实计时器等待：直接触发计时器已连接的槽函数
        panel._flush_talents_changed()

        assert mock_slot.call_count == 1

    def test_rating_panel_double_connect_rating_emits_once(self, qapp, card_model):
        """星级评价是非防抖的直接信号路径，用来做确定性触发。"""
        panel = RatingPanel(card_model)
        panel._connect_signals()
        panel._connect_signals()

        mock_slot = Mock()
        panel.ratingChanged.connect(mock_slot)
        panel.hostility_rating.setValue(
            panel.hostility_rating.getValue() % panel.hostility_rating.max_stars + 1
        )

        assert mock_slot.call_count == 1

    def test_rating_panel_double_connect_description_emits_once(self, qapp, card_model):
        """descriptionChanged 走防抖定时器，直接 flush 而不是真实等待。"""
        panel = RatingPanel(card_model)
        panel._connect_signals()
        panel._connect_signals()

        mock_slot = Mock()
        panel.descriptionChanged.connect(mock_slot)
        panel.brief_description_edit.setPlainText("新的描述文本")
        panel._flush_description_changed()

        assert mock_slot.call_count == 1

    def test_property_panel_double_connect_emits_once(self, qapp, card_model):
        """PropertyPanel._connect_signals() 桥接子面板信号到 card_model.update_property。"""
        panel = PropertyPanel(card_model)
        panel._connect_signals()
        panel._connect_signals()

        mock_update = Mock()
        panel.card_model.update_property = mock_update
        panel.combat_panel.propertyChanged.emit("max_hp", 12345)

        assert mock_update.call_count == 1
        mock_update.assert_called_once_with("max_hp", 12345)



class TestPropertyPanelValidationFailedRefresh:
    """错误处理一致性：CardModel 校验失败后 PropertyPanel 必须恢复 UI 为模型真实值。"""

    def test_validation_failed_refreshes_from_model_once(self, qapp, card_model, monkeypatch):
        panel = PropertyPanel(card_model)
        refresh_from_model = Mock()
        monkeypatch.setattr(panel, "_refresh_from_model", refresh_from_model)

        card_model.validationFailed.emit("grade", "some error")

        refresh_from_model.assert_called_once_with()

    def test_set_card_model_reconnects_validation_failed_to_new_model_once(
        self, qapp, card_model, monkeypatch
    ):
        panel = PropertyPanel(card_model)
        new_card_model = CardModel()
        panel.set_card_model(new_card_model)
        refresh_from_model = Mock()
        monkeypatch.setattr(panel, "_refresh_from_model", refresh_from_model)

        new_card_model.validationFailed.emit("grade", "some error")

        refresh_from_model.assert_called_once_with()


class TestMainWindowNewCardNoDuplicateExport:
    """修复3：_new_card() 不再重复连接 preview_widget.exportRequested。"""

    @pytest.fixture
    def main_window(self, qapp, monkeypatch):
        from PySide6.QtWidgets import QMessageBox

        from gui.main_window import MainWindow

        # 避免真实的模态确认对话框阻塞测试
        monkeypatch.setattr(
            QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes
        )
        # 避免启动真实的 CardGeneratorThread（QThread）
        monkeypatch.setattr(MainWindow, "_generate_card", lambda self: None)
        # 避免真实的 _export_image 弹出 QFileDialog 阻塞测试；
        # exportRequested 在 __init__ 里已经连到它，必须在信号真正 emit 前替换掉
        monkeypatch.setattr(MainWindow, "_export_image", Mock())

        window = MainWindow()
        yield window
        window.close()

    def test_new_card_called_thrice_export_fires_once(self, main_window):
        main_window._new_card()
        main_window._new_card()
        main_window._new_card()

        main_window.preview_widget.exportRequested.emit()

        assert main_window._export_image.call_count == 1

    def test_new_card_replaces_card_model_each_call(self, main_window):
        """_new_card 仍应正确替换 card_model 并重连 dataChanged（功能未被破坏）。"""
        first_model = main_window.card_model
        main_window._new_card()
        second_model = main_window.card_model

        assert second_model is not first_model

        mock_data_changed = Mock()
        main_window.card_model.dataChanged.connect(mock_data_changed)
        main_window.card_model.update_property("max_hp", 999)

        assert mock_data_changed.call_count == 1
