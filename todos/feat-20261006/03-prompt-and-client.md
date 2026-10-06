# 任务 03：提示词、人设与调用层

## 目标

打通「两份敌人数据 → 一次请求 → 合法简评或明确错误」的最小闭环。

## 现状与锚点

| 事实 | 位置 |
|---|---|
| HTTP 约定（headers、四参数超时、重试传输） | `utils/prts_api_client.py` |
| 项目异常基类 | `utils/error_handler.py::EnemyEvalException` |
| 异常穿线程的既有范式（传异常对象，非字符串） | `utils/thread_manager.py::PrtsFetchThread.fetchFinished = Signal(object, object, object)` |
| `categorize_error_message` 现有调用点全传字符串（签名须兼容字符串） | `gui/main_window.py:195,244,263,291`、`tests/test_error_handler.py` |
| 当前卡权威数据（含 `skills`） | `gui/card_model.py::CardModel.enemy_data` |
| 技能项字段（中文键） | `models/skill_entry.py::SkillEntry`：`名称` / `冷却时间` / `技力消耗` / `效果` |
| `models` 层零项目内依赖（标准库 + Pydantic） | `AGENTS.md` 第 12 条 |
| 基准加载 | `utils/ai_baseline.py`（任务 02） |
| 配置读取 | `utils/app_settings_store.py`（任务 01）：入参直接用 `ai_request_config()` 的 `AiRequestConfig`，不在本层读偏好 |
| 独立联网脚本的写法（`sys.path` 注入 + `# noqa: E402`） | `scripts/smoke_mediawiki_api.py` |

## 结论

