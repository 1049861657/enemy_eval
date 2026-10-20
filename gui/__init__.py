"""GUI 层：QML 界面（`qml/`）与 Python 编排（`main_window` / `qml_bridge` / `bridge/` / 模型 / 渲染协调）。

界面只在 QML；Python 负责数据、线程与文件。QML 可见名与信号签名是冻结契约（见 `gui/qml_bridge.py`）。
"""