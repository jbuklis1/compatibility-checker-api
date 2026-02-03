"""Root route."""

from deps import APIRouter, HTMLResponse
from ..templates import render_template

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def root() -> str:
    """Root: welcome page with clickable links."""
    return render_template("root.html", title="Cross-Platform Compatibility Checker API")
