# 批次 0：引入测试基础设施

**为什么最先做**：项目当前零自动化测试（`pyproject.toml` 无 pytest 等任何测试依赖；全仓库 `import pytest|unittest` 零命中）。后续批次涉及并发加锁、大文件拆分等有回归风险的改动，没有测试保护网无法验证正确性，只能靠人工联网肉眼核对。

## 任务

- [ ] `pyproject.toml` 新增 `[dependency-groups].dev`（或 `[project.optional-dependencies].dev`），加入 `pytest`；`uv lock` / `uv sync` 同步。
- [ ] 新建 `tests/` 目录，为以下**纯函数**（无网络/GUI 依赖，最容易测且价值最高）编写单元测试：
  - [ ] `utils/prts_mediawiki_pipeline.py`：`_extract_template_body`、`_parse_template_params`、`merge_wikitext_enemy`、`to_enemy_data`（用固定 wikitext 字符串 fixture，不发真实网络请求）。
  - [ ] `utils/wiki_skia.py`：`parse_wikitext_to_spans`、`wrap_spans_to_lines`。
  - [ ] `core/render/layout.py`：`measure_render_height` 等测量函数（给定 `EnemyData` 样例，断言返回的高度符合预期范围）。
  - [ ] `models/`：`EnemyData`/`SkillEntry`/`CardStyle` 的字段校验规则（等级枚举、URL 校验、数值范围）。
- [ ] `scripts/test_mediawiki_api.py` 改名为 `scripts/smoke_mediawiki_api.py`，消除"看起来像 pytest 测试"的误导性命名；文件头注释明确"人工联网冒烟脚本，非自动化测试，不接入 CI"。
- [ ] 确认 `tests/` 目录被 `pytest` 默认 discovery 规则覆盖（无需额外配置 `pyproject.toml` 的 `[tool.pytest.ini_options]` 也可运行，如需自定义 testpaths 再补充）。

## 验收标准

- `uv run pytest` 可在无网络环境下跑通并全部通过。
- `scripts/` 目录下不再有名字带 `test_` 前缀但实际是调试脚本的文件。
- 新增测试覆盖的函数清单与本文件列出的一致，不多不少（避免为凑数写无意义的 assert True）。
