"""
C/C++-specific checks.
"""

import re
from deps import List

from ..checker_base import BaseChecker
from ..issue import Severity


class CppChecker(BaseChecker):
    """C/C++-specific cross-platform checks (used for both .c/.h and .cpp/.hpp)."""
    
    def _run_checks(self):
        """Run C/C++-specific checks."""
        self._check_filesystem_usage()
        self._check_windows_types()
    
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
