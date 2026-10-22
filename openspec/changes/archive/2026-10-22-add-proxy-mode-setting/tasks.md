# Tasks

## 1. 偏好与策略模块

- [x] 1.1 `utils/app/settings.py` 的 `AppSettings` 增加 `proxy_mode: Literal["system", "none"] = "none"`；验证：`uv run python -c "from utils.app.settings import AppSettings; assert AppSettings().proxy_mode == 'none'"` 退出码为 0
- [x] 1.2 新增 `utils/app/net_prefs.py`（`proxy_mode()` / `set_proxy_mode()`，写盘走 `try_update_settings`）；验证：用临时目录 monkeypatch `settings_file_path` 的一次性脚本完成写入与 `load_app_settings(force_reload=True)` 读回，且不新增 pytest 用例
- [x] 1.3 新增 `utils/net/proxy.py`（`ProxyMode`、`proxy_url_for`：`proxy_bypass` → `getproxies` 的 `https`/`all` → 补 `http://`）；验证：子进程中分别设置 `HTTPS_PROXY`、`NO_PROXY=prts.wiki`、两者皆空，`proxy_url_for("https://prts.wiki")` 依次返回代理 URL、`None`、`None`
- [x] 1.4 确认 `utils/app/settings.py` 不新增对 `utils.net` 的导入；验证：`uv run python -c "import utils.app.settings"` 与 `uv run python -c "import models"` 均通过

## 2. 传输层与 PRTS 通道

- [x] 2.1 `utils/net/transport.py::build_retry_transport` 增加 `proxy: str | None = None`，透传给内层 `AsyncHTTPTransport` / `HTTPTransport`；验证：一次性脚本构造两种 transport，`proxy` 为空时内层 `_pool` 为 `ConnectionPool`，传入代理时为 `HTTPProxy`
- [x] 2.2 `utils/prts/api_client.py` 的 `build_async_client` / `build_client` 增加 `proxy_target` 参数，按 `proxy_mode()` 解析代理并传给 `build_retry_transport`；验证：`proxy_mode` 为 `none` 时 `build_async_client()._mounts == {}` 且内层为 `ConnectionPool`；为 `system` 且设置 `HTTPS_PROXY` 时内层为 `HTTPProxy`
- [x] 2.3 `utils/qt/prts_task.py` 为头像下载另起 `build_async_client(proxy_target=avatar_url)`，`utils/qt/avatar_task.py` 传入 `self.avatar_url`，两处均用 `async with` 关闭；验证：设置 `NO_PROXY=media.prts.wiki` 且启用系统代理时，一次性脚本显示 API client 走代理、头像 client 直连
- [x] 2.4 核对 `utils/prts/pipeline.py` 的回退 client 与 `scripts/smoke_mediawiki_api.py` 使用默认目标；验证：两者不传 `proxy_target` 时解析目标仍为 `https://prts.wiki/api.php`

## 3. AI 评价与更新检查

- [x] 3.1 `utils/app/ai_prefs.py::AiRequestConfig` 增加必填 `trust_env: bool`，`ai_request_config()` 以 `proxy_mode() == "system"` 填充；验证：临时偏好下 `ai_request_config().trust_env` 随 `proxy_mode` 变化
- [x] 3.2 `utils/ai/client.py` 的 `evaluate` / `aevaluate`：跟随系统用默认 transport；不使用代理时传 `httpx.HTTPTransport(trust_env=True)`（async 用 `AsyncHTTPTransport`），保留环境 CA；验证：`proxy_mode=none` 且 `HTTPS_PROXY=http://127.0.0.1:1` 时，AI 调用返回凭据/服务错误而非代理连接错误
- [x] 3.3 `scripts/smoke_ai_review.py` 两处 `AiRequestConfig(...)` 构造补齐 `trust_env`（不可达地址用例为 `False`，正常运行取 `ai_request_config()`）；验证：`--offline` 运行通过，且 `--dry-run` 不抛字段缺失异常
- [x] 3.4 `utils/app/update_check.py::fetch_latest` 与 AI 同构选择 transport；验证：`proxy_mode=none` 且 `HTTPS_PROXY=http://127.0.0.1:1` 时 `fetch_latest("")` 不出现代理连接失败

## 4. 界面与桥接

