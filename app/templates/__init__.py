"""Template rendering utilities."""

from ..ai_status import get_ai_status
from deps import Any, Dict, html, json, List, Optional, os, Path, quote
from ..schemas import FileIssues

TEMPLATES_DIR = Path(__file__).parent


def _render_ai_status_banner() -> str:
    """Generate AI status banner HTML."""
    status = get_ai_status()
    esc = html.escape
    
    if status["available"]:
        icon = "✓"
        cls = "available"
        msg = f"AI features available (model: {esc(status['model'])})"
    else:
        icon = "⚠"
        cls = "unavailable"
        reason = esc(status["reason"])
        if not status["openai_available"]:
            msg = f"AI unavailable: {reason}. Install: pip install openai"
        elif not status["api_key_set"]:
            msg = f"AI unavailable: {reason}. Set TOGETHER_API_KEY in .env"
        else:
            msg = f"AI unavailable: {reason}"
    
    return f'<div class="ai-status {cls}"><span class="ai-status-icon">{icon}</span><span class="ai-status-text">{msg}</span></div>'


def load_template(name: str) -> str:
    """Load a template file."""
    path = TEMPLATES_DIR / name
    return path.read_text(encoding="utf-8")


def load_css() -> str:
    """Load the CSS file."""
    return load_template("styles.css")


def render_template(template_name: str, **kwargs) -> str:
    """Render a template with the given variables."""
    template = load_template(template_name)
    css = load_css()
    base = load_template("base.html")
    content = template.format(**kwargs)
    # Use string replacement for base template to avoid CSS brace conflicts
    title_val = kwargs.get("title", "Compatibility Checker")
    ai_banner = _render_ai_status_banner()
    result = base.replace("{title}", title_val).replace("{css}", css).replace("{ai_status_banner}", ai_banner).replace("{content}", content)
    return result


def render_review_form(error: Optional[str] = None, value: str = "") -> str:
    """Render the review form template."""
    error_block = f'<div class="form-error">{html.escape(error)}</div>' if error else ""
    value_attr = f' value="{html.escape(value)}"' if value else ""
    return render_template("review_form.html", error_block=error_block, value_attr=value_attr)


def render_review_results(
    file_path: str,
    issues: list,
    ai_suggestions: Optional[str],
    generated_tests: Optional[str],
    error: Optional[str] = None,
) -> str:
    """Render the review results template."""
    
    esc = html.escape
    error_block = f'<div class="form-error">{esc(error)}</div>' if error else ""
    issues_block = ""
    for i in issues:
        cls = "error" if i.severity == "ERROR" else "warning" if i.severity == "WARNING" else "info"
        issues_block += f"""
  <div class="issue {cls}">
    <div class="issue-meta">Line {i.line_number} · {esc(i.category)} · {esc(i.severity)}</div>
    <div class="issue-msg">{esc(i.message)}</div>
    <div class="issue-code">Code: {esc(i.code)}</div>
    <div class="issue-fix">Fix: {esc(i.suggestion)}</div>
  </div>"""
    if not issues_block:
        issues_block = "<p>No issues found.</p>"
    issues_block = f"""<details class="collapsible-section" open>
  <summary>Issues</summary>
  <div class="collapsible-content">{issues_block}
  </div>
</details>"""
    suggestions_block = ""
    if ai_suggestions:
        suggestions_block = f"""<details class="collapsible-section" open>
  <summary>AI fix suggestions</summary>
  <div class="collapsible-content">
  <div class="section">
    <pre>{esc(ai_suggestions)}</pre>
  </div>
  </div>
</details>"""
    tests_block = ""
    if generated_tests:
        tests_block = f"""<details class="collapsible-section" open>
  <summary>Generated tests</summary>
  <div class="collapsible-content">
  <div class="section">
    <pre>{esc(generated_tests)}</pre>
  </div>
  </div>
</details>"""
    
    # Prepare JSON data for client-side caching
    results_data = {
        "file_path": file_path,
        "file_name": Path(file_path).name,
        "issues": [
            {
                "severity": i.severity,
                "line_number": i.line_number,
                "column": i.column,
                "message": i.message,
                "code": i.code,
                "suggestion": i.suggestion,
                "category": i.category,
            }
            for i in issues
        ],
        "ai_suggestions": ai_suggestions,
        "generated_tests": generated_tests,
    }
    # Escape JSON for safe embedding in HTML script tag
    results_json_raw = json.dumps(results_data, ensure_ascii=False)
    # Escape </script> to prevent XSS (JSON already escapes quotes properly)
    results_json = results_json_raw.replace("</script>", "<\\/script>")
    
    error_count = sum(1 for i in issues if i.severity == "ERROR")
    warning_count = sum(1 for i in issues if i.severity == "WARNING")
    info_count = sum(1 for i in issues if i.severity == "INFO")
    file_path_escaped = quote(file_path, safe="")
    return render_template(
        "review_results.html",
        file_path=esc(file_path),
        file_path_escaped=file_path_escaped,
        error_block=error_block,
        issue_count=len(issues),
        error_count=error_count,
        warning_count=warning_count,
        info_count=info_count,
        issues_block=issues_block,
        suggestions_block=suggestions_block,
        tests_block=tests_block,
        results_json=results_json,
    )


