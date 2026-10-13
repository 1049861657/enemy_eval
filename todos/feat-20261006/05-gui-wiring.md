# 任务 05：GUI 接线与收口

## 目标

把 01–04 接成可用闭环：点顶栏按钮开面板 → 编辑提示词 → 生成 → 面板给出杰斯顿的点评 → 采纳 / 关闭；采纳一步可撤销；任何失败都不改数据；打包产物可用。

## 现状与锚点

| 事实 | 位置 |
|---|---|
| 顶栏按钮写法（「参考 PRTS」同级） | `gui/qml/CommandBar.qml:197` |
| 顶栏忙态禁用既有写法 | `gui/qml/CommandBar.qml:199`（`enabled: !root.workspace.controller.prtsBusy`） |
| 线程生成 + 忙态守卫 + 状态栏文案 + `finished → deleteLater` 范式 | `gui/main_window.py::_fetch_prts_data:380-394` |
| 可中断轮询范式（asyncio + 50ms 查标志 + `task.cancel()`） | `utils/thread_manager.py::PrtsFetchThread:85-113` |
| 关窗清理（`requestInterruption` + `wait(3000)`，超时只记日志、不 terminate） | `gui/main_window.py::closeEvent:472-501` |
| 过时结果丢弃范式（世代号不匹配即丢） | `gui/render_coordinator.py:31-41, 100-141` |
| 多字段写入一步入栈（自带撤销） | `gui/card_model.py::update_properties:105-120` |
| 当前卡权威数据（返回活引用，需自行深拷贝） | `gui/card_model.py::enemy_data:80-83` |
| 换卡 / 换数据的入口 | `gui/main_window.py::_new_card:210-218`（换 `CardModel`）、`_change_prts_level:440-462`（`apply_enemy_data`）、`_open_file:232`（`load_from_file`，**不换模型**）；`gui/qml_bridge.py::set_card_model:231-238` |
| 对话框挂载区（`PrtsQueryDialog` 之后为自然追加位） | `gui/qml/Workspace.qml:388-428` |
| `Workspace` 连接与字段错误通道 | `gui/qml/Workspace.qml:144-170`（`Connections`）、`:20` / `:49-55`（`fieldErrors` / `clearFieldError`） |
| 错误文案分类（4 个 AI 子类 isinstance 分支**已存在**） | `utils/error_handler.py:73-86` |
| `aiSettingsRequested`（**已存在**，04 交付） | `gui/qml_bridge.py:93` + `gui/qml/Workspace.qml:163-165` |
| 外发白名单 | `utils/ai_client.py:31-48` |
| 基准与调用层 | `utils/ai_baseline.py::load_baseline:57-59`（返回深拷贝，读盘/校验失败抛 `FileOperationError`）、`utils/ai_client.py::evaluate:140-188`（同步阻塞；async 孪生 `aevaluate` 为任务 03 收尾项）、`AI_TIMEOUT` 见 `utils/ai_client.py:29`（`read=120` 秒） |

## 结论

