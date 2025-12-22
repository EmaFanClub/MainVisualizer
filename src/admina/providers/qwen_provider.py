"""
Qwen VL (DashScope) 提供商实现

通过阿里云DashScope API调用Qwen VL视觉语言模型。
使用OpenAI兼容接口。
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncIterator, Optional, Union

from src.core.exceptions import VLMConnectionError, VLMProviderError
from src.core.interfaces.vlm_provider import (
    HealthCheckResult,
    ProviderType,
    VLMCapabilities,
)

from .base_provider import BaseVLMProvider

if TYPE_CHECKING:
    from PIL import Image

logger = logging.getLogger(__name__)

# Qwen VL默认配置
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3-vl-plus"


class QwenVLProvider(BaseVLMProvider):
    """
    Qwen VL (DashScope) 提供商
    
    通过阿里云DashScope的OpenAI兼容接口调用Qwen VL模型。
    
    支持的模型:
    - qwen3-vl-plus: 通用视觉模型（推荐）
    - qwen-vl-max: 高性能视觉模型
    - qwen-vl-plus: 标准视觉模型
    
    Example:
        provider = QwenVLProvider()
        result = await provider.analyze_image(
            image=Path("screenshot.png"),
            prompt="描述这张截图中的内容"
        )
    """
    
    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        timeout_seconds: int = 60,
        max_retries: int = 3,
    ) -> None:
        """
        初始化Qwen VL提供商
        
        Args:
            api_key: DashScope API密钥，默认从环境变量DASHSCOPE_API_KEY获取
            base_url: API基础URL，默认使用DashScope标准地址
            model: 默认模型名称
            timeout_seconds: 请求超时时间（秒）
            max_retries: 最大重试次数
        """
        super().__init__(
            api_key=api_key or os.getenv("DASHSCOPE_API_KEY"),
            base_url=base_url or DEFAULT_BASE_URL,
            model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        
        self._client: Optional[Any] = None
        self._capabilities = VLMCapabilities(
            supports_vision=True,
            supports_video=True,
            supports_streaming=True,
            supports_multi_image=True,
            max_image_size_mb=20.0,
            max_tokens=8192,
            supported_image_formats=["png", "jpg", "jpeg", "webp", "gif"],
            provider_type=ProviderType.CLOUD,
        )
    
    @property
    def name(self) -> str:
        """获取提供商名称"""
        return "qwen"
    
    @property
    def capabilities(self) -> VLMCapabilities:
        """获取提供商能力"""
        return self._capabilities
    
    def _get_client(self) -> Any:
        """
        获取OpenAI客户端实例
        
        Returns:
            OpenAI客户端
            
        Raises:
            VLMConnectionError: 无法创建客户端时抛出
        """
        if self._client is None:
            try:
                from openai import OpenAI
                
                if not self._api_key:
                    raise VLMConnectionError(
                        "未配置DashScope API密钥，"
                        "请设置环境变量DASHSCOPE_API_KEY或在初始化时传入api_key"
                    )
                
                self._client = OpenAI(
                    api_key=self._api_key,
                    base_url=self._base_url,
                    timeout=self._timeout_seconds,
                )
            except ImportError:
                raise VLMConnectionError(
                    "未安装openai库，请执行: pip install openai"
                )
        
        return self._client
    
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
            image: 图像输入（文件路径、URL、bytes或PIL Image）
            prompt: 分析提示词
            model: 模型名称，默认使用qwen3-vl-plus
            max_tokens: 最大输出token数
            temperature: 生成温度
            
        Returns:
            分析结果字典
            
        Raises:
            VLMProviderError: API调用失败时抛出
        """
        try:
            client = self._get_client()
            image_url = self._build_image_url(image)
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ]
            
            start_time = time.time()
            response = client.chat.completions.create(
                model=self._get_model(model),
                messages=messages,
                max_tokens=max_tokens or 2048,
                temperature=temperature,
            )
            latency_ms = (time.time() - start_time) * 1000
            
            choice = response.choices[0] if response.choices else None
            content = choice.message.content if choice else ""
            
            return {
                "content": content or "",
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                "finish_reason": choice.finish_reason if choice else "stop",
                "response_id": response.id,
                "latency_ms": latency_ms,
            }
            
        except Exception as e:
            logger.error(f"Qwen VL分析失败: {e}")
            raise VLMProviderError(f"Qwen VL API调用失败: {e}") from e
    
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
            messages: 消息列表
            model: 模型名称
            max_tokens: 最大输出token数
            temperature: 生成温度
            stream: 是否流式输出
            
        Returns:
            非流式返回响应字典，流式返回异步迭代器
        """
        try:
            client = self._get_client()
            
            if stream:
                return self._stream_chat(
                    client, messages, model, max_tokens, temperature
                )
            
            start_time = time.time()
            response = client.chat.completions.create(
                model=self._get_model(model),
                messages=messages,
                max_tokens=max_tokens or 2048,
                temperature=temperature,
                stream=False,
            )
            latency_ms = (time.time() - start_time) * 1000
            
            choice = response.choices[0] if response.choices else None
            content = choice.message.content if choice else ""
            
            return {
                "content": content or "",
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                "finish_reason": choice.finish_reason if choice else "stop",
                "response_id": response.id,
                "latency_ms": latency_ms,
            }
            
        except Exception as e:
            logger.error(f"Qwen VL对话失败: {e}")
            raise VLMProviderError(f"Qwen VL API调用失败: {e}") from e
    
    async def _stream_chat(
        self,
        client: Any,
        messages: list[dict[str, Any]],
        model: Optional[str],
        max_tokens: Optional[int],
        temperature: float,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        流式对话内部实现
        
        Args:
            client: OpenAI客户端
            messages: 消息列表
            model: 模型名称
            max_tokens: 最大token数
            temperature: 温度
            
        Yields:
            响应chunk字典
        """
        try:
            stream = client.chat.completions.create(
                model=self._get_model(model),
                messages=messages,
                max_tokens=max_tokens or 2048,
                temperature=temperature,
                stream=True,
            )
            
            for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    content = delta.content if delta else ""
                    yield {
                        "content": content or "",
                        "model": chunk.model,
                        "finish_reason": chunk.choices[0].finish_reason,
                    }
                    
        except Exception as e:
            logger.error(f"Qwen VL流式输出失败: {e}")
            raise VLMProviderError(f"Qwen VL流式调用失败: {e}") from e
    
    async def health_check(self) -> HealthCheckResult:
        """
        执行健康检查
        
        通过发送简单请求验证API可用性。
        
        Returns:
            HealthCheckResult对象
        """
        try:
            start_time = time.time()
            client = self._get_client()
            
            # 发送简单的文本请求测试连接
            response = client.chat.completions.create(
                model=self._get_model(None),
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                is_healthy=True,
                message="Qwen VL服务正常",
                latency_ms=latency_ms,
                available_models=[self._default_model],
            )
            
        except Exception as e:
            logger.warning(f"Qwen VL健康检查失败: {e}")
            return HealthCheckResult(
                is_healthy=False,
                message=f"Qwen VL服务不可用: {e}",
            )
    
    async def list_models(self) -> list[str]:
        """
        列出可用的Qwen VL模型
        
        Returns:
            模型名称列表
        """
        # DashScope不提供模型列表API，返回已知模型
        return [
            "qwen3-vl-plus",
            "qwen-vl-max",
            "qwen-vl-plus",
            "qwen-vl-max-0809",
            "qwen-vl-plus-0809",
        ]
    
    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        has_image: bool = False,
    ) -> float:
        """
        估算调用成本（人民币）
        
        基于DashScope定价估算，实际价格请参考官方文档。
        
        Args:
            input_tokens: 输入token数
            output_tokens: 输出token数
            has_image: 是否包含图像
            
        Returns:
            估算成本（CNY）
        """
        # qwen3-vl-plus参考价格（每1000 tokens）
        input_price = 0.003   # 输入 0.003元/千tokens
        output_price = 0.006  # 输出 0.006元/千tokens
        
        cost = (input_tokens / 1000) * input_price
        cost += (output_tokens / 1000) * output_price
        
        return cost
