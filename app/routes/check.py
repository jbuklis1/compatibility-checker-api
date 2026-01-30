"""Check route (rules-only analysis)."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ..schemas import AnalyzeRequest, CheckResponse
from ..templates import render_template
from ..utils import run_check

router = APIRouter()


@router.get("/check", response_class=HTMLResponse)
def check_get() -> str:
    """GET /check: usage page with links. Use POST with JSON body for rules-only analysis."""
    return render_template("check.html", title="Check")


@router.post("/check", response_model=CheckResponse)
def check(req: AnalyzeRequest) -> CheckResponse:
    """Rules-only analysis. No AI."""
    issues, _, _ = run_check(req)
    return CheckResponse(issues=issues)
