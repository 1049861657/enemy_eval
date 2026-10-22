# Tasks

## 1. CI 工作流

- [x] 1.1 新建 `.github/workflows/ci.yml`：监听 `pull_request` 与 `push` 到 `master`，`permissions` 只给 `contents: read`，按分支设置并发并在新推送时取消旧运行
- [x] 1.2 配置 `windows-latest`、Python 3.13 与 `astral-sh/setup-uv` 缓存，执行 `uv sync --locked`，设置 `QT_QPA_PLATFORM=offscreen`
- [x] 1.3 依次执行 `uv run pytest -q` 与 `pyside6-qmllint -I gui/qml` 全量 QML 校验；验证：任一命令失败时 job 失败
- [ ] 1.4 在仓库设置中把 CI 的 `test` 检查设为 `master` 必需状态；验证：未通过的 PR 无法合并
- [ ] 1.5 推送测试分支并发起 PR；验证：安装、pytest、QML 校验依次通过，日志可见

## 2. 发布辅助脚本

- [x] 2.1 修改 `scripts/build_release.py`：生成 zip 后写入同名 `.sha256`，内容为小写摘要与文件名；验证：本地构建后 `dist/` 同时存在 zip 与 `.sha256`
- [x] 2.2 新增 `scripts/extract_changelog.py`：按版本号提取对应 `## [X.Y.Z]` 节，去掉版本标题与末尾分隔线，支持 `--output`
- [x] 2.3 验证提取器：`0.6.0` 输出只含该版本分类与条目；不存在的版本以非零退出并报错
- [x] 2.4 不新增 pytest 用例；用一次性命令核对 CRLF、带日期标题与缺失版本三种输入

## 3. Release 工作流

- [x] 3.1 新建 `.github/workflows/release.yml`：监听 `v*` tag 与 `workflow_dispatch`，校验 ref 为 tag，`permissions` 给 `contents: write`，同一 tag 串行且不取消进行中的运行
- [x] 3.2 在安装依赖前校验 tag、`pyproject.toml`、`uv.lock` 项目版本与 `CHANGELOG.md` 版本节一致；验证：四者任一不匹配时 job 立即失败
- [x] 3.3 依次执行测试、`build_release.py`、Release notes 提取；验证：任一步失败时后续步骤不执行
- [x] 3.4 用 `gh release` 实现草稿中转：不存在则创建草稿，已存在则转草稿，`--clobber` 上传 zip 与 `.sha256`，两者成功后公开
- [x] 3.5 使用内置 `GITHUB_TOKEN` 与 `GH_TOKEN` 环境变量；验证：workflow 未引用额外 Secrets

## 4. 端到端验收

- [x] 4.1 本地执行 `uv sync --locked`、`uv run pytest -q`、全量 qmllint；验证：全部通过
- [ ] 4.2 在 PR 上验证 CI 门禁：成功时检查为绿，临时制造测试或 QML 失败时检查为红，恢复后重新变绿
- [ ] 4.3 在测试分支手动运行 Release 工作流：验证版本校验、构建、两个资产与说明均正确，日志显示创建草稿、上传完成后才公开
- [ ] 4.4 在下一个真实 `v*` tag 上验收自动发布；失败时确认只留下草稿、没有公开的半成品 Release
- [x] 4.5 确认发版提交同时包含 `pyproject.toml`、`uv.lock` 与 `CHANGELOG.md`，且 workflow 不创建 commit/tag
- [x] 4.6 确认未改动应用运行时代码、未引入 Linux runner、未启用 Pyright/OpenSpec 必过门禁
