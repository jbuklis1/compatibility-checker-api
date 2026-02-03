"""Health check route."""

from deps import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict:
    """Liveness check."""
    return {"status": "ok"}
