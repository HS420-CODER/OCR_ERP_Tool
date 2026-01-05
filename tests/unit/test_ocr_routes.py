"""
Unit tests for OCR routes helper functions.

Tests the utility functions in ocr_routes.py without requiring Flask context.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.routes.ocr_routes import allowed_file, get_file_extension, ALLOWED_EXTENSIONS


class TestAllowedFile:
    """Tests for allowed_file function."""

    def test_allowed_png(self):
        """Test PNG is allowed."""
        assert allowed_file("test.png") == True

    def test_allowed_jpg(self):
        """Test JPG is allowed."""
        assert allowed_file("test.jpg") == True

    def test_allowed_jpeg(self):
        """Test JPEG is allowed."""
        assert allowed_file("test.jpeg") == True

    def test_allowed_pdf(self):
        """Test PDF is allowed."""
        assert allowed_file("document.pdf") == True

    def test_allowed_gif(self):
        """Test GIF is allowed."""
        assert allowed_file("image.gif") == True

    def test_allowed_bmp(self):
        """Test BMP is allowed."""
        assert allowed_file("image.bmp") == True

    def test_allowed_tiff(self):
        """Test TIFF is allowed."""
        assert allowed_file("image.tiff") == True

    def test_allowed_tif(self):
        """Test TIF is allowed."""
        assert allowed_file("image.tif") == True

    def test_allowed_webp(self):
        """Test WebP is allowed."""
        assert allowed_file("image.webp") == True

    def test_not_allowed_txt(self):
        """Test TXT is not allowed."""
        assert allowed_file("test.txt") == False

    def test_not_allowed_exe(self):
        """Test EXE is not allowed."""
        assert allowed_file("test.exe") == False

    def test_not_allowed_doc(self):
        """Test DOC is not allowed."""
        assert allowed_file("test.doc") == False

    def test_not_allowed_no_extension(self):
        """Test file without extension is not allowed."""
        assert allowed_file("testfile") == False

    def test_case_insensitive_uppercase(self):
        """Test uppercase extension is allowed."""
        assert allowed_file("test.PNG") == True

    def test_case_insensitive_mixed(self):
        """Test mixed case extension is allowed."""
        assert allowed_file("test.JpG") == True

    def test_multiple_dots_allowed(self):
        """Test file with multiple dots."""
        assert allowed_file("test.backup.png") == True

    def test_multiple_dots_last_extension(self):
        """Test that last extension is checked."""
        assert allowed_file("test.png.txt") == False


class TestGetFileExtension:
    """Tests for get_file_extension function."""

    def test_simple_extension(self):
        """Test simple file extension."""
        assert get_file_extension("test.png") == "png"

    def test_uppercase_extension(self):
        """Test uppercase extension is lowercased."""
        assert get_file_extension("test.PNG") == "png"

    def test_no_extension(self):
        """Test file without extension."""
        assert get_file_extension("testfile") == ""

    def test_multiple_dots(self):
        """Test file with multiple dots returns last extension."""
        assert get_file_extension("test.backup.pdf") == "pdf"

    def test_empty_filename(self):
        """Test empty filename."""
        assert get_file_extension("") == ""

    def test_dot_only(self):
        """Test filename that is just a dot."""
        assert get_file_extension(".") == ""


class TestAllowedExtensions:
    """Tests for ALLOWED_EXTENSIONS constant."""

    def test_contains_image_formats(self):
        """Test that common image formats are in allowed extensions."""
        assert 'png' in ALLOWED_EXTENSIONS
        assert 'jpg' in ALLOWED_EXTENSIONS
        assert 'jpeg' in ALLOWED_EXTENSIONS
        assert 'gif' in ALLOWED_EXTENSIONS
        assert 'bmp' in ALLOWED_EXTENSIONS

    def test_contains_pdf(self):
        """Test that PDF is in allowed extensions."""
        assert 'pdf' in ALLOWED_EXTENSIONS

    def test_contains_tiff_formats(self):
        """Test that TIFF formats are in allowed extensions."""
        assert 'tiff' in ALLOWED_EXTENSIONS
        assert 'tif' in ALLOWED_EXTENSIONS

    def test_contains_webp(self):
        """Test that WebP is in allowed extensions."""
        assert 'webp' in ALLOWED_EXTENSIONS

    def test_no_dangerous_formats(self):
        """Test that dangerous formats are not allowed."""
        assert 'exe' not in ALLOWED_EXTENSIONS
        assert 'bat' not in ALLOWED_EXTENSIONS
        assert 'sh' not in ALLOWED_EXTENSIONS
        assert 'py' not in ALLOWED_EXTENSIONS
        assert 'js' not in ALLOWED_EXTENSIONS
