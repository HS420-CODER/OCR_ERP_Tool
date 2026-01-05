"""
Integration tests for API endpoints.

Tests the Flask API endpoints using test client.
"""

import pytest
import sys
import os
import io
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.app import create_app


@pytest.fixture
def app():
    """Create test application."""
    app = create_app({
        'TESTING': True,
        'UPLOAD_FOLDER': str(Path(__file__).parent / 'test_uploads')
    })
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def test_image():
    """Create a simple test image (1x1 white PNG)."""
    # Minimal valid PNG (1x1 white pixel)
    png_data = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0xFF,
        0x00, 0x05, 0xFE, 0x02, 0xFE, 0xDC, 0xCC, 0x59,
        0xE7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,  # IEND chunk
        0x44, 0xAE, 0x42, 0x60, 0x82
    ])
    return io.BytesIO(png_data)


class TestHealthEndpoint:
    """Tests for /api/health endpoint."""

    def test_health_check_success(self, client):
        """Test health check returns success."""
        response = client.get('/api/health')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] == True
        assert data['status'] == 'ok'
        assert 'version' in data
        assert 'supported_languages' in data
        assert 'en' in data['supported_languages']
        assert 'ar' in data['supported_languages']

    def test_health_check_includes_formats(self, client):
        """Test health check includes supported formats."""
        response = client.get('/api/health')
        data = json.loads(response.data)

        assert 'supported_formats' in data
        assert 'png' in data['supported_formats']
        assert 'pdf' in data['supported_formats']


class TestVersionEndpoint:
    """Tests for /api/version endpoint."""

    def test_version_returns_info(self, client):
        """Test version endpoint returns version info."""
        response = client.get('/api/version')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] == True
        assert 'version' in data
        assert 'name' in data


class TestConfigEndpoints:
    """Tests for /api/config endpoints."""

    def test_get_config(self, client):
        """Test getting configuration."""
        response = client.get('/api/config')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] == True
        assert 'config' in data
        assert 'default_engine' in data['config']
        assert 'default_language' in data['config']
        assert 'fallback_enabled' in data['config']

    def test_update_config_language(self, client):
        """Test updating default language."""
        response = client.put(
            '/api/config',
            json={'default_language': 'ar'},
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] == True
        assert 'default_language' in data.get('updated_fields', [])

    def test_update_config_invalid_language_ignored(self, client):
        """Test that invalid language is ignored."""
        response = client.put(
            '/api/config',
            json={'default_language': 'xyz'},
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] == True
        # Invalid language should not be in updated fields
        assert 'default_language' not in data.get('updated_fields', [])


class TestEnginesEndpoints:
    """Tests for /api/engines endpoints."""

    def test_list_engines(self, client):
        """Test listing all engines."""
        response = client.get('/api/engines')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] == True
        assert 'engines' in data
        assert isinstance(data['engines'], list)

    def test_list_engines_includes_paddle(self, client):
        """Test that paddle engine is in the list."""
        response = client.get('/api/engines')
        data = json.loads(response.data)

        engine_names = [e.get('name') for e in data['engines']]
        assert 'paddle' in engine_names

    def test_list_engines_includes_tesseract(self, client):
        """Test that tesseract engine is in the list."""
        response = client.get('/api/engines')
        data = json.loads(response.data)

        engine_names = [e.get('name') for e in data['engines']]
        assert 'tesseract' in engine_names

    def test_get_engine_details(self, client):
        """Test getting specific engine details."""
        response = client.get('/api/engines/paddle')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] == True
        assert 'engine' in data
        assert data['engine']['name'] == 'paddle'
        assert 'capabilities' in data['engine']

    def test_get_engine_details_not_found(self, client):
        """Test getting non-existent engine."""
        response = client.get('/api/engines/nonexistent')

        assert response.status_code == 404
        data = json.loads(response.data)

        assert data['success'] == False

    def test_list_available_engines(self, client):
        """Test listing only available engines."""
        response = client.get('/api/engines/available')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] == True
        assert 'available_engines' in data
        assert isinstance(data['available_engines'], list)

    def test_test_engine_paddle(self, client):
        """Test testing paddle engine availability."""
        response = client.post('/api/engines/paddle/test')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] == True
        assert data['engine'] == 'paddle'
        assert 'available' in data


