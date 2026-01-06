"""
ERP Arabic OCR Microservice - WSGI Entry Point
===============================================
Production entry point for Gunicorn/uWSGI deployment.

Usage:
    gunicorn wsgi:app --config config/gunicorn.conf.py
    gunicorn wsgi:app -w 4 -b 0.0.0.0:5000
"""

import os
import sys
import logging
from pathlib import Path

# Disable model source check for offline operation
os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Import and create application
from api import create_app

# Create the WSGI application
app = create_app()

logger.info("WSGI application initialized")
logger.info("v2 API endpoints available at /api/v2/ocr/*")


if __name__ == '__main__':
    # For local development/testing
    from api.app import run_server
    run_server()
