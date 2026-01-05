"""
Flask API Package for Hybrid Read Tool.

Provides REST API endpoints for OCR processing with:
- PaddleOCR (primary)
- Tesseract (fallback)
- Structured bilingual output for Arabic documents

Endpoints:
- /api/health - Health check
- /api/ocr - OCR processing
- /api/engines - Engine management
- /api/config - Configuration
- /api/languages - Supported languages
"""

from .app import create_app

__all__ = ["create_app"]
