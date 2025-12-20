"""
数据源接口定义

定义数据摄入层的抽象接口，支持多种数据源实现。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Iterator, List, Optional

if TYPE_CHECKING:
    from PIL import Image


class IActivityDataSource(ABC):
    """
    活动数据源抽象接口
    
    定义从各种来源读取活动数据的标准接口。
    所有数据源实现（如ManicTime、ActivityWatch等）都应实现此接口。
    """
    
    @abstractmethod
    def connect(self) -> None:
        """
        建立与数据源的连接
        
        Raises:
            DatabaseConnectionError: 连接失败时抛出
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """
        断开与数据源的连接
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """
        检查是否已连接
        
        Returns:
            True表示已连接，False表示未连接
        """
        pass
    
    @abstractmethod
    def query_activities(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> List[dict]:
        """
        查询指定时间范围的活动记录
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            活动记录列表，每条记录为字典格式
            
        Raises:
            DatabaseQueryError: 查询失败时抛出
        """
        pass
    
    @abstractmethod
    def query_applications(self) -> List[dict]:
        """
        查询所有应用/窗口信息
        
        Returns:
            应用信息列表
        """
        pass
    
    @abstractmethod
    def query_day_summary(self, target_date: date) -> dict:
        """
        查询指定日期的汇总数据
        
        Args:
            target_date: 目标日期
            
        Returns:
            日汇总数据字典
        """
        pass
    
    @abstractmethod
    def get_last_sync_time(self) -> Optional[datetime]:
        """
        获取上次同步时间点
        
        Returns:
            上次同步的时间戳，如果从未同步则返回None
        """
        pass


class IScreenshotLoader(ABC):
    """
    截图加载器抽象接口
    
    定义加载和处理截图的标准接口。
    """
    
    @abstractmethod
    def load_by_timestamp(
        self,
        timestamp: datetime,
        tolerance_seconds: int = 30,
    ) -> Optional["Image.Image"]:
        """
        按时间戳加载截图
        
        Args:
            timestamp: 目标时间戳
            tolerance_seconds: 时间容差（秒），在此范围内查找最近的截图
            
        Returns:
            PIL Image对象，如果未找到则返回None
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
