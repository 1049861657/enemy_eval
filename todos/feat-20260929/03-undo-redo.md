# 任务 03：撤销 / 重做

**优先级**：P1　**状态**：已实现，待用户本机验收　**依赖**：建议在任务 02 之后（偏好改动先收敛）

**影响文件**：新增 `gui/undo_stack.py`、`gui/qml/icons/undo.svg`、`gui/qml/icons/redo.svg`；改 `gui/card_model.py`、`gui/qml_bridge.py`、`gui/qml/Workspace.qml`、`gui/qml/CommandBar.qml`；同步 `tests/test_card_model_error_handling.py`、`tests/test_gui_signals.py`

## 目标

卡片上已提交的数据变更可撤销、可重做：标量字段、异常抗性、评价分数、技能表。快捷键符合 Windows 习惯。可见入口是「更多」右侧的图标胶囊。界面不显示具体改了哪个字段。

评价标准名称写在应用偏好里。保存标准后撤销栈清空，该步不可撤销。

## 现状与内部锚点

| 事实 | 锚点 |
|---|---|
| 每次变更整份重建 `EnemyData`（旧实例不被原地修改） | `gui/card_model.py:71`（`update_property`）、`:102`（`replace_skills`） |
| 直接替换模型的写入口两条；其余入口转入这两条 | `:71` `update_property`；`:102` `replace_skills`。`:89` `update_skill` → `replace_skills`；`:115` `update_abnormal_resistance`、`:121` `update_rating_score` → `update_property` |
| 评价标准：先写偏好，再对齐卡片分数 | `gui/qml_bridge.py:238` `updateRatingSchema` → `save_rating_schema`，然后 `realign_rating_scores_to_schema`（`gui/card_model.py:130`）。维度名称不在 `EnemyData` |
| 技能表的唯一写入口 | `gui/skill_list_model.py:93` `_commit` → `replace_skills`（`add`/`remove`/`updateField`） |
| 技能表在自身写入之外听 `dataChanged` 并整表刷新 | `gui/skill_list_model.py:57` `_on_card_changed`（`_mutating` 为真时跳过） |
| 校验失败分支：不改数据、只发 `validationFailed` | `gui/card_model.py` |
| 信号集 | `gui/card_model.py:24-28`（`dataChanged`/`snapshotChanged`/`validationFailed`/`ratingSchemaChanged`/`avatarPathChanged`） |
| `replace_skills` 只发 `dataChanged`，不发 `snapshotChanged` | `gui/card_model.py:102` |
| 确认框文案写着「无法撤销」 | `gui/qml/Workspace.qml:78-80` |
| 快捷键集中处 | `gui/qml/Workspace.qml:130-135` |
| 近战 / 不攻击会连续提交攻击方式与射程 | `gui/qml/Workspace.qml:45-48` `commitAttackType` |
| 新建 / 重置替换整个 `CardModel` | `gui/main_window.py:186` `_new_card` → `gui/qml_bridge.py:144` `set_card_model` |
| 换模型时成对断开 / 重连的位置 | `gui/qml_bridge.py:152` `_connect_card_model`、`:157` `_disconnect_card_model` |
| 「更多」菜单位置 | `gui/qml/CommandBar.qml:130` `commandMenu` |
| 既有契约：变更成功恰好一次 `dataChanged`；失败保留旧数据 | `tests/test_card_model_error_handling.py` |
| 桥接信号 / 槽契约 | `tests/test_gui_signals.py` |

## 外部调研与出处

- **`QUndoStack` 官方语义**（<https://doc.qt.io/qt-6/qundostack.html>）：
  - `push()` 无论是否合并，都会调用该命令的 `redo()` 来执行变更；
  - `setUndoLimit(int)` 限制栈深，超出后从栈底丢弃旧命令（宏算一条）；
  - 命令 `id()` 与栈顶相同且非 `-1` 时，栈调用 `mergeWith()`；返回 `true` 则新命令被删除；基类 `id()` 返回 `-1`；
  - 命令已撤销后又 `push` 新命令，被撤销的命令被删除；
  - `canUndo()` / `canRedo()` 是动作可用状态的标准接口。
