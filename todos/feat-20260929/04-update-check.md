# 任务 04：启动时版本检查提示

**优先级**：P2　**状态**：未开始　**依赖**：建议在任务 02 之后（同改 `AppSettings`）

**影响文件**：新增 `utils/update_checker.py`、`utils/thread_manager.py`（新增线程类）、`utils/app_settings_store.py`、`gui/main_window.py`、`gui/qml_bridge.py`、`gui/qml/Workspace.qml`

## 目标

启动后延迟一次静默检查远端最新版本；有更高版本时以**应用内非阻塞横幅**提示并可跳转 Releases 页；一切失败静默；用户可关闭该检查；**不做自更新、不下载资产、不接遥测**。

## 现状与内部锚点

| 事实 | 锚点 |
|---|---|
| 启动序列：依赖检查 → `QQuickStyle` → `QApplication` → 日志 → 启动画面 → 主窗口 → `QTimer.singleShot(1500)` 显窗 → `app.exec` | `gui_main.py:51`、`:99`、`:102-106`、`:109`、`:114`、`:121`、`:124` |
| 版本来源：安装元数据 → `build_info.json` → `pyproject.toml` | `utils/app_version.py:22`（另有 `:46` 构建时间） |
| About 对话框落点 | `gui/main_window.py::_show_about:232`（桥接信号 `aboutRequested`） |
| 异步线程范式（信号 + `run` 内延迟导入 + `deleteLater` 收口） | `utils/thread_manager.py::PrtsFetchThread:84`、`NetworkAvatarPrefetchThread:146` |
| 关窗统一收线程（`requestInterruption` + `wait(3000)`，绝不 `terminate`） | `gui/main_window.py::closeEvent:281` |
| 偏好读写（容错 + 缓存） | `utils/app_settings_store.py::AppSettings:61`、`_persist:109`、`_read_settings:95` |
| 非阻塞提示通道（toast）与动作信号 | `gui/qml_bridge.py:171`（`show_toast`）、`:54-70`（信号） |
| 错误分类文案 | `utils/error_handler.py::categorize_error_message:48` |
| 远端 | `origin = https://github.com/1049861657/enemy_eval.git` |

## 外部调研与出处

- **`releases/latest` 的确切语义**：返回最近一个**非 draft、非 prerelease** 的已发布 release；按 `created_at`（打 tag 的提交时间）排序；若不存在则 **404**。响应含 `tag_name`、`html_url`、`prerelease`、`published_at`、`assets[]`。**本仓库当前尚无 release → 404 是预期状态，必须当"暂无新版本"处理，不能当错误重试。**
  <https://docs.github.com/en/rest/releases/releases#get-the-latest-release>
- **必须带 `User-Agent`**：缺失会被直接拒绝（无效则 403）。
  <https://docs.github.com/en/rest/using-the-rest-api/getting-started-with-the-rest-api#user-agent>
- **限流与条件请求**：匿名 60 次/小时按 IP 计；超限返回 403/429，可用 `retry-after` 或 `x-ratelimit-remaining: 0` + `x-ratelimit-reset` 退避；`ETag` + `If-None-Match` 可返回 304，但**只有正确携带 `Authorization` 时 304 才不计配额**——匿名场景下 304 仍消耗配额，因此"每次启动都条件请求"并不能省额度，必须靠时间冷却。
  <https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api>、<https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api#use-conditional-requests>
- **SemVer 比较规则（官方）**：`MAJOR.MINOR.PATCH` 为非负整数（禁前导零），按数值比较；同号下**预发布版优先级低于正式版**；`+build` 元数据忽略；`v1.2.3` 的前缀 `v` 不是版本的一部分，需先剥离。官方提供正则可用于解析。
  <https://semver.org/>
- **静默检查的主流口径**：Electron 官方更新器默认启动即查、可通过 `notifyUser` 关闭、提供停止接口；即"默认开启 + 显式可关"是主流实践；失败不应打扰用户。
  <https://www.electronjs.org/docs/latest/tutorial/updates>
- **系统托盘气泡不可靠**：Qt 官方明确 `QSystemTrayIcon::showMessage` 受系统配置影响**可能根本不显示**，不应作为关键信息的唯一通道；且它属 Widgets 侧。→ 用应用内横幅。
  <https://doc.qt.io/qt-6/qsystemtrayicon.html#showMessage>
- **打开外部链接**：C++/Python 用 `QDesktopServices.openUrl(QUrl)`；QML 用 `Qt.openUrlExternally(url)`（返回 `true` 仅代表"已请求系统打开"）。
  <https://doc.qt.io/qt-6/qdesktopservices.html#openUrl>、<https://doc.qt.io/qt-6/qml-qtqml-qt.html#openUrlExternally-method>

## 设计

### 1. `utils/update_checker.py`（非 Qt）

```
API_URL = "https://api.github.com/repos/1049861657/enemy_eval/releases/latest"
RELEASES_PAGE = "https://github.com/1049861657/enemy_eval/releases/latest"

@dataclass(frozen=True)
class CheckResult:
    outcome: Literal["update", "current", "none", "error"]   # none = 404（尚无 release）
    tag: str = ""
    url: str = ""

def parse_semver(text: str) -> tuple[int, int, int, int] | None   # 官方正则；剥 v 前缀；预发布返回 -1 段
def is_newer(local: str, remote: str) -> bool                     # 任一侧不可解析 → False（静默）
def fetch_latest(client: httpx.Client, *, etag: str | None) -> tuple[CheckResult, str | None]
    # 请求头：User-Agent: EnemyEval/<版本>、Accept: application/vnd.github+json
    # 不挂 RetryTransport（重试会放大配额消耗）
    # 超时：httpx.Timeout(connect=3, read=5, write=5, pool=5)（四参数写全）
```

