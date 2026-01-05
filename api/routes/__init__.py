"""
API Route Blueprints.

Organizes API endpoints into logical groups:
- ocr_routes: OCR processing endpoints
- engines_routes: Engine management endpoints
- config_routes: Configuration endpoints
"""

from .ocr_routes import ocr_bp
from .engines_routes import engines_bp
from .config_routes import config_bp

__all__ = ["ocr_bp", "engines_bp", "config_bp"]
