# Data Models API Reference

> 本文档是 MainVisualizer API Reference 的一部分
> 返回: [API Reference Index](../api_reference.md)

---


所有数据模型使用 Pydantic 定义，位于 `src/ingest/manictime/models.py`。

### 5.1 ActivityType (Enum)

活动类型枚举。

| Value | Description |
|-------|-------------|
| `ACTIVE` | 活跃状态 |
| `AWAY` | 离开状态 |
| `APPLICATION` | 应用活动 |
| `DOCUMENT` | 文档活动 |
| `UNKNOWN` | 未知类型 |

### 5.2 RawActivity

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

### 5.3 ApplicationInfo

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

### 5.4 ScreenshotMetadata

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

**文件名格式:**

```
YYYY-MM-DD_HH-MM-SS_TZ_width_height_id_monitor.jpg
```

| 部分 | 示例 | 说明 |
|------|------|------|
| `YYYY-MM-DD` | `2025-12-22` | 日期 |
| `HH-MM-SS` | `13-56-02` | 时间 (用 `-` 分隔) |
| `TZ` | `08-00` | 时区偏移 (+08:00) |
| `width` | `2878` | 图像宽度 |
| `height` | `2017` | 图像高度 |
| `id` | `828953` | 截图ID |
| `monitor` | `1` | 显示器索引 |

**完整示例:**

```
2025-12-22_13-56-02_08-00_2878_2017_828953_1.jpg
2025-12-22_13-56-02_08-00_2878_2017_828953_1.thumbnail.jpg  (缩略图)
```

**Usage Example:**

```python
from pathlib import Path
from src.ingest.manictime.models import ScreenshotMetadata

file_path = Path("screenshots/2025-12-22/2025-12-22_13-56-02_08-00_2878_2017_828953_1.jpg")
metadata = ScreenshotMetadata.from_filename(file_path)

if metadata:
    print(f"时间戳: {metadata.timestamp}")
    print(f"尺寸: {metadata.width} x {metadata.height}")
    print(f"截图ID: {metadata.screenshot_id}")
```

### 5.5 ActivityEvent

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

### 5.6 DaySummary

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


---

> 返回: [API Reference Index](../api_reference.md)