| 项 | 结论 |
|---|---|
| 新增文件 | `models/ai_evaluation.py`（结果模型）、`utils/ai_prompt.py`（人设与消息组装，纯函数）、`utils/ai_client.py`（调用与解析） |
| 人设依据 | 执行时采集，不预先冻结；**只采台词原文**（说话人 = 杰斯顿·威廉姆斯），按 称呼 / 句长 / 用词 / 态度 四栏归纳；**二手描述不作出处**。来源：① 官方敌人页 `https://prts.wiki/w/杰斯顿·威廉姆斯`——描述（「装扮成狱警混入监狱的杀手，杰斯顿·威廉姆斯。言谈举止都相当讲究，与人交战时也尽显风度。」）、能力条目（狱警形态 / 杀手形态）、天赋&能力全文、技能表（钢铁风暴 / 装甲穿刺），**文本已随任务 02 的基准取得，无需再抓**；② 孤岛风云剧情正文页，PRTS 命名约定为 `<关卡名>/NBT`（已实测可达，页面内含说话人与台词）：`MB-ST-1 邀请`、`MB-ST-2 正确的代价`、`MB-1 … MB-8`；③ 社区复述（萌娘百科角色页、百度百科词条）**仅用于补人物关系与情节顺序，不作语气依据** |
| 人设文案归属 | 助手起草一版，用户审改定稿；改语气即改文案，不动结构 |
| 结果模型 | `AiEvaluationResult.comment: str`：拒绝空串与纯空白；**不校验、不裁剪长度**（≤50 字是提示词约束，不做代码级截断） |
| 端点 | `POST {ai_base_url.rstrip("/")}/chat/completions`（去尾斜杠，避免拼出 `//`），认证头 `Authorization: Bearer <ai_api_key>` |
| 请求体 | 只带 `model` 与 `messages`：不带 `response_format` 等可选参数，避免兼容端点直接 400 |
| 客户端 | `evaluate(config: AiRequestConfig, baseline: dict, current: EnemyData) -> AiEvaluationResult`；每次调用 `with httpx.Client(...)` 新建，不跨线程复用、不注册全局关闭；**不挂重试传输**（网络类失败不重试，与结论一致） |
| 超时 | 固定 `httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0)`（四参数写全），模块常量，不进偏好 |
| 输出约定 | 期望 JSON `{"comment": "..."}`；解析容错：剥离 ```json 围栏与首尾空白后，正则取**首个括号平衡**的 JSON 对象（容忍「好的，简评如下：」前缀与尾随文字）；只取 `comment`，多余键忽略不报错 |
| 重试 | **仅解析失败重试一次**（同一请求重发一次），仍失败则抛错；网络与状态码失败不重试 |
| 错误载体 | `utils/error_handler.py` 新增 4 个子类（均继承 `EnemyEvalException`）：`AiCredentialError`（未配置 / 401）、`AiRateLimitError`（429）、`AiServiceError`（5xx / 解析重试后仍非法，两者以消息区分）、`AiNetworkError`（连接失败 / 读超时）；异常消息**不含密钥、请求头与请求体**；`categorize_error_message` 签名放宽为 `Exception | str` 并增类型分支——现有调用点与 `tests/test_error_handler.py` 全传字符串，行为不变 |
| 错误穿线程 | 线程信号传**异常对象**（`Signal(object, int)`），分类与文案在 GUI 层做（任务 05）；本层不拼展示文案 |
| 超长输出 | 不裁剪、不拒绝：原样返回给界面（长度上限是提示词约束，取舍在人工） |
| 当前卡取数源 | `CardModel.enemy_data`（权威数据，含 `skills`）；**不用**桥接的 `enemyDataJson` 投影（那是界面回显用，`exclude={"skills"}`） |
| payload 组装 | **白名单式**逐字段构造，不用 `model_dump()` 全量后删键——避免将来新增字段自动外泄。基准（任务 02）本身就是外发字段形状，直接嵌入；当前卡侧逐字段构造；`skills` 每项只取 `名称` / `冷却时间` / `技力消耗` / `效果` 四键，空列表写 `[]` |
| 数据传递 | 线程入参由调用方在起线程前 `model_copy(deep=True)` 深拷贝快照（任务 05）；本层不再复制，也不对内部明确类型做防御性断言 |
| 外发字段 | 13 个数值 + 5 个枚举 + `name` / `brief_description` / `talents_abilities` / `skills`；剔除 `avatar_path`、当前卡旧 `brief_comment`、`ratings`、`grade` |
| 日志 | 每次调用记 耗时 / 成败 / 模型名 / 是否重试；**不记密钥、不记请求与响应全文** |
| 未配置 | 判定点只在任务 05（桥接拦截并打开设置框，不发请求）；本层只保留参数契约：`config` 为 `None` 时抛 `AiCredentialError`（供冒烟脚本路径） |
| 基准缺失 | 不特判：`load_baseline()`（任务 02）缺失 / 非法 JSON / 缺键时抛 `FileOperationError`，由 GUI 既有错误路径展示；打包已保证 `resource/baseline/` 进包 |

### 提示词内容（`utils/ai_prompt.py`）

- 人设：杰斯顿口吻，温和毒舌，**只谈数据**，不拉踩设计者、其他敌人、作者。
- 角色标注：`user` 消息内两段带小标题的文本——`【你（杰斯顿）的基准数据】` 与 `【待评价对象的数据】`，各自后接该份 JSON；基准原样嵌入，不改造形状。
- 允许第一人称自称，可用自身数值作参照物。
- **不出现人称**指代评价对象：不写「它 / 他」，直接用「血量」「防御」这类主语。
- 宽度：可评机制与能力表现（技能、天赋文本），**不评设计好坏与新旧**。
- 长度与取舍：≤50 字，只写最突出的一两处差异。
- 格式：纯正文，不带「简评：」前缀、不带引号、不带署名；**禁 wiki 标记**（`[[...]]` / `{{...}}`）、**禁换行**。
- 字段语义说明（**不预计算任何差异值**）：13 个数值逐项给方向与量纲——`max_hp` / `attack` / `defense` 越高越强；`magic_resistance` 为**百分比**减伤；`damage_resistance` / `element_resistance` 为对应类型的减伤；`attack_interval` **越大越慢**；`move_speed` **越大越快**；`hp_recovery_speed` 越大回血越快；`attack_range_radius` 以格计；`weight_level` 越大越难被推动；`base_taunt_level` 为嘲讽等级；`target_value` 为计分权重。
- 零值语义：`weight_level=0` 无重量、`base_taunt_level=0` 无嘲讽、`target_value=0` 不计分、`attack_range_radius=0` 无额外范围、`hp_recovery_speed=0` 无自回、`damage_resistance=0` / `element_resistance=0` 无对应抗性。
- 事实边界：只依据两份给定数据，**不得引入数据中不存在的机制与数值**。
- 输出：仅一个 JSON 对象，键为 `comment`。

## 步骤

- [ ] `models/ai_evaluation.py`，并加进 `models/__init__.py` 的 `__all__`
- [ ] `utils/error_handler.py`：4 个 AI 异常子类 + `categorize_error_message` 增类型分支（签名 `Exception | str`）
- [ ] 人设采集与起草（执行时做，不必提前）：按上表来源抓剧情台词（`<关卡名>/NBT`）→ 按四栏归纳 → 出人设常量草案 + 逐条出处表（标 `<页面>#<段落>`）→ 交用户审改定稿
- [ ] `utils/ai_prompt.py`：人设常量 + `build_messages(baseline, current)` + 易搞反字段说明表
- [ ] `utils/ai_client.py`：白名单 payload、`evaluate(config, baseline, current)`、请求、解析、解析失败重试一次、状态码与网络异常转 4 个子类、调用日志
- [ ] `scripts/smoke_ai_review.py`：读基准 + 指定敌人配置 → 打印请求摘要与解析结果（不接入 pytest）
- [ ] 冒烟覆盖可造的三条失败路径：断网、错误密钥、非 JSON 响应；**429 / 5xx 无法离线制造，如实记为未实测**

