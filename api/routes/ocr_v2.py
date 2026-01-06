"""
ERP Arabic OCR Microservice - v2 API Routes
============================================
REST API endpoints for multi-engine Arabic OCR processing.
"""

import os
import time
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Blueprint, request, jsonify, current_app, g, Response
from werkzeug.utils import secure_filename

# Import metrics
from src.utils.metrics import (
    get_metrics as get_prometheus_metrics,
    get_metrics_registry,
    record_document_processed,
    set_engine_availability
)

logger = logging.getLogger(__name__)

# Create blueprint
ocr_v2_bp = Blueprint('ocr_v2', __name__, url_prefix='/api/v2/ocr')

# Service start time for uptime calculation
SERVICE_START_TIME = datetime.utcnow()

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'tiff', 'tif', 'bmp'}

# Maximum file sizes
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
MAX_BATCH_SIZE = 10


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_request_id() -> str:
    """Get or generate request ID."""
    return getattr(g, 'request_id', None) or str(uuid.uuid4())[:8]


def save_uploaded_file(file) -> Path:
    """Save uploaded file to temp directory."""
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)

    filename = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
    filepath = Path(upload_folder) / unique_name
    file.save(filepath)

    return filepath


def cleanup_file(filepath: Path) -> None:
    """Remove temporary file."""
    try:
        if filepath and filepath.exists():
            filepath.unlink()
    except Exception as e:
        logger.warning(f"Failed to cleanup file {filepath}: {e}")


def get_ocr_service():
    """Get or initialize OCR service."""
    if 'ocr_service' not in current_app.config:
        from src.services.ocr_microservice import MultiEngineArabicOCR
        current_app.config['ocr_service'] = MultiEngineArabicOCR()
    return current_app.config['ocr_service']


def get_invoice_extractor():
    """Get or initialize invoice extractor."""
    if 'invoice_extractor' not in current_app.config:
        from src.services.invoice_extractor import InvoiceFieldExtractor
        current_app.config['invoice_extractor'] = InvoiceFieldExtractor()
    return current_app.config['invoice_extractor']


def get_output_formatter():
    """Get or initialize output formatter."""
    if 'output_formatter' not in current_app.config:
        from src.services.output_formatter import OutputFormatter
        current_app.config['output_formatter'] = OutputFormatter()
    return current_app.config['output_formatter']


def get_llm_service():
    """Get or initialize LLM correction service."""
    if 'llm_service' not in current_app.config:
        from src.services.llm_correction import LLMCorrectionService
        current_app.config['llm_service'] = LLMCorrectionService()
    return current_app.config['llm_service']


def get_file_validator():
    """Get or initialize file security validator."""
    if 'file_validator' not in current_app.config:
        from src.middleware.file_security import FileSecurityValidator
        current_app.config['file_validator'] = FileSecurityValidator()
    return current_app.config['file_validator']


def validate_uploaded_file(file):
    """
    Validate an uploaded file using the security validator.

    Args:
        file: Werkzeug FileStorage object

    Returns:
        Tuple of (is_valid, validation_result_or_error_response)
    """
    validator = get_file_validator()

    # Validate file
    result = validator.validate(file.stream, file.filename)
    file.stream.seek(0)  # Reset stream position

    if not result.valid:
        return False, error_response(
            "FILE_VALIDATION_FAILED",
            "; ".join(result.errors),
            400,
            {"validation_errors": result.errors}
        )

    return True, result


# ============================================================================
# Request hooks
# ============================================================================

@ocr_v2_bp.before_request
def before_request():
    """Set up request context."""
    g.request_id = str(uuid.uuid4())[:8]
    g.start_time = time.time()
    logger.info(f"[{g.request_id}] {request.method} {request.path}")


@ocr_v2_bp.after_request
def after_request(response):
    """Log request completion."""
    start_time = getattr(g, 'start_time', None)
    request_id = getattr(g, 'request_id', 'unknown')

    if start_time is not None:
        duration = (time.time() - start_time) * 1000
        logger.info(f"[{request_id}] Completed in {duration:.0f}ms - Status {response.status_code}")
        response.headers['X-Processing-Time-Ms'] = str(int(duration))
    else:
        duration = 0

    response.headers['X-Request-ID'] = request_id
    return response


# ============================================================================
# Error responses
# ============================================================================

def error_response(code: str, message: str, status_code: int = 400, details: dict = None):
    """Generate standardized error response."""
    response = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "request_id": get_request_id()
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    if details:
        response["error"]["details"] = details
    return jsonify(response), status_code


