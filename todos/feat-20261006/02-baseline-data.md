# 任务 02：基准数据与打包

## 目标

冻结杰斯顿基准（一份标准 `EnemyData` JSON），提供只读加载器，并确认打包产物能读到它。

## 现状与锚点

| 事实 | 位置 |
|---|---|
| 打包只收集 `resource/`，按目录递归复制 | `enemyEval.spec:188-189`（`project_data = [("resource", "resource")]`） |
| 开发/打包双路径解析 | `utils/resource_manager.py::resource_manager.get_resource_path`（打包时走 `sys._MEIPASS`） |
| 敌人配置 JSON 的形状样例 | `data/小杂毛_config.json` |
| PRTS 导入链路：grade / 简评 / 三星评价留空、不预下载头像 | `utils/prts_mediawiki_pipeline.py:214::fetch_enemy_data` |
| 「天赋」字段的映射与落库 | `utils/prts_field_mapping.py:45` → `utils/prts_enemy_builder.py:52` |
| 渲染侧消费 `talents_abilities` | `core/render/sections/skills_talents.py:45` |

## 结论

| 项 | 结论 |
|---|---|
| 路径 | `resource/baseline/jesselton_config.json`（独立子目录，不与 `resource/` 下既有图标混放） |
| 打包 | **无需改 `enemyEval.spec`**：现有 `("resource", "resource")` 递归带上子目录；由本任务的打包实测确认没有被收集过滤连带剔除 |
| 取数分工 | 由助手走既有 debug 链路（`scripts/smoke_mediawiki_api.py <敌人> --dump`，落 `data/prts_debug/`）拉取并**生成草稿文件**，**用户人工校正数值**；助手不代替用户定稿数值 |
| 级别选择 | **取级别0**：`max_hp=25000`、`attack=700`；其余字段（防御 400、法抗 20、攻击半径 2.0、重量 6、移速 0.6、攻击间隔 4.0、目标价值 2）与级别1 相同。**前置已实施**：`todos/fix-20261006/` 提供级别切换（导入默认取最高级别，切换用 `build_enemy_raw(wikitext, 0)`）。**注意**：导入默认取到的是级别1（40000 / 800），草稿须切到级别0 |
| 两形态单值字段 | 照通常数据字面值：`attack_type="近战 远程"`、`damage_type="物理"` |
| `name` | `杰斯顿·威廉姆斯` |
| 多阶段 | 写进 `talents_abilities`：用 PRTS 原文增量句式（「生命值首次降至 0 时进入杀手形态，攻击力 +700、防御力 +1000、攻击间隔 −1.5、移动速度 +0.3」），不做绝对值换算、不存第二套数值 |
| `grade` / `brief_comment` / `ratings` | 仅为通过 `EnemyData` 校验而填（三者都不外发、不参与比对）：`grade` 取一个合法值、`brief_comment` 空串、`ratings` 空列表 |
| 头像 | 留空或写 URL，不预下载 |
| 读写 | 只读：加载器只读不写；不在运行期改写基准文件 |
| 留档 | 不留来源 URL 与冻结日期（版本过时由人工判断） |

## 步骤

- [ ] 取得杰斯顿数据：走既有「参考 PRTS」链路导入，或从 PRTS 页面抄录后校对
- [ ] 人工校正 18 个战斗字段、`brief_description`、`talents_abilities`、`skills`
- [ ] 按级别0 校正 `max_hp` 与 `attack`（链路默认给的是级别1 的 40000 / 800）
- [ ] 写 `resource/baseline/jesselton_config.json`，确认 `EnemyData(**json)` 校验通过
- [ ] 新增 `utils/ai_baseline.py`：`resource_manager.get_resource_path(...)` 定位 → 校验 → 缓存 → 只读返回 `EnemyData`
- [ ] 基准缺失或非法时抛 `FileOperationError`（不静默降级：AI 功能依赖它，错误文案由任务 05 收口）
- [ ] `pyinstaller --noconfirm --clean enemyEval.spec` 后实测能读到基准

## 非目标

- 不做基准刷新入口；不留档来源与日期；不建分档标尺；不为多阶段加结构化字段；不把基准暴露为可编辑配置。

## 风险与回滚

- 风险：基准文件被打包过程中的数据过滤连带剔除 → 打包实测覆盖；加载器错误先于渲染失败暴露。
- 风险：人工抄录数值出错 → 基准本身错、评价系统性偏差；校正时逐字段与 PRTS 页面对照。
- 回滚：删基准文件与 `utils/ai_baseline.py`。

## 验收

1. `EnemyData(**json)` 校验通过，且用编辑器打开该文件能正常出图。
2. 开发环境中 `load_baseline()` 返回 `EnemyData`，重复调用命中缓存。
3. 打包产物内 `resource/baseline/jesselton_config.json` 存在，且应用能加载成功。
4. 删除基准文件后调用加载器，报错信息可读且不崩溃（文案由任务 05 分类展示）。
