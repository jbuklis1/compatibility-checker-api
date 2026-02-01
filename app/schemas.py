"""Pydantic request/response models."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# --- Request ---


class AnalyzeCodeRequest(BaseModel):
    """Request body for raw code analysis."""

    code: str = Field(..., description="Source code to analyze")
    language: str = Field(..., description="Language: python, cpp, c, javascript, etc.")
    filename: str = Field(default="input", description="Virtual filename for reporting")


class AnalyzeFilePathRequest(BaseModel):
    """Request body for file-path-based analysis."""

    file_path: str = Field(..., description="Absolute path to source file on server")


class AnalyzeRequest(BaseModel):
    """Unified request: either code+language or file_path."""

    code: Optional[str] = None
    language: Optional[str] = None
    filename: Optional[str] = Field(default="input", alias="filename")
    file_path: Optional[str] = Field(default=None, alias="file_path")

    model_config = {"populate_by_name": True}


# --- Issue (response) ---


class IssueOut(BaseModel):
    """Single compatibility issue."""

    severity: str = Field(..., description="ERROR, WARNING, or INFO")
    line_number: int
    column: int
    message: str
    code: str
    suggestion: str
    category: str
    file_path: Optional[str] = Field(default=None, description="File path this issue belongs to (for multi-file analysis)")


# --- Responses ---


class CheckResponse(BaseModel):
    """Response for POST /check (rules-only)."""

    issues: List[IssueOut] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    """Response for POST /analyze (rules + AI)."""

    issues: List[IssueOut] = Field(default_factory=list)
    ai_fix_suggestions: Optional[str] = Field(default=None, description="AI-generated fix suggestions")
    generated_tests: Optional[str] = Field(default=None, description="AI-generated test code")


class ErrorDetail(BaseModel):
    """Error response detail."""

    detail: str = Field(..., description="Error message")


# --- Multi-file Analysis ---


class MultiFileAnalyzeRequest(BaseModel):
    """Request for multi-file analysis."""

    folder_path: Optional[str] = Field(default=None, description="Absolute path to folder containing source files")
    zip_path: Optional[str] = Field(default=None, description="Absolute path to zip file containing source files")
    file_paths: Optional[List[str]] = Field(default=None, description="Explicit list of absolute file paths to analyze")


class FileIssues(BaseModel):
    """Issues found in a single file."""

    file_path: str = Field(..., description="Absolute path to the file")
    issues: List[IssueOut] = Field(default_factory=list, description="Issues found in this file")
    language: Optional[str] = Field(default=None, description="Detected programming language")


class MultiFileAnalyzeResponse(BaseModel):
    """Response for multi-file analysis."""

    files: List[FileIssues] = Field(default_factory=list, description="Issues grouped by file")
    cross_file_insights: Optional[str] = Field(default=None, description="LLM-generated cross-file compatibility insights")
    dependency_graph: Dict[str, Any] = Field(default_factory=dict, description="Import/dependency relationships between files")
    ai_fix_suggestions: Optional[str] = Field(default=None, description="Group-level AI fix suggestions")
    generated_tests: Optional[str] = Field(default=None, description="Group-level generated test code")
