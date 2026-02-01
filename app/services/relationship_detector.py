"""Relationship detector: analyzes imports and dependencies between files."""

from pathlib import Path
from typing import Dict, List, Set

from ..config import ensure_checker_import_path

ensure_checker_import_path()

from cross_platform_checker.main_checker import CrossPlatformChecker
from cross_platform_checker.utils import detect_language


def detect_imports(file_path: Path, language: str = None) -> List[str]:
    """Detect import statements in a file.
    
    Args:
        file_path: Path to the file
        language: Programming language (auto-detected if None)
        
    Returns:
        List of imported module/file names
    """
    if language is None:
        language = detect_language(file_path)
    
    checker = CrossPlatformChecker()
    return checker._extract_imports(file_path, language)


def build_dependency_graph(files: List[Path]) -> Dict[str, Dict]:
    """Build dependency graph from file imports.
    
    Args:
        files: List of file paths to analyze
        
    Returns:
        Dictionary mapping file path (str) to:
        {
            "imports": [list of file paths this file imports],
            "imported_by": [list of file paths that import this file],
            "language": str
        }
    """
    file_set = set(files)
    graph: Dict[str, Dict] = {}
    
    # Initialize graph entries
    for file_path in files:
        file_str = str(file_path.resolve())
        language = detect_language(file_path)
        graph[file_str] = {
            "imports": [],
            "imported_by": [],
            "language": language,
        }
    
    # Build import relationships
    checker = CrossPlatformChecker()
    for file_path in files:
        file_str = str(file_path.resolve())
        language = detect_language(file_path)
        imports = checker._extract_imports(file_path, language)
        
        for imp in imports:
            resolved = checker._resolve_import(imp, file_path, file_set)
            if resolved:
                resolved_str = str(resolved.resolve())
                if resolved_str in graph:
                    graph[file_str]["imports"].append(resolved_str)
                    graph[resolved_str]["imported_by"].append(file_str)
    
    return graph


def format_relationship_summary(graph: Dict[str, Dict]) -> str:
    """Format dependency graph as a human-readable summary for LLM prompts.
    
    Args:
        graph: Dependency graph from build_dependency_graph()
        
    Returns:
        Formatted string summary
    """
    lines = ["Dependency Graph:"]
    lines.append("=" * 80)
    
    for file_path, data in sorted(graph.items()):
        file_name = Path(file_path).name
        language = data.get("language", "unknown")
        imports = data.get("imports", [])
        imported_by = data.get("imported_by", [])
        
        lines.append(f"\n{file_name} ({language})")
        if imports:
            lines.append("  Imports:")
            for imp in imports:
                lines.append(f"    - {Path(imp).name}")
        if imported_by:
            lines.append("  Imported by:")
            for importer in imported_by:
                lines.append(f"    - {Path(importer).name}")
        if not imports and not imported_by:
            lines.append("  (no dependencies)")
    
    # Detect and report circular dependencies
    circular = _detect_circular_dependencies(graph)
    if circular:
        lines.append("\n" + "=" * 80)
        lines.append("Circular Dependencies Detected:")
        for cycle in circular:
            cycle_names = [Path(f).name for f in cycle]
            lines.append(f"  {' -> '.join(cycle_names)} -> {cycle_names[0]}")
    
    return "\n".join(lines)


def _detect_circular_dependencies(graph: Dict[str, Dict]) -> List[List[str]]:
    """Detect circular dependencies using DFS."""
    circular: List[List[str]] = []
    visited: Set[str] = set()
    rec_stack: Set[str] = set()
    
    def dfs(node: str, path: List[str]) -> None:
        if node in rec_stack:
            # Found cycle
            cycle_start = path.index(node)
            cycle = path[cycle_start:] + [node]
            # Normalize cycle (start from lexicographically first node)
            cycle_start_idx = min(range(len(cycle) - 1), key=lambda i: cycle[i])
            normalized_cycle = cycle[cycle_start_idx:-1] + [cycle[cycle_start_idx]]
            if normalized_cycle not in circular:
                circular.append(normalized_cycle)
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
