"""
JavaScript/Node.js-specific checks.
"""

from deps import List, re

from ..checker_base import BaseChecker
from ..issue import Severity


class JavaScriptChecker(BaseChecker):
    """JavaScript/Node.js-specific cross-platform checks."""
    
    def _run_checks(self):
        """Run JavaScript-specific checks."""
        self._check_hardcoded_paths()
    
    def _check_hardcoded_paths(self):
        """Check for hardcoded paths."""
        for i, line in enumerate(self.lines, 1):
            # Check for hardcoded paths
            if re.search(r'["\'][A-Z]:[/\\]', line):
                self._add_issue(
                    Severity.ERROR, i, 0,
                    "Hardcoded Windows drive path detected",
                    line.strip(),
                    "Use path.join() or path.resolve() with process.platform checks",
                    "PATH_HANDLING"
                )
