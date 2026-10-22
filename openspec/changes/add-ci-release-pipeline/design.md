# Design

## Context

参见 `proposal.md - Why`。现状约束：

- 产品只发布 Windows 便携包，构建依赖 PyInstaller 与 `uv` 的 `build` 依赖组；测试全部离线，`tests/conftest.py` 已使用 `offscreen`。
- 仓库已有 `scripts/build_release.py`，负责构建、产物校验、zip 与 SHA256 计算；版本唯一来源是 `pyproject.toml`，发布说明累积在 `CHANGELOG.md` 的版本节。
- 仓库当前没有 `.github/`；质量门与 Release 上传均为人工步骤。
- 分支与 tag 为 `master` 与 `vX.Y.Z`；现有发布流程只创建本地 annotated tag，不自动 push。

## Goals / Non-Goals

**Goals:**

- 在 Windows 上把 pytest 与全量 QML 校验变成 PR 与 `master` 的强制门禁。
- 让 `v*` tag 或针对 tag 的手动运行自动产出与版本严格对应的 GitHub Release。
- 发布失败时最多留下草稿，不公开缺少资产的 Release；同一 tag 可安全重跑。
- 复用现有构建脚本与 CHANGELOG，不引入第二套版本或说明来源。

**Non-Goals:**

- 不引入 Linux/macOS 矩阵、代码签名、安装包或自动升级。
- 不把 Pyright、OpenSpec 校验设为必过门禁。
- 不自动创建或推送 tag；tag 仍由本地发版流程产生。
- 不追求 zip 字节级可复现；`SOURCE_DATE_EPOCH` 只用于稳定构建时间元数据。

## Decisions

### 1. 两条 Windows 工作流

| 工作流 | 触发 | Runner | 权限 |
|---|---|---|---|
| `ci.yml` | `pull_request`、`push` 到 `master` | `windows-latest` | `contents: read` |
| `release.yml` | `push` tag `v*`、`workflow_dispatch` 且 ref 为 tag | `windows-latest` | `contents: write` |

统一使用 `astral-sh/setup-uv`、Python 3.13、`uv sync --locked`。CI 设置 `QT_QPA_PLATFORM=offscreen`，执行 `uv run pytest -q` 与对 `gui/qml` 下全部 QML 文件的 `pyside6-qmllint -I gui/qml`。

选择 `--locked` 而不是 `--frozen`：前者会校验锁文件与声明一致，版本 bump 后漏跑 `uv lock` 会在安装阶段直接失败；后者只按旧锁文件安装，可能放过过期的项目版本。

选择全 Windows 而不是 Linux：交付物与字体、Qt 平台行为都在 Windows；现有测试离线且无头，Windows runner 完全可跑。代价是计费系数更高，但公开仓库额度足够。

### 2. 手动补发只接受 tag

`workflow_dispatch` 不接收版本输入；运行前校验 `github.ref_type == 'tag'`，否则立即失败并提示在 Actions 页面选择已有 tag。这样版本、提交与资产天然对应，避免“分支 + 手填版本”产生错配。

### 3. 版本一致性作为第一道门

在任何安装、测试、构建之前完成：

- tag 必须是 `vX.Y.Z`；
- `pyproject.toml` 的 `project.version` 必须等于 `X.Y.Z`；
- `uv.lock` 中 `enemy-eval` 的项目版本必须等于 `X.Y.Z`；
- `CHANGELOG.md` 必须存在 `## [X.Y.Z]` 节（允许带日期后缀）。

任一失败即退出。版本校验放在 workflow 的内联 Python 中，避免为一次性检查新增脚本。

### 4. SHA256 由构建脚本产出

扩展 `scripts/build_release.py`：在生成 zip 并计算摘要后，同时写入 `dist/<zip 名>.sha256`，内容为 `<小写摘要>  <文件名>`。本地与 CI 使用同一实现，workflow 不再用 PowerShell 重算。

Release 资产固定为两个：`enemyEval-vX.Y.Z-win64.zip` 与同名 `.sha256`。

### 5. Release notes 由独立脚本提取

新增 `scripts/extract_changelog.py`：

- 参数为版本号（不带 `v`）与 `--output`；
- 匹配精确的 `## [X.Y.Z]` 标题，截取到下一个 `## [` 标题；
- 去掉版本标题与结尾的分隔线，保留分类标题和条目；
- 找不到版本节时向 stderr 报错并以非零退出。

workflow 在构建成功后生成 `release-notes.md`，`gh release` 用它作为正文。选择脚本而不是 workflow 内联正则，便于本地核对与后续格式演进。

### 6. 草稿中转后再公开

发布顺序：

1. 版本校验、测试、构建、SHA256、说明提取全部在本地工作区完成；
2. 用 `gh release view` 判断是否已有 Release；
3. 不存在则 `gh release create --draft --verify-tag`；已存在则先 `gh release edit --draft` 隐藏；
4. `gh release upload --clobber` 上传 zip 与 `.sha256`；
5. 全部成功后 `gh release edit --draft=false` 公开。

任何一步失败都停在草稿，不公开缺资产的 Release。同一 tag 重跑复用同一 Release，覆盖同名资产与说明。

### 7. 权限、并发与门禁

- CI 与 Release 的权限分别声明，遵循最小权限；Release 使用内置 `GITHUB_TOKEN`，不新增密钥。
- CI 并发按分支取消旧运行；Release 按 tag 串行，不取消进行中的发布。
- `master` 分支保护把 CI 的 `test` 检查设为 required；该设置是仓库配置，由维护者手动完成，workflow 不尝试修改仓库设置。

### 8. 与现有提交/发版流程的边界

- workflow 不创建 commit、不创建或推送 tag、不修改 `CHANGELOG.md`、`pyproject.toml` 或 `uv.lock`；版本提交与 annotated tag 仍由现有 `git-commit-release` 场景 B 产生。
- 本地创建 tag 不触发任何发布；只有显式 `git push origin vX.Y.Z` 才触发，因此“未经授权不 push”的约束保持不变。一旦授权推送，Release 会自动公开。
- 发版提交必须同时包含 `pyproject.toml`、`CHANGELOG.md` 与更新后的 `uv.lock`；版本校验会拒绝锁文件未同步的 tag。
- 分支保护只要求状态检查，不要求所有提交必须走 PR，因此现有直接提交 `master` 的方式不被阻断；若以后开启“Require a pull request”，发版提交也需改走 PR。

## Risks / Trade-offs

- **Windows Server 与桌面字体差异** → 现有测试只断言布局关系，不比对像素；未来加像素回归时需重新评估 runner。
- **草稿中转短暂隐藏已发布 Release** → 重跑同一 tag 时先转草稿；失败会保持草稿，需人工重跑或发布。
- **CHANGELOG 格式变化** → 提取脚本精确匹配标题并失败退出，问题在发布前暴露。
- **Actions 版本漂移** → 先固定主版本标签；供应链要求提高后再固定到 commit SHA。
- **构建耗时与费用** → 发布只在 tag/手动触发，PR 不打包；CI 只跑测试与 QML 校验。
- **tag push 即公开** → 授权推送后无法停在“只建 tag”；误推只能删除 Release 与 tag 挽回。现有“未授权不 push”规则必须在发版前保持。
- **版本提交漏改锁文件** → `--locked` 与版本校验都会失败；发版流程必须在 bump 后执行 `uv lock` 并提交 `uv.lock`。
- **分支保护不在代码内** → 需在首次 CI 成功后手动启用；私有免费仓库实测无法启用（API 403），需 GitHub Pro 或公开仓库；在此之前 `test` 只是可见检查，不能强制阻止合并。
