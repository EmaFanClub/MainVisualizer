"""
VLM提供商接口定义

定义视觉语言模型(VLM)和大语言模型(LLM)提供商的抽象接口。
所有VLM提供商实现（如Qwen VL、Ollama等）都应实现此接口。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncIterator, Optional, Union

if TYPE_CHECKING:
    from PIL import Image


class ProviderType(Enum):
    """提供商类型枚举"""
    
    CLOUD = "cloud"      # 云端API（如DashScope、OpenAI）
    LOCAL = "local"      # 本地服务（如Ollama）


@dataclass
class VLMCapabilities:
    """
    VLM提供商能力描述
    
    描述提供商支持的功能和限制。
    """
    
    supports_vision: bool = True
    """是否支持图像输入"""
    
    supports_video: bool = False
    """是否支持视频输入"""
    
    supports_streaming: bool = True
    """是否支持流式输出"""
    
    supports_multi_image: bool = True
    """是否支持多图像输入"""
    
    max_image_size_mb: float = 20.0
    """最大图像大小（MB）"""
    
    max_tokens: int = 4096
    """最大输出token数"""
    
    supported_image_formats: list[str] = field(
        default_factory=lambda: ["png", "jpg", "jpeg", "webp", "gif"]
    )
    """支持的图像格式"""
    
    provider_type: ProviderType = ProviderType.CLOUD
    """提供商类型"""


@dataclass
class HealthCheckResult:
    """
    健康检查结果
    
    包含提供商健康状态和详细信息。
    """
    
    is_healthy: bool
    """是否健康"""
    
    message: str = ""
    """状态信息"""
    
    latency_ms: Optional[float] = None
    """响应延迟（毫秒）"""
    
    available_models: list[str] = field(default_factory=list)
    """可用模型列表"""


class IVLMProvider(ABC):
    """
    VLM提供商抽象接口
    
    定义与各种VLM/LLM服务交互的标准接口。
    所有提供商实现（如Qwen VL、Ollama等）都应实现此接口。
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        获取提供商名称
        
        Returns:
            提供商标识名称（如"qwen"、"ollama"）
        """
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> VLMCapabilities:
        """
        获取提供商能力描述
        
        Returns:
            VLMCapabilities对象，描述提供商支持的功能
        """
        pass
    
    @abstractmethod
    async def analyze_image(
        self,
        image: Union[Path, str, bytes, "Image.Image"],
        prompt: str,
        *,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """
        分析图像内容
        
        Args:
            image: 图像输入，支持以下格式：
                - Path: 本地文件路径
                - str: 图像URL或Base64字符串
                - bytes: 图像二进制数据
                - Image.Image: PIL图像对象
            prompt: 分析提示词
            model: 使用的模型名称，为None时使用默认模型
            max_tokens: 最大输出token数
            temperature: 生成温度（0-1）
            
        Returns:
            包含分析结果的字典，至少包含：
            - content: str 分析内容
            - model: str 使用的模型
            - usage: dict token使用情况
            
        Raises:
            VLMProviderError: VLM调用失败时抛出
            VLMConnectionError: 连接失败时抛出
        """
        pass
    
    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> Union[dict[str, Any], AsyncIterator[dict[str, Any]]]:
        """
        多轮对话
        
        Args:
            messages: 消息列表，每条消息包含role和content
            model: 使用的模型名称
            max_tokens: 最大输出token数
            temperature: 生成温度（0-1）
            stream: 是否流式输出
            
        Returns:
            非流式：包含响应内容的字典
            流式：响应chunk的异步迭代器
            
        Raises:
            VLMProviderError: VLM调用失败时抛出
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> HealthCheckResult:
        """
        执行健康检查
        
        检查提供商服务是否可用。
        
        Returns:
            HealthCheckResult对象，包含健康状态和详细信息
        """
        pass
    
    @abstractmethod
    async def list_models(self) -> list[str]:
        """
        列出可用模型
        
        Returns:
            可用模型名称列表
        """
        pass
    
    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        has_image: bool = False,
    ) -> float:
        """
        估算调用成本
        
        默认实现返回0（本地模型无成本）。
        云端提供商应覆盖此方法。
        
        Args:
            input_tokens: 输入token数
            output_tokens: 输出token数
            has_image: 是否包含图像
            
        Returns:
            估算成本（USD）
        """
        return 0.0
