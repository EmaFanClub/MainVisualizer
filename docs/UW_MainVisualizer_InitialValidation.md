# MainVisualizer 初期验证实验架构设计报告

## 一、架构设计原则

### 1.1 核心设计理念

本架构遵循以下设计原则，确保初期验证的可行性和后期扩展的流畅性：

| 原则 | 说明 | 实现方式 |
|------|------|----------|
| **模块解耦** | 各功能模块完全独立，通过接口通信 | 定义抽象基类和协议接口 |
| **依赖注入** | 模块间依赖通过配置注入 | 使用依赖注入容器 |
| **事件驱动** | 模块间通过事件总线通信 | 实现发布-订阅模式 |
| **插件化扩展** | 新功能以插件形式添加 | Provider/Adapter模式 |
| **配置外置** | 所有参数可配置 | YAML配置 + 环境变量 |

### 1.2 初期验证范围

**Phase 1 核心验证目标：**
- ✅ ManicTime数据读取与解析
- ✅ Senatus ti指标计算与VLM触发决策
- ✅ Admina VLM调用（云端API）
- ✅ Cardina fs1实时层存储
- ✅ Cardina fs2日报层聚合
- ✅ fn叙述层基础生成
- ✅ EMA输出接口（初始同步 + 主动查询）

**Phase 2 扩展预留：**
- ⬜ fs3-fs5周/月/年层级聚合
- ⬜ 知识图谱构建（Graphiti集成）
- ⬜ 本地Ollama VLM支持
- ⬜ 动态更新推送机制
- ⬜ OmniParser屏幕解析集成
- ⬜ VLA-Cache帧缓存优化

---

## 二、完整项目文件树