- **`QUndoCommand`**（<https://doc.qt.io/qt-6/qundocommand.html>）：`redo()` / `undo()` 内再调用 `push()`、`undo()`、`redo()` 是未定义行为。命令对象由栈持有。
- **快照式命令**：官方框架不规定命令内容。本项目每次变更都整份重建模型，一条命令保存前后两份 `EnemyData` 即可覆盖全部卡片编辑。
- **界面**：本项目是 QML。`QUndoView` 是 Widgets 组件，不引入。胶囊只绑定 `canUndo` / `canRedo`。
- **合并与宏**：文本在失焦或回车时提交，星级是单次点击，粒度已是一步，不启用 `mergeWith`。一次用户动作若对应多字段，写成一份 `EnemyData` 再 `push` 一次；不用 `beginMacro()`。

## 设计

### 1. 栈与命令

`gui/undo_stack.py`：

```
class _StateCommand(QUndoCommand):
    def __init__(self, model: CardModel, previous: EnemyData, next_: EnemyData, refresh_snapshot: bool)
    def undo(self) -> None:  model.restore_state(self._previous, self._refresh_snapshot)
    def redo(self) -> None:  model.restore_state(self._next, self._refresh_snapshot)
```

- `QUndoStack` 由 `CardModel` 持有（`QUndoStack(self)`，`setUndoLimit(100)`），仅 GUI 线程访问。
- 构造时对 `previous`、`next_` 各 `model_copy(deep=True)`。
- 不调用 `setText`。`undoText()` / `redoText()` 留空，桥接不暴露。

### 2. `CardModel`

只有 `redo()` / `undo()` 替换 `_enemy_data` 并发信号。`_commit` 只 `push`：

```
def _commit(self, previous: EnemyData, next_: EnemyData, refresh_snapshot: bool) -> None
    self._undo_stack.push(_StateCommand(self, previous, next_, refresh_snapshot))

def restore_state(self, enemy: EnemyData, refresh_snapshot: bool) -> None
    previous_avatar = self._enemy_data.avatar_path or ""
    self._enemy_data = enemy
    self.dataChanged.emit()
    if refresh_snapshot: self.snapshotChanged.emit()
    if (enemy.avatar_path or "") != previous_avatar:
        self.avatarPathChanged.emit(enemy.avatar_path or "")
```

- `restore_state` 不调用 `push` / `undo` / `redo`。每次恢复恰好一次 `dataChanged`。
- `update_property`：校验通过后 `_commit(..., refresh_snapshot=True)`。校验失败只发 `validationFailed`，不入栈。
- `replace_skills`：校验通过后 `_commit(..., refresh_snapshot=False)`。技能编辑不刷新标量快照。
- `update_skill`、`update_abnormal_resistance`、`update_rating_score` 继续转入上述两条，自身不 `push`。
- 多字段一次提交：`update_properties(values)` 在同一份 `EnemyData` 上写入后只 `_commit` 一次。`commitAttackType` 在「近战」「不攻击」时一次提交 `attack_type` 与 `attack_range_radius`。
- `realign_rating_scores_to_schema` 不入栈，对齐并发原有信号后 `self._undo_stack.clear()`。
- `load_from_file`、`set_enemy_data` 在替换数据后 `clear()`。
- 新建 / 重置替换整个 `CardModel`，新栈为空。

### 3. 桥接与 UI

- `gui/qml_bridge.py`：
  - Property：`canUndo`、`canRedo`（`bool`），notify = `undoStateChanged`。
  - 槽：`requestUndo()`、`requestRedo()` 调用当前 `CardModel` 的栈。无额外请求信号。
  - `canUndoChanged` / `canRedoChanged` → `undoStateChanged` 写在 `_connect_card_model` / `_disconnect_card_model`。换模型后发一次 `undoStateChanged`。
- `gui/qml/Workspace.qml`：
  - `Ctrl+Z`、`Ctrl+Shift+Z`、`Ctrl+Y`。活动焦点是 `TextInput` 或 `TextEdit` 时三枚 `enabled: false`，按键留给输入控件。
  - `confirmNewCard` 去掉「且无法撤销」：重置为「当前编辑内容将被默认数据替换」，新建为「所有未保存的修改都将丢失」。
  - `commitAttackType` 一次提交攻击方式与射程。