# ============================================================================
# POST /api/v2/ocr/invoice - Invoice Processing
# ============================================================================

@ocr_v2_bp.route('/invoice', methods=['POST'])
def process_invoice():
    """
    Process invoice image and extract structured data.

    Request:
        - file: Invoice image (multipart/form-data)
        - engine_mode: OCR engine mode (optional)
        - enable_llm: Enable LLM correction (optional)
        - extract_fields: Extract invoice fields (optional)

    Response:
        - Structured invoice data with extracted fields
    """
    request_id = get_request_id()
    start_time = time.time()
    filepath = None

    try:
        # Check file presence
        if 'file' not in request.files:
            return error_response(
                "MISSING_FILE",
                "No file provided in request",
                400
            )

        file = request.files['file']

        if file.filename == '':
            return error_response(
                "EMPTY_FILENAME",
                "No file selected",
                400
            )

        # Comprehensive file validation (extension, MIME type, size, content)
        is_valid, validation_result = validate_uploaded_file(file)
        if not is_valid:
            return validation_result  # Returns error response

        file_size = validation_result.file_size

        # Parse options
        engine_mode = request.form.get('engine_mode', 'fusion')
        enable_llm = request.form.get('enable_llm', 'true').lower() == 'true'
        extract_fields = request.form.get('extract_fields', 'true').lower() == 'true'

        # Save file
        filepath = save_uploaded_file(file)

        # Get services
        ocr_service = get_ocr_service()
        extractor = get_invoice_extractor()
        formatter = get_output_formatter()

        # Process with OCR
        ocr_result = ocr_service.process_image(
            str(filepath),
            apply_correction=True,
            extract_blocks=True
        )

        # Apply LLM correction if enabled
        correction_result = None
        if enable_llm:
            llm_service = get_llm_service()
            if llm_service.is_available():
                correction_result = llm_service.correct(ocr_result.text, language="ar")
                if correction_result.was_modified:
                    final_text = correction_result.corrected
                else:
                    final_text = ocr_result.text
            else:
                final_text = ocr_result.text
        else:
            final_text = ocr_result.text

        # Extract invoice fields
        invoice_data = None
        if extract_fields:
            invoice_data = extractor.extract_fields(final_text, ocr_result.blocks)

        # Build processing result
        from src.services import ProcessingResult, DocumentType

        result = ProcessingResult(
            text=final_text,
            confidence=ocr_result.confidence,
            ocr_result=ocr_result,
            correction_result=correction_result,
            invoice_data=invoice_data,
            document_type=DocumentType.INVOICE,
            request_id=request_id,
            processing_time_ms=(time.time() - start_time) * 1000,
            filename=file.filename,
            file_size_bytes=file_size
        )

        # Format response
        response = formatter.format_invoice_response(result)

        # Record metrics
        record_document_processed(
            engine=ocr_result.engine if hasattr(ocr_result, 'engine') else "fusion",
            document_type="invoice",
            confidence=result.confidence,
            text_length=len(result.text) if result.text else 0,
            size_bytes=file_size
        )

        return jsonify(response), 200

    except Exception as e:
        logger.exception(f"[{request_id}] Invoice processing failed")
        return error_response(
            "OCR_FAILED",
            f"OCR processing failed: {str(e)}",
            500
        )

    finally:
        if filepath:
            cleanup_file(filepath)


# ============================================================================
# POST /api/v2/ocr/document - General Document Processing
# ============================================================================

