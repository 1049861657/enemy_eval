# 任务 02：最近打开列表

**优先级**：P1　**状态**：已实现，待用户本机验收　**依赖**：任务 01（已提交）

**影响文件**：`utils/app_settings_store.py`、`gui/main_window.py`、`gui/qml_bridge.py`、`gui/qml/AppButton.qml`、新增 `gui/qml/icons/chevron_down.svg`、新增 `gui/qml/AppMenu.qml`、`gui/qml/CommandBar.qml`、`gui/qml/Workspace.qml`、`tests/test_rating_schema.py`

## 目标

记住最近打开/保存过的配置文件，「打开」下拉内一键回到；失效项可见且可清理；不改变启动行为。

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
recent_files: list[str] = Field(default_factory=list)
```

- 存**绝对路径**（最近文件是机器本地概念，不需要可搬动性；与任务 01 的"配置内头像路径"目的不同）。
- 上限 `_MAX_RECENT_FILES = 8` 只在写入侧截断。**模型侧不设 `max_length`**：校验失败会让 `_read_settings` 回退整份默认偏好（连评价维度一起丢），代价大于收益。

### 2. 归一定义（唯一实现点）

`utils/app_settings_store.py` 新增：

```
remember_recent_file(path: str) -> None      # 记录（打开成功后 / 保存成功后调用）
remove_recent_file(path: str) -> None        # 移除单项（列表项右侧删除图标）
clear_recent_files() -> None                 # 清空（菜单尾部「清除最近记录」）
recent_files() -> list[str]                   # 读取（拷贝）
_with_recent_files(current, entries)          # 私有：构造替换后的偏好
_replace_recent_files(current, entries)       # 私有：落盘 + 更新缓存（失败只记日志）
```

规则：

- 归一：`os.path.normcase(os.path.abspath(path))` 用于去重比较；**存储保留 `abspath` 后的原始大小写形式**（用户看起来自然）。
- 命中已有条目 → 提到最前（不新增）。
- 截断到 8（写入侧唯一强制点）。
- 失效判定：`Path(p).is_file()` 为假 → 界面标记为不可用（**不在读取时自动删**；目录不算可用配置）。
- 写盘失败**只记日志并保留原内存状态**，不打断用户动作：最近列表的失败不该回滚或中断打开/保存流程。

### 3. 桥接与 UI

- `gui/qml_bridge.py`：
  - `recentFilesJson` Property（`list[dict]` 序列化：`{"path": str, "name": str, "exists": bool}`，`exists` 取 `Path.is_file()`），notify 信号 `recentFilesChanged`；
  - `@Slot(str) requestOpenRecent(path)` / `@Slot(str) requestRemoveRecent(path)` / `@Slot() requestClearRecent()` + 对应信号；另有 `removeRecentConfirmRequested(path, name)` 与 `confirm_remove_recent(path)`，供主窗口在"文件已不存在"时请求界面弹确认框；
  - `refresh_recent_files()`：主窗口在列表变化后通知界面重读。
- `gui/main_window.py`：
  - `_open_file(path: str | None = None)`：无参走文件对话框，带参直接打开（最近列表走这条）；两条路径共用同一装载逻辑，**成功后才** `remember_recent_file`；**带参打开失败且文件已不存在时改发确认移除信号**（竞态：列表里显示存在、点击时文件已被删），不弹报错，其它失败仍走 `categorize_error_message` + 对话框；
  - `_save_config` 成功后 `remember_recent_file(最终保存路径)`；
  - `_remove_recent(path)` / `_clear_recent()` → 对应存储函数 + 刷新桥接属性；
  - 三个新信号在 `_connect_signals` 中连接（`openRecentRequested` 直接接 `_open_file`）。
- `gui/qml/AppButton.qml`：新增 `dropdown` 开关（默认 `false`，既有调用点尺寸与配色不变）与 `dropdownClicked` 信号；开启后按钮右侧出现 **chevron 区**——一个嵌套 `ToolButton`（宽 `controlHeight * 0.8`、右圆角、自带 hover/pressed 底色与焦点框），并新增 `mainHovered` / `mainDown` 让主区排除它。**必须是嵌套控件**，写在 `background` / `contentItem` 里的 `MouseArea` / `TapHandler` 拿不到点击（实测见下）。分隔线 accent 底用 35% 白，其它外观用 `Theme.border`；chevron 用新增资源 `icons/chevron_down.svg`（与既有图标同为白色描边）。
- `gui/qml/AppMenu.qml`（新增，**只承载一条修正与一个动作**）：`closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent` + `toggle()`。它不是"为了复用 Menu 内容"，而是把"点 opener 自身不得被弹窗抢先关闭"这条非显然修正收在单点——同一轮里只修「打开」漏了「更多」就是这条被重复实现掉的证据。
- `gui/qml/CommandBar.qml`：「打开」改为**分裂按钮**——主区仍弹文件对话框，chevron 区展开最近菜单：
  - 动态项用 `Instantiator`（`Menu` 内 `Repeater` 不产出菜单项，实测见下），`onObjectAdded`/`onObjectRemoved` 接 `insertItem`/`removeItem`；
  - 项用控件自带槽位：`text` 放文件名（悬停 `ToolTip` 显示完整路径），失效项用 `icon.source: icons/ban.svg`（`icon.width/height: 14`）+ `palette.text: Theme.warning` 凸显（文字与禁止图标同为琥珀色）；**不用 `enabled: false`**（会连删除图标一起禁掉）。点失效项**不弹报错**，改为弹移除确认框（`AppMessageDialog`，标题即该记录的文件名，`tone: "question"` + 取消/移除），确认后移除该记录；
  - 每项右侧一个删除 `ToolButton`（`icon.source: icons/delete.svg` + `display: IconOnly`，`icon.width/height: 16`，用 `rightPadding` 给它留位）：**所有项一律只在悬停时 `opacity: 1`**，不因失效常驻（避免列表里出现常显的红色垃圾桶）；**四边 padding 必须逐个写 0**（`padding: 0` 盖不住 Fluent 样式的状态绑定，见实测记录）；
  - 菜单弹层（`gui/qml/AppMenu.qml`）覆盖样式自带的入场动画：Fluent 的 `Menu` 用 `height: __heightScale * implicitHeight` + 250ms 高度动画，每帧重新布局并重切九宫格背景，观感发卡；改为 `OpacityAnimator` 0→1 / 90ms（与 `AppComboBox` 弹层同档），不动几何、在渲染线程执行；不加退场动画（关闭即已选中）；
  - 菜单 `closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent`，chevron 再点即关；删除项 / 「清除最近记录」后显式关闭，列表变空后自动关闭；
  - 菜单尾部：`MenuSeparator` + 「清除最近记录」（清空整个列表）；
  - 列表为空时 `dropdown: false`：箭头不出现，既不弹空菜单，也就没有隐藏占位项（隐藏项仍占位，实测见下）。
- `gui/qml/Workspace.qml`：`recentFiles` 属性 + `refreshRecentFiles`，在 `Component.onCompleted` 与 `Connections` 中接线。

**实现期修正（相对初稿的取舍）**

- 失效项**不依赖 tooltip** 说明原因：Qt 里 `enabled: false` 的 `MenuItem` 收不到 hover，tooltip 永不显示，因此"文件已不存在"写进文案本身。
- 菜单项 tooltip 在 `Menu` 弹窗内是否被裁剪，属真机验收项（全项目仅此一处 `ToolTip`）。
- 入口从「更多」子菜单改为「打开」分裂按钮（用户 2026-09-29 选定）：一次点击、语义紧邻；代价是共享组件 `AppButton` 增加一条分支。

**实测记录（offscreen Qt 探针，2026-09-29）**

- 分裂按钮的 chevron 区**必须是独立子控件**（`ToolButton`）。写进 `background` / `contentItem` 的 `MouseArea`、`TapHandler`、`PointHandler` 都拿不到点击（探针：三种写法的 chevron 命中文档均为 `[]`，按下被控件自身的按下处理吃掉），后果是点击落到主区——弹出的是文件对话框，看起来"点了没反应/还是原来那个"。改用嵌套 `ToolButton` 后：chevron 命中 `chevron`、主区命中 `main`，互不串。
- 菜单动态项用 `Instantiator` + `required property var modelData`（配合 `pragma ComponentBehavior: Bound`）实测可用；`Repeater` 放进 `Menu` 虽然让 `count` 变大，但不产出菜单项（实测 `items=[]`）。模型必须是 JS 数组——本项目链路是 JSON 字符串 → `JSON.parse`；若把 Python 的 `QVariantList` 直接交给 `Instantiator`，会被当成单个对象（只建 1 项且 `modelData` 为 `undefined`）。
- 已验证行为：点主区只调 `requestOpen` 且不弹菜单；点 chevron 只弹菜单、不调 `requestOpen`；有效项点文字区调 `requestOpenRecent`；点项内删除图标调 `requestRemoveRecent` 且不误触发条目；「清除最近记录」调 `requestClearRecent`；列表为空时按钮 `dropdown=False`（宽 66 → 95）。失效项点文字区**曾**只弹警告提示，本轮改为弹移除确认框（待验收）。
- **刷新必须把 JSON 一并推给界面**：`recentFilesChanged` 若声明成无参 `Signal()`，QML 的 `onRecentFilesChanged(serialized)` 会拿到 `undefined` → `JSON.parse` 抛错 → 列表永不刷新。表现是"删除 / 清空点了没反应"（其实写盘已成功）。实测：修前种子 2 条后 QML 仍是空列表（`dropdown=False`），修后 `count=4`、顺序正确、删除后 `count=3`、清空后 `dropdown=False`。
- **删除图标小到看不见 —— 根因在 Fluent 样式的 padding 绑定**：`FluentWinUI3/ToolButton.qml` 用状态绑定设 `leftPadding/rightPadding/topPadding/bottomPadding: __config.*Padding`（config 值 11/11/8/8），**`padding: 0` 这种组赋值盖不住它们**，于是 24×24 的按钮只剩约 2px 给图标。实测墨迹随尺寸线性增长（24→2×2、26→2×4、28→4×4、30→6×6、32→8×8），与 padding 是否写 0（组赋值）、icon 写 16 还是 24 都无关。改为**逐个写 `leftPadding/rightPadding/topPadding/bottomPadding: 0`**（真正解除样式绑定）后，24×24 + `icon 20` → 墨迹 16×16 ✓。图标本身走 `ToolButton.icon.* + display: IconOnly`（不自绘 `contentItem`）。
- **探针必须设对样式**：`gui_main.py` 用的是 `QQuickStyle.setStyle("FluentWinUI3")`，探针若不带这一行测到的是 Basic 样式，结论会完全错（本任务第一轮就是这么误判的）。
- 菜单开关与"点击后关闭"（同一轮实测）：`更多` 连点三次 → `visible=True/False/True`；点菜单项 → 该项 `triggered` 后 `visible=False`；真实窗口里点失效项、点删除按钮 → 均 `visible=False`。三者都由 `AppMenu` 的策略与显式 `close()` 保证。
- **「再次点 chevron 应关闭而不是重复打开」—— 根因在 `Menu` 的默认关闭策略**：默认含 `CloseOnPressOutside`，按下 chevron 时弹窗**先**关闭、**然后**才把点击交给按钮，于是 `visible ? close() : open()` 读到"已关"又 `open()`。实测时序 `menu.visible=false → chevron:visible=false → menu.visible=true`。改为 `closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent`（点 opener 自身不算"外部"）后时序变为 `chevron:visible=true → menu.visible=false` ✓。**该策略对「更多」同样必需**，故下沉到 `AppMenu`。
- 删除项与「清除最近记录」后显式 `recentMenu.close()`；列表变空时由 `Connections` 监听 `recentFiles` 关闭菜单（同时 `dropdown: false` 让箭头消失），不再留下孤零零的清除项。
- **`visible: false` 的 `MenuItem` 仍占位**（实测 `y=39 h=30`，菜单高 111 vs 无隐藏项 79）——这是"清除项上方不明空白"的成因，故改为列表为空时直接不显示箭头。
- **`enabled: false` 会屏蔽子控件事件**：禁用条目里的删除按钮点不到（实测 `[]`），因此失效项用图标 + 禁用色表达，而不是 `enabled: false`。
- 项内嵌套 `ToolButton` 只触发自己、不会连带触发条目（实测只报 `nested-click`，无 `item-triggered`）。
- 未验证：两半的悬停高亮、删除图标的悬停淡入（`opacity` 逻辑已静态核对，但 offscreen 平台不投递 hover 事件，须真机确认）。

## 步骤

- [x] `AppSettings` 加 `recent_files` 字段（默认空列表；不设 `max_length`，上限只在写入侧截断）。
- [x] `utils/app_settings_store.py` 实现 `remember_recent_file` / `remove_recent_file` / `clear_recent_files` / `recent_files`（共用私有 `_with_recent_files` 构造与 `_replace_recent_files` 落盘）。
- [x] `gui/main_window.py`：`_open_file` 支持带参、打开/保存成功后记录、接清理动作。
- [x] `gui/qml_bridge.py`：新增 Property + 三个槽 + 对应信号，信号在主窗口 `_connect_signals` 中连接。
- [x] `gui/qml/AppButton.qml`：加 `dropdown` 分裂按钮支持；新增 `gui/qml/icons/chevron_down.svg`。
- [x] `gui/qml/CommandBar.qml`：「打开」分裂 + 最近菜单（`Instantiator`、自绘项内容、每项删除图标、「清除最近记录」）。
- [x] `gui/qml/Workspace.qml`：`recentFiles` 属性 + `refreshRecentFiles`，`Component.onCompleted` 与 `Connections` 接线。
- [x] 同步 `tests/test_rating_schema.py` 的偏好 roundtrip 契约（新字段的读写与缺省）；夹具 `tests/conftest.py` 已按临时目录隔离偏好，无需新增夹具。

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
| 偏好文件写入失败 | 只记日志，不影响打开/保存主流程，也不改内存态 |
| 分裂按钮波及共享组件 | `dropdown` 默认 `false`，未开启的调用点尺寸、配色、hover 全走原分支 |
| 菜单内 `ToolTip` 被弹窗裁剪 | 真机确认；被裁则退化为"文件名 + 父目录名"两段文案 |
| 手改偏好文件写入 >8 条 | 模型侧不报错（避免整份偏好回退默认值），下次写入时截断 |
| 回滚 | 移除字段与三处调用即可；旧偏好文件含未知字段时按默认值读取（容错源已覆盖） |

## 验收

1. 依次打开 3 个配置 → 点「打开」的 chevron，列表按最近倒序显示 3 项，当前项在最前。
2. 删除其中一个文件 → 该项左侧出现禁止图标、文字变琥珀色（凸显）；点该项**弹移除确认框**（不打开、不报错），确认后该记录消失、取消则保留。
3. 悬停任意一项（含失效项）→ 右侧才出现删除图标（约 16px 垃圾桶），点它该项立即消失且菜单关闭（不打开文件）；不悬停时列表里没有任何常显的删除图标。
4. 「清除最近记录」→ 整个列表清空、菜单关闭，chevron 随后消失；逐项删完后同样不再留下清除项。
5. 再点一次 chevron → 菜单关闭（不是重复打开）；「更多」同样：点一次开、再点关。
6. 点任一最近项（含失效项）后菜单关闭。
7. 重启应用 → 列表仍在（已持久化）。
8. 通过 chevron 列表打开配置后直接保存 → 该项被提到最前且不重复。
9. `uv run --no-sync pytest -q` 全绿。
10. 「打开」主区仍是文件对话框；chevron 区单开列表；两半的悬停只点亮被悬停的一半。
11. 菜单里「清除最近记录」上方没有多余空白（隐藏占位项会占位，已改为列表为空时不显示箭头）。
12. 菜单项悬停可见完整路径；无记录时「打开」不显示箭头。
