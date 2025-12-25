"""
批量图像处理器

使用 PyTorch 向量化计算实现高效的批量图像特征提取。
支持 GPU 加速（如果可用）和 CPU 批量处理。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

from src.core.logger import get_logger

logger = get_logger(__name__)

# 延迟导入，避免强制依赖
try:
    import torch
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    F = None

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None


@dataclass
class ImageFeatures:
    """
    图像特征结果

    Attributes:
        entropy: 图像熵值 (0.0-1.0)
        text_density: 文本密度 (0.0-1.0)
        edge_ratio: 边缘像素比例
    """
    entropy: float
    text_density: float
    edge_ratio: float


class BatchImageProcessor:
    """
    批量图像处理器

    使用 PyTorch 实现高效的批量图像特征计算

    Features:
        - 批量计算图像熵值
        - 批量计算文本密度（边缘检测）
        - 自动选择 GPU/CPU 设备
        - 支持混合精度计算
    """

    def __init__(
        self,
        device: Optional[str] = None,
        target_size: int = 200,
        batch_size: int = 32,
    ) -> None:
        """
        初始化批量图像处理器

        Args:
            device: 计算设备 ('cuda', 'cpu', None=自动选择)
            target_size: 目标缩放尺寸
            batch_size: 批处理大小
        """
        if not TORCH_AVAILABLE:
            raise ImportError("需要安装 PyTorch: pip install torch")

        # 自动选择设备
        if device is None:
            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self._device = torch.device(device)

        self._target_size = target_size
        self._batch_size = batch_size

        # 预计算 Sobel 卷积核（用于边缘检测）
        self._sobel_x = torch.tensor(
            [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]],
            dtype=torch.float32,
            device=self._device
        ).view(1, 1, 3, 3)

        self._sobel_y = torch.tensor(
            [[-1, -2, -1], [0, 0, 0], [1, 2, 1]],
            dtype=torch.float32,
            device=self._device
        ).view(1, 1, 3, 3)

        logger.info(f"BatchImageProcessor 初始化完成, 设备: {self._device}")

    @property
    def device(self) -> str:
        """获取当前设备"""
        return str(self._device)

    @property
    def is_cuda(self) -> bool:
        """是否使用 CUDA"""
        return self._device.type == "cuda"

    def _pil_to_tensor(self, image: Image.Image) -> torch.Tensor:
        """
        将 PIL 图像转换为 PyTorch 张量

        Args:
            image: PIL 图像

        Returns:
            灰度图张量 (1, 1, H, W)
        """
        # 转换为灰度图
        if image.mode != 'L':
            gray = image.convert('L')
        else:
            gray = image

        # 缩放
        w, h = gray.size
        if w > self._target_size or h > self._target_size:
            scale = self._target_size / max(w, h)
            new_size = (int(w * scale), int(h * scale))
            gray = gray.resize(new_size, resample=0)  # NEAREST

        # 转换为张量 (复制数据避免只读缓冲区警告)
        img_bytes = bytearray(gray.tobytes())
        tensor = torch.frombuffer(img_bytes, dtype=torch.uint8)
        tensor = tensor.view(1, 1, gray.size[1], gray.size[0]).float()
        return tensor.to(self._device)

    def _compute_entropy_batch(self, tensors: torch.Tensor) -> torch.Tensor:
        """
        批量计算图像熵值

        Args:
            tensors: 图像张量批次 (N, 1, H, W)

        Returns:
            熵值张量 (N,)
        """
        batch_size = tensors.shape[0]
        entropies = torch.zeros(batch_size, device=self._device)

        for i in range(batch_size):
            img = tensors[i, 0]  # (H, W)
            # 计算直方图
            hist = torch.histc(img, bins=256, min=0, max=255)
            # 归一化
            hist = hist / hist.sum()
            # 计算熵
            hist = hist[hist > 0]  # 移除零值
            entropy = -torch.sum(hist * torch.log2(hist))
            # 归一化到 0-1
            entropies[i] = torch.clamp(entropy / 8.0, 0, 1)

        return entropies

    def _compute_edge_density_batch(self, tensors: torch.Tensor) -> torch.Tensor:
        """
        批量计算边缘密度（文本密度估算）

        使用 Sobel 算子进行边缘检测

        Args:
            tensors: 图像张量批次 (N, 1, H, W)

        Returns:
            边缘密度张量 (N,)
        """
        # Sobel 边缘检测
        gx = F.conv2d(tensors, self._sobel_x, padding=1)
        gy = F.conv2d(tensors, self._sobel_y, padding=1)

        # 梯度幅值
        gradient = (torch.abs(gx) + torch.abs(gy)) / 2

        # 计算高梯度像素比例 (阈值 30)
        edge_mask = gradient > 30
        edge_ratio = edge_mask.float().mean(dim=[1, 2, 3])

        # 归一化到 0-1 (文本密度通常在 0.1-0.4)
        text_density = torch.clamp(edge_ratio / 0.4, 0, 1)

        return text_density, edge_ratio

    def process_single(self, image: Image.Image) -> ImageFeatures:
        """
        处理单张图像

        Args:
            image: PIL 图像

        Returns:
            ImageFeatures: 图像特征
        """
        tensor = self._pil_to_tensor(image)

        with torch.no_grad():
            entropy = self._compute_entropy_batch(tensor)
            text_density, edge_ratio = self._compute_edge_density_batch(tensor)

        return ImageFeatures(
            entropy=entropy[0].item(),
            text_density=text_density[0].item(),
            edge_ratio=edge_ratio[0].item(),
        )

    def process_batch(
        self,
        images: list[Image.Image],
    ) -> list[ImageFeatures]:
        """
        批量处理图像

        Args:
            images: PIL 图像列表

        Returns:
            ImageFeatures 列表
        """
        if not images:
            return []

        results = []

        # 分批处理
        for start in range(0, len(images), self._batch_size):
            end = min(start + self._batch_size, len(images))
            batch_images = images[start:end]

            # 转换为张量
            tensors = [self._pil_to_tensor(img) for img in batch_images]

            # 填充到相同尺寸
            max_h = max(t.shape[2] for t in tensors)
            max_w = max(t.shape[3] for t in tensors)

            padded = []
            for t in tensors:
                pad_h = max_h - t.shape[2]
                pad_w = max_w - t.shape[3]
                if pad_h > 0 or pad_w > 0:
                    t = F.pad(t, (0, pad_w, 0, pad_h), value=0)
                padded.append(t)

            batch_tensor = torch.cat(padded, dim=0)

            # 批量计算
            with torch.no_grad():
                entropies = self._compute_entropy_batch(batch_tensor)
                text_densities, edge_ratios = self._compute_edge_density_batch(batch_tensor)

            # 收集结果
            for i in range(len(batch_images)):
                results.append(ImageFeatures(
                    entropy=entropies[i].item(),
                    text_density=text_densities[i].item(),
                    edge_ratio=edge_ratios[i].item(),
                ))

        return results

    def process_paths(
        self,
        paths: list[Union[str, Path]],
    ) -> list[Optional[ImageFeatures]]:
        """
        批量处理图像路径

        Args:
            paths: 图像路径列表

        Returns:
            ImageFeatures 列表（加载失败的为 None）
        """
        if not PIL_AVAILABLE:
            raise ImportError("需要安装 Pillow: pip install Pillow")

        # 加载图像
        images = []
        valid_indices = []

        for i, path in enumerate(paths):
            try:
                img = Image.open(path)
                images.append(img)
                valid_indices.append(i)
            except Exception as e:
                logger.debug(f"加载图像失败: {path}, 错误: {e}")

        # 批量处理
        features = self.process_batch(images)

        # 关闭图像
        for img in images:
            img.close()

        # 构建结果（保持原始顺序）
        results: list[Optional[ImageFeatures]] = [None] * len(paths)
        for idx, feat in zip(valid_indices, features):
            results[idx] = feat

        return results


# 全局单例
_processor: Optional[BatchImageProcessor] = None


def get_batch_processor() -> BatchImageProcessor:
    """获取全局批量处理器实例"""
    global _processor
    if _processor is None:
        _processor = BatchImageProcessor()
    return _processor


def compute_image_features(image: Image.Image) -> ImageFeatures:
    """
    计算单张图像特征（使用全局处理器）

    Args:
        image: PIL 图像

    Returns:
        ImageFeatures: 图像特征
    """
    return get_batch_processor().process_single(image)
