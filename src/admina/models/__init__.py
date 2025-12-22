"""
Admina数据模型包

提供VLM请求和响应的数据结构定义。
"""

from .vlm_request import (
    ChatMessage,
    ContentType,
    ImageContent,
    MessageContent,
    MessageRole,
    VLMRequest,
)
from .vlm_response import (
    AnalysisResult,
    ScreenContentType,
    TokenUsage,
    VLMResponse,
)

__all__ = [
    # 请求模型
    "ChatMessage",
    "ContentType",
    "ImageContent",
    "MessageContent",
    "MessageRole",
    "VLMRequest",
    # 响应模型
    "AnalysisResult",
    "ScreenContentType",
    "TokenUsage",
    "VLMResponse",
]
