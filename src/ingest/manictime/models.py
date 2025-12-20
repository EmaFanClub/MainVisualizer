"""
ManicTime 数据模型

定义从ManicTime读取的原始数据和系统内部统一格式的数据模型。
所有模型使用Pydantic进行数据验证。
"""

from __future__ import annotations

from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import Optional, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class ActivityType(str, Enum):
    """
    活动类型枚举
    
    用于分类不同类型的活动记录
    """
    ACTIVE = "active"  # 活跃状态
    AWAY = "away"  # 离开状态
    APPLICATION = "application"  # 应用活动
    DOCUMENT = "document"  # 文档活动
    UNKNOWN = "unknown"  # 未知类型


class RawActivity(BaseModel):
    """
    ManicTime 原始活动记录
    
    直接映射数据库 Ar_Activity 表结构
    """
    report_id: int = Field(..., description="报告ID")
    activity_id: int = Field(..., description="活动ID")
    group_id: int = Field(..., description="分组ID")
    start_utc_time: datetime = Field(..., description="开始时间(UTC)")
    end_utc_time: datetime = Field(..., description="结束时间(UTC)")
    source_id: Optional[str] = Field(default=None, description="来源ID")
    other: Optional[str] = Field(default=None, description="其他JSON数据")


class ApplicationInfo(BaseModel):
    """
    应用/窗口信息
    
    映射 Ar_CommonGroup 表结构
    """
    common_id: int = Field(..., description="通用分组ID")
    report_group_type: int = Field(..., description="报告分组类型")
    key: str = Field(..., description="唯一标识键")
    name: str = Field(..., description="显示名称")
    color: Optional[str] = Field(default=None, description="显示颜色(十六进制)")
    upper_key: Optional[str] = Field(default=None, description="大写键名(用于查找)")
    
    @property
    def application_name(self) -> str:
        """
        提取应用程序名称
        
        从 upper_key (格式: "APP.EXE;WINDOW TITLE") 中提取应用名
        """
        if self.upper_key:
            parts = self.upper_key.split(";")
            if parts:
                return parts[0]
        return self.name
    
    @property
    def window_title(self) -> str:
        """
        提取窗口标题
        
        从 upper_key 中提取窗口标题部分
        """
        if self.upper_key and ";" in self.upper_key:
            return self.upper_key.split(";", 1)[1]
        return self.name


class ScreenshotMetadata(BaseModel):
    """
    截图元信息
    
    解析截图文件名获取的元数据
    """
    file_path: Path = Field(..., description="文件完整路径")
    timestamp: datetime = Field(..., description="截图时间戳")
    width: int = Field(..., description="图像宽度")
    height: int = Field(..., description="图像高度")
    screenshot_id: int = Field(..., description="截图ID")
    monitor_index: int = Field(default=0, description="显示器索引")
    is_thumbnail: bool = Field(default=False, description="是否为缩略图")
    
    @classmethod
    def from_filename(cls, file_path: Path) -> Optional["ScreenshotMetadata"]:
        """
        从文件名解析截图元信息
        
        文件名格式: YYYY-MM-DD_HH-MM-SS_TZ_width_height_id_monitor.jpg
        示例: 2025-10-23_21-58-16_08-00_1704_1341_755811_0.jpg
        
        Args:
            file_path: 截图文件路径
            
        Returns:
            ScreenshotMetadata实例，解析失败返回None
        """
        filename = file_path.stem
        is_thumbnail = filename.endswith(".thumbnail")
        if is_thumbnail:
            filename = filename.replace(".thumbnail", "")
        
        parts = filename.split("_")
        if len(parts) < 7:
            return None
        
        try:
            # 解析日期时间: YYYY-MM-DD_HH-MM-SS
            date_str = parts[0]  # 2025-10-23
            time_str = parts[1]  # 21-58-16
            
            # 时区偏移: 08-00 -> +08:00
            tz_parts = parts[2].split("-")
            if len(tz_parts) == 2:
                tz_str = f"+{tz_parts[0]}:{tz_parts[1]}"
            else:
                tz_str = "+00:00"
            
            datetime_str = f"{date_str}T{time_str.replace('-', ':')}:00{tz_str}"
            timestamp = datetime.fromisoformat(datetime_str)
            
            width = int(parts[3])
            height = int(parts[4])
            screenshot_id = int(parts[5])
            monitor_index = int(parts[6])
            
            return cls(
                file_path=file_path,
                timestamp=timestamp,
                width=width,
                height=height,
                screenshot_id=screenshot_id,
                monitor_index=monitor_index,
                is_thumbnail=is_thumbnail,
            )
        except (ValueError, IndexError):
            return None


class ActivityEvent(BaseModel):
    """
    系统内部统一活动事件格式
    
    所有数据源的活动记录最终都转换为此格式，供后续模块处理。
    """
    event_id: UUID = Field(default_factory=uuid4, description="事件唯一ID")
    timestamp: datetime = Field(..., description="事件时间戳(本地时间)")
    duration_seconds: int = Field(..., ge=0, description="持续时间(秒)")
    
    # 应用信息
    application: str = Field(..., description="应用程序名称")
    window_title: str = Field(default="", description="窗口标题")
    file_path: Optional[str] = Field(default=None, description="关联文件路径")
    
    # 状态信息
    is_active: bool = Field(default=True, description="是否为活跃状态")
    activity_type: ActivityType = Field(
        default=ActivityType.APPLICATION, 
        description="活动类型"
    )
    
    # 截图信息
    screenshot_path: Optional[Path] = Field(
        default=None, 
        description="关联截图路径"
    )
    screenshot_hash: Optional[str] = Field(
        default=None, 
        description="截图感知哈希值(用于去重)"
    )
    
    # 原始数据引用
    source: str = Field(default="manictime", description="数据来源")
    raw_data: dict[str, Any] = Field(
        default_factory=dict, 
        description="原始数据(用于调试)"
    )
    
    class Config:
        """Pydantic配置"""
        arbitrary_types_allowed = True


class DaySummary(BaseModel):
    """
    日汇总数据
    
    某一天的活动统计汇总
    """
    summary_date: date = Field(..., alias="date", description="日期")
    total_active_seconds: int = Field(default=0, description="总活跃时长(秒)")
    application_stats: dict[str, int] = Field(
        default_factory=dict, 
        description="各应用使用时长(秒)"
    )
    top_applications: list[tuple[str, int]] = Field(
        default_factory=list, 
        description="使用最多的应用列表 [(应用名, 时长)]"
    )
    
    class Config:
        """Pydantic配置"""
        populate_by_name = True
    
    @property
    def total_active_hours(self) -> float:
        """获取总活跃小时数"""
        return self.total_active_seconds / 3600
