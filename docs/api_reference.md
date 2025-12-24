# MainVisualizer API Reference

> **Version**: 0.1.1
> **Last Updated**: 2025-12-25
> **Architecture**: Progressive Disclosure (渐进式披露)

本文档提供 MainVisualizer 各模块的 API 索引。详细文档请查看各模块的专属文档。

---

## Quick Reference Card

### 常用导入

```python
# Core
from src.core import setup_logging, get_logger
from src.core import DatabaseConnectionError, VLMProviderError

# Ingest - ManicTime
from src.ingest.manictime import ManicTimeDBConnector, ScreenshotLoader, ActivityParser

# Admina - VLM Providers
from src.admina import QwenVLProvider, OllamaProvider

# Senatus - Intelligent Trigger
from src.senatus import SenatusEngine, DecisionType, TriggerDecision

# Senatus - Filters
from src.senatus.filters import (
    WhitelistFilter, BlacklistFilter, TimeRuleFilter, StaticFrameFilter,
    FilterResult, TimeRule,
)

# Senatus - Analyzers
from src.senatus.analyzers import (
    MetadataAnalyzer, VisualAnalyzer, FrameDiffAnalyzer,
    ContextSwitchAnalyzer, UncertaintyAnalyzer, AnalyzerResult,
)
```

### 快速使用模式

```python
# 读取ManicTime数据
with ManicTimeDBConnector(db_path) as db:
    activities = db.query_activities(start, end)

# 调用VLM分析
provider = QwenVLProvider()
result = await provider.analyze_image(image, prompt)
```

---

## Module Index

### 1. Core Module

**Purpose**: 核心基础设施模块，提供异常定义、日志工具和接口规范。

**Key Classes**:

| Class | Quick Link |
|-------|------------|
| `Exceptions` | [api/core.md](#exceptions) |
| `Logger` | [api/core.md](#logger) |
| `Interfaces` | [api/core.md](#interfaces) |

**Full Documentation**: [api/core.md](api/core.md)

### 2. Ingest Module - ManicTime

**Purpose**: ManicTime 数据摄入模块，提供数据库访问、截图加载和活动解析功能。

**Key Classes**:

| Class | Quick Link |
|-------|------------|
| `ManicTimeDBConnector` | [api/ingest_manictime.md](#manictimedbconnector) |
| `ScreenshotLoader` | [api/ingest_manictime.md](#screenshotloader) |
| `ActivityParser` | [api/ingest_manictime.md](#activityparser) |

**Full Documentation**: [api/ingest_manictime.md](api/ingest_manictime.md)

### 3. Admina Module - VLM Providers

**Purpose**: VLM/LLM 调用层，负责与各种 VLM 提供商交互，执行深度视觉分析。

**Key Classes**:

| Class | Quick Link |
|-------|------------|
| `QwenVLProvider` | [api/admina_providers.md](#qwenvlprovider) |
| `OllamaProvider` | [api/admina_providers.md](#ollamaprovider) |
| `IVLMProvider` | [api/admina_providers.md](#ivlmprovider-interface) |
| `HealthCheckResult` | [api/admina_providers.md](#healthcheckresult) |

**Full Documentation**: [api/admina_providers.md](api/admina_providers.md)

### 4. Senatus Module - Intelligent Trigger

**Purpose**: 智能触发模块，负责计算活动的 Taboo Index (ti) 并决定是否触发 VLM 深度分析。采用三级级联推理架构以最小化 VLM 调用成本。

**Key Classes**:

| Class | Quick Link |
|-------|------------|
| `SenatusEngine` | [api/senatus.md](#senatusengine) |
| `TriggerThresholds` | [api/senatus.md](#triggerthresholds) |
| `TabooIndexCalculator` | [api/senatus.md](#tabooindexcalculator) |
| `TriggerManager` | [api/senatus.md](#triggermanager) |

**Filters**:

| Class | Quick Link |
|-------|------------|
| `WhitelistFilter` | [api/senatus.md](#whitelistfilter) |
| `BlacklistFilter` | [api/senatus.md](#blacklistfilter) |
| `TimeRuleFilter` | [api/senatus.md](#timerulefilter) |
| `StaticFrameFilter` | [api/senatus.md](#staticframefilter) |

**Analyzers**:

| Class | Quick Link |
|-------|------------|
| `MetadataAnalyzer` | [api/senatus.md](#metadataanalyzer) |
| `VisualAnalyzer` | [api/senatus.md](#visualanalyzer) |
| `FrameDiffAnalyzer` | [api/senatus.md](#framediffanalyzer) |
| `ContextSwitchAnalyzer` | [api/senatus.md](#contextswitchanalyzer) |
| `UncertaintyAnalyzer` | [api/senatus.md](#uncertaintyanalyzer) |

**Full Documentation**: [api/senatus.md](api/senatus.md)

### 5. Data Models

**Purpose**: 所有数据模型使用 Pydantic 定义，位于 `src/ingest/manictime/models.py`。

**Key Classes**:

| Class | Quick Link |
|-------|------------|
| `ActivityType` | [api/data_models.md](#activitytype) |
| `RawActivity` | [api/data_models.md](#rawactivity) |
| `ApplicationInfo` | [api/data_models.md](#applicationinfo) |
| `ScreenshotMetadata` | [api/data_models.md](#screenshotmetadata) |
| `ActivityEvent` | [api/data_models.md](#activityevent) |

**Full Documentation**: [api/data_models.md](api/data_models.md)

---

## Data Models Overview

所有数据模型使用 Pydantic 定义。详见 [api/data_models.md](api/data_models.md)

| Model | Module | Description |
|-------|--------|-------------|
| `ActivityEvent` | ingest | 系统内部统一活动事件格式 |
| `RawActivity` | ingest | ManicTime 原始活动记录 |
| `ApplicationInfo` | ingest | 应用/窗口信息 |
| `ScreenshotMetadata` | ingest | 截图元信息 |
| `DaySummary` | ingest | 日汇总数据 |
| `VLMRequest` | admina | VLM 请求模型 |
| `VLMResponse` | admina | VLM 响应模型 |
| `AnalysisResult` | admina | 屏幕分析结果 |
| `HealthCheckResult` | admina | VLM 健康检查结果 |

---

## Documentation Structure

```
docs/
├── api_reference.md          # 本索引文档 (L1/L2)
└── api/                      # 详细文档 (L3)
    ├── core.md               # Core 模块
    ├── ingest_manictime.md   # Ingest 模块
    ├── admina_providers.md   # Admina 模块
    ├── senatus.md            # Senatus 模块
    ├── data_models.md        # 数据模型
    └── quick_start.md        # 快速开始
```

---

*Document Version: 0.1.1*
