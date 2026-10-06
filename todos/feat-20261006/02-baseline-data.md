# 任务 02：基准数据与打包

## 目标

冻结杰斯顿·威廉姆斯的**级别0 数据**为一份手写 JSON（纯 AI 参考数据，不接编辑器、不走 `EnemyData` 校验），提供只读加载器，并确认打包产物能读到它。

## 现状与锚点

| 事实 | 位置 |
|---|---|
| 打包只收集 `resource/`，按目录递归复制 | `enemyEval.spec:188-189`（`project_data = [("resource", "resource")]`） |
| 打包期数据过滤只针对 Qt/QML 与 DLL 名单，不涉及 JSON | `enemyEval.spec:336-352` 的 `_should_drop` |
| 开发/打包双路径解析 | `utils/resource_manager.py::resource_manager.get_resource_path`（打包时走 `sys._MEIPASS`） |
| **级别0 数据来源**（数值 / 描述 / 技能 / 天赋） | `data/prts_debug/杰斯顿·威廉姆斯/page.wikitext` 的 `==级别0==` 块（本地已缓存） |
| 字段名与技能结构的参照（该文件是**级别1** 合并结果，只作参照） | `data/prts_debug/杰斯顿·威廉姆斯/extracted.json` |
| 项目错误类型 | `utils/error_handler.py::FileOperationError` |

## 结论

| 项 | 结论 |
|---|---|
| 路径 | `resource/baseline/jesselton_config.json` |
| 形状 | **手写 JSON，22 个键**：键名与卡面字段同名（`max_hp` / `attack` / …），只含发给模型的内容——13 数值 + 5 枚举 + `name` / `brief_description` / `talents_abilities` / `skills`。**不含** `grade` / `brief_comment` / `ratings` / `avatar_path`，因此没有占位值，也不接 `EnemyData` 校验、不要求编辑器可读或可出图 |
| 数值（级别0） | `max_hp=25000`、`attack=700`、`defense=400`、`magic_resistance=20`、`attack_range_radius=2.0`、`attack_interval=4.0`、`move_speed=0.6`、`hp_recovery_speed=0.0`、`weight_level=6`、`damage_resistance=0`、`element_resistance=0`、`base_taunt_level=0`、`target_value=2` |
| 枚举 | `position="领袖"`、`category="其他"`、`attack_type="近战 远程"`、`damage_type="物理"`、`action_type="地面"` |
| 文本 | `brief_description` 取级别0 描述；`talents_abilities` 取级别0 天赋原文（含「被击败后进行持续 4s 的重生，恢复 100% 生命值」与「攻击力+700、防御力+1000、攻击间隔-1.5、移动速度+0.3」）；`skills` 两条（钢铁风暴 / 装甲穿刺）。保留与卡面一致的 wiki 标记，比对口径相同 |
| 级别 | **只用级别0**：级别1（`max_hp=40000` / `attack=800`）与级别1 天赋文本不得混入。不进运行时流程，不走 PRTS 重建 |
| 加载器 | `utils/ai_baseline.py::load_baseline()`：`resource_manager.get_resource_path` 定位 → `json.loads` → 校验必填键齐全 → `lru_cache` 缓存 → 返回副本 |
| 失败 | 文件缺失、非法 JSON、缺字段 → 抛 `FileOperationError`（不静默降级：AI 功能依赖它） |
| 打包 | **无需改 `enemyEval.spec`**：现有 `("resource", "resource")` 递归带上子目录，过滤名单不含 JSON；由本任务的打包实测确认 |
| 读写 | 只读：加载器只读不写；基准不经编辑器保存 |

## 步骤

- [x] 从 `==级别0==` 块整理数值、描述、技能、天赋
- [x] 写 `resource/baseline/jesselton_config.json`
- [x] 新增 `utils/ai_baseline.py`（`load_baseline()`）
- [ ] 本机确认：JSON 合法、`load_baseline()` 返回 22 个键、缺键或删文件时抛 `FileOperationError`（待本机）
- [ ] `pyinstaller --noconfirm --clean enemyEval.spec` 后实测能读到基准

## 非目标

- 不做基准刷新入口；不留档来源与日期；不建分档标尺；不为多阶段加结构化字段；不把基准暴露为可编辑配置；**不接 `EnemyData`**、不要求编辑器可读或可出图。

## 风险与回滚

- 风险：手写数值与 PRTS 不一致 → 评价系统性偏差；逐项对照上文锚点值。
- 风险：级别混用（级别1 的 40000 / 800 或级别1 天赋文本） → 只从 `==级别0==` 块取数。
- 风险：基准文件未进包 → 打包实测覆盖；加载器报错先于评价失败暴露。
- 回滚：删基准文件与 `utils/ai_baseline.py`。

## 验收

1. `resource/baseline/jesselton_config.json` 是合法 JSON，键集合为上述 22 个，且 `max_hp=25000`、`attack=700`。
2. 开发环境中 `load_baseline()` 返回该 dict，重复调用命中缓存；改返回对象不影响后续调用结果。
3. 打包产物内该文件存在且能加载成功。
4. 删除基准文件、或删掉任一必填键后调用，抛 `FileOperationError` 且信息可读（文案由任务 05 分类展示）。
