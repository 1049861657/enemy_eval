# 批次 0：引入测试基础设施

**为什么最先做**：项目当前零自动化测试（`pyproject.toml` 无 pytest 等任何测试依赖；全仓库 `import pytest|unittest` 零命中）。后续批次涉及并发加锁、大文件拆分等有回归风险的改动，没有测试保护网无法验证正确性，只能靠人工联网肉眼核对。

**执行状态：已完成。** `uv run pytest` 75 个测试全部通过（0.4s，无网络依赖）。

## 任务

- [x] `pyproject.toml` 新增 `[dependency-groups].dev`，加入 `pytest>=8.3.0`（`uv lock` 解析到 `pytest 9.1.1`）；`uv lock` / `uv sync` 已同步。
- [x] 新建 `tests/` 目录，为以下**纯函数**（无网络/GUI 依赖）编写单元测试：
  - [x] `utils/prts_mediawiki_pipeline.py`：`_extract_template_body`（含嵌套模板/未闭合/前缀误匹配边界）、`_extract_all_template_bodies`、`_parse_template_params`（含竖线出现在链接/嵌套模板/HTML 注释内部的边界）、`_map_level_block`/`_map_common_block`、`merge_wikitext_enemy`（含多 levelcontent 按 index 覆盖、技能槽位合并、HTML 注释剥离、空分类兜底）、`to_enemy_data`（含 error 键短路、grade 校验失败返回 None、默认值、技能规整）—— 见 `tests/test_prts_mediawiki_pipeline.py`（29 个测试）。
  - [x] `utils/wiki_skia.py`：`parse_wikitext_to_spans`（加粗/颜色模板/术语/异常效果/内链/未闭合标记/多行/相邻同样式合并）、`wrap_spans_to_lines`（固定宽度换行、空输入、跨行样式保留）—— 见 `tests/test_wiki_skia.py`（14 个测试）。
  - [x] `core/render/layout.py`：`measure_grade_block_height`（最小高度兜底、评语变长增高）、`measure_render_height`（不低于配置高度、技能增多增高、大配置高度不被内容拉低）—— 见 `tests/test_layout.py`（5 个测试）。
  - [x] `models/`：`EnemyData`（等级枚举 S/A/B/C/D 含大小写拒绝、数值范围含边界值、头像路径 URL/本地文件校验、默认值）、`SkillEntry`（默认值、`is_nonempty`）—— 见 `tests/test_models.py`（27 个测试）。**不含 `CardStyle`**：该模型已确认为死代码（全仓库零调用点，宽高与实际渲染生效的 `RenderConfig` 数值不符），批次 4 计划删除，不为将删除的死代码编写测试。
- [x] `scripts/test_mediawiki_api.py` 改名为 `scripts/smoke_mediawiki_api.py`（用 `lsp`/编辑工具的文件移动完成，非文本复制），文件头 docstring 改为明确"人工联网冒烟脚本（非自动化测试，不接入 CI/pytest discovery）"，并注明自动化单元测试见 `tests/`。
- [x] 确认 `tests/` 目录被 `pytest` 默认 discovery 规则覆盖：`uv run pytest --collect-only` 收集到全部 75 个测试，无需在 `pyproject.toml` 添加 `[tool.pytest.ini_options]`。

## 验收标准

- [x] `uv run pytest` 在无网络环境下跑通并全部通过：**75 passed in 0.38s**。
- [x] `scripts/` 目录下不再有名字带 `test_` 前缀但实际是调试脚本的文件（`test_mediawiki_api.py` 已重命名，`scripts/` 现只有 `smoke_mediawiki_api.py`）。
- [x] 新增测试覆盖的函数清单与本文件列出的一致：`_extract_template_body`/`_extract_all_template_bodies`/`_parse_template_params`/`_map_level_block`/`_map_common_block`/`merge_wikitext_enemy`/`to_enemy_data`（prts 管线）、`parse_wikitext_to_spans`/`wrap_spans_to_lines`（wiki_skia）、`measure_grade_block_height`/`measure_render_height`（layout）、`EnemyData`/`SkillEntry` 校验规则（models），无凑数的空断言。

## 执行记录（供后续批次参考）

- 测试用真实 `FontManager()`（走本机 Windows 字体加载路径），未 mock skia 字体加载——`measure_render_height` 系列测试依赖真实字体测量结果的相对大小关系（如"技能越多渲染高度越大"），不关心具体像素值，因此不受字体是否成功加载影响，两种情况下测试都稳定。
- `_map_level_block` 的异常抗性字段测试过程中发现 `ABNORMAL_MAP` 的实际键名是"眩晕抗性"（非"晕眩抗性"），已按源码实际映射表修正测试数据，未改动源码本身。
- `_to_float`/`_clean_num_text` 不处理千分位逗号（如 `"1,000"` 会被截断为 `1`）——测试 fixture 避免使用带逗号的数值输入；如果 PRTS 页面实际会出现千分位格式，这是一个未覆盖的潜在解析问题，超出批次 0 范围（批次 0 只负责补测试，不改动业务逻辑），如需修复应在批次 3（PRTS 管线拆分）中一并处理。
