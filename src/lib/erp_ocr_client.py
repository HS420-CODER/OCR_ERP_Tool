"""
ERP Arabic OCR Microservice - Python Client Library
====================================================
A Python client for integrating with the OCR microservice.

Usage:
    from erp_ocr_client import ERPOCRClient

    client = ERPOCRClient(
        base_url="http://localhost:8000",
        api_key="your-api-key"
    )

    # Process invoice
    result = client.process_invoice("invoice.png")
    print(result.text)
    print(result.invoice_data.tax_number)

    # Process document
    result = client.process_document("document.pdf")
    print(result.text)

    # Batch processing
    results = client.process_batch(["file1.png", "file2.png"])
    for r in results:
        print(r.text)
"""

import os
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, BinaryIO
from pathlib import Path
from datetime import datetime
from enum import Enum

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


# ==============================================================================
# Data Classes
# ==============================================================================

class DocumentType(Enum):
    """Document types."""
    INVOICE = "invoice"
    DOCUMENT = "document"
    RECEIPT = "receipt"


@dataclass
class InvoiceField:
    """Single extracted invoice field."""
    field_name: str
    value: str
    confidence: float
    validated: bool = False

    @classmethod
    def from_dict(cls, data: Dict) -> "InvoiceField":
        return cls(
            field_name=data.get("field_name", ""),
            value=data.get("value", ""),
            confidence=data.get("confidence", 0.0),
            validated=data.get("validated", False)
        )


@dataclass
class InvoiceData:
    """Structured invoice data."""
    tax_number: Optional[InvoiceField] = None
    invoice_number: Optional[InvoiceField] = None
    date: Optional[InvoiceField] = None
    vendor_name: Optional[InvoiceField] = None
    customer_name: Optional[InvoiceField] = None
    subtotal: Optional[InvoiceField] = None
    tax_amount: Optional[InvoiceField] = None
    total: Optional[InvoiceField] = None
    line_items: List[Dict] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict) -> "InvoiceData":
        if not data:
            return cls()

        return cls(
            tax_number=InvoiceField.from_dict(data["tax_number"]) if data.get("tax_number") else None,
            invoice_number=InvoiceField.from_dict(data["invoice_number"]) if data.get("invoice_number") else None,
            date=InvoiceField.from_dict(data["date"]) if data.get("date") else None,
            vendor_name=InvoiceField.from_dict(data["vendor_name"]) if data.get("vendor_name") else None,
            customer_name=InvoiceField.from_dict(data["customer_name"]) if data.get("customer_name") else None,
            subtotal=InvoiceField.from_dict(data["subtotal"]) if data.get("subtotal") else None,
            tax_amount=InvoiceField.from_dict(data["tax_amount"]) if data.get("tax_amount") else None,
            total=InvoiceField.from_dict(data["total"]) if data.get("total") else None,
            line_items=data.get("line_items", [])
        )


@dataclass
class OCRResult:
    """OCR processing result."""
    success: bool
    text: str
    confidence: float
    document_type: DocumentType
    processing_time_ms: float
    request_id: str
    timestamp: str
    invoice_data: Optional[InvoiceData] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    raw_response: Dict = field(default_factory=dict)

    @classmethod
    def from_response(cls, response: Dict, doc_type: DocumentType) -> "OCRResult":
        """Create OCRResult from API response."""
        invoice_data = None
        if doc_type == DocumentType.INVOICE and response.get("invoice_data"):
            invoice_data = InvoiceData.from_dict(response["invoice_data"])

        return cls(
            success=response.get("success", False),
            text=response.get("text", ""),
            confidence=response.get("confidence", 0.0),
            document_type=doc_type,
            processing_time_ms=response.get("processing_time_ms", 0.0),
            request_id=response.get("request_id", ""),
            timestamp=response.get("timestamp", datetime.utcnow().isoformat()),
            invoice_data=invoice_data,
            errors=response.get("errors", []),
            warnings=response.get("warnings", []),
            raw_response=response
        )

    @classmethod
    def error(cls, message: str, doc_type: DocumentType = DocumentType.DOCUMENT) -> "OCRResult":
        """Create error result."""
        return cls(
            success=False,
            text="",
            confidence=0.0,
            document_type=doc_type,
            processing_time_ms=0.0,
            request_id="",
            timestamp=datetime.utcnow().isoformat(),
            errors=[message]
        )


