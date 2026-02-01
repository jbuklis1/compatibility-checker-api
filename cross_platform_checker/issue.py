"""
Issue data models for cross-platform compatibility checker.
"""

from dataclasses import dataclass
from enum import Enum


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
