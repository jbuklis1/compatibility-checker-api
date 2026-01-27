"""Configuration from environment."""

import json
import os
import time
from pathlib import Path

LOG_PATH = Path("/home/j/Documents/code/cursor/.cursor/debug.log")


def _agent_log(location: str, message: str, hypothesis_id: str, data: dict | None = None) -> None:
    # #region agent log
    try:
        payload = {
            "location": location,
            "message": message,
            "hypothesisId": hypothesis_id,
            "data": data or {},
            "timestamp": int(time.time() * 1000),
            "sessionId": "debug-session",
            "runId": "run1",
        }
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        pass
    # #endregion


try:
    from dotenv import load_dotenv
    # #region agent log
    env_file = Path(".env")
    env_exists_before = env_file.exists()
    _agent_log("config.py:load_dotenv", "before load_dotenv", "H1", {"env_exists": env_exists_before})
    # #endregion
    load_dotenv()
    # #region agent log
    env_exists_after = env_file.exists()
    key_set = bool(os.environ.get("TOGETHER_API_KEY", "").strip())
    _agent_log("config.py:load_dotenv", "after load_dotenv", "H2", {"env_exists": env_exists_after, "key_set": key_set})
    # #endregion
except ImportError:
    pass


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
    """Add workspace root to sys.path so cross_platform_checker is importable."""
    import sys

    app_dir = Path(__file__).resolve().parent
    # app -> compatibility-checker-api -> workspace (cursor)
    workspace = app_dir.parent.parent
    s = str(workspace)
    if s not in sys.path:
        sys.path.insert(0, s)
