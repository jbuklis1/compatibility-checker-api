"""Template rendering utilities."""

from ..ai_status import get_ai_status
import re
from deps import Any, Dict, html, json, List, Optional, os, Path, quote
from ..schemas import FileIssues

TEMPLATES_DIR = Path(__file__).parent


def _format_display_category(category: str) -> str:
    """Pretty-print category for display (e.g. DEPRECATION -> Deprecation)."""
    if not category:
        return category
    return category.replace("_", " ").strip().lower().title()


def _format_display_severity(severity: str) -> str:
    """Pretty-print severity for display (e.g. ERROR -> Error)."""
    if not severity:
        return severity
    return severity.strip().lower().title()


def _looks_like_numbered_list(block: str) -> bool:
    """True if block appears to be a numbered list (e.g. 1. ... 2. ...)."""
    lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
    if not lines:
        return False
    for line in lines:
        i = 0
        while i < len(line) and line[i] in "0123456789":
            i += 1
        if i == 0 or i >= len(line) or line[i] != "." or (i + 1 < len(line) and not line[i + 1].isspace()):
            return False
    return True


def _ai_content_to_html(text: str) -> str:
    """Convert AI-generated plain text (possibly markdown-like) to safe, readable HTML."""
    if not text:
        return ""
    esc = html.escape
    parts = text.split("```")
    out = []
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        # Odd-index parts are inside code fences
        if i % 2 == 1:
            out.append(f'<pre class="ai-code"><code>{esc(part)}</code></pre>')
            continue
        # Normal content: paragraphs and optional headings
        blocks = [b.strip() for b in part.split("\n\n") if b.strip()]
        for block in blocks:
            if block.startswith("#### "):
                out.append(f'<h4 class="ai-h4">{esc(block[5:].strip())}</h4>')
            elif block.startswith("### "):
                out.append(f'<h3 class="ai-h3">{esc(block[4:].strip())}</h3>')
            elif block.startswith("## "):
                out.append(f'<h2 class="ai-h2">{esc(block[3:].strip())}</h2>')
            elif block.startswith("# "):
                out.append(f'<h2 class="ai-h2">{esc(block[2:].strip())}</h2>')
            elif block.startswith("- ") or block.startswith("* "):
                items = []
                for line in block.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("- "):
                        items.append(line[2:].strip())
                    elif line.startswith("* "):
                        items.append(line[2:].strip())
                    else:
                        items.append(line)
                items_esc = "".join(f"<li>{esc(item)}</li>" for item in items)
                out.append(f'<ul class="ai-list">{items_esc}</ul>')
            elif _looks_like_numbered_list(block):
                items = []
                for line in block.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    for j, c in enumerate(line):
                        if c in "0123456789":
                            continue
                        if c == "." and j > 0 and (j + 1 >= len(line) or line[j + 1].isspace()):
                            items.append(line[j + 1:].strip())
                            break
                    else:
                        items.append(line)
                items_esc = "".join(f"<li>{esc(item)}</li>" for item in items)
                out.append(f'<ol class="ai-list">{items_esc}</ol>')
            else:
                # Paragraph: single newlines become <br>
                inner = esc(block).replace("\n", "<br>\n")
                out.append(f'<p class="ai-p">{inner}</p>')
    return '<div class="ai-content-body">' + "".join(out) + "</div>"


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


def render_ai_status_banner() -> str:
    """Generate AI status banner HTML (for embedding in review tab)."""
    return _render_ai_status_banner()


def render_template(template_name: str, omit_global_ai_banner: bool = False, **kwargs) -> str:
    """Render a template with the given variables."""
    template = load_template(template_name)
    css = load_css()
    base = load_template("base.html")
    content = template.format(**kwargs)
    # Use string replacement for base template to avoid CSS brace conflicts
    title_val = kwargs.get("title", "Compatibility Checker")
    ai_banner = "" if omit_global_ai_banner else _render_ai_status_banner()
    result = base.replace("{title}", title_val).replace("{css}", css).replace("{ai_status_banner}", ai_banner).replace("{content}", content)
    return result


# C-family languages shown as one combined box in the language grid
_C_FAMILY_GROUP = ("C", "C++", "C#")
_C_FAMILY_LABEL = "C / C++ / C#"


