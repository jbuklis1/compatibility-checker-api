"""
Python-specific checks.
"""

import re
from typing import List

from ..checker_base import BaseChecker
from ..issue import Severity
from ..utils import (
    has_variable_path_argument,
    is_file_path_context,
    is_likely_url_or_display,
    looks_like_file_path,
)


class PythonChecker(BaseChecker):
    """Python-specific cross-platform checks."""

    def _run_checks(self):
        """Run Python-specific checks."""
        self._check_os_name_usage()
        self._check_pathlib_usage()
        self._check_variable_path_usage()

    def _check_os_name_usage(self):
        """Check for os.name usage."""
        for i, line in enumerate(self.lines, 1):
            if "os.name" in line:
                if "nt" in line or "posix" in line:
                    self._add_issue(
                        Severity.INFO, i, 0,
                        "Direct os.name comparison detected",
                        line.strip(),
                        "Consider using platform.system() for more detailed platform detection",
                        "PLATFORM_DETECTION",
                    )

    def _check_pathlib_usage(self):
        """Check for missing pathlib usage (direct issue in file I/O; candidate in assignment or if)."""
        path_pattern = re.compile(r'["\'][^"\']*[A-Za-z0-9_][/\\][A-Za-z0-9_/\\][^"\']*["\']')
        assign_var = re.compile(r"(\w+)\s*=\s*[\"'][^\"']*[\"']")
        if_condition = re.compile(r"\bif\s+")
        for i, line in enumerate(self.lines, 1):
            if "\\n" in line or "\\t" in line or 'f"' in line or "f'" in line:
                continue
            if "os.path.join" in line or "pathlib" in line or "Path(" in line:
                continue
            match = path_pattern.search(line)
            if not match:
                continue
            matched_str = match.group(0)
            literal = matched_str.strip().strip("'\"")
            if not looks_like_file_path(literal):
                continue
            if is_likely_url_or_display(line, matched_str):
                continue
            if is_file_path_context(line, "python"):
                self._add_issue(
                    Severity.WARNING,
                    i,
                    match.start(),
                    "String path concatenation detected",
                    line.strip(),
                    "Use pathlib.Path or os.path.join() for cross-platform path handling",
                    "PATH_HANDLING",
                )
            elif self.candidates is not None:
                m = assign_var.search(line)
                if m:
                    self._add_candidate(
                        Severity.WARNING,
                        i,
                        match.start(),
                        "String path concatenation detected",
                        line.strip(),
                        "Use pathlib.Path or os.path.join() for cross-platform path handling",
                        "PATH_HANDLING",
                        "variable_path",
                        {"var": m.group(1)},
                    )
                elif if_condition.search(line):
                    self._add_candidate(
                        Severity.WARNING,
                        i,
                        match.start(),
                        "String path concatenation detected",
                        line.strip(),
                        "Use pathlib.Path or os.path.join() for cross-platform path handling",
                        "PATH_HANDLING",
                        "string_in_condition",
                        {"column": match.start()},
                    )

    def _check_variable_path_usage(self):
        """Warn when a variable is used as file path (may be set in another file).

        If pathlib.Path/pathlib APIs are already used on the line, we consider the
        suggestion fulfilled and skip this warning.
        """
        for i, line in enumerate(self.lines, 1):
            if not is_file_path_context(line, "python"):
                continue
            # Using pathlib.Path or pathlib.* already addresses this suggestion.
            if "Path(" in line or "pathlib." in line:
                continue
            if is_likely_url_or_display(line):
                continue
            if not has_variable_path_argument(line, "python"):
                continue
            self._add_issue(
                Severity.WARNING, i, 0,
                "Variable used as file path; ensure it is built with pathlib.Path or os.path.join()",
                line.strip(),
                "Use pathlib.Path or os.path.join() for cross-platform path handling",
                "PATH_HANDLING",
            )
