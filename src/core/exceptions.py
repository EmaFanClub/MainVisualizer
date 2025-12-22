"""
MainVisualizer 自定义异常

定义系统中使用的所有异常类，遵循层级结构便于精确捕获和处理错误。
"""

from __future__ import annotations


class MainVisualizerError(Exception):
    """
    所有MainVisualizer异常的基类
    
    所有模块特定异常都应继承此类，以便统一捕获和处理。
    """
    
    def __init__(self, message: str, details: dict | None = None) -> None:
        """
        初始化异常
        
        Args:
            message: 错误信息描述
            details: 可选的详细信息字典，用于调试
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | 详情: {self.details}"
        return self.message


class ConfigurationError(MainVisualizerError):
    """
    配置相关错误
    
    当配置文件缺失、格式错误或必需配置项未设置时抛出。
    """
    pass


class DataIngestionError(MainVisualizerError):
    """
    数据摄入层错误
    
    当从数据源读取数据失败时抛出。
    """
    pass


class DatabaseConnectionError(DataIngestionError):
    """
    数据库连接错误
    
    当无法建立数据库连接或连接断开时抛出。
    """
    pass


class DatabaseQueryError(DataIngestionError):
    """
    数据库查询错误
    
    当SQL查询执行失败时抛出。
    """
    pass


class ScreenshotLoadError(DataIngestionError):
    """
    截图加载错误
    
    当无法加载指定截图时抛出。
    """
    pass


class ScreenshotNotFoundError(ScreenshotLoadError):
    """
    截图未找到错误
    
    当指定时间戳或ID对应的截图不存在时抛出。
    """
    pass


class ActivityParseError(DataIngestionError):
    """
    活动数据解析错误
    
    当活动记录格式无效或无法解析时抛出。
    """
    pass


class SenatusError(MainVisualizerError):
    """
    Senatus模块错误
    
    Senatus智能触发模块相关错误。
    """
    pass


class VLMProviderError(MainVisualizerError):
    """
    VLM提供商调用错误
    
    当VLM API调用失败时抛出。
    """
    pass


class VLMConnectionError(VLMProviderError):
    """
    VLM连接错误
    
    当无法连接到VLM服务时抛出。
    """
    pass


class VLMRateLimitError(VLMProviderError):
    """
    VLM速率限制错误
    
    当VLM API调用超出速率限制时抛出。
    """
    pass


class VLMResponseParseError(VLMProviderError):
    """
    VLM响应解析错误
    
    当无法解析VLM响应内容时抛出。
    """
    pass


class StorageError(MainVisualizerError):
    """
    存储层错误
    
    当数据存储操作失败时抛出。
    """
    pass
