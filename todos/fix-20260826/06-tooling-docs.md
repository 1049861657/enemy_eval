# 批次 6：文档索引

**风险等级**：P2 — 不改产品功能。已去掉原 6.1 Ruff（本仓库改代码走 AI，未接编辑器诊断闭环，单独加 Ruff 无收益）。

**执行状态：已完成。**

## 6.1 `AGENTS.md` 与目录事实对齐

- [x] 技术栈：Python 3.13；HTTP **httpx**（不再写 requests / Pillow / NumPy 为直接依赖）。
- [x] `models/`：`EnemyData` / `SkillEntry` / `RatingSchema` / `RenderOptions`。`AppSettings` 在 `utils/app_settings_store.py`。
- [x] 配置：敌人 JSON 仍 `data/{名}_config.json`；应用偏好 `platformdirs` 配置目录下 `app_settings.json`。
- [x] `resource/`：封面 `resource/pic/`，图标 `gui/qml/icons/`。
- [x] `utils`：`thread_manager` 延迟导入约定保留；PRTS 为 async + `asyncio.run`。
- [x] 验收：助手索引与仓库一致。

## 6.2 历史 todos 与发版备忘

- [x] `todos/fix-20260706/` 保持归档。
- [x] 全部完成后更新本 README 状态；`CHANGELOG`「未发布」用用户可感知语言追加。未要求发版则不 bump。
