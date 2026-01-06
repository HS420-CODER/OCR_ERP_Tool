"""
Flask Application Factory for Hybrid Read Tool API.

Creates and configures the Flask application with:
- Blueprint registration
- CORS configuration
- Error handlers
- HybridReadTool integration
"""

import os
import sys
import logging
from pathlib import Path
from flask import Flask, jsonify, send_from_directory

# Disable model source check for offline operation
os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'

# Add paths for imports
# IMPORTANT: project_root must come BEFORE src to avoid src/config.py shadowing config/
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

from flask_cors import CORS

logger = logging.getLogger(__name__)


def create_app(config_dict: dict = None) -> Flask:
    """
    Application factory for creating Flask app.

    Args:
        config_dict: Optional configuration dictionary

    Returns:
        Configured Flask application
    """
    # Create Flask app
    app = Flask(
        __name__,
        static_folder='../frontend/build',
        static_url_path=''
    )

    # Default configuration
    app.config.update(
        UPLOAD_FOLDER=os.path.join(os.path.dirname(__file__), '..', 'uploads'),
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,  # 50MB max file size
        JSON_SORT_KEYS=False,
        JSON_AS_ASCII=False,  # Allow Unicode in JSON responses
    )

    # Override with custom config if provided
    if config_dict:
        app.config.update(config_dict)

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Enable CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # Initialize HybridReadTool
    _init_read_tool(app)

    # Initialize security middleware for v2 API
    _init_security(app)

    # Register blueprints
    _register_blueprints(app)

    # Register error handlers
    _register_error_handlers(app)

    # Register static file routes
    _register_static_routes(app)

    return app


def _init_read_tool(app: Flask) -> None:
    """Initialize HybridReadTool and store in app config."""
    try:
        from src.read_tool import HybridReadTool
        from src.config import ReadToolConfig

        config = ReadToolConfig()
        read_tool = HybridReadTool(config)

        app.config['READ_TOOL'] = read_tool
        logger.info("HybridReadTool initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize HybridReadTool: {e}")
        raise


def _init_security(app: Flask) -> None:
    """Initialize security middleware for v2 API."""
    try:
        from src.middleware.security import init_security
        init_security(app)
        logger.info("Security middleware initialized for v2 API")

    except Exception as e:
        logger.warning(f"Security middleware initialization failed: {e}")
        logger.warning("v2 API will run without authentication")


def _register_blueprints(app: Flask) -> None:
    """Register all API blueprints."""
    from .routes.ocr_routes import ocr_bp
    from .routes.vision_routes import vision_bp
    from .routes.engines_routes import engines_bp
    from .routes.config_routes import config_bp
    from .routes.ocr_v2 import ocr_v2_bp

    # v1 API routes
    app.register_blueprint(ocr_bp)
    app.register_blueprint(vision_bp)
    app.register_blueprint(engines_bp)
    app.register_blueprint(config_bp)

    # v2 API routes (ERP Arabic OCR Microservice)
    app.register_blueprint(ocr_v2_bp)

    logger.info("Registered API blueprints: ocr, vision, engines, config, ocr_v2")


def _register_error_handlers(app: Flask) -> None:
    """Register global error handlers."""

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': str(error.description) if hasattr(error, 'description') else str(error)
        }), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'The requested resource was not found'
        }), 404

    @app.errorhandler(413)
    def file_too_large(error):
        return jsonify({
            'success': False,
            'error': 'File too large',
            'message': 'The uploaded file exceeds the maximum allowed size (50MB)'
        }), 413

    @app.errorhandler(500)
    def internal_error(error):
        logger.exception("Internal server error")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500


def _register_static_routes(app: Flask) -> None:
    """Register routes for serving static files (React frontend)."""

    @app.route('/')
    def serve_index():
        """Serve React app index."""
        static_folder = app.static_folder
        if static_folder and os.path.exists(os.path.join(static_folder, 'index.html')):
            return send_from_directory(static_folder, 'index.html')
        return jsonify({
            'success': True,
            'message': 'Hybrid Read Tool API',
            'version': '1.0.0',
            'endpoints': {
                'health': '/api/health',
                'ocr': '/api/ocr',
                'engines': '/api/engines',
                'config': '/api/config',
                'languages': '/api/languages'
            }
        })

    @app.route('/<path:path>')
    def serve_static(path):
        """Serve static files or fallback to index.html for SPA routing."""
        static_folder = app.static_folder
        if static_folder:
            file_path = os.path.join(static_folder, path)
            if os.path.exists(file_path):
                return send_from_directory(static_folder, path)
            # SPA fallback
            if os.path.exists(os.path.join(static_folder, 'index.html')):
                return send_from_directory(static_folder, 'index.html')

        return jsonify({
            'success': False,
            'error': 'Not found'
        }), 404


def run_server(host: str = '0.0.0.0', port: int = 5000, debug: bool = True):
    """
    Run the Flask development server.

    Args:
        host: Host to bind to
        port: Port to listen on
        debug: Enable debug mode
    """
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    app = create_app()

    print("=" * 60)
    print("Hybrid Read Tool API Server")
    print("=" * 60)
    print()
    print("v1 API Endpoints:")
    print("  GET  /api/health            - Health check")
    print("  GET  /api/config            - Get configuration")
    print("  PUT  /api/config            - Update configuration")
    print("  GET  /api/engines           - List OCR engines")
    print("  GET  /api/engines/<name>    - Get engine details")
    print("  GET  /api/languages         - List supported languages")
    print("  POST /api/ocr               - Process file with OCR")
    print("  POST /api/ocr/text          - Extract text only")
    print("  POST /api/ocr/structured    - Get structured output")
    print("  POST /api/ocr/batch         - Batch process multiple files")
    print("  POST /api/vision/analyze    - Vision analysis (Ollama)")
    print("  POST /api/vision/prompt     - Custom prompt analysis")
    print("  GET  /api/vision/models     - List vision models")
    print("  GET  /api/vision/status     - Vision server status")
    print()
    print("v2 API Endpoints (ERP Arabic OCR Microservice):")
    print("  POST /api/v2/ocr/invoice    - Process invoice (structured)")
    print("  POST /api/v2/ocr/document   - Process document (general)")
    print("  POST /api/v2/ocr/batch      - Batch processing")
    print("  GET  /api/v2/ocr/health     - Health check")
    print("  GET  /api/v2/ocr/metrics    - Prometheus metrics")
    print()
    print(f"Starting server on http://{host}:{port}")
    print("=" * 60)

    # Disable reloader to prevent conflicts with PaddlePaddle multiprocessing
    app.run(host=host, port=port, debug=debug, use_reloader=False)


# Allow running directly
if __name__ == '__main__':
    run_server()
