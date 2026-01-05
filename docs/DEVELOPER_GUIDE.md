# Developer Guide - Hybrid Read Tool

Technical documentation for developers who want to extend, modify, or contribute to the Hybrid Read Tool.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Adding a New OCR Engine](#adding-a-new-ocr-engine)
5. [Extending the Formatter](#extending-the-formatter)
6. [API Development](#api-development)
7. [Testing](#testing)
8. [Code Style Guidelines](#code-style-guidelines)

---

## Architecture Overview

The Hybrid Read Tool follows a modular architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Flask REST API                           │
│                   (api/routes/*.py)                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   HybridReadTool                            │
│                  (src/read_tool.py)                         │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │   Config    │  │ EngineManager │  │ OutputFormatter   │  │
│  └─────────────┘  └──────────────┘  └───────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ PaddleEngine │ │TesseractEngine│ │ Future Engine│
    └──────────────┘ └──────────────┘ └──────────────┘
```

### Design Principles

1. **Plugin Architecture**: Engines are pluggable via the BaseEngine interface
2. **Fallback Chain**: Automatic fallback between engines on failure
3. **Structured Output**: Consistent data models for all output
4. **Bilingual Support**: Arabic-English translation built into formatters

---

## Project Structure

```
OCR_2/
├── src/                        # Core library
│   ├── __init__.py
│   ├── read_tool.py           # Main HybridReadTool class
│   ├── config.py              # ReadToolConfig - configuration management
│   ├── models.py              # Data models (ReadResult, OCRBox, etc.)
│   ├── engine_manager.py      # Engine orchestration and fallback
│   │
│   ├── engines/               # OCR engine implementations
│   │   ├── __init__.py
│   │   ├── base_engine.py     # Abstract BaseEngine class
│   │   ├── paddle_engine.py   # PaddleOCR implementation
│   │   └── tesseract_engine.py # Tesseract implementation
│   │
│   ├── formatters/            # Output formatting
│   │   ├── __init__.py
│   │   ├── field_dictionary.py    # Arabic-English field translations
│   │   ├── document_analyzer.py   # Document type detection
│   │   └── output_formatter.py    # Structured markdown generation
│   │
│   └── utils/                 # Utilities
│       ├── __init__.py
│       └── file_utils.py      # File type detection, etc.
│
├── api/                       # Flask REST API
│   ├── __init__.py
│   ├── app.py                # Application factory
│   └── routes/               # API blueprints
│       ├── __init__.py
│       ├── ocr_routes.py     # /api/ocr endpoints
│       ├── engines_routes.py # /api/engines endpoints
│       └── config_routes.py  # /api/config, /api/health
│
├── tests/                    # Test suite
│   ├── __init__.py
│   ├── conftest.py          # Shared fixtures
│   ├── fixtures/            # Test files
│   ├── unit/                # Unit tests
│   │   ├── test_read_tool.py
│   │   ├── test_config.py
│   │   ├── test_models.py
│   │   ├── test_engine_manager.py
│   │   ├── test_paddle_engine.py
│   │   ├── test_tesseract_engine.py
│   │   └── test_formatters.py
│   └── integration/         # API integration tests
│       └── test_api_endpoints.py
│
├── scripts/                 # Utility scripts
│   └── install_tesseract.py
│
├── docs/                    # Documentation
│   ├── USER_GUIDE.md
│   └── DEVELOPER_GUIDE.md
│
├── examples/                # Example files
│   └── ...
│
├── requirements.txt         # Python dependencies
├── README.md               # Project overview
└── CLAUDE.md               # Claude Code instructions
```

---

## Core Components

### HybridReadTool (src/read_tool.py)

The main entry point for all OCR operations.

```python
class HybridReadTool:
    def __init__(self, config: ReadToolConfig = None):
        self.config = config or ReadToolConfig()
        self.engine_manager = EngineManager(self.config)
        self.output_formatter = OutputFormatter()

    def read(self, file_path: str, lang: str = "en",
             engine: str = None, structured: bool = True) -> ReadResult:
        """Main method for reading files with OCR."""
        pass

    def get_available_engines(self) -> dict:
        """Returns info about available engines."""
        pass
```

### ReadToolConfig (src/config.py)

Configuration management with environment variable support.

```python
class ReadToolConfig:
    # Engine settings
    default_engine: str = "paddle"
    fallback_enabled: bool = True
    fallback_order: List[str] = ["paddle", "tesseract"]

    # PaddleOCR settings
    paddle_lang: str = "en"
    paddle_use_gpu: bool = False

    # Tesseract settings
    tesseract_cmd: str = None  # Auto-detect

    # File settings
    max_file_size_mb: int = 50

    # Output settings
    structured_output: bool = True
```

### Data Models (src/models.py)

```python
@dataclass
class OCRBox:
    """Single detected text region."""
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2

@dataclass
class PageResult:
    """OCR result for a single page."""
    page_number: int
    full_text: str
    boxes: List[OCRBox]
    confidence: float

@dataclass
class ReadResult:
    """Complete OCR result."""
    file_path: str
    file_type: str
    full_text: str
    pages: List[PageResult]
    structured_output: str
    metadata: Dict[str, Any]
    engine_used: str
    processing_time_ms: int
```

### EngineManager (src/engine_manager.py)

Handles engine registration, selection, and fallback logic.

```python
class EngineManager:
    def register_engine_class(self, name: str, engine_class: Type[BaseEngine]):
        """Register an engine class."""
        pass

    def get_engine(self, name: str) -> BaseEngine:
        """Get or create an engine instance."""
        pass

    def is_available(self, name: str) -> bool:
        """Check if engine is available."""
        pass

    def process_with_fallback(self, file_path: str, lang: str) -> OCRResult:
        """Process with automatic fallback on failure."""
        pass
```

---

## Adding a New OCR Engine

### Step 1: Create Engine Class

Create `src/engines/new_engine.py`:

```python
"""
New OCR Engine Implementation.
"""

import logging
from typing import List, Optional
from pathlib import Path

from .base_engine import BaseEngine
from ..models import OCRBox, PageResult

logger = logging.getLogger(__name__)


class NewEngine(BaseEngine):
    """New OCR engine implementation."""

    # Engine metadata
    ENGINE_NAME = "new_engine"
    DISPLAY_NAME = "New OCR Engine"
    SUPPORTED_LANGUAGES = ["en", "ar"]  # Languages this engine supports

    def __init__(self, config=None):
        super().__init__(config)
        self._engine = None

    @classmethod
    def is_available(cls) -> bool:
        """Check if engine dependencies are installed."""
        try:
            import new_ocr_library
            return True
        except ImportError:
            return False

    def _initialize(self):
        """Lazy initialization of the engine."""
        if self._engine is None:
            import new_ocr_library
            self._engine = new_ocr_library.create_engine()

    def process_image(self, image_path: str, lang: str = "en") -> PageResult:
        """
        Process a single image.

        Args:
            image_path: Path to image file
            lang: Language code ("en" or "ar")

        Returns:
            PageResult with extracted text and boxes
        """
        self._initialize()

        # Perform OCR
        raw_result = self._engine.ocr(image_path, lang=lang)

        # Convert to standard format
        boxes = []
        for item in raw_result:
            box = OCRBox(
                text=item['text'],
                confidence=item['confidence'],
                bbox=(item['x1'], item['y1'], item['x2'], item['y2'])
            )
            boxes.append(box)

        # Combine text
        full_text = "\n".join(box.text for box in boxes)
        avg_confidence = sum(b.confidence for b in boxes) / len(boxes) if boxes else 0.0

        return PageResult(
            page_number=1,
            full_text=full_text,
            boxes=boxes,
            confidence=avg_confidence
        )

    def process_pdf(self, pdf_path: str, lang: str = "en") -> List[PageResult]:
        """
        Process a PDF document.

        Args:
            pdf_path: Path to PDF file
            lang: Language code

        Returns:
            List of PageResult, one per page
        """
        self._initialize()

        # Convert PDF to images and process
        results = []
        images = self._pdf_to_images(pdf_path)

        for i, img in enumerate(images):
            page_result = self.process_image(img, lang=lang)
            page_result.page_number = i + 1
            results.append(page_result)

        return results

    def get_capabilities(self) -> dict:
        """Return engine capabilities."""
        return {
            "supports_images": True,
            "supports_pdf": True,
            "supports_gpu": False,
            "supported_languages": self.SUPPORTED_LANGUAGES,
            "supports_tables": False,
            "supports_structure": False
        }
```

### Step 2: Register the Engine

In `src/read_tool.py`, add registration:

```python
from src.engines.new_engine import NewEngine

class HybridReadTool:
    def __init__(self, config=None):
        # ... existing code ...

        # Register engines
        self.engine_manager.register_engine_class("paddle", PaddleEngine)
        self.engine_manager.register_engine_class("tesseract", TesseractEngine)
        self.engine_manager.register_engine_class("new_engine", NewEngine)  # Add this
```

### Step 3: Add Tests

Create `tests/unit/test_new_engine.py`:

```python
"""Tests for NewEngine."""

import pytest
from unittest.mock import Mock, patch

from src.engines.new_engine import NewEngine


class TestNewEngineAvailability:
    """Tests for engine availability detection."""

    def test_is_available_when_installed(self):
        with patch.dict('sys.modules', {'new_ocr_library': Mock()}):
            assert NewEngine.is_available() == True

    def test_is_available_when_not_installed(self):
        with patch.dict('sys.modules', {'new_ocr_library': None}):
            assert NewEngine.is_available() == False


class TestNewEngineProcessing:
    """Tests for OCR processing."""

    @pytest.fixture
    def engine(self):
        with patch('src.engines.new_engine.new_ocr_library'):
            return NewEngine()

    def test_process_image_returns_page_result(self, engine):
        # ... test implementation
        pass
```

### Step 4: Update Configuration

Add to `src/config.py` if engine needs settings:

```python
class ReadToolConfig:
    # ... existing settings ...

    # New Engine settings
    new_engine_option: str = "default_value"
```

---

## Extending the Formatter

### Adding Field Translations

Edit `src/formatters/field_dictionary.py`:

```python
# Invoice field translations
INVOICE_FIELDS = {
    # Arabic → English
    "فاتورة ضريبية": "Tax Invoice",
    "التاريخ": "Date",
    "رقم الفاتورة": "Invoice Number",
    # Add new translations here:
    "الحقل الجديد": "New Field",
}

# Add reverse lookup
INVOICE_FIELDS_REVERSE = {v: k for k, v in INVOICE_FIELDS.items()}
```

### Adding Document Types

Edit `src/formatters/document_analyzer.py`:

```python
class DocumentType(Enum):
    UNKNOWN = "unknown"
    INVOICE = "invoice"
    RECEIPT = "receipt"
    CONTRACT = "contract"  # Add new type

class DocumentAnalyzer:
    # Add detection keywords
    CONTRACT_KEYWORDS = ["عقد", "اتفاقية", "contract", "agreement"]

    def detect_type(self, text: str) -> DocumentType:
        text_lower = text.lower()

        # Check for contract
        if any(kw in text_lower for kw in self.CONTRACT_KEYWORDS):
            return DocumentType.CONTRACT

        # ... existing detection logic
```

### Adding Output Sections

Edit `src/formatters/output_formatter.py`:

```python
class OutputFormatter:
    def format_contract(self, result: ReadResult) -> str:
        """Format contract document output."""
        sections = []

        # Header
        sections.append("# Contract (عقد)")
        sections.append("")

        # Parties section
        sections.append("## Parties (الأطراف)")
        # ... add formatting logic

        return "\n".join(sections)
```

---

## API Development

### Adding a New Endpoint

Create or edit route files in `api/routes/`:

```python
# api/routes/new_routes.py
from flask import Blueprint, jsonify, request

new_bp = Blueprint('new', __name__, url_prefix='/api/new')

@new_bp.route('/action', methods=['POST'])
def perform_action():
    """
    Perform a new action.

    Request Body (JSON):
        {"param": "value"}

    Response:
        {"success": true, "result": ...}
    """
    try:
        data = request.get_json() or {}
        param = data.get('param', 'default')

        # Perform action
        result = do_something(param)

        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

Register in `api/app.py`:

```python
from api.routes.new_routes import new_bp

def _register_blueprints(app):
    # ... existing blueprints ...
    app.register_blueprint(new_bp)
```

### Error Handling

Use consistent error responses:

```python
# Success response
return jsonify({
    'success': True,
    'data': {...}
})

# Client error (4xx)
return jsonify({
    'success': False,
    'error': 'Description of what went wrong'
}), 400

# Server error (5xx)
return jsonify({
    'success': False,
    'error': 'Internal server error'
}), 500
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov=api --cov-report=html

# Run specific test file
pytest tests/unit/test_formatters.py -v

# Run tests matching pattern
pytest tests/ -k "test_paddle" -v

# Run with verbose output
pytest tests/ -v --tb=short
```

### Test Structure

```python
"""Tests for MyComponent."""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestMyComponentInit:
    """Tests for initialization."""

    def test_default_initialization(self):
        """Test default values on init."""
        component = MyComponent()
        assert component.setting == "default"

    def test_custom_initialization(self):
        """Test custom config on init."""
        component = MyComponent(setting="custom")
        assert component.setting == "custom"


class TestMyComponentMethod:
    """Tests for specific method."""

    @pytest.fixture
    def component(self):
        """Create component for testing."""
        return MyComponent()

    def test_method_success(self, component):
        """Test successful method execution."""
        result = component.method("input")
        assert result == "expected"

    def test_method_error_handling(self, component):
        """Test error handling."""
        with pytest.raises(ValueError):
            component.method(None)


class TestMyComponentIntegration:
    """Integration tests requiring external resources."""

    @pytest.mark.skipif(not resource_available(), reason="Resource not available")
    def test_with_real_resource(self):
        """Test with actual external resource."""
        pass
```

### Mocking External Dependencies

```python
from unittest.mock import Mock, patch, MagicMock

# Mock a module import
with patch.dict('sys.modules', {'external_lib': Mock()}):
    from src.engines.my_engine import MyEngine

# Mock a class method
with patch.object(MyClass, 'method', return_value='mocked'):
    result = instance.method()

# Mock file operations
with patch('builtins.open', mock_open(read_data='file content')):
    result = read_file('path')

# Mock entire class
mock_engine = MagicMock(spec=BaseEngine)
mock_engine.process_image.return_value = PageResult(...)
```

---

## Code Style Guidelines

### Python Style

- Follow PEP 8
- Use type hints for function signatures
- Maximum line length: 100 characters
- Use docstrings for all public methods

```python
def process_document(
    self,
    file_path: str,
    lang: str = "en",
    options: Optional[Dict[str, Any]] = None
) -> ReadResult:
    """
    Process a document with OCR.

    Args:
        file_path: Path to the document file
        lang: Language code ("en" or "ar")
        options: Optional processing options

    Returns:
        ReadResult containing extracted text and metadata

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If language is not supported
    """
    pass
```

### Imports

Order imports as:
1. Standard library
2. Third-party packages
3. Local imports

```python
import logging
import os
from pathlib import Path
from typing import List, Optional

import numpy as np
from flask import Blueprint, jsonify

from src.models import ReadResult
from src.config import ReadToolConfig
```

### Logging

Use the logging module, not print statements:

```python
import logging

logger = logging.getLogger(__name__)

def my_function():
    logger.debug("Detailed debug info")
    logger.info("General information")
    logger.warning("Warning message")
    logger.error("Error occurred")
    logger.exception("Error with traceback")
```

### Error Handling

```python
# Specific exceptions
try:
    result = risky_operation()
except FileNotFoundError:
    logger.error(f"File not found: {path}")
    raise
except ValueError as e:
    logger.warning(f"Invalid value: {e}")
    return default_value

# Don't catch Exception broadly unless re-raising
try:
    operation()
except Exception:
    logger.exception("Unexpected error")
    raise
```

---

## Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Write tests first (TDD recommended)
3. Implement the feature
4. Ensure all tests pass: `pytest tests/ -v`
5. Check coverage: `pytest tests/ --cov=src --cov=api`
6. Commit with descriptive message
7. Create pull request

---

Built with [Claude Code](https://claude.ai/code)
