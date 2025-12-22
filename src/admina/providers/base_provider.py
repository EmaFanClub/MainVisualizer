"""
VLM提供商基类

提供所有VLM提供商的通用功能和工具方法。
"""

from __future__ import annotations

import base64
import logging
from abc import ABC
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

from src.core.exceptions import VLMProviderError
from src.core.interfaces.vlm_provider import (
    HealthCheckResult,
    IVLMProvider,
    VLMCapabilities,
)

if TYPE_CHECKING:
    from PIL import Image

logger = logging.getLogger(__name__)


class BaseVLMProvider(IVLMProvider, ABC):
    """
    VLM提供商基类
    
    提供通用的工具方法和配置管理。
    子类需要实现具体的API调用逻辑。
    """
    
    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "",
        timeout_seconds: int = 60,
        max_retries: int = 3,
    ) -> None:
        """
        初始化基类
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            model: 默认模型名称
            timeout_seconds: 请求超时时间（秒）
            max_retries: 最大重试次数
        """
        self._api_key = api_key
        self._base_url = base_url
        self._default_model = model
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._capabilities: Optional[VLMCapabilities] = None
    
    @property
    def default_model(self) -> str:
        """获取默认模型名称"""
        return self._default_model
    
    @property
    def timeout_seconds(self) -> int:
        """获取超时时间"""
        return self._timeout_seconds
    
    def _encode_image_to_base64(
        self,
        image: Union[Path, str, bytes, "Image.Image"],
    ) -> tuple[str, str]:
        """
        将图像编码为Base64字符串
        
        Args:
            image: 图像输入，支持多种格式
            
        Returns:
            (base64_data, media_type) 元组
            
        Raises:
            VLMProviderError: 图像编码失败时抛出
        """
        try:
            if isinstance(image, Path):
                return self._encode_file_to_base64(image)
            elif isinstance(image, str):
                # 判断是路径还是URL还是Base64
                if image.startswith(("http://", "https://")):
                    # URL直接返回，不需要编码
                    return image, "url"
                elif image.startswith("data:"):
                    # 已经是data URL格式
                    return image, "data_url"
                else:
                    # 尝试作为文件路径处理
                    path = Path(image)
                    if path.exists():
                        return self._encode_file_to_base64(path)
                    else:
                        # 假设是Base64字符串
                        return image, "image/png"
            elif isinstance(image, bytes):
                return base64.b64encode(image).decode("utf-8"), "image/png"
            else:
                # PIL Image
                import io
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                data = base64.b64encode(buffer.getvalue()).decode("utf-8")
                return data, "image/png"
        except Exception as e:
            raise VLMProviderError(f"图像编码失败: {e}") from e
    
    def _encode_file_to_base64(self, file_path: Path) -> tuple[str, str]:
        """
        将文件编码为Base64
        
        Args:
            file_path: 文件路径
            
        Returns:
            (base64_data, media_type) 元组
        """
        if not file_path.exists():
            raise VLMProviderError(f"图像文件不存在: {file_path}")
        
        # 确定媒体类型
        suffix = file_path.suffix.lower()
        media_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = media_types.get(suffix, "image/png")
        
        with open(file_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        
        return data, media_type
    
    def _build_image_url(
        self,
        image: Union[Path, str, bytes, "Image.Image"],
    ) -> str:
        """
        构建图像URL（支持data URL格式）
        
        Args:
            image: 图像输入
            
        Returns:
            图像URL或data URL
        """
        data, media_type = self._encode_image_to_base64(image)
        
        if media_type == "url":
            return data
        elif media_type == "data_url":
            return data
        else:
            return f"data:{media_type};base64,{data}"
    
    def _get_model(self, model: Optional[str]) -> str:
        """
        获取要使用的模型名称
        
        Args:
            model: 指定的模型名称，为None时使用默认模型
            
        Returns:
            模型名称
        """
        return model or self._default_model
    
    async def list_models(self) -> list[str]:
        """
        列出可用模型
        
        默认实现返回空列表。
        子类应覆盖此方法。
        
        Returns:
            可用模型名称列表
        """
        return []
    
    async def health_check(self) -> HealthCheckResult:
        """
        执行健康检查
        
        默认实现尝试列出模型。
        子类可覆盖此方法提供更精确的检查。
        
        Returns:
            HealthCheckResult对象
        """
        try:
            models = await self.list_models()
            return HealthCheckResult(
                is_healthy=True,
                message="服务正常",
                available_models=models,
            )
        except Exception as e:
            logger.warning(f"健康检查失败: {e}")
            return HealthCheckResult(
                is_healthy=False,
                message=f"服务不可用: {e}",
            )
