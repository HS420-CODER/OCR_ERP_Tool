"""
Unit tests for data models.
"""

import pytest
from src.models import ReadOptions, ReadResult, PageResult, TextBlock


class TestReadOptions:
    """Tests for ReadOptions dataclass."""

    def test_default_values(self):
        """Test default option values."""
        options = ReadOptions(file_path="/test/file.txt")

        assert options.file_path == "/test/file.txt"
        assert options.offset == 0
        assert options.limit == 2000
        assert options.max_line_length == 2000
        assert options.lang == "en"
        assert options.engine == "auto"
        assert options.include_confidence == True
        assert options.output_format == "text"

    def test_custom_values(self):
        """Test custom option values."""
        options = ReadOptions(
            file_path="/test/file.png",
            offset=100,
            limit=500,
            lang="ar",
            engine="paddle"
        )

        assert options.offset == 100
        assert options.limit == 500
        assert options.lang == "ar"
        assert options.engine == "paddle"

    def test_invalid_language_raises_error(self):
        """Test that invalid language raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported language"):
            ReadOptions(file_path="/test/file.txt", lang="xyz")

    def test_invalid_engine_raises_error(self):
        """Test that invalid engine raises ValueError."""
        with pytest.raises(ValueError, match="Invalid engine"):
            ReadOptions(file_path="/test/file.txt", engine="invalid")

    def test_invalid_output_format_raises_error(self):
        """Test that invalid output format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid output format"):
            ReadOptions(file_path="/test/file.txt", output_format="xml")


class TestTextBlock:
    """Tests for TextBlock dataclass."""

    def test_creation(self):
        """Test TextBlock creation."""
        block = TextBlock(
            text="Hello World",
            confidence=0.95,
            bbox=[[0, 0], [100, 0], [100, 50], [0, 50]],
            page=1
        )

        assert block.text == "Hello World"
        assert block.confidence == 0.95
        assert block.bbox is not None
        assert block.page == 1

    def test_to_dict(self):
        """Test TextBlock to_dict method."""
        block = TextBlock(text="Test", confidence=0.9876, page=2)
        d = block.to_dict()

        assert d["text"] == "Test"
        assert d["confidence"] == 0.9876
        assert d["page"] == 2
        assert "bbox" not in d  # None values should be excluded


class TestPageResult:
    """Tests for PageResult dataclass."""

    def test_creation(self):
        """Test PageResult creation."""
        blocks = [TextBlock(text="Line 1", confidence=0.9)]
        page = PageResult(
            page_number=1,
            text_blocks=blocks,
            full_text="Line 1"
        )

        assert page.page_number == 1
        assert len(page.text_blocks) == 1
        assert page.full_text == "Line 1"

    def test_to_dict(self):
        """Test PageResult to_dict method."""
        page = PageResult(
            page_number=1,
            text_blocks=[TextBlock(text="Test")],
            full_text="Test",
            width=800,
            height=600
        )
        d = page.to_dict()

        assert d["page_number"] == 1
        assert d["full_text"] == "Test"
        assert d["width"] == 800
        assert d["height"] == 600
        assert len(d["text_blocks"]) == 1


class TestReadResult:
    """Tests for ReadResult dataclass."""

    def test_success_result(self):
        """Test successful ReadResult."""
        result = ReadResult(
            success=True,
            file_path="/test/file.png",
            file_type="image",
            engine_used="paddle",
            pages=[PageResult(page_number=1, full_text="Test")],
            full_text="Test",
            processing_time_ms=123.45,
            language="en"
        )

        assert result.success == True
        assert result.file_type == "image"
        assert result.engine_used == "paddle"
        assert result.error is None

    def test_error_result(self):
        """Test error result factory method."""
        result = ReadResult.error_result(
            "/test/file.txt",
            "File not found"
        )

        assert result.success == False
        assert result.error == "File not found"
        assert result.engine_used == "none"

    def test_to_dict(self):
        """Test ReadResult to_dict method."""
        result = ReadResult(
            success=True,
            file_path="/test/file.png",
            file_type="image",
            engine_used="paddle",
            full_text="Test content",
            processing_time_ms=100.5,
            language="en"
        )
        d = result.to_dict()

        assert d["success"] == True
        assert d["file_type"] == "image"
        assert d["processing_time_ms"] == 100.5
        assert "error" not in d  # No error
