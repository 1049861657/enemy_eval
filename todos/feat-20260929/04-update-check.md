# 任务 04：启动时版本检查提示

**优先级**：P2　**状态**：已实现，待验收　**依赖**：建议在任务 02 之后（同改 `AppSettings`）

**影响文件**：新增 `utils/update_checker.py`、`gui/qml/AboutDialog.qml`；改 `utils/thread_manager.py`、`utils/app_settings_store.py`、`gui/main_window.py`、`gui/qml_bridge.py`、`gui/qml/Workspace.qml`、`gui/qml/CommandBar.qml`

## 目标

启动后先显示偏好里已经记下的新版本，再按冷却决定是否问一次 GitHub。有更高正式版时用**应用内非阻塞横幅**提示，并可打开 Releases 页。自动检查失败不弹窗、不占用 24 小时冷却。用户可在关于窗口关闭自动检查。手动检查放在「更多」菜单。**不做自更新、不下载资产、不接遥测。**

## 现状与内部锚点

| 事实 | 锚点 |
|---|---|
| 启动序列：依赖检查 → `QQuickStyle` → `QApplication` → 日志 → 启动画面 → 主窗口 → `QTimer.singleShot(1500)` 显窗 → `app.exec` | `gui_main.py:91`、`:98`、`:102`、`:108`、`:114`、`:121`、`:124` |
| 版本来源：安装元数据 → `build_info.json` → `pyproject.toml`；构建时间仅打包制品有 | `utils/app_version.py:22`、`:46` |
| 关于是纯文本对话框，没有按钮和开关 | `gui/main_window.py::_show_about:268`（桥接 `aboutRequested`） |
| 「更多」是一次性命令：刷新预览、重置数据、关于、退出 | `gui/qml/CommandBar.qml:183-194` |
| 异步线程范式（信号 + `deleteLater` 收口）。`run` 内延迟导入只用于打破 `core` 环 | `utils/thread_manager.py::PrtsFetchThread:84`、`NetworkAvatarPrefetchThread:146` |
| 关窗统一收线程（`requestInterruption` + `wait(3000)`，绝不 `terminate`） | `gui/main_window.py::closeEvent:317` |
| 偏好读写（容错 + 缓存） | `utils/app_settings_store.py::AppSettings:63`、`_read_settings:98`、`_persist:112` |
| 非阻塞提示通道（toast）与动作信号 | `gui/qml_bridge.py:56-78`（信号）、`:208`（`show_toast`） |
| 错误分类文案 | `utils/error_handler.py::categorize_error_message:48` |
| 远端 | `origin = https://github.com/1049861657/enemy_eval.git` |

## 外部调研与出处

- **`releases/latest` 的确切语义**：返回最近一个**非 draft、非 prerelease** 的已发布 release；按 `created_at`（打 tag 的提交时间）排序；若不存在则 **404**。响应含 `tag_name`、`html_url`、`prerelease`、`published_at`、`assets[]`。**本仓库当前尚无 release → 404 是预期状态，必须当「暂无新版本」处理，不能当错误重试。**
  <https://docs.github.com/en/rest/releases/releases#get-the-latest-release>
- **必须带 `User-Agent`**：缺失会被直接拒绝（无效则 403）。
  <https://docs.github.com/en/rest/using-the-rest-api/getting-started-with-the-rest-api#user-agent>
- **限流与条件请求**：匿名 60 次/小时按 IP 计；超限返回 403/429，可用 `retry-after` 或 `x-ratelimit-remaining: 0` + `x-ratelimit-reset` 退避。GitHub 建议带 `ETag` / `If-None-Match`：资源未变时返回 `304`，响应体为空。**只有请求正确带了 `Authorization` 时，`304` 才不计入主限额**；匿名 `304` 仍扣次数。本任务仍发送条件请求，因为这是缓存校验的正道，以后若有令牌，同一条请求立刻开始省次数。现在不放令牌，所以 24 小时冷却继续负责限额，不指望 `304` 省配额。
  <https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api>、<https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api#use-conditional-requests>
