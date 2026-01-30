"""AI service status checking."""

import time
from typing import Dict, Optional

from .config import get_together_api_key, get_together_model

# Cache status for 30 seconds to avoid excessive API calls
_status_cache: Optional[Dict[str, any]] = None
_cache_timestamp: float = 0
CACHE_TTL = 30.0  # seconds


def get_ai_status() -> Dict[str, any]:
    """Check AI service availability and return status info."""
    global _status_cache, _cache_timestamp
    
    # Return cached status if still valid
    if _status_cache and (time.time() - _cache_timestamp) < CACHE_TTL:
        return _status_cache
    
    status = {
        "available": False,
        "reason": "",
        "api_key_set": False,
        "openai_available": False,
        "model": get_together_model(),
    }
    
    # Check if openai module is available
    try:
        import openai
        status["openai_available"] = True
    except ImportError:
        status["reason"] = "openai package not installed"
        return status
    
    # Check if API key is set
    key = get_together_api_key()
    if not key:
        status["reason"] = "TOGETHER_API_KEY not set in .env"
        return status
    
    status["api_key_set"] = True
    
    # Check if key looks valid (basic validation)
    if len(key) < 10:
        status["reason"] = "TOGETHER_API_KEY appears invalid (too short)"
        return status
    
    if key.startswith("your_api_key") or key == "your_api_key_here":
        status["reason"] = "TOGETHER_API_KEY not configured (still using placeholder)"
        return status
    
    # Actually test the API key with a minimal request
    try:
        client = openai.OpenAI(api_key=key, base_url="https://api.together.xyz/v1")
        # Make a minimal test request
        test_response = client.chat.completions.create(
            model=status["model"],
            messages=[{"role": "user", "content": "test"}],
            max_tokens=1,
            timeout=5.0,
        )
        status["available"] = True
        status["reason"] = "AI features available"
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg or "Invalid" in error_msg:
            status["reason"] = "TOGETHER_API_KEY is invalid or expired"
        elif "timeout" in error_msg.lower():
            status["reason"] = "API request timed out (check network)"
        else:
            status["reason"] = f"API test failed: {error_msg[:100]}"
    
    # Cache the result
    _status_cache = status
    _cache_timestamp = time.time()
    
    return status
