---
name: api-doc-writer
description: Write API documentation for new modules following the Progressive Disclosure architecture. Use when completing a new module development and need to add API documentation. Triggers on new module documentation, API doc writing, or when creating L3 detailed documentation.
---

# API Documentation Writer Skill

> **Purpose**: 为新模块/API 撰写文档，遵循渐进式披露架构
> **Trigger**: 当完成新模块开发后需要添加 API 文档时使用

---

## 文档架构概览

```
docs/
├── api_reference.md          # L1/L2: 索引 + 快速参考 (~150行)
└── api/                      # L3: 详细文档
    ├── core.md               # 1. Core Module (105行)
    ├── ingest_manictime.md   # 2. Ingest Module (178行)
    ├── admina_providers.md   # 3. Admina Module (154行)
    ├── senatus.md            # 4. Senatus Module (248行)
    ├── data_models.md        # 5. Data Models (122行)
    ├── quick_start.md        # 快速开始示例 (55行)
    └── <new_module>.md       # 新模块文档
```

**当前模块编号**: 1-Core, 2-Ingest, 3-Admina, 4-Senatus, 5-DataModels
**下一个模块编号**: 6

---

## Step 1: 创建 L3 详细文档

在 `docs/api/` 创建新模块文档。**必须严格遵循以下格式**：

### 文档模板

```markdown
# <Module Name> API Reference

> 本文档是 MainVisualizer API Reference 的一部分
> 返回: [API Reference Index](../api_reference.md)

---


<一句话模块描述>

### N.1 <主类名>

\`\`\`python
class <ClassName>
\`\`\`

<类描述>

**Constructor:**

\`\`\`python
def __init__(
    self,
    param1: Type1,
    param2: Type2 = default_value,
) -> None
\`\`\`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `param1` | `Type1` | - | 参数说明 |
| `param2` | `Type2` | `default_value` | 参数说明 |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `method_name(args)` | `ReturnType` | 方法说明 |

**Usage Example:**

\`\`\`python
from src.<module_path> import <ClassName>

# 具体示例代码
instance = <ClassName>(param1=value)
result = instance.method_name(args)
\`\`\`

### N.2 <次要类>

...

---


---

> 返回: [API Reference Index](../api_reference.md)
```

### 格式要点

1. **节编号**: 使用 `N.1`, `N.2` 格式，N = 模块序号
2. **表格列对齐**: Parameter/Type/Default/Description 或 Method/Returns/Description
3. **代码块**: 必须指定语言 `python`
4. **空行规则**:
   - `---` 前后各一个空行
   - 节标题 `###` 前后各一个空行
5. **导航**: 文档首尾都有返回索引的链接

---

## Step 2: 更新 L1/L2 索引

编辑 `docs/api_reference.md`，按顺序添加以下内容：

### 2.1 Module Index 添加新节

在 `## Module Index` 部分末尾、`## Data Models Overview` 之前添加：

```markdown
### N. <Module Name>

**Purpose**: <模块用途描述>

**Key Classes**:

| Class | Quick Link |
|-------|------------|
| `ClassName1` | [api/<module>.md](#classname1) |
| `ClassName2` | [api/<module>.md](#classname2) |

**Full Documentation**: [api/<module>.md](api/<module>.md)
```

### 2.2 Quick Reference Card 更新

如有常用导入，在 `### 常用导入` 代码块中添加：

```python
# <Module Name>
from src.<module_path> import <Class1>, <Class2>
```

如有快速使用模式，在 `### 快速使用模式` 代码块中添加示例。

### 2.3 Data Models Overview 更新

如模块包含新数据模型，在表格中添加：

```markdown
| `NewModelName` | <module> | 模型描述 |
```

### 2.4 Documentation Structure 更新

在目录结构中添加：

```markdown
    ├── <new_module>.md       # <Module Name>
```

---

## 实际示例：参照 Senatus 模块

### L3 文档结构 (docs/api/senatus.md)

```
# Senatus Module - Intelligent Trigger API Reference
> 导航头部

---

模块描述

### 4.1 SenatusEngine         ← 主类
    Constructor + Methods + Usage Example

### 4.2 TriggerThresholds     ← 配置类
    字段表格

### 4.3 TabooIndexCalculator  ← 组件类
    Methods

### 4.4 TriggerManager        ← 组件类
    Methods

### 4.5 Senatus Data Models   ← 数据模型
    TILevel, DecisionType, TIResult, TriggerDecision

### 4.6 Filters               ← 过滤器
    WhitelistFilter

### 4.7 Analyzers             ← 分析器
    MetadataAnalyzer

---
> 导航尾部
```

### L1/L2 索引条目 (docs/api_reference.md)

```markdown
### 4. Senatus Module - Intelligent Trigger

**Purpose**: 智能触发模块，负责计算活动的 Taboo Index (ti) 并决定是否触发 VLM 深度分析。采用三级级联推理架构以最小化 VLM 调用成本。

**Key Classes**:

| Class | Quick Link |
|-------|------------|
| `SenatusEngine` | [api/senatus.md](#senatusengine) |
| `TriggerThresholds` | [api/senatus.md](#triggerthresholds) |
| `TabooIndexCalculator` | [api/senatus.md](#tabooindexcalculator) |
| `TriggerManager` | [api/senatus.md](#triggermanager) |
| `WhitelistFilter` | [api/senatus.md](#whitelistfilter) |

**Full Documentation**: [api/senatus.md](api/senatus.md)
```

---

## 命名规范

### 文件命名

| 模块类型 | 文件名格式 | 示例 |
|----------|------------|------|
| 子模块 | `<parent>_<child>.md` | `ingest_manictime.md` |
| 顶级模块 | `<module>.md` | `core.md`, `senatus.md` |
| 提供商类 | `<module>_providers.md` | `admina_providers.md` |

### 类文档顺序

1. **主引擎/管理类** (如 SenatusEngine, ManicTimeDBConnector)
2. **配置类** (如 TriggerThresholds)
3. **组件类** (如 TabooIndexCalculator, TriggerManager)
4. **数据模型** (如 TIResult, TriggerDecision)
5. **辅助类** (如 Filters, Analyzers)

---

## 检查清单

完成文档后验证：

- [ ] **L3 详细文档**
  - [ ] 文件创建于 `docs/api/<module>.md`
  - [ ] 包含导航头部和尾部
  - [ ] 节编号正确 (N.1, N.2...)
  - [ ] 所有类都有 Constructor 和 Methods
  - [ ] 包含至少一个 Usage Example

- [ ] **L1/L2 索引更新**
  - [ ] Module Index 添加新节
  - [ ] Key Classes 表格完整
  - [ ] Full Documentation 链接正确
  - [ ] Quick Reference Card 更新 (如需)
  - [ ] Data Models Overview 更新 (如需)
  - [ ] Documentation Structure 更新

- [ ] **链接验证**
  - [ ] 所有 `[text](path)` 链接可访问
  - [ ] Quick Link 锚点格式正确 (#classname 小写)

- [ ] **格式验证**
  - [ ] 表格对齐
  - [ ] 代码块有语言标识
  - [ ] 中英文间有空格

---

## 版本号更新

如果是重要更新，修改 `api_reference.md` 末尾的版本号：

```markdown
*Document Version: 0.1.0*  →  *Document Version: 0.2.0*
```

同时更新文档头部的 Last Updated 日期。

---

## 相关文档

- 索引: `docs/api_reference.md`
- 详细文档: `docs/api/*.md`
- 开发指南: `docs/development_guide.md`
- 架构文档: `docs/UW_MainVisualizer_InitialValidation.md`
