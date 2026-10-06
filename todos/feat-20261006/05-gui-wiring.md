# 任务 05：GUI 接线与收口

## 目标

把 01–04 接成可用闭环：手动点击 → 后台请求 → 弹窗（两份原始数值并列 + 简评）→ 采纳 / 放弃 / 重新生成；采纳一步可撤销；任何失败都不改数据；打包产物可用。

## 现状与锚点

| 事实 | 位置 |
|---|---|
| 顶栏按钮写法（「参考 PRTS」同级） | `gui/qml/CommandBar.qml:197` |
| 线程范式：同步 `httpx.Client` + 信号回主线程 | `utils/thread_manager.py::UpdateCheckThread` |
| 可中断轮询范式 | `utils/thread_manager.py::PrtsFetchThread`（`requestInterruption` 轮询 + `task.cancel()`） |
| 过时结果丢弃范式（`revision` 不匹配即丢） | `gui/render_coordinator.py:131-139` |
| 多字段写入一步入栈（自带撤销） | `gui/card_model.py::update_properties` |
| 卡片标量快照（不含 `skills`） | `gui/qml_bridge.py::enemyData` |
| 错误文案分类 | `utils/error_handler.py::categorize_error_message` |
| 对话框挂载点 | `gui/qml/Workspace.qml:374,379,405` |
| 基准与调用层 | `utils/ai_baseline.py`（任务 02）、`utils/ai_client.py`（任务 03） |

## 结论

| 项 | 结论 |
|---|---|
| 线程 | `utils/thread_manager.py` 追加 `AiEvaluateThread`：入参 基准 `EnemyData` + 当前卡快照 + 三项配置 + `revision`；信号 `evaluationFinished(object, int)` / `evaluationFailed(str, int)` |
| 触发 | 桥接槽 `requestAiReview()`：`base_url` / `model` / 密钥任一为空 → 发 `aiSettingsRequested` 打开设置框并**不发网络请求**；否则递增 `_ai_revision` 并起线程 |
| 忙态 | `aiBusy` 属性 + 变更信号；请求中顶栏按钮禁用 |
| 弹窗 | `gui/qml/AiEvaluationDialog.qml`：上半为两份原始数值并列（13 个数值 + 5 个枚举，字段顺序固定，**不算差值、不做档位**），下半为简评与三个按钮 |
| 基准数值来源 | 桥接新增只读属性 `aiBaselineData`（白名单字段 dict，无 `avatar_path`）；当前卡侧复用既有 `enemyData` 快照 |
| 字段中文标签 | 沿用 `gui/qml/EditorCombatPage.qml:32-42` 的既有中文名（如 `max_hp` → 最大生命值、`attack_interval` → 攻击间隔），由桥接暴露同一份映射给对话框复用，**不在对话框里另写一份** |
| 采纳 | 桥接槽 `applyAiComment(text)` → `CardModel.update_properties({"brief_comment": text})`，一步入撤销栈；不额外写文件 |
| 放弃 | 只关弹窗，不触碰卡片数据 |
| 重新生成 | 同参数再请求一次，覆盖当前预览（同样递增 `revision`） |
| 过时结果 | 结果 `revision` 与当前不符（切卡 / 新建卡 / 关窗）→ 丢弃并记日志，不弹窗、不写入 |
| 关窗 | 只 `requestInterruption()` + `task.cancel()`，**绝不 `terminate`**；同步请求无法中断，最长 60 秒自行结束，结果按 `revision` 丢弃 |
| 错误文案 | `categorize_error_message` 增 AI 分支：未配置（引导去设置）、网络不可达、响应非法（含重试后仍非法）、服务端拒绝（含状态码） |
| 冒烟 | 按验收总纲 6 条逐条手动实测；打包后重跑第 6 条 |

## 步骤

- [ ] `AiEvaluateThread`（同步调用 `ai_client.evaluate`，信号带 `revision`）
- [ ] 桥接：`aiReviewRequested` / `aiSettingsRequested` / `aiBusy(Changed)` / `_ai_revision` / `requestAiReview()` / `applyAiComment()` / `aiBaselineData`
- [ ] `AiEvaluationDialog.qml`（数值并列表 + 简评 + 采纳 / 放弃 / 重新生成）
- [ ] `Workspace.qml` 挂载对话框并接两个 `Requested` 信号
- [ ] `CommandBar.qml` 顶栏加「AI 评价」按钮（与「参考 PRTS」并列，忙态禁用）
- [ ] `categorize_error_message` 增加 AI 分支
- [ ] 手动实测验收总纲第 1–5 条
- [ ] `pyinstaller --noconfirm --clean enemyEval.spec` 后实测第 6 条

## 非目标

- 不做快捷键、不做右键菜单入口、不导出评价到文件、不做批量评价、不做结果缓存、不把评价写进配置文件的别的字段。

## 风险与回滚

- 风险：请求进行中切卡导致结果串到另一张卡 → `revision` 丢弃。
- 风险：请求中关窗残留线程 → 不 `terminate`；同步请求最长 60 秒自然结束。
- 风险：弹窗并列数值与简评不同屏导致核对失效（这是验收第 3 条的落点）→ 同一对话框内呈现。
- 回滚：删线程、弹窗与桥接改动，撤按钮与错误分支。

## 验收

按 `00-overview.md` 的验收总纲 6 条逐条实测，第 6 条在打包产物内验证。
