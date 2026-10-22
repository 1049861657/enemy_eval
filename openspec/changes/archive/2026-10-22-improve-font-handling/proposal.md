# Proposal

## Why

卡片渲染目前只认 4 个硬编码的 Windows 字体路径（`core/render/fonts.py::_FONT_PATHS`），没有系统字体枚举，也没有随包字体。英文版或精简版 Windows 可能一个都命中不了，中文会渲染成方框；同一份配置在不同机器上导出的文字宽度与换行也可能不同。

## What Changes

- 随包 HarmonyOS Sans SC Regular（HarmonyOS Sans 字体许可，约 7.9 MB）及许可证；卡片渲染始终使用随包字体，保证跨机器输出一致。
- 删除硬编码字体路径；随包文件缺失或损坏时，才按字体族回退到系统中文字体并告警。
- UI 字体改为显式回退栈：Microsoft YaHei UI → Microsoft YaHei → Segoe UI → HarmonyOS Sans SC（随包字体注册给 Qt），不再依赖单一族名。
- 打包产物与构建校验都包含字体文件与许可证。
- 不提供用户自定义字体，不做按字表子集化，不改变卡片布局；本轮不做逐字符回退（现有绘制全链路使用单一 Typeface，随包字体已覆盖常用中文）。

## Capabilities

### New Capabilities

- `font-handling`: 规定界面与卡片渲染的字体来源、回退顺序、随包字体、许可与确定性要求。

### Modified Capabilities

无。现有 specs 未覆盖字体行为。

## Impact

- 渲染：`core/render/fonts.py` 的字体加载与回退逻辑。
- 界面：`gui/qml/Theme.qml` 的字体族回退逻辑（按 `Qt.fontFamilies()` 选择首个可用族）。
- 启动：`gui_main.py` 用 Qt 注册随包字体，供界面回退使用。
- 资源与打包：新增 `resource/fonts/HarmonyOS_Sans_SC_Regular.ttf` 与 HarmonyOS Sans 字体许可；`enemy_eval.spec` 已收集整个 `resource/`，需在 `scripts/build_release.py` 的产物校验中增加字体检查；包体增加约 7.9 MB。
- 测试：布局测量在不同机器上可复现，为后续像素/尺寸回归提供基础。
- 无新增 Python 依赖；字体文件随包分发。
