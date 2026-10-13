# 任务 04：AI 设置面板

## 目标

界面里能填 Base URL / 模型名 / 密钥并写入偏好；三个字段明文展示（**不做密码框**），框内讲清明文存储与「保存后怎么验证」。

## 现状与锚点

| 事实 | 位置 |
|---|---|
| 对话框约定：`Dialog` + `required property var controller`、`parent: Overlay.overlay`、`modal: true`、`standardButtons: Dialog.NoButton`、`Theme` 取色与间距、`enter` 过渡 | `gui/qml/AboutDialog.qml:1-40` |
| 带输入框的表单框先例（视觉基准、按钮主次、`onOpened` 设初值的写法） | `gui/qml/PrtsQueryDialog.qml` |
| 挂载与打开方式：`PrtsQueryDialog { controller: root.controller }` + `Connections { function onPrtsQueryRequested(...) }` | `gui/qml/Workspace.qml:408`、`Workspace.qml:136-160`（`Connections` 块） |
| 桥接属性/信号/槽写法（开关类设置的既有范式） | `gui/qml_bridge.py`（`updateCheckEnabled` / `updateCheckEnabledChanged` / `setUpdateCheckEnabled:445`） |
| 写偏好失败要抛错的既有范式（先 `_persist` 后 `_cached`） | `utils/app_settings_store.py::save_rating_schema`、`set_rating_radar:209` |
| 桥接捕获写盘失败并发字段错误的既有范式 | `gui/qml_bridge.py::setRatingRadar:324`（`fieldError.emit` + 回滚）、`updateRatingSchema:337`（返回 bool + `fieldError`） |
| 字段错误在界面转 toast 与内联提示的通道 | `gui/qml/Workspace.qml:142-148`（`onFieldError`） |
| 偏好读写 | `utils/app_settings_store.py`（任务 01：三字段、`save_ai_settings:318`、`ai_request_config:305`） |
| 输入控件的预填陷阱：只有 `value` / `text` / `placeholderText` / `maximumLength` / `inputMethodHints` 别名；`value` 只在「无焦点」时同步 `text`，`Component.onCompleted` 只跑一次 | `gui/qml/AppTextField.qml:11-22,52,57` |
| 错误文案分类 | `utils/error_handler.py::categorize_error_message` |

## 结论

| 项 | 结论 |
|---|---|
| 新增文件 | `gui/qml/AiSettingsDialog.qml` |
| 字段 | Base URL、模型名、密钥三项，均为**普通文本输入（明文可见，不做密码框）**；无总开关、无超时项 |
| 视觉基准 | 照 `PrtsQueryDialog.qml`：`padding: Theme.space5`、宽 `Math.min(parent.width - 48, 440)`、圆角 `Theme.radiusLarge`；保存按钮默认 `primary`、取消 `secondary` |
| 入口 | ①「AI 评价」未配置时直接打开本框（任务 05）；②「更多」菜单加「AI 设置」项，随时可改 |
| 规范化（Python 侧） | `save_ai_settings` 内先 `normalize_ai_base_url`：非空、http(s) 且带主机（**不复用** `models/media.py::is_url`，它不校验 host 非空）；path 为空补 `/v1`、命中 `/chat/completions` 或 `/completions` 去掉该段、末尾斜杠去掉，自定义版本段（如 `/v1beta/openai`）原样保留；模型名非空、密钥可空；形状非法抛 `ValueError`，写盘失败抛 `FileOperationError` |
| 保存槽 | `@Slot(str, str, str, result=bool) saveAiSettings(...)`：成功 → 发变更信号 + `show_toast("AI 配置已保存", "success")` + 返回 `True`（对话框关闭）；失败 → `fieldError.emit("ai_settings", msg)` + 返回 `False`（对话框保持打开） |
| 保存失败语义 | `utils/app_settings_store.py::save_ai_settings` 改为与 `save_rating_schema` 同形：先 `_persist` 后更新 `_cached`，写盘失败抛 `FileOperationError`——**不再走只记日志的 `_write_updates`** |
| 预填 | 桥接暴露只读属性 `aiBaseUrl` / `aiModel` / `aiApiKey` + `aiConfigured: bool`；对话框在 `onOpened` **显式**把三个框整体重置为这三个属性值，并重置各自 `lastCommittedValue`——只靠绑定会在「取消后重开」时留下未保存的旧输入 |
| 状态提示 | 框内一行：`aiConfigured` 为真显示「当前配置：已配置」，否则「当前配置：未配置（三项齐全后才能评价）」；判定复用 `ai_request_config()`，不在 QML 里各判三项 |
| 输入提示 | 占位符给示例（`https://api.deepseek.com/v1`）；字段下方实时显示「请求将发往 &lt;最终地址&gt;」——由同一个 `normalize_ai_base_url` + `/chat/completions` 生成，与实际发请求同源；不再解释「要不要写 /v1」 |
| 提示文案 | 写出「密钥以明文存于偏好 JSON（如实说明，不做安全承诺）」与「保存后点『AI 评价』即可验证配置」 |
| 数据流 | 本框**不接** `AppTextField` 的 `value` / `valueCommitted`（它带 260ms 防抖，接上就变成边敲边写盘）；只在保存按钮里读三个 `text` |
| 网络 | 打开、编辑、保存都不发起任何网络请求（无连通性测试） |

## 步骤

- [x] `utils/app_settings_store.py::save_ai_settings`：规范化 + 直接落盘（失败抛错），脱离 `_write_updates`
- [x] 桥接：三个只读属性 + `aiConfigured` + 变更信号 + `saveAiSettings(...) -> bool` 槽（失败发 `fieldError`）
- [x] `AiSettingsDialog.qml`：三输入 + 状态行 + 保存 / 取消 + 明文存储与验证方式说明；`onOpened` 重置三框
- [x] `Workspace.qml` 挂载对话框，并在 `Connections` 里接 `onAiSettingsRequested`
- [x] `CommandBar.qml`「更多」菜单加「AI 设置」项
- [ ] 保存成功后让界面回显与文件一致（重启再验一次，待本机）

## 非目标

- 不做密码框与明文回显切换、不做供应商预设下拉、不做连通性测试按钮、不做超时 / 重试项、不做多套配置切换、不做密钥加密。

## 风险与回滚

- 风险：密钥明文展示被旁观 → 已接受；不写日志、不进异常消息、不出现在错误文案。
- 风险：取消后重开显示旧输入 → `onOpened` 显式重置（见结论「预填」）。
- 风险：输入即时写盘冲破「保存 / 取消」语义 → 不接 `value` / `valueCommitted`。
- 风险：保存失败被静默吞掉 → 已由「先落盘、失败抛错」覆盖；桥接发 `fieldError`，对话框不关闭，不表现为「已保存」。
- 回滚：删对话框、撤桥接与菜单改动、把 `save_ai_settings` 恢复为 `_write_updates` 实现。

## 验收

1. 填入三项并保存后，`app_settings.json` 出现三个键；重启后界面回显一致。
2. 密钥框为普通文本输入（明文可见）；日志与错误文案中不出现密钥。
3. `base_url` 留空、缺 host，或模型名为空时：对话框保持打开、字段下方给出形状提示、偏好文件未被改写。
4. 写盘失败时（如把偏好目录设为只读）出现保存失败提示，不出现「已保存」。
5. 清空密钥后保存：状态行显示「未配置」；点「AI 评价」时打开本框（配合任务 05 验收 1）。
6. 打开与保存过程中无任何网络请求（看日志）。
