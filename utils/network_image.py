"""
网络图片支持工具 - 最小侵入性实现
"""

import io
import hashlib
from typing import Optional
from urllib.request import urlopen
from urllib.parse import urlparse
from urllib.error import URLError, HTTPError


def is_url(path: str) -> bool:
    """检查路径是否为网络URL"""
    try:
        parsed = urlparse(path)
        return parsed.scheme in ('http', 'https')
    except:
        return False


def download_image_data(url: str, timeout: int = 10, max_size: int = 10 * 1024 * 1024) -> Optional[bytes]:
    """
    下载网络图片数据
    
    Args:
        url: 图片URL
        timeout: 超时时间（秒）
        max_size: 最大文件大小（字节）
        
    Returns:
        图片二进制数据，失败返回None
    """
    try:
        # 基础URL验证
        if not is_url(url):
            return None
            
        # 下载图片数据
        with urlopen(url, timeout=timeout) as response:
            # 检查内容类型
            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                return None
                
            # 检查文件大小
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) > max_size:
                return None
                
            # 分块下载，控制大小
            data = io.BytesIO()
            total_size = 0
            
            while True:
                chunk = response.read(8192)  # 8KB chunks
                if not chunk:
                    break
                    
                total_size += len(chunk)
                if total_size > max_size:
                    return None
                    
                data.write(chunk)
            
            return data.getvalue()
            
    except (URLError, HTTPError, OSError, Exception):
        # 所有网络和解析错误都静默处理
        return None


def get_url_cache_key(url: str) -> str:
    """为URL生成缓存键"""
    return f"url_{hashlib.md5(url.encode()).hexdigest()}"