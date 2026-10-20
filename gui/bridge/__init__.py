"""桥接域实现：QML 可见名字的声明留在 `gui/qml_bridge.py`，逻辑按域落在这里。

契约：本包只依赖 `models` / `utils` 与本包的模型类，不声明 Qt 元对象（信号、属性一律在
`QmlBridge` 上——PySide6 不支持从非 QObject mixin 继承元对象）；函数显式接收所需协作者，
不读全局单例。QML 可见名与信号签名是冻结契约（见 `todos/refactor-20261016/04`）。
不做聚合导出：调用方直接引用子模块（`from gui.bridge import editor`）。
"""
