# Tasks

## 1. 字体资源与许可

- [x] 1.1 从 `huawei-fonts/HarmonyOS-Sans` 的 `HarmonyOS Sans/HarmonyOS_Sans_SC/HarmonyOS_Sans_SC_Regular.ttf` 下载字体到 `resource/fonts/HarmonyOS_Sans_SC_Regular.ttf`；验证：文件大小 8,261,128 字节，且记录 SHA-256 到提交说明
- [x] 1.2 从 HarmonyOS Sans 字体包的 `HarmonyOS Sans/HarmonyOS_Sans_SC/LICENSE.txt` 提取许可证到 `resource/fonts/LICENSE.txt`；验证：文件包含 `HarmonyOS Sans Fonts License Agreement` 与 `Copyright 2021 Huawei Device Co., Ltd.`

## 2. 卡片字体解析

- [x] 2.1 重写 `core/render/fonts.py`：优先从 `resource_manager.get_resource_path("resource/fonts/HarmonyOS_Sans_SC_Regular.ttf")` 加载，失败时按 `Microsoft YaHei UI → Microsoft YaHei → SimHei → HarmonyOS Sans SC → Noto Sans CJK SC → Source Han Sans SC` 调用 `skia.FontMgr().matchFamilyStyle`，删除 `_FONT_PATHS`；验证：一次性脚本加载 `FontManager()`，`chinese_font` 非 None 且 `unicharToGlyph(ord("敌")) != 0`
- [x] 2.2 保留进程内 Typeface 与按字号的模板缓存；验证：连续创建两个 `FontManager`，第二次不重复读取字体文件（日志/调用计数），且同字号 `get_font` 返回独立实例
- [x] 2.3 模拟随包字体缺失：一次性脚本把资源路径指向不存在的文件；验证：回退到系统字体族或返回 None 并记录告警，不抛异常

## 3. 界面字体栈与注册

- [x] 3.1 `gui/qml/Theme.qml` 保留 `fontFamily: string`，按 `Microsoft YaHei UI → Microsoft YaHei → Segoe UI → HarmonyOS Sans SC` 顺序从 `Qt.fontFamilies()` 选择首个已安装族；验证：`grep` 无 `fontFamilies` 残留，`pyside6-qmllint -I gui/qml gui/qml/Theme.qml` 退出码为 0
- [x] 3.2 `gui_main.py` 在 `QApplication` 创建后、`MainWindow` 之前调用 `QFontDatabase.addApplicationFont` 注册随包字体；验证：一次性 offscreen 脚本注册后 `QFontDatabase.applicationFontFamilies(id)` 包含 `HarmonyOS Sans SC`，注册失败路径只记 warning
- [x] 3.3 验证 `Qt.fontFamilies()` 在选择属性中可用：GUI 启动后 `Theme.fontFamily` 为系统中实际存在的族；验证：手工运行 GUI，检查界面字体与缺字情况，qmllint 无警告

## 4. 打包与校验

- [x] 4.1 `scripts/build_release.py::_validate` 的必需列表增加 `_internal/resource/fonts/HarmonyOS_Sans_SC_Regular.ttf` 与 `_internal/resource/fonts/LICENSE.txt`；验证：人为移除该文件后 `_validate` 抛出缺失项，恢复后通过
- [x] 4.2 确认 `enemy_eval.spec` 的 `project_data` 会把 `resource/fonts/` 收进 `_internal/resource/fonts/`，无需新增 datas；验证：构建后检查产物路径

## 5. 验证

- [x] 5.1 运行现有布局测试：`uv run pytest tests/test_layout.py`；验证：全部通过，不新增 pytest 用例
- [x] 5.2 生成一张含中文名称、技能与评语的卡片，人工对比切换前后的字形、换行与高度；验证：中文无方框，布局无溢出
- [x] 5.3 执行 `uv run python scripts/build_release.py`，验证 zip 内包含 `enemyEval/_internal/resource/fonts/HarmonyOS_Sans_SC_Regular.ttf` 与 `LICENSE.txt`，且体积增量约 8 MB

## Workflow follow-up

- 按项目审查要求完成评审后归档该变更。
- 验证归档后的 `openspec/specs/font-handling/spec.md` 内容完整。
