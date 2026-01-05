"""
Unit tests for HybridReadTool.
"""

import pytest
import os
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.read_tool import HybridReadTool
from src.config import ReadToolConfig


class TestHybridReadToolTextFiles:
    """Tests for text file reading."""

    @pytest.fixture
    def reader(self):
        """Create a HybridReadTool instance."""
        config = ReadToolConfig(debug=True)
        return HybridReadTool(config)

    def test_read_text_file(self, reader, sample_text_file):
        """Test reading a basic text file."""
        result = reader.read(sample_text_file)

        assert result.success == True
        assert result.file_type == "text"
        assert result.engine_used == "native"
        assert "Line 1" in result.full_text
        assert "Hello World" in result.full_text

    def test_read_text_file_with_line_numbers(self, reader, sample_text_file):
        """Test that text files have line numbers (cat -n format)."""
        result = reader.read(sample_text_file)

        # Should have format like "     1\tContent"
        lines = result.full_text.split('\n')
        assert lines[0].strip().startswith('1')
        assert '\t' in lines[0]

    def test_read_text_file_with_offset(self, reader, long_text_file):
        """Test reading with offset."""
        result = reader.read(long_text_file, offset=100, limit=10)

        assert result.success == True
        assert result.metadata["offset"] == 100
        assert result.metadata["lines_read"] == 10

        # First line should be line 101
        first_line = result.full_text.split('\n')[0]
        assert "101" in first_line

    def test_read_text_file_with_limit(self, reader, long_text_file):
        """Test reading with limit."""
        result = reader.read(long_text_file, limit=50)

        assert result.success == True
        assert result.metadata["lines_read"] == 50

    def test_read_text_file_truncates_long_lines(self, reader, fixtures_dir):
        """Test that long lines are truncated at 2000 chars."""
        # Create file with very long line
        file_path = fixtures_dir / "long_line.txt"
        long_line = "A" * 3000
        file_path.write_text(long_line)

        result = reader.read(str(file_path))

        assert result.success == True
        # Line should be truncated with "..."
        assert "..." in result.full_text
        # Original content after line number should be <= 2000 + "..."
        content = result.full_text.split('\t')[1] if '\t' in result.full_text else result.full_text
        assert len(content) <= 2003  # 2000 + "..."

    def test_read_arabic_text_file(self, reader, sample_arabic_text_file):
        """Test reading Arabic text file."""
        result = reader.read(sample_arabic_text_file)

        assert result.success == True
        assert "مرحبا" in result.full_text  # "Hello" in Arabic


class TestHybridReadToolValidation:
    """Tests for file path validation."""

    @pytest.fixture
    def reader(self):
        """Create a HybridReadTool instance."""
        return HybridReadTool()

    def test_relative_path_rejected(self, reader):
        """Test that relative paths are rejected."""
        result = reader.read("relative/path/file.txt")

        assert result.success == False
        assert "absolute" in result.error.lower()

    def test_nonexistent_file_rejected(self, reader, fixtures_dir):
        """Test that nonexistent files are rejected."""
        # Use an absolute path that doesn't exist
        nonexistent = str(Path(fixtures_dir) / "nonexistent_file_xyz.txt")
        result = reader.read(nonexistent)

        assert result.success == False
        assert "not found" in result.error.lower()

    def test_directory_rejected(self, reader, fixtures_dir):
        """Test that directories are rejected."""
        result = reader.read(str(fixtures_dir))

        assert result.success == False
        assert "directory" in result.error.lower()


class TestHybridReadToolNotebooks:
    """Tests for Jupyter notebook reading."""

    @pytest.fixture
    def reader(self):
        """Create a HybridReadTool instance."""
        return HybridReadTool()

    def test_read_notebook(self, reader, sample_notebook_file):
        """Test reading a Jupyter notebook."""
        result = reader.read(sample_notebook_file)

        assert result.success == True
        assert result.file_type == "notebook"
        assert "Test Notebook" in result.full_text
        assert "Hello World" in result.full_text

    def test_notebook_metadata(self, reader, sample_notebook_file):
        """Test notebook metadata extraction."""
        result = reader.read(sample_notebook_file)

        assert "total_cells" in result.metadata
        assert result.metadata["total_cells"] == 2
        assert result.metadata["kernel"] == "python3"


class TestHybridReadToolEngines:
    """Tests for engine management."""

    @pytest.fixture
    def reader(self):
        """Create a HybridReadTool instance."""
        return HybridReadTool()

    def test_get_available_engines(self, reader):
        """Test getting available engine information."""
        info = reader.get_available_engines()

        assert "engines" in info
        assert "default_engine" in info
        assert isinstance(info["engines"], list)

    def test_paddle_engine_registered(self, reader):
        """Test that PaddleEngine is registered."""
        info = reader.get_available_engines()
        engine_names = [e["name"] for e in info["engines"]]

        assert "paddle" in engine_names
