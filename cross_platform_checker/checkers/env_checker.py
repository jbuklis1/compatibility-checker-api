"""
Environment variable checks.
"""

from deps import List, re

from ..checker_base import BaseChecker
from ..issue import Severity


class EnvChecker(BaseChecker):
    """Checks for environment variable issues."""
    
    def _run_checks(self):
        """Run environment variable checks."""
        self._check_windows_env_syntax()
        self._check_platform_specific_vars()
    
    def _check_windows_env_syntax(self):
        """Check for Windows-specific env var syntax."""
        for i, line in enumerate(self.lines, 1):
            if re.search(r'%[A-Z_]+%', line):
                if not self._is_comment(line):
                    self._add_issue(
                        Severity.ERROR, i, 0,
                        "Windows-specific environment variable syntax (%VAR%) detected",
                        line.strip(),
                        "Use os.getenv() (Python), getenv() (C++), or process.env (Node.js)",
                        "ENV_VAR"
                    )
    
    def _check_platform_specific_vars(self):
        """Check for hardcoded env var names that differ by platform."""
        hardcoded_vars = {
            'USERPROFILE': 'Use HOME on Unix/macOS',
            'APPDATA': 'Use XDG_CONFIG_HOME on Linux, ~/Library on macOS',
            'TEMP': 'Use TMPDIR on Unix/macOS',
            'TMP': 'Use TMPDIR on Unix/macOS',
        }
        
        for i, line in enumerate(self.lines, 1):
            for var, suggestion in hardcoded_vars.items():
                if var in line and not self._is_comment(line):
                    self._add_issue(
                        Severity.WARNING, i, 0,
                        f"Windows-specific environment variable: {var}",
                        line.strip(),
                        suggestion,
                        "ENV_VAR"
                    )
