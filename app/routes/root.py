"""Root route."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ..templates import render_template

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def root() -> str:
    """Root: welcome page with clickable links."""
    return render_template("root.html", title="Cross-Platform Compatibility Checker API")
