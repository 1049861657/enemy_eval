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

## [0.1.0] - 2026-05-06

**首个公开发布版本**（`pyproject.toml` `[project].version = "0.1.0"`）。

### 新增

- 基于 PySide6 的敌人评价卡片**实时编辑器**（模块化属性面板、预览区）。
- **动态版本号**：`utils/app_version.py` 从 `pyproject.toml` 或安装元数据读取；GUI / CLI 标题与关于对话框与此同步。
- **变更日志**：本文件 `CHANGELOG.md`，与版本号同步维护。
- **文档**：`CLAUDE.md` 中约定模块结构、发版流程（SemVer 进位）、可选 Git `tag` 说明。