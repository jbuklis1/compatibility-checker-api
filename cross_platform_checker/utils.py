"""
Utility functions for cross-platform compatibility checker.
"""

from deps import Optional, Path


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
    }
    return lang_map.get(ext, 'unknown')


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
