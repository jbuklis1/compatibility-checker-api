"""
Base checker class for cross-platform compatibility issues.
"""

from deps import List, Optional, Path

from .issue import Issue, Severity
from .utils import detect_language, is_comment


class BaseChecker:
    """Base class for all checkers."""
    
    def __init__(self):
        self.issues: List[Issue] = []
        self.file_path: Optional[Path] = None
        self.language: Optional[str] = None
        self.lines: List[str] = []
    
    def check(self, file_path: Path, lines: List[str], language: str) -> List[Issue]:
        """Run checks on the given file."""
        self.file_path = file_path
        self.language = language
        self.lines = lines
        self.issues = []
        self._run_checks()
        return self.issues
    
    def _run_checks(self):
        """Override in subclasses to implement specific checks."""
        pass
    
    def _add_issue(self, severity: Severity, line_num: int, col: int,
                   message: str, code: str, suggestion: str, category: str):
        """Add an issue to the list."""
        self.issues.append(Issue(
            severity, line_num, col, message, code, suggestion, category
        ))
    
    def _is_comment(self, line: str) -> bool:
        """Check if line is a comment."""
        return is_comment(line)
