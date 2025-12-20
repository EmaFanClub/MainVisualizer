"""
ManicTime 数据库连接器

负责与ManicTime SQLite数据库的连接和查询操作。
所有数据库操作都以只读模式进行，不会修改原始数据。
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from src.core import get_logger
from src.core.exceptions import (
    DatabaseConnectionError,
    DatabaseQueryError,
)
from src.core.interfaces.data_source import IActivityDataSource

from .models import ApplicationInfo, DaySummary, RawActivity
from .queries import (
    ACTIVITY_COUNT_QUERY,
    ACTIVITY_QUERY,
    APPLICATION_QUERY,
    DATE_RANGE_QUERY,
    DAY_SUMMARY_QUERY,
    LAST_SYNC_QUERY,
    RAW_ACTIVITY_QUERY,
)

logger = get_logger(__name__)


class ManicTimeDBConnector(IActivityDataSource):
    """
    ManicTime SQLite 数据库连接器
    
    提供对ManicTime数据库的只读访问，支持查询活动记录、应用信息和日汇总数据。
    
    Attributes:
        db_path: 数据库文件路径
        _connection: SQLite连接对象
        
    Example:
        connector = ManicTimeDBConnector(Path("ManicTimeReports.db"))
        connector.connect()
        activities = connector.query_activities(start, end)
        connector.disconnect()
    """
    
    def __init__(self, db_path: Path | str) -> None:
        """
        初始化数据库连接器
        
        Args:
            db_path: ManicTime数据库文件路径
        """
        self.db_path = Path(db_path)
        self._connection: Optional[sqlite3.Connection] = None
    
    def connect(self) -> None:
        """
        建立数据库连接（只读模式）
        
        Raises:
            DatabaseConnectionError: 数据库文件不存在或连接失败时抛出
        """
        if self._connection is not None:
            logger.debug("数据库已连接，跳过重复连接")
            return
        
        if not self.db_path.exists():
            raise DatabaseConnectionError(
                f"数据库文件不存在: {self.db_path}",
                details={"path": str(self.db_path)}
            )
        
        try:
            # 使用URI模式打开只读连接
            uri = f"file:{self.db_path}?mode=ro"
            self._connection = sqlite3.connect(uri, uri=True)
            self._connection.row_factory = sqlite3.Row
            logger.info(f"成功连接到数据库: {self.db_path}")
        except sqlite3.Error as e:
            raise DatabaseConnectionError(
                f"无法连接到数据库: {e}",
                details={"path": str(self.db_path), "error": str(e)}
            ) from e
    
    def disconnect(self) -> None:
        """断开数据库连接"""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("数据库连接已关闭")
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connection is not None
    
    def _ensure_connected(self) -> None:
        """确保数据库已连接"""
        if not self.is_connected():
            raise DatabaseConnectionError(
                "数据库未连接，请先调用 connect() 方法"
            )
    
    def _execute_query(
        self, 
        sql: str, 
        params: tuple = ()
    ) -> list[sqlite3.Row]:
        """
        执行查询并返回结果
        
        Args:
            sql: SQL查询语句
            params: 查询参数
            
        Returns:
            查询结果行列表
            
        Raises:
            DatabaseQueryError: 查询执行失败时抛出
        """
        self._ensure_connected()
        try:
            cursor = self._connection.cursor()
            cursor.execute(sql, params)
            return cursor.fetchall()
        except sqlite3.Error as e:
            raise DatabaseQueryError(
                f"查询执行失败: {e}",
                details={"sql": sql[:200], "error": str(e)}
            ) from e
    
    def query_activities(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict]:
        """
        查询指定时间范围的活动记录
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            活动记录字典列表
        """
        start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
        
        rows = self._execute_query(ACTIVITY_QUERY, (start_str, end_str))
        
        activities = [self._row_to_activity_dict(row) for row in rows]
        logger.debug(f"查询到 {len(activities)} 条活动记录")
        return activities
    
    def _row_to_activity_dict(self, row: sqlite3.Row) -> dict:
        """将数据库行转换为活动字典"""
        return {
            "report_id": row["ReportId"],
            "activity_id": row["ActivityId"],
            "group_id": row["GroupId"],
            "start_utc_time": row["StartUtcTime"],
            "end_utc_time": row["EndUtcTime"],
            "source_id": row["SourceId"],
            "other": row["Other"],
            "common_id": row["CommonId"],
            "group_name": row["GroupName"],
            "group_key": row["GroupKey"],
            "app_key": row["AppKey"],
            "app_name": row["AppName"],
            "upper_key": row["UpperKey"],
        }
    
    def query_activities_raw(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> list[RawActivity]:
        """
        查询原始活动记录（使用Pydantic模型）
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            RawActivity对象列表
        """
        start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
        
        rows = self._execute_query(RAW_ACTIVITY_QUERY, (start_str, end_str))
        
        return [self._row_to_raw_activity(row) for row in rows]
    
    def _row_to_raw_activity(self, row: sqlite3.Row) -> RawActivity:
        """将数据库行转换为RawActivity对象"""
        return RawActivity(
            report_id=row["ReportId"],
            activity_id=row["ActivityId"],
            group_id=row["GroupId"],
            start_utc_time=datetime.fromisoformat(row["StartUtcTime"]),
            end_utc_time=datetime.fromisoformat(row["EndUtcTime"]),
            source_id=row["SourceId"],
            other=row["Other"],
        )
    
    def query_applications(self) -> list[dict]:
        """
        查询所有应用信息
        
        Returns:
            应用信息字典列表
        """
        rows = self._execute_query(APPLICATION_QUERY)
        
        applications = [self._row_to_app_dict(row) for row in rows]
        logger.debug(f"查询到 {len(applications)} 个应用")
        return applications
    
    def _row_to_app_dict(self, row: sqlite3.Row) -> dict:
        """将数据库行转换为应用字典"""
        return {
            "common_id": row["CommonId"],
            "report_group_type": row["ReportGroupType"],
            "key": row["Key"],
            "name": row["Name"],
            "color": row["Color"],
            "upper_key": row["UpperKey"],
        }
    
    def query_applications_model(self) -> list[ApplicationInfo]:
        """
        查询应用信息（使用Pydantic模型）
        
        Returns:
            ApplicationInfo对象列表
        """
        rows = self._execute_query(APPLICATION_QUERY)
        return [
            ApplicationInfo(
                common_id=row["CommonId"],
                report_group_type=row["ReportGroupType"],
                key=row["Key"],
                name=row["Name"],
                color=row["Color"],
                upper_key=row["UpperKey"],
            )
            for row in rows
        ]
    
    def query_day_summary(self, target_date: date) -> dict:
        """
        查询指定日期的汇总数据
        
        Args:
            target_date: 目标日期
            
        Returns:
            日汇总数据字典
        """
        date_str = target_date.isoformat()
        rows = self._execute_query(DAY_SUMMARY_QUERY, (date_str,))
        
        total_seconds = 0
        app_stats = {}
        
        for row in rows:
            app_name = row["Name"] or "Unknown"
            seconds = row["TotalSeconds"] or 0
            app_stats[app_name] = seconds
            total_seconds += seconds
        
        # 排序获取Top应用
        top_apps = sorted(
            app_stats.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        
        return {
            "date": target_date,
            "total_active_seconds": total_seconds,
            "application_stats": app_stats,
            "top_applications": top_apps,
        }
    
    def query_day_summary_model(self, target_date: date) -> DaySummary:
        """
        查询日汇总数据（使用Pydantic模型）
        
        Args:
            target_date: 目标日期
            
        Returns:
            DaySummary对象
        """
        data = self.query_day_summary(target_date)
        return DaySummary(**data)
    
    def get_last_sync_time(self) -> Optional[datetime]:
        """
        获取数据库中最后一条活动的时间
        
        Returns:
            最后活动时间，如果数据库为空则返回None
        """
        rows = self._execute_query(LAST_SYNC_QUERY)
        
        if rows and rows[0]["LastTime"]:
            return datetime.fromisoformat(rows[0]["LastTime"])
        return None
    
    def get_activity_count(self) -> int:
        """
        获取活动记录总数
        
        Returns:
            活动记录数量
        """
        rows = self._execute_query(ACTIVITY_COUNT_QUERY)
        return rows[0]["Count"] if rows else 0
    
    def get_date_range(self) -> tuple[Optional[datetime], Optional[datetime]]:
        """
        获取数据库中活动的时间范围
        
        Returns:
            (最早时间, 最晚时间) 元组
        """
        rows = self._execute_query(DATE_RANGE_QUERY)
        
        if rows:
            min_time = rows[0]["MinTime"]
            max_time = rows[0]["MaxTime"]
            return (
                datetime.fromisoformat(min_time) if min_time else None,
                datetime.fromisoformat(max_time) if max_time else None,
            )
        return (None, None)
    
    def __enter__(self) -> "ManicTimeDBConnector":
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器退出"""
        self.disconnect()
