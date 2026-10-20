# 00 总览

## 目标

1. 目录与文件命名**名副其实**：包名/模块名能预测内容，同义概念不撞名，流程叙事不进名字。
2. 职责不堆叠：单文件超过「一类职责」，或同时服务多个领域的，拆开。
3. 跨层错位归位：只服务某一层的逻辑放回该层，减少反向与旁路依赖。
4. 注释与 docstring 改成**契约**（输入/输出/不变量/单位/边界/副作用/线程安全），任何 AI 只读文件即可判断能不能用、怎么用、何时会炸。
5. 性能：只做有测量证据的改动；无证据不动。

## 非目标

- 不改 `models/`（7 文件 275 行、零项目内依赖、职责单一，本次唯一"零改动"包）。
- 不改任何用户可感知行为：界面文案、交互、配置 JSON 形状、偏好字段名、渲染像素结果、导出文件名规则。
- 不换技术栈（不引 HTML/CSS 渲染、不改 Skia、不改 Qt 版本、不改 QML 控件风格）。
- 不新增测试用例（铁律 1）；只允许在拆分导致**已有测试的导入路径失效**时同步改路径。
- 不做"顺手"的功能增强、参数校验增强、日志增强。
- 不做「字段声明集中化」（每个 `EnemyData` 字段在 prod 侧散落 5~7 处）：收益真实，但要同时改 QML 编辑页、PRTS 映射表与 AI 白名单，属结构 + 行为边界改动；本计划只保留证据，另立项。

## 审计基线（本次实测，作为"改前"快照）

| 项 | 数值 | 来源 |
|---|---|---|
| 代码规模 | 68 个 `.py` / 10241 行；QML 28 文件 / 4687 行 + 15 个 svg | 全仓库统计（排除 `.venv`/`build`/`dist`） |
| 包规模 | `utils` 22/3279；`core` 15/2434；`gui` 8/1806（+QML）；`tests` 11/1569；`scripts` 3/633；`models` 7/275 | 同上 |
| 依赖方向 | 无环；`utils→core` 仅 3 处函数内导入（`utils/thread_manager.py:36,118,201`）；`core→utils` 7 条模块级边 | AST 导入图 |
| `utils` 增长 | 最近 60 次提交改动 `utils/` 108 次 / 26 个文件；2025-08 以来新增约 20 个模块，其间两次改名（`prts_scraper→prts_integration→prts_mediawiki_pipeline`、`wiki_skia→wiki_span_parser`） | `git log --name-only` |
| 最大文件 | `gui/qml_bridge.py` 657；`gui/main_window.py` 553；`utils/wiki_span_parser.py` 470；`core/optimization.py` 402；`utils/app_settings_store.py` 391 | 行数 |
| 抓杂货铺 | `core/optimization.py` 6 个互不相关顶层概念；`utils/app_settings_store.py` 33 个顶层符号 5 类职责；`qml_bridge.py` 36 信号 + 26 属性 + 36 slot + 86 def | AST |
| 真死代码 | `gui/card_model.py::update_skill`（:122）、`get_current_dict`（:242）全仓库零引用（含 QML） | 名称引用计数 |
| 字段散落 | 每个 `EnemyData` 业务字段在 prod 侧被 5~7 个文件硬编码（QML 编辑页 + `prts_field_mapping` + `prts_enemy_builder` + `ai_client` 白名单 + `ai_baseline`） | 字符串检索 |
| 测试覆盖 | 25/46 模块被 `tests/` 引用；缺口集中在 `core/render/sections/*`、`gui/skill_list_model`、`utils/ai_*` | 名称检索 |
| 工程配置 | `pyproject.toml` 无 `[build-system]`、无 `[project.scripts]`、无任何 `[tool.*]` | 文件内容 |
| 打包入口 | `enemyEval.spec`（camelCase，仓库其余文件 snake_case/PascalCase）；`hiddenimports` 含 `core.render.generator`、`core.render.avatar_prefetch`；`sys.path` 注入后 `from utils.app_identity import APP_AUTHOR, APP_NAME` | `enemyEval.spec` |

## 目标结构（本计划终态）