```
MainVisualizer/
│
├── README.md                           # 项目说明文档
├── pyproject.toml                      # Python项目配置（使用uv/poetry）
├── uv.lock                             # 依赖锁定文件
├── .env.example                        # 环境变量模板
├── .gitignore                          # Git忽略规则
│
├── config/                             # 配置文件目录
│   ├── __init__.py
│   ├── settings.yaml                   # 主配置文件
│   ├── logging.yaml                    # 日志配置
│   ├── vlm_providers.yaml              # VLM提供商配置
│   └── schemas/                        # 配置Schema定义
│       ├── __init__.py
│       ├── settings_schema.py
│       └── vlm_schema.py
│
├── src/                                # 源代码主目录
│   ├── __init__.py
│   │
│   ├── core/                           # 核心基础设施
│   │   ├── __init__.py
│   │   ├── container.py                # 依赖注入容器
│   │   ├── event_bus.py                # 事件总线
│   │   ├── exceptions.py               # 自定义异常
│   │   ├── logger.py                   # 日志工具
│   │   └── interfaces/                 # 核心接口定义
│   │       ├── __init__.py
│   │       ├── base_module.py          # 模块基类
│   │       ├── data_source.py          # 数据源接口
│   │       ├── storage.py              # 存储接口
│   │       └── vlm_provider.py         # VLM提供商接口
│   │
│   ├── ingest/                         # 数据摄入层 (ManicTime接口)
│   │   ├── __init__.py
│   │   ├── manictime/                  # ManicTime数据源
│   │   │   ├── __init__.py
│   │   │   ├── db_connector.py         # SQLite数据库连接器
│   │   │   ├── screenshot_loader.py    # 截图加载器
│   │   │   ├── activity_parser.py      # 活动数据解析器
│   │   │   ├── models.py               # ManicTime数据模型
│   │   │   └── sync_manager.py         # 数据同步管理器
│   │   │
│   │   └── adapters/                   # 其他数据源适配器（扩展预留）
│   │       ├── __init__.py
│   │       └── base_adapter.py         # 适配器基类
│   │
│   ├── senatus/                        # Senatus智能触发模块
│   │   ├── __init__.py
│   │   ├── engine.py                   # Senatus主引擎
│   │   ├── ti_calculator.py            # Taboo Index计算器
│   │   ├── trigger_manager.py          # 触发管理器
│   │   ├── analyzers/                  # 分析器组件
│   │   │   ├── __init__.py
│   │   │   ├── base_analyzer.py        # 分析器基类
│   │   │   ├── visual_analyzer.py      # 视觉敏感度分析
│   │   │   ├── metadata_analyzer.py    # 元数据异常分析
│   │   │   ├── frame_diff_analyzer.py  # 帧差异分析
│   │   │   ├── context_switch_analyzer.py  # 窗口切换分析
│   │   │   └── uncertainty_analyzer.py # 不确定性分析
│   │   │
│   │   ├── filters/                    # Stage 1 规则过滤器
│   │   │   ├── __init__.py
│   │   │   ├── base_filter.py          # 过滤器基类
│   │   │   ├── whitelist_filter.py     # 白名单过滤
│   │   │   ├── blacklist_filter.py     # 黑名单过滤
│   │   │   ├── time_rule_filter.py     # 时间规则过滤
│   │   │   └── static_frame_filter.py  # 静态帧过滤
│   │   │
│   │   ├── classifiers/                # Stage 2 轻量分类器
│   │   │   ├── __init__.py
│   │   │   ├── base_classifier.py      # 分类器基类
│   │   │   ├── mobilenet_classifier.py # MobileNet分类器
│   │   │   └── clip_classifier.py      # CLIP零样本分类器（扩展）
│   │   │
│   │   └── models/                     # Senatus数据模型
│   │       ├── __init__.py
│   │       ├── ti_result.py            # TI计算结果
│   │       └── trigger_decision.py     # 触发决策
│   │
│   ├── admina/                         # Admina VLM/LLM调用层
│   │   ├── __init__.py
│   │   ├── manager.py                  # Admina调用管理器
│   │   ├── request_builder.py          # 请求构建器
│   │   ├── response_parser.py          # 响应解析器
│   │   ├── async_executor.py           # 异步执行器
│   │   ├── providers/                  # VLM提供商实现
│   │   │   ├── __init__.py
│   │   │   ├── base_provider.py        # 提供商基类
│   │   │   ├── gemini_provider.py      # Google Gemini
│   │   │   ├── claude_provider.py      # Anthropic Claude
│   │   │   ├── openai_provider.py      # OpenAI GPT-4V
│   │   │   ├── qwen_provider.py        # Qwen2.5-VL (DashScope)
│   │   │   └── ollama_provider.py      # 本地Ollama（扩展）
│   │   │
│   │   ├── prompts/                    # 提示词模板
│   │   │   ├── __init__.py
│   │   │   ├── base_prompt.py          # 提示词基类
│   │   │   ├── screen_analysis.py      # 屏幕分析提示词
│   │   │   ├── activity_summary.py     # 活动总结提示词
│   │   │   └── narrative_generation.py # 叙述生成提示词
│   │   │
│   │   └── models/                     # Admina数据模型
│   │       ├── __init__.py
│   │       ├── vlm_request.py          # VLM请求模型
│   │       ├── vlm_response.py         # VLM响应模型
│   │       └── analysis_result.py      # 分析结果模型
│   │
│   ├── cardina/                        # Cardina数据聚合层
│   │   ├── __init__.py
│   │   ├── engine.py                   # Cardina主引擎
│   │   ├── event_store.py              # 事件存储（Event Sourcing）
│   │   ├── layers/                     # 数据层级实现
│   │   │   ├── __init__.py
│   │   │   ├── base_layer.py           # 层级基类
│   │   │   ├── fs1_realtime.py         # fs1实时层
│   │   │   ├── fs2_daily.py            # fs2日报层
│   │   │   ├── fs3_weekly.py           # fs3周记层（扩展）
│   │   │   ├── fs4_monthly.py          # fs4月记层（扩展）
│   │   │   └── fs5_yearly.py           # fs5年记层（扩展）
│   │   │
│   │   ├── aggregators/                # 聚合器
│   │   │   ├── __init__.py
│   │   │   ├── base_aggregator.py      # 聚合器基类
│   │   │   ├── time_aggregator.py      # 时间聚合
│   │   │   ├── app_aggregator.py       # 应用聚合
│   │   │   └── pattern_aggregator.py   # 模式聚合
│   │   │
│   │   ├── narrative/                  # fn叙述层
│   │   │   ├── __init__.py
│   │   │   ├── generator.py            # 叙述生成器
│   │   │   ├── templates/              # 叙述模板
│   │   │   │   ├── __init__.py
│   │   │   │   ├── daily_template.py   # 日报模板
│   │   │   │   ├── weekly_template.py  # 周记模板（扩展）
│   │   │   │   └── monthly_template.py # 月记模板（扩展）
│   │   │   │
│   │   │   └── formatters/             # 输出格式化器
│   │   │       ├── __init__.py
│   │   │       ├── markdown_formatter.py
│   │   │       └── json_formatter.py
│   │   │
│   │   └── models/                     # Cardina数据模型
│   │       ├── __init__.py
│   │       ├── activity_event.py       # 活动事件
│   │       ├── fs_schemas.py           # fs层级Schema
│   │       └── narrative_output.py     # 叙述输出
│   │
│   ├── storage/                        # 存储层
│   │   ├── __init__.py
│   │   ├── manager.py                  # 存储管理器
│   │   ├── backends/                   # 存储后端
│   │   │   ├── __init__.py
│   │   │   ├── base_backend.py         # 后端基类
│   │   │   ├── sqlite_backend.py       # SQLite（初期验证）
│   │   │   ├── postgres_backend.py     # PostgreSQL（扩展）
│   │   │   ├── redis_backend.py        # Redis缓存（扩展）
│   │   │   └── timescale_backend.py    # TimescaleDB（扩展）
│   │   │
│   │   ├── repositories/               # 数据仓库
│   │   │   ├── __init__.py
│   │   │   ├── base_repository.py      # 仓库基类
│   │   │   ├── event_repository.py     # 事件仓库
│   │   │   ├── fs_repository.py        # fs层级仓库
│   │   │   └── narrative_repository.py # 叙述仓库
│   │   │
│   │   └── migrations/                 # 数据库迁移
│   │       ├── __init__.py
│   │       └── versions/
│   │           └── 001_initial_schema.py
│   │
│   ├── output/                         # 输出接口层 (EMA接口)
│   │   ├── __init__.py
│   │   ├── ema_interface.py            # EMA主接口
│   │   ├── handlers/                   # 输出处理器
│   │   │   ├── __init__.py
│   │   │   ├── base_handler.py         # 处理器基类
│   │   │   ├── initial_sync_handler.py # 初始同步处理
│   │   │   ├── dynamic_update_handler.py # 动态更新处理（扩展）
│   │   │   └── query_handler.py        # 主动查询处理
│   │   │
│   │   ├── formatters/                 # 输出格式化
│   │   │   ├── __init__.py
│   │   │   ├── fn_formatter.py         # fn自然语言格式化
│   │   │   └── fs_formatter.py         # fs JSON格式化
│   │   │
│   │   └── models/                     # 输出数据模型
│   │       ├── __init__.py
│   │       ├── sync_payload.py         # 同步数据包
│   │       └── query_request.py        # 查询请求
│   │
│   ├── pipeline/                       # 处理流水线
│   │   ├── __init__.py
│   │   ├── orchestrator.py             # 流水线编排器
│   │   ├── stages/                     # 流水线阶段
│   │   │   ├── __init__.py
│   │   │   ├── base_stage.py           # 阶段基类
│   │   │   ├── ingest_stage.py         # 数据摄入阶段
│   │   │   ├── senatus_stage.py        # Senatus处理阶段
│   │   │   ├── admina_stage.py         # Admina调用阶段
│   │   │   ├── cardina_stage.py        # Cardina聚合阶段
│   │   │   └── output_stage.py         # 输出阶段
│   │   │
│   │   └── context.py                  # 流水线上下文
│   │
│   └── utils/                          # 工具函数
│       ├── __init__.py
│       ├── image_utils.py              # 图像处理工具
│       ├── time_utils.py               # 时间处理工具
│       ├── hash_utils.py               # 哈希工具（感知哈希）
│       └── validation.py               # 数据验证工具
│
├── tests/                              # 测试目录
│   ├── __init__.py
│   ├── conftest.py                     # pytest配置
│   ├── fixtures/                       # 测试夹具
│   │   ├── __init__.py
│   │   ├── sample_activities.json      # 示例活动数据
│   │   ├── sample_screenshots/         # 示例截图
│   │   └── mock_vlm_responses.json     # 模拟VLM响应
│   │
│   ├── unit/                           # 单元测试
│   │   ├── __init__.py
│   │   ├── test_senatus/
│   │   │   ├── test_ti_calculator.py
│   │   │   ├── test_filters.py
│   │   │   └── test_analyzers.py
│   │   ├── test_cardina/
│   │   │   ├── test_fs1_layer.py
│   │   │   ├── test_fs2_layer.py
│   │   │   └── test_aggregators.py
│   │   └── test_admina/
│   │       ├── test_providers.py
│   │       └── test_response_parser.py
│   │
│   ├── integration/                    # 集成测试
│   │   ├── __init__.py
│   │   ├── test_pipeline.py            # 流水线集成测试
│   │   ├── test_manictime_ingest.py    # ManicTime数据摄入测试
│   │   └── test_ema_output.py          # EMA输出测试
│   │
│   └── e2e/                            # 端到端测试
│       ├── __init__.py
│       └── test_full_workflow.py       # 完整工作流测试
│
├── scripts/                            # 脚本目录
│   ├── setup_dev.py                    # 开发环境设置
│   ├── run_pipeline.py                 # 运行主流水线
│   ├── benchmark_senatus.py            # Senatus性能基准测试
│   └── validate_vlm_output.py          # VLM输出验证
│
├── docs/                               # 文档目录
│   ├── UW_MainVisualizer.md            # 总体架构文档
│   ├── UW_MainVisualizer_InitialValidation.md # 初期验证测试架构文档<--you are here
│   ├── api_reference.md                # API参考
│   ├── development_guide.md            # 开发指南
│   └── deployment.md                   # 部署文档
│
└── examples/                           # 示例代码
    ├── basic_usage.py                  # 基础使用示例
    ├── custom_analyzer.py              # 自定义分析器示例
    └── ema_integration.py              # EMA集成示例
```

