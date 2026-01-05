"""
Engine Management Routes.

Endpoints:
- GET /api/engines - List all available engines
- GET /api/engines/<name> - Get engine details
- POST /api/engines/<name>/test - Test engine availability
"""

import logging
from flask import Blueprint, jsonify, current_app

logger = logging.getLogger(__name__)

engines_bp = Blueprint('engines', __name__, url_prefix='/api/engines')


@engines_bp.route('', methods=['GET'])
def list_engines():
    """
    List all registered OCR/Vision engines.

    Response:
        {
            "success": true,
            "engines": [
                {
                    "name": "paddle",
                    "display_name": "PaddleOCR",
                    "available": true,
                    "capabilities": {...}
                },
                ...
            ],
            "default_engine": "paddle"
        }
    """
    try:
        read_tool = current_app.config['READ_TOOL']
        engines_info = read_tool.get_available_engines()

        return jsonify({
            'success': True,
            'engines': engines_info['engines'],
            'default_engine': engines_info['default_engine']
        })

    except Exception as e:
        logger.exception("Error listing engines")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@engines_bp.route('/<name>', methods=['GET'])
def get_engine_details(name: str):
    """
    Get detailed information about a specific engine.

    Path Parameters:
        - name: Engine identifier (paddle, tesseract, ollama)

    Response:
        {
            "success": true,
            "engine": {
                "name": "paddle",
                "display_name": "PaddleOCR",
                "available": true,
                "capabilities": {
                    "supports_images": true,
                    "supports_pdf": true,
                    "supports_vision_analysis": false,
                    "supports_gpu": true,
                    "supported_languages": ["en", "ar"],
                    "max_file_size_mb": 50,
                    "supports_tables": true,
                    "supports_structure": true
                }
            }
        }
    """
    try:
        read_tool = current_app.config['READ_TOOL']
        engine_manager = read_tool.engine_manager

        # Check if engine is registered
        if name not in engine_manager._engine_classes:
            return jsonify({
                'success': False,
                'error': f"Engine '{name}' not found"
            }), 404

        engine_info = engine_manager.get_engine_info(name)

        return jsonify({
            'success': True,
            'engine': engine_info
        })

    except Exception as e:
        logger.exception(f"Error getting engine details: {name}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@engines_bp.route('/<name>/test', methods=['POST'])
def test_engine(name: str):
    """
    Test if an engine is available and working.

    Path Parameters:
        - name: Engine identifier

    Response:
        {
            "success": true,
            "engine": "paddle",
            "available": true,
            "message": "Engine is ready"
        }
    """
    try:
        read_tool = current_app.config['READ_TOOL']
        engine_manager = read_tool.engine_manager

        # Clear cache to get fresh availability status
        engine_manager.clear_availability_cache()

        available = engine_manager.is_available(name)

        if available:
            return jsonify({
                'success': True,
                'engine': name,
                'available': True,
                'message': f"Engine '{name}' is ready"
            })
        else:
            return jsonify({
                'success': True,
                'engine': name,
                'available': False,
                'message': f"Engine '{name}' is not available or not installed"
            })

    except Exception as e:
        logger.exception(f"Error testing engine: {name}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@engines_bp.route('/available', methods=['GET'])
def list_available_engines():
    """
    List only available (ready to use) engines.

    Response:
        {
            "success": true,
            "available_engines": ["paddle", "tesseract"]
        }
    """
    try:
        read_tool = current_app.config['READ_TOOL']
        engine_manager = read_tool.engine_manager

        available = engine_manager.get_available_engines()

        return jsonify({
            'success': True,
            'available_engines': available
        })

    except Exception as e:
        logger.exception("Error listing available engines")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
