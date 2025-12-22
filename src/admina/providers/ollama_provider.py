"""
Ollama本地服务器提供商实现

通过Ollama本地服务调用VLM/LLM模型。
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

# Ollama默认配置
DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODEL = "llava"  # 默认VLM模型


class OllamaProvider(BaseVLMProvider):
    """
    Ollama本地服务提供商
    
    通过Ollama本地服务调用VLM/LLM模型。
    
    支持的VLM模型（需要预先下载）:
    - llava: LLaVA视觉模型
    - bakllava: BakLLaVA视觉模型
    - llava-llama3: 基于Llama3的LLaVA
    
    支持的LLM模型:
    - llama3: Llama 3模型
    - qwen2: 通义千问2
    - mistral: Mistral模型
    
    Example:
        provider = OllamaProvider()
        result = await provider.analyze_image(
            image=Path("screenshot.png"),
            prompt="描述这张截图中的内容"
        )
    """
    
    def __init__(
        self,
        *,
        host: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        timeout_seconds: int = 120,
        max_retries: int = 3,
    ) -> None:
        """
        初始化Ollama提供商
        
        Args:
            host: Ollama服务地址，默认从环境变量OLLAMA_HOST获取
            model: 默认模型名称
            timeout_seconds: 请求超时时间（秒）
            max_retries: 最大重试次数
        """
        super().__init__(
            base_url=host or os.getenv("OLLAMA_HOST", DEFAULT_HOST),
            model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        
        self._client: Optional[Any] = None
        self._capabilities = VLMCapabilities(
            supports_vision=True,
            supports_video=False,
            supports_streaming=True,
            supports_multi_image=True,
            max_image_size_mb=100.0,  # 本地模型限制较少
            max_tokens=4096,
            supported_image_formats=["png", "jpg", "jpeg", "webp"],
            provider_type=ProviderType.LOCAL,
        )
    
    @property
    def name(self) -> str:
        """获取提供商名称"""
        return "ollama"
    
    @property
    def capabilities(self) -> VLMCapabilities:
        """获取提供商能力"""
        return self._capabilities
    
    @property
    def host(self) -> str:
        """获取Ollama服务地址"""
        return self._base_url or DEFAULT_HOST
    
    def _get_client(self) -> Any:
        """
        获取Ollama客户端实例
        
        Returns:
            Ollama客户端模块
            
        Raises:
            VLMConnectionError: 无法导入ollama库时抛出
        """
        if self._client is None:
            try:
                import ollama
                self._client = ollama
                
                # 设置host（如果不是默认值）
                if self._base_url and self._base_url != DEFAULT_HOST:
                    # ollama库通过环境变量或Client类设置host
                    os.environ["OLLAMA_HOST"] = self._base_url
                    
            except ImportError:
                raise VLMConnectionError(
                    "未安装ollama库，请执行: pip install ollama"
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
            image: 图像输入（文件路径、bytes或PIL Image）
            prompt: 分析提示词
            model: 模型名称，默认使用llava
            max_tokens: 最大输出token数（Ollama使用num_predict参数）
            temperature: 生成温度
            
        Returns:
            分析结果字典
            
        Raises:
            VLMProviderError: API调用失败时抛出
        """
        try:
            client = self._get_client()
            
            # 准备图像数据
            images = self._prepare_images_for_ollama(image)
            
            start_time = time.time()
            
            # Ollama使用chat API进行VLM调用
            response = client.chat(
                model=self._get_model(model),
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                        "images": images,
                    }
                ],
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens or 2048,
                },
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            return {
                "content": response.get("message", {}).get("content", ""),
                "model": response.get("model", self._get_model(model)),
                "usage": {
                    "prompt_tokens": response.get("prompt_eval_count", 0),
                    "completion_tokens": response.get("eval_count", 0),
                    "total_tokens": (
                        response.get("prompt_eval_count", 0) +
                        response.get("eval_count", 0)
                    ),
                },
                "finish_reason": "stop",
                "latency_ms": latency_ms,
                "eval_duration_ms": response.get("eval_duration", 0) / 1e6,
            }
            
        except Exception as e:
            logger.error(f"Ollama分析失败: {e}")
            raise VLMProviderError(f"Ollama API调用失败: {e}") from e
    
    def _prepare_images_for_ollama(
        self,
        image: Union[Path, str, bytes, "Image.Image"],
    ) -> list[str]:
        """
        准备Ollama格式的图像数据
        
        Ollama接受文件路径或Base64字符串。
        
        Args:
            image: 图像输入
            
        Returns:
            图像路径或Base64字符串列表
        """
        if isinstance(image, Path):
            return [str(image.absolute())]
        elif isinstance(image, str):
            # 判断是路径还是Base64
            path = Path(image)
            if path.exists():
                return [str(path.absolute())]
            else:
                # 假设是Base64字符串
                return [image]
        elif isinstance(image, bytes):
            import base64
            return [base64.b64encode(image).decode("utf-8")]
        else:
            # PIL Image，转换为Base64
            import base64
            import io
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return [base64.b64encode(buffer.getvalue()).decode("utf-8")]
    
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
            
            response = client.chat(
                model=self._get_model(model),
                messages=messages,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens or 2048,
                },
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            return {
                "content": response.get("message", {}).get("content", ""),
                "model": response.get("model", self._get_model(model)),
                "usage": {
                    "prompt_tokens": response.get("prompt_eval_count", 0),
                    "completion_tokens": response.get("eval_count", 0),
                    "total_tokens": (
                        response.get("prompt_eval_count", 0) +
                        response.get("eval_count", 0)
                    ),
                },
                "finish_reason": "stop",
                "latency_ms": latency_ms,
            }
            
        except Exception as e:
            logger.error(f"Ollama对话失败: {e}")
            raise VLMProviderError(f"Ollama API调用失败: {e}") from e
    
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
            client: Ollama客户端
            messages: 消息列表
            model: 模型名称
            max_tokens: 最大token数
            temperature: 温度
            
        Yields:
            响应chunk字典
        """
        try:
            stream = client.chat(
                model=self._get_model(model),
                messages=messages,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens or 2048,
                },
                stream=True,
            )
            
            for chunk in stream:
                message = chunk.get("message", {})
                yield {
                    "content": message.get("content", ""),
                    "model": chunk.get("model", self._get_model(model)),
                    "done": chunk.get("done", False),
                }
                    
        except Exception as e:
            logger.error(f"Ollama流式输出失败: {e}")
            raise VLMProviderError(f"Ollama流式调用失败: {e}") from e
    
    async def health_check(self) -> HealthCheckResult:
        """
        执行健康检查
        
        检查Ollama服务是否运行并列出可用模型。
        
        Returns:
            HealthCheckResult对象
        """
        try:
            start_time = time.time()
            models = await self.list_models()
            latency_ms = (time.time() - start_time) * 1000
            
            if not models:
                return HealthCheckResult(
                    is_healthy=True,
                    message="Ollama服务正常，但未下载任何模型",
                    latency_ms=latency_ms,
                    available_models=[],
                )
            
            return HealthCheckResult(
                is_healthy=True,
                message=f"Ollama服务正常，已下载{len(models)}个模型",
                latency_ms=latency_ms,
                available_models=models,
            )
            
        except Exception as e:
            logger.warning(f"Ollama健康检查失败: {e}")
            return HealthCheckResult(
                is_healthy=False,
                message=f"Ollama服务不可用: {e}",
            )
    
    async def list_models(self) -> list[str]:
        """
        列出已下载的模型
        
        Returns:
            模型名称列表
        """
        try:
            client = self._get_client()
            response = client.list()
            
            models = []
            for model_info in response.get("models", []):
                name = model_info.get("name", "")
                if name:
                    models.append(name)
            
            return models
            
        except Exception as e:
            logger.warning(f"列出Ollama模型失败: {e}")
            return []
    
    async def pull_model(self, model_name: str) -> bool:
        """
        下载指定模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            是否下载成功
        """
        try:
            client = self._get_client()
            client.pull(model_name)
            logger.info(f"成功下载模型: {model_name}")
            return True
        except Exception as e:
            logger.error(f"下载模型失败: {e}")
            return False
    
    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        has_image: bool = False,
    ) -> float:
        """
        估算调用成本
        
        本地模型无API成本。
        
        Returns:
            始终返回0
        """
        return 0.0
