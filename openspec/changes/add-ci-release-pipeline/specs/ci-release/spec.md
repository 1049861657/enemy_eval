# Spec Delta

## Purpose

让每次变更都在目标平台接受一致的质量门，并让版本 tag 自动产出可追溯、可校验的 GitHub Release，减少漏测、漏传与说明错配。

## ADDED Requirements

### Requirement: Windows 质量门

仓库 SHALL 在拉取请求和 `master` 分支推送时，于 Windows 运行器上使用锁定的依赖执行完整测试与 QML 校验；任一检查失败时该次运行 SHALL 失败；`master` 的合并 SHALL 要求该检查通过。

#### Scenario: 拉取请求通过

- **WHEN** 拉取请求中的测试与 QML 校验全部成功
- **THEN** 该次 CI 运行成功，可作为合并门禁

#### Scenario: master 合并门禁

- **WHEN** 针对 `master` 的拉取请求准备合并
- **THEN** 分支保护要求 CI 检查通过，未通过时不可合并

#### Scenario: 测试失败

- **WHEN** 任一 pytest 用例失败
- **THEN** CI 运行失败，并保留失败用例的输出

#### Scenario: QML 校验失败

- **WHEN** 任一 QML 文件未通过校验
- **THEN** CI 运行失败，并指出未通过的文件

#### Scenario: 依赖与锁文件不一致

- **WHEN** 依赖声明与锁文件不一致
- **THEN** CI 运行在安装依赖阶段失败，不继续执行测试

#### Scenario: 拉取请求不打包

- **WHEN** CI 由拉取请求触发
- **THEN** 不执行发布打包，也不创建 Release

### Requirement: 发布版本一致性

Release 流水线 SHALL 由 `v*` tag 推送或针对已有 tag 的手动运行触发；开始构建前 SHALL 校验 tag 版本、项目版本、锁文件中的项目版本与变更日志中的版本节完全一致，任一不一致时 SHALL 终止且不发布。

#### Scenario: 版本一致

- **WHEN** tag 为 `vX.Y.Z`，项目版本与锁文件项目版本均为 `X.Y.Z`，且变更日志存在 `## [X.Y.Z]` 节
- **THEN** 流水线继续执行测试与构建

#### Scenario: tag 与项目版本不一致

- **WHEN** tag 版本与项目版本不同
- **THEN** 流水线在构建前失败，不创建或更新 Release

#### Scenario: 锁文件版本未同步

- **WHEN** `pyproject.toml` 已升级但锁文件中的项目版本仍是旧值
- **THEN** 流水线在构建前失败，提示同步锁文件

#### Scenario: 变更日志缺少版本节

- **WHEN** 变更日志中不存在与版本对应的版本节
- **THEN** 流水线失败，不发布空说明

#### Scenario: 手动补发

- **WHEN** 维护者对已有 tag 手动触发发布
- **THEN** 流水线与 tag 推送执行相同的版本校验、测试、构建与上传流程

### Requirement: 发布资产与说明

发布流水线 SHALL 在发布前重新执行完整测试；测试通过后 SHALL 使用仓库既有构建脚本产出便携包，并生成对应的 SHA256 校验文件；GitHub Release SHALL 同时包含便携包与校验文件。发布 SHALL 先创建或复用草稿，只有两个资产都上传成功后才公开。

#### Scenario: 发布成功

- **WHEN** 版本校验、测试与构建全部成功
- **THEN** Release 包含一个 zip 便携包及其 SHA256 校验文件

#### Scenario: 重复发布

- **WHEN** 同一 tag 再次运行且已有 Release
- **THEN** 更新该 Release 的说明与资产，最终只保留一份便携包与一份校验文件

#### Scenario: 测试失败

- **WHEN** 发布前测试失败
- **THEN** 不执行构建，不创建或更新 Release

#### Scenario: 构建失败

- **WHEN** 构建脚本失败或产物校验失败
- **THEN** 不公开 Release，并保留失败日志

#### Scenario: Release 说明来源

- **WHEN** 发布流水线生成 Release 说明
- **THEN** 说明只包含与该版本对应的变更日志条目，不混入其他版本

### Requirement: 权限与失败隔离

CI 运行 SHALL 只拥有读取仓库内容的权限；只有 Release 运行 SHALL 拥有写入 Release 的权限。质量门失败、构建失败或资产上传失败时 SHALL NOT 公开缺少便携包或校验文件的 Release。

#### Scenario: 拉取请求来自分叉仓库

- **WHEN** 分叉仓库发起拉取请求
- **THEN** CI 不获得写入 Release 的权限，也不读取发布密钥

#### Scenario: 发布中途失败

- **WHEN** 测试、构建或上传任一阶段失败
- **THEN** 不公开缺少便携包或校验文件的 Release，草稿可保留供重试