@dataclass
class BatchResult:
    """Batch processing result."""
    success: bool
    total_documents: int
    successful: int
    failed: int
    results: List[OCRResult]
    processing_time_ms: float
    batch_id: str

    @classmethod
    def from_response(cls, response: Dict) -> "BatchResult":
        """Create BatchResult from API response."""
        results = []
        for r in response.get("results", []):
            results.append(OCRResult.from_response(r, DocumentType.DOCUMENT))

        return cls(
            success=response.get("success", False),
            total_documents=response.get("total_documents", 0),
            successful=response.get("successful", 0),
            failed=response.get("failed", 0),
            results=results,
            processing_time_ms=response.get("processing_time_ms", 0.0),
            batch_id=response.get("batch_id", "")
        )


@dataclass
class HealthStatus:
    """Service health status."""
    status: str
    version: str
    uptime_seconds: int
    components: Dict[str, Dict]
    timestamp: str

    @property
    def is_healthy(self) -> bool:
        return self.status == "healthy"

    @property
    def is_degraded(self) -> bool:
        return self.status == "degraded"

    @classmethod
    def from_response(cls, response: Dict) -> "HealthStatus":
        return cls(
            status=response.get("status", "unknown"),
            version=response.get("version", "unknown"),
            uptime_seconds=response.get("uptime_seconds", 0),
            components=response.get("components", {}),
            timestamp=response.get("timestamp", datetime.utcnow().isoformat())
        )


# ==============================================================================
# Client Exceptions
# ==============================================================================

class OCRClientError(Exception):
    """Base exception for OCR client errors."""
    pass


class OCRConnectionError(OCRClientError):
    """Connection error."""
    pass


class OCRAuthenticationError(OCRClientError):
    """Authentication error (401)."""
    pass


class OCRRateLimitError(OCRClientError):
    """Rate limit exceeded (429)."""
    pass


class OCRProcessingError(OCRClientError):
    """OCR processing error (500)."""
    pass


class OCRValidationError(OCRClientError):
    """File validation error (400)."""
    pass


# ==============================================================================
# Main Client Class
# ==============================================================================

