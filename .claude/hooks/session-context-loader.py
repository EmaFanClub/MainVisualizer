#!/usr/bin/env python3
"""
Session Context Loader Hook for MainVisualizer

This hook runs at session start (including after auto-compact) to ensure
Claude has access to essential project context.

加载内容:
1. API Query Skill - 查询现有 API 的指南
2. API Doc Writer Skill - 编写新 API 文档的指南
3. Development Guide - 完整的开发规范文档

Output is sent to stdout and will be injected into Claude's context.
"""

import sys
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    import os
    if "CLAUDE_PROJECT_DIR" in os.environ:
        return Path(os.environ["CLAUDE_PROJECT_DIR"])

    # Fallback: find MainVisualizer directory
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "docs" / "api_reference.md").exists():
            return parent

    return Path.cwd()


def read_file_safe(file_path: Path) -> str:
    """Safely read a file."""
    if not file_path.exists():
        return ""
    try:
        return file_path.read_text(encoding="utf-8")
    except Exception:
        return ""


def main():
    """Main entry point for the session context loader hook."""
    project_root = get_project_root()
    docs_dir = project_root / "docs"
    skills_dir = project_root / ".claude" / "skills"

    output = []
    output.append("=" * 70)
    output.append("MAINVISUALIZER SESSION CONTEXT LOADED")
    output.append("=" * 70)
    output.append("")

    # ========== Section 1: API Query Skill ==========
    api_query_skill = read_file_safe(skills_dir / "api-query" / "SKILL.md")
    if api_query_skill:
        output.append("-" * 70)
        output.append("## SKILL: API Query")
        output.append("-" * 70)
        output.append("")
        output.append(api_query_skill)
        output.append("")

    # ========== Section 2: API Doc Writer Skill ==========
    api_doc_writer_skill = read_file_safe(skills_dir / "api-doc-writer" / "SKILL.md")
    if api_doc_writer_skill:
        output.append("-" * 70)
        output.append("## SKILL: API Doc Writer")
        output.append("-" * 70)
        output.append("")
        output.append(api_doc_writer_skill)
        output.append("")

    # ========== Section 3: Development Guide (Full) ==========
    dev_guide = read_file_safe(docs_dir / "development_guide.md")
    if dev_guide:
        output.append("-" * 70)
        output.append("## Development Guide (Full)")
        output.append("-" * 70)
        output.append("")
        output.append(dev_guide)
        output.append("")

    # ========== Footer ==========
    output.append("=" * 70)
    output.append("END OF SESSION CONTEXT")
    output.append("=" * 70)
    output.append("")
    output.append("Quick Reference:")
    output.append("- API Index: docs/api_reference.md")
    output.append("- API Details: docs/api/*.md")
    output.append("- Architecture: docs/UW_MainVisualizer_InitialValidation.md")
    output.append("")

    print("\n".join(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
