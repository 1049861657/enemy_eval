# 调研结论（官方文档对照）

本文件只记录证据与取舍，不含 checkbox。实施步骤在 `01`–`06`。

**口径（2026-08-26 修订）：** 尚未发第一版，不为「少换栈」保守。能一次上到官方主路径的，直接上；仍拒绝的，只剩**架构上会变差**的选项（不是怕麻烦）。

## 1. 线程生命周期

出处：[Qt 6.11 `QThread`](https://doc.qt.io/qt-6.11/qthread.html)

- 正常停止：`requestInterruption()` + `wait()`。`terminate()`：**dangerous and discouraged**。
- 现状：`gui/render_coordinator.py:83-86` 与 `gui/main_window.py:241-244` 在 `wait(3000)` 失败后仍 `terminate()`。
- 结论：删除 `terminate`。关窗短 `wait`（3–5s）。HTTP 可取消性见 §6：`asyncio.Task.cancel()` 才能真正打断在途请求；批次 5 落地后，关窗应先 cancel PRTS task，再 wait。

## 2. QML 加载失败与绑定

出处：[Qt 6.11 `QQuickWidget`](https://doc.qt.io/qt-6/qquickwidget.html)、[PySide6 Property](https://doc.qt.io/qtforpython-6/PySide6/QtCore/Property.html)、[Python-QML integration](https://doc.qt.io/qtforpython-6/tutorials/qmlintegration/qmlintegration.html)

- `status() == Error` → `errors()`。现状只打日志仍 `setCentralWidget`（白屏）。
- 结论：Error 弹窗后退出，不进入假编辑态。
- **窗口壳保留 `QMainWindow` + `QQuickWidget`。** 这是 Qt 官方「Widgets 壳嵌 QML」路径；状态栏、启动封面、文件对话框仍是 Widgets。迁 `QQmlApplicationEngine` 是重做壳，不提高可靠性，也不解锁新能力。
- 绑定：官方主路径是 `Property` + `notify`，列表用 `QAbstractListModel`。现状每次改字段 `json.dumps` 整份敌人再 `JSON.parse`，与官方相反。本轮：标量暂仍 JSON（QML 已绑好，40+ 字段全改 Property 收益不成比例）；**技能列表改为 `QAbstractListModel`**（唯一可变长集合）；序列化改 `model_dump_json`。

## 3. 序列化

出处：[Pydantic Serialization](https://docs.pydantic.dev/latest/concepts/serialization/)、[Performance](https://docs.pydantic.dev/latest/concepts/performance/)

- `model_dump_json()` / 模块级 `TypeAdapter.dump_json()` 在 pydantic-core（Rust）一次写成 JSON。
- `json.dumps(model.model_dump())` 官方明确更慢。
- **不加 orjson / msgspec。** 这不是保守：Pydantic 应用的官方快路径就是 pydantic-core。orjson 只加速「已经是 dict」的编码，绕开模型等于丢掉校验。

## 4. 应用偏好存储

出处：[Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)、[`JsonConfigSettingsSource`](https://docs.pydantic.dev/latest/api/pydantic_settings/#pydantic_settings.JsonConfigSettingsSource)、[platformdirs](https://platformdirs.readthedocs.io/en/stable/)

- `QSettings.NativeFormat` 在 Windows = **注册表**，与「配置一律 JSON」冲突。
- **上 `pydantic-settings`：** `AppSettings(BaseSettings)` + `JsonConfigSettingsSource` 读 JSON；这是 Pydantic 官方配置伴侣，以后要加环境变量覆盖不必再换库。写入仍显式 `model_dump_json`（Settings 以加载为主，没有对等的「save()」契约）。
- **上 `platformdirs`：** `user_config_path(appname, appauthor=...)` / `user_log_path`。CLI、测试、日志**不依赖** `QApplication` 或 `QStandardPaths`。Windows：`appauthor="Enemy Eval Team"`、`appname="敌人评价卡片编辑器"` → `%LOCALAPPDATA%\Enemy Eval Team\敌人评价卡片编辑器`（与现 org/app 名对齐）。测试用临时目录注入或 `WIN_PD_OVERRIDE_LOCAL_APPDATA`。
- 渲染层只收 `RenderOptions`，禁止 `import` 设置存储。

## 5. Skia 绘制后端

出处：[skia-python Canvas-Creation](https://github.com/kyamagu/skia-python/blob/main/notebooks/Canvas-Creation.ipynb)

- 现码 `skia.Surface(w, h)` = CPU 栅格。GPU 要调用方提供 GL 上下文，后台 `QThread` + 读回 `QPixmap` 会把加速吃掉，并引入 current-context 约束。
- **保持 CPU 栅格。** 这不是怕麻烦，是后端与「后台线程出 PNG/QPixmap」的产品形态不匹配。

## 6. HTTP 客户端（修订：上 httpx，去掉 requests）

出处：

- [HTTPX](https://www.python-httpx.org/)（自称 next-generation；sync + async；默认超时；全类型）
- [Timeouts](https://www.python-httpx.org/advanced/timeouts/)：默认 5s 全局限；用 `httpx.Timeout(connect=..., read=...)` 分项
- [HTTP/2](https://www.python-httpx.org/http2/)：`httpx[http2]` + `http2=True`；服务端不支持则回落 1.1。官方注明 1.1 实现目前更「battle-hardened」，故 **安装 http2 extra 并开启**（机会性升级 + 自动回落），把 `response.http_version` 打 DEBUG
- [Transports](https://www.python-httpx.org/advanced/transports/)：`HTTPTransport(retries=n)` **只**重试 `ConnectError` / `ConnectTimeout`。状态码 503 等，官方原文：*consider general-purpose tools such as tenacity*
- [httpx-retries](https://github.com/will-ockmore/httpx-retries)：Transport 层、API 对齐 urllib3 `Retry`，默认可重试 429/502/503/504，**同步与 AsyncClient 同一套**。比在每个 `get` 外包 tenacity 更贴 HTTP、也更接近现码 `urllib3.util.retry.Retry`

**选定栈：**

| 层 | 选择 | 不选 |
|---|---|---|
| 客户端 | `httpx[http2]` `AsyncClient` | `requests`（无 async、无默认超时、无 H2、无一流类型） |
| 连接重试 | `AsyncHTTPTransport(retries=2, http2=True)` | — |
| 状态码重试 | `httpx_retries.RetryTransport` + `Retry(total=2, backoff_factor=0.5, status_forcelist=(502,503,504))` | 每个调用手写 tenacity（HTTP 策略应挂在 Client 上，而不是散落） |
| 超时 | parse `read=22`、imageinfo `read=12`、resolve `read=4`、connect 统一短（如 5s） | 无超时 / 单一 5s 默认（parse 会被误杀） |
| 头像下载 | 同一 Client（替换 `urllib.request.urlopen`） | 第三套 HTTP 栈 |
| 事件循环 | `PrtsFetchThread.run` 内 `asyncio.run(...)` | `PySide6.QtAsyncio`（[官方仍标 technical preview](https://doc.qt.io/qtforpython-6/PySide6/QtAsyncio/index.html)，不能当稳定版底座） |
| 测试 | `httpx.MockTransport`（库内自带） | 再加 pytest-httpx，除非现有测试写不动 |

**为何必须 async（不是为了炫）：**

- 现 `requests.get` **无法**被 `QThread.requestInterruption()` 打断。关窗只能放弃或 `terminate`。
- `asyncio.Task.cancel()` 在 await 点注入 `CancelledError`，httpx 会关连接。关窗：cancel task → `aclose()` → 短 wait。这是 HTTP 侧「高可用」的真正解。
- 当前流水线仍是 resolve → parse → imageinfo（后一步依赖前一步），**不必** `gather` 这三步。async 的现值是取消 + 连接池 + 以后独立请求可 `gather`（例如多敌人、额外 API）。
- GUI 线程不跑 asyncio（避免 QtAsyncio preview）。渲染仍 CPU Skia + `QThread`。PRTS 只在自己的线程里 `asyncio.run`。

`build_session()` 改为 `build_async_client()`（或同步 `build_client()` 给 smoke 脚本；脚本可用 `httpx.Client` 同步 API，同一套 Transport/Timeout/Headers）。删除 `requests` 依赖。

## 7. 日志

出处：[logging.handlers.RotatingFileHandler](https://docs.python.org/3/library/logging.handlers.html)、[structlog](https://www.structlog.org/)（`stdlib` 集成 / `ProcessorFormatter`）

- windowed 下 `print` 消失。必须有文件日志。
- **上 structlog，sink 仍是 stdlib。** 官方集成路径：`LoggerFactory` + `ProcessorFormatter` → `RotatingFileHandler`（`platformdirs.user_log_path`）+ 开发时 stderr。以后要 JSON 行、按请求绑 `enemy_name`，只加 processor，不换库。
- `sys.excepthook` / `threading.excepthook` 走同一套。`PerformanceTimer` → `logger.debug`。
- 不加遥测后端。

## 8. 缓存

出处：[cachetools](https://cachetools.readthedocs.io/) `LRUCache`、[functools.lru_cache](https://docs.python.org/3/library/functools.html#functools.lru_cache)

- `lru_cache` 只适合纯函数。`skia.Image` 按 URL 缓存要用可变映射。
- **上 `cachetools.LRUCache`** 替换手写 `OrderedDict` LRU（`maxsize=image_cache_size`）。并发仍用现有锁（cachetools 文档不保证线程安全）。文本布局已有时间戳 TTL，保持。

## 9. 质量工具

原计划加 Ruff。执行时去掉：改代码走 AI，未接编辑器诊断闭环，单独加依赖无收益。

## 10. 明确不做（架构会变差，不是怕换库）

| 候选 | 原因 |
|---|---|
| Skia GPU / glfw | 与后台线程出图形态冲突 |
| `PySide6.QtAsyncio` | 官方 technical preview |
| orjson / msgspec | 与 Pydantic 官方序列化路径重复且更差 |
| tenacity（HTTP 层） | 与 Client 级 `RetryTransport` 重复；非 HTTP 重试本产品用不到 |
| 全 QML `ApplicationWindow` | 重做壳，不提高 4 高 |
| 遥测 | 已否决 |
| 真实 PRTS wikitext 回归集 | `fix-20260706` 批次 3 已明确不做 |

## 11. 现码锚点（2026-08-26 核对）

| 事实 | 位置 |
|---|---|
| `QThread.terminate()` | `gui/render_coordinator.py:85`、`gui/main_window.py:243` |
| QML Error 仅日志 | `gui/main_window.py:77-80` |
| 绘制双路径 | `core/render/generator.py` `generate_card` / `generate_card_image` |
| 渲染读 Qt 偏好 | `generator.py:10`、`rating_grade.py:10` |
| `QSettings.NativeFormat` | `utils/rating_schema_store.py:23-30` |
| HTTP = `requests` + urllib3 `Retry` | `utils/prts_api_client.py` |
| 头像下载 = 第三套 `urlopen` | `utils/network_image.py:44` |
| `updateRatingSchema` 不捕获保存失败 | `gui/qml_bridge.py:197-207` |
| `error_handler` 对 UI 丢 `str(e)` | `utils/error_handler.py:46-49` |
| `print` 在 windowed 下消失 | `core/fonts.py`、`core/optimization.py`、`avatar.py` |
| `Workspace.qml` | 891 行 |
| 未用直接依赖 | `pillow`、`beautifulsoup4` |
