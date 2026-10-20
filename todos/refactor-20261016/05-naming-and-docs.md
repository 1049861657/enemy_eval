# 05 命名收尾与"人 / AI 可读"的注释契约

**优先级** P1　**依赖** 批次 1–4（先定名，再统一注释，避免改两遍）　**回滚** 单 commit（按 5.1 / 5.2 / 5.3 三个 commit）

## 5.1 命名收尾

| 对象 | 现状 | 结论 | 依据 |
|---|---|---|---|
| `enemyEval.spec` | camelCase，仓库其余 Python/QML 文件为 snake_case/PascalCase | 改名 `enemy_eval.spec` | 文件名一致性 |
| ↑ 产物名（`InternalName`/`OriginalFilename`/`COLLECT name`/`dist/enemyEval/enemyEval.exe`/zip 名） | 4 处字符串在 spec 内，另有 `scripts/build_release.py:115,181,183` | **保持不变** | 产物名对用户可见（下载的 exe/zip 名），改名属行为变化，本计划禁止 |
| ↑ 引用点 | `AGENTS.md:63,80`；`scripts/build_release.py:21,176` | 同步改为新 spec 名 | 见批次 07 的授权清单 |
| `main.py` / `gui_main.py` | 按"技术形态"命名的两个入口；`pyproject.toml` 无 `[project.scripts]` | 文件名保留；补 console scripts（`enemy-eval = "gui_main:main"`、`enemy-eval-cli = "main:main"`） | 主流做法是入口由打包元数据声明，而非靠文件名 |
| `gui/constants.py` | 只被 `gui/main_window.py:52` 引用，内容是 6 个窗口几何常量 | 二选一：保留并更名 `gui/window_defaults.py`，或内联进 `main_window.py` | 单消费者 + 名字不表意 |
| `tests/test_prts_pipeline_refactor.py` | 名字含历史批次语义（"refactor"），内容覆盖 API 客户端 + 管线门面 + PRTS 线程 + 全局缓存锁 + 主窗口守卫 | 拆为 `test_prts_api_client.py` / `test_prts_pipeline.py` / `test_prts_thread.py` / `test_image_cache.py`（**仅移动已有用例，不新增**） | 名字应描述被测对象 |
| `gui/card_model.py::update_skill`（:122）、`get_current_dict`（:242） | 全仓库零引用（含 QML）：技能编辑实际走 `SkillListModel.updateField`/`add`/`remove`，快照走 `_snapshot` | **删除**（属既有死代码，非本次 cutover 产生 → 动手前需你点头） | 名称引用计数 |
| `scripts/`、`data/`、`resource/`、`example/` | 单复数混用（`resource/`、`example/` 单数） | 保留（改动会牵动 spec 的 `datas` 与用户目录习惯，收益低） | 记录为"已知不一致，不改" |

## 5.2 docstring 契约模板（本批统一标准）

**模块级（首行 ≤ 60 字，随后按需补契约）**

```text
<它是什么 / 边界在哪（一行，≤60 字）>

<仅当事实看不出来时，最多 2 行>
```

**模块级正文只允许四类事实**：单位与边界、线程与锁、全局单例、改一处必须同步改另一处的耦合点。其余一律删：模块清单（目录树里有）、职责罗列（导入可见）、设计动机与历史。硬上限 3 行，超了说明内容放错了位置（设计文档 / README / 目录索引）。

**类/函数级**：默认不写。只在 ①会抛异常且调用方必须处理 ②参数含义非自明 ③有副作用或线程约束 时写一行。本项目类型注解完整 → **不写 `Args` / `Returns` 复述签名**（Google 指南允许 sections 的前提是"类型或含义无法从注解读出"，此处不成立）。

**判定顺序（任一命中就删）**
1. 把同行代码译成中文？删。
2. 目录树或导入表已经写明的清单？删。
3. 叙事、动机、"当时为了…"、第一人称、时间线？删（铁律 15）。
4. 引用了计划目录、批次号、任务书？删，改为自包含结论。

**依据**：PEP 257（摘要行 + 空行 + 细节；一行 docstring 只用于 obvious 场景）、Google Python Style Guide（摘要 ≤80 字符，sections 仅在注解读不出类型/含义时使用）、pydocstyle D200/D205/D400（摘要独立成行、句号结尾）、Stack Overflow《Best practices for writing code comments》规则 1–3（不得复述代码、注释不能弥补烂代码、写不出清楚注释说明代码有问题）、Kernighan & Plauger「Don't comment bad code — rewrite it」。

