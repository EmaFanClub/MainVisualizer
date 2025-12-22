"""
core核心模块

提供系统基础设施，包括异常定义、接口规范、日志工具等。
"""

from .exceptions import (
    ActivityParseError,
    ConfigurationError,
    DatabaseConnectionError,
    DatabaseQueryError,
    DataIngestionError,
    MainVisualizerError,
    ScreenshotLoadError,
    ScreenshotNotFoundError,
    SenatusError,
    StorageError,
    VLMConnectionError,
    VLMProviderError,
    VLMRateLimitError,
    VLMResponseParseError,
)
from .logger import get_logger, setup_logging

__all__ = [
    # 异常类
    "MainVisualizerError",
    "ConfigurationError",
    "DataIngestionError",
    "DatabaseConnectionError",
    "DatabaseQueryError",
    "ScreenshotLoadError",
    "ScreenshotNotFoundError",
    "ActivityParseError",
    "SenatusError",
    "VLMProviderError",
    "VLMConnectionError",
    "VLMRateLimitError",
    "VLMResponseParseError",
    "StorageError",
    # 日志工具
    "get_logger",
    "setup_logging",
]
