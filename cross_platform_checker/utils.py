"""
Utility functions for cross-platform compatibility checker.
"""

import re
from pathlib import Path
from typing import Optional

# Substrings that indicate the line is dealing with file I/O or path APIs.
FILE_PATH_CONTEXT_PYTHON = (
    "open(", "with open", "Path(", "pathlib.", "os.path.", "exists(", "isfile(", "isdir(",
    "chdir(", "listdir(", "glob(", "rglob(", "mkdir", "unlink(", "rename(", "shutil.",
    "expanduser(", "abspath(", "realpath(", "read(", "write(",
)
FILE_PATH_CONTEXT_JAVASCRIPT = (
    "readFile", "writeFile", "existsSync", "path.join", "path.resolve", "path.",
    "fs.readFile", "fs.writeFile", "fs.exists", "fs.stat", "fs.mkdir", "fs.readdir",
)
FILE_PATH_CONTEXT_JAVA = (
    "new File(", "Paths.get(", "Path.of(", "Files.", "FileReader(", "FileWriter(",
    "FileInputStream(", "FileOutputStream(", "RandomAccessFile(",
)
FILE_PATH_CONTEXT_RUST = (
    "std::fs::", "Path::", "PathBuf::", "File::open", "OpenOptions", "read_dir",
    "create_dir", "metadata", "canonicalize", "read_to_string", "write", "copy",
    "remove_file", "remove_dir", "symlink", "std::path::",
)
FILE_PATH_CONTEXT_CSHARP = (
    "Path.Combine", "File.", "Directory.", "FileInfo", "DirectoryInfo", "FileStream",
    "File.Read", "File.Write", "Directory.GetFiles", "Directory.GetDirectories",
    "Path.GetFullPath", "Environment.GetFolderPath",
)

# Substrings that indicate the line is likely URL/API or display text, not a file path.
URL_OR_DISPLAY_INDICATORS = (
    "http://", "https://", "://", "url", "href", "fetch(", "request(", "endpoint",
    "api.", "GET", "POST", "print(", "log(", "message", "display",
)


def is_file_path_context(line: str, language: str = "python") -> bool:
    """True if the line contains file I/O or path API indicators for the given language."""
    if language == "python":
        return any(ctx in line for ctx in FILE_PATH_CONTEXT_PYTHON)
    if language == "javascript" or language == "typescript":
        return any(ctx in line for ctx in FILE_PATH_CONTEXT_JAVASCRIPT)
    if language == "java":
        return any(ctx in line for ctx in FILE_PATH_CONTEXT_JAVA)
    if language == "rust":
        return any(ctx in line for ctx in FILE_PATH_CONTEXT_RUST)
    if language == "csharp":
        return any(ctx in line for ctx in FILE_PATH_CONTEXT_CSHARP)
    return False


def is_likely_url_or_display(line: str, matched_str: str = "") -> bool:
    """True if the line or the matched string looks like a URL or display text."""
    if any(ind in line for ind in URL_OR_DISPLAY_INDICATORS):
        return True
    s = (matched_str or "").strip().strip("'\"")
    return "://" in s or s.startswith("http") or s.startswith("//")


# Regexes: first argument of file I/O call is an identifier/dotted name (not a string literal).
_VAR_PATH_PYTHON = re.compile(
    r"(?:open|Path|exists|isfile|isdir|chdir|listdir|expanduser|abspath|realpath)\s*\(\s*(?![\"'])([a-zA-Z_][a-zA-Z0-9_.]*)\s*[,)]"
)
_VAR_PATH_JAVASCRIPT = re.compile(
    r"(?:readFile|writeFile|existsSync|stat|mkdir|readdir)\s*\(\s*(?![\"'])([a-zA-Z_$][a-zA-Z0-9_.$]*)\s*[,)]"
)
_VAR_PATH_JAVA = re.compile(
    r"(?:new\s+File|Paths\.get|Path\.of|Files\.(?:readAllBytes|write|readAllLines|newBufferedReader|newBufferedWriter|newInputStream|newOutputStream))\s*\(\s*(?![\"'])([a-zA-Z_][a-zA-Z0-9_.]*)\s*[,)]"
)
_VAR_PATH_RUST = re.compile(
    r"(?:File::open|Path::new|PathBuf::from|read_to_string|read_dir|create_dir|metadata|canonicalize|std::fs::(?:read_dir|read_to_string|read|write|create_dir|metadata|canonicalize))\s*\(\s*(?![\"'])([a-zA-Z_][a-zA-Z0-9_.]*)\s*[,)]"
)
_VAR_PATH_CSHARP = re.compile(
    r"(?:File\.(?:ReadAllText|ReadAllBytes|WriteAllText|Exists|Open|Create)|Directory\.(?:Exists|GetFiles|GetDirectories|CreateDirectory)|Path\.Combine)\s*\(\s*(?![\"'])([a-zA-Z_][a-zA-Z0-9_.]*)\s*[,)]"
)
_VAR_PATH_CSHARP_NEW = re.compile(
    r"new\s+(?:FileInfo|DirectoryInfo)\s*\(\s*(?![\"'])([a-zA-Z_][a-zA-Z0-9_.]*)\s*[,)]"
)