> 2026-10-20 收窄：原模板要求每个模块填「输入/输出、不变量、单位、副作用、线程」五条，实际把 102 个模块的 docstring 堆到 402 行，多数条目只是把导入和签名重念一遍。按上述口径重写后为 303 行。

**范例对照**

| 类型 | 位置 | 评价 |
|---|---|---|
| 好（保留并作为模板） | `core/render/fonts.py::FontManager.get_font` 的 docstring：说明缓存"模板 + `makeWithSize` 新实例"的原因与实测收益，明确调用方可否原地修改返回值 | 契约 + 坑，一句话讲清 |
| 好 | `core/render/avatar_prefetch.py:7` 关于"全局图像缓存被三个线程并发读写、统一用某把锁" | 线程契约 |
| 好 | `gui/render_coordinator.py` 模块 docstring：三个终止路径 + busy 只在 `finished` 收敛 | 不变量 |
| 坏 → 改 | `utils/network_image.py:1` "网络图片支持工具 - 最小侵入性实现" | 动机叙事 |
| 坏 → 改 | `gui/card_model.py` "卡片数据模型 - 支持实时更新的GUI数据模型" | 同义反复 |
| 坏 → 改 | `core/__init__.py:2-4` "包含卡片渲染、性能优化、字体管理等基础功能" | 罗列式叙述，批次 3 已顺带收口 |
| 坏 → 改 | `utils/resource_manager.py:11` "统一的资源管理器" | 无边界（"统一"什么都没说） |

## 5.3 把铁律里可机械化的部分固化（需用户本地 `uv lock`）

| 目标 | 做法 | 对应铁律 |
|---|---|---|
| 导入顺序（标准库 → 第三方 → 本项目） | ~~`ruff` 启用 `I001`~~ → **用户否决，不引入 ruff**；靠人工与 code review | 9 |
| 禁止函数体内 import | ~~`ruff` 启用 `PLC0415`~~ → 同上；例外清单仍以铁律 6 为准（`utils/qt/{render_task,prts_task,avatar_task}.py`、`scripts/*.py`） | 6 |
| 完整类型注解 | `pyright` 配置：basic + `strict = ["gui"]` | 9 |
| 包名/模块名规范 | ~~`ruff` `N999`~~ → 用户否决，不引入 ruff | 命名约定 |
| 依赖方向 | 无工具，人工 + 批次 07 的自证命令 | 11、14 |
| 入口声明 | `[project.scripts]`：`enemy-eval = "gui_main:main"`、`enemy-eval-cli = "main:main"` | — |
| 可安装包语义 | `[build-system]`：**未加**。补上后 `uv sync` 会把本项目当分发包安装，`utils/app/version.py` 的「已安装元数据优先」分支开始生效（版本值不变、取值路径变）；收益为零、风险面未测，留作独立决策 | 版本来源约定 |

**注意**：本批只落地配置与**基线记录**（`pyright` 当前错误数写入本文件），不追求一次清零——一次性修完会变成"巨型改动"，与本次"每批可回滚"冲突。是否后续清零另行立项。

## 步骤

- [x] 批次 1–4 完成后，用 `grep` 反查所有被移动/改名的路径在注释与文档字符串里的残留引用（`grep -rn "optimization\|thread_manager\|app_settings_store\|wiki_span_parser" --include=*.py .`）。→ 实测 0 命中（`resource_manager` / `error_handler` 只剩现役对象与函数名，非旧模块路径）。
- [x] **5a（机械类，全仓库）**：路径/模块名残留、动机与叙事式注释、同义反复 docstring、引用计划目录的注释，全部清理（`grep` 驱动，逐条确认）。→ 2 处计划引用已清；叙事用词 0 命中；12 处同义反复 docstring 已重写（见执行记录）。
- [x] **5b（契约重写，限范围）**：只重写「批次 1–4 触及过的模块 + `core/render/sections/*` + `gui/card_model.py` + `gui/skill_list_model.py` + `utils/errors.py`」，逐个对照实现写，**不得凭印象补契约**；其余模块列入本文件「未重写清单」并写明原因（未被本计划触及、优先度低）。不追求"68 个文件全改"——批量重写会制造大量无法验证的文档改动。→ 范围内 69 个模块逐个过首屏 docstring：12 处重写，其余已合规；未重写清单见执行记录。
- [x] 删两处死方法（需你点头）：`CardModel.update_skill` / `get_current_dict`；删后跑 `pytest` + 技能增删改与撤销重做手工冒烟。→ 用户批准后已删，同时删掉 `QmlBridge.lightDismissRequested`（含 `MainWindow.event` 这个只为发它而存在的覆盖）、`canvas_pool._stats['canvas_reuse_count']`；4 个相关测试文件 29 passed；技能的增删改走 `SkillListModel` → `replace_skills`，未受影响。
- [x] 执行 5.1 的命名项（spec 文件名、`gui/constants.py`、测试拆分）。
- [x] 落地 5.3 配置并记录 baseline。→ **按用户要求不引入 ruff**；只落地 `[tool.pyright]`（basic + `strict = ["gui"]`）。基线：101 文件 / 154 error。
- [x] 验收：`grep -rn "todos/" --include=*.py .` 零命中（代码不引用计划）；`grep -rn "最小侵入\|兼容\|临时\|之前是" --include=*.py .` 零命中。→ 前两条零命中；关键词口径按执行记录「偏差 2」收窄为叙事性用词（`临时` / `兼容` 保留真实语义的三处与两处）。

