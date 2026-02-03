"""
Path-related cross-platform compatibility checks.
"""

from deps import List, re

from ..checker_base import BaseChecker
from ..issue import Severity


class PathChecker(BaseChecker):
    """Checks for path-related issues."""
    
    def _run_checks(self):
        """Run path-related checks."""
        self._check_path_separators()
        self._check_hardcoded_paths()
    
    def _check_path_separators(self):
        """Check for hardcoded path separators."""
        for i, line in enumerate(self.lines, 1):
            # Check for Windows backslash in path contexts
            if '\\' in line and not self._is_comment(line):
                # Check if it's a path separator (not an escape sequence)
                path_sep_pattern = re.compile(r'[A-Za-z0-9_/]\\[A-Za-z0-9_/]|["\']\w*:\\|["\']\w+\\\w+')
                if path_sep_pattern.search(line):
                    # Exclude common escape sequences
                    escape_sequences = ['\\n', '\\t', '\\r', '\\b', '\\f', '\\v', '\\a', '\\"', "\\'", '\\\\']
                    is_escape = any(esc in line for esc in escape_sequences)
                    if not is_escape:
                        self._add_issue(
                            Severity.ERROR, i, line.find('\\'),
                            "Hardcoded Windows path separator (backslash) detected",
                            line.strip(),
                            "Use os.path.join() (Python), std::filesystem::path (C++), or path.join() (Node.js)",
                            "PATH_SEPARATOR"
                        )
            
            # Check for Unix forward slash in path contexts
            if re.search(r'["\']([A-Z]:)?[/\\]', line):
                if '/home/' in line or '/usr/' in line or '/etc/' in line:
                    self._add_issue(
                        Severity.WARNING, i, 0,
                        "Hardcoded Unix-style path detected",
                        line.strip(),
                        "Use platform-agnostic path APIs instead",
                        "HARDCODED_PATH"
                    )
    
    def _check_hardcoded_paths(self):
        """Check for hardcoded absolute paths."""
        patterns = [
            (r'["\']C:\\', 'Windows drive letter'),
            (r'["\']/home/', 'Unix home directory'),
            (r'["\']/Users/', 'macOS home directory'),
            (r'["\']/usr/', 'Unix system directory'),
            (r'["\']/etc/', 'Unix config directory'),
            (r'["\']/tmp/', 'Unix temp directory'),
            (r'["\']/var/', 'Unix variable directory'),
        ]
        
        for i, line in enumerate(self.lines, 1):
            for pattern, desc in patterns:
                if re.search(pattern, line):
                    if not self._is_comment(line):
                        self._add_issue(
                            Severity.ERROR, i, 0,
                            f"Hardcoded {desc} path detected",
                            line.strip(),
                            "Use environment variables or platform APIs (os.path.expanduser, getenv('HOME'), etc.)",
                            "HARDCODED_PATH"
                        )
