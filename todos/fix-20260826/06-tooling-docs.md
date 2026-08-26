# 批次 6：工具链与文档索引

**风险等级**：P2 — 不改产品功能。

**执行状态：待执行。**

## 6.1 Ruff（开发依赖）

- [ ] `uv add --dev ruff`。
- [ ] `pyproject.toml`：

```toml
[tool.ruff]
target-version = "py313"
src = ["."]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
ignore = ["E501"]
```

- [ ] 本轮只修本计划触及的文件；不强制全仓库 `ruff format`。
- [ ] 验收：`uv run ruff check gui core models utils gui_main.py main.py` 无新增 F 类错误。

## 6.2 `AGENTS.md` 与目录事实对齐

- [ ] 技术栈：Python 3.13；HTTP **httpx**（不再写 requests / Pillow / NumPy 为直接依赖）。
- [ ] `models/`：`EnemyData` / `SkillEntry` / `RatingSchema` / `RenderOptions` / `AppSettings`。
- [ ] 配置：敌人 JSON 仍 `data/{名}_config.json`；应用偏好 `platformdirs` 配置目录下 `app_settings.json`。
- [ ] `resource/`：封面 `resource/pic/`，图标 `gui/qml/icons/`。
- [ ] `utils`：`thread_manager` 延迟导入约定保留；PRTS 为 async + `asyncio.run`。
- [ ] 验收：助手索引与仓库一致。

## 6.3 历史 todos

- [ ] `todos/fix-20260706/` 保持归档。
- [ ] 全部完成后更新本 README 状态；`CHANGELOG`「未发布」用用户可感知语言追加（httpx、可取消拉取、设置改 JSON 等）。未要求发版则不 bump。