@ocr_v2_bp.route('/document', methods=['POST'])
def process_document():
    """
    Process general document (image or PDF).

    Request:
        - file: Document file (multipart/form-data)
        - engine_mode: OCR engine mode (optional)

    Response:
        - Extracted text with metadata
    """
    request_id = get_request_id()
    start_time = time.time()
    filepath = None

    try:
        if 'file' not in request.files:
            return error_response("MISSING_FILE", "No file provided", 400)

        file = request.files['file']

        if file.filename == '':
            return error_response("EMPTY_FILENAME", "No file selected", 400)

        # Comprehensive file validation
        is_valid, validation_result = validate_uploaded_file(file)
        if not is_valid:
            return validation_result

        # Save file
        filepath = save_uploaded_file(file)

        # Check if PDF
        is_pdf = file.filename.lower().endswith('.pdf')

        # Get services
        ocr_service = get_ocr_service()
        formatter = get_output_formatter()

        if is_pdf:
            # Process PDF pages
            from pdf2image import convert_from_path

            try:
                pages = convert_from_path(str(filepath), dpi=200)
            except Exception as e:
                return error_response(
                    "PDF_CONVERSION_FAILED",
                    f"Failed to convert PDF: {str(e)}",
                    400
                )

            all_text = []
            total_confidence = 0.0

            for i, page_image in enumerate(pages):
                import numpy as np
                page_array = np.array(page_image)
                result = ocr_service.process_image(page_array)
                all_text.append(f"--- Page {i+1} ---\n{result.text}")
                total_confidence += result.confidence

            combined_text = "\n\n".join(all_text)
            avg_confidence = total_confidence / len(pages) if pages else 0.0

            from src.services import ProcessingResult, DocumentType

            result = ProcessingResult(
                text=combined_text,
                confidence=avg_confidence,
                document_type=DocumentType.GENERAL,
                request_id=request_id,
                processing_time_ms=(time.time() - start_time) * 1000,
                filename=file.filename
            )

        else:
            # Process image
            ocr_result = ocr_service.process_image(str(filepath))

            from src.services import ProcessingResult, DocumentType

            result = ProcessingResult(
                text=ocr_result.text,
                confidence=ocr_result.confidence,
                ocr_result=ocr_result,
                document_type=DocumentType.GENERAL,
                request_id=request_id,
                processing_time_ms=(time.time() - start_time) * 1000,
                filename=file.filename
            )

        response = formatter.format_document_response(result)

        # Record metrics
        record_document_processed(
            engine="fusion",
            document_type="document",
            confidence=result.confidence,
            text_length=len(result.text) if result.text else 0,
            size_bytes=validation_result.file_size if hasattr(validation_result, 'file_size') else 0
        )

        return jsonify(response), 200

    except Exception as e:
        logger.exception(f"[{request_id}] Document processing failed")
        return error_response("OCR_FAILED", f"Processing failed: {str(e)}", 500)

    finally:
        if filepath:
            cleanup_file(filepath)


# ============================================================================
# POST /api/v2/ocr/batch - Batch Processing
# ============================================================================

@ocr_v2_bp.route('/batch', methods=['POST'])
def process_batch():
    """
    Process multiple files in batch.

    Request:
        - files: Multiple files (multipart/form-data)

    Response:
        - Aggregated results for all files
    """
    request_id = get_request_id()
    start_time = time.time()
    filepaths = []

    try:
        if 'files' not in request.files:
            return error_response("MISSING_FILES", "No files provided", 400)

        files = request.files.getlist('files')

        if len(files) == 0:
            return error_response("EMPTY_FILES", "No files selected", 400)

        if len(files) > MAX_BATCH_SIZE:
            return error_response(
                "BATCH_TOO_LARGE",
                f"Maximum {MAX_BATCH_SIZE} files per batch",
                400
            )

        # Save all files
        file_info = []
        for file in files:
            if file.filename and allowed_file(file.filename):
                filepath = save_uploaded_file(file)
                filepaths.append(filepath)
                file_info.append({
                    'filepath': filepath,
                    'original_name': file.filename
                })

        if not file_info:
            return error_response(
                "NO_VALID_FILES",
                "No valid files in batch",
                400
            )

        # Process files in parallel
        ocr_service = get_ocr_service()
        formatter = get_output_formatter()

        results = []

        def process_single(info):
            """Process a single file."""
            try:
                from src.services import ProcessingResult, DocumentType

                ocr_result = ocr_service.process_image(str(info['filepath']))

                return ProcessingResult(
                    text=ocr_result.text,
                    confidence=ocr_result.confidence,
                    ocr_result=ocr_result,
                    document_type=DocumentType.GENERAL,
                    filename=info['original_name'],
                    processing_time_ms=ocr_result.processing_time_ms
                )
            except Exception as e:
                from src.services import ProcessingResult, DocumentType
                return ProcessingResult(
                    text="",
                    confidence=0.0,
                    document_type=DocumentType.GENERAL,
                    filename=info['original_name'],
                    errors=[str(e)]
                )

        with ThreadPoolExecutor(max_workers=min(4, len(file_info))) as executor:
            futures = {executor.submit(process_single, info): info for info in file_info}

            for future in as_completed(futures):
                results.append(future.result())

        # Format batch response
        response = formatter.format_batch_response(results, batch_id=request_id)
        response['processing_time_ms'] = (time.time() - start_time) * 1000

        return jsonify(response), 200

    except Exception as e:
        logger.exception(f"[{request_id}] Batch processing failed")
        return error_response("BATCH_FAILED", f"Batch processing failed: {str(e)}", 500)

    finally:
        for filepath in filepaths:
            cleanup_file(filepath)


