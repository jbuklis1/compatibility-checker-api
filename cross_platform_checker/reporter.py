"""
Report generation for cross-platform compatibility checker.
"""

from deps import Dict, List, Path

from .issue import Issue, Severity


class ReportGenerator:
    """Generate reports from issues."""
    
    @staticmethod
    def generate_text_report(issues: List[Issue], file_path: Path) -> str:
        """Generate a text report."""
        if not issues:
            return f"\n✓ No cross-platform issues found in {file_path}\n"
        
        report = [f"\n{'='*80}"]
        report.append(f"Cross-Platform Compatibility Report: {file_path}")
        report.append(f"{'='*80}\n")
        
        # Group by severity
        errors = [i for i in issues if i.severity == Severity.ERROR]
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        infos = [i for i in issues if i.severity == Severity.INFO]
        
        if errors:
            report.append(f"ERRORS ({len(errors)}):")
            report.append("-" * 80)
            for issue in errors:
                report.append(f"  Line {issue.line_number}: {issue.message}")
                report.append(f"    Code: {issue.code}")
                report.append(f"    Fix: {issue.suggestion}")
                report.append(f"    Category: {issue.category}\n")
        
        if warnings:
            report.append(f"WARNINGS ({len(warnings)}):")
            report.append("-" * 80)
            for issue in warnings:
                report.append(f"  Line {issue.line_number}: {issue.message}")
                report.append(f"    Code: {issue.code}")
                report.append(f"    Fix: {issue.suggestion}")
                report.append(f"    Category: {issue.category}\n")
        
        if infos:
            report.append(f"INFO ({len(infos)}):")
            report.append("-" * 80)
            for issue in infos:
                report.append(f"  Line {issue.line_number}: {issue.message}")
                report.append(f"    Code: {issue.code}")
                report.append(f"    Fix: {issue.suggestion}")
                report.append(f"    Category: {issue.category}\n")
        
        report.append(f"\nSummary: {len(errors)} errors, {len(warnings)} warnings, {len(infos)} info")
        report.append("="*80)
        
        return "\n".join(report)
    
    @staticmethod
    def generate_summary(issues: List[Issue]) -> Dict[str, int]:
        """Generate a summary count by category."""
        summary = {}
        for issue in issues:
            summary[issue.category] = summary.get(issue.category, 0) + 1
        return summary
