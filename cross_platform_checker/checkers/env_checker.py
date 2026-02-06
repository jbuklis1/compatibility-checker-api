"""
Environment variable checks.
"""

import re
from typing import List

from ..checker_base import BaseChecker
from ..issue import Severity


class EnvChecker(BaseChecker):
    """Checks for environment variable issues."""

    def _run_checks(self):
        """Run environment variable checks."""
        self._check_windows_env_syntax()
        self._check_platform_specific_vars()

    def _check_windows_env_syntax(self):
        """Emit candidates for %VAR% syntax; pruner checks if used in env API vs display."""
        for i, line in enumerate(self.lines, 1):
            if self._is_comment(line):
                continue
            for m in re.finditer(r"%[A-Z_]+%", line):
                if self.candidates is not None:
                    self._add_candidate(
                        Severity.ERROR,
                        i,
                        m.start(),
                        "Windows-specific environment variable syntax (%VAR%) detected",
                        line.strip(),
                        "Use os.getenv() (Python), getenv() (C++), or process.env (Node.js)",
                        "ENV_VAR",
                        "string_env_syntax",
                        {"literal": m.group(0), "column": m.start()},
                    )
                else:
                    self._add_issue(
                        Severity.ERROR,
                        i,
                        m.start(),
                        "Windows-specific environment variable syntax (%VAR%) detected",
                        line.strip(),
                        "Use os.getenv() (Python), getenv() (C++), or process.env (Node.js)",
                        "ENV_VAR",
                    )

    def _check_platform_specific_vars(self):
        """Emit candidates for platform var names with word boundary (avoid TEMP in TEMPLATE)."""
        hardcoded_vars = {
            "USERPROFILE": "Use HOME on Unix/macOS",
            "APPDATA": "Use XDG_CONFIG_HOME on Linux, ~/Library on macOS",
            "TEMP": "Use TMPDIR on Unix/macOS",
            "TMP": "Use TMPDIR on Unix/macOS",
        }
        for i, line in enumerate(self.lines, 1):
            if self._is_comment(line):
                continue
            for var, suggestion in hardcoded_vars.items():
                pattern = r"\b" + re.escape(var) + r"\b"
                m = re.search(pattern, line)
                if m:
                    if self.candidates is not None:
                        self._add_candidate(
                            Severity.WARNING,
                            i,
                            m.start(),
                            f"Windows-specific environment variable: {var}",
                            line.strip(),
                            suggestion,
                            "ENV_VAR",
                            "string_platform_var",
                            {"literal": var, "column": m.start()},
                        )
                    else:
                        self._add_issue(
                            Severity.WARNING,
                            i,
                            m.start(),
                            f"Windows-specific environment variable: {var}",
                            line.strip(),
                            suggestion,
                            "ENV_VAR",
                        )
