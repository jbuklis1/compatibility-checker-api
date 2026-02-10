"""FastAPI app: main entry point."""

from urllib.parse import urlparse

from .config import ensure_checker_import_path
from deps import CORSMiddleware, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.requests import Request
from .routes import (
    review_router,
    root_router,
)
from .startup import validate_config
from .templates import render_homepage

ensure_checker_import_path()

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

# Register routes
app.include_router(root_router)
app.include_router(review_router)


def _redirect_url_for_unknown_path(request: Request) -> str:
    """Choose redirect target from Referer: home, #review, or results (/#review)."""
    referer = request.headers.get("referer") or ""
    base = str(request.base_url).rstrip("/")
    if not referer or not referer.startswith(base):
        return "/"
    parsed = urlparse(referer)
    path = (parsed.path or "/").rstrip("/") or "/"
    fragment = parsed.fragment or ""
    if "review" in path or "results" in path.lower() or fragment == "review":
        return "/#review"
    return "/"


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"])
async def catch_all_redirect(request: Request, full_path: str):
    """Redirect any unmatched path so invalid URLs don't show raw errors; target from Referer."""
    url = _redirect_url_for_unknown_path(request)
    return RedirectResponse(url=url, status_code=302)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Return merged homepage with review tab open and error for 'Too many files' 400 on POST /review/results."""
    if (
        request.method == "POST"
        and request.url.path.rstrip("/") == "/review/results"
        and "Too many files" in str(exc.detail)
    ):
        html = render_homepage(review_tab_open=True, form_error="Too many files. Maximum number of files is 1000.")
        return HTMLResponse(html)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.on_event("startup")
def startup_event() -> None:
    """Run startup validation."""
    validate_config()
