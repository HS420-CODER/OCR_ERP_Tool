"""
File utility functions.

Provides:
- File type detection
- Path validation
- File size checking
- Extension mapping
"""

import os
from pathlib import Path
from typing import Optional, Tuple
import mimetypes


# File extension categories
TEXT_EXTENSIONS = {
    '.txt', '.md', '.py', '.js', '.ts', '.jsx', '.tsx',
    '.json', '.yaml', '.yml', '.xml', '.html', '.htm',
    '.css', '.scss', '.less', '.sql', '.sh', '.bat',
    '.ps1', '.ini', '.cfg', '.conf', '.config', '.log',
    '.csv', '.env', '.gitignore', '.dockerignore',
    '.c', '.cpp', '.h', '.hpp', '.java', '.go', '.rs',
    '.rb', '.php', '.pl', '.r', '.swift', '.kt', '.scala'
}

IMAGE_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.webp',
    '.bmp', '.tiff', '.tif', '.ico'
}

PDF_EXTENSIONS = {'.pdf'}

NOTEBOOK_EXTENSIONS = {'.ipynb'}

# All supported extensions
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | IMAGE_EXTENSIONS | PDF_EXTENSIONS | NOTEBOOK_EXTENSIONS


def get_file_type(file_path: str) -> str:
    """
    Determine the type of a file.

    Args:
        file_path: Path to the file

    Returns:
        One of: "text", "image", "pdf", "notebook", "unknown"
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in TEXT_EXTENSIONS or suffix == '':
        return "text"
    elif suffix in IMAGE_EXTENSIONS:
        return "image"
    elif suffix in PDF_EXTENSIONS:
        return "pdf"
    elif suffix in NOTEBOOK_EXTENSIONS:
        return "notebook"
    else:
        # Try to detect by content type
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            if mime_type.startswith('text/'):
                return "text"
            elif mime_type.startswith('image/'):
                return "image"
            elif mime_type == 'application/pdf':
                return "pdf"

        return "unknown"


def validate_file_path(file_path: str) -> Tuple[bool, str]:
    """
    Validate a file path for reading.

    Checks:
    - Path is absolute
    - Path exists
    - Path is a file (not directory)
    - File is readable

    Args:
        file_path: Path to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    path = Path(file_path)

    # Check if absolute
    if not path.is_absolute():
        return False, f"File path must be absolute: {file_path}"

    # Check if exists
    if not path.exists():
        return False, f"File not found: {file_path}"

    # Check if directory
    if path.is_dir():
        return False, f"Cannot read directory: {file_path}. Use a file path instead."

    # Check if readable
    if not os.access(path, os.R_OK):
        return False, f"File is not readable: {file_path}"

    return True, ""


def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes.

    Args:
        file_path: Path to the file

    Returns:
        File size in MB
    """
    return os.path.getsize(file_path) / (1024 * 1024)


def check_file_size(file_path: str, max_size_mb: int = 50) -> Tuple[bool, str]:
    """
    Check if file size is within limits.

    Args:
        file_path: Path to the file
        max_size_mb: Maximum allowed size in MB

    Returns:
        Tuple of (is_valid, error_message)
    """
    size_mb = get_file_size_mb(file_path)
    if size_mb > max_size_mb:
        return False, f"File too large: {size_mb:.2f}MB (max {max_size_mb}MB)"
    return True, ""


def is_supported_format(file_path: str) -> bool:
    """
    Check if file format is supported.

    Args:
        file_path: Path to the file

    Returns:
        True if format is supported
    """
    suffix = Path(file_path).suffix.lower()
    return suffix in SUPPORTED_EXTENSIONS or suffix == ''


def get_extension(file_path: str) -> str:
    """
    Get file extension (lowercase, with dot).

    Args:
        file_path: Path to the file

    Returns:
        Extension like ".pdf" or "" if no extension
    """
    return Path(file_path).suffix.lower()


def ensure_absolute_path(file_path: str) -> str:
    """
    Convert relative path to absolute.

    Args:
        file_path: File path (relative or absolute)

    Returns:
        Absolute path
    """
    path = Path(file_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    return str(path.resolve())


def detect_encoding(file_path: str) -> str:
    """
    Detect file encoding.

    Args:
        file_path: Path to the file

    Returns:
        Encoding name (default: "utf-8")
    """
    # Try common encodings
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1256']  # cp1256 for Arabic

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read(1024)  # Read first 1KB
            return encoding
        except (UnicodeDecodeError, UnicodeError):
            continue

    return 'utf-8'  # Default fallback
