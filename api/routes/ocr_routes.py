"""
OCR Processing Routes.

Endpoints:
- POST /api/ocr - Process file with OCR (full result)
- POST /api/ocr/text - Extract text only
- POST /api/ocr/structured - Get structured bilingual output
- POST /api/ocr/batch - Process multiple files in one request
- GET /api/languages - Get supported languages
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
            # Convert to dict
            response_data = result.to_dict()

            # Ensure fields and sections are populated for structured output
            # This handles cases where the read_tool module might be cached
            if structured and lang == 'ar' and 'fields' not in response_data.get('metadata', {}):
                try:
                    from src.formatters import DocumentAnalyzer
                    from src.formatters.field_dictionary import get_english

                    analyzer = DocumentAnalyzer()
                    structure = analyzer.analyze(result)

                    # Add fields
                    if structure.key_value_pairs:
                        fields = {}
                        for ar_key, value in structure.key_value_pairs.items():
                            en_key = get_english(ar_key)
                            fields[ar_key] = {
                                "english_key": en_key if en_key != ar_key else "",
                                "value": value
                            }
                        response_data['metadata']['fields'] = fields

                    # Add sections
                    if structure.regions:
                        sections = []
                        for region in structure.regions:
                            if region.text:
                                is_rtl = any('\u0600' <= c <= '\u06FF' for c in region.text[:50])
                                sections.append({
                                    "name": region.region_type.value.replace('_', ' ').title(),
                                    "content": region.text,
                                    "is_rtl": is_rtl
                                })
                        if sections:
                            response_data['metadata']['sections'] = sections
                except Exception as e:
                    logger.warning(f"Failed to add fields/sections: {e}")

            return jsonify({
                'success': True,
                'data': response_data
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


@ocr_bp.route('/ocr/batch', methods=['POST'])
def process_ocr_batch():
    """
    Process multiple files with OCR in a single request.

    Request (multipart/form-data):
        - files (required): Multiple image or PDF files
        - lang (optional): Language code ("en" or "ar", default: "en")
        - engine (optional): Engine name (default: "auto")
        - structured (optional): Enable structured output ("true"/"false", default: "false")

    Response:
        {
            "success": true,
            "total_files": 3,
            "processed": 3,
            "failed": 0,
            "results": [
                {
                    "filename": "doc1.png",
                    "success": true,
                    "text": "...",
                    "engine_used": "paddle",
                    "processing_time_ms": 1234.56
                },
                ...
            ],
            "total_processing_time_ms": 5678.90
        }
    """
    import time
    start_time = time.perf_counter()

    filepaths = []
    results = []

    try:
        # Check for files
        if 'files' not in request.files and 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No files provided. Use "files" field for multiple files.'
            }), 400

        # Get files - support both 'files' (multiple) and 'file' (single/multiple)
        files = request.files.getlist('files') or request.files.getlist('file')

        if not files or len(files) == 0:
            return jsonify({
                'success': False,
                'error': 'No files provided'
            }), 400

        # Get parameters
        lang = request.form.get('lang', 'en')
        if lang not in ['en', 'ar']:
            lang = 'en'

        engine = request.form.get('engine', 'auto')
        structured = request.form.get('structured', 'false').lower() == 'true'

        read_tool = current_app.config['READ_TOOL']

        processed_count = 0
        failed_count = 0

        for file in files:
            file_result = {
                'filename': file.filename,
                'success': False,
                'text': None,
                'error': None,
                'engine_used': None,
                'processing_time_ms': 0
            }

            try:
                filepath, filename, error = save_uploaded_file(file)

                if error:
                    file_result['error'] = error
                    failed_count += 1
                    results.append(file_result)
                    continue

                filepaths.append(filepath)

                result = read_tool.read(
                    file_path=filepath,
                    lang=lang,
                    engine=engine,
                    structured_output=structured
                )

                if result.success:
                    file_result['success'] = True
                    file_result['text'] = result.full_text
                    file_result['engine_used'] = result.engine_used
                    file_result['processing_time_ms'] = result.processing_time_ms
                    if structured and result.structured_output:
                        file_result['structured_output'] = result.structured_output
                    processed_count += 1
                else:
                    file_result['error'] = result.error or 'OCR processing failed'
                    failed_count += 1

            except Exception as e:
                file_result['error'] = str(e)
                failed_count += 1
                logger.exception(f"Error processing file {file.filename}")

            results.append(file_result)

        # Cleanup all files
        for filepath in filepaths:
            cleanup_file(filepath)

        total_time = (time.perf_counter() - start_time) * 1000

        return jsonify({
            'success': True,
            'total_files': len(files),
            'processed': processed_count,
            'failed': failed_count,
            'results': results,
            'total_processing_time_ms': round(total_time, 2)
        })

    except Exception as e:
        # Cleanup on error
        for filepath in filepaths:
            cleanup_file(filepath)
        logger.exception("Batch OCR processing error")
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
