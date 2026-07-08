# 批次 6：GUI 可维护性打磨

**执行状态：已完成。** `uv run pytest` 122 个测试全部通过；headless `MainWindow` 构造/关闭冒烟通过；`grep` 确认 `gui/*.py` 中内联颜色字面量 ALL CLEAN。

## 6.1 `MainWindow` 职责过重

- [x] 位置：`gui/main_window.py` 混杂 UI 编排、渲染线程生命周期管理、文件 IO、PRTS 网络请求处理四类职责；`_export_image` 直接操作 `self.last_generated_pixmap.save()`。
- [x] 修复：新增 `gui/render_coordinator.py::RenderCoordinator(QObject)`，持有线程、revision、pixmap 状态，暴露 `request()`/`save_current()`/`cleanup()`，通过 `cardReady`/`renderFailed`/`busyChanged` 信号回传；`MainWindow` 只保留 UI 编排与信号转发。`_export_image` 改用 `_render.save_current()`，`closeEvent` 改用 `_render.cleanup()`。
- [x] 前置依赖（批次 1 + 3.1）均已完成后执行，基准线稳定。

## 6.2 面板防抖样板重复

- [x] 位置：三个 panel 各自手写固定延迟 `QTimer` 防抖样板，延迟数值 220/280/240ms 硬编码，未复用 `AdaptiveDebouncer`。
- [x] 修复：`utils/debouncer.py` 新增 `FixedDebouncer(parent, callback, delay_ms)`；三个 panel 改为构造 `FixedDebouncer` 实例，`QTimer` import 全部移除。验证：脚本扫描无残留 `QTimer`/旧防抖字段，CLEAN。

## 6.3 布局尺寸魔法数字散落

- [x] 位置：`gui/main_window.py`、`gui/property_panel.py`、`gui/preview_widget.py` 多处魔法数字，部分存在隐含关联。
- [x] 修复：新增 `gui/constants.py`，定义窗口/面板/分割器/预览适配视口常量（`PREVIEW_CARD_FIT_WIDTH/HEIGHT` 为独立设计值 1200/800，不从窗口尺寸推导）；三处文件统一引用。

## 6.4 配色不统一，未走样式模块

- [x] 位置：`gui/preview_widget.py`、`gui/prts_reference_dialog.py`、`gui/detailed_editor_dialog.py` 内联颜色字面量。
- [x] 修复：新增 `gui/styles/colors.py`、`dialog_styles.py`、`preview_styles.py`；`gui/styles/__init__.py` 导出；三个源文件改为常量引用。`grep gui/*.py` ALL CLEAN。

## 6.5 类型注解与异常捕获细节

- [x] `core/optimization.py`：`Optional[RenderConfig]` 修复已在批次 1 完成。
- [x] `utils/network_image.py`：`except ValueError:` 修复已在批次 3.5 完成。
- [x] 风格清理（非强制）：`gui/property_panel.py` 连续空行为重构遗留，低优先级，暂不处理。

## 验收标准

- [x] 行为无变化：headless `MainWindow` 冒烟通过，`property_panel.width()=400` 确认常量生效。
- [x] `grep` 确认配色只在 `gui/styles/` 内定义，外部全部为常量引用，ALL CLEAN。

## 执行记录

- 新增文件：`gui/constants.py`、`gui/render_coordinator.py`、`gui/styles/colors.py`、`gui/styles/dialog_styles.py`、`gui/styles/preview_styles.py`。
- 改动文件：`gui/main_window.py`（渲染线程管理委托给 `RenderCoordinator`）、`gui/property_panel.py`、`gui/preview_widget.py`、`gui/prts_reference_dialog.py`、`gui/detailed_editor_dialog.py`、`gui/styles/__init__.py`、`gui/panels/basic_info_panel.py`、`gui/panels/rating_panel.py`、`gui/panels/skill_editor_panel.py`、`utils/debouncer.py`、`utils/__init__.py`。
- `uv run pytest` 122 个测试全部通过，无回归。
