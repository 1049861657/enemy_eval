# 任务 03：撤销 / 重做

**优先级**：P1　**状态**：未开始　**依赖**：建议在任务 02 之后（偏好改动先收敛）

**影响文件**：新增 `gui/undo_stack.py`、`gui/card_model.py`、`gui/qml_bridge.py`、`gui/qml/Workspace.qml`、`gui/qml/CommandBar.qml`；同步 `tests/test_card_model_error_handling.py`、`tests/test_gui_signals.py`

## 目标

数据变更（标量字段、异常抗性、评价分数、技能表、评价标准对齐）可撤销/可重做；快捷键与菜单符合 Windows 习惯；菜单文案显示下一步动作。

## 现状与内部锚点

| 事实 | 锚点 |
|---|---|
| 每次变更整份重建 `EnemyData`（旧实例不被原地修改） | `gui/card_model.py:69`（`update_property`）、`:100`（`replace_skills`） |
| 变更入口共五个 + 一个独立提交路径 | `:69` `update_property`、`:87` `update_skill`、`:100` `replace_skills`、`:113` `update_abnormal_resistance`、`:119` `update_rating_score`、`:128` `realign_rating_scores_to_schema` |
| 技能表的唯一写入口 | `gui/skill_list_model.py::_commit` → `replace_skills`（`add`/`remove`/`updateField` 槽） |
| 校验失败分支：不改数据、只发 `validationFailed` | `gui/card_model.py` |
| 信号集 | `gui/card_model.py:22-26`（`dataChanged`/`snapshotChanged`/`validationFailed`/`ratingSchemaChanged`/`avatarPathChanged`） |
| 当前完全不可逆；确认框文案写着"无法撤销" | `gui/qml/Workspace.qml:59-60` |
| 快捷键集中处 | `gui/qml/Workspace.qml:100-105` |
| 命令栏菜单 | `gui/qml/CommandBar.qml:40-56` |
| 桥接层信号与槽的既有写法 | `gui/qml_bridge.py:54-70`、`:74-121` |
| 既有契约：变更成功恰好一次 `dataChanged`；失败保留旧数据 | `tests/test_card_model_error_handling.py` |
| 桥接信号/槽契约 | `tests/test_gui_signals.py` |

## 外部调研与出处

- **`QUndoStack` 官方语义**（<https://doc.qt.io/qt-6/qundostack.html>）：
  - `setUndoLimit(int)` / `undoLimit()` 限制栈深，超出后旧命令被丢弃（内存可控的上限手段）；
  - 每条命令可通过 `QUndoCommand::id()` 声明合并能力（基类返回 `-1` 表示不合并）；当新命令的 `id` 与"最近执行的命令"相同且非 `-1` 时，栈调用前者的 `mergeWith()`，返回 `true` 则新命令被删除而非入栈；
  - 若命令已被撤销后又推入新命令，被撤销的那条命令会被删除；
  - `canUndo()`/`canRedo()`/`undoText()`/`redoText()` 是给菜单/动作绑定的标准接口。
- **快照式 vs 命令式（工程判断 + 上述语义）**：官方框架不规定命令内容。本项目每次变更都整份重建模型，旧对象天然是不可变状态；因此**一个通用命令承载两份状态**即可覆盖全部变更类型，同时保留 `QUndoStack` 的标准语义与限额能力。
- **为什么不用 `QUndoView`**：本项目界面是 QML，`QUndoView` 是 Widgets 组件；只取 `canUndo/undoText` 类接口，不引入第二套 UI 体系。
- **合并（`mergeWith`）暂不启用**：文本框是失焦/回车才提交（`AppTextField` 的 `editingFinished` + 提交计时器），星级点击是明确动作，粒度已经合理；若将来出现拖拽式连续输入，再按官方语义用 `id()` + `mergeWith()` 合并同字段。

## 设计

### 1. 栈与命令

`gui/undo_stack.py`：

```
class _StateCommand(QUndoCommand):
    def __init__(self, model: CardModel, previous: EnemyData, next_: EnemyData, text: str)
    def undo(self) -> None:  model.restore_state(self._previous)
    def redo(self) -> None:  model.restore_state(self._next)
```

- `QUndoStack` 由 `CardModel` 持有（`QUndoStack(self)`），仅 GUI 线程访问。
- 文本：`_StateCommand` 的 `setText("修改生命值")` 一类人类可读描述，供菜单显示。

### 2. `CardModel` 侧改动

- 新增 `self._undo_stack = QUndoStack(self)`（`setUndoLimit(100)` + `setObjectName("cardModel")`）。
- 私有提交helper：

```
def _commit(self, previous: EnemyData, next_: EnemyData, text: str) -> None
    self._enemy_data = next_
    self._undo_stack.push(_StateCommand(self, previous, next_, text))
    <发原有信号>
```

