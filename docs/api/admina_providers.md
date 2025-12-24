# Admina Module - VLM Providers API Reference

> 本文档是 MainVisualizer API Reference 的一部分
> 返回: [API Reference Index](../api_reference.md)

---


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

### 3.4 HealthCheckResult (`src/core/interfaces/vlm_provider.py`)

健康检查结果数据类。

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `is_healthy` | `bool` | - | 是否健康 |
| `message` | `str` | `""` | 状态信息 |
| `latency_ms` | `Optional[float]` | `None` | 响应延迟(毫秒) |
| `available_models` | `list[str]` | `[]` | 可用模型列表 |

**Usage Example:**

```python
from src.admina import QwenVLProvider
import asyncio

async def check_health():
    provider = QwenVLProvider()
    health = await provider.health_check()

    if health.is_healthy:
        print(f"服务正常: {health.message}")
        print(f"响应延迟: {health.latency_ms:.2f}ms")
        print(f"可用模型: {', '.join(health.available_models)}")
    else:
        print(f"服务异常: {health.message}")

asyncio.run(check_health())
```

### 3.5 VLM Data Models

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


---

> 返回: [API Reference Index](../api_reference.md)