| 项 | 结论 |
|---|---|
| 线程 | `utils/thread_manager.py` 追加 `AiEvaluateThread`：入参 基准 dict（`load_baseline()`）+ 当前卡快照 + `AiRequestConfig` + `revision`；信号 `evaluationFinished(object, int)` / `evaluationFailed(object, int)`（**传异常对象**，分类留给桥接）。`run` 内 `asyncio.run` 调 `ai_client.aevaluate`，每 50ms 查 `isInterruptionRequested` 后 `task.cancel()`（照 `PrtsFetchThread:103-113`）；被中断则不发射信号 |
| 线程归属 | **由 `MainWindow` 持有并启动**（照 `_fetch_prts_data` 范式：忙态守卫 → 起线程 → `finished → deleteLater` 置 None），并纳入 `closeEvent` 清理；桥接不持有线程，只做门槛判定、忙态与结果缓存。请求在轮询点被取消，关窗不依赖等待 |
| 快照 | 起线程前 `card_model.enemy_data.model_copy(deep=True)`；线程只读写自己那份，桥接不读线程内部状态 |
| 配置/密钥取值 | 桥接放行线程前取一次 `ai_request_config()`：为 `None` → 发 `aiSettingsRequested` 打开设置框（面板保持打开）并**不发网络请求**；否则把该对象交给线程与调用层，**不在别处另判三项** |
| 触发 | 桥接槽 `requestAiReview(prompt)`：门槛判断 → 提示词落盘 → 递增 `_ai_revision` → 发 `aiReviewRequested(config, prompt, snapshot, baseline, revision)` |
| 失效世代号 | `_ai_revision` 在 `requestAiReview()` 递增，**并在换卡/换数据处一并递增**：`set_card_model`（`qml_bridge.py:231`）与级别变更回调（`main_window.py::_change_prts_level`）；结果回来时不符即丢 |
| 忙态 | `aiBusy` 属性 + `aiBusyChanged` 信号；顶栏按钮禁用；槽入口「忙则忽略并 toast」（照 `main_window.py:381-383`） |
| 信号命名 | 三个方向分开：`aiReviewRequested(config, prompt, snapshot, baseline, revision)` = 面板 → 发起；`aiCommentReady()` = 结果到达（面板已开，只刷新绑定）；`aiAbandonRequested()` = 面板在请求途中关闭 → 取消在飞请求。不复用 `aiSettingsRequested` 之外的语义 |
| 面板 | `gui/qml/AiEvaluationDialog.qml`：人设头（「杰」字瓦片 + 标题 + `aiTarget`/卡名 · `aiModel` + 状态徽标）+ 提示词条（**默认折叠**，折叠时标出「内置默认 / 自定义 · N 字」；展开后 `onOpened` 预填 `aiPromptText()`、「恢复默认」取 `aiDefaultPrompt()`；条整行可点）+ 可展开的「实际请求」条（折叠时即显示 `POST aiBaseUrlPreview(aiBaseUrl)`）+ 简评卡片（引言条 + 引号水印 + 骨架屏 + 空态引导 + 字数刻度）+ 未配置内联横幅（`requestAiSettings()`）+ 底部提示行；按钮为 关闭 / 生成（重新生成）/ 采纳，`Ctrl+Enter` 生成 |
| 入口 | 顶栏「AI 评价」只开面板（`Workspace.openAiReviewDialog()`）；面板内点「生成」才发请求 |
| 基准数值来源 | 桥接在 `requestAiReview()` 与 `aiRequestPreview()` 里各取一次 `load_baseline()`（随请求外发，只作说话人的参照系）；当前卡侧用深拷贝快照的 `build_current_payload`，**不用** `enemyData` 界面投影 |
| 采纳 | 桥接槽 `applyAiComment(text)` → 先比对快照与当前卡数据 → `CardModel.update_properties({"brief_comment": text})`，一步入撤销栈；不额外写文件 |
| 关闭 | 只关面板，不触碰卡片数据；若请求还在飞，则作废本次结果并取消请求（`abandonAiReview()` → `aiAbandonRequested` → 主窗口 `requestInterruption`） |
| 重新生成 | 同参数再请求一次，覆盖当前预览（同样递增 `revision`） |
| 过时结果 | `revision` 与当前不符（切卡 / 换级别 / 关窗）→ 丢弃、记日志并给一条 toast 说明本次作废，不弹窗、不写入 |
| 关窗 | 只 `requestInterruption()` + `task.cancel()`，**绝不 `terminate`**；请求在 50ms 轮询点被取消，不发结果、不写入 |
| 基准缺失 | 取基准处捕 `FileOperationError`（`ai_baseline.py:48/50/53`）→ 走 `show_dialog` 报错，不进忙态、不改数据 |
| 错误文案 | 保留 `categorize_error_message` 既有 4 个分支；补状态码与超时细分，见「增补项」第 7 条 |
| 冒烟 | 按验收 12 条手动实测；打包后重跑第 12 条 |

## 增补项（本轮评估纳管的低风险项，实施时一并做）

