"""Template rendering utilities."""

import html
import json
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from ..ai_status import get_ai_status

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
    suggestions_block = ""
    if ai_suggestions:
        suggestions_block = f"""
  <div class="section">
    <h2>AI fix suggestions</h2>
    <pre>{esc(ai_suggestions)}</pre>
  </div>"""
    tests_block = ""
    if generated_tests:
        tests_block = f"""
  <div class="section">
    <h2>Generated tests</h2>
    <pre>{esc(generated_tests)}</pre>
  </div>"""
    
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
    
    file_path_escaped = quote(file_path, safe="")
    return render_template(
        "review_results.html",
        file_path=esc(file_path),
        file_path_escaped=file_path_escaped,
        error_block=error_block,
        issue_count=len(issues),
        issues_block=issues_block,
        suggestions_block=suggestions_block,
        tests_block=tests_block,
        results_json=results_json,
    )
