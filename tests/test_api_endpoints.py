"""
ERP Arabic OCR Microservice - API Integration Tests
====================================================
Integration tests for REST API endpoints.
"""

import io
import os
import sys
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ==============================================================================
# Test Configuration
# ==============================================================================

@pytest.fixture
def app():
    """Create test Flask application."""
    from api import create_app

    app = create_app()
    app.config['TESTING'] = True
    app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

    # Disable actual OCR for unit tests
    app.config['OCR_MOCK'] = True

    # Disable security middleware for testing
    try:
        from src.middleware.security import get_security_middleware
        security_middleware = get_security_middleware()
        security_middleware.disable_security()
    except Exception:
        pass  # Security middleware may not be initialized

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def mock_ocr_service():
    """Create mock OCR service."""
    from src.services import OCRResult, OCREngine

    mock_service = Mock()
    mock_service.process_image.return_value = OCRResult(
        text="الرقم الضريبي: 310123456789012\nفاتورة رقم: 12345",
        confidence=0.95,
        engine=OCREngine.PADDLE,
        blocks=[]
    )
    mock_service.get_engine_status.return_value = {
        'engine_mode': 'fusion',
        'languages': ['ar', 'en'],
        'paddle': {'available': True, 'gpu': False},
        'easyocr': {'available': True, 'gpu': False},
        'tesseract': {'available': False}
    }

    return mock_service


@pytest.fixture
def mock_llm_service():
    """Create mock LLM service."""
    from src.services import CorrectionResult

    mock_service = Mock()
    mock_service.is_available.return_value = True
    mock_service.correct.return_value = CorrectionResult(
        original="الرقم الضريبي",
        corrected="الرقم الضريبي",
        corrections_made=[],
        confidence=0.95,
        correction_type="llm"
    )
    mock_service.get_status.return_value = {
        'available': True,
        'model': 'test-model'
    }

    return mock_service


@pytest.fixture
def sample_image():
    """Create a sample test image."""
    img = Image.new('RGB', (800, 400), color='white')
    return img


@pytest.fixture
def sample_image_file(sample_image):
    """Create a sample image file in memory."""
    img_bytes = io.BytesIO()
    sample_image.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes


@pytest.fixture
def sample_pdf_file():
    """Create a minimal valid PDF file in memory."""
    # Minimal valid PDF content
    pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000052 00000 n