| # | 项 | 落点 | 无风险的理由 |
|---|---|---|---|
| 1 | 等待反馈：点「生成」后 `status_bar.showMessage("正在生成 AI 评价（模型）…")`，线程结束后复位；顶栏按钮 `enabled: !controller.aiBusy` | `gui/main_window.py`、`gui/qml/CommandBar.qml` | 与 PRTS 路径同构，不改数据流；避免「点了没反应」的 2–120 秒 |
| 2 | 简评区标注字数：`<N> 字`，QML 用 `comment.length` | `gui/qml/AiEvaluationDialog.qml` | 纯展示；把「人工定夺」需要的信息摆出来，不裁剪内容 |
| 3 | 人设头标注点评对象与状态：标题「杰斯顿的点评」，副标题 `<对象名> · <模型名>`，右侧状态徽标（已配置 / 生成中 / 未配置） | `gui/qml/AiEvaluationDialog.qml` | 纯展示；明确这条简评打给谁、当前服务是否可用 |
| 4 | 采纳前一致性校验：比对快照与当前 `card_model.enemy_data.model_dump()`，不一致先提示再写 | `gui/qml_bridge.py::applyAiComment` | 只加检查；写入路径不变，撤销语义不变 |
| 5 | 作废反馈：`revision` 不符时 toast「本次评价结果已作废」 | `gui/qml_bridge.py` 结果处理处 | 只加提示；渲染侧静默丢弃属被动重绘，此处是用户主动点击 |
| 6 | 采纳后 toast「已写入简评，可 Ctrl+Z 撤销」 | `gui/qml_bridge.py::applyAiComment` | 现有 `show_toast` 直调 |
| 7 | 错误文案收口：`httpx.ReadTimeout` 与连接失败分开（「模型响应超时（120 秒）」/「网络不可达」）；402 → 余额或配额不足、400/422 → 请求被拒（提示核对模型名）、503 → 服务繁忙、500 → 服务端异常；429 文案带 `Retry-After` 秒数（缺头回退，解析在调用层） | `utils/ai_client.py:166-175` 与 `_status_message:127-131` | 只改分支与文案，不改控制流；依据是 DeepSeek 官方错误码表 |
| 8 | 信号与属性收口：`aiCommentReady()` / `aiAbandonRequested()` 随通知刷新简评与忙态 | `gui/qml_bridge.py` | 新增表面，命名早定便宜 |
| 9 | 提示词编辑与预览：编辑框（预填 / 恢复默认）+ 可展开的「实际请求」（`render_preview`，与 `build_messages` 同源） | `gui/qml/AiEvaluationDialog.qml` + `utils/ai_prompt.py` | 纯展示与偏好读写；不改请求控制流 |
| 10 | 状态化视觉：生成中骨架条、空态引导文案、简评卡片字数刻度（目标 ≤100）、未配置内联横幅（含「去设置」）、`Ctrl+Enter` 生成 | `gui/qml/AiEvaluationDialog.qml` | 纯展示与既有槽调用；不改请求控制流 |

## 决议（本轮已定，实施不得偏移）

| # | 问题 | 决议 |
|---|---|---|
| R1 | 关窗时在飞请求怎么收（同步请求无取消 API，`read` 超时 120 秒，Qt 删除运行中的 `QThread` 会导致程序崩溃） | **可中断**：调用层增 async 路径（任务 03 收尾项），线程内 `asyncio.run` + 50ms 轮询 + `task.cancel()`。不采用 daemon 线程，也不采用「关窗等到底」 |
| R3 | 面板点「重新生成」后的按钮语义 | 生成中**禁用生成与采纳，仅允许关闭**；关闭只关面板，在飞结果按世代号作废、不写入 |
| O5 | 429 文案是否带秒数 | **带** `Retry-After` 秒数（缺头回退为「请稍后重试」）；**仍不自动重试** |
| O6 | `read` 超时取值 | **120 秒**（覆盖 `deepseek-reasoner` 类推理模型）；仍不进偏好设置项 |

## 步骤