- 响应处置：`200` → 解析并比较；`304` → 视为"无变化"；`404` → `none`（尚无 release）；`403/429` → `error` 并回传 `x-ratelimit-reset`；其它 → `error`。
- 任何异常 → `error`，只记 `logger.debug`。

### 2. 偏好字段（`AppSettings`）

```
update_check_enabled: bool = True        # 用户开关
update_check_last_ts: float = 0.0        # 上次检查时间（冷却 24h）
update_check_etag: str = ""
update_check_skip_tag: str = ""          # 用户选择"忽略此版本"
update_check_block_until: float = 0.0    # 限流退避（来自 x-ratelimit-reset）
```

写入沿用 `_persist()`；失败不影响启动（既有语义：`FileOperationError`）。

### 3. 线程（`utils/thread_manager.py`）

`UpdateCheckThread(QThread)`，照抄 `PrtsFetchThread` 范式：

- 信号：`checkFinished(str tag, str url, str outcome)`（Qt 信号不支持自定义 dataclass，拆成基元）；
- `run()` 内构造 `httpx.Client`（复用 `utils/prts_api_client.py` 的构建器，改用短超时版本）并调用 `fetch_latest`；**不挂 retry**；
- 生命周期与既有线程一致：`deleteLater`、关窗 `requestInterruption` + `wait`。

### 4. 触发与节流（`gui/main_window.py`）

- `__init__` 末：`QTimer.singleShot(3000, self._maybe_check_updates)`（放在主窗口而非 `gui_main`，以便随窗口生命周期收线程，并复用 `closeEvent` 的收尾约定）。
- `_maybe_check_updates()` 前置条件全部满足才启动线程：
  1. `update_check_enabled`；
  2. `now - update_check_last_ts >= 24h`；
  3. `now >= update_check_block_until`。
- 结果处理：`update` 且 `tag != update_check_skip_tag` → 桥接信号提示；`error` 且带限流时间 → 写 `update_check_block_until`；任何情况都更新 `update_check_last_ts`。
- About（`_show_about:232`）增加：当前版本、构建时间、"检查更新"按钮（手动触发，忽略冷却与开关）、以及"启动时自动检查"开关（写 `update_check_enabled`）。

### 5. UI

- `gui/qml_bridge.py`：信号 `updateAvailable(str tag, str url)`；槽 `@Slot() requestCheckUpdates()`（手动）、`@Slot(str) dismissUpdate(str tag)`；Property `updateCheckEnabled`（读写开关）。
- `gui/qml/Workspace.qml`：顶部非阻塞横幅（`visible: controller.updateAvailableTag !== ""`），文案「发现新版本 vX.Y.Z」+ 按钮「查看」→ `Qt.openUrlExternally(url)`、「忽略此版本」→ `dismissUpdate(tag)`。
- 不使用系统托盘气泡（见出处：可能不显示）。

## 步骤

- [ ] 新增 `utils/update_checker.py`（解析、比较、请求、结果类型；无 Qt 依赖）。
- [ ] `utils/thread_manager.py` 加 `UpdateCheckThread`（复刻 `PrtsFetchThread` 结构；`run` 内导入 `httpx` 与 `utils.update_checker`）。
- [ ] `AppSettings` 加五个字段；`utils/app_settings_store.py` 加读写辅助（`mark_update_checked`、`set_update_block_until`、`set_skip_tag`、`set_update_check_enabled`）。
- [ ] `gui/main_window.py`：`QTimer.singleShot(3000, ...)` 触发；结果处理与节流；About 加版本/构建时间/按钮/开关；`closeEvent` 收线程。
- [ ] `gui/qml_bridge.py`：信号 + 两个槽 + 开关 Property（连接写在 `__init__`）。
- [ ] `gui/qml/Workspace.qml`：顶部横幅。

## 非目标

- 不做自更新、不做资产下载、不做强制升级、不做灰度/遥测。
- 不内嵌任何 GitHub token（客户端密钥泄露面）。
- 不做 beta/prerelease 通道（`latest` 天然排除 prerelease；将来要 beta 再走 `/releases` 列表）。
- 不把更新检查做成常驻轮询。

## 风险与回滚

| 风险 | 处置 |
|---|---|
| 匿名限流（60/h，NAT 下共享） | 24h 冷却 + 403/429 退避到 `x-ratelimit-reset` + 失败静默 |
| 当前仓库无 release（404） | 视为 `none`，不提示、不重试 |
| 网络不可达/被墙 | 短超时静默失败，启动不受影响 |
| 版本号含预发布/自定义 tag | 解析失败即静默跳过，不误报 |
| 隐私顾虑 | 只带 `User-Agent`，无标识；可在 About 关闭 |
| 回滚 | 移除线程与触发调用即可；偏好多出的字段对旧逻辑无副作用 |

## 验收

1. 把本地版本临时改低（或在 `pyproject.toml` 里改小版本后运行源码），且远端已有更高 release → 启动约 3 秒后出现「发现新版本」横幅；点「查看」打开 Releases 页；点「忽略此版本」后重新启动不再提示。
2. 当前仓库无 release（404）→ 无任何提示、无错误弹窗、无重试。
3. 断网启动 → 无提示、无错误弹窗；日志仅 `debug` 级记录。
4. 关闭「启动时自动检查」→ 重启后无网络请求（可用日志或代理观察）；About 里的「检查更新」按钮仍可用。
5. `uv run --no-sync pytest -q` 全绿（偏好新字段不破坏既有 roundtrip 契约）。
