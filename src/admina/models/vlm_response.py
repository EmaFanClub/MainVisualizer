"""
VLM响应数据模型

定义VLM/LLM响应的数据结构。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4


class ScreenContentType(Enum):
    """屏幕内容类型枚举"""
    
    CODE_EDITING = "code_editing"
    """代码编辑"""
    
    DOCUMENT_WRITING = "document_writing"
    """文档编写"""
    
    BROWSING = "browsing"
    """网页浏览"""
    
    COMMUNICATION = "communication"
    """通讯交流"""
    
    MEDIA = "media"
    """媒体播放"""
    
    TERMINAL = "terminal"
    """终端操作"""
    
    DESIGN = "design"
    """设计工具"""
    
    DATA_ANALYSIS = "data_analysis"
    """数据分析"""
    
    SYSTEM = "system"
    """系统操作"""
    
    OTHER = "other"
    """其他"""


@dataclass
class TokenUsage:
    """
    Token使用量统计
    """
    
    prompt_tokens: int = 0
    """输入token数"""
    
    completion_tokens: int = 0
    """输出token数"""
    
    total_tokens: int = 0
    """总token数"""
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TokenUsage":
        """
        从字典创建TokenUsage
        
        Args:
            data: 包含token使用信息的字典
            
        Returns:
            TokenUsage实例
        """
        return cls(
            prompt_tokens=data.get("prompt_tokens", 0),
            completion_tokens=data.get("completion_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
        )


@dataclass
class VLMResponse:
    """
    VLM响应数据类
    
    封装VLM API的响应结果。
    """
    
    content: str
    """响应内容"""
    
    model: str
    """使用的模型名称"""
    
    usage: TokenUsage = field(default_factory=TokenUsage)
    """Token使用量"""
    
    finish_reason: str = "stop"
    """完成原因: stop, length, content_filter等"""
    
    response_id: str = ""
    """响应ID"""
    
    created_at: datetime = field(default_factory=datetime.now)
    """响应创建时间"""
    
    raw_response: Optional[dict[str, Any]] = None
    """原始响应数据（用于调试）"""
    
    @classmethod
    def from_openai_response(cls, response: Any) -> "VLMResponse":
        """
        从OpenAI格式响应创建VLMResponse
        
        Args:
            response: OpenAI ChatCompletion响应对象
            
        Returns:
            VLMResponse实例
        """
        choice = response.choices[0] if response.choices else None
        content = choice.message.content if choice else ""
        finish_reason = choice.finish_reason if choice else "stop"
        
        usage = TokenUsage(
            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
            completion_tokens=response.usage.completion_tokens if response.usage else 0,
            total_tokens=response.usage.total_tokens if response.usage else 0,
        )
        
        return cls(
            content=content or "",
            model=response.model,
            usage=usage,
            finish_reason=finish_reason or "stop",
            response_id=response.id,
            raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
        )


@dataclass
class AnalysisResult:
    """
    屏幕分析结果数据类
    
    封装VLM对屏幕截图的分析结果。
    """
    
    result_id: UUID = field(default_factory=uuid4)
    """结果唯一ID"""
    
    content_type: ScreenContentType = ScreenContentType.OTHER
    """内容类型"""
    
    specific_activity: str = ""
    """具体活动描述"""
    
    extracted_text: Optional[str] = None
    """提取的关键文本内容"""
    
    entities: list[str] = field(default_factory=list)
    """识别的实体（项目名、文件名等）"""
    
    progress_indicator: Optional[str] = None
    """工作进度指示（如"第3章第2节"）"""
    
    terminal_output: Optional[str] = None
    """终端输出内容（如有）"""
    
    code_context: Optional[str] = None
    """代码上下文（函数名、类名等）"""
    
    error_messages: list[str] = field(default_factory=list)
    """检测到的错误信息"""
    
    confidence: float = 0.0
    """分析置信度（0-1）"""
    
    raw_analysis: str = ""
    """原始分析文本"""
    
    vlm_response: Optional[VLMResponse] = None
    """关联的VLM响应"""
    
    analyzed_at: datetime = field(default_factory=datetime.now)
    """分析时间"""
    
    def to_dict(self) -> dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            结果字典
        """
        return {
            "result_id": str(self.result_id),
            "content_type": self.content_type.value,
            "specific_activity": self.specific_activity,
            "extracted_text": self.extracted_text,
            "entities": self.entities,
            "progress_indicator": self.progress_indicator,
            "terminal_output": self.terminal_output,
            "code_context": self.code_context,
            "error_messages": self.error_messages,
            "confidence": self.confidence,
            "raw_analysis": self.raw_analysis,
            "analyzed_at": self.analyzed_at.isoformat(),
        }
    
    @classmethod
    def from_vlm_response(
        cls,
        response: VLMResponse,
        content_type: ScreenContentType = ScreenContentType.OTHER,
    ) -> "AnalysisResult":
        """
        从VLM响应创建基础分析结果
        
        需要进一步解析response.content以提取结构化信息。
        
        Args:
            response: VLM响应对象
            content_type: 内容类型
            
        Returns:
            AnalysisResult实例
        """
        return cls(
            content_type=content_type,
            raw_analysis=response.content,
            vlm_response=response,
            confidence=0.8,  # 默认置信度
        )
