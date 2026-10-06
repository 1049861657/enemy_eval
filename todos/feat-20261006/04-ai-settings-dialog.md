# 任务 04：AI 设置面板

## 目标

界面里能填 Base URL / 模型名 / 密钥并写入偏好；密钥以密码框呈现，边上讲清明文存储。

## 现状与锚点

| 事实 | 位置 |
|---|---|
| 对话框约定：`Dialog` + `required property var controller`、`parent: Overlay.overlay`、`modal: true`、`standardButtons: Dialog.NoButton`、`Theme` 取色与间距、`enter` 过渡 | `gui/qml/AboutDialog.qml:1-40` |
| 挂载与打开方式：`PrtsQueryDialog { controller: root.controller }` + `Connections { function onPrtsQueryRequested(...) { prtsDialog.open() } }` | `gui/qml/Workspace.qml:64,405` |
| 桥接属性/信号/槽写法（开关类设置的既有范式） | `gui/qml_bridge.py`（`updateCheckEnabled` / `updateCheckEnabledChanged` / `set_update_check_enabled`） |
| 偏好读写与保存失败口径 | `utils/app_settings_store.py`（任务 01 新增三字段与 `save_ai_settings`） |
| URL 形状校验的既有思路 | `models/media.py::is_url` |
| 错误文案分类 | `utils/error_handler.py::categorize_error_message` |

## 结论

| 项 | 结论 |
|---|---|
| 新增文件 | `gui/qml/AiSettingsDialog.qml` |
| 字段 | Base URL、模型名、密钥（`echoMode: TextInput.Password`）三项，无总开关、无超时项 |
| 入口 | ①「AI 评价」未配置时直接打开本框（任务 05）；②「更多」菜单加「AI 设置」项，随时可改 |
| 校验 | 只校验形状：`base_url` 非空时需可解析出 scheme 与 host；模型名非空；密钥可空 |
| 保存 | 走桥接槽 → 任务 01 的 `save_ai_settings`；成功后发变更信号并提示一句；失败走 `categorize_error_message` |
| 预填 | 打开时读 `load_app_settings()` 的三项作为初值，写盘回同一份文件 |
| 提示文案 | 明确写出：密钥以明文存于偏好 JSON（如实说明，不做安全承诺） |
| 网络 | 打开、编辑、保存都不发起任何网络请求（无连通性测试） |

## 步骤

- [ ] 桥接加三个只读属性 + 一个变更信号 + 保存槽（`@Slot(str, str, str)`）
- [ ] `AiSettingsDialog.qml`：三输入 + 保存 / 取消 + 明文存储说明文字
- [ ] `Workspace.qml` 挂载对话框，并在 `Connections` 里接 `onAiSettingsRequested`
- [ ] `CommandBar.qml`「更多」菜单加「AI 设置」项
- [ ] 保存成功后让界面回显与文件一致（重启再验一次）

## 非目标

- 不做供应商预设下拉、不做连通性测试按钮、不做超时 / 重试项、不做多套配置切换、不做密钥加密。

## 风险与回滚

- 风险：密钥在界面被旁观泄露 → 密码框 + 不回显、不写日志。
- 风险：保存失败被静默吞掉 → 走既有 `_write_updates` 的失败口径（只记日志）时，界面需给出保存失败提示，不能表现为「已保存」。
- 回滚：删对话框、撤桥接与菜单改动。

## 验收

1. 填入三项并保存后，`app_settings.json` 出现三个键；重启后界面回显一致。
2. 密钥在界面为密码态，不出现在日志。
3. `base_url` 留空或写成非法值时给出形状提示且不写入。
4. 打开与保存过程中无任何网络请求（看日志）。
