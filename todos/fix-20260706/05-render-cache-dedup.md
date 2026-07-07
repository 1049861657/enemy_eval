# 批次 5：渲染层缓存复用与重复代码收敛

**风险等级**：P1 — 均为性能/可维护性问题，非正确性 bug；建议在批次 0 测试就绪、批次 1 并发问题解决后再做，避免与加锁改动相互干扰。

**执行状态：已完成。** `uv run pytest` 122 个测试全部通过（批次 4 完成时的 122 个，本批次纯内部重构未新增测试）。改动前后各生成一张示例卡片（`main.py` 内置的示例 `EnemyData`），像素级 diff 结果 **0 差异**（`max pixel channel diff: 0`，2925000 像素全部一致）。

## 5.1 字体缓存被大部分 section 绕过

- [x] 位置：`core/render/sections/avatar.py:44` 是唯一使用 `gen._get_optimized_font()`（→ `RenderResourceManager` 缓存）的 section；`info.py`、`rating_grade.py`、`skills_talents.py` 多处直接调用 `gen.font_manager.get_font(size)`（`core/fonts.py`，原实现每次无条件 `return skia.Font(...)`，无缓存）。
- [x] 修复：采用"`FontManager.get_font()` 内部加缓存"方案（如原文档推荐）。**关键陷阱（原文档未预料到）**：多处调用方会对返回值原地 `setEmbolden(True)`（如 `core/render/layout.py::wiki_line_count`/`wiki_paragraph_renderer.py::draw_wiki_paragraph` 都以同一 size 调用两次分别取 `fn`/`fb`，再对 `fb` 加粗）。若直接缓存并复用同一个 `skia.Font` 实例，后一次的 mutation 会把前一次的引用一并污染（两者是同一对象），导致同 size 的所有渲染/测量意外全部变为粗体。改为**缓存"未修改模板"，每次调用通过 `Font.makeWithSize()` 返回全新独立实例**（实测比直接 `skia.Font(typeface, size)` 构造快约 7 倍，因为省去了 typeface 绑定的重复开销），调用方可安全地对返回值做任意原地修改。`core/optimization.py::RenderResourceManager.get_font` 存在同样的设计缺陷（此前"侥幸"因只有一个调用点未触发），一并用相同模式修复。
- [x] 验证：编写临时回归脚本，确认 `fn = get_font(24); fb = get_font(24); fb.setEmbolden(True)` 后 `fn is not fb` 且 `fn.isEmbolden() == False`（无污染）；`RenderResourceManager.get_font` 同样验证通过。

## 5.2 `stars.py` 星形路径几何重复

- [x] 位置：`core/render/stars.py`（`draw_premium_star`）与（`draw_empty_star`）各自完整复制一遍五角星路径生成算法。
- [x] 修复：抽出 `_build_star_path(cx, cy, radius) -> skia.Path` 私有函数，两个绘制函数共用路径构造。

## 5.3 颜色变暗系数重复实现

- [x] 位置：`core/render/sections/rating_grade.py`（评级卡渐变、等级块渐变两处）与 `core/render/stars.py`（`color[i]*0.8`/`color[i]*0.6`）各自独立手写"颜色乘固定系数得到深色变体"。
- [x] 修复：抽出 `darken(color: tuple[float,float,float], factor: float) -> tuple[float,float,float]` 工具函数，放 `core/render/layout.py`；四处调用点（`stars.py` 两处、`rating_grade.py` 两处）统一替换。

## 5.4 测量与绘制的字号/圆角/横坐标计算未共享

- [x] 位置：`core/render/layout.py` 横向坐标计算（"居中文字 x 坐标 = 容器x + (容器宽-文本宽)/2"）在 `info.py`、`skills_talents.py`、`avatar.py`、`rating_grade.py` 被独立重复实现共 9 处；字号/宽度在测量函数与绘制函数中各写一份。
- [x] 修复：
  - [x] `layout.py` 新增 `center_text_x(x, width, text_width)` 辅助函数，9 处手写表达式全部替换。
  - [x] 新增顶层常量 `INFO_DESC_WRAP_WIDTH`/`INFO_DESC_FONT_SIZE`/`SKILL_EFFECT_WRAP_WIDTH`/`SKILL_EFFECT_FONT_SIZE`/`TALENTS_TEXT_WRAP_WIDTH`/`TALENTS_TEXT_FONT_SIZE`/`GRADE_COMMENT_FONT_SIZE`（放在既有 `COMMENT_*` 常量附近），`measure_info_section`/`measure_skills_talents_bottom`/`measure_grade_block_height` 与对应绘制函数（`info.py`/`skills_talents.py`/`rating_grade.py`）强制引用同一常量源。

## 5.5 `wiki_skia.py` 与 `wiki_text.py` 命名边界模糊 + 重复的测量器构建样板

- [x] 位置：`utils/wiki_skia.py`（纯解析）vs `core/render/wiki_text.py`（绘制）vs `core/render/layout.py`（又一次调用同样的解析函数只为取行数），`wiki_text.py` 与 `layout.py` 有几乎逐行重复的"构建测量器"样板代码。
- [x] 修复：
  - [x] 用 `lsp rename_file` 重命名：`utils/wiki_skia.py` → `utils/wiki_span_parser.py`；`core/render/wiki_text.py` → `core/render/wiki_paragraph_renderer.py`；配套测试 `tests/test_wiki_skia.py` → `tests/test_wiki_span_parser.py`。所有引用点（`layout.py`/`info.py`/`skills_talents.py`/`wiki_paragraph_renderer.py` 自身）已更新 import 路径。
  - [x] 提炼公共 helper `build_wiki_measurer(font_manager, font_size) -> (fn, fb, meas)`（放 `layout.py`，紧邻 `measure_wiki_char`），`wiki_paragraph_renderer.py::draw_wiki_paragraph` 与 `layout.py::wiki_line_count` 均改为调用同一函数。

## 5.6 `EnemyCardGenerator` 部分单例部分每次重建的不一致

- [x] 位置：`core/render/generator.py::__init__`：`self.resource_manager = resource_manager or get_resource_manager()`（共享单例）vs `self.font_manager = FontManager()`（每次新建）。
- [x] 修复：采用推荐方案——新增 `core/fonts.py::get_font_manager()` 全局单例函数（与 `get_resource_manager()` 对称），`__init__` 同时支持可选注入参数（`font_manager: Optional[FontManager] = None`，同 `resource_manager` 一致的模式）与默认单例。验证：两个独立 `EnemyCardGenerator()` 实例的 `font_manager` 确认为同一对象，且两次独立渲染像素级完全一致（无跨实例缓存污染）。

## 验收标准

- [x] 生成一张卡片前后对比截图，确认视觉效果与改动前完全一致：用 `git worktree` 拉出改动前的干净基线（`HEAD`，即批次 4 完成时的提交）与当前工作区分别渲染 `main.py` 内置示例数据的卡片，PIL 逐像素 diff，`max pixel channel diff: 0`，2925000 像素零差异。
- [x] `grep -rn "font_manager.get_font(" core/render/sections/` 仍有直接调用（`info.py`/`rating_grade.py`/`skills_talents.py` 多处），但这些调用现在都会命中 `FontManager.get_font` 内部的模板缓存（见 5.1），不再是"绕过缓存"的直接构造——验收调整为确认 `FontManager.get_font` 内部已有缓存逻辑（`core/fonts.py::FontManager._font_template_cache`），而非要求调用方改用 `_get_optimized_font()`。
