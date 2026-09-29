# 变更日志

本文件记录 **enemy-eval** 各版本的变更，便于发布与回溯。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)。

撰写约定：

- **`[未发布]`**：日常提交追加用户可感知改动；发版时整块剪切到版本节。
- **分类**（按需选用）：`新增` / `变更` / `修复` / `移除` / `安全`。
- **发布流程**：在 `pyproject.toml` 中 bump `[project].version` → 在本文件新增同名版本节 → 提交 / 打 tag。

---

## [未发布]

### 变更

- 保存配置时头像改为跟随配置文件所在目录记录，换机或分享配置后仍能显示头像
- 提示条由右上角移到顶部居中，并按语义区分成功、提示、警告、错误四种语气

### 修复

- 头像文件缺失或配置被移动后，配置仍能正常打开，头像区按无头像显示并给出警告提示
- 主窗口标题不再重复显示应用名
- 打开含网络头像的配置、或手动填写头像链接后，卡片头像不再缺失
- 命令行入口恢复可用，此前启动即报错退出
- 偏好文件损坏时按默认值启动，不再中断启动

<!-- 下一版本发布前，把此处条目移到新版本下 -->

---

## [0.4.0] - 2026-08-26

### 新增

- 评价区可在雷达图与记分板之间切换，选择会记住
- 卡片绘制补齐 popup、特殊机制、异常效果等 wiki 内联模板
- 运行日志写入本机日志目录，按大小滚动保留

### 变更

- QML 按 Qt 6.11 规范收敛：`controller` 改为根组件 required 属性注入；启用 `ComponentBehavior: Bound`；delegate 使用限定访问；Layout 子项改用 preferred 尺寸
- 评价维度达上限时，「添加维度」改为禁止符号提示
- 关于对话框显示构建阶段写入制品的 UTC 构建日期
- 关于对话框不再列出技术栈
- 运行环境改为 Python 3.13
- 导出图片默认文件名改为敌人原名，不再附带等级后缀
- 评价维度与雷达图偏好改为保存在用户配置目录的 JSON 文件，不再写入注册表；升级后不会沿用旧注册表里的设置
- 缺少依赖时提示改为在项目根目录运行 `uv sync`
- 从 PRTS 拉取参考数据时关闭窗口，可在数秒内退出，不再卡住
- 保存配置与导出图片的默认文件名会去掉 Windows 不允许的字符

### 修复

- 关闭窗口时不再强制杀死后台线程
- 打包后的程序预览卡片不再因缺少 numpy 失败
- 界面加载失败时弹出错误说明并退出，不再停在白屏
- 保存评价标准或切换雷达图失败时，界面回退为已保存内容
- 打开损坏的配置文件时，错误对话框会显示具体原因
- 依赖缺失与启动失败对话框的换行能正常显示

### 移除

- 取消编辑器标签页 Ctrl+1 至 Ctrl+5 快捷键切换
- 去掉已不再使用的旧界面图标，预览渲染不再走写文件路径

---

## [0.3.0] - 2026-07-15

### 新增

- 编辑器界面改用 Qt Quick 重写
- 支持自定义评价维度（0 至 5 项），可在应用内编辑评价标准
- 编辑器标签页支持 Ctrl+1 至 Ctrl+5 快捷键切换
- 下拉选择框支持键盘操作，并正确显示不在预设列表中的历史选项

### 变更

- 统一控件焦点与高亮样式，评分、按钮、输入框等交互反馈更清晰
- 技能与评价区块改用图标操作，空技能列表显示占位提示
- PRTS 参考数据导入成功后改为状态栏提示，不再弹出确认框

### 修复

- 打开、保存配置文件或导出图片失败时显示具体错误原因
- 属性校验失败时界面自动恢复为已保存内容，避免显示与数据不一致
- 编辑技能时不再意外丢失未填写的技能槽

---

## [0.2.0] - 2026-07-07

### 新增

- **异步 PRTS 拉取**：新增 `utils/thread_manager.py::PrtsFetchThread`，`gui/main_window.py::_fetch_prts_data` 由同步阻塞改为后台线程执行，消除最长 34 秒的主线程冻结；`_reference_prts` 新增并发拉取守卫，`closeEvent` 补充线程等待/终止逻辑。
- **测试**：新增 `tests/test_prts_pipeline_refactor.py`（19 个）、`tests/test_gui_signals.py`（13 个）+ `tests/conftest.py`（headless QApplication fixture），`uv run pytest` 累计 107 个测试通过。

### 变更