- 五个变更入口改为"先抓 `previous`、校验通过后 `_commit`"；校验失败分支保持"不改数据、只发 `validationFailed`"，**不入栈**。
- 新增 `restore_state(enemy: EnemyData) -> None`：

```
self._enemy_data = enemy
dataChanged.emit(); snapshotChanged.emit()
若 avatar_path 变化 → avatarPathChanged.emit(...)
```

  - **不压栈**（`QUndoStack` 正在驱动 redo）；
  - 每次恢复恰好一次 `dataChanged`（与既有契约一致）；
  - `avatarPathChanged` 必须补发，否则撤销头像后不会重新预取/重绘。

- 快照入栈时 `model_copy(deep=True)`，防呆成本极低（文档小），避免将来出现原地修改污染历史。
- 清栈点：`load_from_file`（`:140`）、`set_enemy_data`（`:172`）、以及 MainWindow 的"新建/重置"路径 → `self._undo_stack.clear()`。

### 3. 桥接与 UI

- `gui/qml_bridge.py`：
  - Property：`canUndo`、`canRedo`（`bool`）、`undoText`、`redoText`（`str`），notify = `undoStateChanged`；
  - 槽：`@Slot() requestUndo()`、`@Slot() requestRedo()`；信号：`undoRequested`、`redoRequested`；
  - 在 `__init__` 连接 `QUndoStack` 的 `canUndoChanged`/`canRedoChanged`/`undoTextChanged`/`redoTextChanged` → `undoStateChanged`。
- `gui/main_window.py`：在 `_connect_signals`（`:104`）连接两个槽到 `CardModel` 的栈。
- `gui/qml/Workspace.qml`：`:100-105` 加 `Ctrl+Z` / `Ctrl+Shift+Z` / `Ctrl+Y` 三个 `Shortcut`；**同时修正** `:59-60` 的"无法撤销"文案（改为"当前编辑内容将被默认数据替换"）。
- `gui/qml/CommandBar.qml`：`更多` 菜单加两项：
  - `MenuItem { text: "撤销 " + controller.undoText; enabled: controller.canUndo }`
  - `MenuItem { text: "重做 " + controller.redoText; enabled: controller.canRedo }`

## 步骤

- [ ] 新增 `gui/undo_stack.py`（`_StateCommand` + 模块 docstring 说明"状态式命令"的口径）。
- [ ] `gui/card_model.py`：加栈、`_commit`、`restore_state`；五个入口接入；三处清栈。
- [ ] 桥接：四个 Property + 两个槽 + 两个信号 + 栈信号转发（连接写在 `__init__`）。
- [ ] `gui/main_window.py`：连接桥接槽；「新建/重置」路径清栈。
- [ ] QML：快捷键三枚、菜单两项、修正"无法撤销"文案。
- [ ] 同步契约测试：`tests/test_card_model_error_handling.py`（`dataChanged` 次数、失败不入栈后的状态）、`tests/test_gui_signals.py`（新 Property/信号）。

## 非目标

- 不做跨文件、跨会话的撤销历史。
- 不做"变更历史面板"（`QUndoView` 是 Widgets，且产物不需要）。
- 不做高频输入的命令合并（理由见上）。
- 不把撤销与草稿/自动保存耦合（本计划不含草稿功能）。

## 风险与回滚

| 风险 | 处置 |
|---|---|
| 撤销后预览不刷新 | 恢复走同一条 `dataChanged` 链路（`MainWindow._on_data_changed` 防抖 → 渲染请求） |
| 撤销头像后不重新取图 | `restore_state` 补发 `avatarPathChanged`；命中缓存则不新起线程 |
| 历史被原地修改污染 | 入栈深拷贝 |
| 内存增长 | `setUndoLimit(100)` |
| 违反"成功恰好一次 dataChanged"契约 | 恢复路径显式只发一次；测试同步确认 |
| 回滚 | 移除栈与 `_commit` 包装，五个入口回退为直接赋值；QML 三处快捷键/菜单项删掉 |

## 验收

1. 连续修改 3 个字段 → `Ctrl+Z` ×3 逐级回到初值；`Ctrl+Shift+Z` ×3 逐级回到末值；每步预览同步刷新。
2. 技能表增/删/改各一次 → 每次一步可撤销，撤销后技能行数与内容正确。
3. 修改头像 → 撤销 → 头像恢复显示，日志无新的网络下载（缓存命中）。
4. 制造一次校验失败（如生命值填非数字）→ 该次不产生撤销步；继续 `Ctrl+Z` 撤销的是上一个有效变更。
5. 打开另一份配置 → 菜单撤销项置灰（栈已清空）。
6. `uv run --no-sync pytest -q` 全绿。
