"""
Unit tests for file utilities.
"""

import pytest
import os
from pathlib import Path
from src.utils.file_utils import (
    get_file_type,
    validate_file_path,
    get_file_size_mb,
    check_file_size,
    is_supported_format,
    get_extension,
    ensure_absolute_path,
    TEXT_EXTENSIONS,
    IMAGE_EXTENSIONS,
    PDF_EXTENSIONS,
    NOTEBOOK_EXTENSIONS
)


class TestGetFileType:
    """Tests for get_file_type function."""

    def test_text_extensions(self):
        """Test text file type detection."""
        assert get_file_type("file.txt") == "text"
        assert get_file_type("file.py") == "text"
        assert get_file_type("file.js") == "text"
        assert get_file_type("file.md") == "text"
        assert get_file_type("file.json") == "text"

    def test_image_extensions(self):
        """Test image file type detection."""
        assert get_file_type("file.png") == "image"
        assert get_file_type("file.jpg") == "image"
        assert get_file_type("file.jpeg") == "image"
        assert get_file_type("file.webp") == "image"
        assert get_file_type("file.gif") == "image"

    def test_pdf_extension(self):
        """Test PDF file type detection."""
        assert get_file_type("file.pdf") == "pdf"
        assert get_file_type("FILE.PDF") == "pdf"  # Case insensitive

    def test_notebook_extension(self):
        """Test notebook file type detection."""
        assert get_file_type("file.ipynb") == "notebook"

    def test_no_extension_is_text(self):
        """Test files without extension are treated as text."""
        assert get_file_type("Makefile") == "text"
        assert get_file_type("Dockerfile") == "text"

    def test_unknown_extension(self):
        """Test unknown extensions."""
        assert get_file_type("file.xyz") == "unknown"


class TestValidateFilePath:
    """Tests for validate_file_path function."""

    def test_valid_absolute_path(self, sample_text_file):
        """Test validation of valid absolute path."""
        is_valid, error = validate_file_path(sample_text_file)
        assert is_valid == True
        assert error == ""

    def test_relative_path_invalid(self):
        """Test that relative paths are invalid."""
        is_valid, error = validate_file_path("relative/path.txt")
        assert is_valid == False
        assert "absolute" in error.lower()

    def test_nonexistent_path_invalid(self, fixtures_dir):
        """Test that nonexistent paths are invalid."""
        # Use an absolute path that doesn't exist
        nonexistent = str(fixtures_dir / "nonexistent_file_xyz.txt")
        is_valid, error = validate_file_path(nonexistent)
        assert is_valid == False
        assert "not found" in error.lower()

    def test_directory_invalid(self, fixtures_dir):
        """Test that directories are invalid."""
        is_valid, error = validate_file_path(str(fixtures_dir))
        assert is_valid == False
        assert "directory" in error.lower()


class TestCheckFileSize:
    """Tests for file size checking."""

    def test_small_file_passes(self, sample_text_file):
        """Test that small files pass size check."""
        is_valid, error = check_file_size(sample_text_file, max_size_mb=50)
        assert is_valid == True
        assert error == ""

    def test_large_file_fails(self, sample_text_file):
        """Test that file exceeding limit fails."""
        # Use tiny limit that any file exceeds
        is_valid, error = check_file_size(sample_text_file, max_size_mb=0)
        assert is_valid == False
        assert "too large" in error.lower()


class TestIsSupportedFormat:
    """Tests for is_supported_format function."""

    def test_supported_formats(self):
        """Test supported file formats."""
        assert is_supported_format("file.txt") == True
        assert is_supported_format("file.py") == True
        assert is_supported_format("file.png") == True
        assert is_supported_format("file.pdf") == True
        assert is_supported_format("file.ipynb") == True

    def test_unsupported_formats(self):
        """Test unsupported file formats."""
        assert is_supported_format("file.exe") == False
        assert is_supported_format("file.dll") == False

    def test_no_extension_supported(self):
        """Test files without extension are supported."""
        assert is_supported_format("Makefile") == True


class TestGetExtension:
    """Tests for get_extension function."""

    def test_get_extension(self):
        """Test extension extraction."""
        assert get_extension("file.txt") == ".txt"
        assert get_extension("file.PNG") == ".png"  # Lowercase
        assert get_extension("path/to/file.pdf") == ".pdf"

    def test_no_extension(self):
        """Test files without extension."""
        assert get_extension("Makefile") == ""


class TestEnsureAbsolutePath:
    """Tests for ensure_absolute_path function."""

    def test_absolute_path_unchanged(self):
        """Test that absolute paths are unchanged."""
        if os.name == 'nt':
            path = "C:\\absolute\\path.txt"
        else:
            path = "/absolute/path.txt"

        result = ensure_absolute_path(path)
        assert Path(result).is_absolute()

    def test_relative_path_converted(self):
        """Test that relative paths are converted."""
        result = ensure_absolute_path("relative/path.txt")
        assert Path(result).is_absolute()


class TestExtensionSets:
    """Tests for extension set definitions."""

    def test_text_extensions_complete(self):
        """Test that common text extensions are included."""
        assert ".txt" in TEXT_EXTENSIONS
        assert ".py" in TEXT_EXTENSIONS
        assert ".js" in TEXT_EXTENSIONS
        assert ".md" in TEXT_EXTENSIONS

    def test_image_extensions_complete(self):
        """Test that common image extensions are included."""
        assert ".png" in IMAGE_EXTENSIONS
        assert ".jpg" in IMAGE_EXTENSIONS
        assert ".jpeg" in IMAGE_EXTENSIONS
        assert ".webp" in IMAGE_EXTENSIONS

    def test_pdf_extensions(self):
        """Test PDF extensions."""
        assert ".pdf" in PDF_EXTENSIONS

    def test_notebook_extensions(self):
        """Test notebook extensions."""
        assert ".ipynb" in NOTEBOOK_EXTENSIONS
