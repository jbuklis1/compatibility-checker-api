"""Checker service: wraps cross_platform_checker and maps to API models."""

import tempfile
from pathlib import Path
from typing import List

from ..config import ensure_checker_import_path
from ..schemas import IssueOut

ensure_checker_import_path()

from cross_platform_checker.main_checker import CrossPlatformChecker
from cross_platform_checker.issue import Issue

_LANG_TO_EXT = {
    "python": ".py",
    "cpp": ".cpp",
    "c": ".c",
    "javascript": ".js",
    "jsx": ".js",
    "typescript": ".ts",
    "java": ".java",
    "go": ".go",
    "rust": ".rs",
    "unknown": ".txt",
}


def _issue_to_out(i: Issue) -> IssueOut:
    return IssueOut(
        severity=i.severity.value,
        line_number=i.line_number,
        column=i.column,
        message=i.message,
        code=i.code,
        suggestion=i.suggestion,
        category=i.category,
    )


class CheckerService:
    """Wraps CrossPlatformChecker for use by the API."""

    def analyze_code(self, code: str, language: str, filename: str = "input") -> List[IssueOut]:
        """Run rule-based checks on raw code. Uses a temp file."""
        ext = _LANG_TO_EXT.get(language.lower(), ".txt")
        base = filename if filename != "input" else "source"
        if base.endswith(ext):
            base = base[: -len(ext)]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=ext, prefix=base + "_", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            path = Path(f.name)
        try:
            issues = CrossPlatformChecker().check_file(path)
            return [_issue_to_out(i) for i in issues]
        finally:
            path.unlink(missing_ok=True)

    def analyze_file(self, file_path: Path) -> List[IssueOut]:
        """Run rule-based checks on a file path."""
        issues = CrossPlatformChecker().check_file(file_path)
        return [_issue_to_out(i) for i in issues]
