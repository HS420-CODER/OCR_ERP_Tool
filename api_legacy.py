"""
Flask API for PaddleOCR Tool
Provides REST endpoints for OCR processing
"""

import os
os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import tempfile
import uuid
from ocr_tool import ERPOCRTool

app = Flask(__name__, static_folder='frontend/build', static_url_path='')
CORS(app)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'pdf'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize OCR engines
ocr_engines = {}

def get_ocr_engine(lang='en'):
    """Get or create OCR engine for specified language."""
    if lang not in ocr_engines:
        print(f"Initializing OCR engine for language: {lang}")
        ocr_engines[lang] = ERPOCRTool(lang=lang)
    return ocr_engines[lang]

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def serve():
    """Serve React app."""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'message': 'OCR API is running',
        'supported_languages': ['en', 'ar'],
        'supported_formats': list(ALLOWED_EXTENSIONS)
    })

@app.route('/api/ocr', methods=['POST'])
def process_ocr():
    """
    Process OCR on uploaded file.

    Request:
        - file: The image or PDF file
        - lang: Language code ('en' or 'ar')

    Response:
        - success: boolean
        - data: OCR results
        - error: error message if failed
    """
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'File type not allowed. Supported: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400

        # Get language parameter
        lang = request.form.get('lang', 'en')
        if lang not in ['en', 'ar']:
            lang = 'en'

        # Save file temporarily
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(filepath)

        try:
            # Get OCR engine
            ocr = get_ocr_engine(lang)

            # Process based on file type
            ext = filename.rsplit('.', 1)[1].lower()

            if ext == 'pdf':
                result = ocr.process_pdf(filepath)
            else:
                result = ocr.process_image(filepath)

            # Clean up
            os.remove(filepath)

            return jsonify({
                'success': True,
                'data': result,
                'language': lang
            })

        except Exception as e:
            # Clean up on error
            if os.path.exists(filepath):
                os.remove(filepath)
            raise e

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/ocr/text', methods=['POST'])
def process_ocr_text_only():
    """
    Process OCR and return only the extracted text.

    Request:
        - file: The image or PDF file
        - lang: Language code ('en' or 'ar')

    Response:
        - success: boolean
        - text: Extracted text
        - error: error message if failed
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'File type not allowed. Supported: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400

        lang = request.form.get('lang', 'en')
        if lang not in ['en', 'ar']:
            lang = 'en'

        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(filepath)

        try:
            ocr = get_ocr_engine(lang)
            text = ocr.get_text_only(filepath)
            os.remove(filepath)

            return jsonify({
                'success': True,
                'text': text,
                'language': lang
            })

        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            raise e

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Serve React static files
@app.route('/<path:path>')
def serve_static(path):
    """Serve static files."""
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    print("="*60)
    print("PaddleOCR API Server")
    print("="*60)
    print("\nInitializing OCR engines...")

    # Pre-load English engine
    get_ocr_engine('en')
    print("English OCR engine ready!")

    print("\nAPI Endpoints:")
    print("  GET  /api/health     - Health check")
    print("  POST /api/ocr        - Full OCR with bounding boxes")
    print("  POST /api/ocr/text   - Text-only OCR")
    print("\nStarting server on http://localhost:5000")
    print("="*60)

    app.run(host='0.0.0.0', port=5000, debug=True)
