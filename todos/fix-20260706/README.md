# 架构审查修复计划

来源：2026-07-06 架构缺陷与技术债审查（全仓库只读审查，`models/`、`core/`、`utils/`、`gui/` 全覆盖，含 3 个并行子代理对 GUI / PRTS 数据管线 / 渲染核心的专项复核）。

## 使用方式

按批次（batch）文件分批执行，每个批次是一次独立可提交的修复单元，避免一次性大改动混杂多个关注点。批次内条目已按优先级排序。完成一批后勾选对应 checkbox 并提交，再进入下一批。

## 批次索引

| 批次 | 文件 | 主题 | 优先级 |
|---|---|---|---|
| 0 | [`00-test-infrastructure.md`](./00-test-infrastructure.md) | 引入测试基础设施 | 最高（其余批次的回归保护网） |
| 1 | [`01-thread-safety-render.md`](./01-thread-safety-render.md) | 渲染线程并发与全局单例加锁 | P0 |
| 2 | [`02-gui-signal-bugs.md`](./02-gui-signal-bugs.md) | GUI 信号连接真实 bug | P0 |
| 3 | [`03-prts-pipeline-refactor.md`](./03-prts-pipeline-refactor.md) | PRTS 数据管线拆分与异步化 | P0/P1 |
| 4 | [`04-error-handling-consistency.md`](./04-error-handling-consistency.md) | 错误处理一致性与死代码清理 | P1 |
| 5 | [`05-render-cache-dedup.md`](./05-render-cache-dedup.md) | 渲染层缓存复用与重复代码收敛 | P1 |
| 6 | [`06-gui-polish.md`](./06-gui-polish.md) | GUI 可维护性打磨（防抖复用/常量收敛/样式统一） | P2/P3 |

## 建议执行顺序

批次 0 → 1 → 2 → 3 → 4 → 5 → 6。批次 0 必须最先做：没有测试保护网时，批次 1（改并发/加锁）和批次 3（拆分大文件）都有引入新回归的风险却无法验证。批次 1 与批次 2 都是独立子系统（渲染线程 vs GUI 信号），若人力充足可并行执行。