- [x] 4.1 `gui/bridge/app.py` 增加 `proxy_mode()` / `save_proxy_mode(mode)`；验证：默认返回 `"none"`，保存 `"system"` 后返回 `"system"` 且偏好文件含该字段
- [x] 4.2 `gui/qml_bridge.py` 增加 `proxyModeChanged` 信号、`proxyMode` 属性与 `setProxyMode` 槽；验证：QML 启动无绑定告警，切换后属性刷新
- [x] 4.3 新增 `gui/qml/dialogs/SettingsDialog.qml`：左侧导航为「AI」「网络」，AI 分区沿用原表单，网络分区用 `AppComboBox` 选择「不使用代理 / 跟随系统」；删除 `AiSettingsDialog.qml`；验证：`pyside6-qmllint -I gui/qml gui/qml/dialogs/SettingsDialog.qml gui/qml/dialogs/AiEvaluationDialog.qml` 退出码为 0
- [x] 4.4 更多菜单在「检查更新」上方增加「设置…」入口；`QmlBridge` 以 `settingsRequested(str)` / `requestSettings(section)` 替换 AI 专用信号；`Workspace` 接线 `SettingsDialog`；更新检查开关保留在 `AboutDialog`；验证：`grep` 无 `AiSettingsDialog` / `requestAiSettings` 残留，qmllint 覆盖 CommandBar、Workspace、AboutDialog 退出码为 0
- [ ] 4.5 运行 GUI 手工确认：更多菜单可打开设置且首次打开无高度跳变；「AI」「网络」可切换；代理下拉两项可选并写入 `app_settings.json`；AI 保存后对话框不关闭；关闭图标位于标题行右上角且明显可见；关于里的自动检查开关仍可用

## 5. 网络层韧性

- [x] 5.1 `utils/net/transport.py` 删除 `CONNECT_RETRIES`，内层 transport 固定 `retries=0`，重试只由 `RetryTransport(total=2)` 承担；验证：`httpx.MockTransport` 分别抛 `ConnectError`、返回 502、返回 404 时，计数为 3、3、1
- [x] 5.2 `utils/prts/api_client.py::resolve_enemy_page_title` 的 `except` 扩为 `(httpx.HTTPError, ValueError)`；验证：MockTransport 让 ask 返回非法 JSON 时，下一次请求仍以裸名调用 parse
- [x] 5.3 `utils/prts/pipeline.py::_fetch_enemy_on_client` 捕获 `_fetch_parse_json` 的 `ValueError`，返回 `error_type="parse_error"`；`error_message_for_raw` 增加对应文案；验证：parse 返回非法 JSON 时得到错误信息且不抛异常
- [x] 5.4 三个 PRTS 请求函数各加一条 DEBUG 日志（动作、状态码、耗时）；验证：DEBUG 级别执行一次导入，日志出现 parse / ask / imageinfo 的记录
- [ ] 5.5 回归既有 PRTS 契约：`_fetch_parse_json` 仍返回二元组、门面导出不变；验证：`uv run pytest tests/test_prts_api_client.py tests/test_prts_pipeline.py tests/test_prts_mediawiki_pipeline.py` 通过，且不新增用例

## 6. 集成验证

- [ ] 6.1 三通道矩阵：分别在 `none` 与 `system` 下执行 PRTS 导入（含头像）、AI 评价、检查更新，确认代理行为与设置一致；验证：记录每个通道的结果，`system` 下 `NO_PROXY` 命中主机的请求仍直连
- [ ] 6.2 脚本一致性：`proxy_mode=none` 且设置 `HTTPS_PROXY=http://127.0.0.1:1` 时运行 `scripts/smoke_mediawiki_api.py`，确认请求不因代理失败；验证：脚本完成或给出非代理类错误
- [ ] 6.3 无静默回退：`proxy_mode=system` 且代理指向不可达端口，确认 PRTS、AI、更新检查均报网络错误且没有直连成功的请求；验证：三处错误文案均出现，日志中无直连响应
- [ ] 6.4 重试次数：同一不可达代理下确认 PRTS 每个请求只产生 3 次尝试；验证：DEBUG 日志或代理端计数为 3，不出现 9 次

## Workflow follow-up

- 按项目审查要求完成评审后归档该变更。
- 验证归档后的 `openspec/specs/outbound-proxy/spec.md` 与 `openspec/specs/network-resilience/spec.md` 内容完整。
