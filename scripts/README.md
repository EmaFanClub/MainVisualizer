# Scripts 目录说明

## 核心工作流

分析流程分为4个步骤，每个步骤独立运行，可以灵活组合：

```
ManicTime数据 → [1.TI计算] → [2.VLM分析] → [3.合并结果] → [4.滑窗分析]
```

### 步骤1: TI批量计算
```bash
python scripts/calculate_ti_batch.py [小时数] [选项]

# 示例
python scripts/calculate_ti_batch.py 168                    # 分析7天
python scripts/calculate_ti_batch.py 24 --threshold 0.45    # 自定义阈值
```
**输出**: `data/ti_results/ti_batch_YYYYMMDD_HHMMSS.json`

### 步骤2: VLM分析
```bash
python scripts/run_vlm_analysis.py [ti_batch文件] [选项]

# 示例
python scripts/run_vlm_analysis.py                          # 自动使用最新ti_batch
python scripts/run_vlm_analysis.py ti_batch.json --max-vlm 100
```
**输出**: `data/vlm_analysis/vlm_result_YYYYMMDD_HHMMSS.json`

### 步骤3: 合并结果
```bash
python scripts/merge_ti_vlm_results.py [ti_batch] [vlm_result]

# 示例
python scripts/merge_ti_vlm_results.py                      # 全自动
python scripts/merge_ti_vlm_results.py ti_batch.json        # 指定ti_batch
```
**输出**:
- `data/merged_results/merged.json` - 完整合并结果
- `data/merged_results/activity_summary.json` - 按时间槽分组的摘要

### 步骤4: 滑窗分析
```bash
python scripts/sliding_window_analysis.py [选项]

# 示例
python scripts/sliding_window_analysis.py                   # 全自动
python scripts/sliding_window_analysis.py -c 20 -m 5        # 20并发，只处理5个窗口
python scripts/sliding_window_analysis.py -w 4 -s 2         # 4槽窗口，2槽步长
```
**输出**: `data/sliding_window/sliding_window_result.json`

---

## 快速运行完整流程

```bash
# 1. 计算TI (7天数据)
python scripts/calculate_ti_batch.py 168

# 2. VLM分析
python scripts/run_vlm_analysis.py

# 3. 合并结果
python scripts/merge_ti_vlm_results.py

# 4. 滑窗分析
python scripts/sliding_window_analysis.py
```

---

## 目录结构

```
scripts/
├── calculate_ti_batch.py       # 步骤1: TI计算
├── run_vlm_analysis.py         # 步骤2: VLM分析
├── merge_ti_vlm_results.py     # 步骤3: 合并结果
├── sliding_window_analysis.py  # 步骤4: 滑窗分析
├── analyze_ti_distribution.py  # TI分布统计分析
├── explore_manictime.py        # 探索ManicTime数据
├── explore_senatus_data.py     # 探索Senatus数据
├── verify_ingest.py            # 验证数据摄入
├── split_api_docs.py           # API文档拆分工具
└── test/                       # 测试脚本
    ├── test_vlm_analysis.py    # VLM分析一体化测试
    ├── test_vlm_integration.py
    ├── test_vlm_with_context.py
    ├── test_senatus_integration.py
    └── verify_batch_processor.py
```

---

## 数据目录

```
data/
├── ti_results/                 # TI计算结果
│   └── ti_batch_*.json
├── vlm_analysis/               # VLM分析结果
│   └── vlm_result_*.json
├── merged_results/             # 合并结果
│   ├── merged.json
│   └── activity_summary.json
└── sliding_window/             # 滑窗分析结果
    └── sliding_window_result.json
```
