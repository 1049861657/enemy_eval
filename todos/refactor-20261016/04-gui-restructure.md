# 04 GUI 桥接层与 QML 组织

**优先级** P1　**依赖** 批次 1–3　**回滚** 4.1 / 4.2 / 4.3 各自一个 commit

## 目标

`gui/qml_bridge.py`（657 行）从"声明 + 实现混在一起"改为"薄声明 + 分域实现"；QML 从平铺 28 文件改为按角色分目录；超长 QML 组件拆分。

## 4.1 桥接层：声明与实现分离

**现状锚点**

| 事实 | 数值/位置 |
|---|---|
| `gui/qml_bridge.py` | 657 行；36 个 `Signal(`；26 个 `@Property`；36 个 `@Slot`；86 个 `def` |
| QML 侧实际调用的桥接名 | **62 个**（`grep -o "controller\.[a-zA-Z]*" gui/qml/*.qml \| sort -u`） |
| QML 调用密度 | `Workspace.qml` 28 处、`CommandBar.qml` 16、`AiEvaluationDialog.qml` 15、`AiSettingsDialog.qml` 12、`AboutDialog.qml` 10 |
| 桥接成员只被 QML 按名调用 | 静态检索看不到调用点（本次审计确认：`QmlBridge` 的多数 slot/property 在 `.py` 内零引用） |

**设计结论**

- **D8 冻结契约**（本批不改）：所有 QML 可见名字（属性名、信号名、slot 名）、`image://enemy-card/current?revision=` 的 provider id 与查询参数、`qmldir` 的模块名 `EnemyEval` 与已注册三项（`Theme`、`AppFocusFrame`、`AppTabButton`）。
- 新增 `gui/bridge/` 目录，按域放**纯 Python 实现**（可测、可读，不依赖 Qt 元对象）：`app.py`（身份/版本/更新）、`files.py`（新建/打开/最近/保存/导出）、`editor.py`（字段与评价维度读写）、`prts.py`（查询与级别切换）、`ai.py`（设置、人设、请求预览、生成与采纳）、`preview.py`（预览图交付）。
- `gui/qml_bridge.py` 只保留：信号与属性声明、`@Slot` 声明、以及一行转发（`return self._impl_xxx.do(...)`）。目标总量 **< 250 行**。
- 桥接对象**保持单一 QObject**：QML 侧零改动。理由：信号必须声明在 QObject 子类上，PySide6 不支持从非 QObject mixin 继承元对象；把域拆成多个 QObject 会改变 QML 调用路径（`controller.ai.xxx`），属破坏 D8，仅作为 4.4 的可选项评估。
- `CardImageProvider`（`gui/qml_bridge.py:56-76`）随 `preview.py` 一并归位；它同时是批次 6 的性能改动点（每次 `requestImage` 都整幅 `copy()`）。

**步骤**
- [ ] 先把 62 个 QML 可见名落成清单（写入本文件附录），作为"改后必须逐一仍存在"的对照表。
- [ ] 按域抽出实现模块（纯函数/小服务类，参数显式传入，不读全局）。
- [ ] `qml_bridge.py` 逐域瘦身，保持声明顺序与分组注释不变（QML 侧无感知）。
- [ ] 每完成一个域，跑一次 QML 装载冒烟 + 该域的手工路径（打开文件 / 导出 / PRTS 查询 / AI 设置 / AI 生成）。
- [ ] 验收：`wc -l gui/*.py gui/bridge/*.py`；62 个名字逐一 `grep` 命中。

## 4.2 QML 目录分层（P1，可单独评估后跳过）

**现状锚点**：`gui/qml/` 平铺 28 个 `.qml` + `icons/`（15 个 svg）+ `qmldir`（module `EnemyEval`，注册 3 项）。根场景由 `QQuickWidget.setSource(.../qml/Workspace.qml)` 直接加载（`gui/main_window.py:111-112`），其余组件靠**同目录隐式可见**解析。

**目标**

```text
gui/qml/
├── Workspace.qml            # 根场景（保持同目录，加载路径不变）
├── qmldir                   # 保持模块名与注册项
├── Theme.qml                # 保持（singleton 被 qmldir 注册）
├── components/              # App* 通用组件（AppButton/AppTextField/AppComboBox/...）
├── pages/                   # Editor*Page.qml + CommandBar.qml + PreviewViewport.qml + RatingDisplaySwitch.qml + RatingStars.qml + AppSection.qml?
├── dialogs/                 # AiEvaluationDialog/AiSettingsDialog/PrtsQueryDialog/DetailedTextDialog/AboutDialog/AppMessageDialog
└── icons/
```

