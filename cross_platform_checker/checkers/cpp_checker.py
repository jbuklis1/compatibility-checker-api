"""
C/C++-specific checks.
"""

import re
from deps import List

from ..checker_base import BaseChecker
from ..issue import Severity
from ..utils import position_inside_string_literal


class CppChecker(BaseChecker):
    """C/C++-specific cross-platform checks (used for both .c/.h and .cpp/.hpp)."""

    def _run_checks(self):
        """Run C/C++-specific checks."""
        self._check_filesystem_usage()
        self._check_windows_types()
        self._check_display_server_apis()
    
    def _check_filesystem_usage(self):
        """Check for C++ filesystem usage (C++ only; C has no std::filesystem)."""
        if self.language != "cpp":
            return
        for i, line in enumerate(self.lines, 1):
            if '<filesystem>' in line or 'std::filesystem' in line:
                self._add_issue(
                    Severity.INFO, i, 0,
                    "std::filesystem usage detected (requires C++17)",
                    line.strip(),
                    "Ensure C++17 is enabled and available on all target platforms",
                    "CPP_STANDARD"
                )
    
    def _check_windows_types(self):
        """Check for Windows-specific types (whole-word match to avoid flagging e.g. ARG_HANDLER)."""
        word_bound = re.compile(r"\b(DWORD|HANDLE|LPSTR)\b")
        for i, line in enumerate(self.lines, 1):
            if self._is_comment(line):
                continue
            for m in word_bound.finditer(line):
                self._add_issue(
                    Severity.ERROR, i, m.start(),
                    "Windows-specific type detected",
                    line.strip(),
                    "Use standard C++ types or add platform guards",
                    "TYPE_DEFINITION",
                )
                break

    def _check_display_server_apis(self):
        """Warn on X11/Wayland API usage for Unix display-server portability."""
        x11_symbols = (
            r'\bXOpenDisplay\b', r'\bXCloseDisplay\b', r'\bXCreateWindow\b',
            r'\bXNextEvent\b', r'\bXFlush\b', r'\bXDefaultScreen\b',
            r'\bxcb_connect\b', r'\bxcb_disconnect\b',
        )
        wayland_symbols = (
            r'\bwl_display_connect\b', r'\bwl_display_disconnect\b',
            r'\bwl_registry\b', r'\bwl_surface\b', r'\bwl_compositor\b',
        )
        for i, line in enumerate(self.lines, 1):
            if self._is_comment(line):
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