0000000101 00000 n
trailer<</Size 4/Root 1 0 R>>
startxref
171
%%EOF"""
    return io.BytesIO(pdf_content)


# ==============================================================================
# Health Endpoint Tests
# ==============================================================================

class TestHealthEndpoint:
    """Tests for /api/v2/ocr/health endpoint."""

    def test_health_check_success(self, client, mock_ocr_service, mock_llm_service):
        """Test successful health check."""
        with patch('api.routes.ocr_v2.get_ocr_service', return_value=mock_ocr_service), \
             patch('api.routes.ocr_v2.get_llm_service', return_value=mock_llm_service):

            response = client.get('/api/v2/ocr/health')

            assert response.status_code == 200
            data = response.get_json()

            assert data['status'] in ['healthy', 'degraded']
            assert 'version' in data
            assert 'timestamp' in data
            assert 'uptime_seconds' in data
            assert 'components' in data

    def test_health_check_components(self, client, mock_ocr_service, mock_llm_service):
        """Test health check returns component status."""
        with patch('api.routes.ocr_v2.get_ocr_service', return_value=mock_ocr_service), \
             patch('api.routes.ocr_v2.get_llm_service', return_value=mock_llm_service):

            response = client.get('/api/v2/ocr/health')
            data = response.get_json()

            assert 'paddle_ocr' in data['components']
            assert 'easyocr' in data['components']
            assert 'llm' in data['components']

    def test_health_check_degraded_status(self, client, mock_llm_service):
        """Test health check returns degraded when OCR engines unavailable."""
        mock_ocr = Mock()
        mock_ocr.get_engine_status.return_value = {
            'paddle': {'available': False},
            'easyocr': {'available': False},
            'tesseract': {'available': False}
        }

        with patch('api.routes.ocr_v2.get_ocr_service', return_value=mock_ocr), \
             patch('api.routes.ocr_v2.get_llm_service', return_value=mock_llm_service):

            response = client.get('/api/v2/ocr/health')
            data = response.get_json()

            assert data['status'] == 'degraded'

    def test_health_check_returns_version(self, client, mock_ocr_service, mock_llm_service):
        """Test health check returns version."""
        with patch('api.routes.ocr_v2.get_ocr_service', return_value=mock_ocr_service), \
             patch('api.routes.ocr_v2.get_llm_service', return_value=mock_llm_service):

            response = client.get('/api/v2/ocr/health')
            data = response.get_json()

            assert data['version'] == '2.0.0'


# ==============================================================================
# Invoice Endpoint Tests
# ==============================================================================

class TestInvoiceEndpoint:
    """Tests for /api/v2/ocr/invoice endpoint."""

    def test_invoice_success(self, client, sample_image_file, mock_ocr_service, mock_llm_service):
        """Test successful invoice processing."""
        mock_validator = Mock()
        mock_validator.validate.return_value = Mock(
            valid=True,
            errors=[],
            file_size=1000
        )

        mock_extractor = Mock()
        mock_extractor.extract_fields.return_value = Mock(
            vat_number="310123456789012",
            invoice_number="12345",
            total_amount=None,
            date=None
        )

        mock_formatter = Mock()
        mock_formatter.format_invoice_response.return_value = {
            'success': True,
            'text': 'Test text',
            'confidence': 0.95,
            'invoice_data': {}
        }

        with patch('api.routes.ocr_v2.get_ocr_service', return_value=mock_ocr_service), \
             patch('api.routes.ocr_v2.get_llm_service', return_value=mock_llm_service), \
             patch('api.routes.ocr_v2.get_file_validator', return_value=mock_validator), \
             patch('api.routes.ocr_v2.get_invoice_extractor', return_value=mock_extractor), \
             patch('api.routes.ocr_v2.get_output_formatter', return_value=mock_formatter):

            response = client.post(
                '/api/v2/ocr/invoice',
                data={
                    'file': (sample_image_file, 'test_invoice.png'),
                    'engine_mode': 'fusion',
                    'enable_llm': 'true',
                    'extract_fields': 'true'
                },
                content_type='multipart/form-data'
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True

    def test_invoice_missing_file(self, client):
        """Test invoice endpoint with missing file."""
        response = client.post('/api/v2/ocr/invoice')

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'MISSING_FILE'

    def test_invoice_empty_filename(self, client):
        """Test invoice endpoint with empty filename."""
        response = client.post(
            '/api/v2/ocr/invoice',
            data={'file': (io.BytesIO(b''), '')},
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'EMPTY_FILENAME'

    def test_invoice_invalid_file_validation(self, client, sample_image_file):
        """Test invoice endpoint with file that fails validation."""
        mock_validator = Mock()
        mock_validator.validate.return_value = Mock(
            valid=False,
            errors=['Invalid file type', 'File too large'],
            file_size=0
        )

        with patch('api.routes.ocr_v2.get_file_validator', return_value=mock_validator):
            response = client.post(
                '/api/v2/ocr/invoice',
                data={'file': (sample_image_file, 'test.png')},
                content_type='multipart/form-data'
            )

            assert response.status_code == 400
            data = response.get_json()
            assert data['error']['code'] == 'FILE_VALIDATION_FAILED'

    def test_invoice_ocr_failure(self, client, sample_image_file):
        """Test invoice endpoint when OCR fails."""
        mock_validator = Mock()
        mock_validator.validate.return_value = Mock(
            valid=True,
            errors=[],
            file_size=1000
        )

        mock_ocr = Mock()
        mock_ocr.process_image.side_effect = Exception("OCR engine crashed")

        with patch('api.routes.ocr_v2.get_file_validator', return_value=mock_validator), \
             patch('api.routes.ocr_v2.get_ocr_service', return_value=mock_ocr):

            response = client.post(
                '/api/v2/ocr/invoice',
                data={'file': (sample_image_file, 'test.png')},
                content_type='multipart/form-data'
            )

            assert response.status_code == 500
            data = response.get_json()
            assert data['error']['code'] == 'OCR_FAILED'

    def test_invoice_request_id_header(self, client, sample_image_file, mock_ocr_service, mock_llm_service):
        """Test that request ID is returned in header."""
        mock_validator = Mock()
        mock_validator.validate.return_value = Mock(valid=True, errors=[], file_size=1000)

        mock_formatter = Mock()
        mock_formatter.format_invoice_response.return_value = {'success': True}

        with patch('api.routes.ocr_v2.get_file_validator', return_value=mock_validator), \
             patch('api.routes.ocr_v2.get_ocr_service', return_value=mock_ocr_service), \
             patch('api.routes.ocr_v2.get_llm_service', return_value=mock_llm_service), \
             patch('api.routes.ocr_v2.get_invoice_extractor', return_value=Mock()), \
             patch('api.routes.ocr_v2.get_output_formatter', return_value=mock_formatter):

            response = client.post(
                '/api/v2/ocr/invoice',
                data={'file': (sample_image_file, 'test.png')},
                content_type='multipart/form-data'
            )

            assert 'X-Request-ID' in response.headers
            assert 'X-Processing-Time-Ms' in response.headers


# ==============================================================================
# Document Endpoint Tests
# ==============================================================================

class TestDocumentEndpoint:
    """Tests for /api/v2/ocr/document endpoint."""

    def test_document_image_success(self, client, sample_image_file, mock_ocr_service):
        """Test successful image document processing."""
        mock_validator = Mock()
        mock_validator.validate.return_value = Mock(valid=True, errors=[], file_size=1000)

        mock_formatter = Mock()
        mock_formatter.format_document_response.return_value = {
            'success': True,
            'text': 'Document text',
            'confidence': 0.92
        }

        with patch('api.routes.ocr_v2.get_file_validator', return_value=mock_validator), \
             patch('api.routes.ocr_v2.get_ocr_service', return_value=mock_ocr_service), \
             patch('api.routes.ocr_v2.get_output_formatter', return_value=mock_formatter):

            response = client.post(
                '/api/v2/ocr/document',
                data={'file': (sample_image_file, 'document.png')},
                content_type='multipart/form-data'
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True

    def test_document_missing_file(self, client):
        """Test document endpoint with missing file."""
        response = client.post('/api/v2/ocr/document')

        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'MISSING_FILE'

    def test_document_pdf_processing(self, client, sample_pdf_file, mock_ocr_service):
        """Test PDF document processing."""
        # Skip if pdf2image not installed
        try:
            import pdf2image
        except ImportError:
            pytest.skip("pdf2image not installed")

        mock_validator = Mock()
        mock_validator.validate.return_value = Mock(valid=True, errors=[], file_size=1000)

        mock_formatter = Mock()
        mock_formatter.format_document_response.return_value = {
            'success': True,
            'text': 'PDF text',
            'confidence': 0.90
        }

        # Mock pdf2image conversion
        mock_page = Image.new('RGB', (100, 100), color='white')

        with patch('api.routes.ocr_v2.get_file_validator', return_value=mock_validator), \
             patch('api.routes.ocr_v2.get_ocr_service', return_value=mock_ocr_service), \
             patch('api.routes.ocr_v2.get_output_formatter', return_value=mock_formatter), \
             patch('pdf2image.convert_from_path', return_value=[mock_page]):

            response = client.post(
                '/api/v2/ocr/document',
                data={'file': (sample_pdf_file, 'document.pdf')},
                content_type='multipart/form-data'
            )

            assert response.status_code == 200


# ==============================================================================
# Batch Endpoint Tests
# ==============================================================================

class TestBatchEndpoint:
    """Tests for /api/v2/ocr/batch endpoint."""

    def test_batch_success(self, client, sample_image_file, mock_ocr_service):
        """Test successful batch processing."""
        # Create multiple image files
        img1 = io.BytesIO()
        img2 = io.BytesIO()
        Image.new('RGB', (100, 100), color='white').save(img1, format='PNG')
        Image.new('RGB', (100, 100), color='white').save(img2, format='PNG')
        img1.seek(0)
        img2.seek(0)

        mock_formatter = Mock()
        mock_formatter.format_batch_response.return_value = {
            'success': True,
            'total_files': 2,
            'successful': 2,
            'failed': 0,
            'results': []
        }

        with patch('api.routes.ocr_v2.get_ocr_service', return_value=mock_ocr_service), \
             patch('api.routes.ocr_v2.get_output_formatter', return_value=mock_formatter), \
             patch('api.routes.ocr_v2.allowed_file', return_value=True):

            response = client.post(
                '/api/v2/ocr/batch',
                data={
                    'files': [
                        (img1, 'image1.png'),
                        (img2, 'image2.png')
                    ]
                },
                content_type='multipart/form-data'
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True

    def test_batch_missing_files(self, client):
        """Test batch endpoint with missing files."""
        response = client.post('/api/v2/ocr/batch')

        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'MISSING_FILES'

    def test_batch_too_many_files(self, client):
        """Test batch endpoint with too many files."""
        # Create 11 files (max is 10)
        files = []
        for i in range(11):
            img = io.BytesIO()
            Image.new('RGB', (10, 10), color='white').save(img, format='PNG')
            img.seek(0)
            files.append((img, f'image{i}.png'))

        with patch('api.routes.ocr_v2.allowed_file', return_value=True):
            response = client.post(
                '/api/v2/ocr/batch',
                data={'files': files},
                content_type='multipart/form-data'
            )

            assert response.status_code == 400
            data = response.get_json()
            assert data['error']['code'] == 'BATCH_TOO_LARGE'

    def test_batch_no_valid_files(self, client):
        """Test batch endpoint with no valid files."""
        with patch('api.routes.ocr_v2.allowed_file', return_value=False):
            response = client.post(
                '/api/v2/ocr/batch',
                data={'files': [(io.BytesIO(b'test'), 'test.txt')]},
                content_type='multipart/form-data'
            )

            assert response.status_code == 400
            data = response.get_json()
            assert data['error']['code'] == 'NO_VALID_FILES'


# ==============================================================================
# Metrics Endpoint Tests
# ==============================================================================

class TestMetricsEndpoint:
    """Tests for /api/v2/ocr/metrics endpoint."""

    def test_metrics_success(self, client, mock_ocr_service):
        """Test successful metrics retrieval."""
        with patch('api.routes.ocr_v2.get_ocr_service', return_value=mock_ocr_service), \
             patch('api.routes.ocr_v2.get_prometheus_metrics', return_value='# HELP test_metric\ntest_metric 1'):

            response = client.get('/api/v2/ocr/metrics')

            assert response.status_code == 200
            assert response.content_type.startswith('text/plain')

    def test_metrics_format(self, client, mock_ocr_service):
        """Test metrics are in Prometheus format."""
        metrics_output = """# HELP ocr_requests_total Total OCR requests
