"""
日志工具模块

提供统一的日志配置和获取接口，确保全项目日志格式一致。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional


# 日志格式常量
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 默认日志级别
DEFAULT_LOG_LEVEL = logging.INFO


def setup_logging(
    level: int = DEFAULT_LOG_LEVEL,
    log_file: Optional[Path] = None,
    log_format: str = LOG_FORMAT,
) -> None:
    """
    配置全局日志设置
    
    Args:
        level: 日志级别，默认INFO
        log_file: 可选的日志文件路径，为None时只输出到控制台
        log_format: 日志格式字符串
    """
    handlers: list[logging.Handler] = []
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format, LOG_DATE_FORMAT))
    handlers.append(console_handler)
    
    # 文件处理器（如果指定了日志文件）
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(log_format, LOG_DATE_FORMAT))
        handlers.append(file_handler)
    
    # 配置根日志器
    logging.basicConfig(
        level=level,
        handlers=handlers,
        format=log_format,
        datefmt=LOG_DATE_FORMAT,
    )


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志器
    
    Args:
        name: 日志器名称，通常使用 __name__
        
    Returns:
        配置好的日志器实例
        
    Example:
        logger = get_logger(__name__)
        logger.info("处理活动数据")
    """
    return logging.getLogger(name)
