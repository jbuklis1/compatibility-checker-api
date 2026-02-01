# Cross-Platform Checker Module Structure

This document describes the modular structure of the cross-platform compatibility checker.

## Directory Structure

```
cross_platform_checker/
├── __init__.py              # Package initialization
├── issue.py                 # Data models (Severity, Issue)
├── utils.py                 # Utility functions
├── checker_base.py          # Base checker class
├── main_checker.py          # Main checker coordinator
├── reporter.py              # Report generation
└── checkers/
    ├── __init__.py          # Checkers package exports
    ├── path_checker.py      # Path-related checks
    ├── api_checker.py       # Platform API checks
    ├── file_checker.py      # File operation checks
    ├── env_checker.py       # Environment variable checks
    ├── system_checker.py    # System call checks
    ├── python_checker.py    # Python-specific checks
    ├── cpp_checker.py       # C++-specific checks
    └── javascript_checker.py # JavaScript-specific checks
```

## Module Descriptions

### Core Modules

#### `issue.py`
- **Severity**: Enum for issue severity levels (ERROR, WARNING, INFO)
- **Issue**: Dataclass representing a compatibility issue

#### `utils.py`
- **detect_language()**: Detects programming language from file extension
- **is_comment()**: Checks if a line is a comment
- **is_comment_or_string()**: Checks if a character is in a comment or string

#### `checker_base.py`
- **BaseChecker**: Abstract base class for all checkers
  - Provides common functionality
  - Manages issues list
  - Handles file path and language

#### `main_checker.py`
- **CrossPlatformChecker**: Main coordinator class
  - Instantiates all checkers
  - Runs checks in sequence
  - Collects all issues

#### `reporter.py`
- **ReportGenerator**: Generates text reports from issues
  - Formats issues by severity
  - Creates summaries
  - Outputs structured reports

### Checker Modules

#### `path_checker.py` - PathChecker
Checks for:
- Hardcoded path separators (`\` vs `/`)
- Hardcoded absolute paths (`C:\`, `/home/`, `/Users/`)
- Case sensitivity in imports/modules

#### `api_checker.py` - APIChecker
Checks for:
- Platform-specific APIs (Win32, Unix, macOS)
- Platform-specific library imports
- Threading API issues
- Network code issues
- GUI framework issues

#### `file_checker.py` - FileChecker
Checks for:
- Missing encoding in file operations
- Platform-specific file locking
- Encoding compatibility issues

#### `env_checker.py` - EnvChecker
Checks for:
- Windows-specific environment variable syntax (`%VAR%`)
- Platform-specific environment variable names

#### `system_checker.py` - SystemChecker
Checks for:
- System call usage (`system()`, `popen()`, etc.)
- Platform-specific command execution

#### `python_checker.py` - PythonChecker
Python-specific checks:
- `os.name` usage (suggests `platform.system()`)
- Missing `pathlib` usage for path handling

#### `cpp_checker.py` - CppChecker
C++-specific checks:
- `std::filesystem` usage (C++17 requirement)
- Windows-specific types (`DWORD`, `HANDLE`, etc.)

#### `javascript_checker.py` - JavaScriptChecker
JavaScript/Node.js-specific checks:
- Hardcoded Windows drive paths
- Missing `path` module usage

## Adding New Checkers

To add a new checker:

1. Create a new file in `checkers/` directory
2. Inherit from `BaseChecker`
3. Implement `_run_checks()` method
4. Use `_add_issue()` to report issues
5. Import and register in `checkers/__init__.py`
6. Add to `main_checker.py` if it's a general checker, or to `language_checkers` if language-specific

Example:

```python
from ..checker_base import BaseChecker
from ..issue import Severity

class MyChecker(BaseChecker):
    """My custom checker."""
    
    def _run_checks(self):
        """Run my custom checks."""
        for i, line in enumerate(self.lines, 1):
            if 'bad_pattern' in line:
                self._add_issue(
                    Severity.WARNING, i, 0,
                    "Bad pattern detected",
                    line.strip(),
                    "Use better pattern instead",
                    "MY_CATEGORY"
                )
```

## Benefits of Modular Structure

1. **Readability**: Each checker is in its own file with a single responsibility
2. **Maintainability**: Easy to find and modify specific checks
3. **Extensibility**: Simple to add new checkers without modifying existing code
4. **Testability**: Each checker can be tested independently
5. **Organization**: Related checks are grouped together logically

## Usage

The main entry point (`cross_platform_checker.py`) imports and uses the modular structure:

```python
from cross_platform_checker.main_checker import CrossPlatformChecker
from cross_platform_checker.reporter import ReportGenerator
```

The API remains the same - all complexity is hidden behind the module structure.
