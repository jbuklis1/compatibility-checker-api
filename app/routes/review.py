"""Review route (form-based file analysis)."""

import re
from deps import (
    APIRouter,
    Dict,
    File,
    Form,
    HTMLResponse,
    HTTPException,
    List,
    Optional,
    Path,
    Query,
    Response,
    Tuple,
    UploadFile,
    time,
    uuid,
)
from fastapi.responses import RedirectResponse
from ..report_formatter import format_multi_file_report, format_text_report
from ..schemas import (
    AnalyzeRequest,
    FileIssues,
    IssueOut,
    MultiFileAnalyzeRequest,
    MultiFileAnalyzeResponse,
)
from ..config import ensure_checker_import_path
from ..services import AIService, CheckerService
from ..services.file_extractor import (
    build_temp_tree_from_uploads,
    cleanup_temp_files,
    extract_files,
)
from ..services.relationship_detector import build_dependency_graph, format_relationship_summary

ensure_checker_import_path()
from cross_platform_checker.utils import detect_language
from ..templates import render_review_form, render_review_results
from ..utils import run_check

router = APIRouter()
ai_svc = AIService()
checker_svc = CheckerService()

# Cache analysis results: key = file_path, value = (issues, code, lang, ai_suggestions, generated_tests, timestamp)
_results_cache: Dict[str, Tuple[list, Optional[str], Optional[str], Optional[str], Optional[str], float]] = {}
# Cache multi-file report for upload flow: key = report_id, value = (report_text, timestamp, source_label)
_multi_report_cache: Dict[str, Tuple[str, float, str]] = {}
CACHE_TTL = 300.0  # 5 minutes


def _safe_report_basename(label: str, for_upload: bool = False) -> str:
    """Build a readable, filesystem-safe base name for the report (no extension)."""
    if not (label or "").strip():
        return "compatibility_report"
    # Use last path component (file or folder name)
    p = Path(label.replace("\\", "/").strip())
    name = p.name or p.stem or "report"
    # Prefer stem so "my_project.zip" -> "my_project", "main.py" -> "main"
    stem = Path(name).stem or name
    # Sanitize: allow letters, digits, underscore, hyphen; cap length
    safe = re.sub(r"[^\w\-]", "_", stem)[:80].strip("_") or "report"
    return safe if safe else "compatibility_report"


def _upload_source_label(
    temp_dir: Optional[Path],
    source_files: List[Path],
    files: List[UploadFile],
) -> str:
    """Human-readable label for upload (folder/zip): prefer root folder name over first filename."""
    if not temp_dir or not source_files:
        return (files[0].filename or "uploaded selection") if files else "uploaded selection"
    try:
        rel_paths = [p.relative_to(temp_dir) for p in source_files]
    except ValueError:
        return (files[0].filename or "uploaded selection") if files else "uploaded selection"
    if not rel_paths:
        return "uploaded selection"
    first_parts = [p.parts[0] for p in rel_paths if len(p.parts) >= 1]
    if first_parts and all(p == first_parts[0] for p in first_parts):
        return first_parts[0]
    # Flat or mixed: use first file's parent dir name if any, else fallback
    first_rel = rel_paths[0]
    if first_rel.parts and len(first_rel.parts) > 1:
        return first_rel.parts[0]
    return files[0].filename or "uploaded selection"


@router.get("/review", response_class=HTMLResponse)
def review_get() -> str:
    """Redirect to homepage with review tab open."""
    return RedirectResponse(url="/#review", status_code=302)


def _analyze_file(file_path: str, use_cache: bool = True):
    """Helper to run analysis on a file. Returns (issues, code, lang, ai_suggestions, generated_tests)."""
    # Check cache first
    if use_cache and file_path in _results_cache:
        cached = _results_cache[file_path]
        issues, code, lang, ai_suggestions, generated_tests, cache_time = cached
        age = time.time() - cache_time
        if age < CACHE_TTL:
            return issues, code, lang, ai_suggestions, generated_tests

    p = Path(file_path)
    if not p.is_absolute():
        raise HTTPException(400, "file_path must be absolute")
    if not p.exists():
        raise HTTPException(404, f"File not found: {file_path}")
    req = AnalyzeRequest(file_path=file_path)
    issues, code, lang = run_check(req)
    ai_suggestions = ai_svc.suggest_fixes(issues, code=code, language=lang)
    generated_tests = ai_svc.generate_tests(code or "", lang or "unknown", issues) if (code and lang) else None

    # Cache the results
    _results_cache[file_path] = (issues, code, lang, ai_suggestions, generated_tests, time.time())
    return issues, code, lang, ai_suggestions, generated_tests


