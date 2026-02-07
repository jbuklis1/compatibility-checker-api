"""
JavaScript/Node.js-specific checks.
"""

import re
from typing import List

from ..checker_base import BaseChecker
from ..issue import Severity
from ..utils import (
    has_variable_path_argument,
    is_file_path_context,
    is_likely_url_or_display,
)


class JavaScriptChecker(BaseChecker):
    """JavaScript/Node.js-specific cross-platform checks."""

    def _run_checks(self):
        """Run JavaScript-specific checks."""
        self._check_hardcoded_paths()
        self._check_variable_path_usage()

    def _check_variable_path_usage(self):
        """Warn when a variable is used as file path (may be set in another file)."""
        for i, line in enumerate(self.lines, 1):
            if not is_file_path_context(line, self.language):
                continue
            if is_likely_url_or_display(line):
                continue
            if not has_variable_path_argument(line, self.language):
                continue
            self._add_issue(
                Severity.WARNING, i, 0,
                "Variable used as file path; ensure it is built with path.join() or path.resolve()",
                line.strip(),
                "Use path.join() or path.resolve() with process.platform checks",
                "PATH_HANDLING",
            )

    def _check_hardcoded_paths(self):
        """Check for hardcoded paths (only in file I/O context; suppress URLs/display)."""
        drive_pattern = re.compile(r'["\'][A-Z]:[/\\]')
        for i, line in enumerate(self.lines, 1):
            match = drive_pattern.search(line)
            if not match:
                continue
            if not is_file_path_context(line, self.language):
                continue
            if is_likely_url_or_display(line, match.group(0)):
                continue
            self._add_issue(
                Severity.ERROR, i, 0,
                "Hardcoded Windows drive path detected",
                line.strip(),
                "Use path.join() or path.resolve() with process.platform checks",
                "PATH_HANDLING",
            )
