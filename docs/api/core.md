# Core Module API Reference

> 本文档是 MainVisualizer API Reference 的一部分
> 返回: [API Reference Index](../api_reference.md)

---


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


---

> 返回: [API Reference Index](../api_reference.md)
