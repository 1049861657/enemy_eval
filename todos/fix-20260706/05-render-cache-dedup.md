# 批次 5：渲染层缓存复用与重复代码收敛

**风险等级**：P1 — 均为性能/可维护性问题，非正确性 bug；建议在批次 0 测试就绪、批次 1 并发问题解决后再做，避免与加锁改动相互干扰。

## 5.1 字体缓存被大部分 section 绕过

- [ ] 位置：`core/render/sections/avatar.py:44` 是唯一使用 `gen._get_optimized_font()`（→ `RenderResourceManager` 缓存）的 section；`info.py`（99,101,163 行）、`rating_grade.py`（54,106,127 行）、`skills_talents.py`（133,173,175,264,336,362 行）全部直接调用 `gen.font_manager.get_font(size)`（`core/fonts.py:56-60`，每次无条件 `return skia.Font(...)`，无缓存）。
- [ ] 修复：统一改为全部走 `gen._get_optimized_font()` / `resource_manager.get_font()`；或者更彻底地让 `FontManager.get_font()` 自身内部做 `size → Font` 字典缓存，两条路径收敛为一套。推荐后者（改动集中在一处，无需改 4 个调用文件）。

## 5.2 `stars.py` 星形路径几何重复

- [ ] 位置：`core/render/stars.py:17-34`（`draw_premium_star`）与 `57-74`（`draw_empty_star`）各自完整复制一遍五角星路径生成算法（`moveTo` + 循环计算内外半径交替顶点），仅填充/描边样式不同。
- [ ] 修复：抽出 `_build_star_path(cx, cy, radius) -> skia.Path` 私有函数，两个绘制函数共用路径构造。

## 5.3 颜色变暗系数重复实现

- [ ] 位置：`core/render/sections/rating_grade.py`（评级卡渐变、等级块渐变两处）与 `core/render/stars.py:38,49`（`color[i]*0.8`/`color[i]*0.6`）各自独立手写"颜色乘固定系数得到深色变体"。
- [ ] 修复：抽出 `darken(color: tuple, factor: float) -> tuple` 工具函数（放 `core/render/layout.py` 或新建 `core/render/color_utils.py`），四处调用点统一替换。

## 5.4 测量与绘制的字号/圆角/横坐标计算未共享

- [ ] 位置：`core/render/layout.py` 只覆盖纵向高度测算，横向坐标计算（"居中文字 x 坐标 = 容器x + (容器宽-文本宽)/2"）在 `info.py`（128,146 行）、`skills_talents.py`（212,253-254,301-302,340-341,365-366 行）、`avatar.py`（48-49 行）、`rating_grade.py`（111-112 行）被独立重复实现至少 8 次。圆角半径（18/24）、字号（21 等）在测量函数与绘制函数中各写一份，必须人工保持同步——任何一处改动都可能导致画布裁切或留白错位。
- [ ] 修复：
  - [ ] `layout.py` 新增 `center_text_x(x, width, text_width)` 辅助函数，替换全部手写表达式。
  - [ ] 把绘制与测量共用的字号/圆角数值提升为 `layout.py` 顶层命名常量（如 `SKILL_TEXT_FONT_SIZE = 21`），绘制函数与 `measure_*` 函数强制引用同一常量源，杜绝双份字面量漂移。

## 5.5 `wiki_skia.py` 与 `wiki_text.py` 命名边界模糊 + 重复的测量器构建样板

- [ ] 位置：`utils/wiki_skia.py`（纯解析：`WikiStyle`/`TextSpan`/`parse_wikitext_to_spans`/`wrap_spans_to_lines`）vs `core/render/wiki_text.py`（`draw_wiki_paragraph`，调用前者后实际绘制）vs `core/render/layout.py`（又一次调用同样的解析函数只为取行数）。
- [ ] 问题：两个文件都叫"wiki"，仅凭文件名无法判断谁负责解析谁负责绘制；且 `wiki_text.py:29-32` 与 `layout.py:29-33` 有几乎逐行重复的"构建测量器"样板代码（`fn=font_manager.get_font(...)`, `fb=...`, `fb.setEmbolden(True)`, `meas=measure_wiki_char(fn, fb)`）。
- [ ] 修复：
  - [ ] 重命名消歧义：`utils/wiki_skia.py` → 强调解析层定位，改名为 `utils/wiki_span_parser.py` 或 `utils/wiki_rich_text.py`（不用 `wikitext_parser.py`，避免与批次 3.2 新建的 `utils/wiki_template_parser.py` 撞名——两者职责不同：一个转换 wiki 富文本为绘制用 span，一个解析 MediaWiki 模板语法）；`core/render/wiki_text.py` → 强调渲染层定位（如 `wiki_paragraph_renderer.py`）。改名需用 `lsp rename_file` 确保引用同步更新，不能用文本替换。
  - [ ] 提炼公共 helper（如 `build_wiki_measurer(font_manager, font_size) -> (fn, fb, meas)`），`wiki_text.py`/`layout.py` 两处调用同一函数，避免测量口径与绘制口径漂移。

## 5.6 `EnemyCardGenerator` 部分单例部分每次重建的不一致

- [ ] 位置：`core/render/generator.py:27-49`（`__init__`）：`self.resource_manager = resource_manager or get_resource_manager()`（共享单例）vs `self.font_manager = FontManager()`（每次新建）。
- [ ] 修复：统一复用策略——要么让 `FontManager` 也通过对称的 `get_font_manager()` 全局单例函数获取，要么把 `font_manager` 也作为可选参数注入 `__init__`（同 `resource_manager` 一样支持外部传入复用）。推荐前者，与现有 `get_resource_manager()` 模式保持一致。

## 验收标准

- 生成一张卡片前后对比截图（`pencil_get_screenshot` 或直接跑 `main.py` 生成 PNG），确认视觉效果与改动前完全一致（这批改动全是内部重构，不应有可见的渲染差异）。
- `grep -rn "font_manager.get_font(" core/render/sections/` 确认不再有绕过缓存的直接调用（若选择 5.1 的"FontManager 内部缓存"方案，此 grep 检查项改为确认 `FontManager.get_font` 内部已有缓存逻辑）。
