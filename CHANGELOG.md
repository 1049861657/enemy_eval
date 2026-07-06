# 变更日志

本文件记录 **enemy-eval** 各版本的变更，便于发布与回溯。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)。

撰写约定：

- **`[未发布]`**：已合并但未打版本号的改动；发布新版本时将整块剪切到对应版本号下并填写日期。
- **分类**（按需选用）：`新增` / `变更` / `修复` / `移除` / `安全`。
- **发布流程**：在 `pyproject.toml` 中 bump `[project].version` → 在本文件新增同名版本节 → 提交 / 打 tag。

---

## [未发布]

<!-- 下一版本发布前，把此处条目移到新版本下 -->

---

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