**成本（必须写进本批说明）**
- 子目录文件之间不再隐式可见：每个跨目录引用要么在文件头加 `import "../components"`，要么在 `main_window.py` 加载前 `engine.addImportPath(...)`（现用 `QQuickWidget`，需确认 `QQuickWidget.engine().addImportPath` 可用）。
- `qmldir` 若随组件挪动，模块路径与 `singleton Theme` 注册必须同步；静态检查命令需扩展为 `pyside6-qmllint -I gui/qml -I gui/qml/components ...`。
- 该批**必须**有 offscreen 逐页装载冒烟兜底（QML 解析失败只在运行时暴露）。

**步骤**
- [ ] 先做可行性探针：临时把 1 个组件移到子目录，确认 `import "../components"` 与 `qmllint` 都能工作，再决定是否全量。
- [ ] 全量搬迁 + 补 `import`；`rooot`/相对路径引用（`icons/*.svg` 用 `src` 拼接处）逐一核对。
- [ ] 冒烟：逐页面 `Loader` 装载 + 主窗口截图对比（外观零变化）。

## 4.3 `AiEvaluationDialog.qml` 拆分（683 行，最大 QML）

**现状**：单文件容纳 人设编辑、只读输出契约、请求预览、生成中/结果/失败三态、采纳与撤销提示。**目标**：拆为 `AiPersonaPanel.qml`、`AiContractPanel.qml`、`AiRequestPreview.qml` + 结果区，父级只做状态与信号编排。

**约束**：对外信号/属性名不变（`controller.*` 契约与父级 `Workspace.qml` 的调用方式不变）；纯视图拆分，不改交互。

**步骤**
- [ ] 抽出三段子组件，状态用属性/别名在父级持有（避免子组件各自读 controller）。
- [ ] 冒烟：打开对话框、切三页、生成成功/失败、采纳、撤销。

## 4.4 可选（默认不做）

把 AI / 更新 / PRTS 三域做成 QML 可访问的子对象（`controller.ai.*`）：能显著减小单文件声明量，但需改 QML 调用名（破 D8），且要逐个回归 62 个名字的调用点。**仅在 4.1 完成后仍判断桥接层是瓶颈时才做**，并单独一个批次。

## 非目标

- 不改 QML 视觉（颜色、间距、字号、动画时长、文案）。
- 不改 QML 与 Python 的名字契约（除 4.4 被明确批准时）。
- 不改 `QQuickWidget` 的加载方式为 `QQmlApplicationEngine`（那是启动路径变更，另立项）。
- 不重命名 `gui/constants.py` 的 6 个常量以外的内容；该文件仅被 `gui/main_window.py:52` 引用，若判定"单一消费者"，可内联进 `main_window.py` 并在本批说明（二选一，禁止同时保留两处）。

## 风险

| 风险 | 缓解 |
|---|---|
| QML 装载失败只在运行时暴露 | offscreen 逐页装载冒烟 + 手工点击路径 |
| 桥接瘦身时漏声明某个 slot（QML 调用报 `TypeError`） | 62 个名字对照表逐一 `grep` + 冒烟 |
| 子目录 QML 的 `import` 路径写错 | 先做 1 个组件的可行性探针 |

## 验收

1. `gui/qml_bridge.py` < 250 行；`gui/bridge/` 每文件 < 200 行。
2. 62 个 QML 可见名一个不少（对照表逐项勾选）。
3. `pyside6-qmllint -I ...` 对改动文件**不新增诊断**（基线：exit 0，5 Warning + 5 Info，全部位于 `gui/qml/RatingDisplaySwitch.qml`，属既有问题）。
4. offscreen 冒烟：主窗口 + 全部对话框 + 每个编辑页装载成功；手工冒烟路径（打开/保存/导出/PRTS/AI 五条）全通过。

## 附录：QML 可见名清单（执行时以实测重算，需逐项核对）

（执行时回填：`grep -o "controller\.[a-zA-Z]*" gui/qml/*.qml | sed 's/.*controller\.//' | sort -u` 的输出，62 项）
