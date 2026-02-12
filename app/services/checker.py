"""Checker service: wraps cross_platform_checker and maps to API models."""

from ..config import ensure_checker_import_path
from deps import Dict, List, Path, Tuple, tempfile
from ..schemas import IssueOut

ensure_checker_import_path()

from cross_platform_checker.main_checker import CrossPlatformChecker
from cross_platform_checker.issue import Issue
from .file_extractor import extract_files, cleanup_temp_files

_LANG_TO_EXT = {
    "python": ".py",
    "cpp": ".cpp",
    "c": ".c",
    "javascript": ".js",
    "jsx": ".js",
    "typescript": ".ts",
    "java": ".java",
    "kotlin": ".kt",
    "go": ".go",
    "rust": ".rs",
    "csharp": ".cs",
    "lua": ".lua",
    "swift": ".swift",
    "unknown": ".txt",
}


def _issue_to_out(i: Issue, file_path: str = None) -> IssueOut:
    return IssueOut(
        severity=i.severity.value,
        line_number=i.line_number,
        column=i.column,
        message=i.message,
        code=i.code,
        suggestion=i.suggestion,
        category=i.category,
        file_path=file_path,
    )


class CheckerService:
    """Wraps CrossPlatformChecker for use by the API."""

    def analyze_code(self, code: str, language: str, filename: str = "input") -> List[IssueOut]:
        """Run rule-based checks on raw code. Uses a temp file."""
        ext = _LANG_TO_EXT.get(language.lower(), ".txt")
        base = filename if filename != "input" else "source"
        if base.endswith(ext):
            base = base[: -len(ext)]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=ext, prefix=base + "_", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            path = Path(f.name)
        try:
            issues = CrossPlatformChecker().check_file(path)
            return [_issue_to_out(i) for i in issues]
        finally:
            path.unlink(missing_ok=True)

    def analyze_file(self, file_path: Path) -> List[IssueOut]:
        """Run rule-based checks on a file path."""
        issues = CrossPlatformChecker().check_file(file_path)
        return [_issue_to_out(i) for i in issues]
    
    def analyze_files(self, file_paths: List[Path]) -> Dict[Path, List[IssueOut]]:
        """Run rule-based checks on multiple files.
        
        Args:
            file_paths: List of file paths to analyze
            
        Returns:
            Dictionary mapping file path to list of issues
        """
        checker = CrossPlatformChecker()
        issues_by_file = checker.check_files(file_paths)
        
        # Convert to IssueOut format
        result: Dict[Path, List[IssueOut]] = {}
        for file_path, issues in issues_by_file.items():
            result[file_path] = [_issue_to_out(i, str(file_path)) for i in issues]
        
        return result
    
    def analyze_folder(self, folder_path: Path) -> Dict[Path, List[IssueOut]]:
        """Run rule-based checks on all source files in a folder.
        
        Args:
            folder_path: Path to folder containing source files
            
        Returns:
            Dictionary mapping file path to list of issues
        """
        source_files = extract_files(folder_path)
        if not source_files:
            return {}
        return self.analyze_files(source_files)
    
    def analyze_zip(self, zip_path: Path) -> Tuple[Dict[Path, List[IssueOut]], Path]:
        """Run rule-based checks on all source files in a zip file.
        
        Args:
            zip_path: Path to zip file containing source files
            
        Returns:
            Tuple of (issues dictionary, temp directory path for cleanup)
        """
        source_files = extract_files(zip_path)
        
        # Find the temp directory (parent of first extracted file)
        temp_dir = None
        if source_files:
            # All extracted files should be under the same temp directory
            temp_dir = source_files[0].parent
            # Walk up to find the actual temp extraction root
            while temp_dir and not temp_dir.name.startswith('compat_checker_'):
                temp_dir = temp_dir.parent
            if temp_dir is None:
                temp_dir = source_files[0].parent
        
        if not source_files:
            return {}, temp_dir or Path(tempfile.gettempdir())
        
        issues = self.analyze_files(source_files)
        return issues, temp_dir or Path(tempfile.gettempdir())
