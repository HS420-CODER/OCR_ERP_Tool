# Hybrid Read Tool for OCR

A powerful OCR (Optical Character Recognition) tool built with PaddleOCR and Tesseract for extracting text from images and PDFs. Features Claude Code CLI-like functionality with structured bilingual output for Arabic documents.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PaddleOCR](https://img.shields.io/badge/PaddleOCR-PP--OCRv5-green.svg)
![Tesseract](https://img.shields.io/badge/Tesseract-5.3+-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Features

- **Multi-Engine OCR**: PaddleOCR (primary) with Tesseract fallback
- **Bilingual Support**: English and Arabic with RTL text handling
- **Structured Output**: Claude Code-like markdown for Arabic invoices
- **File Type Support**: Images (PNG, JPG, WEBP, etc.), PDFs, Jupyter notebooks
- **REST API**: Flask-based API with blueprint architecture
- **Offline Mode**: Works completely offline after model download
- **High Accuracy**: 95%+ accuracy target for Arabic documents

## Quick Start

### Installation

```bash
# Clone and setup
git clone <repository-url>
cd OCR_2

# Create virtual environment
python -m venv venv
./venv/Scripts/activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### Run the API Server

```bash
python -m api.app
```

Server starts at http://localhost:5000

### Python Usage

```python
from src.read_tool import HybridReadTool

# Initialize
reader = HybridReadTool()

# Read an image with OCR
result = reader.read("/path/to/invoice.png", lang="ar")
print(result.full_text)

# Get structured bilingual output
print(result.structured_output)

# Read a PDF
result = reader.read("/path/to/document.pdf", lang="en")
for page in result.pages:
    print(f"Page {page.page_number}: {page.full_text}")
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check and status |
| GET | `/api/config` | Get configuration |
| PUT | `/api/config` | Update configuration |
| GET | `/api/engines` | List OCR engines |
| GET | `/api/engines/<name>` | Get engine details |
| GET | `/api/languages` | List supported languages |
| POST | `/api/ocr` | Full OCR processing |
| POST | `/api/ocr/text` | Text-only extraction |
| POST | `/api/ocr/structured` | Bilingual structured output |

### Example: OCR Processing

```bash
curl -X POST http://localhost:5000/api/ocr \
  -F "file=@invoice.png" \
  -F "lang=ar" \
  -F "structured=true"
```

Response:
```json
{
  "success": true,
  "data": {
    "file_type": "image",
    "engine_used": "paddle",
    "language": "ar",
    "full_text": "فاتورة ضريبية...",
    "structured_output": "# Tax Invoice (فاتورة ضريبية)\n..."
  }
}
```

## Project Structure

```
OCR_2/
├── src/                    # Core library
│   ├── read_tool.py       # Main HybridReadTool class
│   ├── config.py          # Configuration management
│   ├── models.py          # Data models (ReadResult, etc.)
│   ├── engine_manager.py  # OCR engine orchestration
│   ├── engines/           # OCR engine implementations
│   │   ├── paddle_engine.py   # PaddleOCR (primary)
│   │   └── tesseract_engine.py # Tesseract (fallback)
│   ├── formatters/        # Output formatting
│   │   ├── field_dictionary.py    # Arabic-English translations
│   │   ├── document_analyzer.py   # Document structure analysis
│   │   └── output_formatter.py    # Structured markdown output
│   └── utils/             # Utility functions
│       └── file_utils.py
├── api/                   # Flask REST API
│   ├── app.py            # Application factory
│   └── routes/           # API blueprints
│       ├── ocr_routes.py
│       ├── engines_routes.py
│       └── config_routes.py
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   └── integration/      # API integration tests
├── scripts/              # Utility scripts
│   └── install_tesseract.py
├── docs/                 # Documentation
└── examples/             # Example files
```

## Supported Languages

| Code | Language | Direction |
|------|----------|-----------|
| `en` | English | LTR |
| `ar` | Arabic | RTL |

## OCR Engines

### PaddleOCR (Primary)
- High accuracy PP-OCRv5 models
- GPU acceleration support
- Table detection and structure analysis
- Best for complex documents

### Tesseract (Fallback)
- Industry-standard OCR engine
- Wide language support
- Runs when PaddleOCR unavailable

Install Tesseract:
```bash
python scripts/install_tesseract.py --install
python scripts/install_tesseract.py --lang ar
```

## Structured Arabic Output

For Arabic documents (invoices, receipts), the tool generates Claude Code-like bilingual markdown:

```markdown
# Tax Invoice (فاتورة ضريبية)

## Invoice Header

| Field | Value | الحقل |
|-------|-------|-------|
| Date | 2022-12-21 | التاريخ |
| Invoice No. | 220130 | الرقم |

## Customer Information (العميل)

| Field | Value |
|-------|-------|
| Customer (العميل) | قرطاسية اصل |

## Summary (ملخص)

| الاجمالي (Total) | 2000.00 |
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `READ_TOOL_DEFAULT_ENGINE` | Default OCR engine | `paddle` |
| `READ_TOOL_FALLBACK_ENABLED` | Enable engine fallback | `true` |
| `PADDLE_OCR_LANG` | PaddleOCR language | `en` |
| `PADDLE_OCR_USE_GPU` | Enable GPU acceleration | `false` |
| `TESSERACT_CMD` | Path to Tesseract executable | auto-detect |
| `MAX_FILE_SIZE_MB` | Maximum file size | `50` |

### API Configuration

```python
from api import create_app

app = create_app({
    'UPLOAD_FOLDER': '/custom/upload/path',
    'MAX_CONTENT_LENGTH': 100 * 1024 * 1024  # 100MB
})
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov=api --cov-report=html

# Run specific test file
pytest tests/unit/test_formatters.py -v
```

## Development

### Adding a New Engine

1. Create `src/engines/new_engine.py` extending `BaseEngine`
2. Implement required methods: `process_image()`, `process_pdf()`
3. Register in `src/read_tool.py`:
   ```python
   self.engine_manager.register_engine_class("new", NewEngine)
   ```

### Adding Field Translations

Edit `src/formatters/field_dictionary.py`:
```python
INVOICE_FIELDS["الحقل الجديد"] = "New Field"
```

## Troubleshooting

### PaddleOCR not loading
- Ensure PaddlePaddle is installed: `pip install paddlepaddle`
- Check GPU drivers if using CUDA

### Tesseract not found
- Run: `python scripts/install_tesseract.py --check`
- Install language packs: `--lang ar`

### Arabic text reversed
- The tool handles RTL automatically
- Check document structure with `result.metadata['is_bilingual']`

## License

MIT License - see [LICENSE](LICENSE)

## Acknowledgments

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) - Primary OCR engine
- [Tesseract](https://github.com/tesseract-ocr/tesseract) - Fallback OCR engine
- [Flask](https://flask.palletsprojects.com/) - Web framework

---

Built with [Claude Code](https://claude.ai/code)
