"""
Base checker class for cross-platform compatibility issues.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from .issue import Candidate, Issue, Severity
from .utils import detect_language, is_comment


class BaseChecker:
    """Base class for all checkers."""

    def __init__(self):
        self.issues: List[Issue] = []
        self.file_path: Optional[Path] = None
        self.language: Optional[str] = None
        self.lines: List[str] = []
        self.candidates: Optional[List[Candidate]] = None

    def check(
        self,
        file_path: Path,
        lines: List[str],
        language: str,
        candidates: Optional[List[Candidate]] = None,
    ) -> List[Issue]:
        """Run checks on the given file. Optionally collect candidates for context pruning."""
        self.file_path = file_path
        self.language = language
        self.lines = lines
        self.issues = []
        self.candidates = candidates
        self._run_checks()
        return self.issues

    def _run_checks(self):
        """Override in subclasses to implement specific checks."""
        pass

    def _add_issue(
        self,
        severity: Severity,
        line_num: int,
        col: int,
        message: str,
        code: str,
        suggestion: str,
        category: str,
    ):
        """Add an issue to the list."""
        self.issues.append(
            Issue(severity, line_num, col, message, code, suggestion, category)
        )

    def _add_candidate(
        self,
        severity: Severity,
        line_num: int,
        col: int,
        message: str,
        code: str,
        suggestion: str,
        category: str,
        context_type: str,
        context_data: Optional[Dict[str, Any]] = None,
    ):
        """Add a candidate for context pruning (only if candidate list was passed)."""
        if self.candidates is not None:
            self.candidates.append(
                Candidate(
                    severity=severity,
                    line_number=line_num,
                    column=col,
                    message=message,
                    code=code,
                    suggestion=suggestion,
                    category=category,
                    context_type=context_type,
                    context_data=context_data or {},
                )
            )

    def _is_comment(self, line: str) -> bool:
        """Check if line is a comment."""
        return is_comment(line)
