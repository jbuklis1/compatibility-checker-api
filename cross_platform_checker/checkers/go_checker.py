"""
Go-specific checks for cross-platform compatibility.
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
    position_inside_string_literal,
)


class GoChecker(BaseChecker):
    """Go-specific cross-platform checks (paths, platform detection, env)."""

    def _run_checks(self):
        """Run Go-specific checks."""
        self._check_hardcoded_paths()
        self._check_variable_path_usage()
        self._check_platform_detection()
        self._check_windows_env_in_path_context()

    def _check_hardcoded_paths(self):
        """Flag hardcoded Windows drive and Unix-style paths in file-path context."""
        drive_pattern = re.compile(r'["\'][A-Z]:[/\\]')
        unix_path_patterns = [
            (r'["\']/home/', "Unix home directory"),
            (r'["\']/Users/', "macOS home directory"),
            (r'["\']/usr/', "Unix system directory"),
            (r'["\']/etc/', "Unix config directory"),
            (r'["\']/tmp/', "Unix temp directory"),
            (r'["\']/var/', "Unix variable directory"),
        ]
        for i, line in enumerate(self.lines, 1):
            if self._is_comment(line):
                continue
            if not is_file_path_context(line, "go"):
                continue
            if is_likely_url_or_display(line):
                continue
            match = drive_pattern.search(line)
            if match and not is_likely_url_or_display(line, match.group(0)):
                self._add_issue(
                    Severity.ERROR, i, match.start(),
                    "Hardcoded Windows drive path detected",
                    line.strip(),
                    "Use filepath.Join, os.Getenv, or runtime.GOOS guards for portability",
                    "PATH_HANDLING",
                )
                continue
            for pattern, desc in unix_path_patterns:
                m = re.search(pattern, line)
                if m:
                    lit = m.group(0)
                    if not looks_like_file_path(lit.strip("'\"")):
                        continue
                    if is_likely_url_or_display(line, lit):
                        continue
                    self._add_issue(
                        Severity.ERROR, i, m.start(),
                        f"Hardcoded {desc} path detected",
                        line.strip(),
                        "Use os.Getenv or filepath.Join with portable segments",
                        "HARDCODED_PATH",
                    )
                    break

    def _check_variable_path_usage(self):
        """Warn when a variable is used as file path."""
        for i, line in enumerate(self.lines, 1):
            if not is_file_path_context(line, "go"):
                continue
            if is_likely_url_or_display(line):
                continue
            if not has_variable_path_argument(line, "go"):
                continue
            self._add_issue(
                Severity.WARNING, i, 0,
                "Variable used as file path; ensure it is built with filepath.Join or os.Getenv",
                line.strip(),
                "Use path/filepath and os.Getenv for cross-platform paths",
                "PATH_HANDLING",
            )

    def _check_platform_detection(self):
        """Info: runtime.GOOS / runtime.GOARCH - document target platforms."""
        for i, line in enumerate(self.lines, 1):
            if self._is_comment(line):
                continue
            for pattern in (r"runtime\.GOOS", r"runtime\.GOARCH"):
                m = re.search(pattern, line)
                if m and not position_inside_string_literal(line, m.start()):
                    self._add_issue(
                        Severity.INFO, i, m.start(),
                        "Platform detection used; ensure all target platforms are handled",
                        line.strip(),
                        "Document platform assumptions and test on each target (GOOS/GOARCH)",
                        "PLATFORM_DETECTION",
                    )
                    break

    def _check_windows_env_in_path_context(self):
        """Warn on Windows-only env names in path context (os.Getenv/LookupEnv)."""
        windows_vars = ("USERPROFILE", "APPDATA", "TEMP", "TMP")
        for i, line in enumerate(self.lines, 1):
            if self._is_comment(line):
                continue
            if not is_file_path_context(line, "go"):
                continue
            for var in windows_vars:
                pattern = r'\b(?:os\.Getenv|os\.LookupEnv)\s*\(\s*["\']' + re.escape(var) + r'["\']'
                m = re.search(pattern, line)
                if m and not position_inside_string_literal(line, m.start()):
                    self._add_issue(
                        Severity.WARNING, i, m.start(),
                        f"Windows-specific env var in path context: {var}",
                        line.strip(),
                        "Use portable alternatives (e.g. HOME via os.UserHomeDir) or GOOS guards",
                        "ENV_VAR",
                    )
                    break
