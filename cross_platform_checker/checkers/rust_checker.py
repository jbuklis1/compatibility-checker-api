"""
Rust-specific checks for cross-platform compatibility.
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


class RustChecker(BaseChecker):
    """Rust-specific cross-platform checks (paths, display server)."""

    def _run_checks(self):
        """Run Rust-specific checks."""
        self._check_hardcoded_paths()
        self._check_variable_path_usage()
        self._check_display_server_apis()

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
            if not is_file_path_context(line, self.language):
                continue
            if is_likely_url_or_display(line):
                continue
            match = drive_pattern.search(line)
            if match and not is_likely_url_or_display(line, match.group(0)):
                self._add_issue(
                    Severity.ERROR, i, match.start(),
                    "Hardcoded Windows drive path detected",
                    line.strip(),
                    "Use Path::new()/PathBuf::from() with std::path::MAIN_SEPARATOR or env/cfg for portability",
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
                        "Use environment variables or Path APIs for cross-platform paths",
                        "HARDCODED_PATH",
                    )
                    break

    def _check_variable_path_usage(self):
        """Warn when a variable is used as file path."""
        for i, line in enumerate(self.lines, 1):
            if not is_file_path_context(line, self.language):
                continue
            if is_likely_url_or_display(line):
                continue
            if not has_variable_path_argument(line, self.language):
                continue
            self._add_issue(
                Severity.WARNING, i, 0,
                "Variable used as file path; ensure it is built with Path::new/PathBuf::from or Path::join",
                line.strip(),
                "Use std::path::Path/PathBuf and std::path::MAIN_SEPARATOR or cfg for portability",
                "PATH_HANDLING",
            )

    def _check_display_server_apis(self):
        """Warn on X11/Wayland crate or API usage for display-server portability."""
        # use x11::, use x11rb::, wayland_client, wayland_*
        use_x11 = re.compile(r"\buse\s+(?:x11|x11rb|xdg|x11_dl)\s*::")
        use_wayland = re.compile(r"\buse\s+wayland(?:_[a-z]+)?\s*::")
        x11_symbols = (
            r'\bXOpenDisplay\b', r'\bXCloseDisplay\b', r'\bXCreateWindow\b',
            r'\bxcb_connect\b', r'\bxcb_disconnect\b',
        )
        wayland_symbols = (
            r'\bwl_display_connect\b', r'\bwl_display_disconnect\b',
            r'\bwl_registry\b', r'\bwl_surface\b', r'\bwl_compositor\b',
        )
        for i, line in enumerate(self.lines, 1):
            if self._is_comment(line):
                continue
            m = use_x11.search(line)
            if m and not position_inside_string_literal(line, m.start()):
                self._add_issue(
                    Severity.WARNING, i, m.start(),
                    "X11-related crate usage; code may not run on Wayland-only or other display servers",
                    line.strip(),
                    "Use abstraction or cfg for X11/Wayland portability",
                    "DISPLAY_API",
                )
                continue
            m = use_wayland.search(line)
            if m and not position_inside_string_literal(line, m.start()):
                self._add_issue(
                    Severity.WARNING, i, m.start(),
                    "Wayland-related crate usage; code may not run on X11-only systems",
                    line.strip(),
                    "Consider X11/Wayland portability or abstraction layer",
                    "DISPLAY_API",
                )
                continue
            for pat in x11_symbols:
                m = re.search(pat, line)
                if m and not position_inside_string_literal(line, m.start()):
                    self._add_issue(
                        Severity.WARNING, i, m.start(),
                        "X11 API usage; code may not run on Wayland-only or other display servers",
                        line.strip(),
                        "Use abstraction or conditional compilation for X11/Wayland portability",
                        "DISPLAY_API",
                    )
                    break
            for pat in wayland_symbols:
                m = re.search(pat, line)
                if m and not position_inside_string_literal(line, m.start()):
                    self._add_issue(
                        Severity.WARNING, i, m.start(),
                        "Wayland API usage; code may not run on X11-only systems",
                        line.strip(),
                        "Consider X11/Wayland portability or abstraction layer",
                        "DISPLAY_API",
                    )
                    break
