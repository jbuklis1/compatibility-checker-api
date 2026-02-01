"""
Python-specific checks.
"""

import re
from typing import List

from ..checker_base import BaseChecker
from ..issue import Severity


class PythonChecker(BaseChecker):
    """Python-specific cross-platform checks."""
    
    def _run_checks(self):
        """Run Python-specific checks."""
        self._check_os_name_usage()
        self._check_pathlib_usage()
    
    def _check_os_name_usage(self):
        """Check for os.name usage."""
        for i, line in enumerate(self.lines, 1):
            if 'os.name' in line:
                if 'nt' in line or 'posix' in line:
                    self._add_issue(
                        Severity.INFO, i, 0,
                        "Direct os.name comparison detected",
                        line.strip(),
                        "Consider using platform.system() for more detailed platform detection",
                        "PLATFORM_DETECTION"
                    )
    
    def _check_pathlib_usage(self):
        """Check for missing pathlib usage."""
        # Look for patterns like "path/to/file" or "C:\path" but not "\n" or "\t"
        path_pattern = re.compile(r'["\'][^"\']*[A-Za-z0-9_][/\\][A-Za-z0-9_/\\][^"\']*["\']')
        
        for i, line in enumerate(self.lines, 1):
            if path_pattern.search(line):
                # Exclude common escape sequences and f-string formatting
                if '\\n' not in line and '\\t' not in line and 'f"' not in line and "f'" not in line:
                    if 'os.path.join' not in line and 'pathlib' not in line and 'Path(' not in line:
                        self._add_issue(
                            Severity.WARNING, i, 0,
                            "String path concatenation detected",
                            line.strip(),
                            "Use pathlib.Path or os.path.join() for cross-platform path handling",
                            "PATH_HANDLING"
                        )
