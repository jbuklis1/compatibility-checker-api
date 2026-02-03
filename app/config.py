"""Configuration from environment."""

import sys
from pathlib import Path as _Path

_app_dir = _Path(__file__).resolve().parent
_project_root = _app_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from deps import load_dotenv, os, Path

load_dotenv()


def get_together_api_key() -> str:
    """Together.ai API key (required for AI features)."""
    return os.environ.get("TOGETHER_API_KEY", "").strip()


def get_together_model() -> str:
    """Together.ai model. Default: deepseek-ai/DeepSeek-V3.1."""
    return os.environ.get("TOGETHER_MODEL", "deepseek-ai/DeepSeek-V3.1").strip()


def get_host() -> str:
    return os.environ.get("HOST", "0.0.0.0").strip()


def get_port() -> int:
    try:
        return int(os.environ.get("PORT", "8000"))
    except ValueError:
        return 8000


def ensure_checker_import_path() -> None:
    """Add project root to sys.path so cross_platform_checker is importable."""
    import sys

    app_dir = Path(__file__).resolve().parent
    # app -> compatibility-checker-api (project root, contains cross_platform_checker)
    project_root = app_dir.parent
    s = str(project_root)
    if s not in sys.path:
        sys.path.insert(0, s)
