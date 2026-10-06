# 任务 01：导入默认取最高级别 + 临时级别切换控件

## 目标

导入保持一步到位（取最高级别，不增加询问步骤）。导入成功后，若该敌人有多个级别，界面上出现一个**临时**的级别切换控件，让作者把当前卡换到其他级别；换卡或重启即消失。

## 现状与锚点

| 事实 | 位置 |
|---|---|
| 合并全部级别块（按 index 升序覆盖）→ 结果恒等于最高级别；**该行为保留为导入默认** | `utils/prts_field_mapping.py::build_enemy_raw`（`level_index=None`） |
| 技能槽与异常抗性同样跨级累加 | `utils/prts_field_mapping.py::_merge_skill_slots`、`ab_acc` |
| 已可取到全部级别块与每块的 `index` | `utils/wiki_template_parser.py::_extract_all_template_bodies`、`_parse_template_params` |
| 导入线程已拿到整页 wikitext（可留在内存供切换复用，无需二次联网） | `utils/thread_manager.py::PrtsFetchThread._pull`、`utils/prts_mediawiki_pipeline.py` |
| 构建时缺省字段回退卡片默认值 → **会重置简评 / 评分 / 头像** | `utils/prts_enemy_builder.py::to_enemy_data` |
| 撤销单元：一份命令持前后两份「数据 + 级别来源」状态 | `gui/undo_stack.py::_CardSnapshot` / `_StateCommand`、`gui/card_model.py::_commit` |
| 整份数据一步入栈、不清撤销栈（切换应走这条） | `gui/card_model.py::apply_enemy_data` |
| 装数据会清空撤销栈（**切换不得使用**） | `gui/card_model.py::set_enemy_data` |
| 既有提示通道与忙碌态 | `gui/qml_bridge.py::messageChanged`、`prtsBusy` |
| 换卡路径（打开 / 新建 / 重置）：临时上下文需随之清空 | `gui/qml_bridge.py`、`gui/main_window.py` |

## 结论

| 项 | 结论 |
|---|---|
| 导入默认 | **取最高级别**（现状不变），导入过程不新增任何询问步骤 |
| 上下文保留 | 导入成功后保留**本次导入上下文**：页面标题、整页 wikitext、级别列表；只保留一份（对应当前卡），不落盘。当前级别归卡片模型（见下两行） |
| 切换控件 | 仅当级数 ≥2 时显示；位置为**预览列工具行右侧**（`gui/qml/PreviewViewport.qml` 的工具栏 `RowLayout`，「导出」左侧）：`AppButton`（`menu: true`，`appearance: "secondary"`）+ `AppMenu`，按钮显示当前级别名，菜单项即各级别名（`级别0` / `级别1`），当前项带勾选；**不显示数值、不加提示文案** |
| 组件契约 | 预览组件只收属性、发信号：`prtsLevelsJson`（str）/ `prtsLevelIndex`（int）属性与 `prtsLevelChangeRequested(int)` 信号；由 `Workspace`（`:297`）绑定桥接属性与切换槽。**不把 controller 传入预览组件**；文件首行需 `pragma ComponentBehavior: Bound`（与其余含 `Repeater` 的 QML 一致） |
| 切换提交入口 | `gui/card_model.py::apply_enemy_data`（原 `apply_rating_standard` 改名，语义即「整份数据一步入栈」）；**禁用** `set_enemy_data`（会清空撤销栈） |
| 控件生命周期 | **临时**：换卡（打开 / 新建 / 重置数据）、控件被关闭、或重启应用即消失；不写入卡片、不写入偏好 |
| 切换 | 用内存中的 wikitext 重新构造（覆盖到所选 index），**零额外网络请求**；上下文已失效时不提供切换（重新导入即可） |
| 覆盖范围 | 只覆盖 PRTS 来源字段：18 个战斗字段 + 5 个枚举 + `brief_description` + `talents_abilities` + `skills`；**保留** `brief_comment`、`ratings`、`grade`、`avatar_path` |
| 覆盖提示 | 切换会覆盖导入后对上述 PRTS 字段的手工修改；控件需明示这一点，且切换可撤销 |
| 撤销与级别回放 | 「数据 + 级别来源」成对快照（`_CardSnapshot`），`_StateCommand` 持前后两份；`Ctrl+Z` / `Ctrl+Y` **同时回放数据与级别指示**。普通编辑沿用当前来源，撤销一次改名不会丢级别 |
| 级别来源归属 | 唯一值在 `gui/card_model.py::CardModel.prts_level_index`（`NO_PRTS_LEVEL = -1` 表示无来源）；`MainWindow` 的会话上下文只留 `name` / `wikitext` / `levels`，桥接的 `prtsLevelIndex` 直接读模型，**不留第二份影子** |
| 撤销入口 | 走 `apply_enemy_data`：整份数据一步入栈，省略 `level_index` 即沿用当前来源（评价标准那类改动不丢级别）；**禁止** `set_enemy_data` |
| 级数泛化 | 按 N 级实现（不写死 2 级）；只有 1 级时不显示控件 |
| 级别标签 | 优先取页面标题 `==级别N==`；标题与块对不上或缺失时自造 `级别N`，以 levelcontent 块为准 |
| index 异常 | 缺失或非数字时除既有 warning 外把事实返回上层，控件不得在异常数据上静默排序 |
| 数据源 | 生产只用 wikitext；SMW 子对象查询只作开发期校验 |
| 不做 | 改 `EnemyData` schema、加「级别」字段、导入时选择、多级批量导入、多页面选择（消歧已由 `resolve_enemy_page_title` 覆盖）、重写抓取链路、预取或后台刷新 |

