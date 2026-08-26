# 批次 4：GUI / QML 可维护性

**风险等级**：P1 — 不改交互语义。技能列表走官方 Qt 模型，不再整表 JSON 往返。

**执行状态：待执行。**

## 4.1 拆 `Workspace.qml`

- [ ] 现状：891 行。`PreviewViewport.qml` 已独立，不要再拆预览。
- [ ] 按页拆（PascalCase）：`EditorBasicsPage` / `EditorCombatPage` / `EditorResistPage` / `EditorSkillsPage` / `EditorRatingPage` / `CommandBar` / `PrtsQueryDialog`。
- [ ] `Workspace.qml` 只留 controller、刷新、`TabBar`+`StackLayout`、预览、确认框。
- [ ] 五页即时可用，不用动态 `Loader` 源文件。
- [ ] 验收：字段、雷达、PRTS、快捷键与拆前一致。

## 4.2 序列化与技能模型

- [ ] `enemyDataJson`：`enemy_data.model_dump_json(ensure_ascii=False)`，去掉 `json.dumps(get_current_dict())`。
- [ ] 标量表单仍 `JSON.parse` 这份字符串（40+ 字段全改 `Property` 本轮不做）。
- [ ] 新增 `gui/skill_list_model.py`：`QAbstractListModel`，角色覆盖名称/类型/描述等；QML `Repeater`/`ListView` 绑 `controller.skills`。增删改走 model 的 slot，不再整表 JSON 往返技能数组。
- [ ] 验收：改 HP、加/删/改技能，表单与预览仍同步；连续输入技能描述时不再每次 `JSON.parse` 整份敌人（可用日志或 profiler 确认 dump 体积下降）。

## 4.3 导入上顶

- [ ] `models/enemy_data.py`、`core/optimization.py`、`utils/prts_field_mapping.py`、`gui_main.py::create_splash_screen`：导入移到文件顶。
- [ ] **保留** 两个 `run()` 内对 `core` 的延迟导入。
- [ ] 验收：函数体内 `import` 仅剩上述 `run()`。

## 4.4 启动依赖提示

- [ ] `gui_main.py`：提示改为 `uv sync`；检查列表与批次 5 实际依赖一致（skia / pydantic / PySide6 / httpx）。
