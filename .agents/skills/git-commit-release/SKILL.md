---
name: git-commit-release
description: 为 enemy-eval 仓库生成规范化 git commit message，并在用户明确要求发版时按 SemVer 规则自适应更新 pyproject.toml 版本号与 CHANGELOG.md。仅当用户在本轮对话中明确提出"生成 commit"、"写提交信息"、"帮我提交"、"发版"、"release"、"bump 版本"等请求时使用；改动做完、测试通过后，即使看起来"该提交了"，也不要主动调用本 skill 或执行 git commit——停下来汇报结果，等待用户明确要求。
---

# Git Commit & 版本发布助手

本 skill 覆盖两个独立场景，不要混淆：

**硬约束：本 skill 不主动触发。** 无论改动大小、测试是否通过，只要用户没有在本轮明确说"提交"/"commit"/"发版"/"release"类的话，完成改动和验证后就应该停下汇报，不得自行进入下面任何场景并执行 `git commit`。

- **场景 A：生成 commit message**（仅在用户明确要求时执行）
- **场景 B：发版 / release**（仅当用户明确要求"发版"、"release"、"bump 版本"时才执行，参见 `CLAUDE.md` 第 49 行约束）

---

## 场景 A：生成 Commit Message

### 1. 先看变更，不要凭猜测编造

```
git status
git diff --staged   # 已 add 的部分
git diff             # 未 add 的部分
```

未 add 的文件先与用户确认是否需要 `git add`；不要擅自 `git add -A` 吞掉不相关的改动。

### 2. Message 格式（Conventional Commits，仓库既有约定）

```
<type>(<scope>): <中文祈使句描述>

- [<模块或方面>] <具体做了什么，为什么>
- [<模块或方面>] <第二条，如需要>
```

规则：

- **不加 emoji**。仓库早期 commit 带 ✨/♻️ 前缀，但最近两次（`bf09147`、`3d9305a`）已弃用，遵循最新约定。
- `type` 取值：`feat`（新功能）/ `fix`（修复）/ `refactor`（重构，无行为变化）/ `chore`（杂项，如版本号、依赖）/ `docs`（仅文档）/ `perf`（性能）/ `style`（纯格式）。
- `scope` 用改动涉及的模块名，取自目录名或功能域：`gui`、`core`、`models`、`utils`、`prts`、`packaging`、`版本` 等；跨多个模块时用 `+` 连接，如 `models+core+gui`。
- 标题行（`<type>(<scope>): ...`）**祈使/概括式中文**，不超过约 30 字，不写句号。
- 正文用 `- [方面] 说明` 项目符号，仅在改动值得解释"为什么/影响"时才加正文；纯小改动可以只有标题行（参考 `feat(版本): 统一运行时版本号来源至 pyproject.toml` 这类单行 commit 也存在于历史中，但复杂改动应展开正文，参考 `bf09147`）。
- 正文按**改动的实际内容**撰写，禁止编造未发生的改动；每条对应一个真实的文件/逻辑变化。

### 3. 生成后的动作

把生成的 message 交给用户确认（或按用户已表达的自动化程度直接执行），执行：

```
git commit -m "<标题行>" -m "<正文>"
```

多行正文用多个 `-m`，或用 heredoc 写入临时文件后 `git commit -F <file>`（避免 shell 转义问题）。

**禁止**：未经用户明确授权不得 `git push`。

---

## 场景 B：发版（Release）

仅当用户明确说"发版"、"release"、"发布新版本"、"bump 版本"时执行。日常 commit（场景 A）不触发本流程。

### 1. 确定新版本号（SemVer：X.Y.Z）

读取当前版本：`pyproject.toml` 的 `[project].version`（唯一权威来源，`utils/app_version.py` 从此读取）。

**硬约束（来自 `CLAUDE.md`，不可违反）**：

- AI **只能建议或修改 Y 或 Z**。
- **禁止修改 X**（大版本号），除非用户在本次对话中手写明确指定新的 X 值。
- 判断依据：对比 `CHANGELOG.md` 的 `[未发布]` 小节与实际 `git log` / `git diff`：
  - 改动较大（新增重要功能、涉及多模块、用户可感知的行为变化）→ `Y+1`，`Z=0`。
  - 改动较小（修复、小优化、单模块微调）→ `Z+1`。
- 如果无法判断改动量级是"大"还是"小"，向用户简述改动清单并询问，而不是擅自猜测。

### 2. 更新 `CHANGELOG.md`

- 将 `## [未发布]` 小节下的条目，剪切整理到新的 `## [X.Y.Z] - <今天日期 YYYY-MM-DD>` 小节下。
- 按 Keep a Changelog 分类归类：`新增` / `变更` / `修复` / `移除` / `安全`（按需选用，没有对应类别的不要留空标题）。
- 条目要对应真实改动，禁止编造。
- 在原 `## [未发布]` 位置保留空壳（标题 + 占位注释），供下次改动继续追加。

### 3. 更新 `pyproject.toml`

```toml
[project]
version = "X.Y.Z"
```

只改这一处版本号字符串，不动其他字段。

### 4. 提交与打 tag

```
git add pyproject.toml CHANGELOG.md
git commit -m "chore: release X.Y.Z"
git tag -a vX.Y.Z -m "release X.Y.Z"
```

**禁止**未经用户明确授权执行 `git push` 或 `git push --tags`。

### 5. 收尾检查清单

- [ ] `pyproject.toml` 版本号与 `CHANGELOG.md` 新增小节版本号一致
- [ ] `CHANGELOG.md` 的 `[未发布]` 小节已清空并保留占位
- [ ] commit message 遵循 `chore: release X.Y.Z` 格式
- [ ] tag 名称为 `vX.Y.Z`（注意前缀 `v`，与仓库已有 tag `v0.1.0` 一致）
- [ ] 未执行任何 `push`，除非用户明确要求

---

## 参考：本仓库既有约定原文

详见 `CLAUDE.md` "发版（仅当用户明确要求发版 / release）" 一节与 `CHANGELOG.md` 顶部"撰写约定"。本 skill 是对这两处规则的可执行展开，若两者冲突以 `CLAUDE.md` / `CHANGELOG.md` 原文为准（说明文档可能已被用户更新）。
