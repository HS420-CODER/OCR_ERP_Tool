# ERP Arabic OCR Microservice - Comprehensive Implementation Plan

> **Version:** 1.0 | **Date:** January 2026 | **Status:** Ready for Implementation
> **Reference:** `docs/ERP_ARABIC_OCR_MICROSERVICE.md`
> **Target:** CER 0.06 (94% accuracy) | Throughput: 2-20 docs/sec

---

## Table of Contents

1. [Implementation Overview](#implementation-overview)
2. [Stage 1: Project Foundation & Setup](#stage-1-project-foundation--setup)
3. [Stage 2: Core OCR Services](#stage-2-core-ocr-services)
4. [Stage 3: REST API Layer](#stage-3-rest-api-layer)
5. [Stage 4: Security Layer](#stage-4-security-layer)
6. [Stage 5: Performance & Monitoring](#stage-5-performance--monitoring)
7. [Stage 6: Deployment Configuration](#stage-6-deployment-configuration)
8. [Stage 7: Client Libraries & Testing](#stage-7-client-libraries--testing)
9. [Files Summary](#files-to-create-summary)
10. [Verification Checklists](#verification-checklists)
11. [Success Criteria](#success-criteria)

---

## Implementation Overview

This plan implements a production-ready Multi-Engine Arabic OCR Microservice for ERP integration with Apache servers. The implementation is divided into **7 stages** with **42 steps**.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        IMPLEMENTATION ROADMAP                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STAGE 1         STAGE 2         STAGE 3         STAGE 4                    │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐                │
│  │ Project │ ──► │   OCR   │ ──► │   API   │ ──► │Security │                │
│  │  Setup  │     │  Core   │     │  Layer  │     │  Layer  │                │
│  └─────────┘     └─────────┘     └─────────┘     └─────────┘                │
│    4 steps         7 steps         7 steps         3 steps                  │
│                                                                              │
│  STAGE 5         STAGE 6         STAGE 7                                    │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐                                │
│  │ Perf &  │ ──► │ Deploy  │ ──► │ Client  │                                │
│  │ Monitor │     │ Config  │     │  Libs   │                                │
│  └─────────┘     └─────────┘     └─────────┘                                │
│    5 steps         7 steps         6 steps                                  │
│                                                                              │
│                    TOTAL: 39 STEPS                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Stage Dependencies

```
Stage 1 ─┬─► Stage 2 ─┬─► Stage 3 ─┬─► Stage 4
         │            │            │
         │            │            └─► Stage 5 ─► Stage 6
         │            │
         │            └─► Stage 7 (can run in parallel after Stage 2)
         │
         └─► Stage 6 (deployment configs can start early)
```

---

## Stage 1: Project Foundation & Setup

**Goal:** Establish project structure, dependencies, and configuration
**Duration Estimate:** Foundation stage
**Dependencies:** None

### Step 1.1: Create Directory Structure

Create the following project structure:

```
C:\wamp64\www\OCR_2\
├── src/
│   ├── services/                    # Core OCR services
│   │   ├── __init__.py
│   │   ├── ocr_microservice.py      # Multi-engine OCR
│   │   ├── fusion_engine.py         # Confidence-weighted fusion
│   │   ├── llm_correction.py        # LLM post-correction
│   │   ├── invoice_extractor.py     # Invoice field extraction
│   │   ├── output_formatter.py      # Response formatting
│   │   ├── cache_manager.py         # Redis caching
│   │   └── resource_manager.py      # Resource management
│   ├── middleware/                  # Security & request processing
│   │   ├── __init__.py
│   │   ├── security.py              # API authentication
│   │   └── file_security.py         # File validation
│   ├── utils/                       # Utilities
│   │   ├── __init__.py
│   │   ├── logging_config.py        # Structured logging
│   │   └── metrics.py               # Prometheus metrics
│   └── lib/                         # Client libraries
│       ├── __init__.py
│       └── erp_ocr_client.py        # Python client
├── api/
│   ├── __init__.py                  # Flask app factory
│   └── routes/
│       ├── __init__.py
│       └── ocr_v2.py                # v2 API endpoints
├── config/
│   ├── __init__.py
│   ├── settings.py                  # Application settings
│   └── gunicorn.conf.py             # Gunicorn config
├── tests/
│   ├── __init__.py
│   ├── test_ocr_service.py
│   ├── test_fusion_engine.py
│   ├── test_api_endpoints.py
│   └── test_load.py
├── deploy/
│   ├── apache/
│   │   ├── erp-ocr.conf             # HTTP config
│   │   └── erp-ocr-ssl.conf         # HTTPS config
│   ├── systemd/
│   │   └── ocr-service.service      # Systemd service
│   ├── docker/
│   │   ├── Dockerfile
│   │   └── docker-compose.yml
│   └── scripts/
│       └── health_check.sh          # Health monitoring
├── docs/
│   └── clients/
│       └── ArabicOCRClient.php      # PHP client
├── wsgi.py                          # WSGI entry point
├── requirements-microservice.txt    # Dependencies
└── .env.example                     # Environment template
```

**Commands:**
```bash
# Create directories
mkdir -p src/services src/middleware src/utils src/lib
mkdir -p api/routes
mkdir -p config
mkdir -p tests
mkdir -p deploy/apache deploy/systemd deploy/docker deploy/scripts
mkdir -p docs/clients
```

### Step 1.2: Create Requirements File

**File:** `requirements-microservice.txt`

```txt
# ============================================
# ERP Arabic OCR Microservice Dependencies
# ============================================

# Core OCR Engines
paddlepaddle>=2.5.0
paddleocr>=2.7.0
easyocr>=1.7.0
pytesseract>=0.3.10

# Web Framework
flask>=2.3.0
gunicorn>=21.0.0
werkzeug>=2.3.0

# LLM Integration (API-based)
openai>=1.0.0
requests>=2.31.0

# Caching
redis>=4.5.0

# Monitoring
prometheus-client>=0.17.0

# Security
python-magic>=0.4.27
python-dotenv>=1.0.0

# Image Processing
numpy>=1.24.0
Pillow>=10.0.0
opencv-python>=4.8.0

# PDF Support
pdf2image>=1.16.0
PyPDF2>=3.0.0

# Utilities
psutil>=5.9.0
python-dateutil>=2.8.0

# Testing
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-asyncio>=0.21.0
httpx>=0.24.0

# Development
black>=23.0.0
flake8>=6.0.0
mypy>=1.5.0
```

### Step 1.3: Create Settings Configuration

**File:** `config/settings.py`

```python
"""
Application Settings Configuration
Loads from environment variables with sensible defaults
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class OCRSettings:
    """OCR Engine Configuration"""
    engine_mode: str = "fusion"  # fusion, paddle, easyocr, tesseract
    paddle_lang: str = "ar"
    easyocr_langs: List[str] = field(default_factory=lambda: ["ar", "en"])
    tesseract_lang: str = "ara+eng"
    confidence_threshold: float = 0.5


@dataclass
class LLMSettings:
    """LLM Correction Service Configuration"""
    enabled: bool = True
    api_url: str = "http://localhost:8000/v1"
    model: str = "ALLaM-7B-Instruct"
    max_tokens: int = 512
    temperature: float = 0.1
    timeout: int = 30
    fallback_url: Optional[str] = "https://api.openai.com/v1"


@dataclass
class CacheSettings:
    """Redis Cache Configuration"""
    enabled: bool = True
    redis_url: str = "redis://localhost:6379/0"
    ttl: int = 3600  # 1 hour
    max_size_mb: int = 100


@dataclass
class SecuritySettings:
    """API Security Configuration"""
    api_key_hash_secret: str = "change-me-in-production"
    rate_limit_per_minute: int = 100
    max_file_size_mb: int = 50
    allowed_extensions: List[str] = field(
        default_factory=lambda: ["png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp", "pdf"]
    )


@dataclass
class ServerSettings:
    """Server Configuration"""
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    log_level: str = "INFO"


@dataclass
class Settings:
    """Main Application Settings"""
    ocr: OCRSettings = field(default_factory=OCRSettings)
    llm: LLMSettings = field(default_factory=LLMSettings)
    cache: CacheSettings = field(default_factory=CacheSettings)
    security: SecuritySettings = field(default_factory=SecuritySettings)
    server: ServerSettings = field(default_factory=ServerSettings)

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables"""
        return cls(
            ocr=OCRSettings(
                engine_mode=os.getenv("OCR_ENGINE_MODE", "fusion"),
                paddle_lang=os.getenv("OCR_PADDLE_LANG", "ar"),
                easyocr_langs=os.getenv("OCR_EASYOCR_LANGS", "ar,en").split(","),
            ),
            llm=LLMSettings(
                enabled=os.getenv("LLM_ENABLED", "true").lower() == "true",
                api_url=os.getenv("LLM_API_URL", "http://localhost:8000/v1"),
                model=os.getenv("LLM_MODEL", "ALLaM-7B-Instruct"),
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "512")),
            ),
            cache=CacheSettings(
                enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
                redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                ttl=int(os.getenv("CACHE_TTL", "3600")),
            ),
            security=SecuritySettings(
                api_key_hash_secret=os.getenv("API_KEY_HASH_SECRET", "change-me"),
                rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "100")),
            ),
            server=ServerSettings(
                host=os.getenv("OCR_SERVICE_HOST", "0.0.0.0"),
                port=int(os.getenv("OCR_SERVICE_PORT", "5000")),
                debug=os.getenv("DEBUG", "false").lower() == "true",
                log_level=os.getenv("OCR_LOG_LEVEL", "INFO"),
            ),
        )


# Global settings instance
settings = Settings.from_env()
```

### Step 1.4: Create Environment Template

**File:** `.env.example`

```bash
# ============================================
# ERP Arabic OCR Microservice Environment
# ============================================

# Server Configuration
OCR_SERVICE_HOST=0.0.0.0
OCR_SERVICE_PORT=5000
OCR_LOG_LEVEL=INFO
DEBUG=false

# OCR Engine Configuration
OCR_ENGINE_MODE=fusion
OCR_PADDLE_LANG=ar
OCR_EASYOCR_LANGS=ar,en

# LLM Configuration
LLM_ENABLED=true
LLM_API_URL=http://localhost:8000/v1
LLM_MODEL=ALLaM-7B-Instruct
LLM_MAX_TOKENS=512

# Cache Configuration
CACHE_ENABLED=true
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600

# Security Configuration
API_KEY_HASH_SECRET=your-secret-key-change-in-production
RATE_LIMIT_PER_MINUTE=100

# Gunicorn Configuration
GUNICORN_WORKERS=4
GUNICORN_THREADS=2
GUNICORN_TIMEOUT=120
```

---

## Stage 2: Core OCR Services

**Goal:** Implement multi-engine OCR processing with fusion
**Dependencies:** Stage 1 complete

### Step 2.1: Create Base OCR Result Classes

**File:** `src/services/__init__.py`

```python
"""
Core OCR Service Types and Base Classes
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class OCREngine(Enum):
    """Available OCR Engines"""
    PADDLE = "paddle"
    EASYOCR = "easyocr"
    TESSERACT = "tesseract"
    FUSION = "fusion"


class FusionStrategy(Enum):
    """Fusion Strategies"""
    CONFIDENCE_WEIGHTED = "confidence_weighted"
    MAJORITY_VOTING = "majority_voting"
    DICTIONARY_VALIDATED = "dictionary_validated"


@dataclass
class BoundingBox:
    """Text region bounding box"""
    x: int
    y: int
    width: int
    height: int
    confidence: float = 0.0


@dataclass
class OCRResult:
    """Result from a single OCR engine"""
    text: str
    confidence: float
    engine: OCREngine
    bboxes: List[BoundingBox] = field(default_factory=list)
    raw_output: Optional[Any] = None
    processing_time_ms: float = 0.0


@dataclass
class FusionResult:
    """Result from multi-engine fusion"""
    fused_text: str
    confidence: float
    individual_results: List[OCRResult] = field(default_factory=list)
    strategy: FusionStrategy = FusionStrategy.CONFIDENCE_WEIGHTED
    corrections_applied: int = 0


@dataclass
class CorrectionResult:
    """Result from text correction"""
    original: str
    corrected: str
    corrections_made: List[Dict[str, str]] = field(default_factory=list)
    confidence_delta: float = 0.0


@dataclass
class InvoiceField:
    """Extracted invoice field"""
    label: str
    label_ar: str
    value: str
    confidence: float
    valid: bool = True
    bbox: Optional[BoundingBox] = None


@dataclass
class InvoiceResult:
    """Complete invoice extraction result"""
    success: bool
    document_type: str
    confidence: float
    raw_text: str
    structured_output: str
    extracted_fields: Dict[str, InvoiceField] = field(default_factory=dict)
    line_items: List[Dict[str, Any]] = field(default_factory=list)
    processing_time_ms: float = 0.0
    engine_used: str = "fusion"
```

### Step 2.2: Implement Multi-Engine OCR Service

**File:** `src/services/ocr_microservice.py`

Key implementation points:
1. Initialize all three OCR engines (PaddleOCR, EasyOCR, Tesseract)
2. Implement `process_image()` method that runs all engines
3. Handle engine failures gracefully
4. Collect confidence scores from each engine
5. Integrate with existing `arabic_utils.py` for correction

```python
class MultiEngineArabicOCR:
    """
    Multi-Engine Arabic OCR Service

    Combines PaddleOCR, EasyOCR, and Tesseract for maximum accuracy
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._paddle = self._init_paddle_ocr()
        self._easyocr = self._init_easyocr()
        self._tesseract = self._init_tesseract()

    def process_image(self, image_data: bytes, engine_mode: str = "fusion") -> FusionResult:
        """Process image with specified engine mode"""
        # Implementation details in reference document
        pass
```

### Step 2.3: Implement Confidence-Weighted Fusion Engine

**File:** `src/services/fusion_engine.py`

Key algorithms:
1. **Confidence-Weighted:** `Σ(word × confidence) / Σ(confidence)`
2. **Majority Voting:** Democratic word selection
3. **Dictionary Validation:** Prefer valid Arabic words

```python
class FusionEngine:
    """
    Confidence-Weighted Fusion Engine for Multi-Engine OCR

    Algorithm: For each word position, select the word with
    highest weighted confidence across all engines
    """

    def __init__(self, vocabulary_path: Optional[str] = None):
        self.vocabulary = self._load_vocabulary(vocabulary_path)

    def fuse_results(
        self,
        results: List[OCRResult],
        strategy: FusionStrategy = FusionStrategy.CONFIDENCE_WEIGHTED
    ) -> FusionResult:
        """Fuse multiple OCR results into a single output"""
        pass
```

### Step 2.4: Integrate Existing Arabic Correction Pipeline

**File:** `src/services/ocr_microservice.py`

Import and use existing corrections from `src/utils/arabic_utils.py`:
- `advanced_arabic_ocr_correction()` function
- Dotted letter correction patterns
- "ال" prefix handling
- Merged word splitting

### Step 2.5: Implement LLM Correction Service

**File:** `src/services/llm_correction.py`

```python
class LLMCorrectionService:
    """
    LLM-Powered Arabic OCR Post-Correction

    Uses ALLaM-7B or compatible API for context-aware correction
    """

    SYSTEM_PROMPT = """أنت مساعد متخصص في تصحيح أخطاء OCR في النصوص العربية.
    صحح الأخطاء الإملائية والنحوية مع الحفاظ على المعنى الأصلي.
    لا تغير الأرقام أو التواريخ أو الأسماء الأجنبية."""

    def __init__(self, settings: LLMSettings):
        self.settings = settings
        self.client = self._init_client()

    def correct(self, text: str, context: str = "invoice") -> CorrectionResult:
        """Correct OCR errors using LLM"""
        pass
```

### Step 2.6: Implement Invoice Field Extractor

**File:** `src/services/invoice_extractor.py`

Extract fields using Arabic patterns:
- `الرقم الضريبي` → Tax Number
- `رقم الفاتورة` → Invoice Number
- `التاريخ` → Date
- `الاجمالي` → Total
- Line items table extraction

### Step 2.7: Implement Output Formatter

**File:** `src/services/output_formatter.py`

Format outputs:
- Invoice JSON with all fields
- General document JSON
- Batch results JSON
- Bilingual Markdown structured output

---

## Stage 3: REST API Layer

**Goal:** Create Flask REST API with all endpoints
**Dependencies:** Stage 2 complete

### Step 3.1: Create Flask Application Factory

**File:** `api/__init__.py`

```python
from flask import Flask
from config.settings import settings


def create_app() -> Flask:
    """Application Factory Pattern"""
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(settings)

    # Register blueprints
    from api.routes.ocr_v2 import ocr_v2_bp
    app.register_blueprint(ocr_v2_bp, url_prefix='/api/v2/ocr')

    # Initialize middleware
    # Initialize logging
    # Initialize metrics

    return app
```

### Step 3.2: Create WSGI Entry Point

**File:** `wsgi.py`

```python
from api import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
```

### Step 3.3: Implement Invoice Processing Endpoint

**Endpoint:** `POST /api/v2/ocr/invoice`

Request/Response format from API Reference in ERP_ARABIC_OCR_MICROSERVICE.md.

### Step 3.4: Implement Document Processing Endpoint

**Endpoint:** `POST /api/v2/ocr/document`

Handle images and PDFs with page-by-page OCR.

### Step 3.5: Implement Batch Processing Endpoint

**Endpoint:** `POST /api/v2/ocr/batch`

Parallel processing with ThreadPoolExecutor.

### Step 3.6: Implement Health Check Endpoint

**Endpoint:** `GET /api/v2/ocr/health`

Return component status and metrics.

### Step 3.7: Implement Error Handlers

Standard error responses:
- `INVALID_IMAGE` (400)
- `FILE_TOO_LARGE` (413)
- `UNSUPPORTED_FORMAT` (415)
- `OCR_FAILED` (500)
- `LLM_UNAVAILABLE` (503)
- `RATE_LIMITED` (429)

---

## Stage 4: Security Layer

**Goal:** Implement authentication, rate limiting, and file validation
**Dependencies:** Stage 3 complete

### Step 4.1: Implement API Security Middleware

**File:** `src/middleware/security.py`

Features:
- API key validation (Bearer token)
- Per-client rate limiting
- Request signing (optional)
- IP allowlist

### Step 4.2: Implement File Security Validator

**File:** `src/middleware/file_security.py`

Features:
- MIME type validation (magic bytes)
- Extension checking
- Size limits
- Filename sanitization

### Step 4.3: Integrate Security Middleware

Register in Flask app factory with `/health` exemption.

---

## Stage 5: Performance & Monitoring

**Goal:** Implement caching, resource management, and observability
**Dependencies:** Stage 3 complete

### Step 5.1: Implement Redis Cache Manager

**File:** `src/services/cache_manager.py`

Features:
- Image hash-based caching
- Configurable TTL
- Cache decorator

### Step 5.2: Implement Resource Manager

**File:** `src/services/resource_manager.py`

Features:
- Memory monitoring
- CPU throttling
- Concurrent OCR limits (semaphore)

### Step 5.3: Implement Structured Logging

**File:** `src/utils/logging_config.py`

JSON-formatted logs with:
- timestamp, level, logger
- request_id, client_id
- processing_time_ms

### Step 5.4: Implement Prometheus Metrics

**File:** `src/utils/metrics.py`

Metrics:
- `ocr_requests_total` (counter)
- `ocr_request_latency_seconds` (histogram)
- `ocr_active_requests` (gauge)
- `ocr_confidence` (histogram)

### Step 5.5: Add Metrics Endpoint

**Endpoint:** `GET /api/v2/ocr/metrics`

---

## Stage 6: Deployment Configuration

**Goal:** Create production deployment configurations
**Dependencies:** Stage 1 (can start early)

### Step 6.1: Create Gunicorn Configuration

**File:** `config/gunicorn.conf.py`

```python
import multiprocessing

bind = "127.0.0.1:5000"
workers = multiprocessing.cpu_count() * 2 + 1
threads = 2
timeout = 120
max_requests = 1000
max_requests_jitter = 50
accesslog = "/var/log/ocr_service/access.log"
errorlog = "/var/log/ocr_service/error.log"
preload_app = True
```

### Step 6.2: Create Apache Reverse Proxy Config (HTTP)

**File:** `deploy/apache/erp-ocr.conf`

Full VirtualHost configuration from ERP_ARABIC_OCR_MICROSERVICE.md.

### Step 6.3: Create Apache SSL Config (HTTPS)

**File:** `deploy/apache/erp-ocr-ssl.conf`

SSL/TLS configuration with modern security headers.

### Step 6.4: Create Systemd Service

**File:** `deploy/systemd/ocr-service.service`

Service definition for production deployment.

### Step 6.5: Create Dockerfile

**File:** `deploy/docker/Dockerfile`

Multi-stage build with Arabic fonts.

### Step 6.6: Create Docker Compose

**File:** `deploy/docker/docker-compose.yml`

OCR service + Redis with resource limits.

### Step 6.7: Create Health Check Script

**File:** `deploy/scripts/health_check.sh`

Monitoring script for external health checks.

---

## Stage 7: Client Libraries & Testing

**Goal:** Create client libraries and comprehensive tests
**Dependencies:** Stage 3 complete

### Step 7.1: Implement Python Client Library

**File:** `src/lib/erp_ocr_client.py`

Full implementation from ERP_ARABIC_OCR_MICROSERVICE.md ERP Integration Guide.

### Step 7.2: Create PHP Client Library

**File:** `docs/clients/ArabicOCRClient.php`

Full implementation from ERP Integration Guide.

### Step 7.3: Create Unit Tests - OCR Service

**File:** `tests/test_ocr_service.py`

Test cases:
- Engine initialization
- Arabic text extraction
- Bilingual processing
- Confidence calculation

### Step 7.4: Create Unit Tests - Fusion Engine

**File:** `tests/test_fusion_engine.py`

Test cases:
- Weighted fusion
- Majority voting
- Dictionary validation
- Edge cases

### Step 7.5: Create Integration Tests - API

**File:** `tests/test_api_endpoints.py`

Test cases:
- All endpoints
- Error handling
- Authentication
- Rate limiting

### Step 7.6: Create Load Tests

**File:** `tests/test_load.py`

Test cases:
- Concurrent requests
- Throughput measurement
- Memory stability
- Cache effectiveness

---

## Files to Create Summary

| Stage | File | Description | Priority |
|-------|------|-------------|----------|
| 1 | `requirements-microservice.txt` | Dependencies | High |
| 1 | `config/settings.py` | Configuration | High |
| 1 | `.env.example` | Environment template | High |
| 2 | `src/services/__init__.py` | Base classes | High |
| 2 | `src/services/ocr_microservice.py` | Multi-engine OCR | High |
| 2 | `src/services/fusion_engine.py` | Fusion algorithm | High |
| 2 | `src/services/llm_correction.py` | LLM correction | Medium |
| 2 | `src/services/invoice_extractor.py` | Field extraction | Medium |
| 2 | `src/services/output_formatter.py` | Response formatting | Medium |
| 3 | `api/__init__.py` | Flask app factory | High |
| 3 | `api/routes/ocr_v2.py` | API endpoints | High |
| 3 | `wsgi.py` | WSGI entry point | High |
| 4 | `src/middleware/security.py` | API security | Medium |
| 4 | `src/middleware/file_security.py` | File validation | Medium |
| 5 | `src/services/cache_manager.py` | Redis caching | Medium |
| 5 | `src/services/resource_manager.py` | Resource management | Low |
| 5 | `src/utils/logging_config.py` | Logging | Medium |
| 5 | `src/utils/metrics.py` | Prometheus metrics | Low |
| 6 | `config/gunicorn.conf.py` | Gunicorn config | Medium |
| 6 | `deploy/apache/erp-ocr.conf` | Apache HTTP config | Medium |
| 6 | `deploy/apache/erp-ocr-ssl.conf` | Apache SSL config | Low |
| 6 | `deploy/systemd/ocr-service.service` | Systemd service | Medium |
| 6 | `deploy/docker/Dockerfile` | Docker image | Low |
| 6 | `deploy/docker/docker-compose.yml` | Docker compose | Low |
| 6 | `deploy/scripts/health_check.sh` | Health script | Low |
| 7 | `src/lib/erp_ocr_client.py` | Python client | Medium |
| 7 | `docs/clients/ArabicOCRClient.php` | PHP client | Medium |
| 7 | `tests/test_ocr_service.py` | OCR tests | High |
| 7 | `tests/test_fusion_engine.py` | Fusion tests | High |
| 7 | `tests/test_api_endpoints.py` | API tests | High |
| 7 | `tests/test_load.py` | Load tests | Low |

**Total Files:** 31

---

## Verification Checklists

### Stage 1 Verification
- [ ] All directories created
- [ ] `pip install -r requirements-microservice.txt` succeeds
- [ ] Configuration loads from `.env`
- [ ] Settings dataclasses work correctly

### Stage 2 Verification
- [ ] PaddleOCR initializes with Arabic support
- [ ] EasyOCR initializes with Arabic+English
- [ ] Tesseract available as fallback
- [ ] Fusion produces better results than single engine
- [ ] LLM correction improves accuracy (if enabled)
- [ ] Invoice fields extracted correctly

### Stage 3 Verification
- [ ] `POST /api/v2/ocr/invoice` returns structured JSON
- [ ] `POST /api/v2/ocr/document` handles PDFs
- [ ] `POST /api/v2/ocr/batch` processes multiple files
- [ ] `GET /api/v2/ocr/health` returns component status
- [ ] Error codes match specification

### Stage 4 Verification
- [ ] Invalid API keys rejected with 401
- [ ] Rate limiting enforces per-minute limits
- [ ] Invalid files rejected with appropriate errors
- [ ] Filenames sanitized correctly

### Stage 5 Verification
- [ ] Cache hits reduce processing time
- [ ] `GET /api/v2/ocr/metrics` returns Prometheus format
- [ ] Logs are JSON-structured
- [ ] Resource limits prevent OOM

### Stage 6 Verification
- [ ] Apache proxies requests to Flask
- [ ] SSL configuration works (HTTPS)
- [ ] Systemd service starts/stops cleanly
- [ ] Docker container runs successfully
- [ ] Health check script returns correct exit codes

### Stage 7 Verification
- [ ] Python client processes invoices
- [ ] PHP client processes invoices
- [ ] Unit tests pass (>80% coverage)
- [ ] Integration tests pass
- [ ] Load test meets 2-20 docs/sec target

---

## Success Criteria

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **CER** | ≤ 0.06 | Test with `multi-language-invoice.png` |
| **WER** | ≤ 0.14 | Test with `multi-language-invoice.png` |
| **Throughput** | 2-20 docs/sec | Load test with concurrent requests |
| **Latency (p95)** | ≤ 1200ms | Prometheus histogram |
| **Test Coverage** | ≥ 80% | `pytest --cov` |
| **API Uptime** | 99.9% | Health check monitoring |

### Performance Expectations by Engine Mode

| Mode | CER | Throughput | Use Case |
|------|-----|------------|----------|
| `paddle` | 0.12 | 15/sec | High speed, good accuracy |
| `easyocr` | 0.10 | 10/sec | Balanced |
| `fusion` | 0.08 | 8/sec | Best accuracy without LLM |
| `fusion+llm` | 0.06 | 2/sec | Maximum accuracy |

---

## Quick Start Commands

```bash
# 1. Install dependencies
pip install -r requirements-microservice.txt

# 2. Copy environment file
cp .env.example .env

# 3. Run development server
python wsgi.py

# 4. Run tests
pytest tests/ -v --cov=src

# 5. Run with Gunicorn (production)
gunicorn --config config/gunicorn.conf.py wsgi:app

# 6. Build Docker image
docker build -f deploy/docker/Dockerfile -t arabic-ocr-service .

# 7. Run with Docker Compose
docker-compose -f deploy/docker/docker-compose.yml up -d
```

---

## References

- [ERP Arabic OCR Microservice Guide](./ERP_ARABIC_OCR_MICROSERVICE.md)
- [Arabic OCR Advanced Solutions](./ARABIC_OCR_ADVANCED_SOLUTIONS.md)
- [Arabic OCR Solutions](./ARABIC_OCR_SOLUTIONS.md)

---

*Document Version: 1.0 | Created: January 2026 | Author: Claude Code*
