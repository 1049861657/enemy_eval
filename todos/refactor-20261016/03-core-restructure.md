# 03 `core/` 重构与文本域归位

**优先级** P0　**依赖** 批次 1、2　**回滚** 单 commit（建议按 3.1 / 3.2 / 3.3 三个 commit）

## 目标

`core/optimization.py` 这个名字与内容不符的杂货铺拆掉；`core/__init__.py` 收口；只服务渲染的文本子系统从 `utils/` 迁回渲染层。

## 3.1 拆 `core/optimization.py`（402 行 / 6 个顶层概念）

**现状锚点**

| 行 | 内容 | 归属结论 |
|---|---|---|
| `:26` | `TextLayoutResult`（文本布局结果数据类） | → `text_layout.py` |
| `:36` | `RenderConfig`（画布尺寸、池大小、缓存大小） | → `config.py` |
| `:53-54` | `_GLOBAL_IMAGE_CACHE` + `_GLOBAL_IMAGE_CACHE_LOCK` | → `image_cache.py`（**全局唯一**，见下） |
| `:60` | `RenderResourceManager`：画布池（`_canvas_pool`/`_canvas_in_use`/`_variable_surface`/`acquire_canvas`/`acquire_variable_canvas`/`release_canvas`）+ 字体缓存（`_font_cache`/`get_font`）+ 文本布局缓存（`_text_layout_cache`/`get_text_layout`/`_wrap_text_optimized`）+ 图像缓存句柄（`_image_cache`）+ `_stats` | 拆四份：`canvas_pool.py`、`font_cache.py`、`text_layout.py`、`image_cache.py` |
| `:293` | `ImageProcessor`（图像缩放，读写全局图像缓存） | → `image_ops.py` |
| `:378` | `PerformanceTimer` | → `timing.py` |
| `:395-402` | `_global_resource_manager` + `get_resource_manager()` 单例 | 单例归属拆后最大的那个模块；`gui/main_window.py:549` 的 `clear_caches()` 需要保留一个跨模块清理入口 |

**目标模块（`core/render/` 下）**

| 新模块 | 内容 | 说明 |
|---|---|---|
| `config.py` | `RenderConfig` | 尺寸与池/缓存容量；docstring 写清各字段单位与生效位置 |
| `canvas_pool.py` | `CanvasPool`（原名 `RenderResourceManager` 的池部分）+ `get_canvas_pool()` | 池化与可变 Surface；docstring 写清线程约束（渲染由单线程串行驱动，见 `RenderCoordinator`） |
| `font_cache.py` | `skia.Font` 按 size 模板缓存 | 保留现有 `makeWithSize()` 的"模板 + 新实例"语义与其说明注释（这是本仓库最好的注释范例，不要改掉） |
| `text_layout.py` | `TextLayoutResult`、`get_text_layout()`、`_wrap_text_optimized()`（中文避头尾/制表符/主动换行） | 换行规则集中一处；`generator._wrap_text` 委托到这里 |
| `image_cache.py` | `_GLOBAL_IMAGE_CACHE`、锁、公开访问器（`cache_get / cache_put / cache_has / cache_clear`） | 渲染线程与两个网络线程共读写（见 `core/render/avatar_prefetch.py:7` 的说明）；**公开访问器取代外部 import 私有名** |
| `image_ops.py` | `ImageProcessor`（缩放到目标尺寸等） | 只读 image_cache，不发起网络 |
| `timing.py` | `PerformanceTimer` | 与渲染无关的通用计时器 |

**现状引用点（必须全改）**

| 引用点 | 内容 |
|---|---|
| `core/__init__.py:9-11,18-20` | 聚合导出 4 个内部实现（见 3.2） |
| `core/render/generator.py:14-18,33,37-38` | `ImageProcessor` / `PerformanceTimer` / `RenderConfig` / `get_resource_manager` |
| `core/render/avatar_prefetch.py:18,32-33,66-67` | **import 私有名** `_GLOBAL_IMAGE_CACHE` / `_GLOBAL_IMAGE_CACHE_LOCK` 并直接加锁读写 |
| `gui/main_window.py:15,549` | `get_resource_manager()`（关窗清缓存） |
| `tests/test_prts_pipeline_refactor.py:329-336` | 断言 `opt._GLOBAL_IMAGE_CACHE_LOCK` 的身份/类型，与 `prefetch._GLOBAL_IMAGE_CACHE_LOCK is opt.**` 同一对象 |

> 该测试是"锁定全局缓存与锁为同一对象"的契约测试：拆分后 `core.optimization` 消失，测试需同步改导入路径与断言对象（属于"拆分导致已有测试失效"的允许改动，非新增测试）。

**generator 属性面冻结**（`sections/`、`radar.py`、`wiki_*` 依赖，不得改名）

| 属性 | 用处（引用次数） |
|---|---|
| `gen.canvas` | 57 |
| `gen.font_manager` | 23 |
| `gen.grade_colors` | 2 |
| `gen._wrap_text` | 2 |
| `gen.image_processor` | 1 |
| `gen.config` | 1 |
| `gen._get_optimized_font` | 1 |

**步骤**
- [ ] 先跑一次 `grep -rho "gen\.[a-zA-Z_]*" core/render | sort | uniq -c`，把上面这张表按当前代码重算一遍再开工。
- [ ] 新建 7 个模块（含空壳与 docstring），逐个搬内容，**不在旧文件留兼容别名**，搬完即删 `core/optimization.py`。
- [ ] `avatar_prefetch.py` 改用 `image_cache` 的公开访问器（不再 import 私有名）。
- [ ] 改 `generator.py` 的组合方式（画布池 / 图像处理 / 字体 / 文本布局各自持有），保持上表属性名不变。
- [ ] 同步改 `tests/test_prts_pipeline_refactor.py` 的两处导入与断言对象。
- [ ] 验收：像素回归 + 关窗冒烟（`clear_caches` 路径）+ 线程测试。

