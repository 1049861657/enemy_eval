# 任务 02：最近打开列表

**优先级**：P1　**状态**：未开始　**依赖**：任务 01（同为配置读写边界；建议在 01 之后提交）

**影响文件**：`utils/app_settings_store.py`、`gui/main_window.py`、`gui/qml_bridge.py`、`gui/qml/CommandBar.qml`

## 目标

记住最近打开/保存过的配置文件，菜单内一键回到；失效项可见且可清理；不改变启动行为。

## 现状与内部锚点

| 事实 | 锚点 |
|---|---|
| 偏好模型只有两个字段，无任何工作上下文 | `utils/app_settings_store.py::AppSettings`（`:61`，字段 `:66-67`） |
| 偏好落盘/读取已有容错实现（缺失或损坏按默认值） | 同文件 `_read_settings:95`、`_persist:109`、`_TolerantJsonConfigSettingsSource:38` |
| 打开只走文件对话框 | `gui/main_window.py:180-184` |
| 保存对话框与落盘 | `gui/main_window.py:195-209` |
| 桥接层暴露给小数组的既有约定（JSON 字符串 + notify 信号） | `gui/qml_bridge.py:54-70`（信号）、`:74-121`（Property） |
| 命令栏菜单结构与快捷键集中处 | `gui/qml/CommandBar.qml:40-56`、`gui/qml/Workspace.qml:100-105` |
| 偏好字段变更会触碰的测试契约 | `tests/test_rating_schema.py`（偏好 roundtrip + 损坏回退）、`tests/conftest.py:20-26`（偏好文件夹具） |

## 外部调研与出处

- **偏好存储位置（官方事实）**：Qt 的 `QSettings` 在 Windows 落到注册表、在其它平台落到 ini/plist 位置——本项目的偏好因此改用 `platformdirs` + JSON，本任务沿用既有路径，不引入 QSettings。
  <https://doc.qt.io/qt-6/qsettings.html>
- **路径规范化（官方事实）**：Windows 文件系统不区分大小写，比较路径前应 `os.path.normcase`，否则同一文件会以两种大小写并存。
  <https://docs.python.org/3/library/os.path.html#os.path.normcase>
- **MRU 条目上限（工程判断）**：未检索到权威规范（Qt 无内建 recent-files 组件；Windows JumpList 的语义与本工具无关，且引入跳转列表会带来 COM/安装依赖）。取 **8 条**：足够覆盖同时在编的敌人数量，菜单子项不需要滚动。
- **失效项处理（工程判断）**：置灰保留 + 提供显式清理，优于静默剔除——用户能看见"文件被删/被移走"这一事实，而不是疑惑记录消失。

## 设计

### 1. 数据结构

`AppSettings` 新增：

```python
recent_files: list[str] = Field(default_factory=list, max_length=8)
```

- 存**绝对路径**（最近文件是机器本地概念，不需要可搬动性；与任务 01 的"配置内头像路径"目的不同）。
- 越界（`>8`）在写入侧截断，不在模型侧报错。

### 2. 归一定义（唯一实现点）

`utils/app_settings_store.py` 新增：

```
remember_recent_file(path: str) -> None      # 记录（打开成功后 / 保存成功后调用）
prune_recent_files() -> None                 # 清理不存在的条目
recent_files() -> list[str]                  # 读取（拷贝）
```

规则：

- 归一：`os.path.normcase(os.path.abspath(path))` 用于去重比较；**存储保留原始大小写形式**（用户看起来自然）。
- 命中已有条目 → 提到最前（不新增）。
- 截断到 8。
- 失效判定：`Path(p).exists()` 为假 → 读取侧标记为不可用（**不在读取时自动删**）。
- 任何写盘失败沿用既有语义：`FileOperationError` 由调用方决定是提示还是忽略（最近文件写失败**只记日志**，不打断用户动作）。

### 3. 桥接与 UI

- `gui/qml_bridge.py`：
  - `recentFilesJson` Property（`list[dict]` 序列化：`{"path": str, "name": str, "exists": bool}`），notify 信号 `recentFilesChanged`；
  - `@Slot(str) requestOpenRecent(path)` + 信号 `openRecentRequested(str)`；
  - `@Slot() requestPruneRecent()` + 信号 `pruneRecentRequested()`。
- `gui/main_window.py`：
  - `_open_file(path: str | None = None)`：无参走对话框，带参直接打开；两条路径共用同一装载函数（任务 01 的解析也在其中），成功后才 `remember_recent_file`；
  - `_save_config` 成功后 `remember_recent_file(最终保存路径)`；
  - `_on_prune_recent` → `prune_recent_files()` + 刷新桥接属性。
- `gui/qml/CommandBar.qml`：`更多` 菜单内加 `Menu { title: "最近打开" }`：
  - 动态项用 **`Instantiator`**（`Menu` 内 `Repeater` 行为不保证）；
  - 项文案：`name`（悬停显示完整路径）；`exists === false` → `enabled: false` + tooltip「文件不存在」；
  - 菜单尾部固定项「清理失效项」（列表为空或全部有效时可禁用）。

## 步骤

- [ ] `AppSettings` 加 `recent_files` 字段（默认空列表，`max_length=8`）。
- [ ] `utils/app_settings_store.py` 实现 `remember_recent_file` / `prune_recent_files` / `recent_files`。
- [ ] `gui/main_window.py`：`_open_file` 支持带参、打开/保存成功后记录、接清理动作。
- [ ] `gui/qml_bridge.py`：新增 Property + 两个槽 + 对应信号，并在 `__init__` 完成连接。
- [ ] `gui/qml/CommandBar.qml`：加「最近打开」子菜单（`Instantiator`）与「清理失效项」。
- [ ] 同步 `tests/test_rating_schema.py` 的偏好 roundtrip 契约（新字段的读写与缺省）；夹具 `tests/conftest.py` 已按临时目录隔离偏好，无需新增夹具。

## 非目标

- 不做"启动自动打开上次文件"（改变启动行为，需单独授权）。
- 不做每个文件的编辑位置（光标/滚动/缩放）记忆。
- 不写进敌人配置（属应用偏好）。
- 不引入 Windows JumpList / 最近文档系统集成。
- 不做菜单内搜索过滤（敌人配置数量级不需要）。

## 风险与回滚

| 风险 | 处置 |
|---|---|
| 路径大小写不同导致重复项 | 统一用 `normcase(abspath())` 比较 |
| 网络盘/移动盘上的配置消失 | 置灰 + 可清理，不阻塞 |
| 偏好文件写入失败 | 只记日志，不影响打开/保存主流程 |
| 回滚 | 移除字段与三处调用即可；旧偏好文件含未知字段时按默认值读取（容错源已覆盖） |

## 验收

1. 依次打开 3 个配置 → 菜单「最近打开」按最近倒序显示 3 项，当前项在最前。
2. 删除其中一个文件 → 该项置灰且 tooltip 提示；「清理失效项」点击后该项消失。
3. 重启应用 → 列表仍在（已持久化）。
4. 通过「最近打开」打开配置后直接保存 → 该项被提到最前且不重复。
5. `uv run --no-sync pytest -q` 全绿。
