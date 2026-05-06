# 敌人评价卡片生成器项目

## 项目概述
基于 Python 3.12 的敌人评价卡片生成器，具备完整的 GUI 界面和命令行工具。
- **核心技术**: skia-python (图形渲染) + PySide6 (GUI界面)
- **依赖管理**: uv
- **数据模型**: Pydantic 驱动的类型安全配置系统

## 基本守则
1. 不准生成多余的测试用例用于检查
2. 减少冗余的错误检查  
3. 禁止在最后擅自运行python程序检查运行情况，用户自己会运行
4. 当用户要求修改代码时，不要保留兼容性与提供迁移方案
5. 禁止创建回退方案，解决要完美
6. GUI 开发遵循 Qt 设计模式，保持组件职责分离
7. 所有配置文件使用 JSON 格式，遵循 Pydantic 模型验证
8. 禁止在代码中插入import，统一在顶部进行

## 项目结构
```
enemy_eval/
├── main.py                 # 命令行程序入口
├── gui_main.py            # GUI程序入口
├── models/                # Pydantic 数据模型（EnemyData、技能等）
│   ├── __init__.py
│   ├── enemy_data.py
│   ├── skill_entry.py
│   └── card_style.py
├── core/                  # 核心基础逻辑模块
│   ├── __init__.py        # 导出 EnemyCardGenerator 等
│   ├── fonts.py           # 字体管理器
│   ├── optimization.py    # 性能优化和资源管理
│   └── render/            # 卡片渲染子系统（模块化拆分）
│       ├── __init__.py    # 导出 EnemyCardGenerator
│       ├── generator.py   # EnemyCardGenerator：画布池、渐变、分区编排
│       ├── layout.py      # 纵向占位测算（与绘制共用公式，无 Canvas）
│       ├── wiki_text.py   # Wikitext / Skia 段落绘制
│       ├── stars.py       # 评级星级绘制
│       └── sections/      # 分区绘制
│           ├── avatar.py
│           ├── info.py           # 描述、属性表、异常抗性
│           ├── skills_talents.py # 技能与天赋表
│           └── rating_grade.py   # 左侧评级卡、底部等级与简评
├── utils/                 # 工具类模块
│   ├── __init__.py
│   ├── debouncer.py       # 自适应防抖器
│   ├── error_handler.py   # 错误处理和分类
│   └── thread_manager.py  # 线程管理器
├── gui/                   # GUI模块
│   ├── __init__.py
│   ├── card_model.py      # 卡片数据模型(Qt)
│   ├── main_window.py     # 主窗口
│   ├── preview_widget.py  # 预览组件
│   ├── property_panel.py  # 属性编辑面板
│   ├── styles.qss         # Qt样式表
│   ├── panels/            # 模块化编辑面板
│   │   ├── __init__.py
│   │   ├── basic_info_panel.py    # 基础信息面板
│   │   ├── combat_stats_panel.py  # 战斗属性面板
│   │   ├── rating_panel.py        # 评级面板
│   │   ├── resistance_panel.py    # 抗性面板
│   │   └── skill_editor_panel.py  # 技能编辑面板
│   └── styles/            # 样式管理模块
│       ├── __init__.py
│       └── property_panel_styles.py  # 属性面板样式
├── data/                  # 配置文件目录
│   └── *_config.json      # 敌人配置文件
├── enemy/                 # 敌人资源文件
│   └── */                 # 按敌人分类的资源
├── resource/              # 应用资源文件
│   └── ico/               # 图标资源
├── example/               # 设计参考
├── output_*.png          # 生成的卡片文件
├── CHANGELOG.md          # 版本变更记录（发版时与 pyproject 版本同步更新）
├── pyproject.toml        # 项目配置（[project].version 为单一版本号来源）
└── uv.lock               # 依赖锁定文件
```

## 技术栈详细信息
- **图形渲染**: skia-python - 高性能2D图形库
- **GUI框架**: PySide6 - Qt6的Python绑定
- **数据验证**: Pydantic - 类型安全的数据模型
- **图像处理**: Pillow - 辅助图像操作
- **数值计算**: NumPy - 数组计算支持
- **终端输出**: Rich - 美化命令行输出

## 开发指导

