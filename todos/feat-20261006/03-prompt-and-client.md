# 任务 03：提示词、人设与调用层

## 目标

打通「两份敌人数据 → 一次请求 → 合法简评或明确错误」的最小闭环。

## 现状与锚点

| 事实 | 位置 |
|---|---|
| HTTP 约定（headers、四参数超时、重试传输） | `utils/prts_api_client.py` |
| 项目异常基类 | `utils/error_handler.py::EnemyEvalException` |
| `models` 层零项目内依赖（标准库 + Pydantic） | `AGENTS.md` 第 12 条 |
| 基准加载 | `utils/ai_baseline.py`（任务 02） |
| 配置读取 | `utils/app_settings_store.py`（任务 01） |
| 独立联网脚本的写法（`sys.path` 注入 + `# noqa: E402`） | `scripts/smoke_mediawiki_api.py` |

## 结论

| 项 | 结论 |
|---|---|
| 新增文件 | `models/ai_evaluation.py`（结果模型）、`utils/ai_prompt.py`（人设与消息组装，纯函数）、`utils/ai_client.py`（调用与解析） |
| 人设依据 | **必须先充分阅读官方文案与设定再起草**，并在草案里逐条列出出处。素材范围：① 已取得——PRTS 敌人页的敌人描述（「装扮成狱警混入监狱的杀手，杰斯顿·威廉姆斯。言谈举止都相当讲究，与人交战时也尽显风度。」）、能力条目（狱警形态 / 杀手形态）、天赋&能力全文、技能表（钢铁风暴 / 装甲穿刺）；② **待补**——《孤岛风云》剧情与他的台词（PRTS 剧情页 / 角色页），据此提取措辞习惯后再起草 |
| 人设文案归属 | 助手起草一版，用户审改定稿；改语气即改文案，不动结构 |
| 结果模型 | `AiEvaluationResult.comment: str`：拒绝空串与纯空白；**不校验、不裁剪长度**（≤50 字是提示词约束，不做代码级截断） |
| 端点 | `POST {ai_base_url}/chat/completions`，认证头 `Authorization: Bearer <ai_api_key>` |
| 请求体 | 只带 `model` 与 `messages`：不带 `response_format` 等可选参数，避免兼容端点直接 400 |
| 客户端 | 独立 `httpx.Client`；**不挂重试传输**（网络类失败不重试，与结论一致） |
| 超时 | 固定 `httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0)`（四参数写全），模块常量，不进偏好 |
| 输出约定 | 期望 JSON `{"comment": "..."}`；解析容错剥离 ```json 围栏与首尾空白 |
| 重试 | **仅解析失败重试一次**（同一请求重发一次），仍失败则抛错；网络与状态码失败不重试 |
| 状态码归一 | 四类可区分，供 `categorize_error_message` 直接映射：401 → 密钥无效或未配置；429 → 限流；5xx → 服务端异常（带状态码）；连接失败 / 读超时 → 网络不可达 |
| 超长输出 | 不裁剪、不拒绝：原样返回给界面（长度上限是提示词约束，取舍在人工） |
| payload 组装 | **白名单式**逐字段构造，不用 `model_dump()` 全量后删键——避免将来新增字段自动外泄 |
| 外发字段 | 13 个数值 + 5 个枚举 + `name` / `brief_description` / `talents_abilities` / `skills`；剔除 `avatar_path`、当前卡旧 `brief_comment`、`ratings`、`grade` |
| 日志 | 每次调用记 耗时 / 成败 / 模型名 / 是否重试；**不记密钥、不记请求与响应全文** |
| 未配置 | `ai_base_url` / `ai_model` / 密钥任一为空时抛 `EnemyEvalException`，由 GUI 转为「打开设置框」动作（任务 05） |

### 提示词内容（`utils/ai_prompt.py`）

- 人设：杰斯顿口吻，温和毒舌，**只谈数据**，不拉踩设计者、其他敌人、作者。
- 允许第一人称自称，可用自身数值作参照物。
- **不出现人称**指代评价对象：不写「它 / 他」，直接用「血量」「防御」这类主语。
- 宽度：可评机制与能力表现（技能、天赋文本），**不评设计好坏与新旧**。
- 长度与取舍：≤50 字，只写最突出的一两处差异。
- 格式：纯正文，不带「简评：」前缀、不带引号、不带署名。
- 字段语义说明（**不预计算任何差异值**）：`attack_interval` 越大越慢、`move_speed` 越大越快、`magic_resistance` 为百分比减伤、`attack_range_radius` 以格计。
- 输出：仅一个 JSON 对象，键为 `comment`。

## 步骤

- [ ] `models/ai_evaluation.py`
- [ ] `utils/ai_prompt.py`：人设常量 + `build_messages(baseline, current)` + 易搞反字段说明表
- [ ] `utils/ai_client.py`：白名单 payload、请求、解析、解析失败重试一次、错误归一、调用日志
- [ ] `scripts/smoke_ai_review.py`：读基准 + 指定敌人配置 → 打印请求摘要与解析结果（不接入 pytest）
- [ ] 冒烟覆盖三条失败路径：断网、错误密钥、非 JSON 响应

## 非目标

- 不预计算差异表、不做档位判定、不做多候选、不做流式输出、不做结果缓存、不做会话历史、不做批量评价。

## 风险与回滚

- 风险：模型返回带说明文字的响应 → 解析容错 + 重试一次；仍失败则明确报错，不猜测内容。
- 风险：端点不接受某些字段 → 请求体保持最小公共子集。
- 回滚：删三个新增模块与冒烟脚本。

## 验收

1. 有效配置下冒烟脚本产出简评，长度 ≤50 字，不含「简评：」前缀，无「它 / 他」指代。
2. 断网、错误密钥、非 JSON 响应分别给出可区分的错误信息（含 401 / 429 / 5xx / 网络不可达四类）。
3. 日志含耗时/成败/模型名，且看不到密钥与请求全文。
4. 外发 payload 中不存在 `avatar_path`、`ratings`、`grade` 与当前卡旧 `brief_comment`。