---

## 三、初期验证核心模块详细设计

### 3.1 数据摄入层：ManicTime数据源

#### 3.1.1 模块职责

`src/ingest/manictime/` 负责从ManicTime SQLite数据库和截图目录读取原始数据，转换为系统内部统一格式。

#### 3.1.2 核心类设计

**db_connector.py - 数据库连接器**

```
类: ManicTimeDBConnector
职责: 管理与ManicTime SQLite数据库的连接

核心方法:
- connect(db_path: str) -> Connection
  建立数据库连接，支持只读模式
  
- query_activities(start_time: datetime, end_time: datetime) -> List[RawActivity]
  查询指定时间范围的活动记录
  关联表: Ar_Activity, Ar_CommonGroup, Ar_Timeline
  
- query_by_day_summary(date: date) -> DaySummary
  查询日汇总表 Ar_ApplicationByDay
  
- get_last_sync_point() -> datetime
  获取上次同步时间点，用于增量同步

依赖配置:
- db_path: ManicTime数据库路径
- readonly: 是否只读模式（默认True）
```

**screenshot_loader.py - 截图加载器**

```
类: ScreenshotLoader
职责: 加载和预处理ManicTime截图

核心方法:
- load_screenshot(activity_id: int, quality: str = "thumbnail") -> Image
  根据活动ID加载截图
  quality: "thumbnail" | "full"
  
- batch_load(activity_ids: List[int]) -> Dict[int, Image]
  批量加载截图，支持并发
  
- compute_perceptual_hash(image: Image) -> str
  计算感知哈希，用于去重

目录结构映射:
- thumbnails_dir: 缩略图目录
- fullsize_dir: 完整截图目录
- naming_pattern: 文件命名规则
```

