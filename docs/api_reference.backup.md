# MainVisualizer API Reference

> **Version**: 0.1.0  
> **Last Updated**: 2025-12

本文档提供 MainVisualizer 各模块的 API 参考，包括公开类、方法和数据模型。

---

## Table of Contents

1. [Core Module](#1-core-module)
2. [Ingest Module - ManicTime](#2-ingest-module---manictime)
3. [Admina Module - VLM Providers](#3-admina-module---vlm-providers)
4. [Senatus Module - Intelligent Trigger](#4-senatus-module---intelligent-trigger)
5. [Data Models](#5-data-models)

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
| `VLMConnectionError` | VLM连接错误 |
| `VLMRateLimitError` | VLM速率限制错误 |
| `VLMResponseParseError` | VLM响应解析错误 |
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

## 3. Admina Module - VLM Providers

VLM/LLM 调用层，负责与各种 VLM 提供商交互，执行深度视觉分析。

### 3.1 IVLMProvider Interface (`src/core/interfaces/vlm_provider.py`)

VLM 提供商抽象接口。

| Method | Signature | Description |
|--------|-----------|-------------|
| `name` | `property -> str` | 提供商名称 |
| `capabilities` | `property -> VLMCapabilities` | 提供商能力描述 |
| `analyze_image` | `async (image, prompt, **kwargs) -> dict` | 分析图像内容 |
| `chat` | `async (messages, **kwargs) -> dict` | 多轮对话 |
| `health_check` | `async () -> HealthCheckResult` | 健康检查 |
| `list_models` | `async () -> list[str]` | 列出可用模型 |

### 3.2 QwenVLProvider

```python
class QwenVLProvider(BaseVLMProvider)
```

阿里云 DashScope Qwen VL 提供商，使用 OpenAI 兼容接口。

**Constructor:**

```python
def __init__(
    self,
    *,
    api_key: Optional[str] = None,      # 默认从 DASHSCOPE_API_KEY 环境变量获取
    base_url: Optional[str] = None,     # 默认: https://dashscope.aliyuncs.com/compatible-mode/v1
    model: str = "qwen3-vl-plus",
    timeout_seconds: int = 60,
    max_retries: int = 3,
) -> None
```

**Supported Models:**

| Model | Description |
|-------|-------------|
| `qwen3-vl-plus` | 通用视觉模型 (推荐) |
| `qwen-vl-max` | 高性能视觉模型 |
| `qwen-vl-plus` | 标准视觉模型 |

**Usage Example:**

```python
from src.admina import QwenVLProvider
from pathlib import Path
import asyncio

async def analyze_screenshot():
    provider = QwenVLProvider()
    
    # 健康检查
    health = await provider.health_check()
    print(f"服务状态: {'正常' if health.is_healthy else '异常'}")
    
    # 分析图像
    result = await provider.analyze_image(
        image=Path("screenshot.png"),
        prompt="描述这张截图中用户正在进行的活动"
    )
    print(f"分析结果: {result['content']}")

asyncio.run(analyze_screenshot())
```

### 3.3 OllamaProvider

```python
class OllamaProvider(BaseVLMProvider)
```

Ollama 本地服务提供商，支持本地 VLM/LLM 模型。

**Constructor:**

```python
def __init__(
    self,
    *,
    host: Optional[str] = None,          # 默认从 OLLAMA_HOST 环境变量或 http://localhost:11434
    model: str = "llava",
    timeout_seconds: int = 120,
    max_retries: int = 3,
) -> None
```

**Additional Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `pull_model(model_name)` | `bool` | 下载指定模型 |

**Usage Example:**

```python
from src.admina import OllamaProvider
import asyncio

async def use_ollama():
    provider = OllamaProvider(model="llava")
    
    # 列出已下载模型
    models = await provider.list_models()
    print(f"可用模型: {models}")
    
    # 图像分析
    result = await provider.analyze_image(
        image="screenshot.png",
        prompt="What is shown in this screenshot?"
    )
    print(result["content"])

asyncio.run(use_ollama())
```

### 3.4 VLM Data Models

#### VLMRequest (`src/admina/models/vlm_request.py`)

| Class | Description |
|-------|-------------|
| `ImageContent` | 图像内容 (URL 或 Base64) |
| `MessageContent` | 消息内容 (文本/图像混合) |
| `ChatMessage` | 聊天消息 |
| `VLMRequest` | VLM 请求 |

#### VLMResponse (`src/admina/models/vlm_response.py`)

| Class | Description |
|-------|-------------|
| `TokenUsage` | Token 使用量统计 |
| `VLMResponse` | VLM 响应 |
| `ScreenContentType` | 屏幕内容类型枚举 |
| `AnalysisResult` | 屏幕分析结果 |

---

## 4. Senatus Module - Intelligent Trigger

智能触发模块，负责计算活动的 Taboo Index (ti) 并决定是否触发 VLM 深度分析。采用三级级联推理架构以最小化 VLM 调用成本。

### 4.1 SenatusEngine

```python
class SenatusEngine
```

Senatus 主引擎类，整合过滤器、分析器、TI 计算器和触发管理器。

**Constructor:**

```python
def __init__(
    self,
    filters: Optional[list[BaseFilter]] = None,
    analyzers: Optional[list[BaseAnalyzer]] = None,
    thresholds: Optional[TriggerThresholds] = None,
    max_batch_size: int = 10,
    batch_timeout_seconds: int = 300,
) -> None
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filters` | `list[BaseFilter]` | `None` | 自定义过滤器列表 |
| `analyzers` | `list[BaseAnalyzer]` | `None` | 自定义分析器列表 |
| `thresholds` | `TriggerThresholds` | `None` | 触发阈值配置 |
| `max_batch_size` | `int` | `10` | 最大批处理大小 |
| `batch_timeout_seconds` | `int` | `300` | 批处理超时时间(秒) |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `process_activity(activity, screenshot)` | `TriggerDecision` | 处理单个活动事件 |
| `process_batch(activities, screenshots)` | `list[TriggerDecision]` | 批量处理活动事件 |
| `check_batch_queue()` | `list[tuple]` | 检查批处理队列 |
| `check_delayed_queue()` | `list[tuple]` | 检查延迟队列 |
| `flush_batch_queue()` | `list[tuple]` | 强制刷新批处理队列 |
| `get_stats()` | `dict` | 获取统计信息 |
| `get_filter_rate()` | `float` | 获取过滤率 |
| `get_trigger_rate()` | `float` | 获取触发率 |
| `add_filter(filter_)` | `None` | 添加过滤器 |
| `remove_filter(name)` | `bool` | 移除过滤器 |

**Usage Example:**

```python
from src.senatus import SenatusEngine, DecisionType
from src.ingest.manictime import ManicTimeDBConnector, ActivityParser

# 初始化引擎
engine = SenatusEngine()

# 处理活动
with ManicTimeDBConnector(db_path) as db:
    activities = db.query_activities(start, end)
    apps = db.query_applications_model()
    app_map = {app.common_id: app for app in apps}

    parser = ActivityParser()
    events = parser.batch_parse(activities, app_map)

    for event in events:
        decision = engine.process_activity(event)

        if decision.decision_type == DecisionType.IMMEDIATE:
            print(f"立即分析: {event.application}")
        elif decision.decision_type == DecisionType.BATCH:
            print(f"批处理: {event.application}")
        elif decision.decision_type == DecisionType.FILTERED:
            print(f"已过滤: {event.application}")

# 查看统计
stats = engine.get_stats()
print(f"过滤率: {engine.get_filter_rate():.2%}")
print(f"触发率: {engine.get_trigger_rate():.2%}")
```

### 4.2 TriggerThresholds

```python
@dataclass
class TriggerThresholds
```

触发阈值配置。

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `immediate_threshold` | `float` | `0.7` | 立即触发阈值 |
| `batch_threshold` | `float` | `0.4` | 批处理阈值 |
| `skip_threshold` | `float` | `0.2` | 跳过阈值 |

### 4.3 TabooIndexCalculator

```python
class TabooIndexCalculator
```

Taboo Index 计算器，整合多个分析器计算最终的 TI 分数。

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `calculate(activity, screenshot)` | `TIResult` | 计算活动的 TI 分数 |
| `add_analyzer(analyzer)` | `None` | 添加分析器 |
| `remove_analyzer(name)` | `bool` | 移除分析器 |

### 4.4 TriggerManager

```python
class TriggerManager
```

触发管理器，根据 TI 分数决定是否触发 VLM 分析，并管理批处理队列。

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `evaluate(activity, ti_result)` | `TriggerDecision` | 评估触发决策 |
| `check_batch_ready()` | `list[tuple]` | 检查批处理队列就绪项 |
| `check_delayed_ready()` | `list[tuple]` | 检查延迟队列就绪项 |
| `flush_batch_queue()` | `list[tuple]` | 强制刷新队列 |

### 4.5 Senatus Data Models

#### TILevel (Enum)

TI 级别枚举。

| Value | Description |
|-------|-------------|
| `HIGH` | ti > 0.7, 高敏感度 |
| `MEDIUM` | 0.4 < ti <= 0.7, 中等敏感度 |
| `LOW` | 0.2 < ti <= 0.4, 低敏感度 |
| `MINIMAL` | ti <= 0.2, 极低敏感度 |

#### DecisionType (Enum)

触发决策类型枚举。

| Value | Description |
|-------|-------------|
| `IMMEDIATE` | 立即触发 VLM 分析 |
| `BATCH` | 加入批处理队列 |
| `SKIP` | 跳过，不需要 VLM 分析 |
| `DELAY` | 延迟处理 |
| `FILTERED` | 被过滤器过滤 |

#### TIResult

TI 计算结果。

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | `UUID` | 关联事件 ID |
| `ti_score` | `float` | TI 分数 (0.0 - 1.0) |
| `ti_level` | `TILevel` | TI 级别 |
| `component_scores` | `dict[str, ComponentScore]` | 各组件评分 |
| `confidence` | `float` | 计算置信度 |
| `should_delay` | `bool` | 是否应延迟处理 |
| `delay_seconds` | `int` | 建议延迟时间(秒) |

#### TriggerDecision

触发决策结果。

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | `UUID` | 关联事件 ID |
| `decision_type` | `DecisionType` | 决策类型 |
| `ti_score` | `Optional[float]` | TI 分数 |
| `reason` | `str` | 决策原因说明 |
| `filter_name` | `Optional[str]` | 触发过滤器名称 |
| `priority` | `int` | 处理优先级 (1-10) |
| `delay_until` | `Optional[datetime]` | 延迟处理目标时间 |
| `batch_group` | `Optional[str]` | 批处理分组标识 |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `should_analyze` | `bool` | 是否需要 VLM 分析 |
| `is_immediate` | `bool` | 是否需要立即分析 |

### 4.6 Filters

#### WhitelistFilter

白名单过滤器，过滤白名单中的应用程序活动。

```python
class WhitelistFilter(BaseFilter)
```

**Constructor:**

```python
def __init__(
    self,
    whitelist_apps: Optional[list[str]] = None,
    whitelist_title_keywords: Optional[list[str]] = None,
    use_regex: bool = False,
    enabled: bool = True,
) -> None
```

### 4.7 Analyzers

#### MetadataAnalyzer

元数据分析器，基于应用名称和窗口标题分析敏感度。

```python
class MetadataAnalyzer(BaseAnalyzer)
```

**Constructor:**

```python
def __init__(
    self,
    weight: float = 0.35,
    enabled: bool = True,
    custom_high_apps: Optional[list[str]] = None,
    custom_high_keywords: Optional[list[str]] = None,
) -> None
```

---

## 5. Data Models

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
