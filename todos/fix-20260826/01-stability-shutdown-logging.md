# 批次 1：关窗、日志、QML 失败可见

**风险等级**：P0 — 现有失败路径用户看不见或会破坏进程内状态。

**执行状态：待执行。** HTTP 真正可取消在批次 5；本批先禁止 `terminate` 并让日志/QML 失败可见。

## 1.1 禁止 `QThread.terminate`

- [ ] 位置：`gui/render_coordinator.py::cleanup`、`gui/main_window.py::closeEvent`。
- [ ] 只 `requestInterruption()` + `wait(3000)`（最多 5000）。超时 `logger.error`，**不** `terminate`，`event.accept()`。
- [ ] 批次 5 之后补：PRTS 线程在 `run()` 里持有 `asyncio.Task`；`requestInterruption` 被轮询到后 `task.cancel()`。验收改为：拉取中途关窗，3s 内进程退出且无 `terminate`。
- [ ] 验收（本批）：产品代码无 `terminate(`。关窗 3–5s 内返回桌面。

## 1.2 structlog + 滚动文件

- [ ] 本机 `uv add structlog platformdirs`（日志目录用 platformdirs，避免本批再依赖 QStandardPaths；与批次 3 同一路径约定）。
- [ ] 新建 `utils/app_logging.py`：`structlog.stdlib` + `ProcessorFormatter`；`RotatingFileHandler` 写到 `platformdirs.user_log_path("敌人评价卡片编辑器", appauthor="Enemy Eval Team") / "enemy-eval.log"`（`maxBytes=1_000_000`，`backupCount=3`，`encoding="utf-8"`）；开发保留 stderr。
- [ ] `gui_main.py::main` 在 `QApplication` 创建后立刻 `setup_logging()`（CLI `main.py` 同样调用，不依赖 Qt）。
- [ ] `print` 改为 `structlog.get_logger(__name__)`：`core/fonts.py`、`core/optimization.py`（`PerformanceTimer` → debug）、`core/render/sections/avatar.py`、`gui_main.py` 导入失败分支。
- [ ] `sys.excepthook` 与 `threading.excepthook` 写 ERROR + traceback。
- [ ] 验收：跑 GUI 后 log 目录出现文件；缺字体时日志有警告。

## 1.3 QML 加载失败对用户可见

- [ ] `gui/main_window.py::_create_central_widget`：`status() == Error` 收集 `errors()`。
- [ ] 对话框列出 `toString()`；不要把坏 Quick 控件当工作区。推荐对话框后 `QTimer.singleShot(0, QApplication.quit)`。启动失败可用 `QMessageBox`（壳仍是 Widgets）。
- [ ] 验收：改坏一行 QML，启动出现错误文本，不是白屏。
