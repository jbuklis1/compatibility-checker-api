"""AI service: Together.ai for fix suggestions and test generation."""

from typing import List, Optional, Any

from ..config import get_together_api_key, get_together_model
from ..schemas import IssueOut


def _client() -> Optional[Any]:
    """Return OpenAI-compatible client for Together.ai, or None if unavailable."""
    try:
        from openai import OpenAI
    except ImportError:
        return None
    key = get_together_api_key()
    if not key:
        return None
    return OpenAI(api_key=key, base_url="https://api.together.xyz/v1")


def _issues_summary(issues: List[IssueOut]) -> str:
    if not issues:
        return "No rule-based issues found."
    parts = []
    for i in issues:
        parts.append(
            f"- Line {i.line_number} [{i.severity}] {i.category}: {i.message}\n"
            f"  Code: {i.code}\n  Suggestion: {i.suggestion}"
        )
    return "\n".join(parts)


class AIService:
    """Together.ai-backed fix suggestions and test generation."""

    def suggest_fixes(
        self,
        issues: List[IssueOut],
        code: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Optional[str]:
        """Return AI-generated fix suggestions for the given issues. None if AI unavailable."""
        client = _client()
        if not client:
            return None
        model = get_together_model()
        summary = _issues_summary(issues)
        prompt = (
            "You are a cross-platform compatibility expert. Below are compatibility issues "
            "reported by a static checker for code that must run on Windows, macOS, and Linux.\n\n"
            "Issues:\n"
            f"{summary}\n\n"
        )
        if code and language:
            prompt += f"Source code ({language}):\n```\n{code[:8000]}\n```\n\n"
        prompt += (
            "Provide actionable fix suggestions: either per-issue or overall. Be concise. "
            "Focus on platform-agnostic APIs (pathlib, os.path.join, platform.system, etc.). "
            "Use clear bullet points or numbered steps."
        )
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
            )
            if r.choices and r.choices[0].message.content:
                return r.choices[0].message.content.strip()
        except Exception:
            pass
        return None

    def generate_tests(
        self,
        code: str,
        language: str,
        issues: List[IssueOut],
    ) -> Optional[str]:
        """Return AI-generated test code for cross-platform checks. None if AI unavailable."""
        client = _client()
        if not client:
            return None
        model = get_together_model()
        summary = _issues_summary(issues)
        prompt = (
            "You are a cross-platform compatibility expert. Generate test cases that a developer "
            "can add to their project to verify cross-platform behavior (Windows, macOS, Linux).\n\n"
            f"Language: {language}\n\n"
            "Reported compatibility issues (fix these or assert around them):\n"
            f"{summary}\n\n"
            "Source code:\n"
            f"```\n{code[:8000]}\n```\n\n"
            "Provide concrete, runnable test code (e.g. pytest for Python, or platform-specific "
            "assertions). Include a brief comment explaining what each test checks. Output only "
            "the test code, optionally wrapped in a markdown code block."
        )
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
            )
            if r.choices and r.choices[0].message.content:
                text = r.choices[0].message.content.strip()
                # Strip markdown code block if present
                if text.startswith("```"):
                    lines = text.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    text = "\n".join(lines)
                return text
        except Exception:
            pass
        return None