def render_review_multi_results(
    source_path: str,
    source_type: str,
    files: List[FileIssues],
    cross_file_insights: Optional[str],
    dependency_graph: Dict[str, Any],
    ai_fix_suggestions: Optional[str],
    error: Optional[str] = None,
    report_id: Optional[str] = None,
    source_root: Optional[Path] = None,
) -> str:
    """Render the multi-file review results template."""
    esc = html.escape
    
    error_block = f'<div class="form-error">{esc(error)}</div>' if error else ""
    
    total_files = len(files)
    all_issues = [i for f in files for i in f.issues]
    total_issues = len(all_issues)
    total_errors = sum(1 for i in all_issues if i.severity == "ERROR")
    total_warnings = sum(1 for i in all_issues if i.severity == "WARNING")
    total_info = sum(1 for i in all_issues if i.severity == "INFO")

    # Compute display_root for relative paths (used by dependency graph and files block)
    file_paths = [Path(f.file_path).resolve() for f in files]
    display_root = None
    if source_root:
        display_root = Path(source_root).resolve()
    if not display_root and file_paths:
        try:
            display_root = Path(os.path.commonpath([str(p) for p in file_paths]))
            if display_root.is_file():
                display_root = display_root.parent
            def _child_dirs_containing_files(parent: Path) -> List[Path]:
                return [d for d in parent.iterdir() if d.is_dir() and any(str(f).startswith(str(d) + os.sep) or str(f).startswith(str(d) + "/") for f in file_paths)]
            while display_root.parent.exists():
                parent = display_root.parent
                if parent.name == "extracted":
                    display_root = parent
                    break
                children_with_files = _child_dirs_containing_files(parent)
                if len(children_with_files) != 1 or children_with_files[0] != display_root:
                    break
                display_root = parent
        except (ValueError, TypeError):
            pass
    
    # Cross-file insights block (collapsible)
    cross_file_insights_block = ""
    if cross_file_insights:
        cross_file_insights_block = f"""<details class="collapsible-section" open>
  <summary>Cross-File Compatibility Insights</summary>
  <div class="collapsible-content">
  <div class="section">
    <pre>{esc(cross_file_insights)}</pre>
  </div>
  </div>
</details>"""
    
    # Dependency graph block (collapsible)
    dependency_graph_block = ""
    if dependency_graph:
        graph_lines = ["<ul class=\"dependency-graph\">"]
        for file_path, data in list(dependency_graph.items())[:50]:  # Limit display
            fp = Path(file_path).resolve()
            if display_root and str(fp).startswith(str(display_root)):
                file_display = str(fp.relative_to(display_root))
            else:
                file_display = fp.name
            p_display = Path(file_display)
            if p_display.parent != Path("."):
                folder_part = str(p_display.parent).replace("\\", "/") + "/"
                name_part = p_display.name
            else:
                folder_part, name_part = "", file_display
            language = data.get("language", "unknown")
            file_name_html = f'<span class="file-path-folder">{esc(folder_part)}</span><span class="file-path-name">{esc(name_part)}</span> <span class="file-path-lang">({esc(language)})</span>'
            imports = data.get("imports", [])
            imported_by = data.get("imported_by", [])
            graph_lines.append(f"<li>{file_name_html}")
            if imports:
                import_names = [esc(Path(imp).name) for imp in imports[:5]]
                graph_lines.append(f"<br>  Imports: {', '.join(import_names)}")
            if imported_by:
                importer_names = [esc(Path(imp).name) for imp in imported_by[:5]]
                graph_lines.append(f"<br>  Imported by: {', '.join(importer_names)}")
            if not imports and not imported_by:
                graph_lines.append("<br>  <em>(no dependencies)</em>")
            graph_lines.append("</li>")
        graph_lines.append("</ul>")
        dependency_graph_block = f"""<details class="collapsible-section" open>
  <summary>Dependency Relationships</summary>
  <div class="collapsible-content">
  <div class="section">
    {''.join(graph_lines)}
  </div>
  </div>
</details>"""
    
    # AI fix suggestions block (collapsible)
    ai_fix_suggestions_block = ""
    if ai_fix_suggestions:
        ai_fix_suggestions_block = f"""<details class="collapsible-section" open>
  <summary>Group-Level AI Fix Suggestions</summary>
  <div class="collapsible-content">
  <div class="section">
    <pre>{esc(ai_fix_suggestions)}</pre>
  </div>
  </div>
</details>"""
    
    # Files block - issues grouped by file (collapsible section with per-file collapsibles)
    files_block = ""
    for file_issues in files:
        fp = Path(file_issues.file_path).resolve()
        if display_root and str(fp).startswith(str(display_root)):
            file_display = str(fp.relative_to(display_root))
        else:
            file_display = fp.name
        # Split into folder and filename for styling (folder lighter, filename prominent)
        p_display = Path(file_display)
        if p_display.parent != Path("."):
            folder_part = str(p_display.parent).replace("\\", "/") + "/"
            name_part = p_display.name
        else:
            folder_part, name_part = "", file_display
        issues = file_issues.issues
        language = file_issues.language or "unknown"
        error_count = sum(1 for i in issues if i.severity == "ERROR")
        warning_count = sum(1 for i in issues if i.severity == "WARNING")
        info_count = sum(1 for i in issues if i.severity == "INFO")
        
        if issues:
            counts_parts = []
            if error_count:
                counts_parts.append(f"{error_count} error(s)")
            if warning_count:
                counts_parts.append(f"{warning_count} warning(s)")
            if info_count:
                counts_parts.append(f"{info_count} info")
            counts_text = ", ".join(counts_parts) if counts_parts else f"{len(issues)} issue(s)"
            summary_counts = f'<span class="file-counts">{counts_text}</span>'
            issues_html = ""
            for i in issues:
                cls = "error" if i.severity == "ERROR" else "warning" if i.severity == "WARNING" else "info"
                issues_html += f"""
    <div class="issue {cls}">
      <div class="issue-meta">Line {i.line_number} · {esc(i.category)} · {esc(i.severity)}</div>
      <div class="issue-msg">{esc(i.message)}</div>
      <div class="issue-code">Code: {esc(i.code)}</div>
      <div class="issue-fix">Fix: {esc(i.suggestion)}</div>
    </div>"""
            issue_count = len(issues)
            file_name_html = f'<span class="file-path-folder">{esc(folder_part)}</span><span class="file-path-name">{esc(name_part)}</span> <span class="file-path-lang">({esc(language)})</span>'
            files_block += f"""
  <details class="file-collapsible" data-issue-count="{issue_count}" data-file-path="{esc(file_display)}">
    <summary><span class="file-name">{file_name_html}</span>{summary_counts}</summary>
    <div class="collapsible-content">
      <div class="file-group">
{issues_html}
      </div>
    </div>
  </details>"""
        else:
            file_name_html = f'<span class="file-path-folder">{esc(folder_part)}</span><span class="file-path-name">{esc(name_part)}</span> <span class="file-path-lang">({esc(language)})</span>'
            files_block += f"""
  <details class="file-collapsible" data-issue-count="0" data-file-path="{esc(file_display)}">
    <summary><span class="file-name">{file_name_html}</span><span class="file-counts">No issues found.</span></summary>
    <div class="collapsible-content">
      <div class="file-group">
    <p>No issues found.</p>
      </div>
    </div>
  </details>"""
    
    if not files_block:
        files_block = "<p>No files analyzed.</p>"
    else:
        files_block = f"""<details class="collapsible-section" open>
  <summary>Standard File Issues</summary>
  <div class="collapsible-content">
  <div class="file-issues-toolbar">
    <span class="file-issues-toolbar-label">Sort by:</span>
    <button type="button" class="sort-file-by-path" aria-pressed="true">Path</button>
    <button type="button" class="sort-file-by-count" aria-pressed="false">Issue count</button>
  </div>
  <div class="file-issues-list" id="file-issues-list">
{files_block}
  </div>
  </div>
</details>"""

    source_path_escaped = quote(source_path, safe="")
    # For uploads we use report_id so download works without a filesystem path
    if report_id:
        download_url = f"/review/multi/download?source_type=upload&report_id={quote(report_id, safe='')}"
    else:
        download_url = f"/review/multi/download?source_path={source_path_escaped}&source_type={quote(source_type, safe='')}"

    return render_template(
        "review_multi_results.html",
        source_path=esc(source_path),
        source_path_escaped=source_path_escaped,
        source_type=esc(source_type),
        download_url=download_url,
        error_block=error_block,
        total_files=total_files,
        total_issues=total_issues,
        total_errors=total_errors,
        total_warnings=total_warnings,
        total_info=total_info,
        cross_file_insights_block=cross_file_insights_block,
        dependency_graph_block=dependency_graph_block,
        ai_fix_suggestions_block=ai_fix_suggestions_block,
        files_block=files_block,
    )
