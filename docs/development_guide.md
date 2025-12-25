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
9. [File Templates](#9-file-templates)
10. [Quick Reference](#10-quick-reference)

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
├── tests/               # Formal test suites (pytest)
├── scripts/             # Development and deployment scripts
│   └── test/            # Development test scripts (standalone, not formal module)
├── docs/                # Documentation
└── examples/            # Usage examples
```

---

## 2. Environment Setup

### 2.1 System Requirements

| Component | Version | Notes |
|-----------|---------|-------|
| OS | Windows 10 | Primary Development Environment |
| Python | 3.11+ | Recommended: 3.11 or 3.12 |
| Memory | 128GB | For screenshot caching and database |
| Disk | 100GB+ free | Y:\ is a local HDD partition, accessible |

### 2.2 Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pydantic | 2.12+ | Data model validation |
| pillow | 12.0+ | Image processing |
| openai | 2.14+ | VLM API calls (OpenAI-compatible) |
| pytest | 9.0+ | Testing framework |
| httpx | 0.28+ | HTTP client |

**Optional**: SQLAlchemy, aiohttp, imagehash

### 2.3 Conda Environment

The project uses conda environment `mv`. On Windows with non-interactive shells, use `conda run`:

```bash
# Run script in conda environment (recommended for Claude Code)
conda run -n mv python scripts/xxx.py

# Verify environment
conda run -n mv python -c "import sys; print(sys.executable)"
```

### 2.4 Environment Variables

`.env` in project root contains API keys and paths:

```bash
MANICTIME_DB_PATH=/path/to/ManicTimeCore.db
MANICTIME_SCREENSHOTS_PATH=/path/to/Screenshots
GEMINI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
```

---

## 3. Architecture Principles

### 3.1 Core Design Patterns

| Pattern | Application | Implementation |
|---------|-------------|----------------|
| **Module Decoupling** | All modules communicate via interfaces | `src/core/interfaces/` |
| **Dependency Injection** | Module dependencies injected at runtime | `src/core/container.py` |
| **Event-Driven** | Inter-module communication | `src/core/event_bus.py` |
| **Plugin Architecture** | Extensible components | Provider/Adapter pattern |
| **Configuration Externalization** | All parameters configurable | YAML + env variables |

### 3.2 Data Flow

```
ManicTime Data
      |
      v
[Ingest] --> ActivityEvent
      |
      v
[Senatus] --> TriggerDecision (ti-based)
      |
      v
[Admina] --> AnalysisResult (conditional VLM)
      |
      v
[Cardina] --> fs1 --> fs2 --> ... --> fn narrative
      |
      v
[Output] --> EMA Interface
```

---

## 4. Code Style and Constraints

### 4.1 Size Limits

All limits below are **MANDATORY**. See [Section 10 Quick Reference](#10-quick-reference) for the complete table.

| Metric | Soft Limit | Hard Limit |
|--------|------------|------------|
| File lines | 500 | 800 |
| Function lines | 30 | 50 |
| Class lines | 200 | 300 |
| Function parameters | 5 | 7 |
| Nesting depth | 3 | 4 |

When approaching limits, split files following these patterns:
- `engine.py` (>500 lines) → `engine_core.py` + `engine_helpers.py`
- `models.py` (>300 lines) → `models_activity.py` + `models_analysis.py`
- Large class (>300 lines) → Extract mixins or delegate to helpers

### 4.2 Mandatory Rules

| Rule ID | Description |
|---------|-------------|
| **CS-1** | All comments and docstrings MUST be in Chinese |
| **CS-2** | NO emojis, emoticons, or special Unicode symbols (use ASCII: PASS/FAIL) |
| **CS-3** | All public functions MUST have type hints |
| **CS-4** | DO NOT use mutable default arguments |
| **CS-5** | DO NOT catch bare `Exception` without re-raising |
| **CS-6** | DO NOT use `print()` for logging (use `logging` module) |
| **CS-7** | DO NOT hardcode configuration values |

### 4.3 Naming Conventions

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

# Private members: leading underscore
class Engine:
    def __init__(self):
        self._internal_state = {}
    
    def _process_internal(self):
        pass
```

### 4.4 Comment Language (Chinese Example)

```python
class SenatusEngine:
    """
    Senatus智能触发引擎
    
    负责分析活动序列，计算taboo index (ti)，决定是否触发VLM深度分析。
    采用三级级联推理架构以最小化VLM调用成本。
    
    Attributes:
        ti_calculator: TI指标计算器实例
        trigger_manager: 触发决策管理器
    """
    
    def process_activity(self, activity: ActivityEvent) -> TriggerDecision:
        """
        处理单个活动事件
        
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
                return TriggerDecision(
                    decision_type=DecisionType.SKIP,
                    reason=f"被过滤器 {filter_.name} 过滤"
                )
        
        # Stage 2: 轻量分类计算ti
        ti_result = self.ti_calculator.calculate(activity)
        
        # Stage 3: 根据ti阈值决定触发行为
        return self.trigger_manager.evaluate_trigger(ti_result)
```

### 4.5 Import Organization

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

# 本地导入 - 当前模块
from .models import TIResult, TriggerDecision

# 类型检查专用导入（避免循环依赖）
if TYPE_CHECKING:
    from src.cardina.models import ActivityEvent
```

### 4.6 Code Smells to Avoid

```python
# BAD: 深层嵌套
def process(items):
    for item in items:
        if item.is_valid:
            for sub in item.children:
                if sub.is_active:
                    # 处理...

# GOOD: 提前返回 + 提取函数
def process(items):
    valid_items = [i for i in items if i.is_valid]
    for item in valid_items:
        self._process_item(item)


# BAD: 可变默认参数
def add_item(item, items=[]):  # 危险！
    items.append(item)

# GOOD: 使用None
def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
```

---

## 5. Module Boundaries

### 5.1 Module Dependency Matrix

| Module | Can Import From | Cannot Import From |
|--------|-----------------|-------------------|
| `core` | (none - base layer) | ingest, senatus, admina, cardina, output |
| `ingest` | core, utils | senatus, admina, cardina, output |
| `senatus` | core, utils | admina, cardina, output |
| `admina` | core, utils | senatus, cardina, output |
| `cardina` | core, utils | senatus, admina, output |
| `output` | core, utils, cardina (interfaces only) | senatus, admina, ingest |
| `pipeline` | core, all modules (via interfaces) | (none) |

```
Import Direction:
core <-- ingest <-- senatus <-- admina <-- cardina <-- output
  ^                                                       |
  |--------------------<-- pipeline <---------------------|
```

### 5.2 Communication Rules

**MUST**: Modules communicate ONLY through:
1. Defined interfaces in `src/core/interfaces/`
2. Event bus for async notifications
3. Dependency injection container

**MUST NOT**: 
- Direct imports between sibling modules
- Shared mutable state between modules
- Circular dependencies

### 5.3 Interface Definition

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

__all__ = ["SenatusEngine", "TIResult", "TriggerDecision"]
```

### 5.4 Cross-Module Communication Examples

```python
# ALLOWED: 通过接口通信
from src.core.interfaces.vlm_provider import VLMProvider

class AdminaManager:
    def __init__(self, provider: VLMProvider):  # 依赖注入
        self._provider = provider

# PROHIBITED: 直接导入具体实现
from src.admina.providers.gemini_provider import GeminiProvider  # BAD
from src.senatus.analyzers.visual_analyzer import VisualAnalyzer  # BAD
```

### 5.5 Event Bus Usage

```python
from src.core.event_bus import get_event_bus

event_bus = get_event_bus()

# 发布事件
await event_bus.publish("NEW_ACTIVITIES", activities)

# 订阅事件
@event_bus.subscribe("VLM_ANALYSIS_COMPLETED")
async def handle_analysis_completed(result: AnalysisResult):
    await self._store_result(result)
```

---

## 6. Development Workflow

### 6.1 Before Coding (MUST)

1. **Clarify Requirements**: Ask clarifying questions if the task is ambiguous
2. **Review Architecture**: Read relevant sections of `UW_MainVisualizer.md`
3. **Check Existing APIs**: Review `docs/api_reference.md` - reuse existing functions instead of duplicating
4. **Plan Approach**: Draft implementation plan for complex tasks

> **IMPORTANT**: Before implementing new functionality:
> - Check if it already exists in `docs/api_reference.md`
> - Only create new functions when no existing API meets the need
> - Prefer extending existing classes over creating new ones

### 6.2 Incremental Development

For complex features:

```
1. Define interface/protocol first
2. Create data models (Pydantic)
3. Implement skeleton with NotImplementedError
4. Add unit tests for expected behavior
5. Implement one method at a time
6. Run tests after each method
7. Refactor if needed
```

### 6.3 Verification Checklist

Before submitting any code, verify ALL items:

| Category | Check Item |
|----------|------------|
| **Language** | All comments are in Chinese |
| **Style** | No emojis anywhere in code/comments/logs |
| **Size** | File under 800 lines, functions under 50 lines |
| **Types** | Type hints on all public APIs |
| **Docs** | Docstrings on all public classes and functions |
| **Architecture** | No direct cross-module imports |
| **Quality** | Error handling is appropriate |
| **Testing** | Tests are written or updated |
| **Design** | No design downgrade for error bypass |

### 6.4 API Documentation Requirements

After completing a module, update `docs/api_reference.md` with:
1. Module Overview
2. Public Classes (constructor signatures)
3. Public Methods (signatures with types)
4. Data Models (Pydantic models with field descriptions)
5. Usage Examples

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

Suspected cause: The upstream data source might be returning None unexpectedly.

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

### 7.3 Error Handling Pattern

```python
async def analyze_screenshot(self, screenshot: Image) -> AnalysisResult:
    """
    分析截图内容
    
    Raises:
        VLMProviderError: VLM调用失败时抛出
        InvalidImageError: 图像格式无效时抛出
    """
    if screenshot is None:
        raise InvalidImageError("截图不能为空")
    
    try:
        response = await self._provider.analyze(screenshot)
    except ProviderConnectionError as e:
        logger.error(f"VLM连接失败: {e}", exc_info=True)
        raise VLMProviderError(f"无法连接到VLM服务: {e}") from e
    except ProviderRateLimitError as e:
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

### 8.2 Test Organization

| Directory | Runner | Purpose | Dependencies |
|-----------|--------|---------|--------------|
| `tests/` | pytest | CI/CD, formal testing | Mock/fixtures |
| `scripts/test/` | Direct python | Development, debugging | Real data/APIs |

```
tests/
├── unit/
│   ├── test_senatus/
│   │   ├── test_ti_calculator.py
│   │   └── test_engine.py
│   └── ...
├── integration/
│   └── test_pipeline.py
└── e2e/
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
    
    def test_calculate_with_invalid_activity_raises_error(self):
        """测试无效活动数据抛出异常"""
        pass
```

### 8.4 Fixtures

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

## 9. File Templates

### 9.1 Module File Template

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

### 9.2 Test File Template

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

### 9.3 Interface Definition Template

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

## 10. Quick Reference

### 10.1 Size Limits (Authoritative)

| Metric | Soft Limit | Hard Limit |
|--------|------------|------------|
| File lines | 500 | 800 |
| Function lines | 30 | 50 |
| Class lines | 200 | 300 |
| Function parameters | 5 | 7 |
| Nesting depth | 3 | 4 |

### 10.2 Module Import Diagram

```
core <-- ingest <-- senatus <-- admina <-- cardina <-- output
  ^                                                       |
  |--------------------<-- pipeline <---------------------|
```

### 10.3 Common Commands

```bash
# Run in conda environment
conda run -n mv python scripts/xxx.py

# Run tests
pytest tests/ -v

# Type checking
mypy src/

# Linting & Format
ruff check src/
ruff format src/
```

---

*Last Updated: 2025-12-25*
*Document Version: 2.0*

### Changelog
- v2.0 (2025-12-25): Consolidated duplicate content, unified size limits, reorganized structure
- v1.1 (2025-12-25): Added Windows conda experience, scripts/test directory notes
- v1.0 (2025-12): Initial version