"""Format analysis results as human-readable text."""

from deps import Any, Dict, List, Optional, Path, datetime
from .schemas import FileIssues, IssueOut


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


def format_multi_file_report(
    source_path: str,
    source_type: str,
    files: List[FileIssues],
    cross_file_insights: Optional[str],
    dependency_graph: Dict[str, Any],
    ai_fix_suggestions: Optional[str],
) -> str:
    """Format multi-file analysis results as a human-readable text report."""
    lines = []
    lines.append("=" * 80)
    lines.append("Multi-File Cross-Platform Compatibility Analysis Report")
    lines.append("=" * 80)
    lines.append(f"Source: {source_path} ({source_type})")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # Overall summary
    total_files = len(files)
    all_issues: List[IssueOut] = []
    for file_issues in files:
        all_issues.extend(file_issues.issues)
    
    total_issues = len(all_issues)
    error_count = sum(1 for i in all_issues if i.severity == "ERROR")
    warning_count = sum(1 for i in all_issues if i.severity == "WARNING")
    info_count = sum(1 for i in all_issues if i.severity == "INFO")
    
    lines.append("OVERALL SUMMARY")
    lines.append("-" * 80)
    lines.append(f"Total files analyzed: {total_files}")
    lines.append(f"Total issues found: {total_issues}")
    lines.append(f"  Errors:   {error_count}")
    lines.append(f"  Warnings: {warning_count}")
    lines.append(f"  Info:     {info_count}")
    lines.append("")
    
    # Cross-file insights
    if cross_file_insights:
        lines.append("=" * 80)
        lines.append("CROSS-FILE COMPATIBILITY INSIGHTS")
        lines.append("=" * 80)
        lines.append(cross_file_insights)
        lines.append("")
    
    # Dependency graph
    if dependency_graph:
        lines.append("=" * 80)
        lines.append("DEPENDENCY GRAPH")
        lines.append("=" * 80)
        for file_path, data in list(dependency_graph.items())[:50]:  # Limit display
            file_name = Path(file_path).name
            imports = data.get("imports", [])
            imported_by = data.get("imported_by", [])
            
            if imports or imported_by:
                lines.append(f"\n{file_name}:")
                if imports:
                    import_names = [Path(imp).name for imp in imports[:10]]
                    lines.append(f"  Imports: {', '.join(import_names)}")
                if imported_by:
                    importer_names = [Path(imp).name for imp in imported_by[:10]]
                    lines.append(f"  Imported by: {', '.join(importer_names)}")
        lines.append("")
    
    # Group-level AI fix suggestions
    if ai_fix_suggestions:
        lines.append("=" * 80)
        lines.append("GROUP-LEVEL AI FIX SUGGESTIONS")
        lines.append("=" * 80)
        lines.append(ai_fix_suggestions)
        lines.append("")
    
    # Issues by file
    lines.append("=" * 80)
    lines.append("ISSUES BY FILE")
    lines.append("=" * 80)
    lines.append("")
    
    for file_issues in files:
        file_name = Path(file_issues.file_path).name
        issues = file_issues.issues
        language = file_issues.language or "unknown"
        
        lines.append(f"File: {file_name} ({language})")
        lines.append("-" * 80)
        
        if not issues:
            lines.append("No issues found.")
            lines.append("")
            continue
        
        # Group issues by severity
        errors = [i for i in issues if i.severity == "ERROR"]
        warnings = [i for i in issues if i.severity == "WARNING"]
        infos = [i for i in issues if i.severity == "INFO"]
        
        if errors:
            lines.append("ERRORS:")
            for i in errors:
                lines.append(f"  Line {i.line_number} ({i.category})")
                lines.append(f"    Message: {i.message}")
                lines.append(f"    Code:    {i.code}")
                lines.append(f"    Fix:     {i.suggestion}")
                lines.append("")
        
        if warnings:
            lines.append("WARNINGS:")
            for i in warnings:
                lines.append(f"  Line {i.line_number} ({i.category})")
                lines.append(f"    Message: {i.message}")
                lines.append(f"    Code:    {i.code}")
                lines.append(f"    Fix:     {i.suggestion}")
                lines.append("")
        
        if infos:
            lines.append("INFO:")
            for i in infos:
                lines.append(f"  Line {i.line_number} ({i.category})")
                lines.append(f"    Message: {i.message}")
                lines.append(f"    Code:    {i.code}")
                lines.append(f"    Fix:     {i.suggestion}")
                lines.append("")
        
        lines.append("")
    
    lines.append("=" * 80)
    lines.append("End of Report")
    lines.append("=" * 80)
    
    return "\n".join(lines)
