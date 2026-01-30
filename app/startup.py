"""Startup validation and configuration checks."""

from pathlib import Path

from .config import get_together_api_key


def validate_config() -> None:
    """Validate config at startup and warn if .env or TOGETHER_API_KEY missing."""
    env_file = Path(".env")
    env_exists = env_file.exists()
    key = get_together_api_key()
    key_set = bool(key)
    if not env_exists:
        print("⚠️  WARNING: .env file not found. AI features will be disabled.")
        print("   Create .env from .env.example and set TOGETHER_API_KEY for AI features.")
    elif not key_set:
        print("⚠️  WARNING: TOGETHER_API_KEY not set in .env. AI features will be disabled.")
        print("   Set TOGETHER_API_KEY in .env to enable AI suggestions and test generation.")