@router.post("/review", response_class=HTMLResponse)
def review_post(
    file_path: str = Form(default=""),
    folder_path: str = Form(default=""),
    zip_path: str = Form(default=""),
) -> str:
    """Run analysis on file/folder/zip path and render results."""
    file_path = (file_path or "").strip()
    folder_path = (folder_path or "").strip()
    zip_path = (zip_path or "").strip()
    
    # Determine input type
    if folder_path:
        return _handle_multi_file_analysis_html(folder_path, "folder")
    elif zip_path:
        return _handle_multi_file_analysis_html(zip_path, "zip")
    elif file_path:
        try:
            issues, code, lang, ai_suggestions, generated_tests = _analyze_file(file_path)
            return render_review_results(file_path, issues, ai_suggestions, generated_tests)
        except HTTPException as e:
            return render_review_form(error=e.detail, value=file_path)
    else:
        return render_review_form(error="File path, folder path, or zip path is required.", value="")


def _handle_multi_file_analysis_html(source_path: str, source_type: str) -> str:
    """Handle multi-file analysis and render HTML results."""
    from ..templates import render_review_multi_results
    
    try:
        p = Path(source_path)
        if not p.is_absolute():
            return render_review_form(error=f"{source_type.capitalize()} path must be absolute.", value=source_path)
        if not p.exists():
            return render_review_form(error=f"{source_type.capitalize()} not found: {source_path}", value=source_path)
        
        # Extract files
        if source_type == "folder":
            source_files = extract_files(p)
        else:  # zip
            source_files = extract_files(p)
        
        if not source_files:
            return render_review_form(error=f"No source files found in {source_type}: {source_path}", value=source_path)
        
        # Analyze files
        issues_by_file = checker_svc.analyze_files(source_files)
        
        # Build dependency graph
        dependency_graph = build_dependency_graph(source_files)
        
        # Read code for AI analysis
        code_by_file: Dict[Path, str] = {}
        for file_path in source_files:
            try:
                code_by_file[file_path] = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass
        
        # Get AI insights
        cross_file_insights = ai_svc.analyze_group_relationships(source_files, issues_by_file, dependency_graph)
        group_fixes = ai_svc.suggest_group_fixes(issues_by_file, dependency_graph, code_by_file)
        
        # Format response
        file_issues_list = []
        for file_path in source_files:
            issues = issues_by_file.get(file_path, [])
            language = detect_language(file_path)
            file_issues_list.append(FileIssues(
                file_path=str(file_path),
                issues=issues,
                language=language,
            ))
        
        return render_review_multi_results(
            source_path=source_path,
            source_type=source_type,
            files=file_issues_list,
            cross_file_insights=cross_file_insights,
            dependency_graph=dependency_graph,
            ai_fix_suggestions=group_fixes,
            source_root=Path(source_path) if source_type == "folder" else None,
        )
    except Exception as e:
        return render_review_form(error=f"Error analyzing {source_type}: {str(e)}", value=source_path)


