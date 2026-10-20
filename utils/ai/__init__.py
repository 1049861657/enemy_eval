"""AI 评价链路：调用层、提示词、基准数据装配。

契约：配置由调用方注入（本子包不读偏好）；`client` 提供同步与异步两入口，网络错误归一为专用异常。
不做聚合导出：调用方直接引用子模块（`from utils.ai.prompt import build_messages`）。
"""