- [x] 先做任务 03 的两项收尾（`aevaluate` async 路径、`read` 超时 120 秒、`AiRateLimitError` 带 `Retry-After`）——本任务的线程依赖它
- [x] 提示词改为用户数据：偏好 `ai_prompt` + `save_ai_prompt`；`build_messages(prompt, …)`、`render_preview(…)`、`endpoint_url(…)` 保证预览＝实发
- [x] `AiEvaluateThread`（`run` 内 `asyncio.run` + 50ms 轮询 `task.cancel()` 调 `ai_client.aevaluate`，携带提示词与 `revision`）
- [x] `MainWindow`：持有并启动线程、忙态守卫、状态栏文案、纳入 `closeEvent` 清理、采纳写入
- [x] 桥接：`aiReviewRequested(config, prompt, snapshot, baseline, rev)` / `aiCommentReady` / `aiAbandonRequested` / `aiBusy(Changed)` / `_ai_revision`（含换卡与换级别递增）/ `requestAiReview(prompt)` / `aiPromptText()` / `aiDefaultPrompt()` / `aiRequestPreview(prompt)` / `applyAiComment()`
- [x] `AiEvaluationDialog.qml`（提示词编辑 + 实际请求预览 + 简评面板 + 字数行 + 关闭 / 生成 / 采纳）
- [x] `Workspace.qml` 挂载面板并加 `openAiReviewDialog()`
- [x] `CommandBar.qml` 顶栏「AI 评价」按钮改为开面板（`enabled: !aiBusy`）
- [x] 错误文案收口（补超时与状态码细分；`categorize_error_message` 既有分支保持）
- [ ] 手动实测验收第 1–11 条
- [ ] `pyinstaller --noconfirm --clean enemyEval.spec` 后实测第 12 条

## 非目标

- 不做快捷键、不做右键菜单入口、不导出评价到文件、不做批量评价、不做结果缓存、不做流式输出、不把评价写进配置文件的别的字段。
- 不做字数裁剪、不在面板内编辑简评（润色走既有简评编辑器）、不自动重试。

## 风险与回滚

- 风险：请求进行中切卡或换级别导致结果串到另一张卡 → `_ai_revision` 在换卡/换数据处递增；成对补上「快照 ≠ 当前数据」的采纳前校验。
- 风险：请求中关窗残留线程 → 不 `terminate`；走可中断路径，请求在 50ms 轮询点被取消，不依赖等待。
- 风险：错误分类依赖异常对象穿越线程信号 → 信号形参用 `object`，桥接收到后直接交给 `categorize_error_message`。
- 回滚：删线程、面板与桥接改动，撤按钮与错误文案细分。

## 验收

按 `00-overview.md` 的验收总纲逐条实测（打包一条在打包产物内验证），并逐项核对增补项：

1. 点顶栏「AI 评价」只打开面板：提示词栏默认折叠并标出当前用的是内置还是自定义；展开后预填当前生效值、「恢复默认」回到内置文案；打开面板、展开与编辑提示词都不发请求。
2. 「预览实际请求」显示端点、模型名、system（＝当前提示词）与 user（两份数据的 JSON），与真实请求同源。
3. 点「生成」→ 生成按钮忙态、状态栏出现「正在生成 AI 评价（模型）…」；结果直接显示在面板简评区（可选中复制），字数可见且内容未被改写。
4. 未配置时点「生成」→ 打开「AI 设置」，面板保持打开、不发请求。
5. 简评是对这名敌人的评价：不出现逐字段数值清单，不以与杰斯顿的数值对照为主线。
6. 生成中关闭面板 → 作废并取消在飞请求，结果不写入、不弹窗。
7. 改提示词后点「生成」→ 偏好 `ai_prompt` 落盘（与内置默认相同则存空串），重开面板仍显示该文本。
8. 飞行中换卡或换级别 → 无结果写入、有 toast 说明作废、卡片数据不变。
9. 请求后先改字段再采纳 → 出现一致性提示。
10. 请求在飞时关窗 → 立即结束（无 120 秒等待），日志可见中断，无「QThread 仍在运行」告警。
11. 临时改名 `resource/baseline/jesselton_config.json` 后点「生成」→ 走报错弹窗，不崩溃、不改数据；采纳后出现可撤销提示，`Ctrl+Z` 一步回到原简评。
12. 打包产物启动后点击 → 能读到基准并产出结果。
