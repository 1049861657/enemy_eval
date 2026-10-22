# Design

## Context

参见 `proposal.md - Why` 与 `specs/outbound-proxy/spec.md`。

现状关键约束（已核实）：

- httpx 0.28.1 在 `transport is not None` 时**忽略**环境代理与 `trust_env`（`httpx/_client.py:685`、`:1399`）。PRTS 客户端传了显式 `RetryTransport`，因此当前恒直连；实测 `build_async_client()._mounts == {}`。
- AI 评价与更新检查使用默认 transport，`trust_env` 默认 `True`，按 `urllib.request.getproxies()` 解析：环境变量优先，未命中再读 Windows 注册表。
- PRTS API 主机是 `prts.wiki`，头像 URL 主机是 `media.prts.wiki`，同一个 client 会被用于两个主机。
- PRTS 重试目前叠了两层：内层 `AsyncHTTPTransport(retries=2)` 重试连接，外层 `RetryTransport(total=2)` 又重试超时/网络错误与 502/503/504，断连时尝试次数会相乘。
- `utils/ai/client.py` 的契约是「不读偏好，配置由调用方传入」。

## Goals / Non-Goals

**Goals:**

- 一条偏好控制全部外发请求；默认直连，切换后下一次请求生效。
- PRTS 通道在「跟随系统」下真正经过代理，同时保留 HTTP/2、连接重试与 502/503/504 重试。
- 「跟随系统」的主机绕过规则（`NO_PROXY` / 注册表 `ProxyOverride`）对三个通道一致生效。
- 脚本与命令行读取同一偏好，不增加参数。

**Non-Goals:**

- 不做自定义代理地址、代理认证、按模块分档。
- 不改变超时、请求头、重试次数、错误文案体系。
- 不在本变更内优化 `getproxies()` 的环境变量遮蔽问题（`PI_PROXY` 一类变量会让系统注册表代理被忽略）。

## Decisions

### 1. 偏好字段与领域封装

- `utils/app/settings.py::AppSettings` 增加 `proxy_mode: Literal["system", "none"] = "none"`。用 `Literal` 而非 `str`：非法值在读取阶段即被现有容错逻辑识别。
- 新增 `utils/app/net_prefs.py`：`proxy_mode() -> ProxyMode`、`set_proxy_mode(mode) -> None`，仅调用 `load_app_settings` / `update_settings`，与 `update_prefs.py`、`ai_prefs.py` 同构。
- 写盘失败走 `try_update_settings`：与「启动时检查更新」开关一致，界面不需要弹错误。

**备选**：嵌套 `proxy: {...}` 或全局 + 模块覆盖（`inherit/system/none`）。用户已确认全局两档；嵌套结构只会增加拆包成本。

### 2. 系统代理解析（`utils/net/proxy.py`，纯函数）

`ProxyMode` 定义在 `utils/app/net_prefs.py`：`utils/app` 的包契约是「不依赖其他 utils 子包」，因此不把类型放进 `utils/net`。`utils/net/proxy.py` 只保留解析函数：

```python
def proxy_url_for(url: str) -> str | None:
    """该 URL 在「跟随系统」下应使用的代理；命中绕过规则或未配置时返回 None。"""
```

规则：

1. `urlparse(url).hostname` 为空 → `None`。
2. `urllib.request.proxy_bypass(host)` 为真 → `None`（同时覆盖环境变量 `NO_PROXY` 与 Windows 注册表 `ProxyOverride`）。
3. `getproxies()` 依次取 `https`、`all`；值缺少 scheme 时补 `http://`。
4. 都没有 → `None`。

不取 `http` 键：与 httpx 的 scheme mount 语义一致（https 请求只匹配 `https://` 或 `all://` 挂载），避免出现「AI 走代理、PRTS 不走」的不同步。

**备选**：使用 httpx 私有 `_utils.get_environment_proxies()` + `URLPattern`。能完全复刻 httpx，但依赖私有 API；改用公开的 `getproxies` + `proxy_bypass`，语义等价且可读。

### 3. 重试传输层支持代理

`utils/net/transport.py::build_retry_transport(*, async_mode: bool, proxy: str | None = None)`：把 `proxy` 透传给内层传输：

- async：`httpx.AsyncHTTPTransport(http2=True, retries=0, proxy=proxy)`
- sync：`httpx.HTTPTransport(http2=True, retries=0, proxy=proxy)`

内层不做连接重试，统一由外层 `RetryTransport` 承担（见决策 9）。

httpx 的 `AsyncHTTPTransport/HTTPTransport` 原生支持 `proxy=`（`_transports/default.py:288`、`:144`），HTTP/2 经 HTTP 代理走 CONNECT，无需降级。