**activity_parser.py - 活动数据解析器**

```
类: ActivityParser
职责: 将ManicTime原始数据解析为系统内部格式

核心方法:
- parse_raw_activity(raw: RawActivity) -> ActivityEvent
  解析单条活动记录
  
- enrich_with_screenshot_info(event: ActivityEvent, screenshot: Image) -> ActivityEvent
  为事件添加截图元信息（尺寸、哈希等）
  
- detect_office_document(event: ActivityEvent) -> Optional[str]
  检测Office文档关联（通过RelatedActivityId）

输出格式:
ActivityEvent:
  - event_id: UUID
  - timestamp: datetime
  - duration_seconds: int
  - application: str
  - window_title: str
  - file_path: Optional[str]
  - is_active: bool
  - screenshot_hash: Optional[str]
  - raw_data: dict  # 保留原始数据用于调试
```

**sync_manager.py - 数据同步管理器**

```
类: SyncManager
职责: 管理增量数据同步

核心方法:
- start_sync_loop(interval_seconds: int = 60)
  启动定时同步循环
  
- sync_incremental() -> SyncResult
  执行增量同步
  1. 获取上次同步点
  2. 查询新数据
  3. 发布到事件总线
  
- handle_window_change_event(event: WindowChangeEvent)
  处理窗口切换事件（实时触发）

事件发布:
- NEW_ACTIVITIES: 新活动数据
- SYNC_COMPLETED: 同步完成
```

---

### 3.2 Senatus智能触发模块

#### 3.2.1 模块职责

`src/senatus/` 负责分析活动序列，计算taboo index (ti)，决定是否触发VLM深度分析。

#### 3.2.2 核心类设计

**engine.py - Senatus主引擎**

```
类: SenatusEngine
职责: 协调所有分析组件，执行三级级联推理

核心方法:
- process_activity(activity: ActivityEvent) -> TriggerDecision
  处理单个活动事件
  执行三级级联:
  Stage 1: 规则过滤 → 90%事件直接处理
  Stage 2: 轻量分类 → 计算ti
  Stage 3: 决策输出
  
- process_batch(activities: List[ActivityEvent]) -> List[TriggerDecision]
  批量处理活动
  
- get_context_window(current: ActivityEvent, window_size: int = 10) -> List[ActivityEvent]
  获取上下文窗口，用于序列分析

配置参数:
- ti_threshold_immediate: 0.8  # 立即触发阈值
- ti_threshold_batch: 0.5      # 批量处理阈值
- ti_threshold_skip: 0.3       # 跳过阈值
- context_window_size: 10      # 上下文窗口大小
```

**ti_calculator.py - Taboo Index计算器**

```
类: TabooIndexCalculator
职责: 计算综合ti指标

核心方法:
- calculate(
    activity: ActivityEvent,
    context: List[ActivityEvent],
    screenshot: Optional[Image] = None
  ) -> TIResult
  
  计算公式:
  ti = w1 × P_sensitive + w2 × Anomaly + w3 × ΔFrame + w4 × ContextSwitch + w5 × Uncertainty
  
  默认权重:
  - w1 (visual_sensitive): 0.35
  - w2 (metadata_anomaly): 0.25
  - w3 (frame_diff): 0.15
  - w4 (context_switch): 0.15
  - w5 (uncertainty): 0.10

输出结构:
TIResult:
  - ti_score: float (0.0 - 1.0)
  - component_scores: Dict[str, float]  # 各分量得分
  - confidence: float
  - reasoning: str  # 计算依据说明
  - should_delay: bool  # 是否需要延迟分析
  - delay_reason: Optional[str]
```

**analyzers/visual_analyzer.py - 视觉敏感度分析**

```
类: VisualSensitiveAnalyzer(BaseAnalyzer)
职责: 评估截图的视觉敏感度

核心方法:
- analyze(screenshot: Image, activity: ActivityEvent) -> AnalyzerResult
  
分析维度:
1. 应用类型敏感度
   - 高敏感: IDE, Office, 数据库工具
   - 中敏感: 浏览器, 终端
   - 低敏感: 媒体播放器, 系统设置

2. 窗口标题关键词
   - 新建文档/未保存 → 延迟分析标记
   - 调试/Debug → 高敏感
   - 报告/Report → 高敏感

3. 视觉内容复杂度（初期简化）
   - 使用图像熵估算
   - 文本密度评估
```

