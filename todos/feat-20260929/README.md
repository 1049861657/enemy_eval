# feat-20260929

本目录是 2026-09-29 立项的改进计划：**5 项任务，按要求顺序执行**。计划总览、目标定义与关键决策见 [`00-overview.md`](./00-overview.md)。

## 文件地图

| 文件 | 内容 |
|---|---|
| [`README.md`](./README.md) | 本文件：目录索引与使用约定 |
| [`00-overview.md`](./00-overview.md) | 总览：质量口径、任务概览、顺序与依赖、关键决策、调研方法、风险 |
| [`01-config-loading-and-avatar-path.md`](./01-config-loading-and-avatar-path.md) | 任务 1：配置加载容错与头像路径可移植 |
| [`02-recent-files.md`](./02-recent-files.md) | 任务 2：最近打开列表 |
| [`03-undo-redo.md`](./03-undo-redo.md) | 任务 3：撤销 / 重做 |
| [`04-update-check.md`](./04-update-check.md) | 任务 4：启动时版本检查提示 |
| [`05-portable-distribution.md`](./05-portable-distribution.md) | 任务 5：便携分发与打包体积收敛 |

每份任务书自包含：目标、现状与内部锚点、外部调研与出处、设计、步骤 checkbox、非目标、风险与回滚、验收。

## 使用约定

1. **一次一项**：按任务号顺序执行；完成一项后勾选该项 checkbox，并把状态回填下表。

## 状态

| 任务 | 文件 | 优先级 | 状态 |
|---|---|---|---|
| 1 | `01-config-loading-and-avatar-path.md` | P0 | 已实现，待验收 |
| 2 | `02-recent-files.md` | P1 | 未开始 |
| 3 | `03-undo-redo.md` | P1 | 未开始 |
| 4 | `04-update-check.md` | P2 | 未开始 |
| 5 | `05-portable-distribution.md` | P2 | 未开始 |

## 与其他计划目录的关系

- `todos/fix-20260706/`、`todos/fix-20260826/`：历史计划（稳定可靠与错误处理一致性），已归档，本目录不修改它们。
- 本目录只写计划，不改产品代码。
