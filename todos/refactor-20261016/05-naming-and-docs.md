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
<这个模块做什么（一句，名词短语）>

契约：
- 输入 / 输出：<数据从哪来、到哪去>
- 不变量：<必须成立的事实>
- 单位与边界：<像素 / 毫秒 / 取值范围 / 0 的含义>
- 副作用：<写文件 / 发网络 / 改全局状态>
- 线程：<可被哪个线程调用，是否加锁>
```

**函数/方法级**：一句"做什么 + 关键契约"；仅在参数含义非自明、或会抛异常时补 `Args / Returns / Raises`。

**判定规则（写之前自问）**
1. 只看注释能否判断"能不能调用、非法输入会怎样"？不能 → 补事实。
2. 内容是否在实现里能直接读出来（把同行代码翻译成中文）？是 → 删。
3. 是否出现"之前/曾经/为了修复/临时/最小侵入"等叙事、动机、第一人称？是 → 删（铁律 15）。
4. 是否引用了计划目录、批次号、任务书？是 → 删，改为自包含结论。
5. 常量/边界是否写了来源或依据（如"1950 = 1500 × 1.3，设计基准"）？缺 → 补一句事实。

**范例对照**

| 类型 | 位置 | 评价 |
|---|---|---|
| 好（保留并作为模板） | `core/fonts.py::FontManager.get_font` 的 docstring：说明缓存"模板 + `makeWithSize` 新实例"的原因与实测收益，明确调用方可否原地修改返回值 | 契约 + 坑，一句话讲清 |
| 好 | `core/render/avatar_prefetch.py:7` 关于"全局图像缓存被三个线程并发读写、统一用某把锁" | 线程契约 |
| 好 | `gui/render_coordinator.py` 模块 docstring：三个终止路径 + busy 只在 `finished` 收敛 | 不变量 |
| 坏 → 改 | `utils/network_image.py:1` "网络图片支持工具 - 最小侵入性实现" | 动机叙事 |
| 坏 → 改 | `gui/card_model.py` "卡片数据模型 - 支持实时更新的GUI数据模型" | 同义反复 |
| 坏 → 改 | `core/__init__.py:2-4` "包含卡片渲染、性能优化、字体管理等基础功能" | 罗列式叙述，批次 3 已顺带收口 |
| 坏 → 改 | `utils/resource_manager.py:11` "统一的资源管理器" | 无边界（"统一"什么都没说） |

## 5.3 把铁律里可机械化的部分固化（需用户本地 `uv lock`）

| 目标 | 做法 | 对应铁律 |
|---|---|---|
| 导入顺序（标准库 → 第三方 → 本项目） | `ruff` 启用 `I001` | 9 |
| 禁止函数体内 import | `ruff` 启用 `PLC0415`，并对 `utils/qt/*_task.py`、`scripts/*.py` 做 per-file-ignores（延迟导入是既定例外） | 6 |
| 完整类型注解 | `pyright` 配置（GUI 目录更严） | 9 |
| 包名/模块名规范 | `ruff` `N999` | 命名约定 |
| 依赖方向 | 无工具，人工 + 批次 07 的自证命令 | 11、14 |
| 入口声明 | `[project.scripts]`：`enemy-eval = "gui_main:main"`、`enemy-eval-cli = "main:main"` | — |
| 可安装包语义 | `[build-system]`：**[需先验证再决定]** 补上后 `uv sync` 会把本项目当分发包安装，`utils/app_version.py` 的「已安装元数据优先」分支开始生效（版本值不变，但取值路径变了）；确认无副作用再决定加不加 | 版本来源约定 |

**注意**：本批只落地配置与**基线记录**（`pyright` 当前错误数写入本文件），不追求一次清零——一次性修完会变成"巨型改动"，与本次"每批可回滚"冲突。是否后续清零另行立项。

## 步骤

- [ ] 批次 1–4 完成后，用 `grep` 反查所有被移动/改名的路径在注释与文档字符串里的残留引用（`grep -rn "optimization\|thread_manager\|app_settings_store\|wiki_span_parser" --include=*.py .`）。
- [ ] **5a（机械类，全仓库）**：路径/模块名残留、动机与叙事式注释、同义反复 docstring、引用计划目录的注释，全部清理（`grep` 驱动，逐条确认）。
- [ ] **5b（契约重写，限范围）**：只重写「批次 1–4 触及过的模块 + `core/render/sections/*` + `gui/card_model.py` + `gui/skill_list_model.py` + `utils/errors.py`」，逐个对照实现写，**不得凭印象补契约**；其余模块列入本文件「未重写清单」并写明原因（未被本计划触及、优先度低）。不追求"68 个文件全改"——批量重写会制造大量无法验证的文档改动。
- [ ] 删两处死方法（需你点头）：`CardModel.update_skill` / `get_current_dict`；删后跑 `pytest` + 技能增删改与撤销重做手工冒烟。
- [ ] 执行 5.1 的命名项（spec 文件名、`gui/constants.py`、测试拆分）。
- [ ] 落地 5.3 配置并记录 baseline。
- [ ] 验收：`grep -rn "todos/" --include=*.py .` 零命中（代码不引用计划）；`grep -rn "最小侵入\|兼容\|临时\|之前是" --include=*.py .` 零命中。

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

## 顺带发现

（执行时回填，不在本批实施）