**analyzers/context_switch_analyzer.py - 窗口切换分析**

```
类: ContextSwitchAnalyzer(BaseAnalyzer)
职责: 检测窗口切换模式

核心方法:
- analyze(context: List[ActivityEvent]) -> AnalyzerResult
  
检测模式:
1. 快速切换检测
   - 3秒内切换≥3次 → 高分
   
2. 对比模式检测
   - A-B-A-B交替模式识别
   - 窗口对关联性判断
   
3. 切换成本评估
   - 从深度工作应用切换到消息应用 → 高成本

输出:
- switch_frequency: float  # 切换频率
- is_comparison_mode: bool  # 是否对比模式
- involved_windows: List[str]  # 涉及窗口
- estimated_cost: float  # 估计认知成本
```

**filters/whitelist_filter.py - 白名单过滤**

```
类: WhitelistFilter(BaseFilter)
职责: 基于白名单快速过滤无需分析的活动

核心方法:
- should_skip(activity: ActivityEvent) -> FilterResult

过滤规则:
1. 系统进程白名单
   - explorer.exe, dwm.exe 等
   
2. 已知无信息窗口
   - 锁屏, 屏保, 空白桌面
   
3. 短暂活动
   - duration < 5秒 且 非Office应用

配置:
- system_processes: List[str]
- min_duration_seconds: int
- skip_patterns: List[str]  # 窗口标题正则
```

**trigger_manager.py - 触发管理器**

```
类: TriggerManager
职责: 管理VLM触发决策和批量处理

核心方法:
- evaluate_trigger(ti_result: TIResult) -> TriggerDecision
  根据ti结果决定触发行为
  
- add_to_batch(activity: ActivityEvent, ti_result: TIResult)
  添加到批处理队列
  
- flush_batch() -> List[ActivityEvent]
  触发批量VLM分析
  
- handle_delayed_analysis(activity: ActivityEvent, delay_seconds: int)
  处理延迟分析（新建文档场景）

触发决策类型:
- IMMEDIATE: 立即触发VLM
- BATCH: 加入批处理队列
- SKIP: 跳过VLM分析
- DELAY: 延迟分析
```

---

### 3.3 Admina VLM调用层

#### 3.3.1 模块职责

`src/admina/` 负责与各种VLM提供商交互，执行深度视觉分析。

#### 3.3.2 核心类设计

**manager.py - Admina调用管理器**

```
类: AdminaManager
职责: 统一管理VLM调用

核心方法:
- analyze_screenshot(
    screenshot: Image,
    activity: ActivityEvent,
    analysis_type: str = "comprehensive"
  ) -> AnalysisResult
  
- batch_analyze(requests: List[VLMRequest]) -> List[AnalysisResult]
  批量异步分析
  
- get_provider(name: str) -> BaseVLMProvider
  获取指定提供商

分析类型:
- "comprehensive": 全面屏幕分析
- "activity_summary": 活动总结
- "content_extraction": 内容提取（代码/文档）
- "quick_classification": 快速分类

提供商优先级:
1. 首选: Gemini (速度快, 成本低)
2. 备选: Claude (质量高)
3. 降级: Qwen (DashScope)
```

**providers/base_provider.py - 提供商基类**

```
抽象类: BaseVLMProvider
职责: 定义VLM提供商接口

抽象方法:
- async analyze(request: VLMRequest) -> VLMResponse
  执行分析
  
- get_capabilities() -> ProviderCapabilities
  返回提供商能力描述
  
- estimate_cost(request: VLMRequest) -> float
  估算调用成本
  
- health_check() -> bool
  健康检查

通用属性:
- name: str
- api_key: str
- base_url: str
- max_retries: int
- timeout_seconds: int
```

**providers/gemini_provider.py - Gemini提供商**

```
类: GeminiProvider(BaseVLMProvider)
职责: Google Gemini API调用

配置:
- model: "gemini-2.0-flash-exp" | "gemini-1.5-pro"
- safety_settings: Dict
- generation_config: Dict

特殊处理:
- 图像预处理: 自动调整尺寸
- 响应解析: 提取结构化JSON
- 错误重试: 指数退避
```

**async_executor.py - 异步执行器**

```
类: AsyncExecutor
职责: 管理异步VLM调用

核心方法:
- submit(request: VLMRequest) -> asyncio.Future
  提交单个请求
  
- submit_batch(requests: List[VLMRequest]) -> List[asyncio.Future]
  提交批量请求
  
- await_all(futures: List[asyncio.Future], timeout: int = 300) -> List[VLMResponse]
  等待所有结果

并发控制:
- max_concurrent: 10  # 最大并发数
- rate_limit: 60/min  # 速率限制
- semaphore: 并发信号量
```

**response_parser.py - 响应解析器**

