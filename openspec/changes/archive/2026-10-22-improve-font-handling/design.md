# Design

## Context

参见 `proposal.md` 与 `specs/font-handling/spec.md`。

现状约束（已核实）：

- `core/render/fonts.py::_FONT_PATHS` 只列 4 个绝对路径；找不到时 `chinese_font = None`，Skia 用默认字体，中文可能成方框。
- 卡片文本全部经 `canvas.drawString(...)` 使用同一个 `Typeface`（`core/render/text/wikitext_renderer.py`、`sections/*`、`primitives/radar.py`），没有按字符切换字体的入口；本轮不做逐字符回退。
- `utils/app/resources.py` 已处理开发态与 `sys._MEIPASS` 的资源根路径。
- `enemy_eval.spec` 的 `project_data` 已整体收集 `resource/`，新增字体无需改 spec。
- `gui/qml/Theme.qml` 只有单个 `fontFamily: "Microsoft YaHei UI"`，约 60 处 QML 使用。
- `scripts/build_release.py::_validate` 会检查产物中的必需文件，可扩展字体校验。

## Goals / Non-Goals

**Goals:**

- 卡片渲染始终使用随包 HarmonyOS Sans SC，跨机器输出一致。
- UI 有明确的字体回退栈，随包字体注册给 Qt，前三个系统族缺失时仍能显示中文。
- 删除硬编码字体路径；随包资源缺失时安全回退并告警。
- 打包产物与构建校验包含字体与许可证。

**Non-Goals:**

- 不做逐字符字体切换或文本 shaping。
- 不提供用户自定义字体、字体大小或字体族设置。
- 不做字体子集化；不改变卡片布局、字号或绘制顺序。
- 不把微软雅黑等 Windows 字体打进包（许可证不允许）。

## Decisions

### 1. 随包资产

- 字体：`resource/fonts/HarmonyOS_Sans_SC_Regular.ttf`，来源 `huawei-fonts/HarmonyOS-Sans` 的 `HarmonyOS Sans/HarmonyOS_Sans_SC/HarmonyOS_Sans_SC_Regular.ttf`（GitHub API 记录大小 8,261,128 字节，HarmonyOS Sans 字体许可）。
- 许可证：`resource/fonts/LICENSE.txt`，逐字保留 HarmonyOS Sans 字体许可文本；软件内需显著声明使用了该字体。
- 引入时记录下载 URL 与 SHA-256 到任务/提交说明；不新增 Python 依赖。
- `enemy_eval.spec` 已收集 `resource/`，无需修改；`scripts/build_release.py::_validate` 增加两个必需路径。

### 2. 卡片字体解析（`core/render/fonts.py`）

按顺序：

1. `resource_manager.get_resource_path("resource/fonts/HarmonyOS_Sans_SC_Regular.ttf")` → `skia.Typeface.MakeFromFile`；
2. 失败时用 `skia.FontMgr().matchFamilyStyle(name, skia.FontStyle.Normal())` 依次匹配：
   `Microsoft YaHei UI`、`Microsoft YaHei`、`SimHei`、`HarmonyOS Sans SC`、`Noto Sans CJK SC`、`Source Han Sans SC`；
3. 仍失败则 `None`，保留现有告警。

删除 `_FONT_PATHS`；保留进程内单例缓存 `_shared_chinese_typeface` 与 `FontManager` 的按字号模板缓存。卡片渲染不再读取系统字体（除非随包文件不可用）。

**备选**：优先系统雅黑、随包兜底。用户已确认要确定性，否决。

### 3. UI 字体回退栈

- `gui/qml/Theme.qml` 保留 `fontFamily: string`，改为按顺序从 `Qt.fontFamilies()` 中挑选第一个已安装的族：
  `Microsoft YaHei UI` → `Microsoft YaHei` → `Segoe UI` → `HarmonyOS Sans SC`；都不在时返回 `HarmonyOS Sans SC`。
- 各 QML 组件继续使用 `font.family: Design.Theme.fontFamily`，无需改动 60 处调用。
- `gui_main.py` 在 `QApplication` 创建后、`MainWindow` 之前调用 `QFontDatabase.addApplicationFont(resource/fonts/HarmonyOS_Sans_SC_Regular.ttf)`，使 `HarmonyOS Sans SC` 出现在 `Qt.fontFamilies()` 中；注册失败只记 warning，不阻止启动。

**备选**：QML 的 `font.families` 列表。当前 Qt 6.11 的 QML `font` 类型没有该属性（qmllint 报 `missing-property`），否决；逐组件改 Python 侧 `QFont.setFamilies` 又会被 QML 的 `font.family` 覆盖，同样不可行。

### 4. 输出确定性

卡片渲染永远走随包字体；系统字体只作为资源异常时的兜底。同一版本、同一数据在不同机器上的字形、测量与换行一致。现有布局测试因此可在无系统中文字体的环境运行。

### 5. 打包与校验

- `scripts/build_release.py::_validate` 的必需列表增加：
  - `_internal/resource/fonts/HarmonyOS_Sans_SC_Regular.ttf`
  - `_internal/resource/fonts/LICENSE.txt`
- 缺少任一项时构建失败，避免发布无字体包。

### 6. 失败语义

随包字体缺失时记录 warning 并回退系统族；系统族也没有时保持现有行为（默认字体 + 告警）。不抛异常、不阻断卡片生成。

## Risks / Trade-offs

- **包体增加 7.9 MB** → 相对 213 MB 解压体积可接受；zip 压缩后增量更小。
- **`Qt.fontFamilies()` 的族名匹配** → 选族依赖注册后的族名与系统族名完全一致；`HarmonyOS Sans SC` 注册失败时会退回硬编码名，需在启动日志中确认实际返回的字体族。
- **首帧枚举系统字体** → `Qt.fontFamilies()` 只在 `Theme` 单例首次求值时执行一次，开销可接受；不要在组件内重复调用。
- **Qt 字体注册时机** → 必须在创建 QML 引擎前完成；放在 `QApplication` 之后、`MainWindow` 之前。
- **字形观感变化** → 卡片从微软雅黑/黑体切换为 HarmonyOS Sans SC，字宽与换行可能变化；现有布局测试只断言相对关系，需人工对比一张卡片。
- **许可证合规** → 只随包 HarmonyOS Sans；保留 LICENSE 并在关于窗口显著声明；不要把 Windows 自带字体复制进仓库。
- **许可可撤销** → HarmonyOS Sans 许可允许随软件分发但可撤销；若后续要求永久许可，需换回 OFL 字体。

## Migration Plan

- 无数据迁移；旧配置直接使用新字体渲染。
- 回滚：删除字体资源并恢复 `fonts.py` 的旧路径列表即可；已生成图片不受影响。

## Open Questions

无。