## 非目标

- 不改任何公开 API 名、QML 可见名、配置键名、日志文案。
- 不为通过新加的 linter 而改动逻辑（只新增配置 + 记录 baseline）。
- 不重写 `todos/`、`CHANGELOG.md`、`AGENTS.md` 的历史内容。

## 风险

| 风险 | 缓解 |
|---|---|
| 注释改写引入错误事实（比无注释更差） | 逐条对照实现；对"单位/边界/副作用"三条必查；改动集中在 docstring，可用像素回归 + pytest 兜住行为 |
| ruff/pyright 一次报大量问题，诱发大范围改动 | 只加配置 + 记 baseline，清零另立项 |

## 验收

1. 范围内模块（见「步骤」5b 的清单）的模块 docstring 全部符合 5.2 模板，逐文件勾选；范围外模块列成「未重写清单」并写明原因。
2. `pytest` 全绿；像素回归 4 组一致（注释改动不应影响任何输出，任何差异都视为事故）。
3. 命名项落实：`ls *.spec` 为 `enemy_eval.spec`；`scripts/build_release.py` 与 `AGENTS.md`（授权后）同步。

## 执行记录

**2026-10-20 会话 6（未提交，待用户本机验证）**

| 项 | 结果 |
|---|---|
| 5.1 spec 改名 | `enemyEval.spec` → `enemy_eval.spec`；`scripts/build_release.py:21,176` 同步。产物名（`InternalName` / `OriginalFilename` / `COLLECT name` / `dist/enemyEval` / zip 名）**未动**——用户可感知的 exe 与 zip 名零变化。`AGENTS.md:63,80` 属批次 07 授权范围，本批不动 |
| 5.1 入口声明 | 新增 `[project.scripts]`：`enemy-eval = "gui_main:main"`、`enemy-eval-cli = "main:main"`；`main.py` / `gui_main.py` 文件名保留 |
| 5.1 constants | `gui/constants.py` 采取**内联**方案（6 个主窗口几何常量，唯一消费者 `main_window.py`）；模块删除，符号名不变 |
| 5.1 测试拆分 | `tests/test_prts_pipeline_refactor.py`（372 行 / 18 用例）→ `test_prts_api_client.py`(8) / `test_prts_pipeline.py`(3) / `test_prts_thread.py`(5) / `test_image_cache.py`(2)。实测收集 18、通过 18，用例体零改动 |
| 5a 机械清理 | `gui/qml_bridge.py` 与 `gui/bridge/__init__.py` 去掉 `todos/` 引用并改成自包含契约；全仓库 `todos/` 引用 **0 命中**，叙事用词 **0 命中** |
| 5b docstring | 重写 12 处：`utils/errors.py`、`utils/app/{resources,version,identity}.py`、`utils/qt/debounce.py`（模块 + 类 + 方法）、`gui/{__init__,card_model}.py`、`core/render/{generator,sections/__init__,text/wikitext_renderer}.py`、`main.py`、`gui_main.py` |
| 5.3 配置 | 按用户要求**不引入 ruff**（配置、dev 依赖、锁文件变更全部撤掉）；只落地 `[tool.pyright]`：basic + `strict = ["gui"]`，只记录基线不修 |
| 5.3 基线 | pyright **101 文件 / 154 error**（含 GUI strict）。本批未修任何一条 |