- **SemVer 比较规则（官方）**：`MAJOR.MINOR.PATCH` 为非负整数（禁前导零），按数值比较；同号下**预发布版优先级低于正式版**；`+build` 元数据忽略；`v1.2.3` 的前缀 `v` 不是版本的一部分，需先剥离。官方提供正则可用于解析。
  <https://semver.org/>
- **静默检查的主流口径**：Electron 官方更新器默认启动即查、可通过 `notifyUser` 关闭、提供停止接口；即「默认开启 + 显式可关」是主流实践；失败不应打扰用户。
  <https://www.electronjs.org/docs/latest/tutorial/updates>
- **系统托盘气泡不可靠**：Qt 官方明确 `QSystemTrayIcon::showMessage` 受系统配置影响**可能根本不显示**，不应作为关键信息的唯一通道；且它属 Widgets 侧。→ 用应用内横幅。
  <https://doc.qt.io/qt-6/qsystemtrayicon.html#showMessage>
- **打开外部链接**：QML 用 `Qt.openUrlExternally(url)`（返回 `true` 仅代表「已请求系统打开」）。
  <https://doc.qt.io/qt-6/qml-qtqml-qt.html#openUrlExternally-method>

## 设计

一次启动里，显示横幅和访问网络是两件事。横幅来自偏好里记下的版本，不依赖这次请求是否发出。网络请求只负责刷新这份记录。

### 1. `utils/update_checker.py`（非 Qt）

单独的短生命周期 `httpx.Client`。不复用 `utils/prts_api_client.py`：标识、超时、重试策略都不同。

```
API_URL = "https://api.github.com/repos/1049861657/enemy_eval/releases/latest"
RELEASES_PAGE = "https://github.com/1049861657/enemy_eval/releases/latest"

@dataclass(frozen=True)
class CheckResult:
    outcome: Literal["update", "current", "unchanged", "none", "error"]
    tag: str = ""          # 200 时为 tag_name；304 为空，调用方沿用上次见到的版本
    url: str = ""
    etag: str = ""         # 200 时为响应的 ETag；304 / 失败为空，调用方保留旧值
    retry_at: float = 0.0  # 限流时由响应给出的 Unix 时间；0 表示调用方自定退避

def parse_semver(text: str) -> tuple[int, int, int, int] | None   # 官方正则；剥 v 前缀；预发布返回更低的一段
def is_newer(local: str, remote: str) -> bool                     # 任一侧不可解析 → False
def fetch_latest(etag: str) -> CheckResult
    # etag 非空时带 If-None-Match
    # 自己构造并关闭 Client
    # User-Agent: EnemyEval/<get_app_version()>
    # Accept: application/vnd.github+json
    # 不挂 RetryTransport，不带 Authorization
    # 超时：httpx.Timeout(connect=3, read=5, write=5, pool=5)
```

- `200`：解析 `tag_name`、`html_url`，带回响应 `ETag`。`is_newer` 为真 → `update`，否则 → `current`。
- `304` → `unchanged`。没有正文，不表示「已经是最新」，只表示远端和上次 `200` 时相同。
- `404` → `none`。
- `403` / `429` → `error`，`retry_at` 取 `retry-after`（秒数加现在）或 `x-ratelimit-reset`（Unix 时间）。两者都没有则 `retry_at = 0`。
- 其它状态码或任何异常 → `error`，`retry_at = 0`，只记 `logger.debug`。不改已存的 ETag。

### 2. 偏好字段（`AppSettings`）

```
update_check_enabled: bool = True
update_check_last_ts: float = 0.0       # 只在问到明确结果时写入（update / current / unchanged / none）
update_check_block_until: float = 0.0   # 失败退避截止
update_check_etag: str = ""             # 上次 200 的 ETag；空则下次不带 If-None-Match
update_seen_tag: str = ""               # 上次 200 见到的正式版，不论是否比本地新
update_seen_url: str = ""
update_check_skip_tag: str = ""         # 「忽略此版本」
```

