# 敌人评价卡片生成器（AI 上下文）

面向在本仓库改代码的助手：下文为**必须遵守的约束**与**定位代码时的索引**，避免营销式表述。

## 技术栈

- Python 3.13；包管理 **uv**（勿手改 `uv.lock`，依赖或版本变更后在本机执行 `uv lock` / `uv sync`）。
- 渲染 **skia-python**；GUI **PySide6**；配置与数据 **Pydantic**（`models/`）；辅助 Pillow、NumPy；CLI 输出 Rich。

## 助手必须遵守

1. **不要**为「检查」而新增多余测试用例。
2. **不要**重复校验 Pydantic 已验证的字段；不要对明确类型的内部调用堆防御性断言。
3. **不要**在任务末尾擅自运行 Python 验证；由用户本地运行。
4. 修改时**直接替换**，不保留兼容层、不提供迁移说明。
5. **不要**做回退式凑合实现。
6. GUI：Qt 职责分离；Python 侧信号槽在 `__init__` 中连接；界面 `gui/qml/`，主题 `Theme.qml`。
7. 配置一律 **JSON**，路径与形状符合 Pydantic；文件放 `data/`，命名 `{敌人名称}_config.json`。
8. **禁止**在函数体中间插入 `import`，一律文件顶部。

## 架构要点（防循环依赖）

- **对外渲染**：`from core import EnemyCardGenerator`（实现于 `core/render/`）。
- **utils**：通用工具；`thread_manager` 运行时再导入渲染相关，避免与 `core` 循环引用。
- **gui**：QML 工作区 + Python 编排（`main_window` / `qml_bridge` / `card_model`）；组件 PascalCase。
- **错误**：统一 `utils/error_handler.py`（如 `RenderError`、`EnemyEvalException`）；展示走 `categorize_error_message`。
- **性能**：资源见 `core/optimization.py`；长任务 `thread_manager`；预览防抖 `debouncer`。
- **代码风格**：私有 `_` 前缀；完整类型注解（GUI 尤甚）；导入顺序：标准库 → 第三方 → 本项目。

## 目录结构（索引）

```
enemy_eval/
├── main.py / gui_main.py          # CLI / GUI 入口
├── models/                        # Pydantic（EnemyData、技能、样式等）
├── core/
│   ├── fonts.py / optimization.py
│   └── render/                    # generator、layout、wiki_text、stars、sections/
├── utils/                         # debouncer、error_handler、thread_manager 等
├── gui/                           # main_window、qml/、card_model、qml_bridge、render_coordinator
├── data/                          # *_config.json
├── enemy/                         # 按敌人分的资源
├── resource/                      # ico 等
├── AGENTS.md
├── CHANGELOG.md
├── pyproject.toml                 # [project].version 为唯一版本号来源
└── uv.lock
```

## 发版（仅当用户明确要求发版 / release）

1. 把 `CHANGELOG.md`「未发布」剪切到本版；对照自上次 tag 核对完整性。
2. SemVer：AI **只可建议或修改 `Y` 或 `Z`**；**禁止改 `X`**，除非用户手写指定。
   - 变化大：`Y+1`，`Z=0`。
   - 变化小：`Z+1`。
3. 更新 `CHANGELOG.md` 对应版本节；`pyproject.toml` 的 `[project].version` 与之一致（`utils.app_version` 读此处）。
4. Git：提交信息示例 `chore: release X.Y.Z`。附注 tag 示例：`git tag -a vX.Y.Z -m "release X.Y.Z"`。**未经授权不要代为 `git push`。**

## 打包（Windows 参考）

```bash
pyinstaller --noconfirm --clean enemyEval.spec
```
