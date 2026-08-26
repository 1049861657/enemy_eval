# 批次 3：评价偏好 JSON 与错误语义

**风险等级**：P0 — 对齐「配置一律 JSON」；保存失败不再打穿槽。

**执行状态：已完成。** store 只被 GUI/CLI 读，core 不依赖。路径库与批次 1 的 platformdirs 一致。

## 3.1 `AppSettings` + JSON 文件

- [x] 本机 `uv add pydantic-settings`（platformdirs 若批次 1 已加则不再加）。
- [x] `utils/rating_schema_store.py` 重写并改名为 `app_settings_store.py`（**不**留旧文件）。
- [x] 模型：`class AppSettings(BaseSettings)`，字段 `rating_names: list[str]`、`rating_radar: bool`。维度校验继续用 `RatingSchema`。`settings_customise_sources` 挂 `JsonConfigSettingsSource`，文件为 `platformdirs.user_config_path("敌人评价卡片编辑器", appauthor="Enemy Eval Team") / "app_settings.json"`。
- [x] 保存：`mkdir` 后 `model_dump_json` 写入同一路径。失败抛 `FileOperationError`（不要裸 `RuntimeError`）。
- [x] 损坏或缺失 → 默认三维 + `rating_radar=False`，warning 日志。
- [x] Windows 注册表旧 `QSettings` **不读不迁**。产品代码不再 `import QSettings`。
- [x] 测试：注入临时目录（函数参数或 env），更新 `tests/test_rating_schema.py`，去掉 `QSettings` 夹具。
- [x] 验收：改维度、切雷达、重启，json 文件仍在；进程不写注册表。

## 3.2 Bridge 捕获保存失败

- [x] `gui/qml_bridge.py::updateRatingSchema`、`setRatingRadar` 捕获 `FileOperationError`。
- [x] `fieldError` + UI 拨回当前 names / `is_rating_radar()`。
- [x] 验收：store 抛错时界面不崩。

## 3.3 `error_handler` 保留原因

- [x] `raise EnemyEvalException(f"{operation} 失败: {e}") from e`（现状对 UI 丢 `str(e)`，`error_handler.py:46-49`）。
- [x] 删除从未 raise 的 `utils.error_handler.ValidationError`；更新 `utils/__init__.py`。
- [x] 验收：现有错误处理测试仍过；打开坏 JSON 对话框含具体原因。