## 步骤（已实施）

- [x] 解析层拆分：`utils/prts_field_mapping.py` 新增 `EnemyLevel` / `parse_enemy_levels` / `build_enemy_raw(wikitext, level_index=None)`（`None` 即覆盖到最高级别，保留为导入默认）；原 `merge_wikitext_enemy` 直接替换，无兼容层
- [x] 管线：`utils/prts_mediawiki_pipeline.py` 门面改导出新 API；`fetch_enemy_from_prts_mediawiki_with_debug` 的文档字符串改为「页面上下文入口」（wikitext 是级别切换的唯一数据源）
- [x] 导入流程：`PrtsFetchThread.fetchFinished` 改为 `(EnemyData, error, context)` 三参；`_page_context` 组装 `{name, wikitext, levels[], level_index}`
- [x] 桥接：`prtsLevelsJson` / `prtsLevelIndex` 只读属性、`set_prts_levels()`、`requestPrtsLevelChange(int)` 槽与 `prtsLevelChangeRequested` 信号
- [x] 切换提交：`gui/main_window.py::_change_prts_level` 内存重构造 → `rebuild_enemy_data`（白名单保留 `brief_comment` / `ratings` / `grade` / `avatar_path`）→ `CardModel.apply_enemy_data` 一步入栈
- [x] GUI：`gui/qml/PreviewViewport.qml` 工具栏加级别控件（`AppButton` + `AppMenu` + `Repeater` 菜单项），首行补 `pragma ComponentBehavior: Bound`；`Workspace`（`:297`）绑定属性与切换槽
- [x] 控件文案：按钮显示当前级别名，菜单项为各级别名，当前项勾选；**不显示数值、不加提示文案**；未加整宽提示条、未复用更新提示条槽位
- [x] 换卡清理：`_new_card` 与 `_open_file` 成功后调 `_clear_prts_context()`（清空单槽并隐藏控件）
- [x] 测试对齐：`test_prts_mediawiki_pipeline.py` 改用 `build_enemy_raw`；`test_prts_pipeline_refactor.py` 的线程用例改打桩 `_with_debug` 并断言三参上下文；`test_card_model_error_handling.py` 改用 `apply_enemy_data`
- [x] 撤销集成：级别来源进 `CardModel` 状态，`_CardSnapshot(enemy, prts_level_index)` 随 `_StateCommand` 成对快照；`restore_state` 同时恢复数据与级别，经 `prtsLevelChanged` → 桥接 → QML 回放指示；`load_from_file` / `set_enemy_data` 置 `NO_PRTS_LEVEL`
- [ ] 开发期校验（待本机）：用 SMW `[[<页面>#LEVEL<k>]]` 核对各级关键数值
- [ ] 回归（待本机）：导入行为与改动前一致（仍取最高级、无新增交互、无额外请求）

## 非目标

- 不做导入时的级别询问（仅提供事后临时切换）。
- 不做级别落盘 / 卡片留痕 / 「当前级别」的持久显示。
- 不做多级批量导入、不做跨敌人级别对比、不做重新联网取级别。

## 风险与回滚

- 风险：覆盖白名单写错会抹掉作者的简评与评分 → 白名单显式列出，验收第 5 条覆盖。
- 风险：误用 `set_enemy_data` 导致切换不可撤销 → 明确禁用，验收第 3 条覆盖。
- 风险：临时上下文与当前卡不一致（换卡后残留） → 单槽 + 换卡清空，验收第 7 条覆盖。
- 风险：写内存大对象（整页 wikitext） → 单槽、换卡即释放，不累积。
- 风险：预览工具行变拥挤（该行已有标题、导出、缩放控件与适配窗口） → 控件插在「导出」左侧并保持单行；标题已带 `elide` 与最小宽 96（`gui/qml/PreviewViewport.qml:41-52`）
- 回滚：撤掉切换控件与解析层拆分，回到「只能取最高级」的现状。

## 验收

1. 导入行为与改动前一致：仍取最高级别，导入过程无新增询问步骤。
2. 导入杰斯顿·威廉姆斯 → 卡片为级别1 数值（`max_hp=40000`、`attack=800`），预览列工具行「导出」左侧出现显示「级别1」的控件。
3. 切换到级别0 → `max_hp=25000`、`attack=700`，控件显示「级别0」；`Ctrl+Z` 一步回到 40000 / 800，**且控件同步回到「级别1」**；`Ctrl+Y` 再次让数据与控件一起回到级别0。
4. 切换级别后改一个数值 → `Ctrl+Z`（只撤销该数值）→ 仍是级别0；再 `Ctrl+Z` → 数据与控件一起回到级别1。
5. 切换后 `brief_comment` / `ratings` / `grade` / `avatar_path` 保持不变。
6. 对只有 1 个级别的敌人导入 → 不出现切换控件。
7. 换卡（打开另一份配置、新建、重置数据）→ 控件消失；此后再无切换入口（重新导入即可）。
8. 切换过程中 PRTS 侧**零请求**（日志可见），导入本身仍是原有的 resolve → parse → imageinfo 一次链路。
9. 用 SMW 子对象查询核对切换后的关键数值，两者一致。
