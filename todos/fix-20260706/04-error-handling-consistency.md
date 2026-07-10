# 批次 4：错误处理一致性与死代码清理

**风险等级**：P1 — 无并发/数据安全风险，但直接影响用户能否看到真实错误原因，且死代码持续误导后来维护者。

**执行状态：已完成。** `uv run pytest` 117 个测试全部通过（原 107 个 + 本批次新增 10 个：`tests/test_card_model_error_handling.py` 8 个 + `tests/test_gui_signals.py::TestPropertyPanelValidationFailedRefresh` 2 个）。

## 4.1 `CardModel` 绕开统一错误处理机制

- [x] 位置：`gui/card_model.py`：
  - `update_property`（74-75 行）：`except Exception as e: print(f"数据验证失败: {e}")`
  - `load_from_file`（106-107 行）：`except Exception as e: print(f"加载文件失败: {e}")`，`return False`
  - `save_to_file`（116-117 行）：`except Exception as e: print(f"保存文件失败: {e}")`，`return False`
- [x] 问题：`main_window.py` 里所有 IO 路径（`_open_file`/`_save_config`/`_export_image`）都正确使用了 `error_handler` + `categorize_error_message`；`CardModel` 作为下层却自行吞异常打印到控制台——而项目以 `pyinstaller --windowed` 打包（见 `CLAUDE.md` 打包命令），`--windowed` 模式下没有可见的 stdout，这些 print 在生产环境等于完全消失。调用方 `main_window.py:290-291` 拿到的只是一个笼统的 `ValidationError("无效的配置文件格式")`，无法反映真实原因（JSON 语法错误 vs Pydantic 字段校验错误 vs 其他）。
- [x] 修复：`load_from_file`/`save_to_file` 改为不吞异常，向上抛出 `FileOperationError`（见 4.2），`gui/main_window.py::_open_file`/`_save_config` 相应简化为直接调用（去掉旧的布尔返回值判断与 `else: raise ValidationError(...)` 兜底），由外层既有的 `except EnemyEvalException` + `categorize_error_message` 统一展示。`update_property` 属高频交互路径（每次 spinbox/combobox 编辑都会触发），改为 raise 会在每次校验失败时抛出未捕获异常崩溃 GUI——故改为 `logging.getLogger(__name__).error(..., exc_info=True)` + 新增 `validationFailed` 信号（见下一条），而非 raise。
  - **额外修复**：`utils/error_handler.py::categorize_error_message` 的"保存"/"加载"分支原先返回固定文案、完整丢弃传入的 `error_message`（导致即使下层已抛出带字段详情的异常，用户看到的仍是笼统提示）。已改为在文案中内嵌 `{error_message}`，与 else 分支一致。
- [x] 关联：新增 `CardModel.validationFailed = Signal(str, str)`（`property_name`, `error_message`），`update_property` 校验失败时 emit 该信号（不再单纯 print）。`gui/property_panel.py::PropertyPanel` 新增 `_connect_model_signals()`（连接 `card_model.validationFailed` → `_on_validation_failed` → `self._refresh_from_model()`，恢复全部 5 个子面板 UI 为模型当前真实值），刻意放在 `_signals_connected` 幂等守卫之外，确保 `set_card_model()` 换新模型实例时也能重新绑定新实例的信号。批次 2 的信号守卫工作已完成，无冲突。

## 4.2 启用或删除 `FileOperationError`

- [x] 位置：`utils/error_handler.py:27-29` 定义 `FileOperationError`，但 `utils/__init__.py` 的 `__all__` 未导出，全仓库 grep 除自身定义外零调用点（已用 grep 验证）。
- [x] 决策：采用方案 (a)——`card_model.py::load_from_file`/`save_to_file` 失败分支改为 `raise FileOperationError(...)`，`utils/__init__.py::__all__` 补充导出。

## 4.3 删除确认为死代码的模型/方法

以下均已用 `grep`/`lsp references` 验证：定义后除自身文件外全仓库零引用。

- [x] `models/card_style.py::CardStyle`：宽高（800×600）与实际渲染生效的 `RenderConfig`（1950×1500）数值都对不上，是"看起来在生效但从未接入渲染管线"的孤立模型。已删除该文件，同步移除 `models/__init__.py` 中的 `from .card_style import CardStyle` 与 `__all__` 里的 `"CardStyle"`。
- [x] `core/optimization.py::ImageProcessor.create_rounded_image`（静态方法）：`core/render/sections/avatar.py` 实际给头像做圆角展示时并未调用它，而是另用 `drawRoundRect` 画白底圆角框实现"视觉裁剪"。`lsp references` 确认零调用点，已删除，未选择批次 5 的统一实现方案（二选一中选删除）。
- [x] `core/optimization.py::clear_caches`：已在批次 1 处理（挂到 `closeEvent`），本批次不重复处理，与 `01-thread-safety-render.md` 记录一致。

## 验收标准

- [x] `grep -rn "print(f\"" gui/card_model.py` 无匹配（全部替换为 logger 或异常抛出）。
- [x] `utils/__init__.py::__all__` 包含 `FileOperationError`（方案 a）。
- [x] `grep -rn "CardStyle" .` 除 CHANGELOG/本 todo 文档外零匹配。
- [x] 错误提示可反映具体字段/校验失败：由 `tests/test_card_model_error_handling.py` + `tests/test_error_handler.py` 覆盖（`FileOperationError` 文案内嵌详情、`categorize_error_message` 保留原文）；GUI 弹窗路径与 `main_window` 既有 `EnemyEvalException` 展示一致。
