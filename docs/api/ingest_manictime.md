# Ingest Module - ManicTime API Reference

> 本文档是 MainVisualizer API Reference 的一部分
> 返回: [API Reference Index](../api_reference.md)

---


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


---

> 返回: [API Reference Index](../api_reference.md)
