"""
ManicTime 截图加载器

负责从截图目录加载和管理截图文件。
截图文件以只读方式访问，不会修改原始文件。
"""

from __future__ import annotations

import bisect
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator, Optional

from src.core import get_logger
from src.core.exceptions import ScreenshotLoadError, ScreenshotNotFoundError
from src.core.interfaces.data_source import IScreenshotLoader

from .models import ScreenshotMetadata

logger = get_logger(__name__)

# 延迟导入PIL，避免未安装时报错
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None


class ScreenshotLoader(IScreenshotLoader):
    """
    ManicTime 截图加载器
    
    从ManicTime截图目录加载截图，支持按时间戳查找、缩略图加载和批量操作。
    
    Attributes:
        screenshots_path: 截图目录路径
        _screenshot_index: 截图时间索引缓存
        
    Example:
        loader = ScreenshotLoader(Path("screenshots"))
        image = loader.load_by_timestamp(datetime.now())
    """
    
    # 支持的图片格式
    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
    
    def __init__(self, screenshots_path: Path | str) -> None:
        """
        初始化截图加载器

        Args:
            screenshots_path: 截图目录路径
        """
        self.screenshots_path = Path(screenshots_path)
        self._screenshot_index: dict[datetime, ScreenshotMetadata] = {}
        self._sorted_timestamps: list[datetime] = []  # 排序的时间戳列表，用于二分查找
        self._index_built = False
    
    def _ensure_pil_available(self) -> None:
        """确保PIL库可用"""
        if not PIL_AVAILABLE:
            raise ScreenshotLoadError(
                "PIL库未安装，请运行: pip install Pillow"
            )
    
    def _build_index(self) -> None:
        """
        构建截图时间索引
        
        遍历截图目录（包括子目录），解析文件名建立时间戳到文件路径的映射。
        """
        if self._index_built:
            return
        
        if not self.screenshots_path.exists():
            logger.warning(f"截图目录不存在: {self.screenshots_path}")
            self._index_built = True
            return
        
        logger.info(f"正在构建截图索引: {self.screenshots_path}")
        count = 0
        
        # 使用递归glob查找所有图片文件
        for ext in self.SUPPORTED_EXTENSIONS:
            for file_path in self.screenshots_path.rglob(f"*{ext}"):
                if not file_path.is_file():
                    continue
                
                # 跳过缩略图（会在需要时单独处理）
                if ".thumbnail" in file_path.stem:
                    continue
                
                metadata = ScreenshotMetadata.from_filename(file_path)
                if metadata:
                    self._screenshot_index[metadata.timestamp] = metadata
                    count += 1
        
        # 构建排序的时间戳列表，用于二分查找
        self._sorted_timestamps = sorted(self._screenshot_index.keys())
        self._index_built = True
        logger.info(f"截图索引构建完成，共 {count} 张截图")

    def _find_closest_screenshot(
        self,
        timestamp: datetime,
        tolerance_seconds: int,
    ) -> Optional[ScreenshotMetadata]:
        """
        查找最接近指定时间戳的截图

        使用二分查找实现 O(log n) 时间复杂度

        Args:
            timestamp: 目标时间戳
            tolerance_seconds: 时间容差（秒）

        Returns:
            最接近的ScreenshotMetadata，如果在容差范围内没有找到则返回None
        """
        self._build_index()

        if not self._sorted_timestamps:
            return None

        # 使用二分查找定位时间戳位置
        idx = bisect.bisect_left(self._sorted_timestamps, timestamp)
        tolerance = timedelta(seconds=tolerance_seconds)

        # 检查候选位置: idx-1, idx (最多检查2个位置)
        candidates = []
        if idx > 0:
            candidates.append(idx - 1)
        if idx < len(self._sorted_timestamps):
            candidates.append(idx)

        # 在候选位置中找最接近的
        min_diff = timedelta(seconds=tolerance_seconds + 1)
        closest = None

        for i in candidates:
            ts = self._sorted_timestamps[i]
            diff = abs(ts - timestamp)
            if diff < min_diff:
                min_diff = diff
                closest = self._screenshot_index[ts]

        if closest and min_diff <= tolerance:
            return closest
        return None
    
    def find_screenshot_path(
        self,
        timestamp: datetime,
        tolerance_seconds: int = 30,
    ) -> Optional[Path]:
        """
        查找指定时间戳对应的截图路径
        
        Args:
            timestamp: 目标时间戳
            tolerance_seconds: 时间容差（秒）
            
        Returns:
            截图文件路径，如果未找到则返回None
        """
        metadata = self._find_closest_screenshot(timestamp, tolerance_seconds)
        return metadata.file_path if metadata else None
    
    def find_thumbnail_path(
        self,
        timestamp: datetime,
        tolerance_seconds: int = 30,
    ) -> Optional[Path]:
        """
        查找指定时间戳对应的缩略图路径
        
        Args:
            timestamp: 目标时间戳
            tolerance_seconds: 时间容差（秒）
            
        Returns:
            缩略图文件路径，如果未找到则返回None
        """
        full_path = self.find_screenshot_path(timestamp, tolerance_seconds)
        if not full_path:
            return None
        
        # 缩略图命名规则: filename.thumbnail.jpg
        thumbnail_path = full_path.with_suffix(".thumbnail" + full_path.suffix)
        if thumbnail_path.exists():
            return thumbnail_path
        
        # 尝试另一种命名规则: filename.thumbnail.ext
        thumbnail_path2 = full_path.parent / (full_path.stem + ".thumbnail" + full_path.suffix)
        if thumbnail_path2.exists():
            return thumbnail_path2
        
        return None
    
    def load_by_timestamp(
        self,
        timestamp: datetime,
        tolerance_seconds: int = 30,
    ) -> Optional["Image.Image"]:
        """
        按时间戳加载截图
        
        Args:
            timestamp: 目标时间戳
            tolerance_seconds: 时间容差（秒）
            
        Returns:
            PIL Image对象，如果未找到则返回None
        """
        self._ensure_pil_available()
        
        path = self.find_screenshot_path(timestamp, tolerance_seconds)
        if not path:
            logger.debug(f"未找到时间戳 {timestamp} 对应的截图")
            return None
        
        try:
            return Image.open(path)
        except Exception as e:
            logger.error(f"加载截图失败: {path}, 错误: {e}")
            raise ScreenshotLoadError(
                f"无法加载截图: {e}",
                details={"path": str(path)}
            ) from e
    
    def load_thumbnail(
        self,
        timestamp: datetime,
        tolerance_seconds: int = 30,
    ) -> Optional["Image.Image"]:
        """
        按时间戳加载缩略图
        
        Args:
            timestamp: 目标时间戳
            tolerance_seconds: 时间容差（秒）
            
        Returns:
            缩略图Image对象，如果未找到则返回None
        """
        self._ensure_pil_available()
        
        path = self.find_thumbnail_path(timestamp, tolerance_seconds)
        if not path:
            # 尝试加载完整截图作为后备
            full_path = self.find_screenshot_path(timestamp, tolerance_seconds)
            if full_path:
                logger.debug(f"缩略图不存在，使用完整截图: {full_path}")
                path = full_path
            else:
                return None
        
        try:
            return Image.open(path)
        except Exception as e:
            logger.error(f"加载缩略图失败: {path}, 错误: {e}")
            return None
    
    def load_by_path(self, path: Path | str) -> "Image.Image":
        """
        直接通过路径加载截图
        
        Args:
            path: 截图文件路径
            
        Returns:
            PIL Image对象
            
        Raises:
            ScreenshotNotFoundError: 文件不存在
            ScreenshotLoadError: 加载失败
        """
        self._ensure_pil_available()
        
        path = Path(path)
        if not path.exists():
            raise ScreenshotNotFoundError(
                f"截图文件不存在: {path}",
                details={"path": str(path)}
            )
        
        try:
            return Image.open(path)
        except Exception as e:
            raise ScreenshotLoadError(
                f"无法加载截图: {e}",
                details={"path": str(path)}
            ) from e
    
    def iter_screenshots(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> Iterator[tuple[datetime, Path]]:
        """
        迭代指定时间范围内的所有截图
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Yields:
            (时间戳, 文件路径) 元组
        """
        self._build_index()
        
        for ts, metadata in sorted(self._screenshot_index.items()):
            if start_time <= ts <= end_time:
                yield (ts, metadata.file_path)
    
    def get_screenshot_count(self) -> int:
        """获取索引中的截图总数"""
        self._build_index()
        return len(self._screenshot_index)
    
    def get_date_range(self) -> tuple[Optional[datetime], Optional[datetime]]:
        """
        获取截图的时间范围

        Returns:
            (最早时间, 最晚时间) 元组
        """
        self._build_index()

        if not self._sorted_timestamps:
            return (None, None)

        # 直接使用已排序的时间戳列表
        return (self._sorted_timestamps[0], self._sorted_timestamps[-1])
    
    def get_metadata(
        self, 
        timestamp: datetime, 
        tolerance_seconds: int = 30
    ) -> Optional[ScreenshotMetadata]:
        """
        获取指定时间戳的截图元信息
        
        Args:
            timestamp: 目标时间戳
            tolerance_seconds: 时间容差（秒）
            
        Returns:
            ScreenshotMetadata对象，如果未找到则返回None
        """
        return self._find_closest_screenshot(timestamp, tolerance_seconds)
