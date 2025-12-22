"""
VLM请求数据模型

定义VLM/LLM请求的数据结构。
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union


class ContentType(Enum):
    """内容类型枚举"""
    
    TEXT = "text"
    IMAGE_URL = "image_url"
    IMAGE_BASE64 = "image_base64"


class MessageRole(Enum):
    """消息角色枚举"""
    
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class ImageContent:
    """
    图像内容数据类
    
    支持URL和Base64两种图像输入方式。
    """
    
    url: Optional[str] = None
    """图像URL地址"""
    
    base64_data: Optional[str] = None
    """Base64编码的图像数据"""
    
    detail: str = "auto"
    """图像细节级别: auto, low, high"""
    
    @classmethod
    def from_url(cls, url: str, detail: str = "auto") -> "ImageContent":
        """
        从URL创建图像内容
        
        Args:
            url: 图像URL地址
            detail: 图像细节级别
            
        Returns:
            ImageContent实例
        """
        return cls(url=url, detail=detail)
    
    @classmethod
    def from_base64(
        cls,
        data: str,
        media_type: str = "image/png",
        detail: str = "auto",
    ) -> "ImageContent":
        """
        从Base64数据创建图像内容
        
        Args:
            data: Base64编码的图像数据（不含前缀）
            media_type: 图像MIME类型
            detail: 图像细节级别
            
        Returns:
            ImageContent实例
        """
        # 构建data URL格式
        data_url = f"data:{media_type};base64,{data}"
        return cls(base64_data=data_url, detail=detail)
    
    @classmethod
    def from_file(cls, file_path: Union[str, Path], detail: str = "auto") -> "ImageContent":
        """
        从本地文件创建图像内容
        
        Args:
            file_path: 本地文件路径
            detail: 图像细节级别
            
        Returns:
            ImageContent实例
            
        Raises:
            FileNotFoundError: 文件不存在时抛出
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"图像文件不存在: {path}")
        
        # 确定媒体类型
        suffix = path.suffix.lower()
        media_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = media_types.get(suffix, "image/png")
        
        # 读取并编码文件
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        
        return cls.from_base64(data, media_type, detail)
    
    def to_openai_format(self) -> dict[str, Any]:
        """
        转换为OpenAI API格式
        
        Returns:
            OpenAI格式的图像内容字典
        """
        if self.url:
            return {
                "type": "image_url",
                "image_url": {
                    "url": self.url,
                    "detail": self.detail,
                },
            }
        elif self.base64_data:
            return {
                "type": "image_url",
                "image_url": {
                    "url": self.base64_data,
                    "detail": self.detail,
                },
            }
        else:
            raise ValueError("ImageContent必须包含url或base64_data")


@dataclass
class MessageContent:
    """
    消息内容数据类
    
    支持文本和图像混合内容。
    """
    
    text: Optional[str] = None
    """文本内容"""
    
    images: list[ImageContent] = field(default_factory=list)
    """图像内容列表"""
    
    def to_openai_format(self) -> Union[str, list[dict[str, Any]]]:
        """
        转换为OpenAI API格式
        
        Returns:
            纯文本返回字符串，包含图像返回内容列表
        """
        if not self.images:
            return self.text or ""
        
        content = []
        
        # 添加图像
        for image in self.images:
            content.append(image.to_openai_format())
        
        # 添加文本
        if self.text:
            content.append({"type": "text", "text": self.text})
        
        return content


@dataclass
class ChatMessage:
    """
    聊天消息数据类
    """
    
    role: MessageRole
    """消息角色"""
    
    content: MessageContent
    """消息内容"""
    
    def to_openai_format(self) -> dict[str, Any]:
        """
        转换为OpenAI API格式
        
        Returns:
            OpenAI格式的消息字典
        """
        return {
            "role": self.role.value,
            "content": self.content.to_openai_format(),
        }


@dataclass
class VLMRequest:
    """
    VLM请求数据类
    
    封装完整的VLM请求参数。
    """
    
    messages: list[ChatMessage]
    """消息列表"""
    
    model: str = "qwen3-vl-plus"
    """模型名称"""
    
    max_tokens: int = 2048
    """最大输出token数"""
    
    temperature: float = 0.7
    """生成温度"""
    
    top_p: float = 0.95
    """Top-p采样参数"""
    
    stream: bool = False
    """是否流式输出"""
    
    def to_openai_format(self) -> dict[str, Any]:
        """
        转换为OpenAI API格式
        
        Returns:
            OpenAI格式的请求字典
        """
        return {
            "model": self.model,
            "messages": [msg.to_openai_format() for msg in self.messages],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "stream": self.stream,
        }
    
    @classmethod
    def create_image_analysis_request(
        cls,
        image: ImageContent,
        prompt: str,
        model: str = "qwen3-vl-plus",
        system_prompt: Optional[str] = None,
    ) -> "VLMRequest":
        """
        创建图像分析请求的便捷方法
        
        Args:
            image: 图像内容
            prompt: 分析提示词
            model: 模型名称
            system_prompt: 系统提示词（可选）
            
        Returns:
            VLMRequest实例
        """
        messages = []
        
        if system_prompt:
            messages.append(ChatMessage(
                role=MessageRole.SYSTEM,
                content=MessageContent(text=system_prompt),
            ))
        
        messages.append(ChatMessage(
            role=MessageRole.USER,
            content=MessageContent(text=prompt, images=[image]),
        ))
        
        return cls(messages=messages, model=model)
