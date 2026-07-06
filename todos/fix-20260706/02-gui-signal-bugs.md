# 批次 2：GUI 信号连接真实 bug

**风险等级**：P0 — 均为已定位到具体行号的真实 bug，非理论风险。

## 任务

### 2.1 `combat_stats_panel` 缺少刷新守卫（信号风暴）

- [ ] 位置：`gui/panels/combat_stats_panel.py:165-190`（`_refresh_from_model`）。
- [ ] 问题：直接对 12 个 `QSpinBox`/`QDoubleSpinBox` 调用 `setValue()`，未 `blockSignals` 也没有 `_syncing_ui` 守卫标志，而 `_connect_signals`（124-149 行）里每个 spin 的 `valueChanged` 都直接连到 `propertyChanged.emit`，导致"刷新引起再次刷新/再次写回模型"的信号风暴。
- [ ] 修复：参照同一代码库里 `basic_info_panel`（`_syncing_ui`）、`rating_panel`（`blockSignals`）、`skill_editor_panel`（`_suppress_skill_emit`）三者之一已有的模式，选择其中一种统一手法（建议 `blockSignals`，改动最小），在 `_refresh_from_model` 开头/结尾包裹全部 12 个 spin widget 的赋值。
- [ ] 验收：新建卡片 / 加载文件 / PRTS 导入 / 重置数据后，观察日志或加断点确认 `combat_stats_panel` 对应字段的 `update_property` 不再被刷新自身触发的信号重复调用。

### 2.2 `set_card_model()` 重复连接信号

- [ ] 位置：`gui/property_panel.py:110-122`、`gui/panels/basic_info_panel.py:138-142`、`combat_stats_panel.py:159-163`、`resistance_panel.py:78-82`、`skill_editor_panel.py:318-322`、`rating_panel.py:347-351`（共 6 处）。
- [ ] 问题：`set_card_model()` 全部无条件重新调用 `self._connect_signals()`，而 `_connect_signals()` 里的 `connect()` 从不先 `disconnect()`，也未用 `Qt.UniqueConnection`。当前调用路径下每个面板一次生命周期只调用一次 `set_card_model` 所以尚未触发，但这是脆弱的隐藏契约。
- [ ] 修复（二选一，6 处统一用同一种手法）：
  - (a) 给每处 `_connect_signals()` 顶部加幂等保护：`if getattr(self, '_signals_connected', False): return` / 结尾置位 `self._signals_connected = True`；或
  - (b) 全部 `connect()` 调用统一加 `Qt.ConnectionType.UniqueConnection` 参数，重复连接时静默跳过而非报错。
- [ ] 验收：手动调用两次 `set_card_model()` 后触发一次属性变化，确认对应 `update_property`/`propertyChanged` 只触发一次（可加临时计数器验证后移除，或写成单元测试）。

### 2.3 `MainWindow._new_card()` 重复连接 `exportRequested`（已确认的真实 bug）

- [ ] 位置：`gui/main_window.py:268-275`（`_new_card`）+ `gui/main_window.py:187-193`（`_connect_signals`）。
- [ ] 问题：`_new_card()` 重建 `CardModel` 后调用 `self._connect_signals()`，但该方法同时也重新连接了 `self.preview_widget.exportRequested`（`preview_widget` 对象本身没变，只是 `card_model` 变了）——**已验证**：新建卡片 3 次后，导出按钮点击会触发 3 次 `self._export_image()`，弹出多个重复的成功提示框/文件对话框。
- [ ] 修复：拆分 `_connect_signals()` 为两部分——`_connect_model_signals()`（只处理 `card_model.dataChanged`，可重复调用）与保留在 `__init__` 中一次性连接的 `preview_widget.exportRequested`；`_new_card()` 只调用前者。
- [ ] 验收：连续执行"新建卡片"5 次后，点击导出图片仅弹出 1 次对话框/提示框。

## 关联验证

- 2.1、2.2 属于同一类"面板刷新/信号连接缺乏统一守卫机制"问题，修复时建议一次性审视 5 个 panel + `property_panel.py` 是否用了同一套守卫命名/机制，避免本次修复后又出现第 6 种不同的实现方式（当前已有 3 种：`_syncing_ui`/`blockSignals`/`_suppress_skill_emit`，不要再引入第 4 种）。
- 若批次 0 的测试基础设施已就绪，为 `CardModel.update_property` 与各 panel 的 `_refresh_from_model` 补充针对信号触发次数的单元测试（用 `unittest.mock` 计数 `propertyChanged`/`dataChanged` 的 emit 次数）。
