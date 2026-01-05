"""
Pytest configuration and shared fixtures.
"""

import os
import sys
import pytest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Test data directory
TEST_DIR = Path(__file__).parent
FIXTURES_DIR = TEST_DIR / "fixtures"
PROJECT_ROOT = TEST_DIR.parent
EXAMPLES_DIR = PROJECT_ROOT / "examples"


@pytest.fixture
def project_root():
    """Return project root directory."""
    return PROJECT_ROOT


@pytest.fixture
def fixtures_dir():
    """Return test fixtures directory."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    return FIXTURES_DIR


@pytest.fixture
def examples_dir():
    """Return examples directory."""
    return EXAMPLES_DIR


@pytest.fixture
def sample_text_file(fixtures_dir):
    """Create a sample text file for testing."""
    file_path = fixtures_dir / "sample.txt"
    content = """Line 1: Hello World
Line 2: This is a test file
Line 3: With multiple lines
Line 4: For testing the Read Tool
Line 5: End of file"""
    file_path.write_text(content, encoding="utf-8")
    return str(file_path)


@pytest.fixture
def sample_arabic_text_file(fixtures_dir):
    """Create a sample Arabic text file for testing."""
    file_path = fixtures_dir / "sample_arabic.txt"
    content = """السطر 1: مرحبا بالعالم
السطر 2: هذا ملف اختبار
السطر 3: مع عدة أسطر
السطر 4: لاختبار أداة القراءة
السطر 5: نهاية الملف"""
    file_path.write_text(content, encoding="utf-8")
    return str(file_path)


@pytest.fixture
def sample_notebook_file(fixtures_dir):
    """Create a sample Jupyter notebook for testing."""
    import json

    file_path = fixtures_dir / "sample.ipynb"
    notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "source": ["# Test Notebook\n", "This is a test."]
            },
            {
                "cell_type": "code",
                "source": ["print('Hello World')"],
                "outputs": [
                    {
                        "output_type": "stream",
                        "text": ["Hello World\n"]
                    }
                ]
            }
        ],
        "metadata": {
            "kernelspec": {
                "name": "python3"
            },
            "language_info": {
                "name": "python"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }
    file_path.write_text(json.dumps(notebook), encoding="utf-8")
    return str(file_path)


@pytest.fixture
def long_text_file(fixtures_dir):
    """Create a long text file for testing offset/limit."""
    file_path = fixtures_dir / "long_file.txt"
    lines = [f"Line {i}: {'A' * 50} content here" for i in range(1, 3001)]
    content = "\n".join(lines)
    file_path.write_text(content, encoding="utf-8")
    return str(file_path)


@pytest.fixture
def arabic_invoice_image(examples_dir):
    """Return path to Arabic invoice image if it exists."""
    image_path = examples_dir / "OIP.webp"
    if image_path.exists():
        return str(image_path)
    return None


@pytest.fixture
def read_tool_config():
    """Create a test configuration."""
    from src.config import ReadToolConfig

    return ReadToolConfig(
        default_engine="paddle",
        fallback_enabled=True,
        fallback_order=["paddle", "tesseract"],
        paddle_use_gpu=False,
        debug=True
    )