**备选**：给 `Client` 传 `trust_env=True` 或 `mounts`。前者在显式 transport 下无效；后者无法保留 `RetryTransport` 包裹，除非为每个挂载点各建一条重试链。

### 4. PRTS：按目标主机建客户端

`utils/prts/api_client.py` 的两个 builder 增加参数：

```python
def build_async_client(proxy_target: str = PRTS_MEDIAWIKI_API) -> httpx.AsyncClient
def build_client(proxy_target: str = PRTS_MEDIAWIKI_API) -> httpx.Client
```

内部：

```python
proxy = proxy_url_for(proxy_target) if net_prefs.proxy_mode() == "system" else None
transport = build_retry_transport(async_mode=..., proxy=proxy)
```

调用点调整：

- `utils/qt/prts_task.py`：API 请求沿用默认 client；头像下载另起 `async with pipeline.build_async_client(proxy_target=avatar_url)`，避免 `prts.wiki` 与 `media.prts.wiki` 共用一次主机的绕过判定。
- `utils/qt/avatar_task.py`：`build_async_client(proxy_target=self.avatar_url)`。
- `utils/prts/pipeline.py` 内部回退路径与 `scripts/smoke_mediawiki_api.py` 沿用默认参数。

**备选**：一个 client 用 API 主机解析一次。实现更少，但 `media.prts.wiki` 会继承 `prts.wiki` 的绕过结论，`NO_PROXY` 只列其中一个主机时行为错误。

### 5. AI：配置携带传输策略

- `utils/app/ai_prefs.py::AiRequestConfig` 增加必填字段 `trust_env: bool`；`ai_request_config()` 以 `proxy_mode() == "system"` 填充。
- `utils/ai/client.py::evaluate / aevaluate` 按模式选择构造方式：
  - 跟随系统：`httpx.Client(timeout=AI_TIMEOUT)`（默认 transport，读取环境代理）。
  - 不使用代理：`httpx.Client(timeout=AI_TIMEOUT, transport=httpx.HTTPTransport(trust_env=True))`（async 用 `AsyncHTTPTransport`）。显式 transport 会跳过代理挂载，但 `trust_env=True` 仍保留 `SSL_CERT_FILE` / `SSL_CERT_DIR`；用 `trust_env=False` 会连带禁用环境 CA，企业中间人证书场景会坏。
- 客户端仍是「不读偏好」。
- 构造点同步修改：`scripts/smoke_ai_review.py:115` 显式 `trust_env=False`；`:188` 取 `ai_request_config()` 的 `trust_env`，缺失时按当前偏好解析。

**备选**：`trust_env=False` 直接关代理。实现更短，但把「不用代理」与「忽略环境 CA」绑死，已否决。在 `client.py` 内读偏好则违反模块不变量。

### 6. 更新检查

`utils/app/update_check.py::fetch_latest` 与 AI 同构：跟随系统用默认 transport；不使用代理时传显式直连 transport 且 `trust_env=True`，避免关掉环境 CA。该模块本就属于偏好层，`UpdateCheckThread` 无需改动。

### 7. 界面入口：更多菜单 → 聚合设置

- `gui/qml/pages/CommandBar.qml` 的「更多」菜单在「检查更新」上方增加「设置…」，触发 `controller.requestSettings("ai")`。
- 新增 `gui/qml/dialogs/SettingsDialog.qml`：左侧分区导航（`AI` / `网络`），右侧 `StackLayout`；关闭按钮为标题行右上角的关闭图标，不占底部按钮区。字段预填在 `open()` 之前完成，避免首次打开时 URL 预览行出现导致对话框高度跳变。
  - AI：沿用原 `AiSettingsDialog` 的字段、URL 预览与保存语义；名称取 `AI`，配置供后续所有 AI 功能复用；保存成功后不关闭对话框。
  - 网络：文案说明「代理方式决定全局如何访问网络」；代理方式用下拉框（`AppComboBox`）而非开关，当前选项为「不使用代理」「跟随系统」；后续增加自定义代理时只在选项表扩展。
- 更新检查的自动检查开关留在 `AboutDialog`（与「检查更新」按钮同处），不进入设置对话框。
- `AiEvaluationDialog` 未配置时的「去设置」打开同一对话框并定位到 AI 分区。
- 删除 `gui/qml/dialogs/AiSettingsDialog.qml`；`AboutDialog` 只保留版本、构建时间、更新检查（「检查更新」按钮与自动检查开关），不承载 AI / 网络设置。
- 桥接：`settingsRequested(str)` 信号与 `requestSettings(section)` 槽；代理相关沿用 `proxyMode` 属性、`setProxyMode` 槽与 `proxyModeChanged` 信号。

