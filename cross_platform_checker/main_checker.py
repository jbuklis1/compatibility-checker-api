"""
Main checker class that coordinates all checkers.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from .context_pruner import ContextPruner
from .issue import Candidate, Issue, Severity
from .utils import detect_language
from .checkers import (
    PathChecker, APIChecker, FileChecker, EnvChecker,
    SystemChecker, PythonChecker, CppChecker, JavaScriptChecker, JavaChecker,
    GoChecker, RustChecker, CSharpChecker,
)


class CrossPlatformChecker:
    """Main checker class for cross-platform compatibility issues."""
    
    def __init__(self):
        self.issues: List[Issue] = []
        self.file_path: Optional[Path] = None
        self.language: Optional[str] = None
        
        # Initialize all checkers
        self.checkers = [
            PathChecker(),
            APIChecker(),
            FileChecker(),
            EnvChecker(),
            SystemChecker(),
        ]
        
        # Language-specific checkers (C and C++ share the same checker; JS and TS share the same; Java and Kotlin share the same)
        _cpp_checker = CppChecker()
        _js_checker = JavaScriptChecker()
        _java_checker = JavaChecker()
        self.language_checkers = {
            'python': PythonChecker(),
            'cpp': _cpp_checker,
            'c': _cpp_checker,
            'javascript': _js_checker,
            'typescript': _js_checker,
            'java': _java_checker,
            'kotlin': _java_checker,
            'go': GoChecker(),
            'rust': RustChecker(),
            'csharp': CSharpChecker(),
        }
        
    def check_file(self, file_path: Path) -> List[Issue]:
        """Check a file for cross-platform issues."""
        self.file_path = file_path
        self.issues = []
        
        if not file_path.exists():
            return []
        
        # Detect language
        self.language = detect_language(file_path)
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            return [Issue(
                Severity.ERROR, 0, 0,
                f"Could not read file: {e}",
                "", "", "FILE_IO"
            )]
        
        candidates: List[Candidate] = []

        # Run all general checkers (with candidate collection)
        for checker in self.checkers:
            issues = checker.check(file_path, lines, self.language, candidates)
            self.issues.extend(issues)

        # Run language-specific checkers
        if self.language in self.language_checkers:
            checker = self.language_checkers[self.language]
            issues = checker.check(file_path, lines, self.language, candidates)
            self.issues.extend(issues)

        # Phase 2: prune candidates with wider-scope context
        if candidates:
            pruner = ContextPruner(lines, self.language, candidates)
            self.issues.extend(pruner.prune())

        return self.issues
    
    def check_files(self, file_paths: List[Path]) -> Dict[Path, List[Issue]]:
        """Check multiple files for cross-platform issues.
        
        Args:
            file_paths: List of file paths to analyze
            
        Returns:
            Dictionary mapping file path to list of issues found in that file
        """
        results: Dict[Path, List[Issue]] = {}
        for file_path in file_paths:
            issues = self.check_file(file_path)
            results[file_path] = issues
        return results
    
    def detect_relationships(self, file_paths: List[Path]) -> Dict[str, Any]:
        """Detect import/dependency relationships between files.
        
        Args:
            file_paths: List of file paths to analyze
            
        Returns:
            Dictionary with:
            - imports: Dict mapping file path to list of imported modules/files
            - missing: List of imported modules that are not in file_paths
            - circular: List of circular dependency chains
            - graph: Dict mapping file path to {imports: [...], imported_by: [...]}
        """
        imports_by_file: Dict[Path, List[str]] = {}
        file_set = set(file_paths)
        
        # Extract imports from each file
        for file_path in file_paths:
            if not file_path.exists():
                continue
            
            language = detect_language(file_path)
            imports = self._extract_imports(file_path, language)
            imports_by_file[file_path] = imports
        
        # Build dependency graph
        graph: Dict[str, Dict[str, List[str]]] = {}
        missing_imports: List[str] = []
        
        for file_path, imports in imports_by_file.items():
            file_str = str(file_path)
            graph[file_str] = {"imports": [], "imported_by": []}
            
            for imp in imports:
                # Try to resolve import to actual file
                resolved = self._resolve_import(imp, file_path, file_set)
                if resolved:
                    resolved_str = str(resolved)
                    graph[file_str]["imports"].append(resolved_str)
                    if resolved_str not in graph:
                        graph[resolved_str] = {"imports": [], "imported_by": []}
                    graph[resolved_str]["imported_by"].append(file_str)
                else:
                    missing_imports.append(f"{file_str}: {imp}")
        
        # Detect circular dependencies using DFS
        circular = self._detect_circular_dependencies(graph)
        
        return {
            "imports": {str(k): v for k, v in imports_by_file.items()},
            "missing": missing_imports,
            "circular": circular,
            "graph": graph,
        }
    
    def _extract_imports(self, file_path: Path, language: str) -> List[str]:
        """Extract import statements from a file based on language."""
        imports: List[str] = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception:
            return imports
        
        if language == 'python':
            imports.extend(self._extract_python_imports(lines))
        elif language in ('javascript', 'typescript'):
            imports.extend(self._extract_javascript_imports(lines))
        elif language in ('cpp', 'c'):
            imports.extend(self._extract_cpp_includes(lines))
        elif language == 'java':
            imports.extend(self._extract_java_imports(lines))
        elif language == 'kotlin':
            imports.extend(self._extract_java_imports(lines))
        elif language == 'go':
            imports.extend(self._extract_go_imports(lines))
        elif language == 'rust':
            imports.extend(self._extract_rust_imports(lines))
        elif language == 'csharp':
            imports.extend(self._extract_csharp_imports(lines))
        
        return imports
    
    def _extract_python_imports(self, lines: List[str]) -> List[str]:
        """Extract Python import statements. Returns full module paths for resolution."""
        imports: List[str] = []
        import re

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#'):
                continue

            # import module / import module.sub
            match = re.match(r'^\s*import\s+(\S+)', stripped)
            if match:
                imports.append(match.group(1))
                continue

            # from module import ... / from .module import ...
            match = re.match(r'^\s*from\s+(\S+)\s+import', stripped)
            if match:
                imports.append(match.group(1))
                continue

            # __import__('module')
            match = re.search(r"__import__\s*\(\s*['\"](\S+)['\"]", stripped)
            if match:
                imports.append(match.group(1))

        return imports
    
    def _extract_javascript_imports(self, lines: List[str]) -> List[str]:
        """Extract JavaScript/TypeScript import statements."""
        imports: List[str] = []
        import re
        
        for line in lines:
            stripped = line.strip()
            # Skip comments
            if stripped.startswith('//') or stripped.startswith('/*'):
                continue
            
            # import ... from 'module'
            match = re.search(r"import\s+.*\s+from\s+['\"]([^'\"]+)['\"]", stripped)
            if match:
                imports.append(match.group(1))
                continue
            
            # require('module')
            match = re.search(r"require\s*\(\s*['\"]([^'\"]+)['\"]", stripped)
            if match:
                imports.append(match.group(1))
        
        return imports
    
    def _extract_cpp_includes(self, lines: List[str]) -> List[str]:
        """Extract C++ #include directives."""
        imports: List[str] = []
        import re
        
        for line in lines:
            stripped = line.strip()
            # #include <header>
            match = re.search(r'#include\s*<([^>]+)>', stripped)
            if match:
                imports.append(match.group(1))
                continue
            
            # #include "header"
            match = re.search(r'#include\s*"([^"]+)"', stripped)
            if match:
                imports.append(match.group(1))
        
        return imports

    def _extract_java_imports(self, lines: List[str]) -> List[str]:
        """Extract Java import statements. Returns type/package names for resolution."""
        imports: List[str] = []
        import re
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('//') or stripped.startswith('*') or stripped.startswith('/*'):
                continue
            # import pkg.Class; or import pkg.sub.Class;
            match = re.match(r'^\s*import\s+(?:static\s+)?(\S+?)\s*;', stripped)
            if match:
                imports.append(match.group(1))
        
        return imports
    
    def _extract_go_imports(self, lines: List[str]) -> List[str]:
        """Extract Go import statements. Returns package paths for dependency graph."""
        imports: List[str] = []
        import re
        in_import_block = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('//') or stripped.startswith('/*'):
                continue
            # import "path" or import _ "path" or import alias "path"
            match = re.match(r'^\s*import\s+(?:\s*[a-zA-Z0-9_]*\s+)?["\']([^"\']+)["\']\s*$', stripped)
            if match:
                imports.append(match.group(1))
                continue
            # import ( starting block
            if re.match(r'^\s*import\s*\(\s*$', stripped):
                in_import_block = True
                continue
            if in_import_block:
                if stripped.startswith(')'):
                    in_import_block = False
                    continue
                # "path" or _ "path" or alias "path"
                match = re.match(r'^\s*(?:[a-zA-Z0-9_]+\s+)?["\']([^"\']+)["\']\s*$', stripped)
                if match:
                    imports.append(match.group(1))
        return imports
    
    def _extract_rust_imports(self, lines: List[str]) -> List[str]:
        """Extract Rust use and mod statements. Returns crate/module names for dependency graph."""
        imports: List[str] = []
        import re
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
                continue
            # use crate::path::Item; or use external_crate::path;
            match = re.match(r'^\s*use\s+([a-zA-Z0-9_][a-zA-Z0-9_:]*)\s*;', stripped)
            if match:
                imports.append(match.group(1).split('::')[0])
                continue
            # mod name;
            match = re.match(r'^\s*mod\s+([a-zA-Z0-9_]+)\s*;', stripped)
            if match:
                imports.append(match.group(1))
        return imports
    
    def _extract_csharp_imports(self, lines: List[str]) -> List[str]:
        """Extract C# using statements. Returns namespace names."""
        imports: List[str] = []
        import re
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
                continue
            # using Namespace; or using Alias = Namespace;
            match = re.match(r'^\s*using\s+(?:[A-Za-z0-9_.]+\s*=\s*)?([A-Za-z0-9_.]+)\s*;', stripped)
            if match:
                imports.append(match.group(1))
        return imports
    
    def _resolve_import(self, imp: str, from_file: Path, file_set: set) -> Optional[Path]:
        """Try to resolve an import to an actual file path."""
        import os

        from_file = from_file.resolve()
        file_set = {p.resolve() for p in file_set}

        imp_clean = imp.strip()
        if not imp_clean:
            return None

        imp_base = imp_clean.replace('.py', '').replace('.js', '').replace('.ts', '').replace('.h', '').replace('.hpp', '').replace('.java', '').replace('.kt', '').replace('.rs', '').replace('.cs', '')

        # Relative import (Python: from .module or from ..module import ...)
        if imp_clean.startswith('.'):
            dots_and_name = imp_clean.split('.')
            n_dots = sum(1 for x in dots_and_name if x == '')  # leading dots
            parts = [p for p in dots_and_name if p]
            if not parts:
                return None
            rel_path = from_file.parent
            for _ in range(n_dots - 1):
                rel_path = rel_path.parent
            for part in parts:
                rel_path = rel_path / part
            for ext in ['.py', '.ts', '.js']:
                candidate = rel_path.with_suffix(ext)
                if candidate in file_set:
                    return candidate
            candidate = rel_path / '__init__.py'
            if candidate in file_set:
                return candidate
            return None

        # Dotted module path (e.g. app.utils): match by module path derived from file_set
        if '.' in imp_clean and not imp_clean.startswith(('node_modules', '/')):
            try:
                common = Path(os.path.commonpath([str(p) for p in file_set]))
                if common.is_file():
                    common = common.parent
            except (ValueError, TypeError):
                common = None
            if common:
                imp_module = imp_base.replace('.', '/')
                for fp in file_set:
                    try:
                        rel = fp.relative_to(common)
                    except ValueError:
                        continue
                    stem = str(rel).replace('\\', '/').replace('.py', '').replace('.ts', '').replace('.js', '').replace('.java', '').replace('.kt', '').replace('.go', '')
                    if stem.endswith('/__init__'):
                        stem = stem[:-9]
                    module_path = stem.replace('/', '.')
                    if module_path == imp_base or module_path.endswith('.' + imp_base):
                        return fp

        # Exact filename match
        for fp in file_set:
            if fp.name == imp_clean or fp.stem == imp_base:
                return fp

        # Same directory, with extensions
        if from_file.parent:
            for ext in ['.py', '.js', '.ts', '.h', '.hpp', '.cpp', '.c', '.java', '.kt', '.go', '.rs', '.cs']:
                candidate = (from_file.parent / (imp_base + ext)).resolve()
                if candidate in file_set:
                    return candidate

        return None
    
    def _detect_circular_dependencies(self, graph: Dict[str, Dict[str, List[str]]]) -> List[List[str]]:
        """Detect circular dependencies using DFS."""
        circular: List[List[str]] = []
        visited: set = set()
        rec_stack: set = set()
        
        def dfs(node: str, path: List[str]) -> None:
            if node in rec_stack:
                # Found cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                if cycle not in circular:
                    circular.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            
            if node in graph:
                for neighbor in graph[node].get("imports", []):
                    if neighbor in graph:
                        dfs(neighbor, path + [node])
            
            rec_stack.remove(node)
        
        for node in graph:
            if node not in visited:
                dfs(node, [])
        
        return circular