# MIME type pattern: "type/subtype" - not file paths.
_MIME_TYPE_PATTERN = re.compile(
    r"^(text|application|image|audio|video|font|multipart)/[a-zA-Z0-9.+*-]+$",
    re.IGNORECASE,
)


def looks_like_file_path(s: str) -> bool:
    """True if the string looks like a file path, not e.g. a MIME type or other non-path."""
    s = (s or "").strip().strip("'\"")
    if not s or len(s) < 2:
        return False
    if _MIME_TYPE_PATTERN.match(s):
        return False
    if "/" not in s and "\\" not in s:
        return False
    if s.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:[/\\]", s):
        return True
    if any(p in s for p in ("/home/", "/usr/", "/etc/", "/tmp/", "/var/", "/Users/")):
        return True
    if re.search(r"[A-Za-z]:\\", s):
        return True
    # Generic "segment/segment" (e.g. "section/key") - do NOT treat as path.
    if "://" in s:
        return False
    return False


def has_variable_path_argument(line: str, language: str = "python") -> bool:
    """True if the line contains a file I/O call whose path argument looks like a variable."""
    if language == "python":
        return _VAR_PATH_PYTHON.search(line) is not None
    if language == "javascript" or language == "typescript":
        return _VAR_PATH_JAVASCRIPT.search(line) is not None
    if language == "java":
        return _VAR_PATH_JAVA.search(line) is not None
    if language == "rust":
        return _VAR_PATH_RUST.search(line) is not None
    if language == "csharp":
        return _VAR_PATH_CSHARP.search(line) is not None or _VAR_PATH_CSHARP_NEW.search(line) is not None
    return False


def detect_language(file_path: Path) -> str:
    """Detect programming language from file extension."""
    ext = file_path.suffix.lower()
    lang_map = {
        '.py': 'python',
        '.cpp': 'cpp',
        '.cxx': 'cpp',
        '.cc': 'cpp',
        '.c': 'c',
        '.h': 'c',
        '.hpp': 'cpp',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.java': 'java',
        '.go': 'go',
        '.rs': 'rust',
        '.cs': 'csharp',
    }
    return lang_map.get(ext, 'unknown')


def position_inside_string_literal(line: str, pos: int) -> bool:
    """True if position pos in line is inside a quoted string literal (not code)."""
    if pos < 0 or pos >= len(line):
        return False
    in_string = False
    quote_char = None
    i = 0
    while i <= pos and i < len(line):
        ch = line[i]
        if ch in ('"', "'") and (i == 0 or line[i - 1] != "\\"):
            if not in_string:
                in_string = True
                quote_char = ch
            elif ch == quote_char:
                in_string = False
                quote_char = None
        i += 1
    return in_string


def is_comment(line: str) -> bool:
    """Check if line is a comment."""
    stripped = line.strip()
    comment_prefixes = ['#', '//', '/*', '*']
    return any(stripped.startswith(prefix) for prefix in comment_prefixes)


def is_comment_or_string(line: str, char: str) -> bool:
    """Check if character is inside a comment or string."""
    # Simple heuristic: if it's in quotes or after comment markers
    in_string = False
    quote_char = None
    i = 0
    while i < len(line):
        if line[i] in ['"', "'"] and (i == 0 or line[i-1] != '\\'):
            if not in_string:
                in_string = True
                quote_char = line[i]
            elif line[i] == quote_char:
                in_string = False
                quote_char = None
        elif line[i] == '#' and not in_string:
            return True  # Comment starts here
        i += 1
    return False
