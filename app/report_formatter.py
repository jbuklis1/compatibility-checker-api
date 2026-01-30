"""Format analysis results as human-readable text."""

from datetime import datetime
from typing import List, Optional

from .schemas import IssueOut


def format_text_report(
    file_path: str,
    issues: List[IssueOut],
    ai_suggestions: Optional[str],
    generated_tests: Optional[str],
) -> str:
    """Format analysis results as a human-readable text report."""
    lines = []
    lines.append("=" * 80)
    lines.append("Cross-Platform Compatibility Analysis Report")
    lines.append("=" * 80)
    lines.append(f"File: {file_path}")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # Summary
    error_count = sum(1 for i in issues if i.severity == "ERROR")
    warning_count = sum(1 for i in issues if i.severity == "WARNING")
    info_count = sum(1 for i in issues if i.severity == "INFO")
    lines.append("SUMMARY")
    lines.append("-" * 80)
    lines.append(f"Total issues: {len(issues)}")
    lines.append(f"  Errors:   {error_count}")
    lines.append(f"  Warnings: {warning_count}")
    lines.append(f"  Info:     {info_count}")
    lines.append("")
    
    # Issues by severity
    errors = [i for i in issues if i.severity == "ERROR"]
    warnings = [i for i in issues if i.severity == "WARNING"]
    infos = [i for i in issues if i.severity == "INFO"]
    
    if errors:
        lines.append("ERRORS")
        lines.append("-" * 80)
        for i in errors:
            lines.append(f"Line {i.line_number} ({i.category})")
            lines.append(f"  Message: {i.message}")
            lines.append(f"  Code:    {i.code}")
            lines.append(f"  Fix:     {i.suggestion}")
            lines.append("")
    
    if warnings:
        lines.append("WARNINGS")
        lines.append("-" * 80)
        for i in warnings:
            lines.append(f"Line {i.line_number} ({i.category})")
            lines.append(f"  Message: {i.message}")
            lines.append(f"  Code:    {i.code}")
            lines.append(f"  Fix:     {i.suggestion}")
            lines.append("")
    
    if infos:
        lines.append("INFO")
        lines.append("-" * 80)
        for i in infos:
            lines.append(f"Line {i.line_number} ({i.category})")
            lines.append(f"  Message: {i.message}")
            lines.append(f"  Code:    {i.code}")
            lines.append(f"  Fix:     {i.suggestion}")
            lines.append("")
    
    if not issues:
        lines.append("No compatibility issues found.")
        lines.append("")
    
    # AI suggestions
    if ai_suggestions:
        lines.append("=" * 80)
        lines.append("AI FIX SUGGESTIONS")
        lines.append("=" * 80)
        lines.append(ai_suggestions)
        lines.append("")
    
    # Generated tests
    if generated_tests:
        lines.append("=" * 80)
        lines.append("GENERATED TEST CASES")
        lines.append("=" * 80)
        lines.append(generated_tests)
        lines.append("")
    
    lines.append("=" * 80)
    lines.append("End of Report")
    lines.append("=" * 80)
    
    return "\n".join(lines)