- `gui/qml/CommandBar.qml`：「更多」右侧、弹性空白左侧，一枚历史步进胶囊。
  - 高 `controlHeight`，圆角 `radiusMedium`，底 `surfaceSubtle`、边 `border`，中间 1px 竖分割。左半撤销、右半重做，各自按 `canUndo` / `canRedo` 启用。无文字标签。
  - `undo.svg` / `redo.svg`：`viewBox 0 0 24 24`、描边 1.8、圆头。撤销为右侧实心点、弧向左收到箭头；重做镜像。可用色 `textPrimary`，不可用色 `disabledText`。悬停半边 `controlHover`，按下 `controlPressed`。
  - 无障碍名「撤销」「重做」。ToolTip（`delay: 600`）固定为「撤销　Ctrl+Z」「重做　Ctrl+Y」。

## 步骤

- [x] 新增 `gui/undo_stack.py`（`_StateCommand`；模块 docstring 写明状态式命令与「只由 redo/undo 写模型」）。
- [x] `gui/card_model.py`：栈、`_commit`、`restore_state`、`update_properties`；两条写入口入栈；`load_from_file`、`set_enemy_data`、`realign_rating_scores_to_schema` 清栈。
- [x] 桥接：两个 Property、两个槽、栈信号放进换模型连接对。
- [x] QML：三枚快捷键（文本焦点时关闭）、攻击方式一次提交、历史步进胶囊、确认框文案。
- [x] 同步契约测试：成功提交恰好一次 `dataChanged`；校验失败不入栈；近战/不攻击只入栈一步；`realign` 后栈空；`canUndo` / `canRedo`。

## 非目标

- 不做跨文件、跨会话的撤销历史。
- 不做变更历史面板。
- 撤销/重做不进「更多」菜单，命令栏不用文字按钮。
- 不为单条命令生成动作名，界面不绑定 `undoText` / `redoText`。
- 不启用 `mergeWith`，不用 `beginMacro()`。
- 评价标准的名称与分数对齐不入栈。
- 不把撤销与草稿 / 自动保存耦合。
- 不使用 `setClean()`（本应用无未保存标记）。

## 风险与回滚

| 风险 | 处置 |
|---|---|
| 撤销后预览不刷新 | `restore_state` 发 `dataChanged`，沿 `MainWindow._on_data_changed` 防抖渲染 |
| 撤销头像后不重新取图 | 头像路径变化时发 `avatarPathChanged`；命中缓存则不新起线程 |
| 技能撤销后列表不刷新 | `SkillListModel` 在 `_mutating` 为假时已听 `dataChanged` 整表刷新 |
| 历史被原地修改污染 | 入栈深拷贝 |
| 内存增长 | `setUndoLimit(100)` |
| 成功路径发出两次 `dataChanged` | `_commit` 不写模型、不发信号；仅 `redo` / `undo` 发一次 |
| 换卡片后按钮仍指旧栈 | 栈信号连接在 `_connect_card_model` / `_disconnect_card_model` |
| 评价标准变更后分数长度与名称错位 | `realign_rating_scores_to_schema` 末尾清栈 |
| 输入框与卡片栈同时响应 Ctrl+Z | 焦点在 `TextInput` / `TextEdit` 时卡片快捷键关闭 |
| 回滚 | 去掉栈与 `_commit`；两条写入口直接赋值；删掉胶囊、两个 svg、三枚快捷键 |

## 验收

1. 连续修改 3 个字段 → `Ctrl+Z` ×3 逐级回到初值；`Ctrl+Shift+Z` ×3 逐级回到末值；每步预览同步刷新。
2. 技能表增 / 删 / 改各一次 → 每次一步可撤销，撤销后技能行数与内容正确，标量字段不被重绑打断。
3. 切到「近战」或「不攻击」→ `Ctrl+Z` 一次同时恢复攻击方式与射程。
4. 修改头像 → 撤销 → 头像恢复显示，日志无新的网络下载（缓存命中）。
5. 生命值填非数字 → 该次不产生撤销步；继续 `Ctrl+Z` 撤销的是上一个有效变更。
6. 焦点在文本框内按 `Ctrl+Z` → 卡片数据不变；失焦提交后再按，撤销的是已提交内容。
7. 打开另一份配置、导入 PRTS、新建、重置、保存评价标准 → 撤销半边置灰。悬停仍是「撤销　Ctrl+Z」，无字段名。
8. `uv run --no-sync pytest -q` 全绿。
