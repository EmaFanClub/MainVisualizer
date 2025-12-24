#!/usr/bin/env python3
"""
Session Context Loader Hook for MainVisualizer

会话启动时加载精简的项目上下文提醒。
"""

import sys
from pathlib import Path


def get_project_root() -> Path:
    """获取项目根目录"""
    import os
    if "CLAUDE_PROJECT_DIR" in os.environ:
        return Path(os.environ["CLAUDE_PROJECT_DIR"])

    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "docs" / "api_reference.md").exists():
            return parent

    return Path.cwd()


def main():
    """主入口"""
    project_root = get_project_root()
    docs_dir = project_root / "docs"
    skills_dir = project_root / ".claude" / "skills"

    output = []
    output.append("=" * 60)
    output.append("MAINVISUALIZER PROJECT CONTEXT")
    output.append("=" * 60)

    # ========== Skills 摘要 ==========
    output.append("")
    output.append("## Available Skills")
    output.append("")

    # API Query Skill
    if (skills_dir / "api-query" / "SKILL.md").exists():
        output.append("1. **api-query**: 查询现有模块 API")
        output.append("   - 触发: 需要调用现有 API、查看接口签名、了解使用示例时")
        output.append("   - 使用: 执行 skill `api-query`")

    # API Doc Writer Skill
    if (skills_dir / "api-doc-writer" / "SKILL.md").exists():
        output.append("2. **api-doc-writer**: 为新模块编写 API 文档")
        output.append("   - 触发: 完成新模块开发后需要添加 API 文档时")
        output.append("   - 使用: 执行 skill `api-doc-writer`")

    # ========== 开发指南提醒 ==========
    output.append("")
    output.append("## Development Guide")
    output.append("")

    if (docs_dir / "development_guide.md").exists():
        output.append("路径: `docs/development_guide.md`")
        output.append("")
        output.append("**何时阅读**:")
        output.append("- 代码开发阶段: 首次进行代码修改前需完整阅读")
        output.append("- 文档/测试阶段: 无需完整阅读，按需查阅")
        output.append("")
        output.append("**核心规范**:")
        output.append("- 注释和文档字符串使用中文，禁止 emoji")
        output.append("- 单文件 <= 800 行，单函数 <= 50 行")
        output.append("- 模块间通过接口通信，禁止跨模块直接导入")

    # ========== 快速参考 ==========
    output.append("")
    output.append("## Quick Reference")
    output.append("- API 索引: `docs/api_reference.md`")
    output.append("- 架构文档: `docs/UW_MainVisualizer_InitialValidation.md`")
    output.append("")
    output.append("=" * 60)

    print("\n".join(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