@router.get("/review/download")
def review_download(file_path: Optional[str] = Query(None)) -> Response:
    """Download analysis results as a text file. Uses cached results if available. Redirects to / when file_path is missing."""
    if not file_path or not file_path.strip():
        return RedirectResponse(url="/", status_code=302)
    file_path = file_path.strip()
    try:
        # Use cache to avoid re-running AI calls
        issues, code, lang, ai_suggestions, generated_tests = _analyze_file(file_path, use_cache=True)
        report_text = format_text_report(file_path, issues, ai_suggestions, generated_tests)
        base = _safe_report_basename(Path(file_path).name)
        filename = f"{base}_compatibility_report.md"
        return Response(
            content=report_text,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error generating report: {str(e)}")


@router.get("/review/multi")
def review_multi_get():
    """Redirect GET /review/multi to homepage with review tab open."""
    return RedirectResponse(url="/#review", status_code=302)


@router.post("/review/multi", response_model=MultiFileAnalyzeResponse)
def review_multi(req: MultiFileAnalyzeRequest) -> MultiFileAnalyzeResponse:
    """Multi-file analysis endpoint (API)."""
    source_files: List[Path] = []
    temp_dir: Optional[Path] = None
    
    try:
        # Determine source type and extract files
        if req.folder_path:
            p = Path(req.folder_path)
            if not p.is_absolute():
                raise HTTPException(400, "folder_path must be absolute")
            if not p.exists() or not p.is_dir():
                raise HTTPException(404, f"Folder not found: {req.folder_path}")
            source_files = extract_files(p)
        elif req.zip_path:
            p = Path(req.zip_path)
            if not p.is_absolute():
                raise HTTPException(400, "zip_path must be absolute")
            if not p.exists() or not p.is_file():
                raise HTTPException(404, f"Zip file not found: {req.zip_path}")
            source_files = extract_files(p)
            # Find temp directory for cleanup
            if source_files:
                temp_dir = source_files[0].parent
                while temp_dir and not temp_dir.name.startswith('compat_checker_'):
                    temp_dir = temp_dir.parent
        elif req.file_paths:
            source_files = [Path(fp) for fp in req.file_paths]
            for fp in source_files:
                if not fp.is_absolute():
                    raise HTTPException(400, f"File path must be absolute: {fp}")
                if not fp.exists():
                    raise HTTPException(404, f"File not found: {fp}")
        else:
            raise HTTPException(400, "Provide folder_path, zip_path, or file_paths")
        
        if not source_files:
            raise HTTPException(400, "No source files found")
        
        # Analyze files
        issues_by_file = checker_svc.analyze_files(source_files)
        
        # Build dependency graph
        dependency_graph = build_dependency_graph(source_files)
        
        # Read code for AI analysis
        code_by_file: Dict[Path, str] = {}
        for file_path in source_files:
            try:
                code_by_file[file_path] = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass
        
        # Get AI insights
        cross_file_insights = ai_svc.analyze_group_relationships(source_files, issues_by_file, dependency_graph)
        group_fixes = ai_svc.suggest_group_fixes(issues_by_file, dependency_graph, code_by_file)
        
        # Format response
        file_issues_list = []
        for file_path in source_files:
            issues = issues_by_file.get(file_path, [])
            language = detect_language(file_path)
            file_issues_list.append(FileIssues(
                file_path=str(file_path),
                issues=issues,
                language=language,
            ))
        
        return MultiFileAnalyzeResponse(
            files=file_issues_list,
            cross_file_insights=cross_file_insights,
            dependency_graph=dependency_graph,
            ai_fix_suggestions=group_fixes,
            generated_tests=None,  # Could add group test generation later
        )
    finally:
        # Cleanup temp files if needed
        if temp_dir and temp_dir.exists() and temp_dir.name.startswith('compat_checker_'):
            cleanup_temp_files(temp_dir)


@router.get("/review/results")
def review_results_get():
    """Redirect GET /review/results to the review form."""
    return RedirectResponse(url="/review", status_code=302)


@router.post("/review/results", response_class=HTMLResponse)
def review_results_post(
    files: List[UploadFile] = File(...),
    mode: str = Form(default="ai"),
) -> str:
    """Handle generic upload (single file, archive, or folder/multi-file). mode=ai (default) or rules."""
    from ..templates import render_review_multi_results

    # Filter out phantom/empty file parts (some browsers send extra parts with empty filename)
    files = [f for f in files if (f.filename or "").strip()]

    if not files:
        return render_review_form(error="Please select at least one file to upload.", value="")

    # Classify selection
    is_single = len(files) == 1
    first_name = (files[0].filename or "").lower()

    source_files: List[Path] = []
    temp_dir: Optional[Path] = None

    try:
        if is_single and first_name.endswith(".zip"):
            # Single archive: let extract_files handle the uploaded zip directly
            source_files = extract_files(files[0])
        else:
            # One or more regular files / folder selection: build a temp tree then scan it
            temp_dir = build_temp_tree_from_uploads(files)
            source_files = extract_files(temp_dir)

        if not source_files:
            return render_review_form(error="No source files found in uploaded selection.", value="")

        # If exactly one reviewable file, treat as single-file analysis
        if len(source_files) == 1:
            single_path = source_files[0]
            try:
                issues = checker_svc.analyze_file(single_path)
                ai_suggestions = None
                generated_tests = None
                if mode == "ai":
                    try:
                        code = single_path.read_text(encoding="utf-8", errors="replace")
                        lang = detect_language(single_path)
                    except Exception:
                        code = None
                        lang = None
                    ai_suggestions = ai_svc.suggest_fixes(issues, code=code, language=lang)
                    generated_tests = (
                        ai_svc.generate_tests(code or "", lang or "unknown", issues)
                        if (code and lang)
                        else None
                    )
                return render_review_results(str(single_path), issues, ai_suggestions, generated_tests)
            finally:
                if temp_dir and temp_dir.exists() and temp_dir.name.startswith("compat_upload_"):
                    cleanup_temp_files(temp_dir)

        # Multi-file analysis flow
        issues_by_file = checker_svc.analyze_files(source_files)

        # Build dependency graph
        dependency_graph = build_dependency_graph(source_files)

        cross_file_insights = None
        group_fixes = None
        if mode == "ai":
            code_by_file: Dict[Path, str] = {}
            for file_path in source_files:
                try:
                    code_by_file[file_path] = file_path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    pass
            cross_file_insights = ai_svc.analyze_group_relationships(
                source_files, issues_by_file, dependency_graph
            )
            group_fixes = ai_svc.suggest_group_fixes(issues_by_file, dependency_graph, code_by_file)

        # Format response
        file_issues_list = []
        for file_path in source_files:
            issues = issues_by_file.get(file_path, [])
            language = detect_language(file_path)
            file_issues_list.append(
                FileIssues(
                    file_path=str(file_path),
                    issues=issues,
                    language=language,
                )
            )

        # Use root folder name for report/download when all files share one parent under temp_dir
        source_label = _upload_source_label(temp_dir, source_files, files)

        # Generate report text and cache it so download works without a filesystem path
        report_text = format_multi_file_report(
            source_path=source_label,
            source_type="upload",
            files=file_issues_list,
            cross_file_insights=cross_file_insights,
            dependency_graph=dependency_graph,
            ai_fix_suggestions=group_fixes,
        )
        report_id = str(uuid.uuid4())
        now = time.time()
        _multi_report_cache[report_id] = (report_text, now, source_label)
        # Evict expired entries
        for rid in list(_multi_report_cache):
            if now - _multi_report_cache[rid][1] > CACHE_TTL:
                del _multi_report_cache[rid]

        return render_review_multi_results(
            source_path=source_label,
            source_type="upload",
            files=file_issues_list,
            cross_file_insights=cross_file_insights,
            dependency_graph=dependency_graph,
            ai_fix_suggestions=group_fixes,
            report_id=report_id,
            source_root=temp_dir,
        )
    except Exception as e:
        return render_review_form(error=f"Error analyzing uploaded selection: {str(e)}", value="")
    finally:
        # Cleanup temp files
        if temp_dir and temp_dir.exists() and temp_dir.name.startswith("compat_upload_"):
            cleanup_temp_files(temp_dir)


@router.get("/review/multi/download")
def review_multi_download(
    source_path: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    report_id: Optional[str] = Query(None),
) -> Response:
    """Download multi-file analysis results as a text file. For uploads use report_id; for path-based use source_path. Redirects to /#review when opened without params."""
    from ..schemas import FileIssues

    if not source_type or not source_type.strip():
        return RedirectResponse(url="/#review", status_code=302)
    source_type = source_type.strip()

    # Upload flow: serve from cache by report_id (no filesystem path)
    if source_type == "upload" and report_id:
        report_id = report_id.strip()
        if not report_id:
            raise HTTPException(400, "report_id is required for upload download")
        cached = _multi_report_cache.get(report_id)
        if not cached:
            raise HTTPException(404, "Report expired or not found. Re-run the analysis and download again.")
        report_text, _, source_label = cached
        base = _safe_report_basename(source_label)
        filename = f"{base}_compatibility_report.md"
        return Response(
            content=report_text,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # Path-based flow: require absolute source_path
    if not source_path or not source_path.strip():
        raise HTTPException(400, "source_path is required when not using upload report_id")
    source_path = source_path.strip()

    try:
        p = Path(source_path)
        if not p.is_absolute():
            raise HTTPException(400, "source_path must be absolute")
        if not p.exists():
            raise HTTPException(404, f"Source not found: {source_path}")

        # Extract files
        source_files = extract_files(p)
        if not source_files:
            raise HTTPException(400, "No source files found")

        # Analyze files
        issues_by_file = checker_svc.analyze_files(source_files)

        # Build dependency graph
        dependency_graph = build_dependency_graph(source_files)

        # Read code for AI analysis
        code_by_file: Dict[Path, str] = {}
        for file_path in source_files:
            try:
                code_by_file[file_path] = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass

        # Get AI insights
        cross_file_insights = ai_svc.analyze_group_relationships(source_files, issues_by_file, dependency_graph)
        group_fixes = ai_svc.suggest_group_fixes(issues_by_file, dependency_graph, code_by_file)

        # Format response
        file_issues_list = []
        for file_path in source_files:
            issues = issues_by_file.get(file_path, [])
            language = detect_language(file_path)
            file_issues_list.append(FileIssues(
                file_path=str(file_path),
                issues=issues,
                language=language,
            ))

        # Generate report
        report_text = format_multi_file_report(
            source_path=source_path,
            source_type=source_type,
            files=file_issues_list,
            cross_file_insights=cross_file_insights,
            dependency_graph=dependency_graph,
            ai_fix_suggestions=group_fixes,
        )

        base = _safe_report_basename(Path(source_path).name)
        filename = f"{base}_compatibility_report.md"
        return Response(
            content=report_text,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error generating report: {str(e)}")
