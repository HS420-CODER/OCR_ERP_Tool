"""
ERP Arabic OCR Microservice - File Security Validator
======================================================
Validates uploaded files for security and format compliance.
"""

import os
import re
import uuid
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, BinaryIO
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FileValidationError(Exception):
    """Exception raised for file validation failures."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class ValidationErrorCode(Enum):
    """File validation error codes."""
    MISSING_FILE = "MISSING_FILE"
    EMPTY_FILE = "EMPTY_FILE"
    INVALID_EXTENSION = "INVALID_EXTENSION"
    INVALID_MIME_TYPE = "INVALID_MIME_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    FILE_TOO_SMALL = "FILE_TOO_SMALL"
    MALICIOUS_CONTENT = "MALICIOUS_CONTENT"
    FILENAME_UNSAFE = "FILENAME_UNSAFE"


@dataclass
class FileValidationResult:
    """Result of file validation."""
    valid: bool
    filename: str
    sanitized_filename: str
    mime_type: str
    file_size: int
    file_hash: str
    errors: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict:
        return {
            "valid": self.valid,
            "filename": self.filename,
            "sanitized_filename": self.sanitized_filename,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "file_hash": self.file_hash,
            "errors": self.errors,
            "warnings": self.warnings
        }


# Magic bytes for file type detection
MAGIC_BYTES = {
    # Images
    b'\x89PNG\r\n\x1a\n': 'image/png',
    b'\xff\xd8\xff': 'image/jpeg',
    b'GIF87a': 'image/gif',
    b'GIF89a': 'image/gif',
    b'BM': 'image/bmp',
    b'II*\x00': 'image/tiff',  # Little-endian TIFF
    b'MM\x00*': 'image/tiff',  # Big-endian TIFF

    # PDF
    b'%PDF': 'application/pdf',
}

# File extension to MIME type mapping
EXTENSION_MIME_MAP = {
    '.png': ['image/png'],
    '.jpg': ['image/jpeg'],
    '.jpeg': ['image/jpeg'],
    '.gif': ['image/gif'],
    '.bmp': ['image/bmp', 'image/x-ms-bmp'],
    '.tiff': ['image/tiff'],
    '.tif': ['image/tiff'],
    '.pdf': ['application/pdf'],
}

# Allowed extensions for OCR processing
ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.pdf', '.tiff', '.tif', '.bmp'}

# Maximum file sizes (in bytes)
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
MIN_FILE_SIZE = 100  # 100 bytes (minimum for valid image)

# Maximum filename length
MAX_FILENAME_LENGTH = 255

# Dangerous filename patterns
DANGEROUS_PATTERNS = [
    r'\.\.',          # Path traversal
    r'[<>:"/\\|?*]',  # Invalid filename characters
    r'\x00',          # Null byte
    r'^\.ht',         # Apache config files
    r'\.exe$',        # Executables
    r'\.sh$',         # Shell scripts
    r'\.bat$',        # Batch files
    r'\.cmd$',        # Command files
    r'\.php',         # PHP files
    r'\.asp',         # ASP files
    r'\.jsp',         # JSP files
]


class FileSecurityValidator:
    """
    Comprehensive file security validator.

    Features:
    - File extension validation
    - MIME type detection via magic bytes
    - File size limits
    - Filename sanitization
    - Malicious content detection
    - Path traversal prevention
    """

    def __init__(
        self,
        allowed_extensions: Optional[set] = None,
        max_file_size: int = MAX_FILE_SIZE,
        min_file_size: int = MIN_FILE_SIZE,
        use_magic_lib: bool = True
    ):
        """
        Initialize file security validator.

        Args:
            allowed_extensions: Set of allowed file extensions
            max_file_size: Maximum file size in bytes
            min_file_size: Minimum file size in bytes
            use_magic_lib: Try to use python-magic for MIME detection
        """
        self.allowed_extensions = allowed_extensions or ALLOWED_EXTENSIONS
        self.max_file_size = max_file_size
        self.min_file_size = min_file_size
        self._magic = None

        if use_magic_lib:
            self._init_magic()

    def _init_magic(self) -> None:
        """Initialize python-magic library if available."""
        try:
            import magic
            self._magic = magic.Magic(mime=True)
            logger.info("python-magic initialized for MIME detection")
        except ImportError:
            logger.warning("python-magic not available, using fallback MIME detection")
        except Exception as e:
            logger.warning(f"Failed to initialize python-magic: {e}")

    def validate(
        self,
        file_data: BinaryIO,
        filename: str,
        check_content: bool = True
    ) -> FileValidationResult:
        """
        Validate an uploaded file.

        Args:
            file_data: File-like object with file content
            filename: Original filename
            check_content: Whether to check file content

        Returns:
            FileValidationResult with validation details

        Raises:
            FileValidationError: If validation fails critically
        """
        errors = []
        warnings = []

        # Get file size
        file_data.seek(0, 2)
        file_size = file_data.tell()
        file_data.seek(0)

        # Check file size
        size_error = self._check_size(file_size)
        if size_error:
            errors.append(size_error)

        # Check extension
        ext_error, extension = self._check_extension(filename)
        if ext_error:
            errors.append(ext_error)

        # Check MIME type
        if check_content:
            mime_type, mime_error = self._check_mime_type(file_data, extension)
            if mime_error:
                errors.append(mime_error)
            file_data.seek(0)
        else:
            mime_type = EXTENSION_MIME_MAP.get(extension, ['application/octet-stream'])[0]

        # Check for malicious content
        if check_content:
            malicious_error = self._check_malicious_content(file_data)
            if malicious_error:
                errors.append(malicious_error)
            file_data.seek(0)

        # Sanitize filename
        sanitized_filename = self.sanitize_filename(filename)

        # Calculate file hash
        file_hash = self._calculate_hash(file_data)
        file_data.seek(0)

        # Check filename safety
        filename_warning = self._check_filename_safety(filename)
        if filename_warning:
            warnings.append(filename_warning)

        return FileValidationResult(
            valid=len(errors) == 0,
            filename=filename,
            sanitized_filename=sanitized_filename,
            mime_type=mime_type,
            file_size=file_size,
            file_hash=file_hash,
            errors=errors,
            warnings=warnings
        )

    def _check_extension(self, filename: str) -> Tuple[Optional[str], str]:
        """
        Check if file extension is allowed.

        Args:
            filename: Original filename

        Returns:
            Tuple of (error_message, extension)
        """
        if not filename:
            return "Filename is required", ""

        extension = Path(filename).suffix.lower()

        if not extension:
            return f"File must have an extension. Allowed: {', '.join(self.allowed_extensions)}", ""

        if extension not in self.allowed_extensions:
            return f"Extension '{extension}' not allowed. Allowed: {', '.join(self.allowed_extensions)}", extension

        return None, extension

    def _check_mime_type(
        self,
        file_data: BinaryIO,
        extension: str
    ) -> Tuple[str, Optional[str]]:
        """
        Check MIME type using magic bytes.

        Args:
            file_data: File content
            extension: File extension

        Returns:
            Tuple of (detected_mime_type, error_message)
        """
        # Read first bytes for magic detection
        header = file_data.read(32)
        file_data.seek(0)

        detected_mime = None

        # Try python-magic first
        if self._magic:
            try:
                file_data.seek(0)
                content = file_data.read()
                file_data.seek(0)
                detected_mime = self._magic.from_buffer(content)
            except Exception as e:
                logger.warning(f"python-magic detection failed: {e}")

        # Fallback to magic bytes detection
        if not detected_mime:
            for magic_bytes, mime in MAGIC_BYTES.items():
                if header.startswith(magic_bytes):
                    detected_mime = mime
                    break

        if not detected_mime:
            detected_mime = 'application/octet-stream'

        # Validate against expected MIME types for extension
        expected_mimes = EXTENSION_MIME_MAP.get(extension, [])

        if expected_mimes and detected_mime not in expected_mimes:
            # Special case: some JPEG files are detected as image/jpeg
            if extension in ['.jpg', '.jpeg'] and 'image/jpeg' in detected_mime.lower():
                return detected_mime, None

            return detected_mime, f"File content ({detected_mime}) doesn't match extension ({extension})"

        return detected_mime, None

    def _check_size(self, file_size: int) -> Optional[str]:
        """
        Check if file size is within limits.

        Args:
            file_size: File size in bytes

        Returns:
            Error message if invalid, None otherwise
        """
        if file_size < self.min_file_size:
            return f"File too small ({file_size} bytes). Minimum: {self.min_file_size} bytes"

        if file_size > self.max_file_size:
            max_mb = self.max_file_size / (1024 * 1024)
            file_mb = file_size / (1024 * 1024)
            return f"File too large ({file_mb:.1f} MB). Maximum: {max_mb:.1f} MB"

        return None

    def _check_malicious_content(self, file_data: BinaryIO) -> Optional[str]:
        """
        Check for potentially malicious content.

        Checks for:
        - Script tags
        - PHP code
        - Executable signatures

        Args:
            file_data: File content

        Returns:
            Error message if malicious, None otherwise
        """
        # Read first 8KB for content analysis
        content = file_data.read(8192)
        file_data.seek(0)

        # Check for script content in images (polyglot attack)
        suspicious_patterns = [
            b'<script',
            b'<?php',
            b'<%',
            b'#!/',
            b'MZ',  # Windows executable
        ]

        for pattern in suspicious_patterns:
            if pattern in content.lower() if isinstance(pattern, bytes) else pattern.encode() in content:
                logger.warning(f"Suspicious pattern detected in file: {pattern}")
                return "File contains potentially malicious content"

        return None

    def _check_filename_safety(self, filename: str) -> Optional[str]:
        """
        Check filename for safety issues.

        Args:
            filename: Original filename

        Returns:
            Warning message if issues found, None otherwise
        """
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                return f"Filename contains unsafe pattern"

        if len(filename) > MAX_FILENAME_LENGTH:
            return f"Filename too long (max {MAX_FILENAME_LENGTH} characters)"

        return None

    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe storage.

        Args:
            filename: Original filename

        Returns:
            Safe filename
        """
        if not filename:
            return f"{uuid.uuid4().hex[:8]}.unknown"

        # Get extension
        path = Path(filename)
        extension = path.suffix.lower()

        # Clean the stem (filename without extension)
        stem = path.stem

        # Remove dangerous characters
        safe_chars = re.sub(r'[^a-zA-Z0-9_\-\u0600-\u06FF]', '_', stem)

        # Remove multiple underscores
        safe_chars = re.sub(r'_+', '_', safe_chars)

        # Remove leading/trailing underscores
        safe_chars = safe_chars.strip('_')

        # Ensure we have a valid stem
        if not safe_chars:
            safe_chars = uuid.uuid4().hex[:8]

        # Truncate if too long
        max_stem_length = MAX_FILENAME_LENGTH - len(extension) - 10  # Leave room for uniquifier
        if len(safe_chars) > max_stem_length:
            safe_chars = safe_chars[:max_stem_length]

        # Add unique suffix to prevent collisions
        unique_suffix = uuid.uuid4().hex[:6]

        return f"{safe_chars}_{unique_suffix}{extension}"

    def _calculate_hash(self, file_data: BinaryIO) -> str:
        """
        Calculate SHA-256 hash of file content.

        Args:
            file_data: File content

        Returns:
            Hex-encoded hash string
        """
        hasher = hashlib.sha256()

        file_data.seek(0)
        while chunk := file_data.read(8192):
            hasher.update(chunk)
        file_data.seek(0)

        return hasher.hexdigest()

    def get_file_info(self, file_data: BinaryIO, filename: str) -> Dict:
        """
        Get file information without full validation.

        Args:
            file_data: File content
            filename: Filename

        Returns:
            File information dict
        """
        file_data.seek(0, 2)
        file_size = file_data.tell()
        file_data.seek(0)

        extension = Path(filename).suffix.lower()
        mime_type, _ = self._check_mime_type(file_data, extension)
        file_hash = self._calculate_hash(file_data)

        return {
            "filename": filename,
            "extension": extension,
            "mime_type": mime_type,
            "file_size": file_size,
            "file_hash": file_hash
        }


# Singleton instance
_file_validator: Optional[FileSecurityValidator] = None


def get_file_validator() -> FileSecurityValidator:
    """Get the global file validator instance."""
    global _file_validator
    if _file_validator is None:
        _file_validator = FileSecurityValidator()
    return _file_validator


def validate_upload(file_data: BinaryIO, filename: str) -> FileValidationResult:
    """
    Convenience function to validate an uploaded file.

    Args:
        file_data: File content
        filename: Original filename

    Returns:
        FileValidationResult
    """
    return get_file_validator().validate(file_data, filename)


# Export
__all__ = [
    "FileSecurityValidator",
    "FileValidationResult",
    "FileValidationError",
    "ValidationErrorCode",
    "get_file_validator",
    "validate_upload",
    "ALLOWED_EXTENSIONS",
    "MAX_FILE_SIZE"
]
