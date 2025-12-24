---
name: api-query
description: Quickly query and understand existing APIs in MainVisualizer. Use when writing new code, calling existing module APIs, understanding interface signatures, or viewing usage examples. Triggers on API lookups, interface queries, or when importing existing modules.
---

# API Query Skill

> **Purpose**: 在编写新代码或添加新功能时，快速查询和理解 MainVisualizer 现有 API
> **Trigger**: 当需要调用现有模块的 API、了解接口签名、查看使用示例时使用

---

## 渐进式查询流程

### Level 1: 快速索引

读取 `docs/api_reference.md` 获取：
- Quick Reference Card (常用导入和快速使用模式)
- Module Index (5个模块的位置和用途)
- Data Models Overview (8个核心数据模型)

### Level 2: 模块详细文档

| 模块 | 文档路径 | 主要内容 |
|------|----------|----------|
| Core | `docs/api/core.md` | 异常类、日志工具、抽象接口 |
| Ingest | `docs/api/ingest_manictime.md` | DB连接器、截图加载器、活动解析器 |
| Admina | `docs/api/admina_providers.md` | VLM提供商接口、Qwen/Ollama实现 |
| Senatus | `docs/api/senatus.md` | 触发引擎、TI计算、过滤器/分析器 |
| Data Models | `docs/api/data_models.md` | Pydantic模型定义 |
| Quick Start | `docs/api/quick_start.md` | 完整使用示例 |

### Level 3: 源码验证

| 模块 | 源码路径 |
|------|----------|
| Core | `src/core/exceptions.py`, `src/core/logger.py`, `src/core/interfaces/` |
| Ingest | `src/ingest/manictime/connector.py`, `models.py`, `screenshot_loader.py`, `parser.py` |
| Admina | `src/admina/providers/qwen_vl.py`, `ollama.py`, `src/admina/models/` |
| Senatus | `src/senatus/engine.py`, `trigger_manager.py`, `ti_calculator.py` |

---

## 核心 API 速查表

### 1. Core 模块

**异常类** (`src/core/exceptions.py`):
```python
MainVisualizerError          # 基类
├── ConfigurationError       # 配置错误
├── DataIngestionError       # 数据摄入错误
│   ├── DatabaseConnectionError
│   ├── DatabaseQueryError
│   ├── ScreenshotLoadError
│   ├── ScreenshotNotFoundError
│   └── ActivityParseError
├── SenatusError             # Senatus模块错误
├── VLMProviderError         # VLM错误
│   ├── VLMConnectionError
│   ├── VLMRateLimitError
│   └── VLMResponseParseError
└── StorageError             # 存储错误
```

**日志工具** (`src/core/logger.py`):
```python
setup_logging(level=logging.INFO, log_file=None, log_format=LOG_FORMAT) -> None
get_logger(name: str) -> logging.Logger
```

**抽象接口** (`src/core/interfaces/`):
- `IActivityDataSource`: 活动数据源接口 (connect, query_activities, query_applications)
- `IScreenshotLoader`: 截图加载接口 (load_by_timestamp, iter_screenshots)

### 2. Ingest 模块 - ManicTime

**ManicTimeDBConnector** - SQLite只读连接器:
```python
def __init__(self, db_path: Path | str) -> None

# 核心方法
query_activities(start: datetime, end: datetime) -> list[dict]
query_activities_raw(start, end) -> list[RawActivity]  # Pydantic模型
query_applications() -> list[dict]
query_applications_model() -> list[ApplicationInfo]    # Pydantic模型
query_day_summary(date) -> dict
query_day_summary_model(date) -> DaySummary           # Pydantic模型
get_activity_count() -> int
get_date_range() -> tuple[datetime, datetime]
get_last_sync_time() -> Optional[datetime]
```

