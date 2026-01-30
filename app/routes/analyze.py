"""Analyze route (full analysis with AI)."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ..schemas import AnalyzeRequest, AnalyzeResponse
from ..services import AIService
from ..templates import render_template
from ..utils import run_check

router = APIRouter()
ai_svc = AIService()


@router.get("/analyze", response_class=HTMLResponse)
def analyze_get() -> str:
    """GET /analyze: usage page with links. Use POST with JSON body for analysis."""
    return render_template("analyze.html", title="Analyze")


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    """Full analysis: rules + AI fix suggestions + generated tests."""
    issues, code, lang = run_check(req)
    ai_suggestions = ai_svc.suggest_fixes(issues, code=code, language=lang)
    generated_tests = None
    if code and lang:
        generated_tests = ai_svc.generate_tests(code, lang, issues)
    return AnalyzeResponse(
        issues=issues,
        ai_fix_suggestions=ai_suggestions,
        generated_tests=generated_tests,
    )
