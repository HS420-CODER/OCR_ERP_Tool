# Changelog

All notable changes to the Hybrid Read Tool are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-05

### Added

#### Phase 1: Foundation
- **HybridReadTool** main class (`src/read_tool.py`)
  - Claude Code CLI-like `read()` method
  - Support for images (PNG, JPG, WEBP, etc.) and PDFs
  - Line number output (cat -n format)
  - Offset and limit parameters for large files
- **ReadToolConfig** configuration management (`src/config.py`)
  - Environment variable support
  - Engine and language settings
  - File size limits
- **Data Models** (`src/models.py`)
  - `ReadResult` - Complete OCR result
  - `PageResult` - Per-page result
  - `OCRBox` - Individual text detection
- **PaddleEngine** OCR engine (`src/engines/paddle_engine.py`)
  - PP-OCRv5 model integration
  - English and Arabic language support
  - GPU acceleration option
  - Table and structure detection
- **EngineManager** for engine orchestration (`src/engine_manager.py`)
  - Engine registration system
  - Availability caching
  - Fallback chain support
- **File utilities** (`src/utils/file_utils.py`)
  - File type detection
  - Path validation

#### Phase 1.5: Structured Arabic Output
- **OutputFormatter** (`src/formatters/output_formatter.py`)
  - Bilingual markdown output
  - Claude Code-style formatting
  - Invoice/receipt structure detection
- **DocumentAnalyzer** (`src/formatters/document_analyzer.py`)
  - Document type detection (invoice, receipt, unknown)
  - Section identification
  - Bilingual content detection
- **FieldDictionary** (`src/formatters/field_dictionary.py`)
  - Arabic-English field translations
  - 50+ invoice field mappings
  - Reverse lookup support
- **Structured output format**
  - Markdown tables with bilingual headers
  - Section organization (Header, Customer, Items, Summary)
  - RTL text handling

#### Phase 2: Tesseract Fallback Engine
- **TesseractEngine** (`src/engines/tesseract_engine.py`)
  - Full pytesseract integration
  - Windows path auto-detection
  - Language mapping (en→eng, ar→ara)
  - Image and PDF processing
- **Installation script** (`scripts/install_tesseract.py`)
  - Windows installation support
  - Language pack downloads
  - Installation verification
- **Fallback support**
  - Automatic fallback when PaddleOCR unavailable
  - Configurable fallback order

#### Phase 4: Flask REST API
- **Application factory** (`api/app.py`)
  - Blueprint-based architecture
  - Static file serving for frontend
  - Centralized error handling
- **OCR Routes** (`api/routes/ocr_routes.py`)
  - `POST /api/ocr` - Full OCR processing
  - `POST /api/ocr/text` - Text-only extraction
  - `POST /api/ocr/structured` - Bilingual structured output
  - `GET /api/languages` - List supported languages
- **Engine Routes** (`api/routes/engines_routes.py`)
  - `GET /api/engines` - List all engines
  - `GET /api/engines/<name>` - Engine details
  - `POST /api/engines/<name>/test` - Test availability
  - `GET /api/engines/available` - List available engines
- **Config Routes** (`api/routes/config_routes.py`)
  - `GET /api/health` - Health check
  - `GET /api/config` - Get configuration
  - `PUT /api/config` - Update configuration
  - `GET /api/version` - API version info

#### Phase 5: Polish & Documentation
- **README.md** - Complete project documentation
- **docs/USER_GUIDE.md** - End-user guide
- **docs/DEVELOPER_GUIDE.md** - Developer documentation
- **CHANGELOG.md** - This file

### Test Suite
- 134 total tests (4 skipped)
- Unit tests for all core components
- Integration tests for API endpoints
- 65% code coverage

### Dependencies
- paddlepaddle >= 2.5.0
- paddleocr >= 2.7.0
- pytesseract >= 0.3.10
- flask >= 2.3.0
- pdf2image >= 1.16.0
- Pillow >= 10.0.0
- numpy >= 1.24.0
- pytest >= 7.4.0

---

## [Unreleased]

### Planned
- React.js frontend interface
- Batch processing support
- Additional language support
- Performance optimizations
- Docker containerization

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | 2026-01-05 | Initial release with PaddleOCR, Tesseract, and Flask API |

---

Built with [Claude Code](https://claude.ai/code)
