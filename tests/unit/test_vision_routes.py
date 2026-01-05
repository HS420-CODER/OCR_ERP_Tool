"""
Tests for vision analysis endpoints.
"""

import pytest
import io
from unittest.mock import MagicMock, patch, PropertyMock


class TestVisionAnalyzeEndpoint:
    """Tests for POST /api/vision/analyze endpoint."""

    def test_analyze_no_file(self, client):
        """Test analyze endpoint with no file."""
        response = client.post('/api/vision/analyze')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'No file provided' in data['error']

    def test_analyze_invalid_file_type(self, client):
        """Test analyze endpoint with invalid file type."""
        test_file = (io.BytesIO(b'test content'), 'test.exe')

        response = client.post(
            '/api/vision/analyze',
            data={'file': test_file},
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'not allowed' in data['error']

    def test_analyze_ollama_not_available(self, client, mock_read_tool_no_ollama):
        """Test analyze when Ollama is not available."""
        test_file = (io.BytesIO(b'test content'), 'test.png')

        response = client.post(
            '/api/vision/analyze',
            data={'file': test_file},
            content_type='multipart/form-data'
        )

        assert response.status_code == 503
        data = response.get_json()
        assert data['success'] is False
        assert 'not available' in data['error'].lower() or 'not running' in data['error'].lower()

    def test_analyze_success(self, client, mock_read_tool_with_ollama):
        """Test successful vision analysis."""
        test_file = (io.BytesIO(b'test image content'), 'test.png')

        response = client.post(
            '/api/vision/analyze',
            data={'file': test_file},
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'analysis' in data
        assert 'model_used' in data
        assert 'processing_time_ms' in data

    def test_analyze_with_language(self, client, mock_read_tool_with_ollama):
        """Test vision analysis with language parameter."""
        test_file = (io.BytesIO(b'test content'), 'test.png')

        response = client.post(
            '/api/vision/analyze',
            data={
                'file': test_file,
                'lang': 'ar'
            },
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['metadata']['language_hint'] == 'ar'


class TestVisionPromptEndpoint:
    """Tests for POST /api/vision/prompt endpoint."""

    def test_prompt_no_file(self, client):
        """Test prompt endpoint with no file."""
        response = client.post('/api/vision/prompt', data={'prompt': 'Test prompt'})
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    def test_prompt_no_prompt(self, client):
        """Test prompt endpoint with no prompt."""
        test_file = (io.BytesIO(b'test content'), 'test.png')

        response = client.post(
            '/api/vision/prompt',
            data={'file': test_file},
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'Prompt is required' in data['error']

    def test_prompt_empty_prompt(self, client):
        """Test prompt endpoint with empty prompt."""
        test_file = (io.BytesIO(b'test content'), 'test.png')

        response = client.post(
            '/api/vision/prompt',
            data={
                'file': test_file,
                'prompt': '   '
            },
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'Prompt is required' in data['error']

    def test_prompt_success(self, client, mock_read_tool_with_ollama):
        """Test successful custom prompt analysis."""
        test_file = (io.BytesIO(b'test image content'), 'test.png')

        response = client.post(
            '/api/vision/prompt',
            data={
                'file': test_file,
                'prompt': 'What is the total amount?'
            },
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'prompt' in data
        assert 'response' in data
        assert data['prompt'] == 'What is the total amount?'


class TestVisionModelsEndpoint:
    """Tests for GET /api/vision/models endpoint."""

    def test_get_models(self, client, mock_read_tool_with_ollama):
        """Test getting available vision models."""
        response = client.get('/api/vision/models')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'models' in data
        assert 'default_model' in data
        assert len(data['models']) > 0

    def test_models_structure(self, client, mock_read_tool_with_ollama):
        """Test that models have correct structure."""
        response = client.get('/api/vision/models')

        data = response.get_json()
        for model in data['models']:
            assert 'name' in model
            assert 'description' in model


class TestVisionStatusEndpoint:
    """Tests for GET /api/vision/status endpoint."""

    def test_status_available(self, client, mock_read_tool_with_ollama):
        """Test status when Ollama is available."""
        response = client.get('/api/vision/status')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'ollama_available' in data
        assert 'server_url' in data
        assert 'message' in data

    def test_status_unavailable(self, client, mock_read_tool_no_ollama):
        """Test status when Ollama is not available."""
        response = client.get('/api/vision/status')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['ollama_available'] is False


# Fixtures

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
def mock_read_tool_no_ollama(app):
    """Mock read tool where Ollama is not available."""
    mock_tool = MagicMock()
    mock_engine_manager = MagicMock()
    mock_engine_manager.get_engine.side_effect = Exception("Ollama not available")

    mock_tool.engine_manager = mock_engine_manager
    app.config['READ_TOOL'] = mock_tool
    return mock_tool


@pytest.fixture
def mock_read_tool_with_ollama(app):
    """Mock read tool where Ollama is available."""
    from src.models import ReadResult, PageResult

    mock_result = ReadResult(
        success=True,
        file_path='/test/path.png',
        file_type='image',
        engine_used='ollama',
        pages=[PageResult(page_number=1, text_blocks=[], full_text='Vision analysis result')],
        full_text='Vision analysis result',
        processing_time_ms=200.0,
        language='en'
    )

    mock_ollama = MagicMock()
    mock_ollama.is_available.return_value = True
    mock_ollama.process_with_prompt.return_value = mock_result
    mock_ollama._host = 'http://localhost:11434'

    mock_engine_manager = MagicMock()
    mock_engine_manager.get_engine.return_value = mock_ollama

    mock_tool = MagicMock()
    mock_tool.engine_manager = mock_engine_manager
    mock_tool.read.return_value = mock_result

    app.config['READ_TOOL'] = mock_tool
    return mock_tool