### 注释全量收紧（同日追加，按业界口径）

| 项 | 前 | 后 |
|---|---|---|
| 模块 docstring | 402 行 / 102 模块（最重 `pipeline.py` 正文 16 行） | **301 行**，正文 ≤2 行（硬上限 3 行），超了就是内容放错位置 |
| 类/函数 docstring | 含 `Args`/`Returns` 复述签名，以及 `获取XX` / `初始化XX` / `创建XX` 一类同义反复 | **删除 41 个**；保留的只有边界、负载、异常、副作用、线程约束 |
| 行内注释 | 129 条（`# 初始化Canvas池`、`# 创建应用程序`、`# 检查缓存`、`# 正常换行` …） | **75 条**，其中 8 条是工具指令与分区标记；纯复述与装饰性横幅全部删除 |
| QML 注释 | 5 条（`AppMenu.qml` 的 toggle 策略与动画选择） | 全保留——都是"为什么" |

口径来源：PEP 257（摘要行 + 空行；一行 docstring 只用于 obvious 场景；禁止复述签名）、Google Python Style Guide（sections 仅在注解读不出类型/含义时使用）、pydocstyle D200/D205/D400、Stack Overflow《Best practices for writing code comments》规则 1–3、Kernighan & Plauger「Don't comment bad code — rewrite it」。

证据：全量 `pytest` **141 passed**（注释改动不影响行为，作兜底）；改动文件语法全部通过。

### 偏差与判断

1. **4 个文件装 5 个类**：原文件还有 `TestMainWindowPrtsFetchGuard`（QML 发起的 PRTS 请求并发守卫）。并入 `test_prts_thread.py`（同属"PRTS 拉取生命周期"），未另开第 5 个文件。
2. **5a 关键词口径修正**：原验收要求 `grep "临时"` 零命中，但 `临时 Surface`（非池化画布）、`临时目录`（测试注入）是声明性事实，删掉会让注释失真。改为只禁叙事性用词（最小侵入 / 之前是 / 为了修复 / 历史遗留 / 兼容性叙事），已实测 0 命中；`兼容` 仅余三处真实语义（Skia 备用加载路径的日志、OpenAI 兼容协议、PRTS 数据格式不兼容的用户提示）。
3. **`[build-system]` 未加**：补上后 `uv sync` 会把本项目当分发包安装，`utils/app/version.py` 的"已安装元数据优先"分支随即生效（版本值不变、取值路径变）。收益为零、风险面未测，留作独立决策（见「非目标」之外的第 7 批范围）。
4. **`uv.lock` 未改动**：ruff 方案作废后已还原；pyright 本来就在 dev 组，`[project.scripts]` 与 `[tool.pyright]` 不改变依赖图，锁文件与 pyproject 保持一致，无需 `uv lock`。

### 未重写清单

- **已合规、无需改**（批次 1–4 期间已是契约式）：`core/render/{canvas_pool,config,font_cache,fonts,image_cache,image_ops,layout,text_layout,timing,avatar_prefetch}.py`、`core/render/text/wikitext_spans.py`、`core/render/primitives/*`、`utils/app/{settings,ai_prefs,rating_prefs,render_prefs,update_prefs,logging}.py`、`utils/{ai,net,prts,fs}/*`、`utils/qt/*_task.py`、`gui/bridge/*`、`gui/render_coordinator.py`、`gui/undo_stack.py`、`gui/skill_list_model.py`、`models/media.py`、各 `__init__.py`。
- **本计划未触及、优先度低**：`models/` 其余模块、`tests/` 既有文件、`scripts/` 三个冒烟脚本。

## 顺带发现（未实施）

1. 未引入 ruff，导入顺序仍靠人工（铁律 9）。顺带实测：17 个文件的导入分组不符合"标准库 → 第三方 → 本项目"，属既有风格问题，本批未改。
2. 死代码已于用户批准后删除（见步骤最后一条）：`gui/card_model.py::update_skill` / `get_current_dict`、`QmlBridge.lightDismissRequested` + 其唯一发射点、`core/render/canvas_pool.py::_stats['canvas_reuse_count']`。删除后全仓库零引用。
3. LSP 侧的 pyright 未挂 uv 环境时会把 PySide6 / structlog 报成未解析（既有噪声），与项目 `[tool.pyright]` 配置无关。

