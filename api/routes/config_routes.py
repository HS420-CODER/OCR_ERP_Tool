"""
Configuration Routes.

Endpoints:
- GET /api/config - Get current configuration
- PUT /api/config - Update configuration
- GET /api/health - Health check
"""

import logging
from flask import Blueprint, jsonify, request, current_app

logger = logging.getLogger(__name__)

config_bp = Blueprint('config', __name__, url_prefix='/api')


@config_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.

    Response:
        {
            "success": true,
            "status": "ok",
            "message": "Hybrid Read Tool API is running",
            "version": "1.0.0",
            "supported_languages": ["en", "ar"],
            "supported_formats": ["png", "jpg", ...],
            "available_engines": ["paddle", "tesseract"]
        }
    """
    try:
        read_tool = current_app.config['READ_TOOL']
        engine_manager = read_tool.engine_manager
        available_engines = engine_manager.get_available_engines()

        return jsonify({
            'success': True,
            'status': 'ok',
            'message': 'Hybrid Read Tool API is running',
            'version': '1.0.0',
            'supported_languages': ['en', 'ar'],
            'supported_formats': [
                'png', 'jpg', 'jpeg', 'gif', 'bmp',
                'tiff', 'tif', 'webp', 'pdf'
            ],
            'available_engines': available_engines
        })

    except Exception as e:
        logger.exception("Health check error")
        return jsonify({
            'success': False,
            'status': 'error',
            'message': str(e)
        }), 500


@config_bp.route('/config', methods=['GET'])
def get_config():
    """
    Get current configuration settings.

    Response:
        {
            "success": true,
            "config": {
                "default_engine": "auto",
                "default_language": "en",
                "fallback_enabled": true,
                "fallback_order": ["paddle", "tesseract", "ollama"],
                "max_file_size_mb": 50,
                "structured_output_enabled": true
            }
        }
    """
    try:
        read_tool = current_app.config['READ_TOOL']
        config = read_tool.config

        return jsonify({
            'success': True,
            'config': {
                'default_engine': config.default_engine,
                'default_language': config.paddle_lang,  # Use paddle_lang as default
                'fallback_enabled': config.fallback_enabled,
                'fallback_order': config.fallback_order,
                'max_file_size_mb': config.max_file_size_mb,
                'structured_output_enabled': config.structured_output,
                'supported_languages': ['en', 'ar']
            }
        })

    except Exception as e:
        logger.exception("Error getting config")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@config_bp.route('/config', methods=['PUT'])
def update_config():
    """
    Update configuration settings.

    Request Body (JSON):
        {
            "default_engine": "paddle",
            "default_language": "ar",
            "fallback_enabled": true
        }

    Response:
        {
            "success": true,
            "message": "Configuration updated",
            "config": {...}
        }
    """
    try:
        data = request.get_json() or {}
        read_tool = current_app.config['READ_TOOL']
        config = read_tool.config

        # Update allowed fields
        updated_fields = []

        if 'default_engine' in data:
            valid_engines = ['auto', 'paddle', 'tesseract', 'ollama']
            if data['default_engine'] in valid_engines:
                config.default_engine = data['default_engine']
                updated_fields.append('default_engine')

        if 'default_language' in data:
            valid_languages = ['en', 'ar']
            if data['default_language'] in valid_languages:
                config.paddle_lang = data['default_language']
                updated_fields.append('default_language')

        if 'fallback_enabled' in data:
            config.fallback_enabled = bool(data['fallback_enabled'])
            updated_fields.append('fallback_enabled')

        if 'fallback_order' in data:
            if isinstance(data['fallback_order'], list):
                config.fallback_order = data['fallback_order']
                updated_fields.append('fallback_order')

        return jsonify({
            'success': True,
            'message': f"Configuration updated: {', '.join(updated_fields)}" if updated_fields else "No changes made",
            'updated_fields': updated_fields,
            'config': {
                'default_engine': config.default_engine,
                'default_language': config.paddle_lang,
                'fallback_enabled': config.fallback_enabled,
                'fallback_order': config.fallback_order,
                'max_file_size_mb': config.max_file_size_mb
            }
        })

    except Exception as e:
        logger.exception("Error updating config")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@config_bp.route('/version', methods=['GET'])
def get_version():
    """
    Get API version information.

    Response:
        {
            "success": true,
            "version": "1.0.0",
            "name": "Hybrid Read Tool API",
            "description": "OCR API with PaddleOCR and Tesseract support"
        }
    """
    return jsonify({
        'success': True,
        'version': '1.0.0',
        'name': 'Hybrid Read Tool API',
        'description': 'OCR API with PaddleOCR and Tesseract support for English and Arabic documents'
    })