### 模块架构约定
- **core/**: 核心逻辑；对外仍通过 `from core import EnemyCardGenerator` 使用渲染器
- **core/render/**: 布局测算、Wiki 文本、分区绘制与 `generator` 编排，便于扩展与维护
- **utils/**: 通用工具类（注意：`thread_manager` 在运行时再导入 `EnemyCardGenerator`，避免与 `core` 循环依赖）
- **gui/**: 界面相关
- **models/**: 数据模型统一管理（Pydantic）
- 模块间通过明确的接口导入，避免循环依赖

### GUI 开发约定
- 使用 Qt 的 Model/View 架构
- 组件命名采用 PascalCase (如 PreviewWidget)
- 信号槽连接在 `__init__` 方法中完成
- 样式管理：`styles.qss` 主样式 + `gui/styles/` 模块化样式
- 布局优先使用 QVBoxLayout/QHBoxLayout
- 面板组件独立开发，通过 `gui/panels/` 模块管理

### 性能优化约定
- 使用 `core/optimization.py` 的资源管理器
- 图像处理通过 `ImageProcessor` 统一管理
- 长时间操作使用 `utils/thread_manager.py` 的线程池
- UI 更新使用 `utils/debouncer.py` 防抖

### 错误处理约定
- 统一使用 `utils/error_handler.py` 的异常类型
- 错误分类：`RenderError`, `ValidationError`, `EnemyEvalException`
- 错误消息通过 `categorize_error_message` 分类显示

### 配置文件管理
- 所有配置使用 JSON 格式存储在 `data/` 目录
- 配置结构由 `models/` 包中的 Pydantic 模型定义
- 文件命名格式: `{敌人名称}_config.json`

### 代码风格约定
- 私有方法使用 `_` 前缀
- 类型提示必须完整，特别是 GUI 相关代码
- 导入顺序：标准库 → 第三方库 → 项目模块

### 版本发布与 AI 协作（触发：用户要求「发版 / 发布版本 / 打 release」等）

当用户明确要**发布版本**时，协助者须按下面执行，**先总结与判级，再改文件**。

1. **归纳变更**  
   根据 `CHANGELOG.md` 中「未发布」段落、自上一版以来的代码/提交差异（或用户指定范围），用若干条**简短、面向人的要点**总结**本版关键功能与行为变化**（可写进该版 CHANGELOG 导语或「变更」下的小节）。

2. **主观判级 + 建议版本号**  
   在 **SemVer `X.Y.Z`** 下判断本版属于**变化大**还是**变化小**，并给出**仅含 Y 或 Z 进位**的**建议下一版本号**（见下表）。  
   - **变化大**的参考：新能力/新模块、对用户可见的显著行为变化、数据或配置形态影响、渲染或 GUI 的实质性调整、较大范围重构。  
   - **变化小**的参考：缺陷修复、小优化、文案/样式微调、不改变对外契约的内部整理。

3. **落盘**（在用户确认或任务要求编辑仓库时）  
   - 将「未发布」合并到**新版本**节，写清日期与分类（新增/变更/修复等）。  
   - 将 `pyproject.toml` 的 `[project].version` 改为与建议一致（该值为运行时 `utils.app_version` 的单一来源）。

4. **Git 提交与 tag（作者在本机或 CI 执行；AI 可提供命令草稿）**  
   - **提交**：把 `CHANGELOG.md`、`pyproject.toml` 等与发版相关的改动纳入一次提交（示例信息：`chore: release X.Y.Z`）。  
   - **tag**：Git 的 **tag** 是给**某一提交**打的永久别名，常见 **`vX.Y.Z`**，与 `pyproject` 版本对齐，便于日后检出该版本、以及在 GitHub/GitLab 上挂 **Release**。  
     - 附注标签（推荐，带说明）：`git tag -a vX.Y.Z -m "release X.Y.Z"`  
     - 推送标签到远程：`git push origin vX.Y.Z`，或与分支一起：`git push --follow-tags`  
   - **是否打 tag、何时 push** 由作者决定（远程策略、权限）；发版**不强制**必须有 tag，但**推荐**有 tag，否则仓库里不易对齐「哪次提交对应哪一版」。  
   - AI **不得**在未获授权时代为执行 `git push`/写远程；只可在文档或回复中写出上述命令供复制。

#### 版本号三位的修改权限与进位规则（AI 必须遵守）

版本字符串为 **`X.Y.Z`** 三位数字段（与 `pyproject.toml` 一致）。

| 位置 | 通常含义 | 谁可改 | AI 的约定 |
|------|----------|--------|-----------|
| **第 1 位 `X`** | 主版本 / 产品代际，由作者战略约定 | **仅作者** | **禁止**修改、禁止擅自建议改 `X`；除非用户**亲手**指定新 `X` 并明确写入。 |
| **第 2 位 `Y`** | 次版本，**较大**变更 | 作者定稿；AI 可**建议** | 判为**变化大**时：在**保持 `X` 不变**的前提下，**`Y ← Y+1`，`Z ← 0`**。 |
| **第 3 位 `Z`** | 修订，**较小**变更 | 作者定稿；AI 可**建议** | 判为**变化小**时：在**保持 `X`、`Y` 不变**的前提下，**`Z ← Z+1`**。 |

**结论**：AI 只通过**升第 2 位或第 3 位**来体现本次发版体量；**最前一位 `X` 只能由作者约定，AI 不得动。**

## 设计参考
- 卡片生成遵循紧凑布局原则
- GUI界面支持实时预览和属性编辑

## 版本信息
当前版本实现了模块化重构的 GUI 编辑器和命令行工具，支持:
- **核心功能**: 实时卡片预览、`core/render` 分包的高性能渲染管线
- **GUI编辑**: 模块化属性面板、技能动态编辑、样式管理
- **性能优化**: 资源复用池、智能缓存、性能提升75%
- **错误处理**: 分类异常处理、用户友好错误提示
- **配置管理**: JSON配置文件、类型安全验证
- **多线程**: 异步渲染、UI防抖、线程池管理

## 打包语句
pyinstaller --clean --windowed --add-data "resource;resource" --add-data "gui;gui" --name enemyEval gui_main.py