def _render_reviewable_languages_grid() -> str:
    """HTML for the grid of reviewable language names, grouped and colored by support level."""
    from ..services.file_extractor import (
        FULL_SUPPORT_LANGUAGE_NAMES_SORTED,
        PARTIAL_SUPPORT_LANGUAGE_NAMES,
    )
    esc = html.escape
    # Full support: C, C++, C# in one box; rest as individual tags
    full_display = [n for n in FULL_SUPPORT_LANGUAGE_NAMES_SORTED if n not in _C_FAMILY_GROUP]
    full_display.insert(0, _C_FAMILY_LABEL)
    full_tags_parts = []
    for name in full_display:
        extra_class = " language-tag-c-family" if name == _C_FAMILY_LABEL else ""
        full_tags_parts.append(f'<span class="language-tag language-tag-full{extra_class}">{esc(name)}</span>')
    full_tags = "".join(full_tags_parts)
    partial_tags = "".join(
        f'<span class="language-tag language-tag-partial">{esc(name)}</span>'
        for name in PARTIAL_SUPPORT_LANGUAGE_NAMES
    )
    parts = []
    parts.append('<div class="language-grid-wrapper" aria-label="Supported languages">')
    parts.append('<p class="language-grid-intro language-grid-label-full">Full support (language-specific checks)</p>')
    parts.append(f'<div class="language-grid language-grid-full">{full_tags}</div>')
    if partial_tags:
        parts.append('<p class="language-grid-intro language-grid-label-partial">Basic support (path/API checks only)</p>')
        parts.append(f'<div class="language-grid language-grid-partial">{partial_tags}</div>')
    parts.append("</div>")
    return "\n".join(parts)


def render_review_form_fragment(error: Optional[str] = None, value: str = "") -> str:
    """Return only the review form content (no base layout), for embedding in the homepage tab."""
    error_block = f'<div class="form-error">{html.escape(error)}</div>' if error else ""
    value_attr = f' value="{html.escape(value)}"' if value else ""
    reviewable_languages_html = _render_reviewable_languages_grid()
    template = load_template("review_form.html")
    return template.format(
        error_block=error_block,
        value_attr=value_attr,
        reviewable_languages_html=reviewable_languages_html,
    )


def render_homepage(review_tab_open: bool = False, form_error: Optional[str] = None) -> str:
    """Render the merged homepage with optional review tab open and form error message."""
    review_form_content = render_review_form_fragment(error=form_error)
    ai_status_banner = _render_ai_status_banner()
    review_tab_attr = "" if review_tab_open else "hidden"
    return render_template(
        "root.html",
        omit_global_ai_banner=True,
        title="Cross-Platform Compatibility Checker API",
        ai_status_banner=ai_status_banner,
        review_form_content=review_form_content,
        review_tab_attr=review_tab_attr,
    )


