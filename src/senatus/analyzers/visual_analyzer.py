"""
视觉敏感度分析器

评估截图的视觉复杂度和敏感度，基于图像特征进行分析。
权重: 0.35 (最高权重分析器)

优化策略:
- 支持 PyTorch 批量处理器加速 (BatchImageProcessor)
- 回退到纯 Python 实现 (当 PyTorch 不可用时)
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional

from .base_analyzer import BaseAnalyzer, AnalyzerResult

if TYPE_CHECKING:
    from PIL import Image
    from src.ingest.manictime.models import ActivityEvent

# 尝试导入批量处理器
_BATCH_PROCESSOR_AVAILABLE = False
_batch_processor = None

try:
    from src.senatus.batch_image_processor import (
        get_batch_processor,
        TORCH_AVAILABLE,
    )
    if TORCH_AVAILABLE:
        _BATCH_PROCESSOR_AVAILABLE = True
except ImportError:
    pass


# 应用类型敏感度权重
APP_TYPE_SENSITIVITY = {
    # 高敏感度应用 (0.7-0.9)
    "high": {
        "patterns": [
            "chrome", "firefox", "edge", "brave", "opera",  # 浏览器
            "telegram", "discord", "wechat", "qq", "whatsapp",  # 即时通讯
            "outlook", "thunderbird",  # 邮件客户端
            "paypal", "alipay", "bank",  # 支付/银行
        ],
        "score": 0.8,
    },
    # 中等敏感度应用 (0.4-0.6)
    "medium": {
        "patterns": [
            "word", "excel", "powerpoint", "onenote",  # Office
            "pdf", "acrobat", "foxit",  # 文档阅读
            "teams", "zoom", "slack",  # 协作工具
        ],
        "score": 0.5,
    },
    # 低敏感度应用 (0.1-0.3)
    "low": {
        "patterns": [
            "code", "vscode", "visual studio",  # IDE
            "pycharm", "idea", "webstorm",  # JetBrains
            "terminal", "powershell", "cmd",  # 终端
            "explorer", "finder",  # 文件管理器
            "notepad", "sublime", "vim",  # 文本编辑器
        ],
        "score": 0.2,
    },
}


def _get_image_features_fast(image: "Image.Image") -> tuple[float, float]:
    """
    使用 PyTorch 批量处理器快速获取图像特征

    Args:
        image: PIL 图像对象

    Returns:
        (熵值, 文本密度) 元组
    """
    global _batch_processor
    if _batch_processor is None:
        _batch_processor = get_batch_processor()

    features = _batch_processor.process_single(image)
    return features.entropy, features.text_density


def _compute_image_entropy(image: "Image.Image") -> float:
    """
    计算图像的信息熵

    熵值越高表示图像内容越复杂/多样

    Args:
        image: PIL 图像对象

    Returns:
        归一化的熵值 (0.0-1.0)
    """
    # 转换为灰度图
    if image.mode != 'L':
        gray = image.convert('L')
    else:
        gray = image

    # 计算直方图
    histogram = gray.histogram()
    total_pixels = sum(histogram)

    if total_pixels == 0:
        return 0.0

    # 计算熵
    entropy = 0.0
    for count in histogram:
        if count > 0:
            probability = count / total_pixels
            entropy -= probability * math.log2(probability)

    # 归一化到 0-1 (最大熵为 8 位 = log2(256) = 8)
    max_entropy = 8.0
    normalized_entropy = min(1.0, entropy / max_entropy)

    return normalized_entropy


def _estimate_text_density(image: Image.Image) -> float:
    """
    估算图像中的文本密度

    使用边缘检测的简化方法评估文本区域
    优化版: 使用更小的缩放尺寸和采样策略

    Args:
        image: PIL 图像对象

    Returns:
        归一化的文本密度 (0.0-1.0)
    """
    # 转换为灰度图
    if image.mode != 'L':
        gray = image.convert('L')
    else:
        gray = image

    # 大幅缩放以加快处理 (200px 足以评估文本密度)
    width, height = gray.size
    if width > 200 or height > 200:
        scale = 200 / max(width, height)
        new_size = (int(width * scale), int(height * scale))
        gray = gray.resize(new_size, resample=0)  # NEAREST (最快)

    # 获取像素数据
    pixels = gray.tobytes()  # 比 list(getdata()) 更快
    width, height = gray.size

    edge_count = 0
    total_checks = 0

    # 使用步长 2 采样，减少计算量 4 倍
    step = 2
    for y in range(1, height - 1, step):
        row_offset = y * width
        for x in range(1, width - 1, step):
            idx = row_offset + x

            # 计算水平和垂直梯度
            gx = abs(pixels[idx + 1] - pixels[idx - 1])
            gy = abs(pixels[idx + width] - pixels[idx - width])

            # 梯度幅值
            gradient = (gx + gy) >> 1  # 位运算更快

            # 高梯度表示边缘（文本通常有清晰的边缘）
            if gradient > 30:
                edge_count += 1

            total_checks += 1

    if total_checks == 0:
        return 0.0

    # 边缘密度
    edge_density = edge_count / total_checks

    # 文本密度通常在 0.1-0.4 之间
    # 将其映射到 0-1 范围
    normalized_density = min(1.0, edge_density / 0.4)

    return normalized_density


class VisualAnalyzer(BaseAnalyzer):
    """
    视觉敏感度分析器

    评估截图的视觉复杂度和敏感度

    分析维度:
    1. 图像熵计算 - 评估内容复杂度
    2. 文本密度评估 - 基于边缘检测
    3. 应用类型敏感度 - 预定义权重表

    计算公式:
    score = (app_type * 0.4) + (entropy * 0.3) + (text_density * 0.3)

    Attributes:
        app_sensitivity: 应用敏感度配置
    """

    def __init__(
        self,
        weight: float = 0.35,
        enabled: bool = True,
        custom_app_sensitivity: Optional[dict] = None,
        use_batch_processor: bool = True,
    ) -> None:
        """
        初始化视觉敏感度分析器

        Args:
            weight: 权重
            enabled: 是否启用
            custom_app_sensitivity: 自定义应用敏感度配置
            use_batch_processor: 是否使用 PyTorch 批量处理器加速
        """
        super().__init__(name="visual", weight=weight, enabled=enabled)

        # 设置是否使用批量处理器
        self._use_batch_processor = (
            use_batch_processor and _BATCH_PROCESSOR_AVAILABLE
        )

        # 合并自定义配置
        self._app_sensitivity = dict(APP_TYPE_SENSITIVITY)
        if custom_app_sensitivity:
            for level, config in custom_app_sensitivity.items():
                if level in self._app_sensitivity:
                    self._app_sensitivity[level]["patterns"].extend(
                        config.get("patterns", [])
                    )
                    if "score" in config:
                        self._app_sensitivity[level]["score"] = config["score"]

    def _do_analyze(
        self,
        activity: ActivityEvent,
        screenshot: Optional[Image.Image] = None,
    ) -> AnalyzerResult:
        """
        执行视觉敏感度分析

        Args:
            activity: 活动事件
            screenshot: 关联截图(可选)

        Returns:
            AnalyzerResult: 分析结果
        """
        app_name = activity.application.lower()

        # 分析应用类型敏感度
        app_score, app_level = self._analyze_app_sensitivity(app_name)

        # 如果没有截图，只使用应用类型评分
        if screenshot is None:
            return AnalyzerResult(
                analyzer_name=self.name,
                score=app_score * 0.6,  # 降低置信度
                confidence=0.6,
                reason=f"应用类型敏感度: {app_level}",
                details={
                    "app_score": app_score,
                    "app_level": app_level,
                    "has_screenshot": False,
                },
            )

        # 计算图像特征 (根据配置选择处理器)
        if self._use_batch_processor:
            entropy, text_density = _get_image_features_fast(screenshot)
        else:
            entropy = _compute_image_entropy(screenshot)
            text_density = _estimate_text_density(screenshot)

        # 综合评分
        # 应用类型权重 40%, 熵值权重 30%, 文本密度权重 30%
        final_score = (
            app_score * 0.4 +
            entropy * 0.3 +
            text_density * 0.3
        )

        return AnalyzerResult(
            analyzer_name=self.name,
            score=final_score,
            confidence=0.85,
            reason=self._build_reason(app_level, entropy, text_density),
            details={
                "app_score": app_score,
                "app_level": app_level,
                "entropy": entropy,
                "text_density": text_density,
                "has_screenshot": True,
            },
        )

    def _analyze_app_sensitivity(self, app_name: str) -> tuple[float, str]:
        """
        分析应用敏感度

        Args:
            app_name: 应用名称(已转小写)

        Returns:
            (敏感度分数, 敏感度级别) 元组
        """
        for level, config in self._app_sensitivity.items():
            for pattern in config["patterns"]:
                if pattern in app_name:
                    return config["score"], level

        # 未知应用，给予中等分数
        return 0.4, "unknown"

    def _build_reason(
        self,
        app_level: str,
        entropy: float,
        text_density: float,
    ) -> str:
        """构建分析原因说明"""
        parts = []

        # 应用类型
        level_names = {
            "high": "高敏感度",
            "medium": "中等敏感度",
            "low": "低敏感度",
            "unknown": "未分类",
        }
        parts.append(f"应用: {level_names.get(app_level, app_level)}")

        # 熵值描述
        if entropy > 0.7:
            parts.append("内容复杂")
        elif entropy > 0.4:
            parts.append("内容适中")
        else:
            parts.append("内容简单")

        # 文本密度描述
        if text_density > 0.6:
            parts.append("文本密集")
        elif text_density > 0.3:
            parts.append("有文本")
        else:
            parts.append("图像为主")

        return "; ".join(parts)

    def analyze_image_only(
        self,
        screenshot: "Image.Image",
    ) -> dict:
        """
        仅分析图像特征

        Args:
            screenshot: 截图图像

        Returns:
            包含熵值和文本密度的字典
        """
        if self._use_batch_processor:
            entropy, text_density = _get_image_features_fast(screenshot)
        else:
            entropy = _compute_image_entropy(screenshot)
            text_density = _estimate_text_density(screenshot)

        return {
            "entropy": entropy,
            "text_density": text_density,
            "complexity_score": (entropy + text_density) / 2,
        }

    def add_app_pattern(
        self,
        pattern: str,
        level: str = "medium",
    ) -> None:
        """
        添加应用模式

        Args:
            pattern: 应用名称模式
            level: 敏感度级别 (high/medium/low)
        """
        if level in self._app_sensitivity:
            self._app_sensitivity[level]["patterns"].append(pattern.lower())
