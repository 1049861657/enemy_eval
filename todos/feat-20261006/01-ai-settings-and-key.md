# 任务 01：AI 偏好字段与密钥

## 目标

偏好层能存 AI 配置并在 JSON 中往返；`ai_api_key` 可被环境变量覆盖，且只这一个字段参与环境变量读取。

## 现状与锚点

| 事实 | 位置 |
|---|---|
| `AppSettings` 字段与来源配置 | `utils/app_settings_store.py::AppSettings` |
| **当前显式禁用环境变量源**：`settings_customise_sources` 里 `del env_settings, dotenv_settings, file_secret_settings` | `utils/app_settings_store.py:78-92` |
| 写入既有模式：`_write_updates(**updates)`（失败只记日志、内存保持原状）、`_cloned` 保留其余字段 | `utils/app_settings_store.py` |
| 偏好文件路径可被测试注入：`settings_file_path()` | `utils/app_settings_store.py::settings_file_path` |
| 容错读源：文件缺失或损坏按「不存在」处理 | `_TolerantJsonConfigSettingsSource` |
| 超时四参数写法的既有形状 | `utils/prts_api_client.py::request_timeout` |

## 结论

| 项 | 结论 |
|---|---|
| 新增字段 | `ai_base_url: str = ""`、`ai_model: str = ""`、`ai_api_key: str = ""`，默认空串 |
| 密钥覆盖 | 环境变量 `ENEMY_EVAL_AI_API_KEY` 优先于偏好文件 |
| 覆盖范围 | **只给 `ai_api_key` 开环境变量别名**（`AliasChoices("ai_api_key", "ENEMY_EVAL_AI_API_KEY")`），其余字段不参与环境变量读取，避免偏好被环境意外改写 |
| JSON 键名 | 仍是 `ai_api_key`（别名列表必须包含它，否则文件读不到） |
| 超时 | **不进偏好**：固定读超时是调用层的模块常量（任务 03），不暴露给用户 |
| 总开关 | **不设**：三项为空即视为未配置 |
| 保存入口 | 新增 `save_ai_settings(base_url, model, api_key)`，内部走 `_write_updates` 并更新缓存 |

## 步骤

- [ ] `AppSettings` 加三个字段（默认空串）
- [ ] `settings_customise_sources` 放回环境变量源，并确保优先级为 `init_settings → env → JSON 文件`
- [ ] `ai_api_key` 用 `AliasChoices` 指定别名（含 JSON 键名与环境变量名）
- [ ] 新增 `save_ai_settings(...)` 与读取辅助（取三项，返回空串表示未配置）
- [ ] 确认旧偏好文件（无 `ai_*` 键）仍能加载，其余字段语义不变

## 非目标

- 不引入 keyring 或任何新依赖；不做密钥加密；不做超时与重试的用户配置项；不做多套配置切换。

## 风险与回滚

- 风险：放回环境变量源时若用了全局 `env_prefix`，会在低概率下让其它偏好字段被同名环境变量覆盖 → 只给密钥一个字段开别名。
- 风险：`AliasChoices` 漏掉 `ai_api_key` 会让 JSON 键读不到 → 验收第一条覆盖。
- 回滚：撤三字段与来源改动。

## 验收

1. 写入三项后重启，读回一致，`app_settings.json` 中出现这三个键。
2. 设置 `ENEMY_EVAL_AI_API_KEY` 时取环境变量值；未设置时取文件值。
3. 既有偏好文件（无 `ai_*` 键、含 `recent_files` 等）加载后其余字段不受影响。
