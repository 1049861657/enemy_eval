"""GUI 色彩常量。

集中定义全部内联 QSS 颜色值，消除同色不同名/同名不同色问题。

Element UI 调色板（#409eff 系）：用于主操作按钮、输入框焦点边框等。
Action 调色板（#3b82f6 系，Tailwind blue）：用于 DetailedEditorDialog 保存按钮渐变。
"""

# ── Element UI 蓝 ─────────────────────────────────────────────────────────────
PRIMARY_COLOR = "#409eff"          # 主色：按钮底色、焦点边框
PRIMARY_HOVER = "#66b1ff"          # 主色悬停
PRIMARY_PRESSED = "#3a8ee6"        # 主色按下
DISABLED_BG = "#c0c4cc"            # 禁用背景
DISABLED_FG = "#ffffff"            # 禁用前景

# ── Action 渐变蓝（DetailedEditorDialog 保存按钮）─────────────────────────────
ACTION_PRIMARY_TOP = "#3b82f6"     # 渐变起始
ACTION_PRIMARY_BOT = "#1d4ed8"     # 渐变结束
ACTION_HOVER_TOP = "#2563eb"
ACTION_HOVER_BOT = "#1e40af"
ACTION_PRESSED_TOP = "#1d4ed8"
ACTION_PRESSED_BOT = "#1e3a8a"

# ── 中性色 ────────────────────────────────────────────────────────────────────
BORDER_DEFAULT = "#dcdfe6"         # 默认边框
BORDER_HOVER = "#c0c4cc"           # 悬停边框（与 DISABLED_BG 同值，语义不同）
TEXT_PRIMARY = "#303133"
TEXT_SECONDARY = "#606266"
TEXT_PLACEHOLDER = "#94a3b8"

# ── 背景 ──────────────────────────────────────────────────────────────────────
BG_CANVAS = "#f8fafc"
BG_CANVAS_END = "#e2e8f0"
BG_WHITE = "white"
BG_SUBTLE = "#f1f5f9"
BG_CANCEL = "#f5f5f5"
BG_CANCEL_HOVER = "#ecf5ff"
BG_CANCEL_PRESSED = "#d9ecff"

# ── 语义色 ────────────────────────────────────────────────────────────────────
ERROR_COLOR = "#f56c6c"
