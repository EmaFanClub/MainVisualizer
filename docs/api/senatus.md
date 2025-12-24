# Senatus Module - Intelligent Trigger API Reference

> 本文档是 MainVisualizer API Reference 的一部分
> 返回: [API Reference Index](../api_reference.md)

---


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

Senatus 模块提供四种过滤器，用于在 TI 计算前过滤活动。过滤器按顺序执行，任一过滤器匹配则跳过该活动。

**默认过滤器链:**
```
WhitelistFilter → BlacklistFilter → TimeRuleFilter → StaticFrameFilter
```

#### BaseFilter

所有过滤器的抽象基类。

```python
class BaseFilter(ABC)
```

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `name` | `str` | 过滤器名称 |
| `enabled` | `bool` | 是否启用 |
| `stats` | `dict` | 统计信息 |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `check(activity)` | `FilterResult` | 检查活动是否应被过滤 |
| `check_with_image(activity, image)` | `FilterResult` | 带图像的检查(用于 StaticFrameFilter) |

#### FilterResult

过滤器检查结果。

| Field | Type | Description |
|-------|------|-------------|
| `should_skip` | `bool` | 是否应跳过该活动 |
| `reason` | `str` | 跳过原因说明 |
| `matched_rule` | `str` | 匹配的规则名称 |

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

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `whitelist_apps` | `list[str]` | 内置列表 | 白名单应用名称 |
| `whitelist_title_keywords` | `list[str]` | 内置列表 | 白名单标题关键词 |
| `use_regex` | `bool` | `False` | 是否使用正则表达式匹配 |
| `enabled` | `bool` | `True` | 是否启用 |

#### BlacklistFilter

黑名单过滤器，过滤已知安全的应用程序活动。

```python
class BlacklistFilter(BaseFilter)
```

**Constructor:**

```python
def __init__(
    self,
    blacklist_apps: Optional[list[str]] = None,
    blacklist_title_keywords: Optional[list[str]] = None,
    use_regex: bool = False,
    enabled: bool = True,
) -> None
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `blacklist_apps` | `list[str]` | 内置列表 | 黑名单应用名称 |
| `blacklist_title_keywords` | `list[str]` | 内置列表 | 黑名单标题关键词 |
| `use_regex` | `bool` | `False` | 是否使用正则表达式匹配 |
| `enabled` | `bool` | `True` | 是否启用 |

**内置黑名单应用:**
- 锁屏: `lockapp.exe`, `logonui.exe`
- 系统: `explorer.exe` (桌面), `searchui.exe`
- 安装程序: `msiexec.exe`, `setup.exe`

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `add_app(app_name)` | `None` | 添加应用到黑名单 |
| `add_title_keyword(keyword)` | `None` | 添加标题关键词到黑名单 |
| `remove_app(app_name)` | `bool` | 从黑名单移除应用 |
| `is_blacklisted(activity)` | `bool` | 快速检查活动是否在黑名单中 |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `blacklist_apps` | `set[str]` | 黑名单应用列表(只读副本) |
| `blacklist_title_keywords` | `list[str]` | 黑名单标题关键词列表(只读副本) |
| `force_immediate` | `bool` | 是否强制立即触发 |
| `suggested_ti_score` | `float` | 建议的 TI 分数 |

#### TimeRuleFilter

时间规则过滤器，基于时间规则过滤活动。

```python
class TimeRuleFilter(BaseFilter)
```

**Constructor:**

```python
def __init__(
    self,
    rules: Optional[list[TimeRule]] = None,
    enabled: bool = True,
) -> None
```

**TimeRule 数据类:**

```python
@dataclass
class TimeRule:
    name: str                    # 规则名称
    days: list[int]              # 适用的星期几 (0=周一, 6=周日)
    start_time: str              # 开始时间 (HH:MM 格式)
    end_time: str                # 结束时间 (HH:MM 格式)
    skip_analysis: bool = False  # 是否跳过分析
    weight_modifier: float = 1.0 # 权重修正因子
    reason: str = ""             # 规则说明
```

**Usage Example:**

```python
from src.senatus.filters import TimeRuleFilter, TimeRule

# 创建规则: 工作日晚上 22:00-06:00 跳过
night_rule = TimeRule(
    name="night_hours",
    days=[0, 1, 2, 3, 4],  # 周一至周五
    start_time="22:00",
    end_time="06:00",
    skip_analysis=True,
    reason="夜间时段，跳过分析",
)

# 周末全天跳过
weekend_rule = TimeRule(
    name="weekend",
    days=[5, 6],  # 周六、周日
    start_time="00:00",
    end_time="23:59",
    skip_analysis=True,
    reason="周末时段",
)

