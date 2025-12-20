# MainVisualizer API Reference

> **Version**: 0.1.0  
> **Last Updated**: 2025-12

本文档提供 MainVisualizer 各模块的 API 参考，包括公开类、方法和数据模型。

---

## Table of Contents

1. [Core Module](#1-core-module)
2. [Ingest Module - ManicTime](#2-ingest-module---manictime)
3. [Data Models](#3-data-models)

---

## 1. Core Module

核心基础设施模块，提供异常定义、日志工具和接口规范。

### 1.1 Exceptions (`src/core/exceptions.py`)

所有异常都继承自 `MainVisualizerError` 基类。

| Exception | Description |
|-----------|-------------|
| `MainVisualizerError` | 所有异常的基类 |
| `ConfigurationError` | 配置相关错误 |
| `DataIngestionError` | 数据摄入层错误 |
| `DatabaseConnectionError` | 数据库连接错误 |
| `DatabaseQueryError` | 数据库查询错误 |
| `ScreenshotLoadError` | 截图加载错误 |
| `ScreenshotNotFoundError` | 截图未找到错误 |
| `ActivityParseError` | 活动数据解析错误 |
| `SenatusError` | Senatus模块错误 |
| `VLMProviderError` | VLM提供商调用错误 |
| `StorageError` | 存储层错误 |

**Usage Example:**

```python
from src.core import DatabaseConnectionError

try:
    connector.connect()
except DatabaseConnectionError as e:
    logger.error(f"连接失败: {e.message}")
    print(f"详情: {e.details}")
```

### 1.2 Logger (`src/core/logger.py`)

```python
def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    log_format: str = LOG_FORMAT,
) -> None
```

配置全局日志设置。

```python
def get_logger(name: str) -> logging.Logger
```

获取指定名称的日志器。

**Usage Example:**

```python
from src.core import setup_logging, get_logger

setup_logging(level=logging.DEBUG)
logger = get_logger(__name__)
logger.info("处理活动数据")
```

### 1.3 Interfaces (`src/core/interfaces/`)

#### IActivityDataSource

活动数据源抽象接口。

| Method | Signature | Description |
|--------|-----------|-------------|
| `connect` | `() -> None` | 建立连接 |
| `disconnect` | `() -> None` | 断开连接 |
| `is_connected` | `() -> bool` | 检查连接状态 |
| `query_activities` | `(start: datetime, end: datetime) -> List[dict]` | 查询活动 |
| `query_applications` | `() -> List[dict]` | 查询应用列表 |
| `query_day_summary` | `(date: date) -> dict` | 查询日汇总 |
| `get_last_sync_time` | `() -> Optional[datetime]` | 获取最后同步时间 |

#### IScreenshotLoader

截图加载器抽象接口。

| Method | Signature | Description |
|--------|-----------|-------------|
| `load_by_timestamp` | `(timestamp: datetime, tolerance: int) -> Optional[Image]` | 按时间戳加载 |
| `load_thumbnail` | `(timestamp: datetime, tolerance: int) -> Optional[Image]` | 加载缩略图 |
| `find_screenshot_path` | `(timestamp: datetime, tolerance: int) -> Optional[Path]` | 查找截图路径 |
| `iter_screenshots` | `(start: datetime, end: datetime) -> Iterator` | 迭代截图 |

---

## 2. Ingest Module - ManicTime

ManicTime 数据摄入模块，提供数据库访问、截图加载和活动解析功能。

### 2.1 ManicTimeDBConnector

```python
class ManicTimeDBConnector(IActivityDataSource)
```

ManicTime SQLite 数据库连接器，只读模式访问。

**Constructor:**

```python
def __init__(self, db_path: Path | str) -> None
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `db_path` | `Path \| str` | ManicTime数据库文件路径 |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `connect()` | `None` | 建立只读连接 |
| `disconnect()` | `None` | 断开连接 |
| `is_connected()` | `bool` | 检查连接状态 |
| `query_activities(start, end)` | `list[dict]` | 查询活动记录 |
| `query_activities_raw(start, end)` | `list[RawActivity]` | 查询原始活动(Pydantic) |
| `query_applications()` | `list[dict]` | 查询应用列表 |
| `query_applications_model()` | `list[ApplicationInfo]` | 查询应用(Pydantic) |
| `query_day_summary(date)` | `dict` | 查询日汇总 |
| `query_day_summary_model(date)` | `DaySummary` | 查询日汇总(Pydantic) |
| `get_last_sync_time()` | `Optional[datetime]` | 获取最后活动时间 |
| `get_activity_count()` | `int` | 获取活动总数 |
| `get_date_range()` | `tuple[datetime, datetime]` | 获取数据时间范围 |

**Usage Example:**

```python
from src.ingest.manictime import ManicTimeDBConnector
from datetime import datetime, timedelta

# 使用上下文管理器
with ManicTimeDBConnector(r"D:\path\to\ManicTimeReports.db") as db:
    # 查询最近7天活动
    end = datetime.now()
    start = end - timedelta(days=7)
    activities = db.query_activities(start, end)
    
    # 获取应用列表
    apps = db.query_applications_model()
    
    # 获取统计信息
    count = db.get_activity_count()
    date_range = db.get_date_range()
```

### 2.2 ScreenshotLoader

```python
class ScreenshotLoader(IScreenshotLoader)
```

ManicTime 截图加载器，支持按时间戳查找和批量加载。

**Constructor:**

```python
def __init__(self, screenshots_path: Path | str) -> None
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `screenshots_path` | `Path \| str` | 截图目录路径 |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `find_screenshot_path(timestamp, tolerance)` | `Optional[Path]` | 查找截图路径 |
| `find_thumbnail_path(timestamp, tolerance)` | `Optional[Path]` | 查找缩略图路径 |
| `load_by_timestamp(timestamp, tolerance)` | `Optional[Image]` | 加载截图 |
| `load_thumbnail(timestamp, tolerance)` | `Optional[Image]` | 加载缩略图 |
| `load_by_path(path)` | `Image` | 直接加载指定路径 |
| `iter_screenshots(start, end)` | `Iterator[tuple]` | 迭代时间范围内截图 |
| `get_screenshot_count()` | `int` | 获取截图总数 |
| `get_date_range()` | `tuple[datetime, datetime]` | 获取截图时间范围 |
| `get_metadata(timestamp, tolerance)` | `Optional[ScreenshotMetadata]` | 获取截图元信息 |

**Usage Example:**

```python
from src.ingest.manictime import ScreenshotLoader
from datetime import datetime

loader = ScreenshotLoader(r"Y:\Screenshots")

# 获取统计信息
print(f"截图总数: {loader.get_screenshot_count()}")

# 按时间戳加载截图
timestamp = datetime(2025, 10, 30, 14, 30, 0)
image = loader.load_by_timestamp(timestamp, tolerance_seconds=60)

# 获取元信息
metadata = loader.get_metadata(timestamp, tolerance_seconds=60)
if metadata:
    print(f"尺寸: {metadata.width} x {metadata.height}")
```

### 2.3 ActivityParser

```python
class ActivityParser
```

活动数据解析器，将原始数据转换为统一的 `ActivityEvent` 格式。

**Constructor:**

```python
def __init__(self, local_timezone_hours: int = 8) -> None
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `local_timezone_hours` | `int` | `8` | 本地时区偏移(小时) |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `parse_from_dict(raw_data, app_info, screenshot)` | `ActivityEvent` | 从字典解析 |
| `parse_from_raw_activity(raw, app_info, screenshot)` | `ActivityEvent` | 从RawActivity解析 |
| `enrich_with_screenshot(event, metadata)` | `ActivityEvent` | 添加截图信息 |
| `batch_parse(raw_data_list, app_info_map)` | `list[ActivityEvent]` | 批量解析 |

**Usage Example:**

```python
from src.ingest.manictime import (
    ManicTimeDBConnector,
    ActivityParser,
)

parser = ActivityParser(local_timezone_hours=8)

with ManicTimeDBConnector(db_path) as db:
    # 查询原始数据
    activities = db.query_activities(start, end)
    apps = db.query_applications_model()
    
    # 构建应用映射
    app_map = {app.common_id: app for app in apps}
    
    # 批量解析
    events = parser.batch_parse(activities, app_map)
    
    for event in events:
        print(f"{event.application}: {event.duration_seconds}s")
```

---

## 3. Data Models

所有数据模型使用 Pydantic 定义，位于 `src/ingest/manictime/models.py`。

### 3.1 ActivityType (Enum)

活动类型枚举。

| Value | Description |
|-------|-------------|
| `ACTIVE` | 活跃状态 |
| `AWAY` | 离开状态 |
| `APPLICATION` | 应用活动 |
| `DOCUMENT` | 文档活动 |
| `UNKNOWN` | 未知类型 |

### 3.2 RawActivity

ManicTime 原始活动记录。

| Field | Type | Description |
|-------|------|-------------|
| `report_id` | `int` | 报告ID |
| `activity_id` | `int` | 活动ID |
| `group_id` | `int` | 分组ID |
| `start_utc_time` | `datetime` | 开始时间(UTC) |
| `end_utc_time` | `datetime` | 结束时间(UTC) |
| `source_id` | `Optional[str]` | 来源ID |
| `other` | `Optional[str]` | 其他JSON数据 |

### 3.3 ApplicationInfo

应用/窗口信息。

| Field | Type | Description |
|-------|------|-------------|
| `common_id` | `int` | 通用分组ID |
| `report_group_type` | `int` | 报告分组类型 |
| `key` | `str` | 唯一标识键 |
| `name` | `str` | 显示名称 |
| `color` | `Optional[str]` | 显示颜色(十六进制) |
| `upper_key` | `Optional[str]` | 大写键名 |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `application_name` | `str` | 提取的应用名称 |
| `window_title` | `str` | 提取的窗口标题 |

### 3.4 ScreenshotMetadata

截图元信息。

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | `Path` | 文件完整路径 |
| `timestamp` | `datetime` | 截图时间戳 |
| `width` | `int` | 图像宽度 |
| `height` | `int` | 图像高度 |
| `screenshot_id` | `int` | 截图ID |
| `monitor_index` | `int` | 显示器索引 |
| `is_thumbnail` | `bool` | 是否为缩略图 |

**Class Methods:**

```python
@classmethod
def from_filename(cls, file_path: Path) -> Optional[ScreenshotMetadata]
```

从文件名解析截图元信息。

### 3.5 ActivityEvent

系统内部统一活动事件格式。

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | `UUID` | 事件唯一ID |
| `timestamp` | `datetime` | 事件时间戳(本地时间) |
| `duration_seconds` | `int` | 持续时间(秒) |
| `application` | `str` | 应用程序名称 |
| `window_title` | `str` | 窗口标题 |
| `file_path` | `Optional[str]` | 关联文件路径 |
| `is_active` | `bool` | 是否为活跃状态 |
| `activity_type` | `ActivityType` | 活动类型 |
| `screenshot_path` | `Optional[Path]` | 关联截图路径 |
| `screenshot_hash` | `Optional[str]` | 截图感知哈希值 |
| `source` | `str` | 数据来源 |
| `raw_data` | `dict` | 原始数据(用于调试) |

### 3.6 DaySummary

日汇总数据。

| Field | Type | Description |
|-------|------|-------------|
| `summary_date` | `date` | 日期 (alias: "date") |
| `total_active_seconds` | `int` | 总活跃时长(秒) |
| `application_stats` | `dict[str, int]` | 各应用使用时长 |
| `top_applications` | `list[tuple[str, int]]` | 使用最多的应用列表 |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `total_active_hours` | `float` | 总活跃小时数 |

---

## Quick Start

```python
from datetime import datetime, timedelta
from src.ingest.manictime import (
    ManicTimeDBConnector,
    ScreenshotLoader,
    ActivityParser,
)

# 配置路径
DB_PATH = r"D:\path\to\ManicTimeReports.db"
SCREENSHOTS_PATH = r"Y:\path\to\Screenshots"

# 初始化组件
parser = ActivityParser()
loader = ScreenshotLoader(SCREENSHOTS_PATH)

# 读取并解析数据
with ManicTimeDBConnector(DB_PATH) as db:
    # 获取时间范围
    min_time, max_time = db.get_date_range()
    
    # 查询最近一天数据
    activities = db.query_activities(
        max_time - timedelta(days=1), 
        max_time
    )
    apps = db.query_applications_model()
    app_map = {app.common_id: app for app in apps}
    
    # 解析为统一格式
    events = parser.batch_parse(activities, app_map)
    
    # 输出结果
    for event in events[:5]:
        print(f"{event.timestamp}: {event.application} ({event.duration_seconds}s)")
```

---

*Document Version: 0.1.0*