class TestLanguagesEndpoint:
    """Tests for /api/languages endpoint."""

    def test_list_languages(self, client):
        """Test listing supported languages."""
        response = client.get('/api/languages')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] == True
        assert 'languages' in data

        # Check English
        en_lang = next((l for l in data['languages'] if l['code'] == 'en'), None)
        assert en_lang is not None
        assert en_lang['name'] == 'English'

        # Check Arabic
        ar_lang = next((l for l in data['languages'] if l['code'] == 'ar'), None)
        assert ar_lang is not None
        assert ar_lang['name'] == 'Arabic'
        assert ar_lang['direction'] == 'rtl'


class TestOCREndpoints:
    """Tests for /api/ocr endpoints."""

    def test_ocr_no_file_error(self, client):
        """Test OCR without file returns error."""
        response = client.post('/api/ocr')

        assert response.status_code == 400
        data = json.loads(response.data)

        assert data['success'] == False
        assert 'No file' in data['error']

    def test_ocr_empty_filename_error(self, client):
        """Test OCR with empty filename returns error."""
        response = client.post(
            '/api/ocr',
            data={'file': (io.BytesIO(b''), '')}
        )

        assert response.status_code == 400
        data = json.loads(response.data)

        assert data['success'] == False

    def test_ocr_invalid_file_type_error(self, client):
        """Test OCR with invalid file type returns error."""
        response = client.post(
            '/api/ocr',
            data={'file': (io.BytesIO(b'test'), 'test.xyz')}
        )

        assert response.status_code == 400
        data = json.loads(response.data)

        assert data['success'] == False
        assert 'not allowed' in data['error'].lower()

    def test_ocr_text_no_file_error(self, client):
        """Test text-only OCR without file returns error."""
        response = client.post('/api/ocr/text')

        assert response.status_code == 400
        data = json.loads(response.data)

        assert data['success'] == False

    def test_ocr_structured_no_file_error(self, client):
        """Test structured OCR without file returns error."""
        response = client.post('/api/ocr/structured')

        assert response.status_code == 400
        data = json.loads(response.data)

        assert data['success'] == False


class TestOCRWithFile:
    """Tests for OCR endpoints with actual files (requires PaddleOCR)."""

    @pytest.fixture
    def fixtures_dir(self):
        """Get fixtures directory."""
        return Path(__file__).parent.parent / "fixtures"

    def test_ocr_with_test_image(self, client, fixtures_dir):
        """Test OCR with a real test image."""
        test_image = fixtures_dir / "test_image.png"
        if not test_image.exists():
            pytest.skip("Test image fixture not available")

        with open(test_image, 'rb') as f:
            response = client.post(
                '/api/ocr',
                data={
                    'file': (f, 'test_image.png'),
                    'lang': 'en'
                }
            )

        # Should either succeed or fail gracefully
        data = json.loads(response.data)
        assert 'success' in data

        if data['success']:
            assert 'data' in data
            assert 'full_text' in data['data']
            assert 'engine_used' in data['data']


class TestErrorHandling:
    """Tests for error handling."""

    def test_404_for_unknown_endpoint(self, client):
        """Test 404 for unknown API endpoint."""
        response = client.get('/api/unknown_endpoint')

        assert response.status_code == 404

    def test_json_response_for_errors(self, client):
        """Test that errors return JSON responses."""
        response = client.post('/api/ocr')

        assert response.content_type == 'application/json'
        data = json.loads(response.data)
        assert 'success' in data
        assert 'error' in data


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_returns_api_info(self, client):
        """Test root endpoint returns API info when no frontend."""
        response = client.get('/')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] == True
        assert 'endpoints' in data
