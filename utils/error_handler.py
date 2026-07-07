"""
统一错误处理机制
"""
import logging
from contextlib import contextmanager
from typing import Generator, Any

# 设置日志
logger = logging.getLogger(__name__)


class EnemyEvalException(Exception):
    """项目基础异常"""
    pass


class RenderError(EnemyEvalException):
    """渲染错误"""
    pass


class ValidationError(EnemyEvalException):
    """验证错误"""
    pass


class FileOperationError(EnemyEvalException):
    """文件操作错误"""
    pass


@contextmanager
def error_handler(operation: str, silent: bool = False) -> Generator[None, None, None]:
    """统一错误处理上下文管理器
    
    Args:
        operation: 操作描述
        silent: 是否静默失败（不抛出异常）
    """
    try:
        yield
    except EnemyEvalException:
        # 重新抛出业务异常
        raise
    except Exception as e:
        error_msg = f"{operation} 失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        if not silent:
            raise EnemyEvalException(f"{operation} 操作失败") from e
        else:
            logger.warning(f"静默失败: {error_msg}")


def categorize_error_message(error_message: str) -> tuple[str, str]:
    """根据错误信息分类返回标题和用户友好的消息
    
    Args:
        error_message: 原始错误信息
        
    Returns:
        tuple: (错误标题, 用户友好的错误消息)
    """
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