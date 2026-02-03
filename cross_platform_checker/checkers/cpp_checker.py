"""
C++-specific checks.
"""

from deps import List

from ..checker_base import BaseChecker
from ..issue import Severity


class CppChecker(BaseChecker):
    """C++-specific cross-platform checks."""
    
    def _run_checks(self):
        """Run C++-specific checks."""
        self._check_filesystem_usage()
        self._check_windows_types()
    
    def _check_filesystem_usage(self):
        """Check for filesystem usage."""
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
        """Check for Windows-specific types."""
        for i, line in enumerate(self.lines, 1):
            if 'DWORD' in line or 'HANDLE' in line or 'LPSTR' in line:
                if not self._is_comment(line):
                    self._add_issue(
                        Severity.ERROR, i, 0,
                        "Windows-specific type detected",
                        line.strip(),
                        "Use standard C++ types or add platform guards",
                        "TYPE_DEFINITION"
                    )
