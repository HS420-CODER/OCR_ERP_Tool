"""
OCR Processing Routes.

Endpoints:
- POST /api/ocr - Process file with OCR (full result)
- POST /api/ocr/text - Extract text only
- POST /api/ocr/structured - Get structured bilingual output
"""

import os
import uuid
import logging
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

ocr_bp = Blueprint('ocr', __name__, url_prefix='/api')

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'tif', 'webp', 'pdf'}


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_extension(filename: str) -> str:
    """Get file extension."""
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''


def save_uploaded_file(file) -> tuple:
    """
    Save uploaded file to temporary location.

    Returns:
        Tuple of (filepath, filename, error)
    """
    if not file or file.filename == '':
        return None, None, "No file provided"

    if not allowed_file(file.filename):
        return None, None, f"File type not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}"

    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"

    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)

    filepath = os.path.join(upload_folder, unique_filename)
    file.save(filepath)

    return filepath, filename, None


def cleanup_file(filepath: str) -> None:
    """Remove temporary file."""
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        logger.warning(f"Failed to cleanup file {filepath}: {e}")


@ocr_bp.route('/ocr', methods=['POST'])
def process_ocr():
    """
    Process file with OCR and return full result.

    Request (multipart/form-data):
        - file (required): Image or PDF file
        - lang (optional): Language code ("en" or "ar", default: "en")
        - engine (optional): Engine name ("auto", "paddle", "tesseract", default: "auto")
        - structured (optional): Enable structured output ("true"/"false", default: "true")

    Response:
        {
            "success": true,
            "data": {
                "file_path": "...",
                "file_type": "image",
                "engine_used": "paddle",
                "language": "en",
                "processing_time_ms": 1234.56,
                "pages": [...],
                "full_text": "...",
                "structured_output": "..." (if structured=true and Arabic)
            }
        }
    """
    filepath = None
    try:
        # Validate file
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400

        file = request.files['file']
        filepath, filename, error = save_uploaded_file(file)

        if error:
            return jsonify({'success': False, 'error': error}), 400

        # Get parameters
        lang = request.form.get('lang', 'en')
        if lang not in ['en', 'ar']:
            lang = 'en'

        engine = request.form.get('engine', 'auto')
        structured = request.form.get('structured', 'true').lower() == 'true'

        # Get read tool from app context
        read_tool = current_app.config['READ_TOOL']

        # Process file
        result = read_tool.read(
            file_path=filepath,
            lang=lang,
            engine=engine,
            structured_output=structured
        )

        # Cleanup
        cleanup_file(filepath)

        if result.success:
            return jsonify({
                'success': True,
                'data': result.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'error': result.error or 'OCR processing failed'
            }), 500

    except Exception as e:
        cleanup_file(filepath)
        logger.exception("OCR processing error")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ocr_bp.route('/ocr/text', methods=['POST'])
def process_ocr_text_only():
    """
    Process file with OCR and return only extracted text.

    Request (multipart/form-data):
        - file (required): Image or PDF file
        - lang (optional): Language code ("en" or "ar", default: "en")
        - engine (optional): Engine name (default: "auto")

    Response:
        {
            "success": true,
            "text": "Extracted text content...",
            "language": "en",
            "engine_used": "paddle",
            "processing_time_ms": 1234.56
        }
    """
    filepath = None
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400

        file = request.files['file']
        filepath, filename, error = save_uploaded_file(file)

        if error:
            return jsonify({'success': False, 'error': error}), 400

        lang = request.form.get('lang', 'en')
        if lang not in ['en', 'ar']:
            lang = 'en'

        engine = request.form.get('engine', 'auto')

        read_tool = current_app.config['READ_TOOL']

        result = read_tool.read(
            file_path=filepath,
            lang=lang,
            engine=engine,
            structured_output=False
        )

        cleanup_file(filepath)

        if result.success:
            return jsonify({
                'success': True,
                'text': result.full_text,
                'language': lang,
                'engine_used': result.engine_used,
                'processing_time_ms': result.processing_time_ms
            })
        else:
            return jsonify({
                'success': False,
                'error': result.error or 'OCR processing failed'
            }), 500

    except Exception as e:
        cleanup_file(filepath)
        logger.exception("OCR text extraction error")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ocr_bp.route('/ocr/structured', methods=['POST'])
def process_ocr_structured():
    """
    Process file with OCR and return structured bilingual output.

    Best for Arabic documents - produces Claude Code-like markdown output.

    Request (multipart/form-data):
        - file (required): Image or PDF file
        - lang (optional): Language code (default: "ar" for this endpoint)
        - format (optional): Output format ("markdown", "json", "text", default: "markdown")

    Response:
        {
            "success": true,
            "structured_output": "# Tax Invoice (فاتورة ضريبية)\\n...",
            "document_type": "tax_invoice",
            "is_bilingual": true,
            "language": "ar",
            "processing_time_ms": 1234.56
        }
    """
    filepath = None
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400

        file = request.files['file']
        filepath, filename, error = save_uploaded_file(file)

        if error:
            return jsonify({'success': False, 'error': error}), 400

        # Default to Arabic for structured output
        lang = request.form.get('lang', 'ar')
        if lang not in ['en', 'ar']:
            lang = 'ar'

        output_format = request.form.get('format', 'markdown')
        if output_format not in ['markdown', 'json', 'text']:
            output_format = 'markdown'

        read_tool = current_app.config['READ_TOOL']

        result = read_tool.read(
            file_path=filepath,
            lang=lang,
            engine='auto',
            output_format=output_format,
            structured_output=True
        )

        cleanup_file(filepath)

        if result.success:
            response_data = {
                'success': True,
                'structured_output': result.structured_output or result.full_text,
                'raw_text': result.full_text,
                'document_type': result.metadata.get('document_type', 'generic'),
                'is_bilingual': result.metadata.get('is_bilingual', False),
                'language': result.metadata.get('detected_language', lang),
                'engine_used': result.engine_used,
                'processing_time_ms': result.processing_time_ms
            }
            return jsonify(response_data)
        else:
            return jsonify({
                'success': False,
                'error': result.error or 'OCR processing failed'
            }), 500

    except Exception as e:
        cleanup_file(filepath)
        logger.exception("Structured OCR error")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ocr_bp.route('/languages', methods=['GET'])
def get_languages():
    """
    Get list of supported languages.

    Response:
        {
            "success": true,
            "languages": [
                {"code": "en", "name": "English", "native_name": "English"},
                {"code": "ar", "name": "Arabic", "native_name": "العربية"}
            ]
        }
    """
    return jsonify({
        'success': True,
        'languages': [
            {
                'code': 'en',
                'name': 'English',
                'native_name': 'English',
                'direction': 'ltr'
            },
            {
                'code': 'ar',
                'name': 'Arabic',
                'native_name': 'العربية',
                'direction': 'rtl'
            }
        ]
    })