```
类: ResponseParser
职责: 解析VLM响应为结构化数据

核心方法:
- parse(raw_response: str, expected_schema: Type[BaseModel]) -> AnalysisResult
  解析响应并验证Schema
  
- extract_structured_data(response: str) -> Dict
  从自由文本中提取结构化数据

输出Schema (AnalysisResult):
- content_type: str  # "code_editing" | "document_writing" | "browsing" | ...
- specific_activity: str  # 具体活动描述
- extracted_text: Optional[str]  # 提取的关键文本
- entities: List[str]  # 识别的实体
- progress_indicator: Optional[str]  # 工作进度指示
- terminal_output: Optional[str]  # 终端输出（如有）
- confidence: float
- raw_analysis: str  # 原始分析文本
```

**prompts/screen_analysis.py - 屏幕分析提示词**

```
类: ScreenAnalysisPrompt(BasePrompt)
职责: 生成屏幕分析提示词

模板结构:
1. 角色设定
   "你是一个专业的屏幕内容分析助手..."
   
2. 任务说明
   根据analysis_type动态调整
   
3. 上下文注入
   - 应用名称
   - 窗口标题
   - 时间戳
   - 持续时间
   
4. 输出格式要求
   JSON Schema约束
   
5. 特殊指令
   - Office文档: 提取章节/段落进度
   - IDE: 提取代码内容/错误信息
   - 浏览器: 提取页面主题
```

---

### 3.4 Cardina数据聚合层

#### 3.4.1 模块职责

`src/cardina/` 负责存储活动事件，执行层级聚合，生成叙述。

#### 3.4.2 核心类设计

**engine.py - Cardina主引擎**

```
类: CardinaEngine
职责: 协调事件存储和层级聚合

核心方法:
- ingest_event(event: ActivityEvent, analysis: Optional[AnalysisResult]) -> str
  摄入事件到fs1层
  返回event_id
  
- trigger_aggregation(layer: str, time_range: TimeRange)
  触发指定层级聚合
  
- get_narrative(layer: str, time_range: TimeRange) -> NarrativeOutput
  获取指定范围的叙述
  
- query_fs(layer: str, filters: QueryFilters) -> List[Dict]
  查询指定层级数据

事件监听:
- 订阅 NEW_ACTIVITIES 事件
- 订阅 VLM_ANALYSIS_COMPLETED 事件
```

**event_store.py - 事件存储**

```
类: EventStore
职责: 实现Event Sourcing模式的事件存储

核心方法:
- append(event: ActivityEvent) -> str
  追加事件（不可变）
  
- get_events(start: datetime, end: datetime) -> List[ActivityEvent]
  获取时间范围内的事件
  
- get_by_id(event_id: str) -> ActivityEvent
  根据ID获取事件
  
- replay(start: datetime) -> Iterator[ActivityEvent]
  重放事件流

存储格式:
- 使用UUID v7 (时间有序)
- 支持事件压缩归档
- 保留完整审计追踪
```

**layers/fs1_realtime.py - fs1实时层**

```
类: FS1RealtimeLayer(BaseLayer)
职责: 管理fs1实时层数据

核心方法:
- store(event: ActivityEvent, analysis: Optional[AnalysisResult]) -> FS1Record
  存储单条记录
  
- get_recent(minutes: int = 30) -> List[FS1Record]
  获取最近N分钟记录
  
- get_by_application(app_name: str, time_range: TimeRange) -> List[FS1Record]
  按应用查询

数据结构 (FS1Record):
{
  "event_id": "uuid-v7",
  "timestamp": "2025-01-15T14:30:00Z",
  "application": "Visual Studio Code",
  "window_title": "main.py - ProjectX",
  "duration_seconds": 1800,
  "is_active": true,
  "vlm_enhanced": true,
  "vlm_analysis": {
    "content_type": "code_editing",
    "specific_activity": "debugging async function",
    "extracted_code_context": "async def process_data()...",
    "terminal_output": "TypeError: Cannot read property...",
    "progress_indicator": "Line 156, investigating Promise chain"
  }
}

保留策略: 24小时滑动窗口
```

**layers/fs2_daily.py - fs2日报层**

```
类: FS2DailyLayer(BaseLayer)
职责: 管理fs2日报层数据

核心方法:
- aggregate_day(date: date) -> FS2DailyReport
  聚合指定日期的fs1数据
  
- get_report(date: date) -> FS2DailyReport
  获取日报
  
- get_range(start_date: date, end_date: date) -> List[FS2DailyReport]
  获取日期范围报告

数据结构 (FS2DailyReport):
{
  "date": "2025-01-15",
  "total_active_hours": 8.5,
  "periods": {
    "morning": {"start": "09:00", "end": "12:00", "hours": 3.0},
    "afternoon": {"start": "13:00", "end": "18:00", "hours": 4.5},
    "evening": {"start": "19:00", "end": "21:00", "hours": 1.0}
  },
  "activity_breakdown": {
    "coding": {"hours": 4.2, "switches": 15},
    "documentation": {"hours": 2.1, "switches": 8},
    "communication": {"hours": 1.5, "switches": 23}
  },
  "top_applications": [
    {"name": "VS Code", "hours": 4.0, "percentage": 47.1},
    {"name": "Chrome", "hours": 2.5, "percentage": 29.4}
  ],
  "key_activities": [
    "完成ProjectX核心模块异步处理优化",
    "审阅3个Pull Requests"
  ],
  "deep_work_sessions": [
    {"start": "14:30", "end": "16:45", "duration_minutes": 135, "activity": "编码"}
  ]
}

聚合触发: 每日凌晨自动 + 手动触发
保留策略: 90天
```