## 非目标

- 不预计算差异表、不做档位判定、不做多候选、不做流式输出、不做结果缓存、不做会话历史、不做批量评价。

## 风险与回滚

- 风险：模型返回带说明文字的响应 → 解析容错（剥围栏 + 正则取首个括号平衡对象）+ 重试一次；仍失败则明确报错，不猜测内容。
- 风险：错误类型在跨线程时丢失 → 信号传异常对象（`Signal(object, int)`）+ `categorize_error_message` 接受 `Exception | str`。
- 风险：端点不接受某些字段 → 请求体保持最小公共子集。
- 风险：后台线程与主线程共享同一份卡数据 → 起线程前深拷贝快照。
- 风险：人设口径跑偏（把旁白或他人评价当成他的语气）→ 只取说话人为杰斯顿·威廉姆斯的台词行；社区复述只补情节顺序，不作语气依据。
- 回滚：删三个新增模块、冒烟脚本与 `error_handler` 的 4 个子类，恢复 `categorize_error_message` 原签名。

## 验收

1. 有效配置下冒烟脚本产出简评：不含「简评：」前缀、不带引号、无「它 / 他」指代、无 wiki 标记与换行；长度在提示词约束下通常 ≤50 字，**超出不裁剪、原样返回**。
2. 断网、错误密钥、非 JSON 响应分别抛出**可区分的异常子类**（`AiNetworkError` / `AiCredentialError` / `AiServiceError`），且 `categorize_error_message` 对异常对象与字符串都给出一致文案；429 / 5xx 仅代码走查，**未实测**。
3. 日志含耗时/成败/模型名，且看不到密钥与请求全文。
4. 外发 payload 中不存在 `avatar_path`、`ratings`、`grade` 与当前卡旧 `brief_comment`；`skills` 四键齐全（`名称` / `冷却时间` / `技力消耗` / `效果`）。
5. `config` 为 `None` 时抛 `AiCredentialError`。
