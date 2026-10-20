# 07 验收、回滚与 `AGENTS.md` 同步

**优先级** P0（贯穿全程）　**依赖** 全部

## 7.0 批次 0：冻结基线（开批前一次性，只读不改代码）

未完成本节不得开始批次 1（D12）。产出全部回填本文件，并作为独立 commit 提交（`chore(todos): freeze refactor baseline`）。

| # | 冻结项 | 落盘位置 | 方法 |
|---|---|---|---|
| 0.1 | 审计指标（包规模、最大文件、真死代码、字段散落、测试覆盖） | `00-overview.md`「审计基线」表（已填，重跑核对一遍） | `00` 表内"来源"列所述统计 |
| 0.2 | 像素基线（4 组，**解码后像素字节**的 sha256） | §7.2 表格「基线」列 | §7.2 脚本 |
| 0.3 | 测试数与用例清单 | 本文件附录 | `uv run pytest --collect-only -q` |
| 0.4 | QML 装载基线（当前无警告、无缺失组件） | 本文件附录 | §7.1 第 4、5 步 |
| 0.5 | 引用点普查输出（含相对导入） | 本文件附录 | §7.1 第 2 步 |

附：**取基线前先清干净构建残留**——删除 `build/`、`dist/` 与全仓库 `__pycache__`。理由：`dist/enemyEval/_internal/` 里含 `.py`/`.qml` 副本（旧模块路径），会让字符串检索与打包校验出现假命中。此后每批涉及打包时，打包前同样先删 `dist/`。

### 批次 0 实测结果（2026-10-20，基线 `142d7a6`）

| # | 项 | 结果 |
|---|---|---|
| 0.1 | 审计指标 | 与 `00-overview.md`「审计基线」表一致（未改动，复核通过） |
| 0.2 | 像素基线 | 5 组样本，见 §7.2 表；全部取自**已跟踪**文件，无网络、无本地缺失资源依赖 |
| 0.3 | 测试数 | **141**（`uv run pytest --collect-only -q`） |
| 0.4 | QML 静态检查 | `pyside6-qmllint -I gui/qml gui/qml/*.qml` → **exit 0，5 Warning + 5 Info**；全部集中在 `gui/qml/RatingDisplaySwitch.qml`（嵌套组件里用外层 id 的 `Unqualified access`，需 `pragma ComponentBehavior: Bound`）→ **属既有问题，与本计划无关，见各批「顺带发现」** |
| 0.5 | 引用点普查 | 71 行导入语句（含相对导入与函数内导入），已按文件登记，见 `01` 的映射表 |
| 0.6 | 构建残留 | `build/`（36M）、`dist/`（299M）与全仓库 `__pycache__` 已删除 |
| 0.7 | `pyright` 现状 | **当前不可作门禁**：未配置 venv/解释器 → 大量 `reportMissingImports`（httpx / structlog / platformdirs / skia / PySide6 等）；另有 2 处**既有**真实类型错误：`utils/prts/pipeline.py:148`（`_enemy_from_parse_response` 收到 `dict \| None`）、`tests/test_prts_pipeline_refactor.py:84`（`Literal['网络超时'] in str \| None`）→ 批次 5 先配好 pyright 再决定是否清零，本计划各批**不以 pyright 为验收项** |

## 7.1 统一验收序列（每批结束必跑）

