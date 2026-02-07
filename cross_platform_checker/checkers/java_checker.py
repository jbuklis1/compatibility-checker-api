"""
Java-specific checks for cross-platform compatibility (stdlib limitations).
"""

import re
from typing import List

from ..checker_base import BaseChecker
from ..issue import Severity
from ..utils import (
    is_file_path_context,
    is_likely_url_or_display,
    looks_like_file_path,
    position_inside_string_literal,
)


class JavaChecker(BaseChecker):
    """Java-specific cross-platform checks (standard library limitations)."""

    def _run_checks(self):
        """Run Java-specific checks."""
        self._check_path_handling()
        self._check_file_reader_writer_encoding()
        self._check_platform_detection()
        self._check_process_builder_single_string()
        self._check_hardcoded_platform_paths()
        self._check_variable_path_usage()

    def _check_path_handling(self):
        """Warn on new File("...") with path-like literals; prefer Paths.get()/Path.of()."""
        # new File("path") with path-like string literal
        file_ctor = re.compile(r"\bnew\s+File\s*\(")
        path_literal = re.compile(r'["\']([^"\']*[\/\\][^"\']*)["\']')
        for i, line in enumerate(self.lines, 1):
            if self._is_comment(line):
                continue
            if "Paths.get(" in line or "Path.of(" in line:
                continue
            for m in file_ctor.finditer(line):
                if position_inside_string_literal(line, m.start()):
                    continue
                # Look for a path-like string literal on this line (could be argument to File)
                for lit in path_literal.finditer(line):
                    literal_content = lit.group(1)
                    if not looks_like_file_path(literal_content) and "/" not in literal_content and "\\" not in literal_content:
                        continue
                    if is_likely_url_or_display(line, lit.group(0)):
                        continue
                    self._add_issue(
                        Severity.WARNING,
                        i,
                        lit.start(),
                        "File path from string literal; use Paths.get() or Path.of() for cross-platform paths",
                        line.strip(),
                        "Use java.nio.file.Paths.get() or Path.of() and avoid hardcoded separators",
                        "PATH_HANDLING",
                    )
                    break
                break
            # String concatenation used as path: "dir" + "/" + "file" or + File.separator +
            if "+" in line and ("/" in line or "File.separator" in line) and is_file_path_context(line, "java"):
                if "Paths.get(" in line or "Path.of(" in line:
                    continue
                sep_concat = re.search(r'["\'][^"\']*["\']\s*\+\s*["\']\s*[/\\]\s*["\']|["\']\s*[/\\]\s*["\']\s*\+|\+\s*File\.separator\s*\+', line)
                if sep_concat and not position_inside_string_literal(line, sep_concat.start()):
                    self._add_issue(
                        Severity.WARNING,
                        i,
                        sep_concat.start(),
                        "String concatenation used as path",
                        line.strip(),
                        "Use Paths.get() or Path.resolve() with Path segments for cross-platform paths",
                        "PATH_HANDLING",
                    )

    def _check_file_reader_writer_encoding(self):
        """Warn that FileReader/FileWriter use platform default encoding."""
        for i, line in enumerate(self.lines, 1):
            if self._is_comment(line):
                continue
            if "Charset" in line or "StandardCharsets" in line or "InputStreamReader" in line or "OutputStreamWriter" in line:
                continue
            for pattern in ("new FileReader(", "new FileWriter("):
                idx = line.find(pattern)
                if idx != -1 and not position_inside_string_literal(line, idx):
                    self._add_issue(
                        Severity.WARNING,
                        i,
                        idx,
                        "FileReader/FileWriter use platform default encoding",
                        line.strip(),
                        "Use Files.newBufferedReader(path, StandardCharsets.UTF_8) or InputStreamReader with explicit Charset",
                        "FILE_ENCODING",
                    )
                    break

    def _check_platform_detection(self):
        """Info: System.getProperty('os.name') / 'file.separator' - document target platforms."""
        prop_pattern = re.compile(
            r'System\.getProperty\s*\(\s*["\'](os\.name|file\.separator)["\']'
        )
        for i, line in enumerate(self.lines, 1):
            if self._is_comment(line):
                continue
            for m in prop_pattern.finditer(line):
                if position_inside_string_literal(line, m.start()):
                    continue
                self._add_issue(
                    Severity.INFO,
                    i,
                    m.start(),
                    "Platform-specific property access; ensure all target platforms are handled",
                    line.strip(),
                    "Use File.separator or java.nio.file.Path APIs where possible; document platform assumptions",
                    "PLATFORM_DETECTION",
                )
                break

    def _check_process_builder_single_string(self):
        """Warn: ProcessBuilder with single string is shell-dependent."""
        for i, line in enumerate(self.lines, 1):
            if self._is_comment(line):
                continue
            # new ProcessBuilder("single string") - one string arg
            m = re.search(r"new\s+ProcessBuilder\s*\(\s*[\"']", line)
            if m and not position_inside_string_literal(line, m.start()):
                self._add_issue(
                    Severity.WARNING,
                    i,
                    m.start(),
                    "ProcessBuilder with single string invokes shell; behavior is platform-specific",
                    line.strip(),
                    "Use ProcessBuilder with array of arguments and avoid shell-builtin commands",
                    "PROCESS_EXEC",
                )

    def _check_hardcoded_platform_paths(self):
        """Hardcoded platform paths in file-path context (Java-specific context)."""
        patterns = [
            (r'["\']C:\\', "Windows drive letter"),
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
            if not is_file_path_context(line, "java"):
                continue
            if is_likely_url_or_display(line):
                continue
            for pattern, desc in patterns:
                m = re.search(pattern, line)
                if m:
                    self._add_issue(
                        Severity.ERROR,
                        i,
                        m.start(),
                        f"Hardcoded {desc} path detected",
                        line.strip(),
                        "Use environment variables or Paths.get() with portable segments",
                        "HARDCODED_PATH",
                    )
                    break

    def _check_variable_path_usage(self):
        """Warn when a variable is used as file path (may come from elsewhere)."""
        from ..utils import has_variable_path_argument
        for i, line in enumerate(self.lines, 1):
            if not is_file_path_context(line, "java"):
                continue
            if is_likely_url_or_display(line):
                continue
            if not has_variable_path_argument(line, "java"):
                continue
            self._add_issue(
                Severity.WARNING,
                i,
                0,
                "Variable used as file path; ensure it is built with Paths.get() or Path APIs",
                line.strip(),
                "Use Paths.get() or Path.resolve() for cross-platform paths",
                "PATH_HANDLING",
            )
