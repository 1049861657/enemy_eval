---
name: git-commit-release
description: 用户明确要求"生成 commit"/"提交"/"发版"/"release"/"bump 版本"时使用。A=日常提交（同步更新 CHANGELOG「未发布」）；B=发版。不主动触发。
---

# Git Commit & 版本发布

不主动进入任一场景。禁止未经授权 `git push` / `git push --tags`。

- **A 日常提交**：写 Conventional Commit；把本次用户可感知改动追加进 `CHANGELOG.md` 的 `[未发布]`，与代码同一 commit。禁止 bump 版本、禁止新建 `## [X.Y.Z]`。
- **B 发版**：只剪切已攒下的 `[未发布]` → 版本节，改 `pyproject.toml` 版本，打 tag。禁止在发版时凭记忆补条目。

约定原文：`AGENTS.md` 发版节、`CHANGELOG.md` 撰写约定。冲突时先报差异，不擅自覆盖。

---

## 场景 A

### 1. 看变更

```
git status
git diff --staged
git diff
```

并读 `CHANGELOG.md` 的 `## [未发布]`（第 2 步在现有条目上追加/改写，不是整节重写）。

**范围**：工作区全部未提交改动（已 add + 未 add）进这一个 commit。跨模块不算拆分理由。仅当某文件明显与本次无关（误触、他人并行）时才问用户是否拆出。相关文件全部 `git add`，不要漏选。

### 2. 更新 `[未发布]`

对照第 1 步 diff，追加**终端用户可感知**的功能、界面、行为。B 只剪切这一节，漏写则发版 changelog 会缺条目。

- 分类按需：`新增` / `变更` / `修复` / `移除` / `安全`。没有内容的分类不要留空标题。
- 面向用户：禁止文件名、类名、函数名、模块路径。一条一个价值点，同类小改动可合并。禁止编造 diff 里没有的改动。
- **保留**仍正确的旧未发布条目，只追加本次新价值点；同一点已有则不重复；被本次证伪/过时的才改写。不要把整节换成「仅本次」的列表。
- `[未发布]` 若只剩占位注释，写第一条时再补对应 `### 分类`。
- 工作区若已有人为本次写好的条目：核对是否覆盖本次 diff，缺了再补，正确的不要删。
- **不写** `[未发布]`（文件保持原样）：用户无感的内部重构；仅 todos / skill / AGENTS；纯格式或类型注解；无行为变化的锁文件。

改完的 `CHANGELOG.md` 与代码打进同一个 commit。

### 3. Message

```
<type>(<scope>): <中文祈使句，约 30 字内，无句号>

- [<方面>] <做了什么，为什么>
```

- 无 emoji。禁止写 diff 里没有发生的事。
- `type`：`feat` / `fix` / `refactor` / `chore` / `docs` / `perf` / `style`。
- `scope` 取模块或功能域：`gui`、`core`、`models`、`utils`、`prts`、`packaging`、`版本`；跨模块用 `+`，如 `models+core+gui`。
- 正文用 `- [方面] …`；只在需要说明影响时写正文。纯小改动可以只有标题行。

### 4. 提交

把 message 交给用户确认，或按用户已表达的自动化程度直接提交。

- 正文没有或多于一行以外的单行正文：`git commit -m "标题" -m "正文（可省）"`
- 正文是多行项目符号：**必须**写入 `.git/COMMIT_MSG_DRAFT`（第 1 行标题，空一行，再正文），然后 `-F`。禁止用多个 `-m` 传多行（换行会被 shell 吃掉，条目会连成一行）。
- 正文若含以 `#` 开头的行（含 `### 新增` 这类标题），**必须** `--cleanup=verbatim`，否则 git 默认当注释静默剥离。

```
git commit -F .git/COMMIT_MSG_DRAFT --cleanup=verbatim
rm -f .git/COMMIT_MSG_DRAFT
```

---

## 场景 B

日常 commit 不触发本流程。只剪切 A 攒下的 `[未发布]`，不要从 git 历史重写用户可见变更。

发版前：若自上次版本 tag 到 HEAD 有用户可见 commit，但 `[未发布]` 为空或明显漏项，**先补齐或问用户，再发版**。禁止凭记忆编条目，禁止把内部实现术语塞进版本节。

### 1. 版本号

读 `pyproject.toml` 的 `[project].version`（唯一权威来源）。**只能改 Y 或 Z**；**禁止改 X**，除非用户在本次对话手写指定新的 X。

以 `[未发布]` 为主，对照上次 tag 以来的 `git log` / `git diff`，按顺序：

1. 用户可见完整功能、跨 ≥2 模块的结构性改动、破坏或显著改变既有行为 → `Y+1`，`Z=0`
2. 仅修 bug、纯性能、单模块内部重构、文档/依赖 → `Z+1`
3. 同时命中 1 和 2：功能达第 1 条则 `Y+1`，否则 `Z+1`
4. 拿不准：列出 `[未发布]` 问用户「这次算 Y+1 还是 Z+1」，不要自己猜

### 2. 剪切 CHANGELOG

把 `## [未发布]` 下条目**原样剪切**到 `## [X.Y.Z] - YYYY-MM-DD`（分类标题一起走；没有条目的分类不要出现）。只许合并明显重复、修正笔误；**禁止**新增 A 没写过的内容。

原位置留空壳：

```
## [未发布]

<!-- 下一版本发布前，把此处条目移到新版本下 -->
```

### 3. `pyproject.toml`

只改 `version = "X.Y.Z"`，不动其他字段。`uv.lock` 里项目版本若已同步，一并提交。

### 4. Commit 与 tag

- Commit **标题** `chore: release X.Y.Z`；**正文**照抄本版本 CHANGELOG 分类条目（只含实际有的分类，不留空标题）。
- Tag **message 不要照抄分类条目**，固定一行 `release X.Y.Z`。详细变更只进 commit 与 `CHANGELOG.md`。
- 正文含 `### 新增` 等 `#` 开头行，`git commit -F` **必须** `--cleanup=verbatim`，否则分类标题会被 git 当注释剥掉。

```
git add pyproject.toml CHANGELOG.md
git commit -F .git/COMMIT_MSG_DRAFT --cleanup=verbatim
git tag -a vX.Y.Z -m "release X.Y.Z"
rm -f .git/COMMIT_MSG_DRAFT
```

草稿（没有的分类整段删掉）：

```
chore: release X.Y.Z

### 新增

- <照抄本版本「新增」全部条目>

### 变更

- <照抄本版本「变更」全部条目>

### 修复

- <照抄本版本「修复」全部条目>
```

### 5. 检查

- `pyproject.toml` 版本号与 CHANGELOG 新小节一致
- `[未发布]` 已清空并留下面占位
- `git show -s --format=%B HEAD` 含分类标题与条目（不是只剩条目、标题被剥掉）
- `git cat-file -p refs/tags/vX.Y.Z` 的 message 只有 `release X.Y.Z`
- tag 名为 `vX.Y.Z`；未执行任何 push
