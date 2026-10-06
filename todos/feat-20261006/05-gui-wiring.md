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
| 当前卡权威数据（含 `skills`） | `gui/card_model.py::CardModel.enemy_data` |
| 错误文案分类（按 4 个 AI 异常子类分支） | `utils/error_handler.py::categorize_error_message` |
| 对话框挂载点 | `gui/qml/Workspace.qml:374,379,405` |
| 基准与调用层 | `utils/ai_baseline.py`（任务 02）、`utils/ai_client.py`（任务 03） |

## 结论

| 项 | 结论 |
|---|---|
| 线程 | `utils/thread_manager.py` 追加 `AiEvaluateThread`：入参 基准 dict（`load_baseline()`，任务 02）+ 当前卡快照 + `AiRequestConfig`（任务 01）+ `revision`；信号 `evaluationFinished(object, int)` / `evaluationFailed(object, int)`（**传异常对象**，分类留给桥接） |
| 快照 | 起线程前 `card_model.enemy_data.model_copy(deep=True)`；线程只读写自己那份，桥接不读线程内部状态 |
| 配置/密钥取值 | 桥接放行线程前取一次 `ai_request_config()`：为 `None` → 发 `aiSettingsRequested` 打开设置框并**不发网络请求**；否则把该对象交给线程与调用层，**不在别处另判三项** |
| 触发 | 桥接槽 `requestAiReview()`：递增 `_ai_revision` 并起线程（门槛判断见上一行） |
| 忙态 | `aiBusy` 属性 + 变更信号；请求中顶栏按钮禁用 |
| 弹窗 | `gui/qml/AiEvaluationDialog.qml`：上半为两份原始数值并列（13 个数值 + 5 个枚举，字段顺序固定，**不算差值、不做档位**），下半为简评与三个按钮 |
| 基准数值来源 | 桥接新增只读属性 `aiBaselineData`，直接来自 `load_baseline()`（任务 02，已是外发字段形状）；当前卡侧取上面那份深拷贝快照，**不用** `enemyData` 界面投影 |
| 字段中文标签 | 沿用 `gui/qml/EditorCombatPage.qml:32-42` 的既有中文名（如 `max_hp` → 最大生命值、`attack_interval` → 攻击间隔），由桥接暴露同一份映射给对话框复用，**不在对话框里另写一份** |
| 采纳 | 桥接槽 `applyAiComment(text)` → `CardModel.update_properties({"brief_comment": text})`，一步入撤销栈；不额外写文件 |
| 放弃 | 只关弹窗，不触碰卡片数据 |
| 重新生成 | 同参数再请求一次，覆盖当前预览（同样递增 `revision`） |
| 过时结果 | 结果 `revision` 与当前不符（切卡 / 新建卡 / 关窗）→ 丢弃并记日志，不弹窗、不写入 |
| 关窗 | 只 `requestInterruption()` + `task.cancel()`，**绝不 `terminate`**；同步请求无法中断，最长 60 秒自行结束，结果按 `revision` 丢弃 |
| 错误文案 | `categorize_error_message` 按 4 个 AI 子类分支：`AiCredentialError` → 未配置引导打开设置框 / 密钥无效；`AiRateLimitError` → 稍后重试；`AiServiceError` → 服务端异常（带状态码）或响应无法解析（含重试后仍非法）；`AiNetworkError` → 网络不可达 |
| 冒烟 | 按验收总纲 6 条逐条手动实测；打包后重跑第 6 条 |

## 步骤

- [ ] `AiEvaluateThread`（同步调用 `ai_client.evaluate`，信号带 `revision`）
- [ ] 桥接：`aiReviewRequested` / `aiSettingsRequested` / `aiBusy(Changed)` / `_ai_revision` / `requestAiReview()` / `applyAiComment()` / `aiBaselineData`
- [ ] `AiEvaluationDialog.qml`（数值并列表 + 简评 + 采纳 / 放弃 / 重新生成）
- [ ] `Workspace.qml` 挂载对话框并接两个 `Requested` 信号
- [ ] `CommandBar.qml` 顶栏加「AI 评价」按钮（与「参考 PRTS」并列，忙态禁用）
- [ ] `categorize_error_message` 增加 AI 分支（按子类）
- [ ] 手动实测验收总纲第 1–5 条
- [ ] `pyinstaller --noconfirm --clean enemyEval.spec` 后实测第 6 条

## 非目标

- 不做快捷键、不做右键菜单入口、不导出评价到文件、不做批量评价、不做结果缓存、不把评价写进配置文件的别的字段。

## 风险与回滚

- 风险：请求进行中切卡导致结果串到另一张卡 → `revision` 丢弃。
- 风险：请求中关窗残留线程 → 不 `terminate`；同步请求最长 60 秒自然结束。
- 风险：弹窗并列数值与简评不同屏导致核对失效（这是验收第 3 条的落点）→ 同一对话框内呈现。
- 风险：错误分类依赖异常对象穿越线程信号 → 信号形参用 `object`，桥接收到后直接交给 `categorize_error_message`。
- 回滚：删线程、弹窗与桥接改动，撤按钮与错误分支。

## 验收

按 `00-overview.md` 的验收总纲 6 条逐条实测，第 6 条在打包产物内验证。
