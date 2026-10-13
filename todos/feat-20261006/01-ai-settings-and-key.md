# 任务 01：AI 偏好字段与密钥

## 目标

偏好层能存 AI 配置与自定义提示词并在 JSON 中往返：四个字段落进 `app_settings.json`，读回一致。

## 现状与锚点

| 事实 | 位置 |
|---|---|
| `AppSettings` 字段与来源配置 | `utils/app_settings_store.py::AppSettings` |
| 写入既有模式：`_write_updates(**updates)`（失败只记日志、内存保持原状） | `utils/app_settings_store.py::_write_updates` |
| 写盘链路：`_cloned(current, **updates)` 用 `current.model_dump()` → `model_validate()` → `_persist` | `utils/app_settings_store.py:104-160` |
| 容错读源：文件缺失或损坏按「不存在」处理 | `_TolerantJsonConfigSettingsSource` |
| 偏好文件路径可被测试注入：`settings_file_path()` | `utils/app_settings_store.py::settings_file_path` |

## 结论

| 项 | 结论 |
|---|---|
| 新增字段 | `ai_base_url: str = ""`、`ai_model: str = ""`、`ai_api_key: str = ""`、`ai_prompt: str = ""`，默认空串 |
| 存储 | 只走偏好 JSON：字段直接读写，无别名、无第二来源；`settings_customise_sources` 原样不动 |
| 保存入口 | 新增 `save_ai_settings(base_url, model, api_key)`，内部走 `_write_updates`，其余字段保留 |
| 读取入口 | 新增 frozen dataclass `AiRequestConfig(base_url, model, api_key)` 与 `ai_request_config() -> AiRequestConfig \| None`：三项去空白后缺任一即 `None`。「是否已配置」只有这一处判断，任务 03 发起前与任务 05 判定门槛共用 |
| 提示词字段 | `ai_prompt` 存自定义提示词，**空串表示沿用内置默认**（任务 05 用 `utils/ai_prompt.py::effective_prompt` / `prompt_for_storage` 折算）；写入走 `save_ai_prompt(prompt)`，与 `save_ai_settings` 同形（先落盘再更新缓存，失败抛 `FileOperationError`） |
| 表单预填 | 不另做读取辅助：任务 04 预填直接读 `load_app_settings()` 的三个字段 |
| 超时 | **不进偏好**：固定读超时是调用层的模块常量（任务 03），不暴露给用户 |
| 总开关 | **不设**：三项为空即视为未配置 |

## 步骤

- [x] `AppSettings` 加三个字段（默认空串，不设 `alias` / `validation_alias`）
- [x] `AppSettings` 加 `ai_prompt`（默认空串）与 `save_ai_prompt(prompt)`
- [x] 新增 `AiRequestConfig` 与 `ai_request_config()`
- [x] 新增 `save_ai_settings(base_url, model, api_key)`
- [ ] 确认旧偏好文件（无 `ai_*` 键）仍能加载，其余字段语义不变（待本机）

## 非目标

- 不引入 keyring 或任何新依赖；不做密钥加密；不做环境变量覆盖；不做超时与重试的用户配置项；不做多套配置切换；不改 `settings_customise_sources`。

## 风险与回滚

- 风险：明文密钥落在偏好 JSON，随配置分享外泄 → 界面用密码框、不进日志与异常消息（任务 03 / 04）；已接受不做加密。
- 风险：给这三个字段设 `validation_alias` 会让 `_cloned()` 的 `model_dump()` → `model_validate()` 往返丢字段（每次写偏好把密钥清空）→ 不设别名。
- 回滚：撤三字段、`AiRequestConfig` 与两个入口。

## 验收

1. 填入三项并保存后，`app_settings.json` 出现 `ai_base_url` / `ai_model` / `ai_api_key` 三个键；重启读回一致。
2. `ai_request_config()` 在三项齐备时给出三者，缺任一或为空白时给出 `None`。
3. 既有偏好文件（无 `ai_*` 键、含 `recent_files` 等）加载后其余字段不受影响。
4. 保存自定义提示词后 `app_settings.json` 出现 `ai_prompt`；存回内置默认文案时该键为空串。
