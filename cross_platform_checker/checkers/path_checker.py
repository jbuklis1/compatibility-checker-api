"""
Path-related cross-platform compatibility checks.
"""

import re
from typing import List

from ..checker_base import BaseChecker
from ..issue import Severity
from ..utils import is_file_path_context, is_likely_url_or_display


class PathChecker(BaseChecker):
    """Checks for path-related issues."""

    def _run_checks(self):
        """Run path-related checks."""
        self._check_path_separators()
        self._check_hardcoded_paths()

    def _check_path_separators(self):
        """Check for hardcoded path separators (only in file I/O context; suppress URLs/display)."""
        escape_sequences = ['\\n', '\\t', '\\r', '\\b', '\\f', '\\v', '\\a', '\\"', "\\'", '\\\\']
        path_sep_pattern = re.compile(r'[A-Za-z0-9_/]\\[A-Za-z0-9_/]|["\']\w*:\\|["\']\w+\\\w+')
        for i, line in enumerate(self.lines, 1):
            if self._is_comment(line):
                continue
            if not is_file_path_context(line, self.language or "python"):
                continue
            if is_likely_url_or_display(line):
                continue
            # Windows backslash in path contexts
            if "\\" in line and path_sep_pattern.search(line):
                if not any(esc in line for esc in escape_sequences):
                    self._add_issue(
                        Severity.ERROR, i, line.find("\\"),
                        "Hardcoded Windows path separator (backslash) detected",
                        line.strip(),
                        "Use os.path.join() (Python), std::filesystem::path (C++), or path.join() (Node.js)",
                        "PATH_SEPARATOR",
                    )
            # Unix forward slash in path contexts
            if re.search(r'["\']([A-Z]:)?[/\\]', line) and ("/home/" in line or "/usr/" in line or "/etc/" in line):
                self._add_issue(
                    Severity.WARNING, i, 0,
                    "Hardcoded Unix-style path detected",
                    line.strip(),
                    "Use platform-agnostic path APIs instead",
                    "HARDCODED_PATH",
                )

    def _check_hardcoded_paths(self):
        """Check for hardcoded absolute paths (direct issue in file I/O; candidate in assignment)."""
        patterns = [
            (r'["\']C:\\', 'Windows drive letter'),
            (r'["\']/home/', 'Unix home directory'),
            (r'["\']/Users/', 'macOS home directory'),
            (r'["\']/usr/', 'Unix system directory'),
            (r'["\']/etc/', 'Unix config directory'),
            (r'["\']/tmp/', 'Unix temp directory'),
            (r'["\']/var/', 'Unix variable directory'),
        ]
        assign_var = re.compile(r"(\w+)\s*=\s*[\"'][^\"']*[\"']")
        for i, line in enumerate(self.lines, 1):
            if self._is_comment(line):
                continue
            if is_likely_url_or_display(line):
                continue
            for pattern, desc in patterns:
                if not re.search(pattern, line):
                    continue
                in_file_context = is_file_path_context(line, self.language or "python")
                if in_file_context:
                    self._add_issue(
                        Severity.ERROR,
                        i,
                        0,
                        f"Hardcoded {desc} path detected",
                        line.strip(),
                        "Use environment variables or platform APIs (os.path.expanduser, getenv('HOME'), etc.)",
                        "HARDCODED_PATH",
                    )
                elif self.candidates is not None:
                    m = assign_var.search(line)
                    var = m.group(1) if m else None
                    if var:
                        self._add_candidate(
                            Severity.ERROR,
                            i,
                            0,
                            f"Hardcoded {desc} path detected",
                            line.strip(),
                            "Use environment variables or platform APIs (os.path.expanduser, getenv('HOME'), etc.)",
                            "HARDCODED_PATH",
                            "variable_path",
                            {"var": var},
                        )
                break