**备选**：继续内嵌在 About（已否决：设置与关于混在一起，后续无法自然扩展）；独立网络设置对话框（已否决：入口分散，AI 与网络设置分处两个菜单）。

### 8. 失败语义

- 代理 URL 由系统给出；格式非法时 httpx 在构造 client 阶段抛异常，PRTS 线程的 `run` 既有兜底会把异常转成拉取失败文案，AI 与更新检查由各自既有异常路径上报。
- 不捕获代理错误后改为直连；失败即失败。
- 头像预取沿用 `preload_network_avatar_image` 的「失败只记 warning」语义，不新增用户可见错误。

### 9. 重试只保留一层

- 删除 `utils/net/transport.py::CONNECT_RETRIES`，内层 `AsyncHTTPTransport` / `HTTPTransport` 固定 `retries=0`；`RetryTransport(total=2)` 成为唯一重试层。
- 外层已覆盖内层的重试范围：`httpx_retries.Retry` 默认重试 `TimeoutException`、`NetworkError`（含 `ConnectError`）、`RemoteProtocolError`，并尊重 `Retry-After`、带退避与 jitter。
- 结果：连接失败与 502/503/504 均为「初始 + 2 次」共 3 次尝试；断连场景不再出现 3×3 的嵌套放大。
- **备选**：保留内层重试、收窄外层异常。退避节奏不统一，连接错误拿不到 `Retry-After`，已否决。

### 10. PRTS 非 JSON 响应

- `resolve_enemy_page_title`：`except` 从 `httpx.HTTPError` 扩为 `(httpx.HTTPError, ValueError)`，返回 `(None, str(e))`；调用方本就忽略该错误，随即退回裸名 parse。
- `_fetch_enemy_on_client`：捕获 `_fetch_parse_json` 抛出的 `ValueError`，返回 `{"error": str(e), "error_type": "parse_error"}` 与空 bundle。
- `error_message_for_raw` 增加 `parse_error` 分支，文案为「PRTS 返回内容不是合法 JSON：…」。
- `_fetch_parse_json` 的 `(json, err)` 签名保持不变，现有测试无需改写；`fetch_avatar_imageinfo` 已捕获 `Exception`，不改。
- **备选**：让 `_fetch_parse_json` 返回错误类型三元组。需要改调用点与既有测试，收益相同，已否决。

### 11. PRTS 请求日志

- 三个请求函数各记一条 `logger.debug`：动作（parse / ask / imageinfo）、状态码、耗时；异常路径沿用各自既有返回，不额外刷日志。
- 不用 httpx 事件钩子：钩子拿不到稳定的动作名，且 sync/async 要各写一份；函数内一行计时更直接。
- 级别取 DEBUG，避免正常使用刷屏；代理排障时打开 DEBUG 即可看到每个请求走了哪条链路。

## Risks / Trade-offs

- **环境变量遮蔽系统设置** → `getproxies()` 命中任意 `*_proxy` 环境变量后不再读注册表；某些启动环境（如带 `PI_PROXY`）会选择「无代理」。按 proposal 记录，后续单独优化；切换设置后可立即观察结果。
- **两套解析实现的细微差异** → PRTS 路径用 `getproxies` + `proxy_bypass`，AI/更新检查用 httpx 内部实现。差异主要在 `NO_PROXY` 通配符匹配；用 `proxy_bypass` 这一标准库实现缩小差距，验收时覆盖「命中绕过列表」场景。
- **PRTS 头像多一个连接池** → 每次导入多建一个 `AsyncClient`，用 `async with` 保证关闭；相对渲染开销可忽略。
- **默认值变化影响存量用户** → 之前依赖系统代理访问 AI/更新检查的用户会变为直连。proposal 已声明；错误路径与手动切换可恢复。
- **认证代理返回 407** → 本轮不支持认证代理，AI 侧显示通用 HTTP 407 文案；不额外扩展错误映射。
- **重试层收敛改变失败节奏** → 连接失败的重试间隔改由外层退避统一（0.5s、1s），总尝试次数从最多 9 次降到 3 次；用不可达端口与 MockTransport 各验证一次。
- **新增 `parse_error` 文案** → GUI 走既有 `categorize_error_message`，无需新增界面分支；手工确认错误弹窗能展示该文案。
- **日志只到 DEBUG** → 正常使用无额外输出；排障文档说明开启方式即可。

## Migration Plan

- 无数据迁移：旧 `app_settings.json` 缺字段时 Pydantic 取默认 `none`。
- 回滚：撤掉代码即可；旧版本读取含 `proxy_mode` 的偏好文件不会报错（`extra="ignore"`），字段保留但不生效。
- 发布后首启按直连运行，用户在「关于」中按需开启系统代理。

## Open Questions

无。界面入口与双档语义已在本设计内确定。