## 3.2 `core/__init__.py` 收口

**现状**：额外 re-export `RenderResourceManager` / `ImageProcessor` / `PerformanceTimer` / `get_resource_manager`（`core/__init__.py:9-11,18-20`），使 `core/render` 的单一入口契约变松，外部可绕过 `EnemyCardGenerator` 直接摸内部实现。

**结论**：`core/__init__.py` 只 re-export `EnemyCardGenerator`；`gui` 需要的清缓存入口改为从 `core.render.<新模块>` 导入（`gui/main_window.py:15,549`）。docstring 改写为声明式事实（现在写的是"包含卡片渲染、性能优化、字体管理等基础功能"，属罗列式叙述）。

**步骤**
- [ ] 收紧 `__all__`；改 `gui/main_window.py` 的导入。
- [ ] 验收：`uv run python -c "import core; print([n for n in dir(core) if not n.startswith('_')])"` 只剩预期名。

## 3.3 文本域归位（`core/render/text/`）

**现状锚点**：`utils/wiki_span_parser.py`（470 行，`utils` 最大文件）docstring 自述"wikitext → Skia 绘制用片段 + 按宽度换行（**仅供卡片渲染**）"，却被 4 个渲染文件引用：

| 引用点 | 内容 |
|---|---|
| `core/render/layout.py` | 用其测量函数算行数 |
| `core/render/sections/info.py` | 描述文本 |
| `core/render/sections/skills_talents.py` | 技能效果文本 |
| `core/render/wiki_paragraph_renderer.py` | 绘制 |
| `tests/test_wiki_span_parser.py` | 单元测试 |

**结论**：迁为 `core/render/text/wikitext_spans.py`；同时把 `core/render/wiki_paragraph_renderer.py` 迁为 `core/render/text/wikitext_renderer.py`（解析与绘制同域同目录）。`utils/prts/wikitext_templates.py`（模板语法，被 `utils/prts/field_mapping.py` 使用）**留在 PRTS 侧**——它是数据源解析，不是渲染。

**步骤**
- [ ] 建 `core/render/text/`，迁入两个模块并改名，改 5 处引用。
- [ ] 迁移后复核：`grep -rn "wiki_span_parser" .` 零命中（含注释与文档字符串）。
- [ ] 复核 `core → utils` 剩余边：应为 `utils.errors`、`utils.fs.filenames`、`utils/net/image_fetch`（以及 `core/render/sections/*` 对 `utils.errors` 的使用），无 `wiki_*`。
- [ ] 验收：像素回归（三段 wiki 富文本必须逐像素一致：`info` 描述、技能效果、天赋）。

## 3.4 `core/fonts.py` 与图元

| 现状 | 结论 | 依据 |
|---|---|---|
| `core/fonts.py` 被 6 个渲染模块 + `core/__init__` 引用，内容是 skia 中文字体加载（Windows 字体路径硬编码） | 迁为 `core/render/fonts.py`；docstring 写明平台假设与兜底（加载失败 → 中文显示方框，不抛） | 只服务渲染；`core/` 顶层只剩 `render/` 后层级更一致 |
| `core/render/stars.py`（星形图元）、`core/render/radar.py`（雷达图）与 `sections/` 平级 | 迁入 `core/render/primitives/`（`stars.py`、`radar.py`） | 图元 vs 分区粒度不一致 |
| `core/render/sections/rating_grade.py`（355 行）一名含两概念（记分板 + 等级/简评块） | **保留文件名**，在 docstring 说明由两个入口函数分别负责；若后续要拆，需先确认 `draw_rating_section`/`draw_grade_section` 的共享私有函数（`_panel_path`、`_draw_panel_chrome` 等）归属 | 拆分收益低于回归风险 |

## 非目标

- 不改渲染顺序、坐标、颜色、字号（`layout.py` 的常量与公式一字不动）。
- 不改缓存容量、池大小、锁策略、线程模型。
- 不改 `RenderOptions`、`RenderConfig` 的字段名与默认值（`RenderConfig.width=1950/height=1500` 保持）。
- 不引入 GPU / 多进程渲染。

## 风险

| 风险 | 缓解 |
|---|---|
| 拆 `RenderResourceManager` 时漏掉 `_stats`、`clear_caches`、可变 Surface 的复用条件 | 逐方法搬，搬完对照 `grep -n "def " core/optimization.py`（改前副本）逐条核对 |
| 全局图像缓存被拆到两个模块 → 出现两份缓存 | `image_cache.py` 是唯一持有者；`grep -rn "_GLOBAL_IMAGE_CACHE" ` 只允许出现在该文件与测试 |
| 文本域迁移导致换行差异（像素变化） | 迁移前后跑 4 组像素样本，sha256 必须一致 |

## 验收

1. `core/optimization.py` 不存在；`core/` 下只有 `__init__.py` 与 `render/`。
2. `import core` 可用且 `core.__all__` 只有渲染入口；`import main` 可用（铁律 14）。
3. `grep -rn "core.optimization" .` 零命中（含 `spec` 的 `hiddenimports`：`core.render.generator`、`core.render.avatar_prefetch` 需按新路径复核）。
4. 像素回归 4 组一致；`pytest` 全绿（含改路径后的 `test_prts_pipeline_refactor.py`、`test_layout.py`）。

## 顺带发现

（执行时回填，不在本批实施）
