# MainVisualizer Development Guide for AI-Assisted Coding

> **Purpose**: This document provides mandatory guidelines for AI coding assistants (Claude Code) working on the MainVisualizer project. All AI-generated code MUST adhere to these rules.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Environment Setup](#2-environment-setup)
3. [Architecture Principles](#3-architecture-principles)
4. [Code Style and Constraints](#4-code-style-and-constraints)
5. [Module Boundaries](#5-module-boundaries)
6. [Development Workflow](#6-development-workflow)
7. [Error Handling Protocol](#7-error-handling-protocol)
8. [Testing Requirements](#8-testing-requirements)
9. [Prohibited Behaviors](#9-prohibited-behaviors)
10. [File Templates](#10-file-templates)

---

## 1. Project Overview

### 1.1 What is MainVisualizer?

MainVisualizer is a screen activity analysis system that processes ManicTime data through a cascaded reasoning architecture. The system consists of four core modules:

| Module | Responsibility |
|--------|----------------|
| **Ingest** | Read and parse ManicTime SQLite database and screenshots |
| **Senatus** | Calculate taboo index (ti) and make VLM trigger decisions |
| **Admina** | Execute VLM/LLM API calls for deep visual analysis |
| **Cardina** | Aggregate data across fs1-fs5 layers and generate narratives |

### 1.2 Technology Stack

- **Language**: Python 3.11+
- **Package Manager**: conda + pip
- **Primary Libraries**: Pydantic, SQLAlchemy, aiohttp, Pillow
- **VLM Providers**: Gemini, Claude, OpenAI, Qwen (DashScope)
- **Storage**: SQLite (Phase 1), PostgreSQL/TimescaleDB (Phase 2)

### 1.3 Directory Structure

```
MainVisualizer/
├── config/              # Configuration files (YAML)
├── src/                 # Source code
│   ├── core/            # Core infrastructure (DI, events, interfaces)
│   ├── ingest/          # Data ingestion layer
│   ├── senatus/         # Intelligent trigger module
│   ├── admina/          # VLM/LLM call layer
│   ├── cardina/         # Data aggregation layer
│   ├── storage/         # Storage backends
│   ├── output/          # EMA output interface
│   ├── pipeline/        # Processing pipeline orchestration
│   └── utils/           # Utility functions
├── tests/               # Test suites
├── scripts/             # Development and deployment scripts
├── docs/                # Documentation
└── examples/            # Usage examples
```

---

## 2. Environment Setup

### 2.1 Conda Environment

The project uses a conda environment named `mv`. Always activate this environment before any development work.

```bash
# Activate environment
conda activate mv

# Verify activation
which python  # Should point to conda env
```

### 2.2 Required Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Type checking
mypy src/

# Linting
ruff check src/

# Format code
ruff format src/
```

### 2.3 Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
MANICTIME_DB_PATH=/path/to/ManicTimeCore.db
MANICTIME_SCREENSHOTS_PATH=/path/to/Screenshots
GEMINI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
```

---

## 3. Architecture Principles

### 3.1 Core Design Patterns

The following patterns are MANDATORY throughout the codebase:

| Pattern | Application | Implementation |
|---------|-------------|----------------|
| **Module Decoupling** | All modules communicate via interfaces | Define abstract base classes in `src/core/interfaces/` |
| **Dependency Injection** | Module dependencies injected at runtime | Use `src/core/container.py` |
| **Event-Driven** | Inter-module communication | Publish-subscribe via `src/core/event_bus.py` |
| **Plugin Architecture** | Extensible components | Provider/Adapter pattern |
| **Configuration Externalization** | All parameters configurable | YAML files + environment variables |

### 3.2 Module Communication Rules

**MUST**: Modules communicate ONLY through:
1. Defined interfaces in `src/core/interfaces/`
2. Event bus for async notifications
3. Dependency injection container

**MUST NOT**: 
- Direct imports between sibling modules (e.g., senatus importing from cardina)
- Shared mutable state between modules
- Circular dependencies

### 3.3 Data Flow

```
ManicTime Data
      |
      v
[Ingest] --> ActivityEvent
      |
      v
[Senatus] --> TriggerDecision
      |
      +--> ti > 0.8: Immediate VLM
      +--> 0.5 < ti <= 0.8: Batch VLM
      +--> ti <= 0.5: Skip VLM
      |
      v
[Admina] --> AnalysisResult (conditional)
      |
      v
[Cardina] --> fs1 --> fs2 --> ... --> fn narrative
      |
      v
[Output] --> EMA Interface
```

---

## 4. Code Style and Constraints

### 4.1 Mandatory Rules (MUST)

| Rule ID | Description |
|---------|-------------|
| **CS-1** | All code comments and docstrings MUST be written in Chinese |
| **CS-2** | NO emojis or emoticons anywhere in code, comments, or logs |
| **CS-3** | Single file MUST NOT exceed 500 lines (soft limit) or 800 lines (hard limit) |
| **CS-4** | Single function MUST NOT exceed 50 lines (excluding docstrings) |
| **CS-5** | Single class MUST NOT exceed 300 lines |
| **CS-6** | Maximum function parameters: 7 (use dataclass/TypedDict for more) |
| **CS-7** | Maximum nesting depth: 4 levels |
| **CS-8** | All public functions MUST have type hints |

### 4.2 Naming Conventions

```python
# Classes: PascalCase
class TabooIndexCalculator:
    pass

# Functions and variables: snake_case
def calculate_ti_score(activity: ActivityEvent) -> float:
    result_value = 0.0
    return result_value

# Constants: UPPER_SNAKE_CASE
DEFAULT_TI_THRESHOLD = 0.8
MAX_BATCH_SIZE = 100

# Private members: leading underscore
class Engine:
    def __init__(self):
        self._internal_state = {}
    
    def _process_internal(self):
        pass

# Module-level private: leading underscore
_module_cache = {}
```

### 4.3 Comment Language (Chinese)

All comments MUST be in Chinese:

```python
class SenatusEngine:
    """
    Senatus智能触发引擎
    
    负责分析活动序列，计算taboo index (ti)，决定是否触发VLM深度分析。
    采用三级级联推理架构以最小化VLM调用成本。
    
    Attributes:
        ti_calculator: TI指标计算器实例
        trigger_manager: 触发决策管理器
        filters: Stage 1规则过滤器列表
        classifier: Stage 2轻量分类器
    """
    
    def process_activity(self, activity: ActivityEvent) -> TriggerDecision:
        """
        处理单个活动事件
        
        执行三级级联推理：
        1. Stage 1: 规则过滤 - 过滤90%静态/无关帧
        2. Stage 2: 轻量分类 - 计算ti和置信度
        3. Stage 3: 触发决策 - 根据阈值决定VLM调用
        
        Args:
            activity: 待处理的活动事件
            
        Returns:
            TriggerDecision: 包含触发类型和相关元数据的决策对象
            
        Raises:
            InvalidActivityError: 活动数据格式无效时抛出
        """
        # 检查活动是否有效
        if not self._validate_activity(activity):
            raise InvalidActivityError(f"无效的活动数据: {activity.event_id}")
        
        # Stage 1: 规则过滤
        for filter_ in self.filters:
            if filter_.should_skip(activity):
                # 活动被过滤，直接返回跳过决策
                return TriggerDecision(
                    decision_type=DecisionType.SKIP,
                    reason=f"被过滤器 {filter_.name} 过滤"
                )
        
        # Stage 2: 轻量分类计算ti
        ti_result = self.ti_calculator.calculate(activity)
        
        # Stage 3: 根据ti阈值决定触发行为
        return self.trigger_manager.evaluate_trigger(ti_result)
```

### 4.4 Import Organization

```python
# 标准库导入
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

# 第三方库导入
from pydantic import BaseModel, Field
from sqlalchemy import select

# 本地导入 - 核心模块
from src.core.event_bus import EventBus
from src.core.exceptions import MainVisualizerError
from src.core.interfaces.base_module import BaseModule

# 本地导入 - 当前模块
from .models import TIResult, TriggerDecision

# 类型检查专用导入（避免循环依赖）
if TYPE_CHECKING:
    from src.cardina.models import ActivityEvent
```

### 4.5 File Size Management

When a file approaches size limits, split it following these patterns:

| Original File | Split Strategy |
|---------------|----------------|
| `engine.py` (>500 lines) | Extract to `engine_core.py` + `engine_helpers.py` |
| `models.py` (>300 lines) | Split by domain: `models_activity.py`, `models_analysis.py` |
| Large class (>300 lines) | Extract mixins or delegate to helper classes |

**Example Split**:

```python
# Before: senatus/engine.py (600 lines)

# After:
# senatus/engine.py (200 lines) - Main engine class
# senatus/engine_cascade.py (150 lines) - Cascade logic
# senatus/engine_batch.py (150 lines) - Batch processing
# senatus/engine_utils.py (100 lines) - Helper functions
```

---

## 5. Module Boundaries

### 5.1 Interface Definitions

Each module MUST define its public interface in `__init__.py`:

```python
# src/senatus/__init__.py
"""
Senatus智能触发模块

公开接口:
- SenatusEngine: 主引擎类
- TIResult: TI计算结果数据类
- TriggerDecision: 触发决策数据类
"""

from .engine import SenatusEngine
from .models.ti_result import TIResult
from .models.trigger_decision import TriggerDecision

__all__ = [
    "SenatusEngine",
    "TIResult", 
    "TriggerDecision",
]
```

### 5.2 Cross-Module Communication

**Allowed**:
```python
# 通过接口通信
from src.core.interfaces.vlm_provider import VLMProvider

class AdminaManager:
    def __init__(self, provider: VLMProvider):
        # 依赖注入，接受接口类型
        self._provider = provider
```

**Prohibited**:
```python
# 禁止直接导入具体实现
from src.admina.providers.gemini_provider import GeminiProvider  # BAD

# 禁止跨模块直接访问内部类
from src.senatus.analyzers.visual_analyzer import VisualAnalyzer  # BAD
```

### 5.3 Module Dependency Matrix

| Module | Can Import From | Cannot Import From |
|--------|-----------------|-------------------|
| `core` | (none - base layer) | ingest, senatus, admina, cardina, output |
| `ingest` | core, utils | senatus, admina, cardina, output |
| `senatus` | core, utils | admina, cardina, output |
| `admina` | core, utils | senatus, cardina, output |
| `cardina` | core, utils | senatus, admina, output |
| `output` | core, utils, cardina (interfaces only) | senatus, admina, ingest |
| `pipeline` | core, all modules (via interfaces) | (none) |

### 5.4 Event Bus Communication

For cross-module notifications, use the event bus:

```python
# 发布事件
from src.core.event_bus import get_event_bus

event_bus = get_event_bus()
await event_bus.publish("NEW_ACTIVITIES", activities)

# 订阅事件
@event_bus.subscribe("VLM_ANALYSIS_COMPLETED")
async def handle_analysis_completed(result: AnalysisResult):
    # 处理VLM分析完成事件
    await self._store_result(result)
```

---

## 6. Development Workflow

### 6.1 Before Coding (MUST)

1. **Clarify Requirements**: Ask clarifying questions if the task is ambiguous
2. **Review Architecture**: Read relevant sections of `UW_MainVisualizer.md` and `UW_MainVisualizer_InitialValidation.md`
3. **Plan Approach**: Draft implementation plan for complex tasks
4. **Check Existing Code**: Search for similar patterns in the codebase

### 6.2 Implementation Checklist

Before writing code, verify:

- [ ] Target file exists and location is correct
- [ ] File will not exceed size limits after changes
- [ ] Required interfaces are defined
- [ ] No circular dependencies will be introduced
- [ ] Test file location is identified

### 6.3 Code Review Checklist

After writing code, verify:

- [ ] All comments are in Chinese
- [ ] No emojis in code or comments
- [ ] File size within limits
- [ ] Function size within limits
- [ ] Type hints on all public functions
- [ ] Docstrings on all public classes and functions
- [ ] No direct cross-module imports
- [ ] Error handling is appropriate
- [ ] Tests are written or updated

### 6.4 Incremental Development

For complex features, follow this sequence:

```
1. Define interface/protocol first
2. Create data models (Pydantic)
3. Implement skeleton with NotImplementedError
4. Add unit tests for expected behavior
5. Implement one method at a time
6. Run tests after each method
7. Refactor if needed
```

---

## 7. Error Handling Protocol

### 7.1 When AI Encounters Repeated Errors

**CRITICAL RULE**: When facing the same error 3+ times without resolution:

1. **STOP** attempting further fixes
2. **DO NOT** downgrade or simplify the design
3. **DO NOT** remove features to bypass the error
4. **ASK** the user for guidance with:
   - Clear description of the error
   - What approaches have been tried
   - What the suspected root cause might be

**Example Response**:

```
I've encountered the same error 3 times while implementing the ti_calculator module:

Error: TypeError: 'NoneType' object is not iterable at line 45

Attempted solutions:
1. Added null check before iteration - still fails
2. Changed return type to Optional[List] - same error
3. Added default empty list - error persists

Suspected cause: The upstream data source might be returning None in an unexpected case.

Would you like me to:
A) Add more detailed logging to identify the exact data causing the issue?
B) Review the upstream data provider implementation?
C) Take a different approach to this functionality?
```

### 7.2 Exception Hierarchy

```python
# src/core/exceptions.py

class MainVisualizerError(Exception):
    """所有MainVisualizer异常的基类"""
    pass

class ConfigurationError(MainVisualizerError):
    """配置相关错误"""
    pass

class DataIngestionError(MainVisualizerError):
    """数据摄入层错误"""
    pass

class SenatusError(MainVisualizerError):
    """Senatus模块错误"""
    pass

class VLMProviderError(MainVisualizerError):
    """VLM提供商调用错误"""
    pass

class StorageError(MainVisualizerError):
    """存储层错误"""
    pass
```

### 7.3 Error Handling Patterns

```python
# 正确的错误处理模式
async def analyze_screenshot(self, screenshot: Image) -> AnalysisResult:
    """
    分析截图内容
    
    Raises:
        VLMProviderError: VLM调用失败时抛出
        InvalidImageError: 图像格式无效时抛出
    """
    # 验证输入
    if screenshot is None:
        raise InvalidImageError("截图不能为空")
    
    try:
        # 调用VLM
        response = await self._provider.analyze(screenshot)
    except ProviderConnectionError as e:
        # 记录详细错误信息
        logger.error(f"VLM连接失败: {e}", exc_info=True)
        # 包装并重新抛出
        raise VLMProviderError(f"无法连接到VLM服务: {e}") from e
    except ProviderRateLimitError as e:
        # 特定错误的特定处理
        logger.warning(f"VLM速率限制: {e}")
        raise
    
    return self._parse_response(response)
```

---

## 8. Testing Requirements

### 8.1 Test Coverage

| Component Type | Minimum Coverage |
|---------------|------------------|
| Core modules (core/) | 90% |
| Business logic (senatus/, cardina/) | 80% |
| Providers (admina/providers/) | 70% |
| Utils | 80% |

### 8.2 Test File Organization

```
tests/
├── unit/                    # 单元测试
│   ├── test_senatus/
│   │   ├── test_ti_calculator.py
│   │   └── test_engine.py
│   └── ...
├── integration/             # 集成测试
│   ├── test_pipeline.py
│   └── ...
└── e2e/                     # 端到端测试
    └── test_full_workflow.py
```

### 8.3 Test Naming Convention

```python
# 测试文件: test_<module>.py
# 测试类: Test<ClassName>
# 测试方法: test_<method>_<scenario>_<expected_result>

class TestTabooIndexCalculator:
    def test_calculate_with_high_visual_sensitivity_returns_high_ti(self):
        """测试高视觉敏感度活动返回高ti值"""
        pass
    
    def test_calculate_with_static_frame_returns_low_ti(self):
        """测试静态帧返回低ti值"""
        pass
    
    def test_calculate_with_invalid_activity_raises_error(self):
        """测试无效活动数据抛出异常"""
        pass
```

### 8.4 Mock and Fixture Usage

```python
# tests/conftest.py

import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_vlm_provider():
    """创建模拟VLM提供商"""
    provider = AsyncMock()
    provider.analyze.return_value = {
        "content_type": "code_editing",
        "confidence": 0.95
    }
    return provider

@pytest.fixture
def sample_activity():
    """创建示例活动事件"""
    return ActivityEvent(
        event_id="test-uuid-001",
        timestamp=datetime.now(),
        application="Visual Studio Code",
        window_title="main.py - Project"
    )
```

---

## 9. Prohibited Behaviors

### 9.1 Absolute Prohibitions (DO NOT)

| ID | Prohibition | Reason |
|----|-------------|--------|
| **P-1** | DO NOT use emojis or emoticons anywhere | Professional codebase standard |
| **P-2** | DO NOT downgrade/simplify design when errors occur | Preserves architectural integrity |
| **P-3** | DO NOT create files exceeding 800 lines | Maintainability |
| **P-4** | DO NOT create functions exceeding 50 lines | Readability and testability |
| **P-5** | DO NOT import directly between sibling modules | Module decoupling |
| **P-6** | DO NOT use mutable default arguments | Python gotcha |
| **P-7** | DO NOT catch bare `Exception` without re-raising | Error handling clarity |
| **P-8** | DO NOT use `print()` for logging | Use proper logging |
| **P-9** | DO NOT hardcode configuration values | Use config files |
| **P-10** | DO NOT write comments in English | Project standard (Chinese) |

### 9.2 Code Smells to Avoid

```python
# BAD: 巨型函数
def process_everything(data):
    # 200行代码...
    pass

# GOOD: 拆分为小函数
def process_everything(data):
    validated = self._validate_data(data)
    transformed = self._transform_data(validated)
    return self._finalize_result(transformed)


# BAD: 深层嵌套
def process(items):
    for item in items:
        if item.is_valid:
            for sub in item.children:
                if sub.is_active:
                    for detail in sub.details:
                        if detail.value > 0:
                            # 处理...

# GOOD: 提前返回 + 提取函数
def process(items):
    valid_items = [i for i in items if i.is_valid]
    for item in valid_items:
        self._process_item(item)

def _process_item(self, item):
    active_children = [c for c in item.children if c.is_active]
    for child in active_children:
        self._process_child(child)


# BAD: 可变默认参数
def add_item(item, items=[]):  # 危险！
    items.append(item)
    return items

# GOOD: 使用None
def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```

### 9.3 Anti-Patterns in Module Design

```python
# BAD: 上帝类
class MainVisualizerDoEverything:
    def ingest_data(self): ...
    def calculate_ti(self): ...
    def call_vlm(self): ...
    def aggregate_data(self): ...
    def generate_narrative(self): ...
    def output_to_ema(self): ...

# GOOD: 单一职责
class IngestManager:
    def ingest_data(self): ...

class SenatusEngine:
    def calculate_ti(self): ...

class AdminaManager:
    def call_vlm(self): ...
```

---

## 10. File Templates

### 10.1 Module File Template

```python
"""
<模块名称>

<模块的详细描述，说明其职责和在系统中的位置>

Example:
    <使用示例>
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from src.core.exceptions import MainVisualizerError

if TYPE_CHECKING:
    from <type_imports>

logger = logging.getLogger(__name__)


class <ClassName>:
    """
    <类描述>
    
    Attributes:
        <属性说明>
    """
    
    def __init__(self, <params>) -> None:
        """
        初始化<类名>
        
        Args:
            <参数说明>
        """
        self._attribute = value
    
    def public_method(self, param: Type) -> ReturnType:
        """
        <方法描述>
        
        Args:
            param: <参数描述>
            
        Returns:
            <返回值描述>
            
        Raises:
            <可能的异常>
        """
        pass
    
    def _private_method(self) -> None:
        """<私有方法描述>"""
        pass
```

### 10.2 Test File Template

```python
"""
<模块名>测试

测试<模块功能>的各种场景
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.<module> import <Class>
from src.core.exceptions import <Exceptions>


class Test<ClassName>:
    """<类名>测试套件"""
    
    @pytest.fixture
    def instance(self):
        """创建测试实例"""
        return <Class>()
    
    @pytest.fixture
    def mock_dependency(self):
        """创建模拟依赖"""
        return MagicMock()
    
    def test_<method>_with_valid_input_returns_expected(self, instance):
        """测试有效输入返回预期结果"""
        # Arrange
        input_data = ...
        
        # Act
        result = instance.<method>(input_data)
        
        # Assert
        assert result == expected
    
    def test_<method>_with_invalid_input_raises_error(self, instance):
        """测试无效输入抛出异常"""
        with pytest.raises(<ExpectedException>):
            instance.<method>(invalid_input)
    
    @pytest.mark.asyncio
    async def test_<async_method>_success(self, instance, mock_dependency):
        """测试异步方法成功场景"""
        # Arrange
        mock_dependency.some_method.return_value = expected_value
        
        # Act
        result = await instance.<async_method>()
        
        # Assert
        assert result is not None
        mock_dependency.some_method.assert_called_once()
```

### 10.3 Interface Definition Template

```python
"""
<接口名>接口定义

定义<功能域>的抽象接口，所有具体实现必须遵循此接口。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class <InterfaceName>(ABC, Generic[T]):
    """
    <接口描述>
    
    所有<功能>实现必须继承此接口。
    """
    
    @abstractmethod
    def method_one(self, param: Type) -> ReturnType:
        """
        <方法描述>
        
        Args:
            param: <参数描述>
            
        Returns:
            <返回值描述>
        """
        raise NotImplementedError
    
    @abstractmethod
    async def async_method(self) -> T:
        """
        <异步方法描述>
        
        Returns:
            <返回值描述>
        """
        raise NotImplementedError
```

---

## Appendix A: Quick Reference Card

### File Size Limits

| Metric | Soft Limit | Hard Limit |
|--------|------------|------------|
| File lines | 500 | 800 |
| Function lines | 30 | 50 |
| Class lines | 200 | 300 |
| Function parameters | 5 | 7 |
| Nesting depth | 3 | 4 |

### Module Import Rules

```
core <-- ingest <-- senatus <-- admina <-- cardina <-- output
  ^                                                       |
  |--------------------<-- pipeline <---------------------|
```

### ti Threshold Quick Reference

| ti Value | Action |
|----------|--------|
| > 0.8 | Immediate VLM analysis |
| 0.5 - 0.8 | Batch VLM analysis |
| 0.3 - 0.5 | Lightweight classification only |
| <= 0.3 | Skip analysis |

---

## Appendix B: Checklist for AI Assistant

Before submitting any code, verify:

```
[ ] Comments are in Chinese
[ ] No emojis anywhere
[ ] File under 800 lines
[ ] Functions under 50 lines
[ ] No cross-module direct imports
[ ] Type hints on public APIs
[ ] Docstrings present
[ ] Error handling appropriate
[ ] Tests written/updated
[ ] No design downgrade for error bypass
```

---

*Last Updated: 2025-01*
*Document Version: 1.0*