**ScreenshotLoader** - 截图加载器:
```python
def __init__(self, screenshots_path: Path | str) -> None

# 核心方法
find_screenshot_path(timestamp, tolerance_seconds) -> Optional[Path]
find_thumbnail_path(timestamp, tolerance_seconds) -> Optional[Path]
load_by_timestamp(timestamp, tolerance_seconds) -> Optional[Image]
load_thumbnail(timestamp, tolerance_seconds) -> Optional[Image]
iter_screenshots(start, end) -> Iterator[tuple]
get_metadata(timestamp, tolerance) -> Optional[ScreenshotMetadata]
get_screenshot_count() -> int
get_date_range() -> tuple[datetime, datetime]
```

**ActivityParser** - 活动解析器:
```python
def __init__(self, local_timezone_hours: int = 8) -> None

# 核心方法
parse_from_dict(raw_data, app_info, screenshot) -> ActivityEvent
parse_from_raw_activity(raw, app_info, screenshot) -> ActivityEvent
batch_parse(raw_data_list, app_info_map) -> list[ActivityEvent]
enrich_with_screenshot(event, metadata) -> ActivityEvent
```

### 3. Admina 模块 - VLM Providers

**IVLMProvider 接口**:
```python
@property name -> str                    # 提供商名称
@property capabilities -> VLMCapabilities # 能力描述
async analyze_image(image, prompt, **kwargs) -> dict
async chat(messages, **kwargs) -> dict
async health_check() -> HealthCheckResult
async list_models() -> list[str]
```

**QwenVLProvider** - 阿里云DashScope:
```python
def __init__(
    self,
    *,
    api_key: Optional[str] = None,      # 默认: DASHSCOPE_API_KEY 环境变量
    base_url: Optional[str] = None,     # 默认: https://dashscope.aliyuncs.com/compatible-mode/v1
    model: str = "qwen3-vl-plus",       # 可选: qwen-vl-max, qwen-vl-plus
    timeout_seconds: int = 60,
    max_retries: int = 3,
) -> None
```

**OllamaProvider** - 本地Ollama:
```python
def __init__(
    self,
    *,
    host: Optional[str] = None,         # 默认: OLLAMA_HOST 或 http://localhost:11434
    model: str = "llava",
    timeout_seconds: int = 120,
    max_retries: int = 3,
) -> None

# 额外方法
pull_model(model_name: str) -> bool     # 下载模型
```

**数据模型**:
- `ImageContent`: 图像内容 (URL/Base64)
- `MessageContent`: 消息内容 (文本/图像混合)
- `ChatMessage`: 聊天消息
- `VLMRequest`: VLM请求
- `VLMResponse`: VLM响应
- `TokenUsage`: Token使用量
- `AnalysisResult`: 屏幕分析结果

### 4. Senatus 模块 - Intelligent Trigger

**SenatusEngine** - 主引擎:
```python
def __init__(
    self,
    filters: Optional[list[BaseFilter]] = None,
    analyzers: Optional[list[BaseAnalyzer]] = None,
    thresholds: Optional[TriggerThresholds] = None,
    max_batch_size: int = 10,
    batch_timeout_seconds: int = 300,
) -> None

# 核心方法
process_activity(activity, screenshot) -> TriggerDecision
process_batch(activities, screenshots) -> list[TriggerDecision]
check_batch_queue() -> list[tuple]
check_delayed_queue() -> list[tuple]
flush_batch_queue() -> list[tuple]
get_stats() -> dict
get_filter_rate() -> float
get_trigger_rate() -> float
add_filter(filter_) -> None
remove_filter(name) -> bool
```

**TriggerThresholds** - 阈值配置:
```python
@dataclass
class TriggerThresholds:
    immediate_threshold: float = 0.7    # 立即触发
    batch_threshold: float = 0.4        # 批处理
    skip_threshold: float = 0.2         # 跳过
```

**枚举类型**:
```python
class TILevel(Enum):      # TI级别
    HIGH     # ti > 0.7
    MEDIUM   # 0.4 < ti <= 0.7
    LOW      # 0.2 < ti <= 0.4
    MINIMAL  # ti <= 0.2

class DecisionType(Enum): # 决策类型
    IMMEDIATE  # 立即触发VLM分析
    BATCH      # 加入批处理队列
    SKIP       # 跳过
    DELAY      # 延迟处理
    FILTERED   # 被过滤器过滤
```

