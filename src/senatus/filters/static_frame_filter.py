"""
静态帧过滤器

使用感知哈希检测静态画面，避免对重复或无变化的截图进行分析。
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from .base_filter import BaseFilter, FilterResult

if TYPE_CHECKING:
    from PIL import Image
    from src.ingest.manictime.models import ActivityEvent


def _compute_average_hash(image: Image.Image, hash_size: int = 8) -> str:
    """
    计算图像的平均哈希 (aHash)

    这是一个简化的感知哈希实现，不依赖 imagehash 库。

    Args:
        image: PIL 图像对象
        hash_size: 哈希大小 (默认 8x8 = 64 位)

    Returns:
        哈希字符串 (十六进制)
    """
    # 缩放到指定大小
    resized = image.resize(
        (hash_size, hash_size),
        resample=getattr(image, 'Resampling', image).LANCZOS
        if hasattr(image, 'Resampling')
        else 1  # PIL.Image.LANCZOS
    )

    # 转换为灰度
    if resized.mode != 'L':
        resized = resized.convert('L')

    # 获取像素值
    pixels = list(resized.getdata())

    # 计算平均值
    avg = sum(pixels) / len(pixels)

    # 生成哈希: 高于平均为 1，否则为 0
    hash_bits = ['1' if p >= avg else '0' for p in pixels]

    # 转换为十六进制字符串
    hash_int = int(''.join(hash_bits), 2)
    return format(hash_int, f'0{hash_size * hash_size // 4}x')


def _compute_difference_hash(image: Image.Image, hash_size: int = 8) -> str:
    """
    计算图像的差异哈希 (dHash)

    比较相邻像素的差异，对渐变更稳定。

    Args:
        image: PIL 图像对象
        hash_size: 哈希大小

    Returns:
        哈希字符串 (十六进制)
    """
    # 缩放到 (hash_size + 1, hash_size) 以便比较相邻像素
    resized = image.resize(
        (hash_size + 1, hash_size),
        resample=getattr(image, 'Resampling', image).LANCZOS
        if hasattr(image, 'Resampling')
        else 1
    )

    # 转换为灰度
    if resized.mode != 'L':
        resized = resized.convert('L')

    # 获取像素值
    pixels = list(resized.getdata())

    # 生成哈希: 比较左右相邻像素
    hash_bits = []
    for row in range(hash_size):
        for col in range(hash_size):
            left_pixel = pixels[row * (hash_size + 1) + col]
            right_pixel = pixels[row * (hash_size + 1) + col + 1]
            hash_bits.append('1' if left_pixel > right_pixel else '0')

    # 转换为十六进制字符串
    hash_int = int(''.join(hash_bits), 2)
    return format(hash_int, f'0{hash_size * hash_size // 4}x')


def _hamming_distance(hash1: str, hash2: str) -> int:
    """
    计算两个哈希的汉明距离

    Args:
        hash1: 第一个哈希字符串
        hash2: 第二个哈希字符串

    Returns:
        汉明距离
    """
    if len(hash1) != len(hash2):
        return max(len(hash1), len(hash2)) * 4  # 返回最大可能距离

    # 转换为整数并计算异或结果中的 1 的数量
    int1 = int(hash1, 16)
    int2 = int(hash2, 16)
    xor_result = int1 ^ int2

    return bin(xor_result).count('1')


@dataclass
class FrameHashRecord:
    """
    帧哈希记录

    Attributes:
        event_id: 活动事件 ID
        timestamp: 时间戳
        ahash: 平均哈希
        dhash: 差异哈希
    """
    event_id: str
    timestamp: datetime
    ahash: str
    dhash: str


class StaticFrameFilter(BaseFilter):
    """
    静态帧检测过滤器

    使用感知哈希检测静态画面，避免重复分析相似截图。

    检测策略:
    1. 计算当前帧的感知哈希
    2. 与历史帧进行比较
    3. 如果与任一历史帧差异小于阈值，则认为是静态帧

    Attributes:
        diff_threshold: 差异阈值 (0.0-1.0)
        history_size: 历史记录大小
        hash_size: 哈希大小
    """

    def __init__(
        self,
        diff_threshold: float = 0.05,
        history_size: int = 5,
        hash_size: int = 8,
        enabled: bool = True,
    ) -> None:
        """
        初始化静态帧过滤器

        Args:
            diff_threshold: 差异阈值，低于此值视为静态帧
            history_size: 保留的历史帧数量
            hash_size: 哈希大小 (hash_size x hash_size 位)
            enabled: 是否启用
        """
        super().__init__(name="static_frame", enabled=enabled)

        self._diff_threshold = max(0.0, min(1.0, diff_threshold))
        self._history_size = max(1, history_size)
        self._hash_size = hash_size

        # 历史哈希记录
        self._history: deque[FrameHashRecord] = deque(maxlen=history_size)

        # 最大汉明距离 (用于归一化)
        self._max_distance = hash_size * hash_size

        # 扩展统计
        self._stats.update({
            "static_frames": 0,
            "unique_frames": 0,
            "no_screenshot": 0,
        })

    def _do_check(self, activity: ActivityEvent) -> FilterResult:
        """
        执行静态帧检查

        注意: 此过滤器需要截图信息，如果活动没有截图路径，将通过检查。

        Args:
            activity: 活动事件

        Returns:
            FilterResult: 过滤结果
        """
        # 检查是否有截图
        if not hasattr(activity, 'screenshot_path') or not activity.screenshot_path:
            self._stats["no_screenshot"] += 1
            return FilterResult.passed(self.name)

        # 尝试从截图路径加载图像并计算哈希
        try:
            from PIL import Image
            screenshot = Image.open(activity.screenshot_path)
            return self._check_with_image(activity, screenshot)
        except Exception:
            # 无法加载截图，通过检查
            self._stats["no_screenshot"] += 1
            return FilterResult.passed(self.name)

    def check_with_image(
        self,
        activity: ActivityEvent,
        screenshot: Image.Image,
    ) -> FilterResult:
        """
        使用提供的图像进行静态帧检查

        Args:
            activity: 活动事件
            screenshot: 截图图像

        Returns:
            FilterResult: 过滤结果
        """
        if not self._enabled:
            return FilterResult.passed(self.name)

        self._stats["total_checked"] += 1
        return self._check_with_image(activity, screenshot)

    def _check_with_image(
        self,
        activity: ActivityEvent,
        screenshot: Image.Image,
    ) -> FilterResult:
        """
        使用图像执行静态帧检查

        Args:
            activity: 活动事件
            screenshot: 截图图像

        Returns:
            FilterResult: 过滤结果
        """
        # 计算当前帧的哈希
        current_ahash = _compute_average_hash(screenshot, self._hash_size)
        current_dhash = _compute_difference_hash(screenshot, self._hash_size)

        # 与历史帧比较
        min_diff = 1.0
        matched_record = None

        for record in self._history:
            # 计算差异 (使用两种哈希的平均)
            ahash_dist = _hamming_distance(current_ahash, record.ahash)
            dhash_dist = _hamming_distance(current_dhash, record.dhash)

            ahash_diff = ahash_dist / self._max_distance
            dhash_diff = dhash_dist / self._max_distance

            # 使用两种哈希的平均差异
            avg_diff = (ahash_diff + dhash_diff) / 2

            if avg_diff < min_diff:
                min_diff = avg_diff
                matched_record = record

        # 添加当前帧到历史
        new_record = FrameHashRecord(
            event_id=str(activity.event_id),
            timestamp=activity.timestamp,
            ahash=current_ahash,
            dhash=current_dhash,
        )
        self._history.append(new_record)

        # 判断是否为静态帧
        if min_diff < self._diff_threshold and matched_record:
            self._stats["static_frames"] += 1
            self._stats["total_skipped"] += 1
            return FilterResult.skipped(
                filter_name=self.name,
                reason=f"静态帧检测: 与历史帧差异 {min_diff:.4f} < {self._diff_threshold}",
                matched_rule=f"static:diff={min_diff:.4f}:ref={matched_record.event_id}",
            )

        self._stats["unique_frames"] += 1
        return FilterResult.passed(self.name)

    def compute_hash(self, screenshot: Image.Image) -> tuple[str, str]:
        """
        计算图像的感知哈希

        Args:
            screenshot: 截图图像

        Returns:
            (ahash, dhash) 元组
        """
        ahash = _compute_average_hash(screenshot, self._hash_size)
        dhash = _compute_difference_hash(screenshot, self._hash_size)
        return ahash, dhash

    def compare_images(
        self,
        image1: Image.Image,
        image2: Image.Image,
    ) -> float:
        """
        比较两张图像的相似度

        Args:
            image1: 第一张图像
            image2: 第二张图像

        Returns:
            差异度 (0.0 = 完全相同, 1.0 = 完全不同)
        """
        ahash1 = _compute_average_hash(image1, self._hash_size)
        dhash1 = _compute_difference_hash(image1, self._hash_size)
        ahash2 = _compute_average_hash(image2, self._hash_size)
        dhash2 = _compute_difference_hash(image2, self._hash_size)

        ahash_dist = _hamming_distance(ahash1, ahash2)
        dhash_dist = _hamming_distance(dhash1, dhash2)

        ahash_diff = ahash_dist / self._max_distance
        dhash_diff = dhash_dist / self._max_distance

        return (ahash_diff + dhash_diff) / 2

    def clear_history(self) -> None:
        """清除历史记录"""
        self._history.clear()

    @property
    def diff_threshold(self) -> float:
        """获取差异阈值"""
        return self._diff_threshold

    @diff_threshold.setter
    def diff_threshold(self, value: float) -> None:
        """设置差异阈值"""
        self._diff_threshold = max(0.0, min(1.0, value))

    @property
    def history_size(self) -> int:
        """获取历史记录大小"""
        return self._history_size

    @property
    def history(self) -> list[FrameHashRecord]:
        """获取历史记录"""
        return list(self._history)

    @property
    def static_frame_rate(self) -> float:
        """
        获取静态帧率

        Returns:
            静态帧占比
        """
        total = self._stats["static_frames"] + self._stats["unique_frames"]
        if total == 0:
            return 0.0
        return self._stats["static_frames"] / total