横幅不单独存一份。是否显示由 `update_seen_tag` 推出来：比本地新，且不等于忽略版本。`304` 没有正文，没有这份记录就无法在「远端没变、本地已经升级」时把横幅收掉。

写入沿用 `_persist()`；失败不影响启动（既有语义：`FileOperationError`）。

辅助写入口：`set_update_check_enabled`、`mark_update_checked`、`set_update_block_until`、`set_update_seen`（tag、url、etag 一起写）、`clear_update_seen`（404 时清掉 tag、url、etag）、`set_update_skip_tag`。忽略版本只写 skip，不清 `update_seen_*`。

### 3. 线程（`utils/thread_manager.py`）

`UpdateCheckThread(QThread)`。`utils.update_checker` 在文件顶部导入（它不导入 `core`，不构成环）。

- 构造时传入当前 `update_check_etag`。信号：`checkFinished(str outcome, str tag, str url, str etag, float retryAt)`。
- `run()` 调用 `fetch_latest(etag)`。线程不写偏好。
- 生命周期与既有线程一致：`deleteLater`、关窗 `requestInterruption` + `wait`。同一次运行只允许一个在飞请求。

### 4. 触发与结果（`gui/main_window.py`）

`__init__` 末：`QTimer.singleShot(3000, self._maybe_check_updates)`。放在主窗口，以便随窗口收线程。

**先显示，再决定要不要问：**

1. `update_seen_tag` 比本地新，且不等于 `update_check_skip_tag` → 立刻显示横幅。否则不显示。不删已见版本和 ETag。
2. 同时满足下面三条才启动线程：`update_check_enabled`；`last_ts` 为 0、早于现在 24 小时、或晚于现在（时钟回拨视为冷却已过）；`now >= block_until`。写入退避时，若截止时间晚于现在 24 小时以上，封顶为现在 + 24 小时。

**结果：**

| 结果 | `last_ts` | 记下的版本与 ETag | 横幅 |
|---|---|---|---|
| `update` 或 `current`（有正文的 `200`） | 写成现在 | 换成这次的 tag、url、ETag | 按新记下的版本重算 |
| `unchanged`（`304`） | 写成现在 | 保持不变。若 ETag 在而 `update_seen_tag` 为空，丢掉 ETag，下次要完整正文 | 按已记下的版本和当前本地版本重算 |
| `none`（`404`） | 写成现在 | 清掉 tag、url、ETag | 关掉 |
| `error`，`retry_at` 在未来 | 不改 | 不改 | 保持。退避到 `min(retry_at, 现在+24h)` |
| `error`，没有可用的 `retry_at` | 不改 | 不改 | 保持。退避 30 分钟 |

自动检查的 `error` / `current` / `unchanged` / `none` 不弹窗。手动检查的提示见下一节。

### 5. 入口

- **手动检查**放在「更多」，菜单项「检查更新」，排在「关于」上面（`CommandBar.qml`）。它是一次性命令，和刷新预览、重置数据同类。忽略开关、24 小时冷却和退避；仍遵守「同时只有一个请求」。结果：有更新走横幅；`current` / `unchanged` / `none` 用 toast「已是最新版本」；`error` 用 toast「暂时无法检查更新」。
- **自动检查开关**不放进「更多」。关于从纯文本对话框改为小窗口 `AboutDialog.qml`：保留现有版本、构建日期和简介，加「启动时自动检查」开关，写入 `update_check_enabled`。这个窗口里没有「检查更新」按钮。

### 6. 横幅（`Workspace.qml`）

顶部非阻塞横幅。是否可见由桥接按 `update_seen_tag` 算好后交给界面，文案「发现新版本 vX.Y.Z」。按钮「查看」→ `Qt.openUrlExternally(url)`；「忽略此版本」→ 只写入 `update_check_skip_tag`。不用系统托盘气泡。

`gui/qml_bridge.py`：Property 暴露横幅标签、链接和 `updateCheckEnabled`；槽 `requestCheckUpdates()`、`dismissUpdate(str tag)`、`setUpdateCheckEnabled(bool)`。连接写在 `__init__`。

## 步骤

