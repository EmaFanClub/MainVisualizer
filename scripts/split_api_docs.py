#!/usr/bin/env python3
"""
API文档分割脚本

将单一的api_reference.md按照渐进式披露原则分割为多层级结构：
- docs/api_reference.md (索引文档)
- docs/api/*.md (各模块详细文档)

使用方法:
    python scripts/split_api_docs.py

输出结构:
    docs/
    ├── api_reference.md     # 索引文档（L1/L2层级）
    └── api/                  # 详细文档（L3层级）
        ├── core.md
        ├── ingest_manictime.md
        ├── admina_providers.md
        └── data_models.md
"""

import re
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Section:
    """表示文档中的一个章节"""
    level: int  # 1 = ##, 2 = ###, 3 = ####
    number: str  # 例如 "1", "1.1", "1.2"
    title: str  # 章节标题
    content: str  # 章节内容（不含子章节）
    subsections: list = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0


@dataclass
class ModuleInfo:
    """模块信息，用于生成索引"""
    number: str
    name: str
    description: str
    key_classes: list
    file_path: str


class APIDocSplitter:
    """API文档分割器"""

    def __init__(self, source_path: Path, output_dir: Path):
        self.source_path = source_path
        self.output_dir = output_dir
        self.api_dir = output_dir / "api"
        self.original_content = ""
        self.lines = []
        self.header_content = ""  # 文档头部（版本信息等）
        self.toc_content = ""  # 原始目录
        self.sections = []  # 主要章节列表
        self.quick_start = ""  # Quick Start 部分
        self.footer = ""  # 文档尾部

        # 模块名称到文件名的映射
        self.module_file_map = {
            "Core Module": "core.md",
            "Ingest Module - ManicTime": "ingest_manictime.md",
            "Admina Module - VLM Providers": "admina_providers.md",
            "Senatus Module - Intelligent Trigger": "senatus.md",
            "Data Models": "data_models.md",
        }

    def load_document(self):
        """加载源文档"""
        self.original_content = self.source_path.read_text(encoding="utf-8")
        self.lines = self.original_content.split("\n")
        print(f"已加载文档: {self.source_path}")
        print(f"总行数: {len(self.lines)}")

    def parse_structure(self):
        """解析文档结构 - 使用状态机方式"""
        # 状态: header -> toc -> sections -> quick_start
        STATE_HEADER = "header"
        STATE_TOC = "toc"
        STATE_SECTIONS = "sections"
        STATE_QUICK_START = "quick_start"

        state = STATE_HEADER
        header_lines = []
        toc_lines = []

        current_section = None
        current_subsection = None

        i = 0
        while i < len(self.lines):
            line = self.lines[i]

            # 状态转换检测
            if state == STATE_HEADER:
                if line.startswith("## Table of Contents"):
                    state = STATE_TOC
                    toc_lines.append(line)
                    i += 1
                    continue
                elif re.match(r'^## \d+\.', line):
                    # 没有目录，直接进入章节
                    state = STATE_SECTIONS
                    # 不要 continue，让下面的章节处理逻辑处理这行
                else:
                    header_lines.append(line)
                    i += 1
                    continue

            if state == STATE_TOC:
                toc_lines.append(line)
                if line.startswith("---"):
                    state = STATE_SECTIONS
                i += 1
                continue

            if state == STATE_SECTIONS:
                # 检测 Quick Start（文档末尾）
                if line.startswith("## Quick Start"):
                    # 保存当前章节
                    if current_subsection and current_section:
                        current_section.subsections.append(current_subsection)
                    if current_section:
                        current_section.end_line = i - 1
                        self.sections.append(current_section)

                    state = STATE_QUICK_START
                    # 收集 Quick Start 到文档末尾
                    quick_start_lines = []
                    while i < len(self.lines):
                        quick_start_lines.append(self.lines[i])
                        i += 1
                    self.quick_start = "\n".join(quick_start_lines)
                    break

                # 检测主章节 (## N. Title)
                main_section_match = re.match(r'^## (\d+)\. (.+)$', line)
                if main_section_match:
                    # 保存前一个章节
                    if current_subsection and current_section:
                        current_section.subsections.append(current_subsection)
                    if current_section:
                        current_section.end_line = i - 1
                        self.sections.append(current_section)

                    current_section = Section(
                        level=1,
                        number=main_section_match.group(1),
                        title=main_section_match.group(2),
                        content="",
                        start_line=i,
                        subsections=[]
                    )
                    current_subsection = None
                    i += 1
                    continue

                # 检测子章节 (### N.M Title)
                sub_section_match = re.match(r'^### (\d+\.\d+) (.+)$', line)
                if sub_section_match and current_section:
                    if current_subsection:
                        current_section.subsections.append(current_subsection)

                    current_subsection = Section(
                        level=2,
                        number=sub_section_match.group(1),
                        title=sub_section_match.group(2),
                        content="",
                        start_line=i
                    )
                    i += 1
                    continue

                # 普通内容行
                if current_subsection:
                    current_subsection.content += line + "\n"
                elif current_section:
                    current_section.content += line + "\n"

                i += 1
                continue

            i += 1

        # 保存最后的章节（如果没有 Quick Start）
        if state == STATE_SECTIONS:
            if current_subsection and current_section:
                current_section.subsections.append(current_subsection)
            if current_section:
                current_section.end_line = len(self.lines) - 1
                self.sections.append(current_section)

        self.header_content = "\n".join(header_lines)
        self.toc_content = "\n".join(toc_lines)

        print(f"\n解析完成:")
        print(f"- 头部行数: {len(header_lines)}")
        print(f"- 目录行数: {len(toc_lines)}")
        print(f"- 主章节数: {len(self.sections)}")
        for sec in self.sections:
            print(f"  - {sec.number}. {sec.title} (子章节: {len(sec.subsections)})")

    def extract_module_content(self, section: Section) -> str:
        """提取模块的完整内容（从原始文档）"""
        # 直接从原始行中提取，保证内容完整
        start = section.start_line
        end = section.end_line

        lines = self.lines[start:end + 1]
        return "\n".join(lines)

    def generate_module_header(self, section: Section) -> str:
        """生成模块文档的头部"""
        return f"""# {section.title} API Reference

> 本文档是 MainVisualizer API Reference 的一部分
> 返回: [API Reference Index](../api_reference.md)

---

"""

    def extract_key_classes(self, section: Section) -> list:
        """从章节中提取关键类名"""
        classes = []
        content = self.extract_module_content(section)

        # 匹配 class ClassName 或 ### N.M ClassName
        class_patterns = [
            r'class (\w+)',
            r'### \d+\.\d+ (\w+)',
        ]

        for pattern in class_patterns:
            matches = re.findall(pattern, content)
            classes.extend(matches)

        # 去重并保持顺序
        seen = set()
        unique_classes = []
        for cls in classes:
            if cls not in seen and not cls.startswith("def"):
                seen.add(cls)
                unique_classes.append(cls)

        return unique_classes[:10]  # 最多返回10个

    def extract_description(self, section: Section) -> str:
        """提取模块描述（第一段非空内容）"""
        content = section.content.strip()
        if not content:
            # 尝试从子章节描述中获取
            for sub in section.subsections:
                if sub.content.strip():
                    first_line = sub.content.strip().split("\n")[0]
                    return first_line[:100]
            return ""

        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("|") and not line.startswith("```"):
                return line[:150]
        return ""

    def generate_index_document(self) -> str:
        """生成索引文档"""
        modules_info = []

        # 收集模块信息
        for section in self.sections:
            file_name = self.module_file_map.get(section.title, f"module_{section.number}.md")
            modules_info.append(ModuleInfo(
                number=section.number,
                name=section.title,
                description=self.extract_description(section),
                key_classes=self.extract_key_classes(section),
                file_path=f"api/{file_name}"
            ))

        # 构建索引文档
        doc = []

        # 头部
        doc.append("# MainVisualizer API Reference")
        doc.append("")
        doc.append("> **Version**: 0.1.0  ")
        doc.append(f"> **Last Updated**: 2025-12  ")
        doc.append("> **Architecture**: Progressive Disclosure (渐进式披露)")
        doc.append("")
        doc.append("本文档提供 MainVisualizer 各模块的 API 索引。详细文档请查看各模块的专属文档。")
        doc.append("")
        doc.append("---")
        doc.append("")

        # Quick Reference Card
        doc.append("## Quick Reference Card")
        doc.append("")
        doc.append("### 常用导入")
        doc.append("")
        doc.append("```python")
        doc.append("# Core")
        doc.append("from src.core import setup_logging, get_logger")
        doc.append("from src.core import DatabaseConnectionError, VLMProviderError")
        doc.append("")
        doc.append("# Ingest - ManicTime")
        doc.append("from src.ingest.manictime import ManicTimeDBConnector, ScreenshotLoader, ActivityParser")
        doc.append("")
        doc.append("# Admina - VLM Providers")
        doc.append("from src.admina import QwenVLProvider, OllamaProvider")
        doc.append("```")
        doc.append("")
        doc.append("### 快速使用模式")
        doc.append("")
        doc.append("```python")
        doc.append("# 读取ManicTime数据")
        doc.append("with ManicTimeDBConnector(db_path) as db:")
        doc.append("    activities = db.query_activities(start, end)")
        doc.append("")
        doc.append("# 调用VLM分析")
        doc.append("provider = QwenVLProvider()")
        doc.append("result = await provider.analyze_image(image, prompt)")
        doc.append("```")
        doc.append("")
        doc.append("---")
        doc.append("")

        # Module Index
        doc.append("## Module Index")
        doc.append("")

        for info in modules_info:
            doc.append(f"### {info.number}. {info.name}")
            doc.append("")
            if info.description:
                doc.append(f"**Purpose**: {info.description}")
                doc.append("")

            if info.key_classes:
                doc.append("**Key Classes**:")
                doc.append("")
                doc.append("| Class | Quick Link |")
                doc.append("|-------|------------|")
                for cls in info.key_classes[:5]:  # 只显示前5个
                    doc.append(f"| `{cls}` | [{info.file_path}](#{cls.lower()}) |")
                doc.append("")

            doc.append(f"**Full Documentation**: [{info.file_path}]({info.file_path})")
            doc.append("")

        doc.append("---")
        doc.append("")

        # Data Models Overview
        doc.append("## Data Models Overview")
        doc.append("")
        doc.append("所有数据模型使用 Pydantic 定义。详见 [api/data_models.md](api/data_models.md)")
        doc.append("")
        doc.append("| Model | Module | Description |")
        doc.append("|-------|--------|-------------|")
        doc.append("| `ActivityEvent` | ingest | 系统内部统一活动事件格式 |")
        doc.append("| `RawActivity` | ingest | ManicTime 原始活动记录 |")
        doc.append("| `ApplicationInfo` | ingest | 应用/窗口信息 |")
        doc.append("| `ScreenshotMetadata` | ingest | 截图元信息 |")
        doc.append("| `DaySummary` | ingest | 日汇总数据 |")
        doc.append("| `VLMRequest` | admina | VLM 请求模型 |")
        doc.append("| `VLMResponse` | admina | VLM 响应模型 |")
        doc.append("| `AnalysisResult` | admina | 屏幕分析结果 |")
        doc.append("")
        doc.append("---")
        doc.append("")

        # Navigation
        doc.append("## Documentation Structure")
        doc.append("")
        doc.append("```")
        doc.append("docs/")
        doc.append("├── api_reference.md          # 本索引文档 (L1/L2)")
        doc.append("└── api/                      # 详细文档 (L3)")
        doc.append("    ├── core.md               # Core 模块")
        doc.append("    ├── ingest_manictime.md   # Ingest 模块")
        doc.append("    ├── admina_providers.md   # Admina 模块")
        doc.append("    └── data_models.md        # 数据模型")
        doc.append("```")
        doc.append("")
        doc.append("---")
        doc.append("")
        doc.append("*Document Version: 0.1.0*")
        doc.append("")

        return "\n".join(doc)

    def save_module_document(self, section: Section, file_name: str):
        """保存模块文档"""
        content = self.extract_module_content(section)

        # 添加文档头部
        header = self.generate_module_header(section)

        # 处理内容：移除原来的主标题（## N. Title），因为我们添加了新的标题
        lines = content.split("\n")
        if lines and re.match(r'^## \d+\.', lines[0]):
            lines = lines[1:]  # 移除第一行（原标题）

        # 组合完整内容
        full_content = header + "\n".join(lines)

        # 添加导航尾部
        full_content += "\n\n---\n\n"
        full_content += "> 返回: [API Reference Index](../api_reference.md)\n"

        # 保存文件
        output_path = self.api_dir / file_name
        output_path.write_text(full_content, encoding="utf-8")
        print(f"已保存: {output_path}")

        return output_path

    def run(self):
        """执行分割"""
        print("=" * 60)
        print("API文档分割脚本")
        print("=" * 60)

        # 创建输出目录
        self.api_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n输出目录: {self.api_dir}")

        # 加载和解析
        self.load_document()
        self.parse_structure()

        # 保存各模块文档
        print("\n保存模块文档:")
        for section in self.sections:
            file_name = self.module_file_map.get(section.title, f"module_{section.number}.md")
            self.save_module_document(section, file_name)

        # 保存 Quick Start 到单独文件（可选）
        if self.quick_start:
            quick_start_path = self.api_dir / "quick_start.md"
            quick_start_content = f"""# Quick Start Guide

> 本文档是 MainVisualizer API Reference 的一部分
> 返回: [API Reference Index](../api_reference.md)

---

{self.quick_start}

---

> 返回: [API Reference Index](../api_reference.md)
"""
            quick_start_path.write_text(quick_start_content, encoding="utf-8")
            print(f"已保存: {quick_start_path}")

        # 生成并保存索引文档
        print("\n生成索引文档:")
        index_content = self.generate_index_document()
        index_path = self.output_dir / "api_reference.md"

        # 备份原文档
        backup_path = self.output_dir / "api_reference.backup.md"
        if self.source_path.exists():
            backup_path.write_text(self.original_content, encoding="utf-8")
            print(f"已备份原文档: {backup_path}")

        # 保存新索引
        index_path.write_text(index_content, encoding="utf-8")
        print(f"已保存索引: {index_path}")

        # 输出统计
        print("\n" + "=" * 60)
        print("分割完成!")
        print("=" * 60)
        print(f"\n生成文件统计:")
        print(f"  - 索引文档: 1")
        print(f"  - 模块文档: {len(self.sections)}")
        if self.quick_start:
            print(f"  - Quick Start: 1")
        print(f"  - 备份文件: 1")

        # 返回生成的文件列表
        return {
            "index": index_path,
            "modules": [self.api_dir / self.module_file_map.get(s.title, f"module_{s.number}.md")
                       for s in self.sections],
            "backup": backup_path
        }


def main():
    """主入口"""
    # 确定路径
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    docs_dir = project_root / "docs"
    source_file = docs_dir / "api_reference.md"

    if not source_file.exists():
        print(f"错误: 源文件不存在: {source_file}")
        return 1

    # 执行分割
    splitter = APIDocSplitter(source_file, docs_dir)
    result = splitter.run()

    # 输出结果路径（JSON格式，方便其他脚本使用）
    print("\n生成的文件:")
    print(json.dumps({
        "index": str(result["index"]),
        "modules": [str(p) for p in result["modules"]],
        "backup": str(result["backup"])
    }, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    exit(main())
