"""File extraction service: handles folders and zip files."""

import tempfile
import zipfile
from pathlib import Path
from typing import List, Union

from starlette.datastructures import UploadFile


# Source file extensions to include
SOURCE_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx',
    '.cpp', '.cxx', '.cc', '.c', '.h', '.hpp',
    '.java', '.go', '.rs', '.rb', '.php',
    '.swift', '.kt', '.scala', '.clj',
}

# Directories to exclude
EXCLUDE_DIRS = {
    '.git', '.svn', '.hg', '__pycache__', 'node_modules',
    '.venv', 'venv', 'env', '.env', 'dist', 'build',
    '.pytest_cache', '.mypy_cache', '.tox', '.idea', '.vscode',
}


def extract_files(source: Union[str, Path, UploadFile]) -> List[Path]:
    """Extract source files from folder path, zip file path, or uploaded zip file.
    
    Args:
        source: Folder path (str/Path), zip file path (str/Path), or UploadFile
        
    Returns:
        List of absolute paths to source files found
    """
    if isinstance(source, UploadFile):
        return _extract_from_uploaded_zip(source)
    elif isinstance(source, (str, Path)):
        path = Path(source)
        if path.is_file() and path.suffix.lower() == '.zip':
            return _extract_from_zip_path(path)
        elif path.is_dir():
            return _extract_from_folder(path)
        else:
            raise ValueError(f"Source must be a folder or zip file: {path}")
    else:
        raise TypeError(f"Unsupported source type: {type(source)}")


def _extract_from_folder(folder_path: Path) -> List[Path]:
    """Extract source files from a folder recursively."""
    source_files: List[Path] = []
    folder_path = folder_path.resolve()

    for file_path in folder_path.rglob("*"):
        if not file_path.is_file():
            continue
        # Check if in excluded directory
        if any(excluded in file_path.parts for excluded in EXCLUDE_DIRS):
            continue
        # Check if has source file extension
        if file_path.suffix.lower() in SOURCE_EXTENSIONS:
            source_files.append(file_path.resolve())

    return sorted(source_files)


def _extract_from_zip_path(zip_path: Path) -> List[Path]:
    """Extract source files from a zip file path."""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        temp_dir = Path(tempfile.mkdtemp(prefix='compat_checker_'))
        zip_ref.extractall(temp_dir)
        return _extract_from_folder(temp_dir)


def _extract_from_uploaded_zip(upload_file: UploadFile) -> List[Path]:
    """Extract source files from an uploaded zip file."""
    temp_dir = Path(tempfile.mkdtemp(prefix='compat_checker_'))
    
    # Save uploaded file to temp location
    temp_zip = temp_dir / upload_file.filename
    with open(temp_zip, 'wb') as f:
        content = upload_file.file.read()
        f.write(content)
    
    # Extract zip
    with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
        extract_dir = temp_dir / 'extracted'
        extract_dir.mkdir()
        zip_ref.extractall(extract_dir)
    
    # Find source files
    source_files = _extract_from_folder(extract_dir)
    
    return source_files


def cleanup_temp_files(temp_dir: Path) -> None:
    """Remove temporary extraction directory.
    
    Args:
        temp_dir: Path to temporary directory to remove
    """
    import shutil
    try:
        shutil.rmtree(temp_dir)
    except Exception:
        pass  # Ignore cleanup errors


def build_temp_tree_from_uploads(files: List[UploadFile]) -> Path:
    """Create a temporary directory tree from uploaded files.

    Each UploadFile is written under a temp root using its filename, which may
    include relative paths (e.g. from folder selection in the browser).

    The returned directory can then be scanned with extract_files().
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="compat_upload_"))

    for upload in files:
        # Derive a safe relative path
        rel = upload.filename or "uploaded"
        # Normalize leading separators
        rel_path = Path(rel.lstrip("/\\"))
        dest = temp_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)

        upload.file.seek(0)
        with dest.open("wb") as f:
            chunk = upload.file.read(1024 * 1024)
            while chunk:
                f.write(chunk)
                chunk = upload.file.read(1024 * 1024)

    return temp_dir
