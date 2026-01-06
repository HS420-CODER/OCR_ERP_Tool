"""
ERP Arabic OCR Microservice - Middleware Package
=================================================
Security and request processing middleware.
"""

from .security import (
    APISecurityMiddleware,
    APIClient,
    RateLimiter,
    get_security_middleware,
    init_security
)

from .file_security import (
    FileSecurityValidator,
    FileValidationResult,
    FileValidationError,
    ValidationErrorCode,
    get_file_validator,
    validate_upload,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE
)

__all__ = [
    # API Security
    "APISecurityMiddleware",
    "APIClient",
    "RateLimiter",
    "get_security_middleware",
    "init_security",
    # File Security
    "FileSecurityValidator",
    "FileValidationResult",
    "FileValidationError",
    "ValidationErrorCode",
    "get_file_validator",
    "validate_upload",
    "ALLOWED_EXTENSIONS",
    "MAX_FILE_SIZE",
]
