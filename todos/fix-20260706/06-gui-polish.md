# 批次 6：GUI 可维护性打磨

**风险等级**：P2/P3 — 纯可维护性/风格问题，不影响功能正确性，优先级最低，可在人力充裕时再排期。

## 6.1 `MainWindow` 职责过重

- [ ] 位置：`gui/main_window.py` 全类，420 行/23 方法，混杂 UI 编排、渲染线程生命周期管理（`_generate_card`/`_release_finished_render_thread`/`_on_card_generated`/`_on_generation_error`）、文件 IO（`_open_file`/`_save_config`/`_export_image`）、PRTS 网络请求处理（`_fetch_prts_data`）四类职责；`_export_image`（314-337 行）还直接操作 `self.last_generated_pixmap.save(file_path)` 这类渲染产物序列化细节。
- [ ] 修复：抽取 `RenderCoordinator`（或 `CardExportService`）类，专职管理 `generator_thread`、`_orphan_render_threads`、`revision` 计数与信号中转；`MainWindow` 只保留 UI 编排和转发。`_export_image` 的 `pixmap.save` 逻辑迁移到该服务或 `preview_widget` 提供的 `save_current(path)` 接口。
- [ ] 建议在批次 1（线程模型可能已因方案 A/B 调整）和批次 3.1（新增 `PrtsFetchThread`）都完成后再做这项重构，避免抽取时基准线不稳定。

## 6.2 面板防抖样板重复

- [ ] 位置：`gui/panels/basic_info_panel.py`（20-28 行）、`rating_panel.py`（281-288 行）、`skill_editor_panel.py`（71-75,198-202 行）各自手写几乎相同的固定延迟 `QTimer` 防抖样板，延迟数值分别是 220ms/280ms/240ms，各不相同且是硬编码字面量；均未复用已有的 `utils/debouncer.py::AdaptiveDebouncer`。
- [ ] 修复：抽取 `TextChangeDebouncer`/`DebouncedSignalMixin` 小工具类（放 `gui/panels/_debounce.py` 或扩展 `utils/debouncer.py`），接收 `(signal_emit_callable, delay_ms)`，各 panel 用组合方式复用。`resistance_panel`/`combat_stats_panel` 是 checkbox/spinbox 值变化即定稿，不需要此模式，不用改。

## 6.3 布局尺寸魔法数字散落

- [ ] 位置：`gui/main_window.py:49-50`（`setGeometry(100,100,1400,900)`/`setMinimumSize(1200,800)`）、`gui/property_panel.py:23`（`setFixedWidth(400)`）、`gui/main_window.py:171`（`splitter.setSizes([400,900])`）、`gui/preview_widget.py:317-318,194` 等多处窗口/面板尺寸字面量，且部分存在隐含关联（`property_panel` 固定宽度 400 应与 `main_window` 里 `splitter.setSizes([400, 900])` 第一个值保持一致，目前是两处独立字面量）。
- [ ] 修复：新增 `gui/constants.py`（或 `gui/styles/layout_constants.py`）集中定义 `DEFAULT_WINDOW_SIZE`、`PROPERTY_PANEL_WIDTH`、`PREVIEW_AVAILABLE_SIZE` 等常量，三个文件统一引用。

## 6.4 配色不统一，未走样式模块

- [ ] 位置：`gui/preview_widget.py`（159-174,291 行）与 `gui/prts_reference_dialog.py`（85-176 行）重复内联相同的按钮配色（`#409eff`/`#66b1ff`/`#c0c4cc`）；`gui/detailed_editor_dialog.py`（36-184 行）又用另一套完全不同的配色（`#3b82f6` 系）。`gui/styles/property_panel_styles.py` 是项目里唯一的样式常量集中地，但这三个文件完全没有引用它。
- [ ] 修复：将三个文件的内联 QSS 迁移到 `gui/styles/` 下新增模块（如 `dialog_styles.py`、`preview_styles.py`），统一复用同一套色彩变量（如 `PRIMARY_COLOR = '#409eff'`），消除同色不同名/同名不同色问题。这也是落实 `CLAUDE.md`"样式 styles.qss + gui/styles/"约定的具体执行。

## 6.5 类型注解与异常捕获细节

- [ ] `core/optimization.py:46`：`RenderResourceManager.__init__(self, config: RenderConfig = None)` 缺 `Optional`，改为 `config: Optional[RenderConfig] = None`。
- [ ] `utils/network_image.py:18`（`is_url` 内裸 `except:`）改为 `except ValueError:`。
- [ ] 风格清理（非强制）：`gui/property_panel.py:52-58` 存在 6 个连续空行（重构遗留），`_update_property` 与相邻方法间距不统一，运行项目格式化工具（如已配置 black/ruff format）清理即可，不需要手动逐行改。

## 验收标准

- 这批改动全部不涉及行为变化，用视觉对比（截图前后对比 GUI 窗口）确认外观无变化即可，无需额外编写测试。
- `grep -rn "#409eff\|#66b1ff\|#c0c4cc" gui/*.py` 确认改动后配色只在 `gui/styles/` 模块内定义一次，其余位置改为常量引用。
