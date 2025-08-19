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
├── models.py              # Pydantic数据模型定义
├── core/                  # 核心基础逻辑模块
│   ├── __init__.py        # 模块入口
│   ├── renderer.py        # 高性能卡片渲染器(原card_generator)
│   ├── fonts.py           # 字体管理器(原font_manager)
│   └── optimization.py    # 性能优化和资源管理
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
├── pyproject.toml        # 项目配置
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
- **core/**: 核心逻辑
- **utils/**: 通用工具类
- **gui/**: 界面相关
- **models.py**: 数据模型统一管理
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
- 配置结构由 `models.py` 中的 Pydantic 模型定义
- 文件命名格式: `{敌人名称}_config.json`

### 代码风格约定
- 私有方法使用 `_` 前缀
- 类型提示必须完整，特别是 GUI 相关代码
- 导入顺序：标准库 → 第三方库 → 项目模块

## 设计参考
- 卡片生成遵循紧凑布局原则
- GUI界面支持实时预览和属性编辑

## 版本信息
当前版本实现了模块化重构的GUI编辑器和命令行工具，支持:
- **核心功能**: 实时卡片预览、高性能渲染引擎
- **GUI编辑**: 模块化属性面板、技能动态编辑、样式管理
- **性能优化**: 资源复用池、智能缓存、性能提升75%
- **错误处理**: 分类异常处理、用户友好错误提示
- **配置管理**: JSON配置文件、类型安全验证
- **多线程**: 异步渲染、UI防抖、线程池管理

## 打包语句
pyinstaller --clean --windowed --add-data "resource;resource" --add-data "gui;gui" --name enemyEval gui_main.py