```text
enemy_eval/
├── models/                       # 不动
│   ├── enemy_data.py  rating_schema.py  skill_entry.py
│   ├── render_options.py  media.py  ai_evaluation.py
│   └── __init__.py
├── core/                         # 对外只暴露 EnemyCardGenerator
│   ├── __init__.py               # 收口：只 re-export EnemyCardGenerator
│   └── render/
│       ├── config.py             # ← optimization.RenderConfig
│       ├── surface_pool.py       # ← optimization.RenderResourceManager / get_resource_manager
│       ├── image_ops.py          # ← optimization.ImageProcessor（缩放、全局图像缓存）
│       ├── text_layout.py        # ← optimization.TextLayoutResult / get_text_layout / _wrap_text_optimized
│       ├── timing.py             # ← optimization.PerformanceTimer
│       ├── fonts.py              # ← core/fonts.py
│       ├── layout.py             # 保留（测量唯一真源）
│       ├── generator.py  avatar_prefetch.py
│       ├── primitives/           # ← stars.py radar.py
│       ├── text/                 # 渲染域文本子系统
│       │   ├── wikitext_spans.py # ← utils/wiki_span_parser.py（跨包迁入）
│       │   └── wikitext_renderer.py # ← wiki_paragraph_renderer.py
│       └── sections/             # 保留
├── utils/                        # 只放"不属于任何层"的横向能力
│   ├── errors.py                 # ← error_handler.py（跨层错误词表）
│   ├── app/                      # identity/version/logging/settings(+rating/ai/render 偏好)/update_check/resources
│   ├── prts/                     # api_client/pipeline/enemy_builder/field_mapping/wikitext_templates
│   ├── ai/                       # client/prompt/baseline
│   ├── net/                      # transport.py（超时与重试策略）/image_fetch.py
│   ├── qt/                       # debounce.py + render_task.py/prts_task.py/avatar_task.py
│   └── fs/                       # filenames.py/avatar_paths.py
├── gui/                          # 8 py + qml/（components | pages | dialogs | icons，见 04）
├── tests/ scripts/ data/ resource/ example/
└── enemy_eval.spec               # ← enemyEval.spec（需授权改名，见 05/07）
```

## 冻结结论

| # | 结论 | 理由（证据） |
|---|---|---|
| D1 | 保持四层与单向依赖：`models ← utils / core / gui`。不引入新层、不改分层含义 | 当前图无环、有守卫注释与铁律支撑；分层不是问题，问题在层内归类 |
| D2 | `utils` 按**特性**分 6 个子包（`app/prts/ai/net/qt/fs`），顶层只留 `errors.py` | `utils` 混装 4 类职责，且 2025-08 起持续膨胀（108 次改动） |
| D3 | 渲染域文本逻辑迁入 `core/render/text/`（`wiki_span_parser` 跨包迁入） | 该模块 docstring 自述"仅供卡片渲染"，却被 4 个 core 渲染文件引用；迁入后减少一条 `core→utils` 边 |
| D4 | `core/optimization.py` 不存在了：拆为 `config / surface_pool / image_ops / text_layout / timing` | 名称与内容不符（6 个概念），且被 `gui` 直接导入，是对外暴露的偶然 API |
| D5 | `core/__init__.py` 收口为只 re-export `EnemyCardGenerator` | 现状额外导出 4 个内部实现（`RenderResourceManager` 等），使 `core/render` 单一入口契约变松 |
| D6 | `utils/thread_manager.py` 不存在了：**按任务一文件拆 5 个**（`render_task` / `prts_task` / `avatar_task` / `update_task` / `ai_task`） | 名字只说"卡片生成"，实际装渲染/PRTS/头像/版本检查/AI 五类长任务（立项审计只数出 3 类，把后加的两个 AI 期线程漏了；批 2 实测 5 类） |
| D7 | 网络传输策略集中到 `utils/net/transport.py`，PRTS/图像下载共用 | `utils/network_image.py` 反向依赖 `utils/prts_api_client.request_timeout`；AI/更新检查各自写超时 |
| D8 | QML 侧**公开契约字符串**（属性名、信号名、`image://` key、`qmldir` 模块名）视为对外 API，只有批次 4 明确列出的才改 | QML 按名字调用，改名不会编译报错，只在运行时静默失效 |
| D9 | 性能改动一律"先测后改"，单帧收益 <5% 或像素结果有差异即回退 | 无证据的优化会引入回归而无法判定 |
| D10 | `AGENTS.md` 本次不动；迁移导致的路径引用失效汇总到批次 07，等用户授权后一次性同步 | 铁律：`AGENTS.md` 仅用户明确要求时可改 |
| D11 | **一个文件只搬一次**：搬迁与拆分同批完成。`app_settings_store`、`thread_manager`、`network_image` 只在批次 2 搬一次，批次 1 不动 | 否则这三个文件的 15 处导入点会被改两遍（10 + 3 + 2），回归面积与漏改概率翻倍 |
| D12 | **先冻结基线再开批**（批次 0）：审计指标重算 + 像素基线 + 测试数 + QML 装载基线全部落盘后，才允许动第一批 | 否则"未改行为"没有可判定的参照，回滚也失去基准 |

