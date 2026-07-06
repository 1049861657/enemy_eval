# 批次 2：GUI 信号连接真实 bug

**风险等级**：P0 — 均为已定位到具体行号的真实 bug，非理论风险。

**执行状态：已完成。** `uv run pytest` 88 个测试全部通过（批次 0 的 75 个 + 本批次新增 13 个信号回归测试）。

## 任务

### 2.1 `combat_stats_panel` 缺少刷新守卫（信号风暴）

- [x] 位置：`gui/panels/combat_stats_panel.py:165-190`（`_refresh_from_model`）。
- [x] 问题：直接对 12 个 `QSpinBox`/`QDoubleSpinBox` 调用 `setValue()`，未 `blockSignals` 也没有 `_syncing_ui` 守卫标志，而 `_connect_signals`（124-149 行）里每个 spin 的 `valueChanged` 都直接连到 `propertyChanged.emit`，导致"刷新引起再次刷新/再次写回模型"的信号风暴。
- [x] 修复：采用 `blockSignals`（改动最小）。`_refresh_from_model` 开头对全部 12 个 spin widget 调用 `blockSignals(True)`，`try/finally` 包裹赋值逻辑，结束后统一 `blockSignals(False)`。
- [x] 验收：新增 `tests/test_gui_signals.py::TestCombatStatsPanelSignalStormGuard`（3 个测试），断言 `_refresh_from_model`/`refresh_from_model`/`set_card_model` 触发的刷新过程中 `propertyChanged` 零触发。

### 2.2 `set_card_model()` 重复连接信号

- [x] 位置：`gui/property_panel.py:110-122`、`gui/panels/basic_info_panel.py:138-142`、`combat_stats_panel.py:159-163`、`resistance_panel.py:78-82`、`skill_editor_panel.py:318-322`、`rating_panel.py:347-351`（共 6 处）。
- [x] 问题：`set_card_model()` 全部无条件重新调用 `self._connect_signals()`，而 `_connect_signals()` 里的 `connect()` 从不先 `disconnect()`，也未用 `Qt.UniqueConnection`。当前调用路径下每个面板一次生命周期只调用一次 `set_card_model` 所以尚未触发，但这是脆弱的隐藏契约。
- [x] 修复：采用方案 (a)——6 处 `_connect_signals()` 顶部统一加幂等保护 `if not self.card_model or getattr(self, '_signals_connected', False): return`（`property_panel.py` 无 `card_model` 前置判断，条件相应精简），全部 `connect()` 调用完成后统一置位 `self._signals_connected = True`。与代码库已有的 `_syncing_ui`/`blockSignals`/`_suppress_skill_emit` 三种刷新期守卫并列，未引入第 4 种刷新守卫命名（`_signals_connected` 是连接期守卫，语义不同，不冲突）。
- [x] 验收：新增 `tests/test_gui_signals.py::TestPanelConnectSignalsIdempotent`（8 个测试，覆盖全部 6 个面板 + `PropertyPanel` 顶层重复连接场景），手动调用两次 `_connect_signals()`/`set_card_model()` 后触发一次属性变化，确认对应信号只触发一次。

### 2.3 `MainWindow._new_card()` 重复连接 `exportRequested`（已确认的真实 bug）

- [x] 位置：`gui/main_window.py:268-275`（`_new_card`）+ `gui/main_window.py:187-193`（`_connect_signals`）。
- [x] 问题：`_new_card()` 重建 `CardModel` 后调用 `self._connect_signals()`，但该方法同时也重新连接了 `self.preview_widget.exportRequested`（`preview_widget` 对象本身没变，只是 `card_model` 变了）——**已验证**：新建卡片 3 次后，导出按钮点击会触发 3 次 `self._export_image()`，弹出多个重复的成功提示框/文件对话框。
- [x] 修复：拆分 `_connect_signals()` 为两部分——新增 `_connect_model_signals()`（只处理 `card_model.dataChanged`，可重复调用），`_connect_signals()` 保留为 `__init__` 中一次性调用的入口（内部调用 `_connect_model_signals()` + 连接 `preview_widget.exportRequested`）；`_new_card()` 改为只调用 `_connect_model_signals()`。
- [x] 验收：新增 `tests/test_gui_signals.py::TestMainWindowNewCardNoDuplicateExport`（2 个测试），连续执行"新建卡片"3 次后（monkeypatch 掉真实渲染线程与 `_export_image`/`QMessageBox.question`），触发一次 `exportRequested`/`dataChanged`，确认对应处理只触发一次。

## 关联验证

- 2.1、2.2 属于同一类"面板刷新/信号连接缺乏统一守卫机制"问题，5 个 panel + `property_panel.py` 已统一使用 `_signals_connected` 同一套连接期守卫命名，未引入新的第 4 种刷新期守卫实现方式。
- 已为 `CardModel` 相关 panel 的信号触发次数补充单元测试（`unittest.mock.Mock` 计数 `propertyChanged`/`dataChanged`/`exportRequested` 的 emit 次数），见 `tests/test_gui_signals.py`（13 个测试，`tests/conftest.py` 新增 `qapp` 会话级 fixture 提供 headless `QApplication`）。

## 执行记录

- 新增 `tests/conftest.py`：会话级 `qapp` fixture，在导入 Qt 前设置 `QT_QPA_PLATFORM=offscreen`，保证测试无头运行、不产生真实窗口。
- 新增 `tests/test_gui_signals.py`（13 个测试）：信号风暴保护 3 个、6 面板幂等连接 8 个、`MainWindow._new_card` 去重复连接 2 个。排查过程中发现的真实陷阱：`MainWindow.__init__` 中 `_export_image` 保持真实连接，若不 monkeypatch 会在 headless 环境下触发真实 `QFileDialog.getSaveFileName` 导致测试挂起——已在测试里 monkeypatch 掉。
- `uv run pytest` 88 个测试全部通过（批次 0 的 75 个 + 本批次新增 13 个），无回归。
- 未改动 `core/`、`utils/`：本批次问题完全在 `gui/panels/*.py` + `gui/property_panel.py` + `gui/main_window.py` 的信号编排层。
