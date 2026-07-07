---
name: git-commit-release
description: 用户明确要求"生成 commit"/"提交"/"发版"/"release"/"bump 版本"时，为 enemy-eval 仓库生成规范化 git commit message，或按 SemVer 更新 pyproject.toml + CHANGELOG.md 并打 tag。不主动触发——改动做完、测试通过后即使该提交了，也停下汇报，等用户明确要求。
---

# Git Commit & 版本发布助手

本 skill 覆盖两个独立场景，触发条件见上方 description，不主动进入任何场景。

- **场景 A：生成 commit message**
- **场景 B：发版 / release**（另见 `CLAUDE.md`「发版（仅当用户明确要求发版 / release）」一节）

---

## 场景 A：生成 Commit Message

### 1. 先看变更，不要凭猜测编造

```
git status
git diff --staged   # 已 add 的部分
git diff             # 未 add 的部分
```

**默认范围：工作区当前全部未提交改动（已 add + 未 add）一次性合并进这一个 commit，不主动拆分。** 只有明确认出某处改动与本次任务无关（例如误触的临时文件、他人并行改动）时，才向用户确认是否要拆出去单独处理；改动看起来分属不同模块/文件不构成拆分理由——一次任务的产出即使跨多个模块，也归为一个 commit。未 add 的文件直接 `git add` 纳入这次范围，不要擅自 `git add -A` 之外再自行漏选或分批。

### 2. Message 格式（Conventional Commits，仓库既有约定）

```
<type>(<scope>): <中文祈使句描述>

- [<模块或方面>] <具体做了什么，为什么>
- [<模块或方面>] <第二条，如需要>
```

规则：

- **不加 emoji**。
- `type` 取值：`feat`（新功能）/ `fix`（修复）/ `refactor`（重构，无行为变化）/ `chore`（杂项，如版本号、依赖）/ `docs`（仅文档）/ `perf`（性能）/ `style`（纯格式）。
- `scope` 用改动涉及的模块名，取自目录名或功能域：`gui`、`core`、`models`、`utils`、`prts`、`packaging`、`版本` 等；跨多个模块时用 `+` 连接，如 `models+core+gui`。
- 标题行（`<type>(<scope>): ...`）**祈使/概括式中文**，不超过约 30 字，不写句号。
- 正文用 `- [方面] 说明` 项目符号，仅在改动值得解释"为什么/影响"时才加正文；纯小改动可以只有标题行。
- 正文按**改动的实际内容**撰写，禁止编造未发生的改动；每条对应一个真实的文件/逻辑变化。

### 3. 生成后的动作

把生成的 message 交给用户确认（或按用户已表达的自动化程度直接执行）。

- 正文只有一行或没有正文：
  ```
  git commit -m "<标题行>" -m "<单行正文，可省略>"
  ```
- 正文是多行项目符号：**必须**写入临时文件后 `-F` 提交，禁止塞进多个 `-m`（换行会被 shell 吃掉，条目连成一行）。正文若含以 `#` 开头的行（如 Markdown 三级标题 `### xxx`），**必须**加 `--cleanup=verbatim`，否则 git 会把这些行当注释静默剥离：
  ```
  git commit -F .git/COMMIT_MSG_DRAFT --cleanup=verbatim
  rm -f .git/COMMIT_MSG_DRAFT
  ```
  （临时文件第一行是标题，空一行后接正文）

**禁止**：未经用户明确授权不得 `git push`。

---

## 场景 B：发版（Release）

日常 commit（场景 A）不触发本流程。

### 1. 确定新版本号（SemVer：X.Y.Z）

读取当前版本：`pyproject.toml` 的 `[project].version`（唯一权威来源，`utils/app_version.py` 从此读取）。

**硬约束（来自 `CLAUDE.md`，不可违反）**：

- AI **只能建议或修改 Y 或 Z**。
- **禁止修改 X**（大版本号），除非用户在本次对话中手写明确指定新的 X 值。
- 判断依据：对比 `CHANGELOG.md` 的 `[未发布]` 小节与实际 `git log` / `git diff`，按顺序检查：
  1. 新增用户可见的完整功能、涉及 2 个及以上模块的结构性改动、破坏或显著改变既有行为 → `Y+1`，`Z=0`。
  2. 仅修复 bug、纯性能优化、单模块内部重构、文档/依赖调整 → `Z+1`。
  3. 同时命中 1 和 2：功能层面达到第 1 条标准就按 `Y+1`；否则按 `Z+1`。
  4. 仍拿不准：列出 `[未发布]` 条目问用户"这次算 Y+1 还是 Z+1"，不要自己猜。

