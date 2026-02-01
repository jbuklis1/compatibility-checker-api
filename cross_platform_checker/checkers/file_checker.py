"""
File operation checks.
"""

import re
from typing import List

from ..checker_base import BaseChecker
from ..issue import Severity


class FileChecker(BaseChecker):
    """Checks for file operation issues."""
    
    def _run_checks(self):
        """Run file operation checks."""
        self._check_file_encoding()
        self._check_file_locking()
        self._check_encoding_issues()
    
    def _check_file_encoding(self):
        """Check for binary/text mode issues."""
        for i, line in enumerate(self.lines, 1):
            # Python: check for missing encoding parameter
            if self.language == 'python':
                if re.search(r'open\([^)]+\)', line):
                    if 'encoding=' not in line and 'mode=' in line and 'b' not in line:
                        if 'r' in line or 'w' in line or 'a' in line:
                            self._add_issue(
                                Severity.WARNING, i, 0,
                                "File open without explicit encoding",
                                line.strip(),
                                "Specify encoding='utf-8' for text files to ensure cross-platform compatibility",
                                "FILE_ENCODING"
                            )
    
    def _check_file_locking(self):
        """Check for file locking issues."""
        for i, line in enumerate(self.lines, 1):
            if 'flock' in line or 'fcntl' in line:
                if not self._is_comment(line):
                    self._add_issue(
                        Severity.WARNING, i, 0,
                        "Unix-specific file locking API detected",
                        line.strip(),
                        "Use cross-platform file locking or platform-specific guards",
                        "FILE_LOCKING"
                    )
    
    def _check_encoding_issues(self):
        """Check for encoding-related issues."""
        for i, line in enumerate(self.lines, 1):
            # Check for Windows-1252 or other platform-specific encodings
            if re.search(r'encoding\s*=\s*["\'](windows-1252|cp1252|latin1)["\']', line, re.IGNORECASE):
                self._add_issue(
                    Severity.WARNING, i, 0,
                    "Platform-specific encoding detected",
                    line.strip(),
                    "Use UTF-8 encoding for maximum cross-platform compatibility",
                    "ENCODING"
                )
