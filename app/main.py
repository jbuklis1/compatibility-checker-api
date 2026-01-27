"""FastAPI app: /health, /check, /analyze."""

import html
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .config import ensure_checker_import_path
from .schemas import AnalyzeRequest, AnalyzeResponse, CheckResponse, IssueOut
from .services import AIService, CheckerService

ensure_checker_import_path()

from cross_platform_checker.utils import detect_language

app = FastAPI(
    title="AI-Powered Cross-Platform Compatibility Checker API",
    description="Rule-based checks plus Together.ai fix suggestions and test generation.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

checker_svc = CheckerService()
ai_svc = AIService()


@app.on_event("startup")
def _validate_config() -> None:
    """Validate config at startup and warn if .env or TOGETHER_API_KEY missing."""
    import json
    import time
    from pathlib import Path
    from .config import get_together_api_key

    LOG_PATH = Path("/home/j/Documents/code/cursor/.cursor/debug.log")

    def _agent_log(location: str, message: str, hypothesis_id: str, data: dict | None = None) -> None:
        # #region agent log
        try:
            payload = {
                "location": location,
                "message": message,
                "hypothesisId": hypothesis_id,
                "data": data or {},
                "timestamp": int(time.time() * 1000),
                "sessionId": "debug-session",
                "runId": "run1",
            }
            with open(LOG_PATH, "a") as f:
                f.write(json.dumps(payload) + "\n")
        except Exception:
            pass
        # #endregion

    # #region agent log
    env_file = Path(".env")
    env_exists = env_file.exists()
    key = get_together_api_key()
    key_set = bool(key)
    _agent_log("main.py:startup", "config validation", "H3", {"env_exists": env_exists, "key_set": key_set})
    # #endregion
    if not env_exists:
        print("⚠️  WARNING: .env file not found. AI features will be disabled.")
        print("   Create .env from .env.example and set TOGETHER_API_KEY for AI features.")
    elif not key_set:
        print("⚠️  WARNING: TOGETHER_API_KEY not set in .env. AI features will be disabled.")
        print("   Set TOGETHER_API_KEY in .env to enable AI suggestions and test generation.")


def _run_check(req: AnalyzeRequest) -> Tuple[List[IssueOut], Optional[str], Optional[str]]:
    """Run checker. Returns (issues, code, language) for AI. code/lang are set when available."""
    code: Optional[str] = None
    lang: Optional[str] = None
    if req.file_path:
        p = Path(req.file_path)
        if not p.is_absolute():
            raise HTTPException(400, "file_path must be absolute")
        if not p.exists():
            raise HTTPException(404, f"File not found: {req.file_path}")
        issues = checker_svc.analyze_file(p)
        try:
            code = p.read_text(encoding="utf-8", errors="replace")
            lang = detect_language(p)
        except Exception:
            pass
        return issues, code, lang
    if req.code is not None and req.language:
        issues = checker_svc.analyze_code(
            req.code,
            req.language,
            filename=req.filename or "input",
        )
        return issues, req.code, req.language
    raise HTTPException(
        400,
        "Provide either (code + language) or file_path.",
    )


_ROOT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Cross-Platform Compatibility Checker API</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 42rem; margin: 2rem auto; padding: 0 1rem; }
    h1 { font-size: 1.25rem; font-weight: 600; }
    ul { list-style: none; padding: 0; }
    li { margin: 0.5rem 0; }
    a { color: #2563eb; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .meta { color: #64748b; font-size: 0.875rem; margin-top: 1.5rem; }
  </style>
</head>
<body>
  <h1>AI-Powered Cross-Platform Compatibility Checker API</h1>
  <p>Endpoints:</p>
  <ul>
    <li><a href="/review">/review</a> — Form: enter file path, view results</li>
    <li><a href="/docs">/docs</a> — Swagger UI</li>
    <li><a href="/redoc">/redoc</a> — ReDoc</li>
    <li><a href="/health">/health</a> — Liveness</li>
    <li><a href="/check">/check</a> — Usage (POST)</li>
    <li><a href="/analyze">/analyze</a> — Usage (POST)</li>
  </ul>
  <p class="meta">Use <a href="/review">/review</a> to submit a file path, or POST /check or /analyze with JSON. See <a href="/docs">/docs</a> for details.</p>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    """Root: welcome page with clickable links."""
    return _ROOT_HTML


_REVIEW_STYLE = """
  body { font-family: system-ui, sans-serif; max-width: 48rem; margin: 2rem auto; padding: 0 1rem; }
  h1 { font-size: 1.25rem; font-weight: 600; }
  form { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: flex-end; margin: 1rem 0; }
  label { display: block; font-size: 0.875rem; font-weight: 500; margin-bottom: 0.25rem; }
  input[type="text"] { padding: 0.5rem 0.75rem; font-size: 0.9375rem; min-width: 20rem; }
  button { padding: 0.5rem 1rem; font-size: 0.9375rem; background: #2563eb; color: white; border: none; border-radius: 0.375rem; cursor: pointer; }
  button:hover { background: #1d4ed8; }
  .form-error { color: #dc2626; margin: 1rem 0; padding: 0.75rem; background: #fef2f2; border-radius: 0.375rem; }
  .issue { margin: 1rem 0; padding: 0.75rem; background: #f8fafc; border-radius: 0.375rem; border-left: 4px solid #94a3b8; }
  .issue.error { border-left-color: #dc2626; }
  .issue.warning { border-left-color: #f59e0b; }
  .issue.info { border-left-color: #3b82f6; }
  .issue-meta { font-size: 0.8125rem; color: #64748b; margin-bottom: 0.25rem; }
  .issue-msg { font-weight: 500; margin-bottom: 0.25rem; }
  .issue-code, .issue-fix { font-family: ui-monospace, monospace; font-size: 0.8125rem; white-space: pre-wrap; word-break: break-all; }
  .section { margin-top: 1.5rem; }
  .section h2 { font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem; }
  pre { background: #f1f5f9; padding: 1rem; border-radius: 0.375rem; overflow-x: auto; font-size: 0.8125rem; white-space: pre-wrap; }
  a { color: #2563eb; text-decoration: none; }
  a:hover { text-decoration: underline; }
"""


def _review_form_html(error: Optional[str] = None, value: str = "") -> str:
    err_block = f'<div class="form-error">{html.escape(error)}</div>' if error else ""
    val_attr = f' value="{html.escape(value)}"' if value else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Review — Compatibility Checker API</title>
  <style>{_REVIEW_STYLE}</style>
</head>
<body>
  <h1>Review file for cross-platform compatibility</h1>
  <p>Enter the <strong>absolute path</strong> to a source file on this server (e.g. <code>/home/you/project/main.py</code>).</p>
  {err_block}
  <form method="post" action="/review">
    <div>
      <label for="file_path">File path</label>
      <input type="text" id="file_path" name="file_path" placeholder="/absolute/path/to/file.py" required{val_attr}>
    </div>
    <div>
      <button type="submit">Analyze</button>
    </div>
  </form>
  <p><a href="/">Home</a> · <a href="/docs">Swagger UI</a> · <a href="/redoc">ReDoc</a> · <a href="/health">Health</a></p>
</body>
</html>
"""


def _results_html(
    file_path: str,
    issues: List[IssueOut],
    ai_suggestions: Optional[str],
    generated_tests: Optional[str],
    error: Optional[str] = None,
) -> str:
    esc = html.escape
    err_block = f'<div class="form-error">{esc(error)}</div>' if error else ""
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
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Results — {esc(file_path)}</title>
  <style>{_REVIEW_STYLE}</style>
</head>
<body>
  <h1>Results: {esc(file_path)}</h1>
  {err_block}
  <p><strong>{len(issues)}</strong> issue(s) found.</p>
  <div class="section">
    <h2>Issues</h2>
    {issues_block if issues_block else "<p>No issues found.</p>"}
  </div>
  {suggestions_block}
  {tests_block}
  <p style="margin-top: 1.5rem;"><a href="/review">Review another file</a> · <a href="/">Home</a> · <a href="/docs">Swagger UI</a></p>
</body>
</html>
"""


@app.get("/review", response_class=HTMLResponse)
def review_get() -> str:
    """Form: enter file path for analysis."""
    return _review_form_html()


@app.post("/review", response_class=HTMLResponse)
def review_post(file_path: str = Form(default="")) -> str:
    """Run analysis on file path and render results."""
    file_path = (file_path or "").strip()
    if not file_path:
        return _review_form_html(error="File path is required.", value=file_path)
    p = Path(file_path)
    if not p.is_absolute():
        return _review_form_html(error="File path must be absolute.", value=file_path)
    if not p.exists():
        return _review_form_html(error=f"File not found: {file_path}", value=file_path)
    req = AnalyzeRequest(file_path=file_path)
    issues, code, lang = _run_check(req)
    ai_suggestions = ai_svc.suggest_fixes(issues, code=code, language=lang)
    generated_tests = ai_svc.generate_tests(code or "", lang or "unknown", issues) if (code and lang) else None
    return _results_html(file_path, issues, ai_suggestions, generated_tests)


@app.get("/health")
def health() -> dict:
    """Liveness check."""
    return {"status": "ok"}


_CHECK_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Check — Compatibility Checker API</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 42rem; margin: 2rem auto; padding: 0 1rem; }
    h1 { font-size: 1.25rem; font-weight: 600; }
    ul { list-style: none; padding: 0; }
    li { margin: 0.5rem 0; }
    a { color: #2563eb; text-decoration: none; }
    a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <h1>POST /check</h1>
  <p>Rules-only analysis (no AI). Send JSON: <code>{"code": "...", "language": "python"}</code> or <code>{"file_path": "/path/to/file"}</code>.</p>
  <p><a href="/">Home</a> · <a href="/review">Review</a> · <a href="/docs">Swagger UI</a> · <a href="/redoc">ReDoc</a> · <a href="/health">Health</a> · <a href="/analyze">Analyze</a></p>
</body>
</html>
"""


@app.get("/check", response_class=HTMLResponse)
def check_get() -> str:
    """GET /check: usage page with links. Use POST with JSON body for rules-only analysis."""
    return _CHECK_HTML


@app.post("/check", response_model=CheckResponse)
def check(req: AnalyzeRequest) -> CheckResponse:
    """Rules-only analysis. No AI."""
    issues, _, _ = _run_check(req)
    return CheckResponse(issues=issues)


_ANALYZE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Analyze — Compatibility Checker API</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 42rem; margin: 2rem auto; padding: 0 1rem; }
    h1 { font-size: 1.25rem; font-weight: 600; }
    ul { list-style: none; padding: 0; }
    li { margin: 0.5rem 0; }
    a { color: #2563eb; text-decoration: none; }
    a:hover { text-decoration: underline; }
    pre { background: #f1f5f9; padding: 1rem; border-radius: 0.5rem; overflow-x: auto; font-size: 0.8125rem; }
  </style>
</head>
<body>
  <h1>POST /analyze</h1>
  <p>Send a JSON body for full analysis (rules + AI suggestions + generated tests).</p>
  <p><strong>Request body options:</strong></p>
  <ul>
    <li><strong>Option A:</strong> <code>{"code": "...", "language": "python", "filename": "example.py"}</code></li>
    <li><strong>Option B:</strong> <code>{"file_path": "/absolute/path/to/file.py"}</code></li>
  </ul>
  <p><a href="/">Home</a> · <a href="/review">Review</a> · <a href="/docs">Swagger UI</a> · <a href="/redoc">ReDoc</a> · <a href="/health">Health</a> · <a href="/check">Check</a></p>
</body>
</html>
"""


@app.get("/analyze", response_class=HTMLResponse)
def analyze_get() -> str:
    """GET /analyze: usage page with links. Use POST with JSON body for analysis."""
    return _ANALYZE_HTML


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    """Full analysis: rules + AI fix suggestions + generated tests."""
    issues, code, lang = _run_check(req)
    ai_suggestions = ai_svc.suggest_fixes(issues, code=code, language=lang)
    generated_tests: Optional[str] = None
    if code and lang:
        generated_tests = ai_svc.generate_tests(code, lang, issues)
    return AnalyzeResponse(
        issues=issues,
        ai_fix_suggestions=ai_suggestions,
        generated_tests=generated_tests,
    )