filter_ = TimeRuleFilter(rules=[night_rule, weekend_rule])
```

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `add_rule(rule)` | `None` | 添加时间规则 |
| `remove_rule(name)` | `bool` | 移除时间规则 |
| `get_active_rules(timestamp)` | `list[TimeRule]` | 获取指定时间生效的规则 |

#### StaticFrameFilter

静态帧过滤器，检测并过滤连续相似的截图帧。使用感知哈希算法比较图像相似度。

```python
class StaticFrameFilter(BaseFilter)
```

**Constructor:**

```python
def __init__(
    self,
    diff_threshold: float = 0.1,
    hash_size: int = 8,
    history_size: int = 10,
    enabled: bool = True,
) -> None
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `diff_threshold` | `float` | `0.1` | 差异阈值，低于此值视为静态帧 |
| `hash_size` | `int` | `8` | 感知哈希大小 |
| `history_size` | `int` | `10` | 历史帧缓存大小 |
| `enabled` | `bool` | `True` | 是否启用 |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `check_with_image(activity, image)` | `FilterResult` | 带图像检查 |
| `compute_hash(image)` | `tuple[str, str]` | 计算图像的 aHash 和 dHash |
| `compare_images(img1, img2)` | `float` | 比较两图像差异度 |
| `clear_history()` | `None` | 清除历史帧缓存 |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `history` | `list` | 历史帧哈希列表 |
| `static_frame_rate` | `float` | 静态帧比率 |

**Usage Example:**

```python
from src.senatus.filters import StaticFrameFilter
from PIL import Image

filter_ = StaticFrameFilter(diff_threshold=0.05)

# 检查帧
image = Image.open("screenshot.png")
result = filter_.check_with_image(activity, image)

if result.should_skip:
    print(f"跳过静态帧: {result.reason}")

# 查看静态帧率
print(f"静态帧率: {filter_.static_frame_rate:.2%}")
```

---

### 4.7 Analyzers

Senatus 模块提供五种分析器，用于计算活动的 Taboo Index (TI) 分数。每个分析器有独立的权重，最终 TI 为加权平均值。

**默认分析器权重:**

| Analyzer | Weight | Description |
|----------|--------|-------------|
| `MetadataAnalyzer` | 0.25 | 元数据分析 |
| `VisualAnalyzer` | 0.35 | 视觉敏感度分析 |
| `ContextSwitchAnalyzer` | 0.15 | 上下文切换分析 |
| `FrameDiffAnalyzer` | 0.15 | 帧差异分析 |
| `UncertaintyAnalyzer` | 0.10 | 不确定性分析 |

#### BaseAnalyzer

所有分析器的抽象基类。

```python
class BaseAnalyzer(ABC)
```

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `name` | `str` | 分析器名称 |
| `weight` | `float` | 权重 (0.0-1.0) |
| `enabled` | `bool` | 是否启用 |
| `stats` | `dict` | 统计信息 |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `analyze(activity, screenshot)` | `AnalyzerResult` | 分析活动 |

#### AnalyzerResult

分析器结果。

| Field | Type | Description |
|-------|------|-------------|
| `score` | `float` | 分析分数 (0.0-1.0) |
| `confidence` | `float` | 置信度 (0.0-1.0) |
| `reason` | `str` | 分析说明 |
| `details` | `dict` | 详细信息 |

#### MetadataAnalyzer

元数据分析器，基于应用名称和窗口标题分析敏感度。

```python
class MetadataAnalyzer(BaseAnalyzer)
```

**Constructor:**

```python
def __init__(
    self,
    weight: float = 0.25,
    enabled: bool = True,
    custom_high_apps: Optional[list[str]] = None,
    custom_high_keywords: Optional[list[str]] = None,
) -> None
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `weight` | `float` | `0.25` | 分析器权重 |
| `enabled` | `bool` | `True` | 是否启用 |
| `custom_high_apps` | `list[str]` | `None` | 自定义高敏感应用 |
| `custom_high_keywords` | `list[str]` | `None` | 自定义高敏感关键词 |

#### VisualAnalyzer

视觉敏感度分析器，分析截图的视觉特征。

```python
class VisualAnalyzer(BaseAnalyzer)
```

**Constructor:**

```python
def __init__(
    self,
    weight: float = 0.35,
    enabled: bool = True,
) -> None
```

**分析维度:**
- 应用类型敏感度 (浏览器、代码编辑器等)
- 图像熵值 (信息复杂度)
- 窗口标题特征

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `stats` | `dict` | 统计信息，包含 `total_analyzed` |

**Usage Example:**

```python
from src.senatus.analyzers import VisualAnalyzer
from PIL import Image

analyzer = VisualAnalyzer(weight=0.35)