**narrative/generator.py - 叙述生成器**

```
类: NarrativeGenerator
职责: 生成自然语言叙述

核心方法:
- generate_daily(report: FS2DailyReport) -> str
  生成日报叙述
  
- generate_for_query(fs_data: List[Dict], query_context: str) -> str
  根据查询生成叙述
  
- generate_initial_sync(recent_reports: List[FS2DailyReport]) -> str
  生成初始同步叙述

生成策略:
1. 模板填充 + LLM润色
2. 第二人称视角
3. 突出关键信息
4. 控制长度（日报: 200-400字）

示例输出:
"今天你主要在进行ProjectX的开发工作，总共活跃了8.5小时。
下午14:30到16:45是你的深度工作时段，持续135分钟专注于编码，
完成了核心模块的异步处理优化。期间你在VS Code中工作了4小时，
占总时间的47%。你还审阅了3个Pull Requests，处理了一些团队沟通。
建议明天上午安排深度工作，避免下午的会议时段。"
```

---

### 3.5 输出接口层 (EMA接口)

#### 3.5.1 模块职责

`src/output/` 负责向EMA提供数据输出接口。

#### 3.5.2 核心类设计

**ema_interface.py - EMA主接口**

```
类: EMAInterface
职责: 提供EMA所需的所有输出接口

核心方法:
- get_initial_sync() -> SyncPayload
  获取初始同步数据（fn格式）
  用于新对话开始时注入上下文
  
- get_incremental_update(since: datetime) -> Optional[SyncPayload]
  获取增量更新
  返回None表示无需更新
  
- query_activities(request: QueryRequest) -> QueryResponse
  主动查询接口
  支持时间范围、应用过滤、关键词搜索

查询请求格式 (QueryRequest):
{
  "time_range": {"start": "...", "end": "..."},
  "applications": ["VS Code", "Chrome"],
  "keywords": ["项目X"],
  "output_format": "fn" | "fs",
  "granularity": "fs1" | "fs2" | "fs3" | "fs4" | "fs5"
}

响应格式:
- fn格式: 自然语言叙述字符串
- fs格式: 结构化JSON数据
```

**handlers/initial_sync_handler.py - 初始同步处理**

```
类: InitialSyncHandler(BaseHandler)
职责: 处理初始同步请求

核心方法:
- handle() -> SyncPayload
  生成初始同步数据
  
生成策略:
1. 获取最近7天的fs2日报
2. 获取当天的fs1实时数据
3. 组合生成综合叙述
4. 控制总长度（约500-800字）

输出结构 (SyncPayload):
{
  "sync_type": "initial",
  "timestamp": "...",
  "fn_narrative": "过去一周你主要在...",
  "current_activity": "目前你正在VS Code中编辑main.py...",
  "key_projects": ["ProjectX", "文档更新"],
  "patterns": {
    "peak_hours": "14:00-17:00",
    "most_used_app": "VS Code"
  }
}
```

**handlers/query_handler.py - 主动查询处理**

```
类: QueryHandler(BaseHandler)
职责: 处理EMA主动查询请求

核心方法:
- handle(request: QueryRequest) -> QueryResponse
  处理查询请求
  
查询处理流程:
1. 解析查询参数
2. 确定目标层级（根据时间范围自动选择）
3. 执行查询
4. 格式化输出

层级选择规则:
- < 1天: fs1
- 1-7天: fs2
- 1-4周: fs3
- 1-12月: fs4
- > 1年: fs5

示例场景:
用户: "我昨天晚上做了什么？"
→ 查询fs2/fs1
→ 返回: "昨晚19:00-22:00，你主要在..."
```

---

### 3.6 处理流水线

#### 3.6.1 模块职责

`src/pipeline/` 负责编排整个处理流程。

#### 3.6.2 核心类设计

**orchestrator.py - 流水线编排器**

```
类: PipelineOrchestrator
职责: 编排和执行处理流水线

核心方法:
- run_realtime_pipeline()
  启动实时处理流水线
  
- run_batch_aggregation(date: date)
  执行批量聚合
  
- process_single_activity(activity: ActivityEvent) -> PipelineResult
  处理单个活动

流水线阶段:
1. IngestStage: 数据摄入
2. SenatusStage: ti计算 + 触发决策
3. AdminaStage: VLM调用（条件触发）
4. CardinaStage: 存储 + 聚合
5. OutputStage: 输出准备

执行模式:
- 实时模式: 事件驱动，逐条处理
- 批量模式: 定时触发，批量聚合
```

**context.py - 流水线上下文**

