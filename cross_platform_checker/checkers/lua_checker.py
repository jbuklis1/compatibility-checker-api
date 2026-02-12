"""
Lua-specific checks for cross-platform compatibility.
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


class LuaChecker(BaseChecker):
    """Lua-specific cross-platform checks (paths, platform detection)."""

    def _run_checks(self):
        """Run Lua-specific checks."""
        self._check_hardcoded_paths()
        self._check_variable_path_usage()
        self._check_platform_detection()

    def _check_hardcoded_paths(self):
        """Flag hardcoded Windows drive and Unix-style paths in file-path context."""
        drive_pattern = re.compile(r'["\'][A-Za-z]:[/\\]')
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
            if not is_file_path_context(line, "lua"):
                continue
            if is_likely_url_or_display(line):
                continue
            match = drive_pattern.search(line)
            if match and not is_likely_url_or_display(line, match.group(0)):
                self._add_issue(
                    Severity.ERROR, i, match.start(),
                    "Hardcoded Windows drive path detected",
                    line.strip(),
                    "Use package.config and portable path building (path separator)",
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
                        "Use portable path building or os.getenv for home/tmp",
                        "HARDCODED_PATH",
                    )
                    break

    def _check_variable_path_usage(self):
        """Warn when a variable is used as file path."""
        for i, line in enumerate(self.lines, 1):
            if not is_file_path_context(line, "lua"):
                continue
            if is_likely_url_or_display(line):
                continue
            if not has_variable_path_argument(line, "lua"):
                continue
            self._add_issue(
                Severity.WARNING, i, 0,
                "Variable used as file path; ensure it is built with portable path segments",
                line.strip(),
                "Use package.config path separator and portable segments",
                "PATH_HANDLING",
            )

    def _check_platform_detection(self):
        """Info: jit.os / jit.arch (LuaJIT) - document target platforms."""
        for i, line in enumerate(self.lines, 1):
            if self._is_comment(line):
                continue
            for pattern in (r"jit\.os", r"jit\.arch", r"package\.config"):
                m = re.search(pattern, line)
                if m and not position_inside_string_literal(line, m.start()):
                    self._add_issue(
                        Severity.INFO, i, m.start(),
                        "Platform or path config used; ensure all target platforms are handled",
                        line.strip(),
                        "Document platform assumptions and test on each target",
                        "PLATFORM_DETECTION",
                    )
                    break