result = analyzer.analyze(activity, screenshot=image)
print(f"视觉敏感度: {result.score:.2f}")
print(f"图像熵: {result.details.get('entropy', 0):.2f}")
```

#### FrameDiffAnalyzer

帧差异分析器，分析连续截图帧之间的变化程度。

```python
class FrameDiffAnalyzer(BaseAnalyzer)
```

**Constructor:**

```python
def __init__(
    self,
    weight: float = 0.15,
    enabled: bool = True,
) -> None
```

**分析逻辑:**
- 第一帧: 无对比，返回低分
- 相同帧: 低分 (用户可能在阅读/思考)
- 不同帧: 高分 (用户活跃操作)

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `clear_history()` | `None` | 清除历史帧 |

**Result Details:**

| Key | Type | Description |
|-----|------|-------------|
| `is_first_frame` | `bool` | 是否为第一帧 |
| `diff_level` | `float` | 差异级别 (0.0-1.0) |

#### ContextSwitchAnalyzer

上下文切换分析器，分析用户的应用切换行为模式。

```python
class ContextSwitchAnalyzer(BaseAnalyzer)
```

**Constructor:**

```python
def __init__(
    self,
    weight: float = 0.15,
    context_window_size: int = 10,
    rapid_switch_threshold: float = 5.0,
    enabled: bool = True,
) -> None
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `weight` | `float` | `0.15` | 分析器权重 |
| `context_window_size` | `int` | `10` | 上下文窗口大小 |
| `rapid_switch_threshold` | `float` | `5.0` | 快速切换阈值(秒) |
| `enabled` | `bool` | `True` | 是否启用 |

**检测的切换模式:**

| Pattern | Description | Score |
|---------|-------------|-------|
| `rapid_switch` | 快速应用切换 (< 5秒) | 0.6+ |
| `abab_comparison` | A-B-A-B 对比模式 | 0.5+ |
| `switch_cost` | 深度→浅度工作切换 | 0.6+ |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `set_context_window(activities)` | `None` | 设置上下文窗口 |
| `clear_history()` | `None` | 清除历史 |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `current_history_length` | `int` | 当前历史长度 |
| `switch_pattern_stats` | `dict` | 切换模式统计 |

**Usage Example:**

```python
from src.senatus.analyzers import ContextSwitchAnalyzer

analyzer = ContextSwitchAnalyzer(rapid_switch_threshold=3.0)

# 设置上下文窗口
analyzer.set_context_window(recent_activities)

# 分析当前活动
result = analyzer.analyze(current_activity)

# 检查检测到的模式
patterns = result.details.get("patterns", [])
for p in patterns:
    print(f"模式: {p['type']}, 分数: {p['score']:.2f}")
```

#### UncertaintyAnalyzer

不确定性分析器，评估活动信息的不确定性程度。高不确定性活动更需要 VLM 分析。

```python
class UncertaintyAnalyzer(BaseAnalyzer)
```

**Constructor:**

```python
def __init__(
    self,
    weight: float = 0.10,
    min_duration_threshold: int = 5,
    enabled: bool = True,
) -> None
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `weight` | `float` | `0.10` | 分析器权重 |
| `min_duration_threshold` | `int` | `5` | 最小持续时间阈值(秒) |
| `enabled` | `bool` | `True` | 是否启用 |

**不确定性来源:**

| Source | Description |
|--------|-------------|
| `no_screenshot` | 无截图 |
| `empty_title` | 空标题 |
| `unknown_app` | 未知应用 |
| `short_duration` | 短持续时间 |
| `generic_title` | 通用标题 (如 "Untitled") |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `add_known_app(app_name)` | `None` | 添加已知应用 |
| `add_generic_title(title)` | `None` | 添加通用标题 |
| `compute_activity_uncertainty(activity, has_screenshot)` | `float` | 快速计算不确定性 |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `uncertainty_rate` | `float` | 高不确定性活动比率 |

**Usage Example:**

```python
from src.senatus.analyzers import UncertaintyAnalyzer

analyzer = UncertaintyAnalyzer()

# 添加自定义已知应用
analyzer.add_known_app("mycustomapp")

result = analyzer.analyze(activity, screenshot=None)

# 查看不确定性来源
sources = result.details.get("sources", {})
print(f"不确定性来源: {list(sources.keys())}")
print(f"总不确定性: {result.score:.2f}")
```

---

### 4.8 SenatusEngine Helper Methods

引擎提供的辅助方法用于访问和管理内部组件。

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `get_context_switch_analyzer()` | `Optional[ContextSwitchAnalyzer]` | 获取上下文切换分析器 |
| `set_context_window(activities)` | `None` | 设置上下文窗口 |
| `get_static_frame_filter()` | `Optional[StaticFrameFilter]` | 获取静态帧过滤器 |

**Usage Example:**

```python
from src.senatus import SenatusEngine

engine = SenatusEngine()

# 设置上下文窗口
engine.set_context_window(recent_activities)

# 访问静态帧过滤器
static_filter = engine.get_static_frame_filter()
if static_filter:
    print(f"静态帧率: {static_filter.static_frame_rate:.2%}")
```

---

> 返回: [API Reference Index](../api_reference.md)
