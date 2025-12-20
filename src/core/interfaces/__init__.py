"""
core.interfaces包初始化

核心接口定义，提供模块间通信的抽象基类。
"""

from .data_source import IActivityDataSource, IScreenshotLoader

__all__ = [
    "IActivityDataSource",
    "IScreenshotLoader",
]