# ============================================================================
# GET /api/v2/ocr/health - Health Check
# ============================================================================

@ocr_v2_bp.route('/health', methods=['GET'])
def health_check():
    """
    Service health check.

    Response:
        - Service status and component health
    """
    try:
        # Get services
        ocr_service = get_ocr_service()

        # Check component health
        engine_status = ocr_service.get_engine_status()

        # Check LLM
        llm_service = get_llm_service()
        llm_status = llm_service.get_status() if llm_service else {"available": False}

        # Calculate uptime
        uptime_seconds = (datetime.utcnow() - SERVICE_START_TIME).total_seconds()

        # Determine overall status
        paddle_ok = engine_status.get('paddle', {}).get('available', False)
        easyocr_ok = engine_status.get('easyocr', {}).get('available', False)

        if paddle_ok or easyocr_ok:
            status = "healthy"
        else:
            status = "degraded"

        response = {
            "status": status,
            "version": "2.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int(uptime_seconds),
            "components": {
                "paddle_ocr": {
                    "status": "healthy" if paddle_ok else "unavailable",
                    "available": paddle_ok,
                    "gpu": engine_status.get('paddle', {}).get('gpu', False)
                },
                "easyocr": {
                    "status": "healthy" if easyocr_ok else "unavailable",
                    "available": easyocr_ok,
                    "gpu": engine_status.get('easyocr', {}).get('gpu', False)
                },
                "tesseract": {
                    "status": "healthy" if engine_status.get('tesseract', {}).get('available') else "unavailable",
                    "available": engine_status.get('tesseract', {}).get('available', False)
                },
                "llm": {
                    "status": "healthy" if llm_status.get('available') else "unavailable",
                    "available": llm_status.get('available', False),
                    "model": llm_status.get('model', 'N/A')
                }
            },
            "configuration": {
                "engine_mode": engine_status.get('engine_mode', 'fusion'),
                "languages": engine_status.get('languages', ['ar', 'en'])
            }
        }

        return jsonify(response), 200

    except Exception as e:
        logger.exception("Health check failed")
        return jsonify({
            "status": "unhealthy",
            "version": "2.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }), 503


# ============================================================================
# GET /api/v2/ocr/metrics - Prometheus Metrics
# ============================================================================

@ocr_v2_bp.route('/metrics', methods=['GET'])
def metrics_endpoint():
    """
    Prometheus-format metrics endpoint.

    Response:
        - Metrics in Prometheus text format
    """
    try:
        # Update engine availability before returning metrics
        try:
            ocr_service = get_ocr_service()
            engine_status = ocr_service.get_engine_status()
            set_engine_availability("paddle", engine_status.get('paddle', {}).get('available', False))
            set_engine_availability("easyocr", engine_status.get('easyocr', {}).get('available', False))
            set_engine_availability("tesseract", engine_status.get('tesseract', {}).get('available', False))
        except Exception:
            pass  # Don't fail metrics endpoint if service not ready

        # Get Prometheus-format metrics from registry
        metrics_output = get_prometheus_metrics()

        return Response(metrics_output, mimetype='text/plain; charset=utf-8')

    except Exception as e:
        logger.exception("Metrics endpoint failed")
        return error_response("METRICS_FAILED", str(e), 500)


# ============================================================================
# Error Handlers
# ============================================================================

@ocr_v2_bp.errorhandler(400)
def handle_bad_request(error):
    return error_response("INVALID_REQUEST", str(error), 400)


@ocr_v2_bp.errorhandler(413)
def handle_file_too_large(error):
    return error_response(
        "FILE_TOO_LARGE",
        f"File exceeds maximum size ({MAX_FILE_SIZE // (1024*1024)}MB)",
        413
    )


@ocr_v2_bp.errorhandler(415)
def handle_unsupported_media(error):
    return error_response("UNSUPPORTED_FORMAT", "Unsupported file format", 415)


@ocr_v2_bp.errorhandler(429)
def handle_rate_limit(error):
    return error_response("RATE_LIMITED", "Too many requests", 429)


@ocr_v2_bp.errorhandler(500)
def handle_server_error(error):
    return error_response("INTERNAL_ERROR", "Internal server error", 500)


@ocr_v2_bp.errorhandler(503)
def handle_service_unavailable(error):
    return error_response("SERVICE_UNAVAILABLE", "Service temporarily unavailable", 503)
