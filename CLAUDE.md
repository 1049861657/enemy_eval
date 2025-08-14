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

## 项目结构
```
enemy_eval/
├── main.py                 # 命令行程序入口
├── gui_main.py            # GUI程序入口
├── card_generator.py       # 核心卡片生成器
├── models.py              # Pydantic数据模型定义
├── font_manager.py        # 字体管理器
├── gui/                   # GUI模块
│   ├── __init__.py
│   ├── card_model.py      # 卡片数据模型(Qt)
│   ├── main_window.py     # 主窗口
│   ├── preview_widget.py  # 预览组件
│   ├── property_panel.py  # 属性编辑面板
│   └── styles.qss         # Qt样式表
├── data/                  # 配置文件目录
│   ├── *_config.json      # 敌人配置文件
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

### GUI 开发约定
- 使用 Qt 的 Model/View 架构
- 组件命名采用 PascalCase (如 PreviewWidget)
- 信号槽连接在 `__init__` 方法中完成
- 样式统一在 `styles.qss` 中管理
- 布局优先使用 QVBoxLayout/QHBoxLayout

### 配置文件管理
- 所有配置使用 JSON 格式存储在 `data/` 目录
- 配置结构由 `models.py` 中的 Pydantic 模型定义
- 文件命名格式: `{敌人名称}_config.json`

### 代码风格约定
- 方法使用 `_` 前缀
- 类型提示必须完整，特别是 GUI 相关代码

## 设计参考
- example/ 目录包含UI设计参考图
- 卡片生成遵循紧凑布局原则
- GUI界面支持实时预览和属性编辑

## 版本信息
当前版本实现了完整的GUI编辑器和命令行工具，支持:
- 实时卡片预览
- 属性面板编辑
- 技能动态添加/删除
- 配置文件导入/导出
- 多种敌人类型支持