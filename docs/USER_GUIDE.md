# User Guide - Hybrid Read Tool

A comprehensive guide for using the Hybrid Read Tool OCR system.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Installation](#installation)
3. [Basic Usage](#basic-usage)
4. [API Usage](#api-usage)
5. [Working with Arabic Documents](#working-with-arabic-documents)
6. [Configuration Options](#configuration-options)
7. [Troubleshooting](#troubleshooting)

---

## Getting Started

The Hybrid Read Tool is an OCR (Optical Character Recognition) system designed to extract text from images and PDFs with high accuracy. It supports English and Arabic languages with special features for processing Arabic documents like invoices and receipts.

### Key Features

- **Offline Operation**: Works completely offline after initial setup
- **Multi-Engine**: PaddleOCR (primary) with Tesseract fallback
- **Bilingual Output**: Structured markdown output for Arabic documents
- **REST API**: Easy integration via HTTP endpoints
- **High Accuracy**: 95%+ accuracy target for Arabic documents

---

## Installation

### Prerequisites

- Python 3.10 or higher
- Windows, Linux, or macOS

### Quick Install

```bash
# Clone the repository
git clone <repository-url>
cd OCR_2

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
./venv/Scripts/activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Install Tesseract (Optional Fallback)

For Tesseract fallback support:

```bash
# Check if Tesseract is installed
python scripts/install_tesseract.py --check

# Install Tesseract (Windows)
python scripts/install_tesseract.py --install

# Install Arabic language pack
python scripts/install_tesseract.py --lang ar
```

---

## Basic Usage

### Python Library

```python
from src.read_tool import HybridReadTool

# Initialize the tool
reader = HybridReadTool()

# Read an image
result = reader.read("path/to/image.png")
print(result.full_text)

# Read with specific language
result = reader.read("path/to/arabic_invoice.png", lang="ar")
print(result.full_text)

# Get structured output for Arabic documents
print(result.structured_output)

# Read a PDF
result = reader.read("path/to/document.pdf", lang="en")
for page in result.pages:
    print(f"--- Page {page.page_number} ---")
    print(page.full_text)
```

### Command Line (via Python)

```bash
# Simple OCR
python -c "
from src.read_tool import HybridReadTool
reader = HybridReadTool()
result = reader.read('path/to/image.png')
print(result.full_text)
"
```

---

## API Usage

### Starting the API Server

```bash
python -m api.app
```

The server starts at `http://localhost:5000`.

### Health Check

```bash
curl http://localhost:5000/api/health
```

Response:
```json
{
  "success": true,
  "status": "ok",
  "version": "1.0.0",
  "supported_languages": ["en", "ar"],
  "supported_formats": ["png", "jpg", "jpeg", "pdf", ...],
  "available_engines": ["paddle", "tesseract"]
}
```

### OCR Processing

#### Full OCR (with metadata)

```bash
curl -X POST http://localhost:5000/api/ocr \
  -F "file=@document.png" \
  -F "lang=en"
```

Response:
```json
{
  "success": true,
  "data": {
    "file_type": "image",
    "engine_used": "paddle",
    "language": "en",
    "full_text": "Extracted text content...",
    "confidence": 0.95,
    "processing_time_ms": 1234
  }
}
```

#### Text-Only Extraction

```bash
curl -X POST http://localhost:5000/api/ocr/text \
  -F "file=@document.png" \
  -F "lang=en"
```

Response:
```json
{
  "success": true,
  "text": "Extracted text content..."
}
```

#### Structured Arabic Output

```bash
curl -X POST http://localhost:5000/api/ocr/structured \
  -F "file=@arabic_invoice.png" \
  -F "lang=ar"
```

Response:
```json
{
  "success": true,
  "data": {
    "full_text": "فاتورة ضريبية...",
    "structured_output": "# Tax Invoice (فاتورة ضريبية)\n\n## Header\n..."
  }
}
```

### Engine Management

#### List All Engines

```bash
curl http://localhost:5000/api/engines
```

#### Get Engine Details

```bash
curl http://localhost:5000/api/engines/paddle
```

#### Test Engine Availability

```bash
curl -X POST http://localhost:5000/api/engines/paddle/test
```

### Configuration

#### Get Current Configuration

```bash
curl http://localhost:5000/api/config
```

#### Update Configuration

```bash
curl -X PUT http://localhost:5000/api/config \
  -H "Content-Type: application/json" \
  -d '{"default_language": "ar", "fallback_enabled": true}'
```

---

## Working with Arabic Documents

The Hybrid Read Tool has special features for processing Arabic documents, particularly invoices and receipts.

### Structured Output Format

For Arabic documents, the tool generates bilingual markdown output:

```markdown
# Tax Invoice (فاتورة ضريبية)

## Invoice Header

| Field | Value | الحقل |
|-------|-------|-------|
| Date | 2022-12-21 | التاريخ |
| Invoice No. | 220130 | رقم الفاتورة |

## Customer Information (العميل)

| Field | Value |
|-------|-------|
| Customer (العميل) | شركة المثال |
| Address (العنوان) | الرياض |

## Items (البنود)

| # | Description (الوصف) | Qty (الكمية) | Price (السعر) | Total (المجموع) |
|---|---------------------|--------------|---------------|-----------------|
| 1 | منتج أول | 10 | 100.00 | 1000.00 |
| 2 | منتج ثاني | 5 | 200.00 | 1000.00 |

## Summary (ملخص)

| الاجمالي (Total) | 2000.00 |
| الضريبة (VAT 15%) | 300.00 |
| المجموع النهائي (Grand Total) | 2300.00 |
```

### Using Structured Output

```python
from src.read_tool import HybridReadTool

reader = HybridReadTool()
result = reader.read("arabic_invoice.png", lang="ar")

# Get the structured markdown output
structured = result.structured_output
print(structured)

# Check document metadata
print(f"Document Type: {result.metadata.get('document_type')}")
print(f"Is Bilingual: {result.metadata.get('is_bilingual')}")
```

### RTL Text Handling

Arabic text is automatically handled with proper right-to-left (RTL) ordering. The tool:

1. Detects Arabic text automatically
2. Preserves reading order
3. Aligns text correctly in structured output
4. Provides bilingual field translations

---

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `READ_TOOL_DEFAULT_ENGINE` | Default OCR engine (`paddle`, `tesseract`, `auto`) | `paddle` |
| `READ_TOOL_FALLBACK_ENABLED` | Enable fallback to alternative engines | `true` |
| `PADDLE_OCR_LANG` | Default PaddleOCR language | `en` |
| `PADDLE_OCR_USE_GPU` | Enable GPU acceleration for PaddleOCR | `false` |
| `TESSERACT_CMD` | Path to Tesseract executable | auto-detect |
| `MAX_FILE_SIZE_MB` | Maximum allowed file size | `50` |

### Programmatic Configuration

```python
from src.read_tool import HybridReadTool
from src.config import ReadToolConfig

# Create custom config
config = ReadToolConfig()
config.default_engine = "paddle"
config.fallback_enabled = True
config.paddle_use_gpu = False

# Initialize with config
reader = HybridReadTool(config=config)
```

### Supported Languages

| Code | Language | Script Direction |
|------|----------|------------------|
| `en` | English | Left-to-Right (LTR) |
| `ar` | Arabic | Right-to-Left (RTL) |

### Supported File Formats

**Images:**
- PNG (`.png`)
- JPEG (`.jpg`, `.jpeg`)
- GIF (`.gif`)
- BMP (`.bmp`)
- TIFF (`.tiff`, `.tif`)
- WebP (`.webp`)

**Documents:**
- PDF (`.pdf`)

---

## Troubleshooting

### PaddleOCR Not Loading

**Symptom:** Error message about PaddleOCR not being available.

**Solutions:**
1. Install PaddlePaddle: `pip install paddlepaddle`
2. For CPU-only: `pip install paddlepaddle -i https://pypi.tuna.tsinghua.edu.cn/simple`
3. Check Python version compatibility (3.10+ recommended)

### Tesseract Not Found

**Symptom:** Tesseract fallback not working.

**Solutions:**
```bash
# Check installation
python scripts/install_tesseract.py --check

# Verify Tesseract is in PATH
tesseract --version

# Set path manually (Windows)
set TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

### Arabic Text Appears Reversed

**Symptom:** Arabic text is displayed backwards.

**Solutions:**
1. The tool handles RTL automatically - check if you're using `result.full_text`
2. Use `result.structured_output` for properly formatted bilingual output
3. Check `result.metadata['is_bilingual']` to verify Arabic detection

### Low OCR Accuracy

**Symptom:** Extracted text has many errors.

**Solutions:**
1. **Image Quality**: Use higher resolution images (300 DPI recommended)
2. **Preprocessing**: Ensure good contrast and minimal noise
3. **Language Setting**: Make sure correct language is specified
4. **Engine Selection**: Try different engines (`paddle` vs `tesseract`)

### API Server Won't Start

**Symptom:** Flask server fails to start.

**Solutions:**
1. Check if port 5000 is already in use
2. Verify virtual environment is activated
3. Check all dependencies are installed: `pip install -r requirements.txt`
4. Look at error logs for specific issues

### Out of Memory Errors

**Symptom:** Process crashes on large files.

**Solutions:**
1. Reduce image resolution before processing
2. Process PDFs page by page
3. Increase system memory
4. Use CPU mode instead of GPU: `PADDLE_OCR_USE_GPU=false`

### File Upload Errors

**Symptom:** API rejects file uploads.

**Solutions:**
1. Check file size (default max: 50MB)
2. Verify file format is supported
3. Ensure file is not corrupted
4. Check server logs for specific errors

---

## Getting Help

If you encounter issues not covered in this guide:

1. Check the [README](../README.md) for quick reference
2. Review the [Developer Guide](DEVELOPER_GUIDE.md) for technical details
3. Open an issue on the repository

---

Built with [Claude Code](https://claude.ai/code)