```
类: PipelineContext
职责: 在流水线阶段间传递数据

属性:
- activity: ActivityEvent  # 当前处理的活动
- screenshot: Optional[Image]  # 截图
- ti_result: Optional[TIResult]  # ti计算结果
- trigger_decision: Optional[TriggerDecision]  # 触发决策
- vlm_analysis: Optional[AnalysisResult]  # VLM分析结果
- fs1_record: Optional[FS1Record]  # 存储结果
- metadata: Dict  # 其他元数据

方法:
- should_continue() -> bool
  判断是否继续执行后续阶段
```

---

## 四、初期验证测试计划

### 4.1 验证目标

| 验证项 | 成功标准 | 测试方法 |
|--------|----------|----------|
| ManicTime数据读取 | 100%数据正确解析 | 对比原始数据和解析结果 |
| ti指标计算 | 与人工标注一致性>80% | 准备100条标注数据 |
| VLM调用准确性 | 关键信息提取准确率>90% | 人工审核50条VLM输出 |
| fs1存储完整性 | 无数据丢失 | 端到端数据追踪 |
| fs2聚合正确性 | 统计数据正确 | 与ManicTime原生报告对比 |
| fn叙述质量 | 用户满意度>4/5 | 用户评估10条叙述 |
| EMA接口响应 | 延迟<2秒 | 压力测试 |

### 4.2 测试数据准备

```
tests/fixtures/
├── sample_activities.json     # 100条模拟活动数据
├── sample_screenshots/        # 50张标注截图
│   ├── coding_vscode_001.png
│   ├── document_word_001.png
│   └── ...
├── ti_ground_truth.json       # ti标注数据
└── mock_vlm_responses.json    # 模拟VLM响应
```

### 4.3 基准测试脚本

**scripts/benchmark_senatus.py**
- 测试ti计算性能（目标: <10ms/event）
- 测试过滤器准确率
- 测试VLM调用量减少比例（目标: >85%）

**scripts/validate_vlm_output.py**
- 验证VLM输出结构完整性
- 验证提取信息准确性
- 统计各提供商响应时间

---

## 五、扩展路径

### 5.1 Phase 2 扩展项

完成初期验证后，按以下优先级扩展：

1. **fs3-fs5层级聚合**
   - 在`src/cardina/layers/`中实现
   - 复用现有聚合器框架

2. **知识图谱集成**
   - 新增`src/knowledge_graph/`模块
   - 集成Graphiti
   - 实现双时态实体关系存储

3. **动态更新推送**
   - 实现`dynamic_update_handler.py`
   - 基于WebSocket或SSE

4. **本地VLM支持**
   - 实现`ollama_provider.py`
   - 支持UI-TARS-7B本地部署

5. **OmniParser集成**
   - 新增`src/parsing/`模块
   - 替代直接VLM截图分析

### 5.2 接口预留

所有扩展点都已在文件树中预留：
- `adapters/`: 新数据源适配
- `providers/`: 新VLM提供商
- `backends/`: 新存储后端
- `layers/`: 新聚合层级
- `handlers/`: 新输出处理器

---

## 六、配置文件示例

### config/settings.yaml

```yaml
# MainVisualizer 主配置文件

app:
  name: "MainVisualizer"
  version: "0.1.0"
  debug: true

ingest:
  manictime:
    db_path: "${MANICTIME_DB_PATH}"
    screenshots_path: "${MANICTIME_SCREENSHOTS_PATH}"
    sync_interval_seconds: 60
    batch_size: 100

senatus:
  ti_weights:
    visual_sensitive: 0.35
    metadata_anomaly: 0.25
    frame_diff: 0.15
    context_switch: 0.15
    uncertainty: 0.10
  thresholds:
    immediate: 0.8
    batch: 0.5
    skip: 0.3
  context_window_size: 10
  delay_analysis_seconds: 300  # 新建文档延迟

admina:
  default_provider: "gemini"
  max_concurrent: 10
  rate_limit_per_minute: 60
  timeout_seconds: 30
  retry_max: 3

cardina:
  fs1:
    retention_hours: 24
  fs2:
    retention_days: 90
    aggregation_time: "00:30"  # 每日聚合时间

storage:
  backend: "sqlite"  # sqlite | postgres | timescale
  sqlite:
    path: "./data/mainvisualizer.db"

output:
  initial_sync:
    lookback_days: 7
    max_length: 800
  narrative:
    style: "conversational"
    language: "zh-CN"

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "./logs/mv.log"
```

---

## 七、总结

本初期验证架构设计实现了以下目标：

1. **完整性**: 覆盖从数据摄入到EMA输出的完整流程
2. **模块化**: 所有组件解耦，通过接口通信
3. **可扩展**: 预留所有扩展点，Phase 2功能可无缝接入
4. **可验证**: 核心功能可独立测试验证
5. **可配置**: 所有参数外置，支持灵活调整

建议按以下顺序实现：
1. 核心基础设施 (`src/core/`)
2. 数据摄入层 (`src/ingest/`)
3. Senatus模块 (`src/senatus/`)
4. Admina模块 (`src/admina/`)
5. Cardina模块 (`src/cardina/`)
6. 输出接口 (`src/output/`)
7. 流水线编排 (`src/pipeline/`)
