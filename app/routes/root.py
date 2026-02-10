"""Root route."""

from deps import APIRouter, HTMLResponse
from ..templates import render_homepage

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def root() -> str:
    """Root: merged homepage with Review tab containing form."""
    return render_homepage()
