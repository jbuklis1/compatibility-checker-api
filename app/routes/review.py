"""Review route (form-based file analysis)."""

import json
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

from fastapi import APIRouter, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, Response

from ..report_formatter import format_text_report
from ..schemas import AnalyzeRequest, IssueOut
from ..services import AIService
from ..templates import render_review_form, render_review_results
from ..utils import run_check

LOG_PATH = Path("/home/j/Documents/code/cursor/.cursor/debug.log")

router = APIRouter()
ai_svc = AIService()

# Cache analysis results: key = file_path, value = (issues, code, lang, ai_suggestions, generated_tests, timestamp)
_results_cache: Dict[str, Tuple[list, Optional[str], Optional[str], Optional[str], Optional[str], float]] = {}
CACHE_TTL = 300.0  # 5 minutes


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


@router.get("/review", response_class=HTMLResponse)
def review_get() -> str:
    """Form: enter file path for analysis."""
    return render_review_form()


def _analyze_file(file_path: str, use_cache: bool = True):
    """Helper to run analysis on a file. Returns (issues, code, lang, ai_suggestions, generated_tests)."""
    # #region agent log
    _agent_log("routes/review.py:_analyze_file", "entry", "H1", {"file_path": file_path, "use_cache": use_cache})
    # #endregion
    
    # Check cache first
    if use_cache and file_path in _results_cache:
        cached = _results_cache[file_path]
        issues, code, lang, ai_suggestions, generated_tests, cache_time = cached
        age = time.time() - cache_time
        # #region agent log
        _agent_log("routes/review.py:_analyze_file", "cache_check", "H2", {"cached": True, "age_seconds": age})
        # #endregion
        if age < CACHE_TTL:
            # #region agent log
            _agent_log("routes/review.py:_analyze_file", "cache_hit", "H2", {"returning_cached": True})
            # #endregion
            return issues, code, lang, ai_suggestions, generated_tests
    
    # #region agent log
    _agent_log("routes/review.py:_analyze_file", "cache_miss_or_bypass", "H3", {"running_analysis": True})
    # #endregion
    
    p = Path(file_path)
    if not p.is_absolute():
        raise HTTPException(400, "file_path must be absolute")
    if not p.exists():
        raise HTTPException(404, f"File not found: {file_path}")
    req = AnalyzeRequest(file_path=file_path)
    issues, code, lang = run_check(req)
    # #region agent log
    _agent_log("routes/review.py:_analyze_file", "before_ai_calls", "H4", {"issue_count": len(issues), "has_code": bool(code), "has_lang": bool(lang)})
    # #endregion
    ai_suggestions = ai_svc.suggest_fixes(issues, code=code, language=lang)
    # #region agent log
    _agent_log("routes/review.py:_analyze_file", "after_suggest_fixes", "H4", {"ai_suggestions_made": True})
    # #endregion
    generated_tests = ai_svc.generate_tests(code or "", lang or "unknown", issues) if (code and lang) else None
    # #region agent log
    _agent_log("routes/review.py:_analyze_file", "after_generate_tests", "H4", {"generated_tests_made": True})
    # #endregion
    
    # Cache the results
    _results_cache[file_path] = (issues, code, lang, ai_suggestions, generated_tests, time.time())
    # #region agent log
    _agent_log("routes/review.py:_analyze_file", "cached_results", "H2", {"cache_size": len(_results_cache)})
    # #endregion
    
    return issues, code, lang, ai_suggestions, generated_tests


@router.post("/review", response_class=HTMLResponse)
def review_post(file_path: str = Form(default="")) -> str:
    """Run analysis on file path and render results."""
    file_path = (file_path or "").strip()
    if not file_path:
        return render_review_form(error="File path is required.", value=file_path)
    try:
        issues, code, lang, ai_suggestions, generated_tests = _analyze_file(file_path)
        return render_review_results(file_path, issues, ai_suggestions, generated_tests)
    except HTTPException as e:
        return render_review_form(error=e.detail, value=file_path)


@router.get("/review/download")
def review_download(file_path: str = Query(...)) -> Response:
    """Download analysis results as a text file. Uses cached results if available."""
    # #region agent log
    _agent_log("routes/review.py:review_download", "entry", "H1", {"file_path": file_path})
    # #endregion
    file_path = file_path.strip()
    if not file_path:
        raise HTTPException(400, "file_path query parameter is required")
    try:
        # Use cache to avoid re-running AI calls
        issues, code, lang, ai_suggestions, generated_tests = _analyze_file(file_path, use_cache=True)
        # #region agent log
        _agent_log("routes/review.py:review_download", "after_analyze", "H1", {"issue_count": len(issues)})
        # #endregion
        report_text = format_text_report(file_path, issues, ai_suggestions, generated_tests)
        filename = Path(file_path).name + "_compatibility_report.txt"
        return Response(
            content=report_text,
            media_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error generating report: {str(e)}")