- **PRTS 数据管线拆分**：690 行的 `utils/prts_mediawiki_pipeline.py` 按职责拆分为 `prts_api_client.py`（HTTP Session/超时/重试）、`wiki_template_parser.py`（纯 wikitext 解析）、`prts_field_mapping.py`（字段映射与合并规则）、`prts_enemy_builder.py`（EnemyData 组装）5 个模块；原文件瘦身为编排门面。Skia 头像缓存逻辑移至新增的 `core/render/avatar_prefetch.py`，消除 `utils` 反向依赖 `core` 的方向性违规。
- `core/optimization.py` 新增 `_GLOBAL_IMAGE_CACHE_LOCK`，保护渲染线程与 PRTS 拉取线程对全局图片缓存的并发读写。

### 修复

- **敌我同名单位查询报错**：弑君者、W 等敌人查询报错"未找到敌人 wikitext 模板（common2 / levelcontent）"——裸名命中的是同名干员页而非敌人页。新增 `utils/prts_api_client.py::resolve_enemy_page_title`，用 Semantic MediaWiki 的 `action=ask`（`[[分类:敌人]][[名称::<name>]]`）精确解析敌人页面标题，替代此前"猜测 `(敌方)` 后缀重试"的方案（PRTS 消歧义后缀并不统一，还有 `变格博士(敌人)` 等猜测式重试无法覆盖的情况）。
- **PRTS 查询延迟**：`resolve_enemy_page_title` 改用独立零重试、4 秒短超时的 Session，避免遇上 PRTS 源站瞬时抖动（Varnish 502/503）时，因默认 Session 的指数退避重试把单次查询拖到 10+ 秒，拖累整条 `ask → parse → imageinfo` 串行链路耗时；超时或未命中时退回按裸名 `parse`。
- **面板信号连接**：`combat_stats_panel._refresh_from_model` 补上 `blockSignals` 守卫，消除刷新赋值期间的信号风暴；6 处面板 `_connect_signals()` 统一加幂等保护，杜绝重复 `connect` 导致同一控件信号被多次触发；修复新建卡片 3 次后导出按钮触发 3 次 `_export_image` 确认弹窗的 bug。

## [0.1.1] - 2026-07-06

### 新增

- **测试基础设施**：新增 `tests/` 目录，75 个 pytest 单元测试覆盖 PRTS MediaWiki 数据管线（模板解析、字段映射、多 levelcontent 合并、EnemyData 构建）、wikitext 转绘制片段解析、卡片渲染高度测算、`EnemyData`/`SkillEntry` 数据模型校验规则，全部无网络依赖，可离线跑通。
- **开发工具链**：`pyproject.toml` 新增 `[dependency-groups].dev`，引入 `pytest` 与 `pyright`（后者用于编辑器 LSP 类型感知重命名/引用查找），均为纯开发依赖，不影响运行时与打包产物。

### 变更

- `scripts/test_mediawiki_api.py` 更名为 `scripts/smoke_mediawiki_api.py`，消除其"看起来像自动化测试"的误导性命名，明确定位为人工联网冒烟脚本。
- `CLAUDE.md` 精简重写为面向 AI 助手的强约束速查文档（技术栈、必须遵守事项、防循环依赖架构要点、目录索引、发版规则）。
- 依赖版本下限提升：`pillow`、`skia-python`、`pydantic`、`rich`、`numpy`、`pyside6`、`pyinstaller`、`pyinstaller-hooks-contrib`、`requests`、`beautifulsoup4`。

### 修复

- **渲染线程并发竞态**：卡片预览的渲染线程编排此前在高频连续编辑时可并发运行多个 `CardGeneratorThread`，同时访问 `core.optimization` 的全局共享单例（Canvas 池、字体缓存、图像缓存），存在数据竞争与画面撕裂风险。现改为异步串行化——任意时刻只允许一个渲染线程运行，排队请求延迟到上一线程结束后才发起，全程不阻塞主界面。
- 图像缓存（`_GLOBAL_IMAGE_CACHE`）淘汰策略修正为真正的 LRU（原实现按插入顺序淘汰，与其"LRU"注释不符，命中不刷新顺序）。

---

## [0.1.0] - 2026-05-06

**首个公开发布版本**（`pyproject.toml` `[project].version = "0.1.0"`）。

### 新增

- 基于 PySide6 的敌人评价卡片**实时编辑器**（模块化属性面板、预览区）。
- **动态版本号**：`utils/app_version.py` 从 `pyproject.toml` 或安装元数据读取；GUI / CLI 标题与关于对话框与此同步。
- **变更日志**：本文件 `CHANGELOG.md`，与版本号同步维护。
- **文档**：`CLAUDE.md` 中约定模块结构、发版流程（SemVer 进位）、可选 Git `tag` 说明。