## 批次概览

| 批次 | 主题 | 触及包 | 依赖 | 回滚粒度 |
|---|---|---|---|---|
| 0 | **冻结基线**：审计指标重算 + 像素 sha256 + 测试数 + QML 装载基线（只读 + 落盘） | 无（不改代码） | — | 独立 commit |
| 1 | `utils/` 分子包 + 改名 | `utils`（+全部导入点） | 批次 0 | 单 commit，`git revert` |
| 2 | `utils/` 内部拆分 + 传输层抽取 | `utils`、`core`（`network_image` 调用点） | 批次 1 | 同上 |
| 3 | `core/` 重构 + 文本域迁入 | `core`、`gui`（`core.optimization` 导入点）、`utils` | 批次 1、2 | 同上 |
| 4 | 桥接层与 QML 组织 | `gui` | 批次 1–3 | 同上 |
| 5 | 命名与注释契约 | 全仓库注释层 | 批次 1–4（先定名再统一注释，避免改两遍） | 同上 |
| 6 | 性能（按证据） | 视项而定 | 批次 3 | 每项独立 commit |
| 7 | 验收 / 回滚 / `AGENTS.md` 同步 | 文档 | 全部 | — |

## 总验收（每批都必须过）

```text
1) uv run python -c "import models" / "import core" / "import main"      # 铁律 14 自证
2) uv run pytest                                                        # 全绿
3) 像素回归：固定输入渲染 PNG 的 sha256 与基线一致（含 4 组样本，见 07）
4) QML 装载冒烟：QT_QPA_PLATFORM=offscreen，逐页面/对话框装载成功
5) 涉及 spec/入口/模块路径的批次：pyinstaller 打包 + scripts/build_release.py 校验
```

## 风险总表

| 风险 | 触发批次 | 影响 | 缓解 |
|---|---|---|---|
| 漏改导入点 | 1–4 | 运行时 ImportError；PyInstaller 打包缺模块 | 每批先跑「引用普查」（含相对导入，命令见 01 附录），改后用铁律 14 自证 + `pytest`；spec 的 `hiddenimports` 单独核对 |
| QML 按名调用失效 | 4 | 属性/slot 静默失效，界面无响应 | D8 白名单 + offscreen 装载冒烟 + 逐页点击冒烟 |
| 渲染像素漂移 | 3、6 | 卡片外观变化 | sha256 比对（4 组样本），不一致即回滚 |
| 注释改写引入错误事实 | 5 | 文档与实现不一致（比没注释更糟） | 逐条对照实现改，禁止凭印象补"契约"；改完用 `grep` 反查被删的路径/名 |
| 打包名/路径改名漏改 | 5 | 打包失败或产物名不一致 | 核对 `AGENTS.md:63,80`、`scripts/build_release.py:21,115,176,181,183`、spec 内部 4 处 `enemyEval` 字符串 |
| 顺手功能改动 | 全部 | 违背"功能不缺失" | 批次内禁止行为改动，只记录到「顺带发现」 |
| 同一导入点被改两遍（二次搬迁） | 1→2 | 漏改概率与回归面积翻倍（`app_settings_store` 10 处、`thread_manager` 3 处、`network_image` 2 处） | D11：这三个文件只在批次 2 搬一次 |
| 测试隔离失效（**高危**） | 1、2 | `tests/conftest.py` 按字符串 patch `utils.app_settings_store.settings_file_path` 与 `_cached`；模块改名后若不同步，轻则测试报错、重则 GUI 测试写到**真实用户偏好文件** | 见 `07` §7.9：conftest 与搬迁同一 commit；改后核对真实偏好文件未被写入 |
| 批次 4 安全网弱于 1–3 | 4 | 像素回归不覆盖 QML/UI，桥接名失效只在运行时暴露 | 一小步一 commit + 每步 qmllint / offscreen 装载 / 手工点击（见 `04`、`07` §7.3） |
| 像素基线口径不清 | 全部 | 编码器元数据差异造成假红/假绿 | `07` §7.2：比对**解码后像素字节**的 sha256，渲染直接调 `core` 生成器（不经 Qt） |