class ERPOCRClient:
    """
    Python client for the ERP Arabic OCR Microservice.

    Features:
    - Automatic retry with exponential backoff
    - Connection pooling
    - File validation
    - Structured result parsing
    - Health check support

    Example:
        client = ERPOCRClient("http://localhost:8000", "api-key")
        result = client.process_invoice("invoice.png")
        print(result.invoice_data.tax_number.value)
    """

    # Default configuration
    DEFAULT_TIMEOUT = 120
    DEFAULT_RETRIES = 3
    DEFAULT_BACKOFF = 0.5

    # Supported file extensions
    SUPPORTED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.pdf', '.tiff', '.tif', '.bmp'}

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF,
        verify_ssl: bool = True
    ):
        """
        Initialize OCR client.

        Args:
            base_url: Base URL of OCR service (e.g., "http://localhost:8000")
            api_key: API key for authentication
            timeout: Request timeout in seconds
            retries: Number of retries for failed requests
            backoff_factor: Exponential backoff factor
            verify_ssl: Verify SSL certificates
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        # Setup session with retry logic
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "ERPOCRClient/2.0.0"
        })

        # Configure retries
        retry_strategy = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.info(f"ERPOCRClient initialized: {base_url}")

    def _get_url(self, endpoint: str) -> str:
        """Build full URL for endpoint."""
        return f"{self.base_url}/api/v2/ocr/{endpoint.lstrip('/')}"

    def _validate_file(self, file_path: Union[str, Path]) -> Path:
        """Validate file exists and has supported extension."""
        path = Path(file_path)

        if not path.exists():
            raise OCRValidationError(f"File not found: {path}")

        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise OCRValidationError(
                f"Unsupported file type: {path.suffix}. "
                f"Supported: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )

        return path

    def _handle_response(self, response: requests.Response) -> Dict:
        """Handle API response and raise appropriate exceptions."""
        if response.status_code == 200:
            return response.json()

        # Handle error responses
        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", "Unknown error")
        except:
            error_message = response.text or "Unknown error"

        if response.status_code == 401:
            raise OCRAuthenticationError(f"Authentication failed: {error_message}")
        elif response.status_code == 429:
            raise OCRRateLimitError(f"Rate limit exceeded: {error_message}")
        elif response.status_code == 400:
            raise OCRValidationError(f"Validation error: {error_message}")
        elif response.status_code >= 500:
            raise OCRProcessingError(f"Server error: {error_message}")
        else:
            raise OCRClientError(f"Request failed ({response.status_code}): {error_message}")

    def _upload_file(
        self,
        endpoint: str,
        file_path: Union[str, Path],
        extra_data: Dict = None
    ) -> Dict:
        """Upload file to endpoint."""
        path = self._validate_file(file_path)

        with open(path, 'rb') as f:
            files = {'file': (path.name, f, 'application/octet-stream')}
            data = extra_data or {}

            try:
                response = self.session.post(
                    self._get_url(endpoint),
                    files=files,
                    data=data,
                    timeout=self.timeout,
                    verify=self.verify_ssl
                )
                return self._handle_response(response)
            except requests.exceptions.ConnectionError as e:
                raise OCRConnectionError(f"Connection failed: {e}")
            except requests.exceptions.Timeout:
                raise OCRConnectionError(f"Request timed out after {self.timeout}s")

    # ==========================================================================
    # Public API Methods
    # ==========================================================================

    def process_invoice(
        self,
        file_path: Union[str, Path],
        engine_mode: str = "fusion",
        enable_llm: bool = True,
        extract_fields: bool = True
    ) -> OCRResult:
        """
        Process invoice image and extract structured data.

        Args:
            file_path: Path to invoice image
            engine_mode: OCR engine mode (fusion, paddle, easyocr, tesseract)
            enable_llm: Enable LLM post-correction
            extract_fields: Extract invoice fields

        Returns:
            OCRResult with invoice data

        Example:
            result = client.process_invoice("invoice.png")
            if result.success:
                print(f"Tax Number: {result.invoice_data.tax_number.value}")
                print(f"Total: {result.invoice_data.total.value}")
        """
        logger.info(f"Processing invoice: {file_path}")

        try:
            response = self._upload_file(
                "invoice",
                file_path,
                {
                    "engine_mode": engine_mode,
                    "enable_llm": str(enable_llm).lower(),
                    "extract_fields": str(extract_fields).lower()
                }
            )
            return OCRResult.from_response(response, DocumentType.INVOICE)
        except OCRClientError as e:
            logger.error(f"Invoice processing failed: {e}")
            return OCRResult.error(str(e), DocumentType.INVOICE)

    def process_document(
        self,
        file_path: Union[str, Path],
        engine_mode: str = "fusion"
    ) -> OCRResult:
        """
        Process general document (image or PDF).

        Args:
            file_path: Path to document file
            engine_mode: OCR engine mode

        Returns:
            OCRResult with extracted text

        Example:
            result = client.process_document("contract.pdf")
            if result.success:
                print(result.text)
        """
        logger.info(f"Processing document: {file_path}")

        try:
            response = self._upload_file(
                "document",
                file_path,
                {"engine_mode": engine_mode}
            )
            return OCRResult.from_response(response, DocumentType.DOCUMENT)
        except OCRClientError as e:
            logger.error(f"Document processing failed: {e}")
            return OCRResult.error(str(e), DocumentType.DOCUMENT)

    def process_batch(
        self,
        file_paths: List[Union[str, Path]],
        engine_mode: str = "fusion"
    ) -> BatchResult:
        """
        Process multiple files in batch.

        Args:
            file_paths: List of file paths to process
            engine_mode: OCR engine mode

        Returns:
            BatchResult with individual results

        Example:
            results = client.process_batch(["file1.png", "file2.png"])
            for r in results.results:
                print(f"{r.request_id}: {r.confidence}")
        """
        logger.info(f"Processing batch of {len(file_paths)} files")

        # Validate all files first
        validated_paths = []
        for path in file_paths:
            try:
                validated_paths.append(self._validate_file(path))
            except OCRValidationError as e:
                logger.warning(f"Skipping invalid file: {e}")

        if not validated_paths:
            return BatchResult(
                success=False,
                total_documents=len(file_paths),
                successful=0,
                failed=len(file_paths),
                results=[],
                processing_time_ms=0,
                batch_id=""
            )

        # Prepare multipart files
        files = []
        for path in validated_paths:
            files.append(('files', (path.name, open(path, 'rb'), 'application/octet-stream')))

        try:
            response = self.session.post(
                self._get_url("batch"),
                files=files,
                data={"engine_mode": engine_mode},
                timeout=self.timeout * len(validated_paths),
                verify=self.verify_ssl
            )

            # Close file handles
            for _, (_, f, _) in files:
                f.close()

            return BatchResult.from_response(self._handle_response(response))

        except requests.exceptions.ConnectionError as e:
            raise OCRConnectionError(f"Connection failed: {e}")
        except requests.exceptions.Timeout:
            raise OCRConnectionError("Batch request timed out")
        finally:
            # Ensure files are closed
            for _, (_, f, _) in files:
                if not f.closed:
                    f.close()

    def health_check(self) -> HealthStatus:
        """
        Get service health status.

        Returns:
            HealthStatus with component details

        Example:
            health = client.health_check()
            if health.is_healthy:
                print(f"Service OK, uptime: {health.uptime_seconds}s")
        """
        try:
            response = self.session.get(
                self._get_url("health"),
                timeout=10,
                verify=self.verify_ssl
            )
            return HealthStatus.from_response(self._handle_response(response))
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthStatus(
                status="unreachable",
                version="unknown",
                uptime_seconds=0,
                components={},
                timestamp=datetime.utcnow().isoformat()
            )

    def is_healthy(self) -> bool:
        """
        Quick health check.

        Returns:
            True if service is healthy or degraded
        """
        try:
            health = self.health_check()
            return health.status in ("healthy", "degraded")
        except:
            return False

    def get_metrics(self) -> str:
        """
        Get Prometheus metrics.

        Returns:
            Prometheus format metrics string
        """
        try:
            response = self.session.get(
                self._get_url("metrics"),
                timeout=10,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return ""

    def close(self):
        """Close the client session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# ==============================================================================
# Convenience Functions
# ==============================================================================

def create_client(
    base_url: str = None,
    api_key: str = None
) -> ERPOCRClient:
    """
    Create OCR client from environment variables or parameters.

    Environment variables:
    - OCR_SERVICE_URL: Base URL
    - OCR_API_KEY: API key

    Args:
        base_url: Base URL (overrides env)
        api_key: API key (overrides env)

    Returns:
        Configured ERPOCRClient
    """
    url = base_url or os.getenv("OCR_SERVICE_URL", "http://localhost:8000")
    key = api_key or os.getenv("OCR_API_KEY", "")

    if not key:
        raise ValueError("API key required. Set OCR_API_KEY or pass api_key parameter.")

    return ERPOCRClient(url, key)


# ==============================================================================
# Export
# ==============================================================================

__all__ = [
    # Main client
    "ERPOCRClient",
    "create_client",
    # Data classes
    "OCRResult",
    "BatchResult",
    "InvoiceData",
    "InvoiceField",
    "HealthStatus",
    "DocumentType",
    # Exceptions
    "OCRClientError",
    "OCRConnectionError",
    "OCRAuthenticationError",
    "OCRRateLimitError",
    "OCRProcessingError",
    "OCRValidationError"
]
