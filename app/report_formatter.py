"""Format analysis results as human-readable Markdown (aligned with webpage layout)."""

from deps import Any, Dict, List, Optional, Path, datetime
from .schemas import FileIssues, IssueOut


def _title_case(s: str) -> str:
    """e.g. ERROR -> Error, DEPRECATION -> Deprecation."""
    if not s:
        return s
    return s.replace("_", " ").strip().lower().title()


def _issue_block_md(i: IssueOut) -> List[str]:
    """One issue as Markdown: Line N · Category · Severity, then message, code, fix (like webpage)."""
    cat = _title_case(getattr(i, "category", "") or "")
    sev = _title_case(getattr(i, "severity", "") or "")
    lines = []
    lines.append(f"**Line {i.line_number} · {cat} · {sev}**")
    lines.append("")
    lines.append(i.message)
    lines.append("")
    lines.append("- **Code:**")
    lines.append("```")
    lines.append(i.code)
    lines.append("```")
    lines.append("")
    lines.append("- **Fix:**")
    lines.append("```")
    lines.append(i.suggestion)
    lines.append("```")
    lines.append("")
    return lines


def format_text_report(
    file_path: str,
    issues: List[IssueOut],
    ai_suggestions: Optional[str],
    generated_tests: Optional[str],
) -> str:
    """Format single-file analysis results as Markdown (structure mirrors results page)."""
    lines = []
    lines.append(f"# Results: {file_path}")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    error_count = sum(1 for i in issues if i.severity == "ERROR")
    warning_count = sum(1 for i in issues if i.severity == "WARNING")
    info_count = sum(1 for i in issues if i.severity == "INFO")
    lines.append(f"**{len(issues)}** issue(s) found ({error_count} error(s), {warning_count} warning(s), {info_count} info).")
    lines.append("")

    # Issues section (like the collapsible "Issues" on the page)
    lines.append("## Issues")
    lines.append("")
    if not issues:
        lines.append("No compatibility issues found.")
        lines.append("")
    else:
        errors = [i for i in issues if i.severity == "ERROR"]
        warnings = [i for i in issues if i.severity == "WARNING"]
        infos = [i for i in issues if i.severity == "INFO"]
        for i in errors + warnings + infos:
            lines.extend(_issue_block_md(i))

    if ai_suggestions:
        lines.append("## AI fix suggestions")
        lines.append("")
        lines.append(ai_suggestions.strip())
        lines.append("")

    if generated_tests:
        lines.append("## Generated tests")
        lines.append("")
        lines.append(generated_tests.strip())
        lines.append("")

    return "\n".join(lines)


def format_multi_file_report(
    source_path: str,
    source_type: str,
    files: List[FileIssues],
    cross_file_insights: Optional[str],
    dependency_graph: Dict[str, Any],
    ai_fix_suggestions: Optional[str],
) -> str:
    """Format multi-file analysis results as Markdown (structure mirrors multi-file results page)."""
    lines = []
    lines.append(f"# Multi-File Analysis Results: {source_path}")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    all_issues: List[IssueOut] = []
    for f in files:
        all_issues.extend(f.issues)
    total_issues = len(all_issues)
    error_count = sum(1 for i in all_issues if i.severity == "ERROR")
    warning_count = sum(1 for i in all_issues if i.severity == "WARNING")
    info_count = sum(1 for i in all_issues if i.severity == "INFO")
    lines.append(f"**{len(files)}** file(s) analyzed · **{total_issues}** total issue(s) found ({error_count} error(s), {warning_count} warning(s), {info_count} info)")
    lines.append("")

    # Dependency Relationships (like the collapsible on the page)
    if dependency_graph:
        lines.append("## Dependency Relationships")
        lines.append("")
        for file_path, data in list(dependency_graph.items())[:50]:
            file_name = Path(file_path).name
            imports = data.get("imports", [])
            imported_by = data.get("imported_by", [])
            lang = data.get("language", "unknown")
            lines.append(f"- **{file_name}** ({lang})")
            if imports:
                import_names = [Path(imp).name for imp in imports[:10]]
                lines.append(f"  - Imports: {', '.join(import_names)}")
            if imported_by:
                importer_names = [Path(imp).name for imp in imported_by[:10]]
                lines.append(f"  - Imported by: {', '.join(importer_names)}")
            if not imports and not imported_by:
                lines.append("  - *(no dependencies)*")
            lines.append("")
        lines.append("")

    # Standard File Issues (like the collapsible with per-file details)
    lines.append("## Standard File Issues")
    lines.append("")
    for file_issues in files:
        file_name = Path(file_issues.file_path).name
        issues = file_issues.issues
        language = file_issues.language or "unknown"
        ec = sum(1 for i in issues if i.severity == "ERROR")
        wc = sum(1 for i in issues if i.severity == "WARNING")
        ic = sum(1 for i in issues if i.severity == "INFO")
        badges = []
        if ec:
            badges.append(f"Errors: {ec}")
        if wc:
            badges.append(f"Warnings: {wc}")
        if ic:
            badges.append(f"Info: {ic}")
        badge_str = " · ".join(badges) if badges else "No issues"
        lines.append(f"### {file_name} ({language}) — {badge_str}")
        lines.append("")
        if not issues:
            lines.append("No issues found.")
            lines.append("")
            continue
        for i in issues:
            lines.extend(_issue_block_md(i))
    lines.append("")

    # AI-generated insights (same order as page: Cross-File then Group-Level Fix Suggestions)
    if cross_file_insights or ai_fix_suggestions:
        lines.append("## AI-generated insights")
        lines.append("")
        if cross_file_insights:
            lines.append("### Cross-File Compatibility Insights")
            lines.append("")
            lines.append(cross_file_insights.strip())
            lines.append("")
        if ai_fix_suggestions:
            lines.append("### Group-Level AI Fix Suggestions")
            lines.append("")
            lines.append(ai_fix_suggestions.strip())
            lines.append("")

    return "\n".join(lines)
