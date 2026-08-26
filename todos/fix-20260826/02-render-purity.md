# 批次 2：渲染纯化与单一绘制路径

**风险等级**：P0 — 全局最优的核心：渲染是 `(EnemyData, RenderOptions) → 图`，不再读全局 Qt 偏好。

**执行状态：待执行。** 依赖批次 1 的日志，便于对比预览耗时。

## 2.1 引入 `RenderOptions`

- [ ] 位置：新建 `models/render_options.py`（或放 `core/render/options.py`；优先 `models`，与 Pydantic 数据一处）。
- [ ] 字段：`rating_names: list[str]`、`rating_radar: bool`。用 Pydantic 或 frozen dataclass；GUI 传入已校验的名称列表即可，不必再校验维度上限（那是 schema 的事）。
- [ ] `EnemyCardGenerator.generate_card_image(enemy, options)` 与 `generate_card(enemy, options, output_path=...)` **都接收 options**。
- [ ] `core/render/generator.py`、`sections/rating_grade.py` **删除** `from utils.rating_schema_store import ...`。
- [ ] 高度测算 `layout.measure_render_height` / `draw_rating_section` 使用 `options`，不读全局。
- [ ] GUI：`RenderCoordinator.request` 与 `CardGeneratorThread` 携带 `options` 快照（`model_copy` 敌人数据的同时拷贝 options），避免渲染中途切雷达导致撕裂。
- [ ] 验收：`grep core/ | rating_schema_store` 无匹配。改雷达开关仍只影响下一帧预览（现行为）。

## 2.2 合并两条绘制实现

- [ ] 现状：`generate_card` 与 `generate_card_image` 复制 `_init_canvas` + 五段 `draw_*`。
- [ ] 修复：唯一私有 `_draw_card(enemy, options) -> skia.Image`；`generate_card_image` 返回该图；`generate_card` 对其 `save` PNG。CLI `main.py` 构造默认 `RenderOptions`（当前 schema + 雷达开关从 store 读一次，或写死默认记分板——CLI 是演示，用 store 一次读取可接受，**core 内部仍不读 store**）。
- [ ] `PerformanceTimer` 只包 `_draw_card` 一次，DEBUG 日志。
- [ ] 验收：CLI 与 GUI 预览同一套绘制顺序；功能视觉不变。

## 2.3 画布池（保持 CPU，小改）

- [ ] 默认高度走现有 pool（已实现）。
- [ ] 可变高度：保持现「按高度 `Surface`」；不要引入 GPU。
- [ ] 可选（本批次若时间不够可跳过）：按 `height` 缓存 1 张备用 Surface，避免每次 `new`。不做多尺寸大池。
- [ ] 验收：长技能卡片仍拉高画布，无裁切。

## 2.4 死符号

- [ ] 删除未调用的 `RenderResourceManager.get_performance_stats`。
- [ ] 验收：`grep get_performance_stats` 仅历史 todos（若有）。
