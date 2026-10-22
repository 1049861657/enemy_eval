# Proposal

## Why

当前测试、QML 校验、打包与 GitHub Release 全部依赖本地人工执行：质量门没有强制力，tag 与产物没有云端可追溯记录，发版容易漏跑测试、漏传资产或写错说明。项目只发布 Windows 桌面版，最合适的验证与构建环境就是 Windows。

## What Changes

- 新增 Windows CI 门禁：在拉取请求和 `master` 推送时使用锁定依赖运行 pytest 与 QML 校验，任一失败即阻止合并；`master` 分支保护把该检查设为必需。
- 新增 Release 流水线：在 `v*` tag 推送或针对已有 tag 的手动运行时，校验 tag、`pyproject.toml` 与 `CHANGELOG.md` 版本一致，重跑测试，调用现有构建脚本，生成 SHA256，并把 zip 与校验文件上传到 GitHub Release。
- Release 先使用草稿：测试、构建与两个资产上传全部成功后才公开；同一 tag 重跑时更新已有 Release，失败不留公开的半成品。
- 新增从 `CHANGELOG.md` 提取对应版本节的确定性能力，作为 Release notes；版本节缺失时发布失败，而不是发布空说明。
- 明确边界：拉取请求不执行打包；Pyright、OpenSpec 校验暂不作为必过门禁；代码签名、安装包、自动升级不在本次范围。
- 不修改应用运行时代码与数据格式。

## Capabilities

### New Capabilities

- `ci-release`: Windows 持续集成门禁、可复现的发布构建与 GitHub Release 自动上传行为。

### Modified Capabilities

无。

## Impact

- 预期新增 `.github/workflows/ci.yml`、`.github/workflows/release.yml` 与 CHANGELOG 版本节提取脚本；本次仅规划，不落地。
- 复用现有 `uv.lock`、`dev` 依赖组、`scripts/build_release.py` 与 `CHANGELOG.md` 格式。
- 需要仓库 Actions 写权限与 `GITHUB_TOKEN`；不需要新增应用密钥。
- 不改变用户本地运行、配置兼容性或渲染结果。
