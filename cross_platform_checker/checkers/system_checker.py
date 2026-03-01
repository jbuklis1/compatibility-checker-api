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
            if self._is_comment(line):
                continue
            in_string = False
            quote_char = None
            j = 0
            while j < len(line):
                ch = line[j]
                if not in_string:
                    if ch == '#':
                        break
                    if ch == '/' and j + 1 < len(line) and line[j + 1] == '/':
                        break
                    if ch in ('"', "'") and (j == 0 or line[j - 1] != '\\'):
                        in_string = True
                        quote_char = ch
                        j += 1
                        continue
                    for call in system_calls:
                        if line.startswith(call, j):
                            if call == 'exec(' and self.language in ('c', 'cpp') and self.candidates is not None:
                                self._add_candidate(
                                    Severity.WARNING, i, j,
                                    f"System call detected: {call}",
                                    line.strip(),
                                    "Ensure command syntax is compatible across platforms or use platform-specific guards",
                                    "SYSTEM_CALL",
                                    "exec_call",
                                    {},
                                )
                            else:
                                self._add_issue(
                                    Severity.WARNING, i, j,
                                    f"System call detected: {call}",
                                    line.strip(),
                                    "Ensure command syntax is compatible across platforms or use platform-specific guards",
                                    "SYSTEM_CALL",
                                )
                            j += len(call)
                            break
                    else:
                        j += 1
                else:
                    if ch == quote_char and (j == 0 or line[j - 1] != '\\'):
                        in_string = False
                        quote_char = None
                    j += 1
