"""
ManicTime 数据源模块

提供ManicTime数据的读取和解析功能，包括：
- 数据库连接器: 读取SQLite数据库中的活动记录
- 截图加载器: 加载和管理截图文件
- 活动解析器: 将原始数据转换为统一格式

公开接口:
- ManicTimeDBConnector: 数据库连接器
- ScreenshotLoader: 截图加载器
- ActivityParser: 活动解析器
- 数据模型类

Example:
    from src.ingest.manictime import ManicTimeDBConnector, ScreenshotLoader
    
    # 读取数据库
    with ManicTimeDBConnector(db_path) as connector:
        activities = connector.query_activities(start, end)
    
    # 加载截图
    loader = ScreenshotLoader(screenshots_path)
    image = loader.load_by_timestamp(timestamp)
"""

from .activity_parser import ActivityParser
from .db_connector import ManicTimeDBConnector
from .models import (
    ActivityEvent,
    ActivityType,
    ApplicationInfo,
    DaySummary,
    RawActivity,
    ScreenshotMetadata,
)
from .screenshot_loader import ScreenshotLoader

__all__ = [
    # 核心类
    "ManicTimeDBConnector",
    "ScreenshotLoader",
    "ActivityParser",
    # 数据模型
    "RawActivity",
    "ActivityEvent",
    "ApplicationInfo",
    "ScreenshotMetadata",
    "DaySummary",
    "ActivityType",
]