- [x] 新增 `utils/update_checker.py`（解析、比较、请求、结果类型；自建 `httpx.Client`；无 Qt）。
- [x] `utils/thread_manager.py` 加 `UpdateCheckThread`（顶部导入 `utils.update_checker`；信号拆成基元；不写偏好）。
- [x] `AppSettings` 加七个字段；`utils/app_settings_store.py` 加第 2 节的写入口。
- [x] `gui/main_window.py`：3 秒触发；先显示已记下的横幅再按冷却请求；按第 4 节处理结果；`closeEvent` 收线程。
- [x] `gui/qml/CommandBar.qml`：「更多」里「检查更新」放在「关于」上面。
- [x] `gui/qml/AboutDialog.qml`：版本、构建日期、简介、「启动时自动检查」开关。关于由 `aboutRequested` 打开该窗口。
- [x] `gui/qml_bridge.py`：横幅标签、链接、开关 Property，三个槽；连接写在 `__init__`。
- [x] `gui/qml/Workspace.qml`：顶部横幅。

## 非目标

- 不做自更新、不做资产下载、不做强制升级、不做灰度/遥测。
- 不内嵌任何 GitHub 令牌。ETag 只做条件请求，不代替 24 小时冷却。
- 不做 beta/prerelease 通道（`latest` 天然排除 prerelease；将来要 beta 只换请求地址，结果类型和横幅不动）。
- 不把更新检查做成常驻轮询。
- 不复用 PRTS 的 HTTP 客户端。
- 不把「检查更新」放进关于，也不把自动检查开关放进「更多」。

## 风险与回滚

| 风险 | 处置 |
|---|---|
| 匿名限流（60/h，NAT 下共享） | 明确结果才进入 24h 冷却；403/429 退避到响应时间并封顶 24h。匿名 `304` 仍计次，不靠 ETag 省配额 |
| 启动时断网 | 不改 `last_ts`，退避 30 分钟；已有横幅保留；自动检查不弹窗 |
| 看到横幅后直接关掉软件 | 已见版本在偏好里，下次启动立刻再显示，不必再等 24h |
| 远端未变但本地已升级 | `304` 用已见版本和当前本地版本重算，横幅收掉 |
| 当前仓库无 release（404） | `none`：不提示，写入 `last_ts`，不按错误重试 |
| 版本号含预发布或自定义 tag | 解析失败视为没有更新 |
| 时钟回拨或重置时间异常 | `last_ts` 晚于现在则冷却视为已过；退避最长 24h |
| 隐私 | 只带 `User-Agent`；关于窗口可关自动检查；关掉后启动不发请求 |
| 回滚 | 移除线程、菜单项、关于窗口和横幅即可；多出的偏好字段对旧逻辑无副作用 |

## 验收

1. 本地版本低于远端正式版 → 启动约 3 秒后出现「发现新版本」横幅；「查看」打开 Releases 页；「忽略此版本」后重启不再提示该版本。
2. 横幅出现后不点忽略、直接退出 → 24 小时内再次启动，横幅立刻出现，且这次不必等到网络返回。
3. 用户已换成不低于已见版本的版本 → 启动时横幅消失。已见版本和 ETag 仍留着，供下次条件请求使用。
4. 仓库无 release（404）→ 无提示、无错误弹窗；这次算明确结果，进入 24 小时冷却。
5. 断网启动 → 无错误弹窗，日志仅 `debug`；`last_ts` 和 ETag 都不变；约 30 分钟内再次启动不会自动请求。若已见版本仍比本地新，横幅仍在。
6. 已有 ETag 时再次检查，请求带 `If-None-Match`。远端未变得到 `304`：已见版本保留；本地若已不低于该版本，横幅收掉。
7. 关于窗口关闭「启动时自动检查」→ 重启后无自动请求。「更多 → 检查更新」仍可发请求。已是最新时 toast「已是最新版本」；失败时 toast「暂时无法检查更新」。
8. `uv run --no-sync pytest -q` 全绿（偏好新字段不破坏既有 roundtrip 契约）。
