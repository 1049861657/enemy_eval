"""文件系统边界：文件名消毒、头像路径存储形式互转。

契约：不读偏好、不发起网络、不依赖 Qt。
不做聚合导出：调用方直接引用子模块（`from utils.fs.filenames import safe_filename`）。
"""