### 2. 更新 `CHANGELOG.md`

- 将 `## [未发布]` 小节下的条目，剪切整理到新的 `## [X.Y.Z] - <今天日期 YYYY-MM-DD>` 小节下。
- 按 Keep a Changelog 分类归类：`新增` / `变更` / `修复` / `移除` / `安全`（按需选用，没有对应类别的不要留空标题）。
- 条目要对应真实改动，禁止编造。
- 在原 `## [未发布]` 位置保留空壳，格式：`## [未发布]` 一行 + 空行 + `<!-- 下一版本发布前，把此处条目移到新版本下 -->` 一行，供下次改动继续追加。

### 3. 更新 `pyproject.toml`

```toml
[project]
version = "X.Y.Z"
```

只改这一处版本号字符串，不动其他字段。若 `uv.lock` 中的 `enemy-eval` 版本号随之自动同步（如运行过 `uv run`/`uv sync`），一并提交，不要单独遗留。

### 4. 提交与打 tag：commit 承载详情，tag 只做一行版本指针

`chore: release X.Y.Z` 作为 **commit** 标题行单独一行信息量为零——`git log` 必须能直接看到这一版做了什么，所以 commit **正文**照抄第 2 步写入 `## [X.Y.Z]` 的分类条目。

**tag message 与 commit message 不同，禁止同步复制分类条目**：tag message 固定写 `release X.Y.Z` 一行，不写分类标题、不写条目；详细变更只进 commit message 与 `CHANGELOG.md`，从不塞进 tag object。

**关键陷阱**：commit 正文含 `### 新增`/`### 变更`/`### 修复` 这类 `#` 开头的 Markdown 标题行时，`git commit -F` **默认会把这些行当注释静默剥离**（git 的 `--cleanup=strip` 默认行为），标题行会无声消失、只剩条目列表。**必须加 `--cleanup=verbatim`** 保留原文。

执行：

```
git add pyproject.toml CHANGELOG.md
```

把 commit 说明写入临时文件（如 `.git/COMMIT_MSG_DRAFT`）。**只复制 CHANGELOG 本版本实际存在的分类**，下面模板里的三个标题是全量示例——本版本没有的分类整个标题一起删掉，不要留空标题：

```
chore: release X.Y.Z

### 新增

- <照抄 CHANGELOG.md 本版本「新增」下的全部条目>

### 变更

- <照抄 CHANGELOG.md 本版本「变更」下的全部条目>

### 修复

- <照抄 CHANGELOG.md 本版本「修复」下的全部条目>
```

然后 commit 用这个文件（`--cleanup=verbatim`），tag 单独用一行 `-m`：

```
git commit -F .git/COMMIT_MSG_DRAFT --cleanup=verbatim
git tag -a vX.Y.Z -m "release X.Y.Z"
rm -f .git/COMMIT_MSG_DRAFT
```

**禁止**未经用户明确授权执行 `git push` 或 `git push --tags`。

### 5. 收尾检查清单

- [ ] `pyproject.toml` 版本号与 `CHANGELOG.md` 新增小节版本号一致
- [ ] `CHANGELOG.md` 的 `[未发布]` 小节已清空并保留占位
- [ ] `git show -s --format=%B HEAD` 完整含 CHANGELOG 本版本分类标题与条目（不是只剩条目、标题被吃掉）
- [ ] `git cat-file -p refs/tags/vX.Y.Z` 的 message 只有 `release X.Y.Z` 一行，未混入分类条目
- [ ] tag 名称为 `vX.Y.Z`（前缀 `v`，与既有 tag 一致）
- [ ] 未执行任何 `push`，除非用户明确要求

---

## 参考：本仓库既有约定原文

详见 `CLAUDE.md`「发版（仅当用户明确要求发版 / release）」一节与 `CHANGELOG.md` 顶部"撰写约定"。本 skill 是对这两处规则的可执行展开，若两者冲突以 `CLAUDE.md` / `CHANGELOG.md` 原文为准（说明文档可能已被用户更新）。发现冲突时先向用户报告差异，不要擅自选边站或直接覆盖。
