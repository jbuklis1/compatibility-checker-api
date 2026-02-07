"""
C#-specific checks for cross-platform compatibility.
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


class CSharpChecker(BaseChecker):
    """C#-specific cross-platform checks (paths, OS/platform APIs)."""

    def _run_checks(self):
        """Run C#-specific checks."""
        self._check_hardcoded_paths()
        self._check_variable_path_usage()
        self._check_platform_apis()

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
                    "Use Path.Combine, Path.GetFullPath, or Environment.GetFolderPath for portability",
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
                "Variable used as file path; ensure it is built with Path.Combine or Path.GetFullPath",
                line.strip(),
                "Use Path.Combine, Path.GetFullPath, or Environment.GetFolderPath for portability",
                "PATH_HANDLING",
            )

    def _check_platform_apis(self):
        """Warn on platform-bound APIs (Windows, Mono/Unix)."""
        # DllImport("kernel32"), DllImport("ntdll"), etc. - match the attribute, not the string content
        dll_import = re.compile(r'DllImport\s*\(\s*["\']')
        for i, line in enumerate(self.lines, 1):
            if self._is_comment(line):
                continue
            m = dll_import.search(line)
            if m and not position_inside_string_literal(line, m.start()):
                # Check if library name is Windows-specific (inside the parens string)
                if "kernel32" in line or "ntdll" in line or "user32" in line or "advapi32" in line:
                    self._add_issue(
                        Severity.WARNING, i, m.start(),
                        "Windows-specific DllImport detected",
                        line.strip(),
                        "Use cross-platform APIs or runtime checks (RuntimeInformation.IsOSPlatform)",
                        "PLATFORM_API",
                    )
                    continue
            if "Microsoft.Win32" in line and not position_inside_string_literal(line, line.find("Microsoft.Win32")):
                self._add_issue(
                    Severity.WARNING, i, line.find("Microsoft.Win32"),
                    "Windows-specific namespace: Microsoft.Win32",
                    line.strip(),
                    "Use cross-platform APIs or RuntimeInformation.IsOSPlatform guards",
                    "PLATFORM_API",
                )
                continue
            if "Mono.Unix" in line or "Mono.Posix" in line:
                idx = line.find("Mono.Unix") if "Mono.Unix" in line else line.find("Mono.Posix")
                if not position_inside_string_literal(line, idx):
                    self._add_issue(
                        Severity.WARNING, i, idx,
                        "Mono/Unix-specific namespace; not available on all .NET runtimes",
                        line.strip(),
                        "Use cross-platform .NET APIs or runtime checks",
                        "PLATFORM_API",
                    )
                    continue
            # Informational: platform detection
            if "IsOSPlatform" in line and "OSPlatform." in line:
                idx = line.find("IsOSPlatform")
                if not position_inside_string_literal(line, idx):
                    self._add_issue(
                        Severity.INFO, i, idx,
                        "Platform detection used; ensure all target platforms are handled",
                        line.strip(),
                        "Document platform assumptions and test on each target",
                        "PLATFORM_DETECTION",
                    )