def render_review_form(error: Optional[str] = None, value: str = "") -> str:
    """Render the review form template."""
    error_block = f'<div class="form-error">{html.escape(error)}</div>' if error else ""
    value_attr = f' value="{html.escape(value)}"' if value else ""
    reviewable_languages_html = _render_reviewable_languages_grid()
    return render_template(
        "review_form.html",
        error_block=error_block,
        value_attr=value_attr,
        reviewable_languages_html=reviewable_languages_html,
    )


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
        cat_display = _format_display_category(getattr(i, "category", "") or "")
        sev_display = _format_display_severity(getattr(i, "severity", "") or "")
        issues_block += f"""
  <div class="issue {cls}">
    <div class="issue-meta">Line {i.line_number} · {esc(cat_display)} · <span class="issue-severity-pill issue-severity-{cls}">{esc(sev_display)}</span></div>
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
  <div class="section ai-content-block">
{_ai_content_to_html(ai_suggestions)}
  </div>
  </div>
</details>"""
    tests_block = ""
    if generated_tests:
        tests_block = f"""<details class="collapsible-section" open>
  <summary>Generated tests</summary>
  <div class="collapsible-content">
  <div class="section ai-content-block">
{_ai_content_to_html(generated_tests)}
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
        omit_global_ai_banner=True,
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
    
    # Cross-file insights block (collapsible) — AI-generated, same formatting as other AI sections
    cross_file_insights_block = ""
    if cross_file_insights:
        cross_file_insights_block = f"""<details class="collapsible-section" open>
  <summary>Cross-File Compatibility Insights</summary>
  <div class="collapsible-content">
  <div class="section ai-content-block">
{_ai_content_to_html(cross_file_insights)}
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
  <div class="section ai-content-block">
{_ai_content_to_html(ai_fix_suggestions)}
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
            badge_parts = []
            if error_count:
                badge_parts.append(f'<span class="issue-badge issue-badge-error">Errors: {error_count}</span>')
            if warning_count:
                badge_parts.append(f'<span class="issue-badge issue-badge-warning">Warnings: {warning_count}</span>')
            if info_count:
                badge_parts.append(f'<span class="issue-badge issue-badge-info">Info: {info_count}</span>')
            badges_html = "".join(badge_parts)
            issues_html = ""
            for i in issues:
                cls = "error" if i.severity == "ERROR" else "warning" if i.severity == "WARNING" else "info"
                cat_display = _format_display_category(getattr(i, "category", "") or "")
                sev_display = _format_display_severity(getattr(i, "severity", "") or "")
                issues_html += f"""
    <div class="issue {cls}">
      <div class="issue-meta">Line {i.line_number} · {esc(cat_display)} · <span class="issue-severity-pill issue-severity-{cls}">{esc(sev_display)}</span></div>
      <div class="issue-msg">{esc(i.message)}</div>
      <div class="issue-code">Code: {esc(i.code)}</div>
      <div class="issue-fix">Fix: {esc(i.suggestion)}</div>
    </div>"""
            issue_count = len(issues)
            file_name_html = f'<span class="file-path-folder">{esc(folder_part)}</span><span class="file-path-name">{esc(name_part)}</span> <span class="file-path-lang">({esc(language)})</span>'
            files_block += f"""
  <details class="file-collapsible" data-issue-count="{issue_count}" data-file-path="{esc(file_display)}">
    <summary>
      <span class="file-summary-inner">
        <span class="file-path-row">{file_name_html}</span>
        <span class="file-issue-badges">{badges_html}</span>
      </span>
    </summary>
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
    <summary>
      <span class="file-summary-inner">
        <span class="file-path-row">{file_name_html}</span>
        <span class="file-issue-badges"><span class="issue-badge issue-badge-neutral">No issues</span></span>
      </span>
    </summary>
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

    # Group AI-generated sections with a heading so it's clear which content is AI output
    ai_results_block = ""
    if cross_file_insights_block or ai_fix_suggestions_block:
        ai_results_block = '<h2 class="results-section-heading">AI-generated insights</h2>\n'
        ai_results_block += (cross_file_insights_block or "") + "\n" + (ai_fix_suggestions_block or "")

    source_path_escaped = quote(source_path, safe="")
    # For uploads we use report_id so download works without a filesystem path
    if report_id:
        download_url = f"/review/multi/download?source_type=upload&report_id={quote(report_id, safe='')}"
    else:
        download_url = f"/review/multi/download?source_path={source_path_escaped}&source_type={quote(source_type, safe='')}"

    # Filename for download attribute so the browser triggers instant download (no open/save dialog)
    _label = (source_path or "").strip()
    _name = Path(_label.replace("\\", "/")).name or Path(_label).stem or "report"
    _stem = Path(_name).stem or _name
    _safe = (re.sub(r"[^\w\-]", "_", _stem)[:80].strip("_") or "compatibility_report")
    download_filename = f"{_safe}_compatibility_report.md"

    return render_template(
        "review_multi_results.html",
        omit_global_ai_banner=True,
        source_path=esc(source_path),
        source_path_escaped=source_path_escaped,
        source_type=esc(source_type),
        download_url=download_url,
        download_filename=download_filename,
        error_block=error_block,
        total_files=total_files,
        total_issues=total_issues,
        total_errors=total_errors,
        total_warnings=total_warnings,
        total_info=total_info,
        dependency_graph_block=dependency_graph_block,
        files_block=files_block,
        ai_results_block=ai_results_block,
    )