**数据模型**:
- `TIResult`: TI计算结果 (event_id, ti_score, ti_level, component_scores, confidence)
- `TriggerDecision`: 触发决策 (event_id, decision_type, ti_score, reason, priority)
  - 属性: `should_analyze`, `is_immediate`

**过滤器与分析器**:
```python
# WhitelistFilter - 白名单过滤
WhitelistFilter(
    whitelist_apps: list[str] = None,
    whitelist_title_keywords: list[str] = None,
    use_regex: bool = False,
)

# MetadataAnalyzer - 元数据分析
MetadataAnalyzer(
    weight: float = 0.35,
    custom_high_apps: list[str] = None,
    custom_high_keywords: list[str] = None,
)
```

### 5. Data Models

**核心数据模型** (`src/ingest/manictime/models.py`):

| 模型 | 关键字段 |
|------|----------|
| `ActivityType` | ACTIVE, AWAY, APPLICATION, DOCUMENT, UNKNOWN |
| `RawActivity` | report_id, activity_id, group_id, start_utc_time, end_utc_time |
| `ApplicationInfo` | common_id, key, name, color; 属性: application_name, window_title |
| `ScreenshotMetadata` | file_path, timestamp, width, height, screenshot_id, monitor_index |
| `ActivityEvent` | event_id(UUID), timestamp, duration_seconds, application, window_title, is_active, screenshot_path |
| `DaySummary` | summary_date, total_active_seconds, application_stats; 属性: total_active_hours |

---

## 常用代码模式

### 模式1: 读取ManicTime数据

```python
from src.ingest.manictime import ManicTimeDBConnector, ActivityParser
from datetime import datetime, timedelta

parser = ActivityParser(local_timezone_hours=8)

with ManicTimeDBConnector(db_path) as db:
    end = datetime.now()
    start = end - timedelta(days=7)

    activities = db.query_activities(start, end)
    apps = db.query_applications_model()
    app_map = {app.common_id: app for app in apps}

    events = parser.batch_parse(activities, app_map)
```

### 模式2: 调用VLM分析

```python
from src.admina import QwenVLProvider
from pathlib import Path
import asyncio

async def analyze():
    provider = QwenVLProvider()

    health = await provider.health_check()
    if not health.is_healthy:
        raise RuntimeError("VLM服务不可用")

    result = await provider.analyze_image(
        image=Path("screenshot.png"),
        prompt="描述截图中的用户活动"
    )
    return result["content"]

asyncio.run(analyze())
```

### 模式3: Senatus触发决策

```python
from src.senatus import SenatusEngine, DecisionType

engine = SenatusEngine()

for event in events:
    decision = engine.process_activity(event)

    if decision.decision_type == DecisionType.IMMEDIATE:
        # 立即调用VLM
        pass
    elif decision.decision_type == DecisionType.BATCH:
        # 等待批处理
        pass
    elif decision.decision_type == DecisionType.FILTERED:
        # 已被白名单过滤
        pass

print(f"过滤率: {engine.get_filter_rate():.2%}")
```

---

## 模块依赖关系

```
          ┌─────────┐
          │  core   │  (异常、日志、接口)
          └────┬────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
┌───────┐  ┌───────┐  ┌─────────┐
│ingest │  │admina │  │ senatus │
└───────┘  └───────┘  └────┬────┘
                           │
                      依赖 ingest
```

---

## 查询指南

1. **查构造函数参数**: 读取对应模块的 L3 文档，查看 Constructor 部分
2. **查方法签名**: 读取 L3 文档的 Methods 表格
3. **查使用示例**: 读取 L3 文档的 Usage Example 或 `docs/api/quick_start.md`
4. **查异常处理**: 读取 `docs/api/core.md` 的 Exceptions 部分
5. **查数据模型字段**: 读取 `docs/api/data_models.md`
6. **验证实现细节**: 读取对应源码文件
