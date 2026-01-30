"""Route handlers."""

from .analyze import router as analyze_router
from .check import router as check_router
from .health import router as health_router
from .review import router as review_router
from .root import router as root_router

__all__ = ["root_router", "health_router", "check_router", "analyze_router", "review_router"]
