# Quick Start Guide

> 本文档是 MainVisualizer API Reference 的一部分
> 返回: [API Reference Index](../api_reference.md)

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


---

> 返回: [API Reference Index](../api_reference.md)
