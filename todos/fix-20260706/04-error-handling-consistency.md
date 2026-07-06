# 批次 4：错误处理一致性与死代码清理

**风险等级**：P1 — 无并发/数据安全风险，但直接影响用户能否看到真实错误原因，且死代码持续误导后来维护者。

## 4.1 `CardModel` 绕开统一错误处理机制

- [ ] 位置：`gui/card_model.py`：
  - `update_property`（74-75 行）：`except Exception as e: print(f"数据验证失败: {e}")`
  - `load_from_file`（106-107 行）：`except Exception as e: print(f"加载文件失败: {e}")`，`return False`
  - `save_to_file`（116-117 行）：`except Exception as e: print(f"保存文件失败: {e}")`，`return False`
- [ ] 问题：`main_window.py` 里所有 IO 路径（`_open_file`/`_save_config`/`_export_image`）都正确使用了 `error_handler` + `categorize_error_message`；`CardModel` 作为下层却自行吞异常打印到控制台——而项目以 `pyinstaller --windowed` 打包（见 `CLAUDE.md` 打包命令），`--windowed` 模式下没有可见的 stdout，这些 print 在生产环境等于完全消失。调用方 `main_window.py:290-291` 拿到的只是一个笼统的 `ValidationError("无效的配置文件格式")`，无法反映真实原因（JSON 语法错误 vs Pydantic 字段校验错误 vs 其他）。
- [ ] 修复：三处改为不吞异常，向上抛出 `EnemyEvalException`/`ValidationError`/`FileOperationError`（见 4.2），让调用方统一走 `categorize_error_message`；或至少用 `logging.getLogger(__name__).error(..., exc_info=True)` 替代 `print`，并将原始异常信息通过返回值/异常链传递给调用方。
- [ ] 关联：`update_property` 校验失败时应给 UI 一个恢复信号（新增 `CardModel.validationFailed(property_name, error)` signal），供各 panel 捕获后将对应 widget 恢复为 `card_model.enemy_data` 当前真实值，避免"UI 显示新值但模型仍是旧值"的隐性不一致（批次 2 的信号守卫工作完成后再做此项，避免信号机制改动叠加冲突）。

## 4.2 启用或删除 `FileOperationError`

- [ ] 位置：`utils/error_handler.py:27-29` 定义 `FileOperationError`，但 `utils/__init__.py` 的 `__all__` 未导出，全仓库 grep 除自身定义外零调用点（已用 grep 验证）。
- [ ] 决策二选一：
  - (a) 在 4.1 的 `card_model.py::load_from_file`/`save_to_file` 失败分支中改为 `raise FileOperationError(...)`，真正启用它，并在 `utils/__init__.py::__all__` 中补充导出。
  - (b) 若确认不需要区分"文件操作错误"与其他业务异常，直接删除该类。
- [ ] 推荐 (a)：现成的语义正好匹配 `card_model.py` 的两个文件 IO 失败场景，删除反而浪费已设计好的错误分类体系。

## 4.3 删除确认为死代码的模型/方法

以下均已用 `grep` 验证：定义后除自身文件外全仓库零引用。

- [ ] `models/card_style.py::CardStyle`：宽高（800×600）与实际渲染生效的 `RenderConfig`（1950×1500）数值都对不上，是"看起来在生效但从未接入渲染管线"的孤立模型。删除该文件，同步移除 `models/__init__.py` 中的 `from .card_style import CardStyle` 与 `__all__` 里的 `"CardStyle"`。
- [ ] `core/optimization.py::ImageProcessor.create_rounded_image`（静态方法）：`core/render/sections/avatar.py` 实际给头像做圆角展示时并未调用它，而是另用 `drawRoundRect` 画白底圆角框实现"视觉裁剪"。确认无其他调用点后删除；若决定统一实现方式，见批次 5 的 5.x 项（二选一，不要同时做拆分和删除的冲突改动）。
- [ ] `core/optimization.py::clear_caches`：与批次 1 的清理项重复，两个批次只需处理一次，此处不重复标记为独立任务（见 `01-thread-safety-render.md` 的"关联清理"部分）。

## 验收标准

- `grep -rn "print(f\"" gui/card_model.py` 无匹配（全部替换为 logger 或异常抛出）。
- `utils/__init__.py::__all__` 包含 `FileOperationError`（若选方案 a）或 `utils/error_handler.py` 不再定义该类（若选方案 b）。
- `grep -rn "CardStyle" .` 除 CHANGELOG/本 todo 文档外零匹配。
- 手动测试：故意提供一个字段类型错误的 JSON 配置文件用"打开配置文件"加载，弹出的错误提示应能反映具体是哪个字段/哪种校验失败，而非笼统的"无效的配置文件格式"。
