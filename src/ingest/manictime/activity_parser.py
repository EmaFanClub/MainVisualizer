"""
ManicTime 活动数据解析器

将ManicTime原始数据解析并转换为系统内部统一格式。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from src.core import get_logger
from src.core.exceptions import ActivityParseError

from .models import (
    ActivityEvent,
    ActivityType,
    ApplicationInfo,
    RawActivity,
    ScreenshotMetadata,
)

logger = get_logger(__name__)


class ActivityParser:
    """
    ManicTime 活动数据解析器
    
    负责将ManicTime数据库中的原始记录转换为系统统一的ActivityEvent格式。
    
    Attributes:
        local_timezone: 本地时区偏移
        
    Example:
        parser = ActivityParser()
        event = parser.parse_from_dict(raw_data)
    """
    
    # 已知的系统进程（将被标记为非活跃）
    SYSTEM_PROCESSES = {
        "explorer.exe",
        "dwm.exe",
        "taskmgr.exe",
        "shellexperiencehost.exe",
        "searchui.exe",
        "startmenuexperiencehost.exe",
        "lockapp.exe",
    }
    
    # 活动状态关键词映射
    ACTIVITY_STATE_KEYWORDS = {
        "active": ActivityType.ACTIVE,
        "away": ActivityType.AWAY,
        "idle": ActivityType.AWAY,
    }
    
    def __init__(self, local_timezone_hours: int = 8) -> None:
        """
        初始化解析器
        
        Args:
            local_timezone_hours: 本地时区偏移（小时），默认+8（北京时间）
        """
        self.local_timezone = timezone(timedelta(hours=local_timezone_hours))
    
    def parse_from_dict(
        self,
        raw_data: dict,
        app_info: Optional[ApplicationInfo] = None,
        screenshot_metadata: Optional[ScreenshotMetadata] = None,
    ) -> ActivityEvent:
        """
        从字典数据解析活动事件
        
        Args:
            raw_data: 原始数据字典（来自数据库查询）
            app_info: 可选的应用信息
            screenshot_metadata: 可选的截图元信息
            
        Returns:
            ActivityEvent对象
            
        Raises:
            ActivityParseError: 解析失败时抛出
        """
        try:
            # 解析时间和持续时间
            start_time, duration = self._parse_time_info(raw_data)
            
            # 提取应用信息
            application, window_title = self._extract_app_info(raw_data, app_info)
            
            # 判断活动类型和状态
            activity_type = self._determine_activity_type(
                raw_data.get("group_key", ""),
                application.lower(),
            )
            is_active = self._determine_is_active(activity_type, application)
            
            # 转换为本地时间
            local_timestamp = start_time.replace(tzinfo=timezone.utc).astimezone(
                self.local_timezone
            )
            
            # 构建ActivityEvent
            event = self._build_event(
                local_timestamp, duration, application, 
                window_title, is_active, activity_type, raw_data
            )
            
            # 添加截图信息
            if screenshot_metadata:
                event = self.enrich_with_screenshot(event, screenshot_metadata)
            
            return event
            
        except ActivityParseError:
            raise
        except Exception as e:
            raise ActivityParseError(
                f"解析活动数据失败: {e}",
                details={"raw_data": raw_data, "error": str(e)}
            ) from e
    
    def _parse_time_info(self, raw_data: dict) -> tuple[datetime, int]:
        """
        解析时间信息
        
        Args:
            raw_data: 原始数据字典
            
        Returns:
            (开始时间, 持续秒数) 元组
            
        Raises:
            ActivityParseError: 缺少开始时间时抛出
        """
        start_time = self._parse_datetime(raw_data.get("start_utc_time"))
        end_time = self._parse_datetime(raw_data.get("end_utc_time"))
        
        if not start_time:
            raise ActivityParseError(
                "活动记录缺少开始时间",
                details={"raw_data": raw_data}
            )
        
        duration = 0
        if end_time:
            duration = int((end_time - start_time).total_seconds())
        
        return start_time, max(0, duration)
    
    def _extract_app_info(
        self, 
        raw_data: dict, 
        app_info: Optional[ApplicationInfo]
    ) -> tuple[str, str]:
        """
        提取应用信息
        
        Args:
            raw_data: 原始数据字典
            app_info: 可选的ApplicationInfo对象
            
        Returns:
            (应用名称, 窗口标题) 元组
        """
        # 默认值
        application = raw_data.get("app_name") or raw_data.get("group_name") or "Unknown"
        window_title = ""
        
        # 从upper_key解析
        upper_key = raw_data.get("upper_key", "")
        if upper_key and ";" in upper_key:
            parts = upper_key.split(";", 1)
            application = parts[0].replace(".EXE", "").replace(".exe", "")
            window_title = parts[1] if len(parts) > 1 else ""
        
        # 如果提供了应用信息，优先使用
        if app_info:
            application = app_info.application_name.replace(".EXE", "").replace(".exe", "")
            window_title = app_info.window_title
        
        return application, window_title
    
    def _determine_is_active(self, activity_type: ActivityType, application: str) -> bool:
        """
        判断是否为活跃状态
        
        Args:
            activity_type: 活动类型
            application: 应用名称
            
        Returns:
            是否活跃
        """
        return activity_type == ActivityType.ACTIVE or (
            activity_type == ActivityType.APPLICATION and
            application.lower() not in self.SYSTEM_PROCESSES
        )
    
    def _build_event(
        self,
        timestamp: datetime,
        duration: int,
        application: str,
        window_title: str,
        is_active: bool,
        activity_type: ActivityType,
        raw_data: dict,
    ) -> ActivityEvent:
        """
        构建ActivityEvent对象
        
        Args:
            timestamp: 时间戳
            duration: 持续秒数
            application: 应用名称
            window_title: 窗口标题
            is_active: 是否活跃
            activity_type: 活动类型
            raw_data: 原始数据
            
        Returns:
            ActivityEvent对象
        """
        return ActivityEvent(
            timestamp=timestamp,
            duration_seconds=duration,
            application=application,
            window_title=window_title,
            is_active=is_active,
            activity_type=activity_type,
            source="manictime",
            raw_data=raw_data,
        )
    
    def parse_from_raw_activity(
        self,
        raw: RawActivity,
        app_info: Optional[ApplicationInfo] = None,
        screenshot_metadata: Optional[ScreenshotMetadata] = None,
    ) -> ActivityEvent:
        """
        从RawActivity模型解析活动事件
        
        Args:
            raw: RawActivity对象
            app_info: 可选的应用信息
            screenshot_metadata: 可选的截图元信息
            
        Returns:
            ActivityEvent对象
        """
        return self.parse_from_dict(
            raw_data={
                "report_id": raw.report_id,
                "activity_id": raw.activity_id,
                "group_id": raw.group_id,
                "start_utc_time": raw.start_utc_time,
                "end_utc_time": raw.end_utc_time,
                "source_id": raw.source_id,
                "other": raw.other,
            },
            app_info=app_info,
            screenshot_metadata=screenshot_metadata,
        )
    
    def enrich_with_screenshot(
        self,
        event: ActivityEvent,
        metadata: ScreenshotMetadata,
    ) -> ActivityEvent:
        """
        为事件添加截图信息
        
        Args:
            event: 活动事件
            metadata: 截图元信息
            
        Returns:
            更新后的ActivityEvent
        """
        # Pydantic模型是不可变的，需要创建新实例
        return ActivityEvent(
            event_id=event.event_id,
            timestamp=event.timestamp,
            duration_seconds=event.duration_seconds,
            application=event.application,
            window_title=event.window_title,
            file_path=event.file_path,
            is_active=event.is_active,
            activity_type=event.activity_type,
            screenshot_path=metadata.file_path,
            screenshot_hash=None,  # 哈希在需要时计算
            source=event.source,
            raw_data=event.raw_data,
        )
    
    def _parse_datetime(self, value: any) -> Optional[datetime]:
        """
        解析日期时间值
        
        Args:
            value: 日期时间值（字符串或datetime）
            
        Returns:
            datetime对象，解析失败返回None
        """
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            # 尝试多种格式解析
            return self._try_parse_datetime_string(value)
        
        logger.warning(f"无法解析日期时间: {value}")
        return None
    
    def _try_parse_datetime_string(self, value: str) -> Optional[datetime]:
        """
        尝试多种格式解析日期时间字符串
        
        Args:
            value: 日期时间字符串
            
        Returns:
            datetime对象，解析失败返回None
        """
        formats = [
            ("%Y-%m-%d %H:%M:%S", None),
            ("%Y-%m-%d %H:%M:%S.%f", None),
        ]
        
        # 尝试ISO格式
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
        
        # 尝试其他格式
        for fmt, _ in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        
        return None
    
    def _determine_activity_type(
        self,
        group_key: str,
        application: str,
    ) -> ActivityType:
        """
        判断活动类型
        
        Args:
            group_key: 分组键
            application: 应用名称
            
        Returns:
            ActivityType枚举值
        """
        group_key_lower = group_key.lower()
        
        # 检查是否为活跃/离开状态
        for keyword, activity_type in self.ACTIVITY_STATE_KEYWORDS.items():
            if keyword in group_key_lower:
                return activity_type
        
        # 检查是否为系统进程
        if application in self.SYSTEM_PROCESSES:
            return ActivityType.AWAY
        
        # 默认为应用活动
        return ActivityType.APPLICATION
    
    def batch_parse(
        self,
        raw_data_list: list[dict],
        app_info_map: Optional[dict[int, ApplicationInfo]] = None,
    ) -> list[ActivityEvent]:
        """
        批量解析活动数据
        
        Args:
            raw_data_list: 原始数据字典列表
            app_info_map: 可选的应用信息映射 {common_id: ApplicationInfo}
            
        Returns:
            ActivityEvent对象列表
        """
        events = []
        app_info_map = app_info_map or {}
        
        for raw_data in raw_data_list:
            try:
                # 获取对应的应用信息
                common_id = raw_data.get("common_id")
                app_info = app_info_map.get(common_id) if common_id else None
                
                event = self.parse_from_dict(raw_data, app_info)
                events.append(event)
            except ActivityParseError as e:
                logger.warning(f"跳过无法解析的活动: {e}")
                continue
        
        return events
