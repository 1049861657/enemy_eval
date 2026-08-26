# 稳定可靠版本计划（2026-08-26）

来源：针对「4 高 + 全局最优」的全仓库调研（官方文档 + 现码对照）。目标是打一版**可长期维护的稳定发布**，不破坏现有功能。

口径修订：尚未发第一版，**直接上目标栈**（httpx / pydantic-settings / platformdirs / structlog / cachetools / ruff），不为「少换依赖」留过渡。仍拒绝的只剩架构会变差的选项（Skia GPU、QtAsyncio preview、orjson）。细节见 [`00-research.md`](./00-research.md)。

本目录只写计划，不改产品代码。执行时按批次独立提交：完成一批后勾选 checkbox，再进下一批。

## 对本产品，「4 高 + 全局最优」指什么

这是**单机 Windows 桌面卡片编辑器**，不是分布式服务。指标必须落到可验收行为。

| 口号 | 本仓库可验收含义 |
|---|---|
| 高质量 | 分层单向、绘制路径唯一、无死符号、无函数体中部 `import`（`QThread.run` 防循环除外）、类型与错误语义一致 |
| 高可用 | 主界面不因 PRTS/渲染卡死；失败可感知；关窗不 `terminate`；PRTS 任务可 `cancel` |
| 高性能 | 预览防抖 + 单渲染线程；Pydantic 核心序列化；httpx 连接池 / 机会性 HTTP/2；技能列表用 Qt 模型 |
| 高稳定 | 滚动日志；QML 加载失败可见；设置写入失败被捕获；渲染是纯函数；HTTP 默认超时 + 状态码重试 |
| 全局最优 | 唯一绘制入口；唯一 HTTP 客户端；偏好 JSON 与敌人 JSON 同构；渲染不读全局设置 |

硬约束（来自 `AGENTS.md`，不可违反）：

- 不破坏现有功能（编辑、预览、导出、PRTS、雷达/记分板、自定义维度）。
- 直接替换，不留兼容层。评价标准从注册表改 JSON 后，**旧注册表偏好不迁移**。
- 不为「检查」堆测试；契约变化处（HTTP 客户端、设置存储）**必须**改现有测试，可加最小夹具。
- 禁止函数体中间 `import`（两个 `run()` 延迟导入 `core` 除外）。
- 不接入遥测。

## 建议执行顺序

`01` 稳定性（先去掉 `terminate`、让失败可见）→ `05` HTTP（httpx + 可取消；让关窗真能打断 PRTS）→ `02` 渲染纯化 → `03` 偏好 JSON → `04` GUI/QML → `06` 工具链。

`01` 必须最先。`05` 提到紧接 `01`：取消能力属于可用性，不是「依赖打扫」。`02` 与 `03` 不可对调。`04` 在 `02`/`03` 之后。`06` 可与 `04` 并行。

## 批次索引

| 批次 | 文件 | 主题 | 优先级 | 状态 |
|---|---|---|---|---|
| 0 | [`00-research.md`](./00-research.md) | 官方文档调研与依赖取舍 | — | 已按「目标栈」修订 |
| 1 | [`01-stability-shutdown-logging.md`](./01-stability-shutdown-logging.md) | 关窗、structlog、QML 失败可见 | P0 | 待执行 |
| 2 | [`02-render-purity.md`](./02-render-purity.md) | `RenderOptions` + 单一绘制路径 | P0 | 待执行 |
| 3 | [`03-settings-errors.md`](./03-settings-errors.md) | pydantic-settings + platformdirs | P0 | 待执行 |
| 4 | [`04-gui-qml.md`](./04-gui-qml.md) | 拆工作区、`model_dump_json`、技能 ListModel | P1 | 待执行 |
| 5 | [`05-deps-prts.md`](./05-deps-prts.md) | **httpx 替换 requests**；去掉未用依赖；文件名消毒 | P0 | 待执行 |
| 6 | [`06-tooling-docs.md`](./06-tooling-docs.md) | ruff；修正 `AGENTS.md` | P2 | 待执行 |

## 依赖取舍（结论先行）

**新增运行时：** `httpx[http2]`、`httpx-retries`、`pydantic-settings`、`platformdirs`、`structlog`、`cachetools`。

**新增开发：** `ruff`。

**移除运行时：** `requests`、`beautifulsoup4`、`pillow`；`numpy` 改为 `skia-python` 传递依赖，不再直接声明。

**明确不加：** orjson、msgspec、tenacity、glfw、Sentry、pytest-httpx（先用 `httpx.MockTransport`）。

本机改依赖后执行 `uv lock` / `uv sync`（**助手勿手改 `uv.lock`**）。

## 发版建议（执行全部批次后，等用户明确要求再 bump）

结构性改动跨 `core`/`gui`/`utils`，按 `AGENTS.md` 倾向 `Y+1`、`Z=0`（例如 `0.4.0`）。AI 不得在未要求时改版本号。