```bash
# 1) 依赖方向自证（铁律 14）
uv run python -c "import models"
uv run python -c "import core"
uv run python -c "import main"

# 2) 引用普查：悬空导入 + 旧模块名残留（能解析相对导入与 `from . import X` 形态）
uv run python - <<'PY'
import ast, pathlib
root = pathlib.Path('.'); skip = {'.venv','__pycache__','.git','dist','build','todos','.agents'}
files = [p for p in root.rglob('*.py') if not any(s in p.parts for s in skip)]
mods = {'.'.join(p.relative_to(root).with_suffix('').parts) for p in files}
pkgs = set()
for m in mods:
    parts = m.split('.')
    for i in range(1, len(parts)):
        pkgs.add('.'.join(parts[:i]))
OLD = {'error_handler','app_identity','app_version','app_logging','update_checker','resource_manager',
       'prts_api_client','prts_mediawiki_pipeline','prts_enemy_builder','prts_field_mapping',
       'wiki_template_parser','ai_client','ai_prompt','ai_baseline','debouncer','filenames','avatar_paths'}
problems = []
for p in files:
    rel = str(p).replace('\\','/')
    tree = ast.parse(p.read_text(encoding='utf-8', errors='replace'))
    pkg = '.'.join(p.relative_to(root).with_suffix('').parts[:-1])
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        base = pkg.split('.')
        base = base[:len(base) - (node.level - 1)] if node.level else []
        target = '.'.join(base + ([node.module] if node.module else []))
        if target.split('.')[0] in {'utils','core','gui','models'} and target not in mods and target not in pkgs:
            problems.append(f'{rel}:{node.lineno} 悬空 → {target}')
            continue
        if target in pkgs or target in ('', pkg):
            for name in [a.name for a in node.names]:
                if name in OLD and f'{target}.{name}' not in mods and f'{pkg}.{name}' not in mods:
                    problems.append(f'{rel}:{node.lineno} 旧名残留 → {target or "(相对)"} import {name}')
print('✅ 无悬空导入、无旧模块名残留' if not problems else '\n'.join(problems))
PY

# 2b) 注释与文档字符串里写的文件路径必须真实存在（避免注释指向已搬走的文件）
uv run python - <<'PY'
import pathlib, re
root = pathlib.Path('.'); skip = {'.venv','__pycache__','.git','dist','build','todos','.agents'}
bad, seen = [], 0
for p in list(root.rglob('*.py')) + [pathlib.Path('AGENTS.md')]:
    if any(s in p.parts for s in skip):
        continue
    for i, line in enumerate(p.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
        for m in re.finditer(r'(?:utils|core|gui|models|scripts|tests|resource|data|example)/[\w./\-]*\.(?:py|qml|json|txt|md)', line):
            seen += 1
            if not pathlib.Path(m.group(0)).exists():
                bad.append(f'{p}:{i} → {m.group(0)}')
print(f'{seen} 处路径引用；' + ('✅ 全部存在' if not bad else '\n'.join(bad)))
# 注：AGENTS.md 的失效路径按 D10 不修，登记在 §7.6
PY

# 2c) 目录深度假设核查【本批新增】：移动文件后，任何 `Path(__file__).parents[N]` / `parent.parent`
#     推断的项目根都会偏移；上面 2/2b 抓不到这类问题（像素样本也抓不到）
uv run python - <<'PY'
import pathlib
skip = {'.venv','__pycache__','.git','dist','build','todos','.agents'}
for p in sorted(pathlib.Path('.').rglob('*.py')):
    if any(s in p.parts for s in skip):
        continue
    depth = len(p.parts) - 1  # 文件所在目录深度；仓库根文件为 1
    for i, line in enumerate(p.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
        if 'parents[' in line or 'parent.parent' in line:
            print(f'{p}:{i}  深度={depth}  {line.strip()}')
# 人工逐条确认：parents[N] 的目标是否仍等于仓库根/预期目录
PY

# 3) 单元测试
uv run pytest -q

# 4) QML 静态检查（按改动的目录扩展 -I；批次 4.2 起 gui/qml 有子目录）
pyside6-qmllint -I gui/qml -I gui/qml/components -I gui/qml/pages -I gui/qml/dialogs \
    gui/qml/*.qml gui/qml/components/*.qml gui/qml/pages/*.qml gui/qml/dialogs/*.qml

# 5) QML 装载冒烟（offscreen）
QT_QPA_PLATFORM=offscreen uv run python gui_main.py    # 人工看日志：无 QML 警告、QML 就绪
```

## 7.2 渲染像素回归（"功能不缺失"的硬证据）

四组样本，批次 0 先把基线填进下表。

**口径（避免假红/假绿）**
- 比对**解码后像素字节**的 sha256（如 `image.tobytes()`），**不比对 PNG 文件字节**——文件字节会受编码器与元数据影响。
- 渲染**直接调 `core` 生成器**（`EnemyCardGenerator().generate_card_image(enemy, options)`），不经 Qt、不复用 GUI 线程：更快，且少一个变量（`core` 无 PySide6 依赖）。
- 样本 1 的 `avatar_path` 指向不存在的 `E:/pythonProject/enemy_eval/enemy/墟/头像_敌人_资深的小弟.png`（仓库在 `D:`），渲染走"缓存未命中即跳过"的既有路径——**基线必须保持这个状态**：不要中途修数据文件或补图，否则基线作废。

