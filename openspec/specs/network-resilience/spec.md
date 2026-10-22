# network-resilience Specification

## Purpose

让外发请求在失败时行为可预测：重试只由一层承担，异常响应走既有错误路径，而不是嵌套重试或抛出未处理异常。

## Requirements

### Requirement: 单层重试

PRTS 外发请求 SHALL 由同一层统一重试连接类错误与 502/503/504；同一请求 SHALL NOT 在传输层与请求层各自重试，重试总次数 SHALL 可预测为初始请求加两次重试。

#### Scenario: 连接失败

- **WHEN** 目标主机拒绝连接
- **THEN** 该请求共尝试 3 次（初始 1 次 + 重试 2 次），不出现嵌套放大

#### Scenario: 服务端 5xx

- **WHEN** PRTS 返回 502、503 或 504
- **THEN** 该请求共尝试 3 次

#### Scenario: 不重试的状态码

- **WHEN** PRTS 返回 404
- **THEN** 该请求只尝试 1 次

### Requirement: 非 JSON 响应

PRTS 响应正文不是合法 JSON 时，系统 SHALL 通过既有错误路径返回失败，SHALL NOT 让未处理异常终止拉取。

#### Scenario: 解析定位阶段返回非法 JSON

- **WHEN** 语义查询响应正文不是合法 JSON
- **THEN** 放弃精确定位，继续用用户输入的名称请求 parse

#### Scenario: 页面解析阶段返回非法 JSON

- **WHEN** parse 响应正文不是合法 JSON
- **THEN** 返回「响应不是合法 JSON」的错误提示，拉取流程正常结束

#### Scenario: 头像查询阶段返回非法 JSON

- **WHEN** imageinfo 响应正文不是合法 JSON
- **THEN** 本次拉取不附带网络头像，其余数据照常返回
