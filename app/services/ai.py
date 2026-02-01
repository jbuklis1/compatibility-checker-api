"""AI service: Together.ai for fix suggestions and test generation."""

from pathlib import Path
from typing import Dict, List, Optional, Any

from ..config import get_together_api_key, get_together_model
from ..schemas import IssueOut


def _client() -> Optional[Any]:
    """Return OpenAI-compatible client for Together.ai, or None if unavailable."""
    try:
        from openai import OpenAI
    except ImportError:
        return None
    key = get_together_api_key()
    if not key:
        return None
    return OpenAI(api_key=key, base_url="https://api.together.xyz/v1")


def _issues_summary(issues: List[IssueOut]) -> str:
    if not issues:
        return "No rule-based issues found."
    parts = []
    for i in issues:
        parts.append(
            f"- Line {i.line_number} [{i.severity}] {i.category}: {i.message}\n"
            f"  Code: {i.code}\n  Suggestion: {i.suggestion}"
        )
    return "\n".join(parts)


class AIService:
    """Together.ai-backed fix suggestions and test generation."""

    def suggest_fixes(
        self,
        issues: List[IssueOut],
        code: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Optional[str]:
        """Return AI-generated fix suggestions for the given issues. None if AI unavailable."""
        client = _client()
        if not client:
            return None
        model = get_together_model()
        summary = _issues_summary(issues)
        prompt = (
            "You are a cross-platform compatibility expert. Below are compatibility issues "
            "reported by a static checker for code that must run on Windows, macOS, and Linux.\n\n"
            "Issues:\n"
            f"{summary}\n\n"
        )
        if code and language:
            prompt += f"Source code ({language}):\n```\n{code[:8000]}\n```\n\n"
        prompt += (
            "Provide actionable fix suggestions: either per-issue or overall. Be concise. "
            "Focus on platform-agnostic APIs (pathlib, os.path.join, platform.system, etc.). "
            "Use clear bullet points or numbered steps."
        )
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
            )
            if r.choices and r.choices[0].message.content:
                return r.choices[0].message.content.strip()
        except Exception:
            pass
        return None

    def generate_tests(
        self,
        code: str,
        language: str,
        issues: List[IssueOut],
    ) -> Optional[str]:
        """Return AI-generated test code for cross-platform checks. None if AI unavailable."""
        client = _client()
        if not client:
            return None
        model = get_together_model()
        summary = _issues_summary(issues)
        prompt = (
            "You are a cross-platform compatibility expert. Generate test cases that a developer "
            "can add to their project to verify cross-platform behavior (Windows, macOS, Linux).\n\n"
            f"Language: {language}\n\n"
            "Reported compatibility issues (fix these or assert around them):\n"
            f"{summary}\n\n"
            "Source code:\n"
            f"```\n{code[:8000]}\n```\n\n"
            "Provide concrete, runnable test code (e.g. pytest for Python, or platform-specific "
            "assertions). Include a brief comment explaining what each test checks. Output only "
            "the test code, optionally wrapped in a markdown code block."
        )
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
            )
            if r.choices and r.choices[0].message.content:
                text = r.choices[0].message.content.strip()
                # Strip markdown code block if present
                if text.startswith("```"):
                    lines = text.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    text = "\n".join(lines)
                return text
        except Exception:
            pass
        return None
    
    def analyze_group_relationships(
        self,
        files: List[Path],
        issues_by_file: Dict[Path, List[IssueOut]],
        dependency_graph: Dict,
    ) -> Optional[str]:
        """Analyze cross-file relationships and provide group-level compatibility insights.
        
        Args:
            files: List of file paths analyzed
            issues_by_file: Dictionary mapping file path to issues found
            dependency_graph: Dependency graph from relationship detector
            
        Returns:
            LLM-generated insights about cross-file compatibility patterns, or None if AI unavailable
        """
        client = _client()
        if not client:
            return None
        
        model = get_together_model()
        
        # Build summary of issues by file
        file_summaries = []
        total_issues = 0
        for file_path in files:
            issues = issues_by_file.get(file_path, [])
            total_issues += len(issues)
            if issues:
                file_name = file_path.name
                error_count = sum(1 for i in issues if i.severity == "ERROR")
                warning_count = sum(1 for i in issues if i.severity == "WARNING")
                file_summaries.append(
                    f"{file_name}: {len(issues)} issues ({error_count} errors, {warning_count} warnings)"
                )
        
        # Format dependency graph summary
        graph_summary = self._format_graph_for_prompt(dependency_graph)
        
        prompt = (
            "You are a cross-platform compatibility expert analyzing a multi-file codebase "
            "that must run on Windows, macOS, and Linux.\n\n"
            f"Total files analyzed: {len(files)}\n"
            f"Total issues found: {total_issues}\n\n"
            "Issues by file:\n"
        )
        for summary in file_summaries:
            prompt += f"  - {summary}\n"
        
        prompt += f"\n{graph_summary}\n\n"
        prompt += (
            "Analyze cross-file compatibility patterns and provide insights:\n"
            "1. Shared dependencies that may cause cross-platform issues\n"
            "2. Import path compatibility concerns (Windows vs Unix path separators)\n"
            "3. Cross-file patterns that could break on different platforms\n"
            "4. Recommendations for improving cross-platform compatibility across the codebase\n\n"
            "Be concise and actionable. Focus on issues that span multiple files."
        )
        
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
            )
            if r.choices and r.choices[0].message.content:
                return r.choices[0].message.content.strip()
        except Exception:
            pass
        return None
    
    def suggest_group_fixes(
        self,
        issues_by_file: Dict[Path, List[IssueOut]],
        dependency_graph: Dict,
        code_by_file: Dict[Path, str],
    ) -> Optional[str]:
        """Generate group-level fix suggestions considering cross-file impacts.
        
        Args:
            issues_by_file: Dictionary mapping file path to issues found
            dependency_graph: Dependency graph from relationship detector
            code_by_file: Dictionary mapping file path to source code
            
        Returns:
            LLM-generated group-level fix suggestions, or None if AI unavailable
        """
        client = _client()
        if not client:
            return None
        
        model = get_together_model()
        
        # Build comprehensive issue summary
        all_issues: List[IssueOut] = []
        for issues in issues_by_file.values():
            all_issues.extend(issues)
        
        issues_summary = _issues_summary(all_issues)
        
        # Format code samples (limit to first few files to avoid token limits)
        code_samples = []
        for file_path, code in list(code_by_file.items())[:5]:
            file_name = file_path.name
            code_samples.append(f"\n{file_name}:\n```\n{code[:2000]}\n```")
        
        graph_summary = self._format_graph_for_prompt(dependency_graph)
        
        prompt = (
            "You are a cross-platform compatibility expert. Below are compatibility issues "
            "found across multiple files in a codebase that must run on Windows, macOS, and Linux.\n\n"
            "Issues:\n"
            f"{issues_summary}\n\n"
            "Dependency relationships:\n"
            f"{graph_summary}\n\n"
        )
        
        if code_samples:
            prompt += "Sample source code:\n" + "\n".join(code_samples) + "\n\n"
        
        prompt += (
            "Provide group-level fix suggestions that consider:\n"
            "1. How fixes in one file might affect dependent files\n"
            "2. Cross-file patterns that need coordinated changes\n"
            "3. Import path fixes that need to be consistent across files\n"
            "4. Platform-agnostic APIs that should be used consistently\n\n"
            "Be specific about which files need changes and in what order. "
            "Use clear bullet points or numbered steps."
        )
        
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
            )
            if r.choices and r.choices[0].message.content:
                return r.choices[0].message.content.strip()
        except Exception:
            pass
        return None
    
    def _format_graph_for_prompt(self, dependency_graph: Dict) -> str:
        """Format dependency graph for LLM prompt."""
        if not dependency_graph:
            return "No dependency relationships detected."
        
        lines = []
        for file_path, data in list(dependency_graph.items())[:20]:  # Limit to avoid token limits
            file_name = Path(file_path).name
            imports = data.get("imports", [])
            imported_by = data.get("imported_by", [])
            
            if imports or imported_by:
                lines.append(f"\n{file_name}:")
                if imports:
                    import_names = [Path(imp).name for imp in imports[:5]]
                    lines.append(f"  Imports: {', '.join(import_names)}")
                if imported_by:
                    importer_names = [Path(imp).name for imp in imported_by[:5]]
                    lines.append(f"  Imported by: {', '.join(importer_names)}")
        
        return "\n".join(lines) if lines else "No significant dependencies detected."