| # | 样本 | 构造 | 覆盖 | 基线尺寸 | 基线 sha256（解码后像素） |
|---|---|---|---|---|---|
| S1 | 小杂毛 默认 | `data/小杂毛_config.json` 原样 | 0 技能 / 1 天赋 / 3 评价维度 / 头像缺失走跳过路径 | 1950×1500 | `efde66b23d32d5613e0d3dcdb6dff9953b78d77694b385bbc91645df47321033` |
| S2 | 小杂毛 + 雷达 | S1 且 `RenderOptions(rating_radar=True)` | 左侧评价区雷达形态 | 1950×1500 | `fbee41858f059428bf271d7acc2c20312290d93f772d428513de7c92c5e0b6ef` |
| S3 | 杰斯顿 长内容 | `resource/baseline/jesselton_config.json` + `grade='S'`、`brief_comment=''`、`avatar_path=None` | 2 技能 / 320 字天赋 / 149 字描述 / 0 评价维度 | 1950×1500 | `5a1b03e0ebe060cd9f9eaa61205eeeddb81064bbabcdea0e25fc24e0acdf7587` |
| S4 | 兜底 空内容 | S1 且 `skills=[]`、`talents_abilities=''`、`brief_comment=''`、`ratings=[]`、`brief_description=''` | 空占位与 `GRADE_BLOCK_MIN_H` 兜底 | 1950×1500 | `cf651b4cb02148be170eab6a5fc1e65eece3c35d5b63a9a0a5880922b19b02c9` |
| S5 | 杰斯顿 8 技能（增高） | S3 的 `skills` 重复 ×4 | 内容驱动增高（可变 Surface + 等级块顺延） | **1950×1795** | `5f920ec0c8590f8de0c683b4683004db80ef93e7116c896d3df2dbe32b5f7da2` |

**复现脚本（原样保存，勿改；改前需先回填新基线）**

```python
import hashlib, json, pathlib
from models import EnemyData, RenderOptions
from core import EnemyCardGenerator

gen = EnemyCardGenerator()
load = lambda p: json.loads(pathlib.Path(p).read_text(encoding="utf-8"))

base = load("data/小杂毛_config.json")
jess = load("resource/baseline/jesselton_config.json")
jess.update({"grade": "S", "brief_comment": "", "avatar_path": None})
minimal = dict(base, skills=[], talents_abilities="", brief_comment="", ratings=[], brief_description="")
tall = dict(jess, skills=jess["skills"] * 4)

samples = [
    ("S1", EnemyData.model_validate(base), False),
    ("S2", EnemyData.model_validate(base), True),
    ("S3", EnemyData.model_validate(jess), False),
    ("S4", EnemyData.model_validate(minimal), False),
    ("S5", EnemyData.model_validate(tall), False),
]
for name, enemy, radar in samples:
    img = gen.generate_card_image(enemy, RenderOptions(rating_radar=radar))
    print(name, f"{img.width()}x{img.height()}", hashlib.sha256(img.tobytes()).hexdigest())
```

运行方式：`uv run python <脚本>`（`core` 无 PySide6 依赖，无需 offscreen；字体走本机 `C:/Windows/Fonts/simhei.ttf`，换机比对无效）。

```bash
# 复现脚本见上一小节（原样运行，勿改）
```

| 样本 | 基线 sha256 | 批次 1 | 批次 2 | 批次 3 | 批次 4 | 批次 5 | 批次 6 |
|---|---|---|---|---|---|---|---|
| S1 | `efde66b2…1033` | ✅ | ✅ | ✅ | | | |
| S2 | `fbee4185…b6ef` | ✅ | ✅ | ✅ | | | |
| S3 | `5a1b03e0…7587` | ✅ | ✅ | ✅ | | | |
| S4 | `cf651b4c…02c9` | ✅ | ✅ | ✅ | | | |
| S5 | `5f920ec0…7da2` | ✅ | ✅ | ✅ | | | |

> 批次 1/2 的"✅"证据来自批次 3 会话的**改动前**实测（树含批次 1+2 的改动，5 组 sha256 与基线逐字一致）；批次 3 的"✅"是改动**后**实测结果（2026-10-20）。

> 任一格与基线不同 = 该批失败，先回滚再定位。本计划不含任何渲染改动，**不允许出现"差异可接受"的判断**；批次 6 的性能项若改变像素，同样按该项失败处理（回退）。

## 7.3 手工冒烟（每批，最少 5 条路径）

1. 启动 → 打开一份配置 → 预览出现。
2. 编辑一个字段（如攻击方式/技能效果）→ 预览更新（防抖生效、无花屏）。
3. 导出 PNG → 文件可用。
4. PRTS 查询 + 级别切换（人工联网）。
5. AI 设置（保存 Base URL）→ AI 生成简评 → 采纳 → Ctrl+Z 撤销。

## 7.4 涉及打包的批次（1、3、5）

