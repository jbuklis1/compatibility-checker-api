"""
Issue data models for cross-platform compatibility checker.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class Severity(Enum):
    """Issue severity levels."""
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class Issue:
    """Represents a cross-platform compatibility issue."""
    severity: Severity
    line_number: int
    column: int
    message: str
    code: str
    suggestion: str
    category: str


@dataclass
class Candidate:
    """A potential issue that needs wider-scope context to promote or drop."""
    severity: Severity
    line_number: int
    column: int
    message: str
    code: str
    suggestion: str
    category: str
    context_type: str
    context_data: Dict[str, Any] = field(default_factory=dict)
