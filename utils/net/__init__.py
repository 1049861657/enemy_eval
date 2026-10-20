"""网络中立层：HTTP 超时/重试与图像下载；不含 PRTS / AI / 更新检查的领域语义。

`image_fetch` 只交字节，不写全局图像缓存（缓存归 `core/render/image_cache.py`）。
"""
