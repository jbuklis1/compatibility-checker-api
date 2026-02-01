"""
System call checks.
"""

from typing import List

from ..checker_base import BaseChecker
from ..issue import Severity


class SystemChecker(BaseChecker):
    """Checks for system call issues."""
    
    def _run_checks(self):
        """Run system call checks."""
        self._check_system_calls()
    
    def _check_system_calls(self):
        """Check for system call issues."""
        system_calls = [
            'system(', 'popen(', 'exec(', 'execv(', 'execvp(',
            'CreateProcess', 'ShellExecute', 'fork()', 'vfork()',
        ]
        
        for i, line in enumerate(self.lines, 1):
            for call in system_calls:
                if call in line and not self._is_comment(line):
                    self._add_issue(
                        Severity.WARNING, i, 0,
                        f"System call detected: {call}",
                        line.strip(),
                        "Ensure command syntax is compatible across platforms or use platform-specific guards",
                        "SYSTEM_CALL"
                    )
