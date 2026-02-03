"""Utility functions for the API."""

from .config import ensure_checker_import_path
from deps import HTTPException, List, Optional, Path, Tuple
from .schemas import AnalyzeRequest, IssueOut
from .services import CheckerService

ensure_checker_import_path()

from cross_platform_checker.utils import detect_language

checker_svc = CheckerService()


def run_check(req: AnalyzeRequest) -> Tuple[List[IssueOut], Optional[str], Optional[str]]:
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