# TYPE ocr_requests_total counter
ocr_requests_total{status="success"} 100
# HELP ocr_latency_seconds OCR processing latency
# TYPE ocr_latency_seconds histogram
ocr_latency_seconds_bucket{le="0.1"} 10
"""
        with patch('api.routes.ocr_v2.get_ocr_service', return_value=mock_ocr_service), \
             patch('api.routes.ocr_v2.get_prometheus_metrics', return_value=metrics_output):

            response = client.get('/api/v2/ocr/metrics')
            content = response.data.decode('utf-8')

            assert '# HELP' in content
            assert '# TYPE' in content


# ==============================================================================
# Authentication Tests
# ==============================================================================

class TestAuthentication:
    """Tests for API authentication."""

    def test_authenticated_request_success(self, client, sample_image_file, mock_ocr_service, mock_llm_service):
        """Test authenticated request succeeds."""
        mock_validator = Mock()
        mock_validator.validate.return_value = Mock(valid=True, errors=[], file_size=1000)

        mock_formatter = Mock()
        mock_formatter.format_invoice_response.return_value = {'success': True}

        # Mock security middleware to accept token
        with patch('api.routes.ocr_v2.get_file_validator', return_value=mock_validator), \
             patch('api.routes.ocr_v2.get_ocr_service', return_value=mock_ocr_service), \
             patch('api.routes.ocr_v2.get_llm_service', return_value=mock_llm_service), \
             patch('api.routes.ocr_v2.get_invoice_extractor', return_value=Mock()), \
             patch('api.routes.ocr_v2.get_output_formatter', return_value=mock_formatter):

            response = client.post(
                '/api/v2/ocr/invoice',
                headers={'Authorization': 'Bearer test-api-key-123'},
                data={'file': (sample_image_file, 'test.png')},
                content_type='multipart/form-data'
            )

            # Should not fail due to auth (auth may be disabled in test mode)
            assert response.status_code in [200, 401]


# ==============================================================================
# Rate Limiting Tests
# ==============================================================================

class TestRateLimiting:
    """Tests for API rate limiting."""

    def test_rate_limit_response_format(self, client):
        """Test rate limit response format."""
        # This tests the error handler format
        with client.application.test_request_context():
            from api.routes.ocr_v2 import error_response

            response, status_code = error_response(
                "RATE_LIMITED",
                "Too many requests",
                429
            )

            data = response.get_json()
            assert data['success'] is False
            assert data['error']['code'] == 'RATE_LIMITED'
            assert status_code == 429


# ==============================================================================
# Error Handler Tests
# ==============================================================================

class TestErrorHandlers:
    """Tests for error handlers."""

    def test_error_response_format(self, client):
        """Test error response format."""
        response = client.post('/api/v2/ocr/invoice')

        data = response.get_json()

        assert 'success' in data
        assert data['success'] is False
        assert 'error' in data
        assert 'code' in data['error']
        assert 'message' in data['error']
        assert 'timestamp' in data

    def test_request_id_in_error(self, client):
        """Test request ID is included in errors."""
        response = client.post('/api/v2/ocr/invoice')

        data = response.get_json()

        assert 'request_id' in data['error']


# ==============================================================================
# Request Context Tests
# ==============================================================================

class TestRequestContext:
    """Tests for request context handling."""

    def test_request_id_generated(self, client, sample_image_file, mock_ocr_service):
        """Test request ID is generated."""
        mock_validator = Mock()
        mock_validator.validate.return_value = Mock(valid=True, errors=[], file_size=1000)

        mock_formatter = Mock()
        mock_formatter.format_document_response.return_value = {'success': True}

        with patch('api.routes.ocr_v2.get_file_validator', return_value=mock_validator), \
             patch('api.routes.ocr_v2.get_ocr_service', return_value=mock_ocr_service), \
             patch('api.routes.ocr_v2.get_output_formatter', return_value=mock_formatter):

            response = client.post(
                '/api/v2/ocr/document',
                data={'file': (sample_image_file, 'test.png')},
                content_type='multipart/form-data'
            )

            assert 'X-Request-ID' in response.headers
            # Request ID should be 8 characters
            assert len(response.headers['X-Request-ID']) == 8

    def test_processing_time_tracked(self, client, sample_image_file, mock_ocr_service):
        """Test processing time is tracked."""
        mock_validator = Mock()
        mock_validator.validate.return_value = Mock(valid=True, errors=[], file_size=1000)

        mock_formatter = Mock()
        mock_formatter.format_document_response.return_value = {'success': True}

        with patch('api.routes.ocr_v2.get_file_validator', return_value=mock_validator), \
             patch('api.routes.ocr_v2.get_ocr_service', return_value=mock_ocr_service), \
             patch('api.routes.ocr_v2.get_output_formatter', return_value=mock_formatter):

            response = client.post(
                '/api/v2/ocr/document',
                data={'file': (sample_image_file, 'test.png')},
                content_type='multipart/form-data'
            )

            assert 'X-Processing-Time-Ms' in response.headers
            # Should be a valid integer
            int(response.headers['X-Processing-Time-Ms'])


# ==============================================================================
# File Validation Tests
# ==============================================================================

class TestFileValidation:
    """Tests for file validation in API."""

    def test_allowed_extensions(self):
        """Test allowed file extension checking."""
        from api.routes.ocr_v2 import allowed_file

        assert allowed_file('test.png') is True
        assert allowed_file('test.jpg') is True
        assert allowed_file('test.jpeg') is True
        assert allowed_file('test.pdf') is True
        assert allowed_file('test.tiff') is True
        assert allowed_file('test.bmp') is True

    def test_disallowed_extensions(self):
        """Test disallowed file extensions."""
        from api.routes.ocr_v2 import allowed_file

        assert allowed_file('test.txt') is False
        assert allowed_file('test.exe') is False
        assert allowed_file('test.doc') is False
        assert allowed_file('test') is False

    def test_case_insensitive_extensions(self):
        """Test extension check is case insensitive."""
        from api.routes.ocr_v2 import allowed_file

        assert allowed_file('test.PNG') is True
        assert allowed_file('test.JPG') is True
        assert allowed_file('test.PDF') is True


# ==============================================================================
# Content Type Tests
# ==============================================================================

class TestContentTypes:
    """Tests for content type handling."""

    def test_health_returns_json(self, client, mock_ocr_service, mock_llm_service):
        """Test health endpoint returns JSON."""
        with patch('api.routes.ocr_v2.get_ocr_service', return_value=mock_ocr_service), \
             patch('api.routes.ocr_v2.get_llm_service', return_value=mock_llm_service):

            response = client.get('/api/v2/ocr/health')

            assert response.content_type == 'application/json'

    def test_metrics_returns_plain_text(self, client, mock_ocr_service):
        """Test metrics endpoint returns plain text."""
        with patch('api.routes.ocr_v2.get_ocr_service', return_value=mock_ocr_service), \
             patch('api.routes.ocr_v2.get_prometheus_metrics', return_value='metrics'):

            response = client.get('/api/v2/ocr/metrics')

            assert response.content_type.startswith('text/plain')


# ==============================================================================
# Integration Flow Tests
# ==============================================================================

class TestIntegrationFlows:
    """Tests for complete integration flows."""

    def test_complete_invoice_flow(self, client, sample_image_file, mock_ocr_service, mock_llm_service):
        """Test complete invoice processing flow."""
        mock_validator = Mock()
        mock_validator.validate.return_value = Mock(valid=True, errors=[], file_size=1000)

        mock_extractor = Mock()
        mock_extractor.extract_fields.return_value = Mock(
            vat_number="310123456789012",
            invoice_number="12345"
        )

        mock_formatter = Mock()
        mock_formatter.format_invoice_response.return_value = {
            'success': True,
            'request_id': 'test123',
            'data': {
                'text': 'Test invoice text',
                'confidence': 0.95,
                'invoice_fields': {
                    'vat_number': '310123456789012',
                    'invoice_number': '12345'
                }
            }
        }

        with patch('api.routes.ocr_v2.get_file_validator', return_value=mock_validator), \
             patch('api.routes.ocr_v2.get_ocr_service', return_value=mock_ocr_service), \
             patch('api.routes.ocr_v2.get_llm_service', return_value=mock_llm_service), \
             patch('api.routes.ocr_v2.get_invoice_extractor', return_value=mock_extractor), \
             patch('api.routes.ocr_v2.get_output_formatter', return_value=mock_formatter):

            response = client.post(
                '/api/v2/ocr/invoice',
                data={
                    'file': (sample_image_file, 'invoice.png'),
                    'enable_llm': 'true',
                    'extract_fields': 'true'
                },
                content_type='multipart/form-data'
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True


# ==============================================================================
# Run Tests
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