```bash
uv run --group build -- pyinstaller --noconfirm --clean enemy_eval.spec   # 批次 5 已改名
uv run --group build -- python scripts/build_release.py                  # 校验 + 打 zip
```
产物校验清单见 `todos/feat-20260929/05-portable-distribution.md:115-117`（`dist/enemyEval/enemyEval.exe`、`_internal/build_info.json`、`_internal/gui/qml`、`_internal/resource`、`opengl32sw.dll`、`Qt6ShaderTools.dll`、`qml/QtQuick/Controls`）。
**注意**：spec 的 `hiddenimports` 含 `core.render.generator`、`core.render.avatar_prefetch`——本计划**不移动**这两个模块（`core/render/` 下只新增子目录与拆出的基础设施模块），但每批改完 `core` 结构后仍要复核这一行没有指向已不存在的模块。spec 的 `project_data` 是目录级复制（`("resource","resource")`、`("gui/qml","gui/qml")`），批次 4 的 QML 子目录会随之进包，**无需改 spec**。

## 7.5 提交与回滚

| 项 | 约定 |
|---|---|
| 提交信息 | `refactor(<scope>): <一句话>`，正文列"不变量"：本次未改行为的三条证据（pytest / 像素 sha256 / 冒烟路径） |
| 粒度 | 每批一个 commit；批次 2、3、4、6 内可再拆（按小节/按项） |
| 回滚 | `git revert <commit>`；批次内独立项回滚不影响其他项 |
| 禁止 | 同一 commit 内夹带行为改动；`git push`；打 tag；改 `uv.lock` |

## 7.6 `AGENTS.md` 同步清单（**已于 2026-10-20 按用户要求同步完成**，下表保留为对照记录）

| # | 位置 | 现内容 | 迁移后需改成 | 影响批次 |
|---|---|---|---|---|
| 1 | 铁律 6 | 例外路径 `utils/thread_manager.py` 的 `CardGeneratorThread.run` / `PrtsFetchThread._pull` / `NetworkAvatarPrefetchThread._pull` | `utils/qt/render_task.py` / `utils/qt/prts_task.py` / `utils/qt/avatar_task.py` | 2 |
| 2 | 铁律 7 | 偏好存储条目里的 `utils/app_settings_store.py` | `utils/app/settings.py`（另四个偏好模块：`rating_prefs` / `ai_prefs` / `render_prefs` / `update_prefs`） | 1、2 |
| 3 | 铁律 13 | 示例 `from utils.thread_manager import PrtsFetchThread` / `from utils.app_settings_store import current_render_options` | `utils.qt.prts_task` / `utils.app.render_prefs` | 1、2 |
| 4 | 铁律 14 | "`utils` 不得模块级 `import core`；新增跨包 import 前自证不成环" | 结论不变，示例路径更新 | 1、2 |
| 5 | 架构要点·对外渲染 | `from core import EnemyCardGenerator`（实现在 `core/render/`）；"唯一绘制入口 `_draw_card`" | 增补 `core/render/text/`、`core/render/primitives/`；注明 `core/__init__` 只导出 `EnemyCardGenerator` | 3 |
| 6 | 架构要点·网络头像 | 渲染侧只查全局图像缓存；`core/render/avatar_prefetch.py` | 路径不变，补一句"全局图像缓存与锁在 `core/render/image_cache.py`" | 3 |
| 7 | 架构要点·PRTS | `utils/prts_api_client.py`、`utils/prts_mediawiki_pipeline.py` | `utils/prts/api_client.py`、`utils/prts/pipeline.py` | 1 |
| 8 | 架构要点·错误 | `utils/error_handler.py`（`RenderError` / `EnemyEvalException` / `FileOperationError`） | `utils/errors.py` | 1 |
| 9 | 架构要点·性能 | 图像缓存 `core/optimization.py`、预览防抖 `utils/debouncer.py` | `core/render/image_cache.py`、`utils/qt/debounce.py` | 1、3 |
| 10 | 架构要点·文件名 | `utils/filenames.py::safe_filename` | `utils/fs/filenames.py::safe_filename` | 1 |
| 11 | 架构要点·版本 | `utils/app_version.py` | `utils/app/version.py` | 1 |
| 12 | 目录索引 | 目录树（含 `enemyEval.spec`、`core/render/`、`utils/`、`gui/qml/`） | 与新结构一致：`core/render/{text,primitives}/`、`utils/{app,prts,ai,net,qt,fs}/`、`gui/bridge/`、`gui/qml/{components,pages,dialogs}/` | 1–5 |
| 13 | 打包命令 | `pyinstaller --noconfirm --clean enemyEval.spec` | `enemy_eval.spec` | 5 |
| 14 | 架构要点·gui | "Python 编排 `main_window` / `qml_bridge` / `card_model` / `skill_list_model` / `render_coordinator`" | 补 `gui/bridge/`（按域实现，声明面留在 `qml_bridge.py`）与 `CardImageProvider` 现位置 `gui/bridge/preview.py` | 4 |

