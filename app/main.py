"""FastAPI app: main entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import ensure_checker_import_path
from .routes import (
    analyze_router,
    check_router,
    health_router,
    review_router,
    root_router,
)
from .startup import validate_config

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
app.include_router(health_router)
app.include_router(check_router)
app.include_router(analyze_router)
app.include_router(review_router)


@app.on_event("startup")
def startup_event() -> None:
    """Run startup validation."""
    validate_config()
