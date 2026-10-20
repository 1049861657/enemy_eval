"""跨层错误词表与界面文案归类。

`error_handler` 把非业务异常包成 `EnemyEvalException`（`silent=True` 只记日志）；
`categorize_error_message` 是 异常 → (标题, 文案) 的唯一映射点。
"""
import logging
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)


class EnemyEvalException(Exception):
    pass


class RenderError(EnemyEvalException):
    pass


class FileOperationError(EnemyEvalException):
    pass


class AiCredentialError(EnemyEvalException):
    """AI 调用凭证缺失或无效（未配置 / HTTP 401）。"""


class AiRateLimitError(EnemyEvalException):
    """AI 服务限流（HTTP 429）。"""


class AiServiceError(EnemyEvalException):
    """AI 服务端异常（5xx / 其他错误状态码）或响应无法解析。"""


class AiNetworkError(EnemyEvalException):
    """AI 服务连接失败或读超时。"""


@contextmanager
def error_handler(operation: str, silent: bool = False) -> Generator[None, None, None]:
    """统一错误语义：业务异常原样上抛，其余包成 `EnemyEvalException`（消息带 operation 前缀）。

    `silent=True` 只记 warning 不抛，用于失败无妨的路径（如关窗清理）。
    """
    try:
        yield
    except EnemyEvalException:
        # 重新抛出业务异常
        raise
    except Exception as e:
        error_msg = f"{operation} 失败: {e}"
        logger.error(error_msg, exc_info=True)
        if not silent:
            raise EnemyEvalException(error_msg) from e
        logger.warning("静默失败: %s", error_msg)


def categorize_error_message(error_message: Exception | str) -> tuple[str, str]:
    """异常或原始文本 → (标题, 用户可读正文)；界面只消费这一处映射。"""
    if isinstance(error_message, AiCredentialError):
        return (
            "AI 配置错误",
            f"AI 评价无法使用：\n\n{error_message}\n\n请在「更多 → AI 设置」中检查 Base URL、模型与密钥。",
        )
    if isinstance(error_message, AiRateLimitError):
        return "AI 请求受限", f"{error_message}\n\n请稍后重试。"
    if isinstance(error_message, AiServiceError):
        return (
            "AI 服务异常",
            f"{error_message}\n\n若持续失败，请核对 Base URL、模型名与账户余额。",
        )
    if isinstance(error_message, AiNetworkError):
        return (
            "AI 网络异常",
            f"{error_message}\n\n请检查网络连接；若为响应超时，可换用响应更快的模型重试。",
        )

    error_message = str(error_message)
    if "图像转换失败" in error_message:
        return "图像处理错误", "卡片图像转换失败，请检查图像资源文件。"
    elif "无法读取" in error_message:
        return "文件读取错误", "无法读取必要的文件，请检查文件路径和权限。"
    elif "保存" in error_message and "失败" in error_message:
        return "保存失败", f"文件保存失败：\n\n{error_message}\n\n请检查文件路径和磁盘空间。"
    elif "加载" in error_message and "失败" in error_message:
        return "加载失败", f"配置文件加载失败：\n\n{error_message}\n\n请检查文件格式和内容。"
    else:
        return "操作错误", f"操作失败：\n\n{error_message}\n\n请检查设置和资源文件。"