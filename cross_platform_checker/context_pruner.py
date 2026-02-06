"""
Context pruner: uses file-scope (assignments and usages) to promote or drop candidates.
"""

import re
from typing import Dict, List, Set, Tuple

from .issue import Candidate, Issue, Severity
from .utils import FILE_PATH_CONTEXT_PYTHON, is_comment, looks_like_file_path

# Env API indicators (string/variable used as env var name or value).
ENV_API_INDICATORS = (
    "getenv(",
    "os.environ",
    "os.getenv(",
    "process.env",
    "subprocess.",
    "environ[",
    "environ.get(",
)
# Display-only: not relevant for path/env issues.
DISPLAY_INDICATORS = ("print(", "log(", "logger.", "message", "display", "repr(")
ENV_SYNTAX_PATTERN = re.compile(r"%[A-Z_]+%")
PLATFORM_VAR_NAMES = {"TEMP", "TMP", "USERPROFILE", "APPDATA"}


def _classify_literal(literal: str) -> str:
    """Classify a string literal as 'path', 'env_syntax', 'platform_var', or 'other'."""
    if ENV_SYNTAX_PATTERN.search(literal):
        return "env_syntax"
    if literal.strip() in PLATFORM_VAR_NAMES:
        return "platform_var"
    if looks_like_file_path(literal):
        return "path"
    return "other"


def _build_assignment_map_python(lines: List[str]) -> Dict[str, Tuple[int, str, str]]:
    """Build var_name -> (line_num, literal_value, kind) for Python."""
    result: Dict[str, Tuple[int, str, str]] = {}
    pattern = re.compile(r"(\w+)\s*=\s*[\"']([^\"']*)[\"']")
    for i, line in enumerate(lines, 1):
        if is_comment(line):
            continue
        match = pattern.search(line)
        if match:
            var_name, literal = match.group(1), match.group(2)
            kind = _classify_literal(literal)
            if kind != "other":
                result[var_name] = (i, literal, kind)
    return result


def _build_usage_map_python(lines: List[str]) -> Dict[str, List[str]]:
    """Build var_name -> list of usage types ('file_io', 'env_api', 'display') for Python."""
    result: Dict[str, List[str]] = {}
    file_io_var = re.compile(
        r"(?:open|Path|exists|isfile|isdir|chdir|listdir|expanduser|abspath|realpath)\s*\(\s*(?![\"'])([a-zA-Z_][a-zA-Z0-9_.]*)\s*[,)]"
    )
    env_var = re.compile(r"getenv\s*\(\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*[,)]")
    env_var_str = re.compile(r"getenv\s*\(\s*[\"']([^\"']+)[\"']")
    for i, line in enumerate(lines, 1):
        if is_comment(line):
            continue
        for m in file_io_var.finditer(line):
            var = m.group(1)
            result.setdefault(var, []).append("file_io")
        for m in env_var.finditer(line):
            var = m.group(1)
            result.setdefault(var, []).append("env_api")
        for m in env_var_str.finditer(line):
            pass
    return result


def _line_usage_types(line: str) -> Set[str]:
    """Classify line as containing file_io, env_api, and/or display usage."""
    types: Set[str] = set()
    if any(ctx in line for ctx in FILE_PATH_CONTEXT_PYTHON):
        types.add("file_io")
    if any(ind in line for ind in ENV_API_INDICATORS):
        types.add("env_api")
    if any(ind in line for ind in DISPLAY_INDICATORS):
        types.add("display")
    return types


def _build_line_usage(lines: List[str]) -> Dict[int, Set[str]]:
    """Build line_number -> set of usage types for string-in-line candidates."""
    return {i: _line_usage_types(line) for i, line in enumerate(lines, 1)}


class ContextPruner:
    """Promotes or drops candidates using file-scope context (assignments and usages)."""

    def __init__(self, lines: List[str], language: str, candidates: List[Candidate]):
        self.lines = lines
        self.language = language
        self.candidates = candidates
        self._assignment_map: Dict[str, Tuple[int, str, str]] = {}
        self._usage_map: Dict[str, List[str]] = {}
        self._line_usage: Dict[int, Set[str]] = {}

    def _build_context(self):
        if self.language == "python":
            self._assignment_map = _build_assignment_map_python(self.lines)
            self._usage_map = _build_usage_map_python(self.lines)
        self._line_usage = _build_line_usage(self.lines)

    def _should_promote_variable_path(self, context_data: dict) -> bool:
        """Promote if variable is used in file I/O; drop if only in display or not path-related."""
        var = context_data.get("var")
        if not var:
            return True
        if var in self._assignment_map:
            _, _, kind = self._assignment_map[var]
            if kind != "path":
                return False
        usages = self._usage_map.get(var, [])
        if not usages:
            return True
        if "file_io" in usages:
            return True
        if "display" in usages and "file_io" not in usages and "env_api" not in usages:
            return False
        return True

    def _should_promote_string_in_condition(self, candidate: Candidate) -> bool:
        """Promote if the condition involves a variable used in file I/O."""
        line_num = candidate.line_number
        if line_num < 1 or line_num > len(self.lines):
            return False
        line = self.lines[line_num - 1]
        if any(ctx in line for ctx in FILE_PATH_CONTEXT_PYTHON):
            return True
        for var_name, usages in self._usage_map.items():
            if "file_io" in usages and var_name in line:
                return True
        return False

    def _should_promote_string_env_or_platform(self, candidate: Candidate) -> bool:
        """Promote if line is used in env API; drop if only display; else promote."""
        line_num = candidate.line_number
        line_types = self._line_usage.get(line_num, set())
        if "env_api" in line_types:
            return True
        if "display" in line_types and "env_api" not in line_types and "file_io" not in line_types:
            return False
        return True

    def prune(self) -> List[Issue]:
        """Return list of issues to add (promoted candidates)."""
        self._build_context()
        promoted: List[Issue] = []
        for c in self.candidates:
            if c.context_type == "variable_path":
                if self._should_promote_variable_path(c.context_data):
                    promoted.append(
                        Issue(
                            c.severity,
                            c.line_number,
                            c.column,
                            c.message,
                            c.code,
                            c.suggestion,
                            c.category,
                        )
                    )
            elif c.context_type in ("string_env_syntax", "string_platform_var"):
                if self._should_promote_string_env_or_platform(c):
                    promoted.append(
                        Issue(
                            c.severity,
                            c.line_number,
                            c.column,
                            c.message,
                            c.code,
                            c.suggestion,
                            c.category,
                        )
                    )
            elif c.context_type == "string_in_condition":
                if self._should_promote_string_in_condition(c):
                    promoted.append(
                        Issue(
                            c.severity,
                            c.line_number,
                            c.column,
                            c.message,
                            c.code,
                            c.suggestion,
                            c.category,
                        )
                    )
            else:
                promoted.append(
                    Issue(
                        c.severity,
                        c.line_number,
                        c.column,
                        c.message,
                        c.code,
                        c.suggestion,
                        c.category,
                    )
                )
        return promoted
