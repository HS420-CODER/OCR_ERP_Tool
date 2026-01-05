"""
Vision Analysis Routes.

Endpoints for context-aware document analysis using Ollama Vision models.

Endpoints:
- POST /api/vision/analyze - Analyze document with vision model
- POST /api/vision/prompt - Custom prompt-based analysis
- GET /api/vision/models - Get available vision models
- GET /api/vision/status - Check Ollama server status
"""

import os
import uuid
import logging
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

vision_bp = Blueprint('vision', __name__, url_prefix='/api/vision')

# Allowed file extensions for vision analysis
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'tif', 'webp', 'pdf'}


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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


@vision_bp.route('/analyze', methods=['POST'])
def analyze_document():
    """
    Analyze document using vision model (Ollama LLaVA).

    Performs context-aware analysis of images and PDFs,
    extracting text with understanding of document structure.

    Request (multipart/form-data):
        - file (required): Image or PDF file
        - lang (optional): Language hint ("en" or "ar", default: "en")
        - model (optional): Ollama vision model (default: "llava")

    Response:
        {
            "success": true,
            "analysis": "This is a tax invoice from Skysoft Co...",
            "model_used": "llava",
            "processing_time_ms": 2345.67,
            "metadata": {
                "file_type": "image",
                "language_hint": "en"
            }
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

        # Get parameters
        lang = request.form.get('lang', 'en')
        if lang not in ['en', 'ar']:
            lang = 'en'

        model = request.form.get('model', 'llava')

        # Get engine manager and check for Ollama
        read_tool = current_app.config['READ_TOOL']

        try:
            ollama_engine = read_tool.engine_manager.get_engine('ollama')
        except Exception:
            cleanup_file(filepath)
            return jsonify({
                'success': False,
                'error': 'Ollama vision engine not available. Ensure Ollama is running.'
            }), 503

        if not ollama_engine.is_available():
            cleanup_file(filepath)
            return jsonify({
                'success': False,
                'error': 'Ollama server is not running. Start Ollama and try again.'
            }), 503

        # Default analysis prompt based on language
        if lang == 'ar':
            default_prompt = (
                "Analyze this document. Extract all text, identify the document type "
                "(invoice, receipt, form, etc.), and describe its structure. "
                "This document may contain Arabic text - preserve all Arabic characters exactly. "
                "Provide a structured summary."
            )
        else:
            default_prompt = (
                "Analyze this document. Extract all visible text, identify the document type "
                "(invoice, receipt, form, letter, etc.), and describe its structure. "
                "Provide a structured summary with key information."
            )

        # Process with vision model
        result = ollama_engine.process_with_prompt(filepath, default_prompt)

        cleanup_file(filepath)

        if result.success:
            return jsonify({
                'success': True,
                'analysis': result.full_text,
                'model_used': model,
                'processing_time_ms': result.processing_time_ms,
                'metadata': {
                    'file_type': result.file_type,
                    'language_hint': lang,
                    'engine': 'ollama'
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': result.error or 'Vision analysis failed'
            }), 500

    except Exception as e:
        cleanup_file(filepath)
        logger.exception("Vision analysis error")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@vision_bp.route('/prompt', methods=['POST'])
def custom_prompt_analysis():
    """
    Analyze document with a custom prompt.

    Allows users to ask specific questions about the document
    or request targeted information extraction.

    Request (multipart/form-data):
        - file (required): Image or PDF file
        - prompt (required): Custom analysis prompt/question
        - model (optional): Ollama vision model (default: "llava")

    Response:
        {
            "success": true,
            "prompt": "What is the total amount on this invoice?",
            "response": "The total amount on this invoice is SAR 2,300.00...",
            "model_used": "llava",
            "processing_time_ms": 1234.56
        }

    Example prompts:
        - "What is the total amount on this invoice?"
        - "List all items in this receipt"
        - "Extract the customer name and address"
        - "Is this document in Arabic or English?"
        - "Summarize the key information in this document"
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

        # Get prompt - required
        prompt = request.form.get('prompt')
        if not prompt or not prompt.strip():
            cleanup_file(filepath)
            return jsonify({
                'success': False,
                'error': 'Prompt is required. Provide a question or instruction about the document.'
            }), 400

        model = request.form.get('model', 'llava')

        # Get Ollama engine
        read_tool = current_app.config['READ_TOOL']

        try:
            ollama_engine = read_tool.engine_manager.get_engine('ollama')
        except Exception:
            cleanup_file(filepath)
            return jsonify({
                'success': False,
                'error': 'Ollama vision engine not available. Ensure Ollama is running.'
            }), 503

        if not ollama_engine.is_available():
            cleanup_file(filepath)
            return jsonify({
                'success': False,
                'error': 'Ollama server is not running. Start Ollama and try again.'
            }), 503

        # Process with custom prompt
        result = ollama_engine.process_with_prompt(filepath, prompt.strip())

        cleanup_file(filepath)

        if result.success:
            return jsonify({
                'success': True,
                'prompt': prompt.strip(),
                'response': result.full_text,
                'model_used': model,
                'processing_time_ms': result.processing_time_ms
            })
        else:
            return jsonify({
                'success': False,
                'error': result.error or 'Custom prompt analysis failed'
            }), 500

    except Exception as e:
        cleanup_file(filepath)
        logger.exception("Custom prompt analysis error")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@vision_bp.route('/models', methods=['GET'])
def get_vision_models():
    """
    Get available vision models from Ollama.

    Response:
        {
            "success": true,
            "models": [
                {"name": "llava", "description": "LLaVA vision model"},
                {"name": "llava:13b", "description": "LLaVA 13B variant"}
            ],
            "default_model": "llava"
        }
    """
    try:
        read_tool = current_app.config['READ_TOOL']

        try:
            ollama_engine = read_tool.engine_manager.get_engine('ollama')
        except Exception:
            return jsonify({
                'success': False,
                'error': 'Ollama engine not available'
            }), 503

        # Default supported models
        models = [
            {'name': 'llava', 'description': 'LLaVA - Large Language and Vision Assistant'},
            {'name': 'llava:7b', 'description': 'LLaVA 7B - Lighter, faster variant'},
            {'name': 'llava:13b', 'description': 'LLaVA 13B - More capable variant'},
            {'name': 'bakllava', 'description': 'BakLLaVA - Alternative vision model'},
        ]

        return jsonify({
            'success': True,
            'models': models,
            'default_model': 'llava',
            'server_available': ollama_engine.is_available()
        })

    except Exception as e:
        logger.exception("Error getting vision models")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@vision_bp.route('/status', methods=['GET'])
def get_vision_status():
    """
    Check Ollama vision server status.

    Response:
        {
            "success": true,
            "ollama_available": true,
            "server_url": "http://localhost:11434",
            "message": "Ollama server is running and ready"
        }
    """
    try:
        read_tool = current_app.config['READ_TOOL']

        try:
            ollama_engine = read_tool.engine_manager.get_engine('ollama')
            is_available = ollama_engine.is_available()

            return jsonify({
                'success': True,
                'ollama_available': is_available,
                'server_url': ollama_engine._host if hasattr(ollama_engine, '_host') else 'http://localhost:11434',
                'message': 'Ollama server is running and ready' if is_available else 'Ollama server is not responding'
            })
        except Exception as e:
            return jsonify({
                'success': True,
                'ollama_available': False,
                'server_url': 'http://localhost:11434',
                'message': f'Ollama engine not configured: {str(e)}'
            })

    except Exception as e:
        logger.exception("Error checking vision status")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
