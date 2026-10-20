"""网络传输中立层：HTTP 超时/重试策略与图像下载。

契约：不依赖其它 `utils` 子包（`prts` / `ai` / `app` 反向依赖本包），也不含领域语义
（PRTS 端点、AI 协议、更新检查响应格式都不在此）。
`image_fetch` 只把字节交给调用方：下载方不写全局图像缓存，缓存读写见
`core/optimization.py` 与 `core/render/avatar_prefetch.py`。

不做聚合导出：调用方直接引用子模块（`from utils.net.transport import build_timeout`）。
"""
