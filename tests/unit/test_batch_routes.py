"""
Tests for batch OCR processing endpoint.
"""

import pytest
import io
from unittest.mock import MagicMock, patch


class TestBatchOCREndpoint:
    """Tests for POST /api/ocr/batch endpoint."""

    def test_batch_no_files(self, client):
        """Test batch endpoint with no files."""
        response = client.post('/api/ocr/batch')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'No files provided' in data['error']

    def test_batch_empty_files_list(self, client):
        """Test batch endpoint with empty files list."""
        response = client.post('/api/ocr/batch', data={})
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    def test_batch_single_file(self, client, mock_read_tool):
        """Test batch processing with single file."""
        # Create test file
        test_file = (io.BytesIO(b'test image content'), 'test.png')

        response = client.post(
            '/api/ocr/batch',
            data={'files': test_file},
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['total_files'] == 1
        assert 'results' in data
        assert 'total_processing_time_ms' in data

    def test_batch_multiple_files(self, client, mock_read_tool):
        """Test batch processing with multiple files."""
        # Create multiple test files
        files = [
            (io.BytesIO(b'test image 1'), 'test1.png'),
            (io.BytesIO(b'test image 2'), 'test2.jpg'),
        ]

        response = client.post(
            '/api/ocr/batch',
            data={'files': files},
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['total_files'] == 2
        assert len(data['results']) == 2

    def test_batch_with_language(self, client, mock_read_tool):
        """Test batch processing with language parameter."""
        test_file = (io.BytesIO(b'test content'), 'test.png')

        response = client.post(
            '/api/ocr/batch',
            data={
                'files': test_file,
                'lang': 'ar'
            },
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_batch_with_engine(self, client, mock_read_tool):
        """Test batch processing with engine parameter."""
        test_file = (io.BytesIO(b'test content'), 'test.png')

        response = client.post(
            '/api/ocr/batch',
            data={
                'files': test_file,
                'engine': 'paddle'
            },
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_batch_with_structured_output(self, client, mock_read_tool):
        """Test batch processing with structured output enabled."""
        test_file = (io.BytesIO(b'test content'), 'test.png')

        response = client.post(
            '/api/ocr/batch',
            data={
                'files': test_file,
                'structured': 'true'
            },
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_batch_invalid_file_type(self, client):
        """Test batch processing with invalid file type."""
        test_file = (io.BytesIO(b'test content'), 'test.exe')

        response = client.post(
            '/api/ocr/batch',
            data={'files': test_file},
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['failed'] == 1
        assert 'not allowed' in data['results'][0]['error']

    def test_batch_mixed_valid_invalid(self, client, mock_read_tool):
        """Test batch with mix of valid and invalid files."""
        files = [
            (io.BytesIO(b'valid image'), 'valid.png'),
            (io.BytesIO(b'invalid file'), 'invalid.exe'),
        ]

        response = client.post(
            '/api/ocr/batch',
            data={'files': files},
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['total_files'] == 2
        assert data['processed'] == 1
        assert data['failed'] == 1

    def test_batch_response_structure(self, client, mock_read_tool):
        """Test that batch response has correct structure."""
        test_file = (io.BytesIO(b'test content'), 'test.png')

        response = client.post(
            '/api/ocr/batch',
            data={'files': test_file},
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        data = response.get_json()

        # Check top-level fields
        assert 'success' in data
        assert 'total_files' in data
        assert 'processed' in data
        assert 'failed' in data
        assert 'results' in data
        assert 'total_processing_time_ms' in data

        # Check result item structure
        result = data['results'][0]
        assert 'filename' in result
        assert 'success' in result


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def app():
    """Create test application."""
    from api.app import create_app

    app = create_app({
        'TESTING': True,
        'UPLOAD_FOLDER': '/tmp/test_uploads'
    })

    return app


@pytest.fixture
def mock_read_tool(app):
    """Mock the read tool for testing."""
    from src.models import ReadResult, PageResult

    mock_result = ReadResult(
        success=True,
        file_path='/test/path.png',
        file_type='image',
        engine_used='paddle',
        pages=[PageResult(page_number=1, text_blocks=[], full_text='Test text')],
        full_text='Test text',
        processing_time_ms=100.0,
        language='en'
    )

    mock_tool = MagicMock()
    mock_tool.read.return_value = mock_result

    app.config['READ_TOOL'] = mock_tool
    return mock_tool