> 实测 `AGENTS.md` 共出现 17 个代码路径，其中 `models/media.py`、`Theme.qml`、`main.py`、`gui_main.py`、`pyproject.toml`、`data/{敌人名称}_config.json` 等**路径不变**，无需同步；上表 13 条覆盖全部会失效的引用。

**处理方式**：批次 1–5 期间**不动 `AGENTS.md`**；每批结束时把"使哪条失效"记到本表；由用户决定何时一次性同步（届时由用户明确要求）。

**批次 2 已核对上表**：第 1、2、3 条的目标路径已随代码落地并实测存在（`utils/qt/{render_task,prts_task,avatar_task}.py`、`utils/app/{settings,rating_prefs,ai_prefs,render_prefs,update_prefs}.py`）；AGENTS.md 全文没有 `utils/network_image.py` 引用，本次无需新增条目。

**批次 3 补充**：第 6、9 条的目标模块名按实际落地为 `core/render/image_cache.py`（全局图像缓存 + 锁 + `cache_get/cache_put/cache_has/cache_clear`）；第 5 条提到的 `core/render/primitives/` 与 `core/render/text/` 已建成；`AGENTS.md` 目录索引（第 12 条）还需补 `core/render/text/`、`core/render/primitives/` 与拆出的 7 个渲染基础模块。

## 7.7 用户本地动作清单（我无法代做）

| 项 | 何时 | 命令 |
|---|---|---|
| 依赖/锁文件（若批次 5 动了 `pyproject.toml`） | 批次 5 后 | `uv lock` / `uv sync` |
| 打包实测 | 批次 1、3、5 后 | 见 7.4 |
| 人工联网冒烟 | 批次 2、4 后 | PRTS 查询 / AI 生成 / 更新检查 |
| `pytest` 与像素脚本 | 每批（铁律 3：验证由用户本机运行） | 见 7.1、7.2 |

## 7.8 收尾

- [x] 批次 1–6 完成后，重跑 `00-overview.md` 的「审计基线」全部指标，产出"改后"对照表（包规模、最大文件、真死代码归零、字段散落不变或下降、`utils` 单文件行数分布）。→ 2026-10-20 完成，表在 `00-overview.md`「改后对照」。**字段散落未改善**（`max_hp` 10 处 / `attack_interval` 9 处），已在表内标注为结构性问题、本计划未覆盖。
- [x] 判定 `CHANGELOG.md` 是否需要条目：本次无用户可感知变化 → **默认不写**；若最终决定改产物名/入口名（属行为变化，需另批），才写「变更」。→ 判定：**不写**。spec 改名与入口声明都不改变 exe / zip 名与双击行为。
- [x] 把本目录状态表全部置为"已实施"，并在 `README.md` 记录完成日期与实际偏移（哪些批次跳过、哪些结论被修正）。→ 批次 6 跳过；批次 5 的 `qml_bridge.py < 250 行` 已修正为 `≤ 550 行`；5.3 的 ruff 三行按用户要求作废；`[build-system]` 未加。

## 7.7' 未完成的本机动作（收尾时仍属用户）

| 项 | 状态 |
|---|---|
| `uv run pytest -q` | 我实测 141 passed；按铁律 3 仍需本机确认 |
| 像素 5 组 sha256（§7.2） | 未由助手执行，待本机 |
| 打包（§7.4，`enemy_eval.spec`） | 待本机 |
| `AGENTS.md` 14 条同步 | 待用户授权 |

## 7.9 测试隔离目标（批次 1/2 改动前必看）

`tests/conftest.py` 用字符串 patch 隔离真实偏好文件。批次 2 已把目标改为（现状）：

```python
monkeypatch.setattr("utils.app.settings.settings_file_path", lambda: path)
monkeypatch.setattr("utils.app.settings._cached", None)
```

- 目标名不存在时 `monkeypatch.setattr` 会直接报错（可见、安全）；但若被改到**另一个真实存在**的对象上，测试就会静默读写本机偏好文件。因此改完必须核对真实偏好文件
  `platformdirs.user_config_path("牢杰的物种奇遇", appauthor="双老蜂")/app_settings.json`
  的 mtime 未变。
- `settings.py` 内部若重命名 `_cached`，会连带打断 conftest——属预期联动，一并改。
