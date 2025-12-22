"""
Admina模块

VLM/LLM调用层，负责与各种VLM提供商交互，执行深度视觉分析。

公开接口:
- QwenVLProvider: 阿里云DashScope Qwen VL提供商
- OllamaProvider: Ollama本地服务提供商
- VLMRequest: VLM请求数据模型
- VLMResponse: VLM响应数据模型
- AnalysisResult: 屏幕分析结果数据模型
"""

from .models import (
    AnalysisResult,
    ChatMessage,
    ImageContent,
    MessageContent,
    ScreenContentType,
    TokenUsage,
    VLMRequest,
    VLMResponse,
)
from .providers import (
    BaseVLMProvider,
    OllamaProvider,
    QwenVLProvider,
)

__all__ = [
    # 提供商
    "BaseVLMProvider",
    "OllamaProvider",
    "QwenVLProvider",
    # 请求模型
    "ChatMessage",
    "ImageContent",
    "MessageContent",
    "VLMRequest",
    # 响应模型
    "AnalysisResult",
    "ScreenContentType",
    "TokenUsage",
    "VLMResponse",
]
