<?php
/**
 * ERP Arabic OCR Microservice - PHP Client Library
 * =================================================
 *
 * A PHP client for integrating with the OCR microservice.
 *
 * Requirements:
 * - PHP 7.4+
 * - cURL extension
 * - JSON extension
 *
 * Usage:
 *   $client = new ArabicOCRClient('http://localhost:8000', 'your-api-key');
 *
 *   // Process invoice
 *   $result = $client->processInvoice('/path/to/invoice.png');
 *   echo $result['text'];
 *   echo $result['invoice_data']['tax_number']['value'];
 *
 *   // Process document
 *   $result = $client->processDocument('/path/to/document.pdf');
 *   echo $result['text'];
 *
 *   // Batch processing
 *   $results = $client->processBatch(['/path/to/file1.png', '/path/to/file2.png']);
 *   foreach ($results['results'] as $r) {
 *       echo $r['text'];
 *   }
 *
 * @package ERPOCRClient
 * @version 2.0.0
 * @author ERP Team
 */

namespace ERP\OCR;

/**
 * Exception classes
 */
class OCRException extends \Exception {}
class OCRConnectionException extends OCRException {}
class OCRAuthenticationException extends OCRException {}
class OCRRateLimitException extends OCRException {}
class OCRValidationException extends OCRException {}
class OCRProcessingException extends OCRException {}

/**
 * Invoice field data class
 */
class InvoiceField
{
    public string $fieldName;
    public string $value;
    public float $confidence;
    public bool $validated;

    public function __construct(array $data)
    {
        $this->fieldName = $data['field_name'] ?? '';
        $this->value = $data['value'] ?? '';
        $this->confidence = $data['confidence'] ?? 0.0;
        $this->validated = $data['validated'] ?? false;
    }

    public function toArray(): array
    {
        return [
            'field_name' => $this->fieldName,
            'value' => $this->value,
            'confidence' => $this->confidence,
            'validated' => $this->validated
        ];
    }
}

/**
 * Invoice data class
 */
class InvoiceData
{
    public ?InvoiceField $taxNumber = null;
    public ?InvoiceField $invoiceNumber = null;
    public ?InvoiceField $date = null;
    public ?InvoiceField $vendorName = null;
    public ?InvoiceField $customerName = null;
    public ?InvoiceField $subtotal = null;
    public ?InvoiceField $taxAmount = null;
    public ?InvoiceField $total = null;
    public array $lineItems = [];

    public function __construct(array $data)
    {
        if (isset($data['tax_number'])) {
            $this->taxNumber = new InvoiceField($data['tax_number']);
        }
        if (isset($data['invoice_number'])) {
            $this->invoiceNumber = new InvoiceField($data['invoice_number']);
        }
        if (isset($data['date'])) {
            $this->date = new InvoiceField($data['date']);
        }
        if (isset($data['vendor_name'])) {
            $this->vendorName = new InvoiceField($data['vendor_name']);
        }
        if (isset($data['customer_name'])) {
            $this->customerName = new InvoiceField($data['customer_name']);
        }
        if (isset($data['subtotal'])) {
            $this->subtotal = new InvoiceField($data['subtotal']);
        }
        if (isset($data['tax_amount'])) {
            $this->taxAmount = new InvoiceField($data['tax_amount']);
        }
        if (isset($data['total'])) {
            $this->total = new InvoiceField($data['total']);
        }
        $this->lineItems = $data['line_items'] ?? [];
    }

    public function toArray(): array
    {
        return [
            'tax_number' => $this->taxNumber?->toArray(),
            'invoice_number' => $this->invoiceNumber?->toArray(),
            'date' => $this->date?->toArray(),
            'vendor_name' => $this->vendorName?->toArray(),
            'customer_name' => $this->customerName?->toArray(),
            'subtotal' => $this->subtotal?->toArray(),
            'tax_amount' => $this->taxAmount?->toArray(),
            'total' => $this->total?->toArray(),
            'line_items' => $this->lineItems
        ];
    }
}

/**
 * OCR Result class
 */
class OCRResult
{
    public bool $success;
    public string $text;
    public float $confidence;
    public string $documentType;
    public float $processingTimeMs;
    public string $requestId;
    public string $timestamp;
    public ?InvoiceData $invoiceData = null;
    public array $errors = [];
    public array $warnings = [];
    public array $rawResponse = [];

    public function __construct(array $response, string $documentType = 'document')
    {
        $this->success = $response['success'] ?? false;
        $this->text = $response['text'] ?? '';
        $this->confidence = $response['confidence'] ?? 0.0;
        $this->documentType = $documentType;
        $this->processingTimeMs = $response['processing_time_ms'] ?? 0.0;
        $this->requestId = $response['request_id'] ?? '';
        $this->timestamp = $response['timestamp'] ?? date('c');
        $this->errors = $response['errors'] ?? [];
        $this->warnings = $response['warnings'] ?? [];
        $this->rawResponse = $response;

        if ($documentType === 'invoice' && isset($response['invoice_data'])) {
            $this->invoiceData = new InvoiceData($response['invoice_data']);
        }
    }

    public function isSuccess(): bool
    {
        return $this->success;
    }

    public function toArray(): array
    {
        return [
            'success' => $this->success,
            'text' => $this->text,
            'confidence' => $this->confidence,
            'document_type' => $this->documentType,
            'processing_time_ms' => $this->processingTimeMs,
            'request_id' => $this->requestId,
            'timestamp' => $this->timestamp,
            'invoice_data' => $this->invoiceData?->toArray(),
            'errors' => $this->errors,
            'warnings' => $this->warnings
        ];
    }
}

/**
 * Health status class
 */
class HealthStatus
{
    public string $status;
    public string $version;
    public int $uptimeSeconds;
    public array $components;
    public string $timestamp;

    public function __construct(array $response)
    {
        $this->status = $response['status'] ?? 'unknown';
        $this->version = $response['version'] ?? 'unknown';
        $this->uptimeSeconds = $response['uptime_seconds'] ?? 0;
        $this->components = $response['components'] ?? [];
        $this->timestamp = $response['timestamp'] ?? date('c');
    }

    public function isHealthy(): bool
    {
        return $this->status === 'healthy';
    }

    public function isDegraded(): bool
    {
        return $this->status === 'degraded';
    }

    public function isAvailable(): bool
    {
        return in_array($this->status, ['healthy', 'degraded']);
    }
}

/**
 * Arabic OCR Client
 *
 * Main client class for interacting with the OCR microservice.
 */
class ArabicOCRClient
{
    private string $baseUrl;
    private string $apiKey;
    private int $timeout;
    private bool $verifySsl;

    // Supported file extensions
    private const SUPPORTED_EXTENSIONS = ['png', 'jpg', 'jpeg', 'pdf', 'tiff', 'tif', 'bmp'];

    /**
     * Create a new OCR client.
     *
     * @param string $baseUrl Base URL of the OCR service
     * @param string $apiKey API key for authentication
     * @param int $timeout Request timeout in seconds
     * @param bool $verifySsl Whether to verify SSL certificates
     */
    public function __construct(
        string $baseUrl,
        string $apiKey,
        int $timeout = 120,
        bool $verifySsl = true
    ) {
        $this->baseUrl = rtrim($baseUrl, '/');
        $this->apiKey = $apiKey;
        $this->timeout = $timeout;
        $this->verifySsl = $verifySsl;
    }

    /**
     * Process invoice image and extract structured data.
     *
     * @param string $filePath Path to invoice image
     * @param string $engineMode OCR engine mode (fusion, paddle, easyocr)
     * @param bool $enableLlm Enable LLM post-correction
     * @param bool $extractFields Extract invoice fields
     * @return OCRResult Processing result
     * @throws OCRException On error
     */
    public function processInvoice(
        string $filePath,
        string $engineMode = 'fusion',
        bool $enableLlm = true,
        bool $extractFields = true
    ): OCRResult {
        $this->validateFile($filePath);

        $response = $this->uploadAndProcess('invoice', $filePath, [
            'engine_mode' => $engineMode,
            'enable_llm' => $enableLlm ? 'true' : 'false',
            'extract_fields' => $extractFields ? 'true' : 'false'
        ]);

        return new OCRResult($response, 'invoice');
    }

    /**
     * Process general document (image or PDF).
     *
     * @param string $filePath Path to document
     * @param string $engineMode OCR engine mode
     * @return OCRResult Processing result
     * @throws OCRException On error
     */
    public function processDocument(
        string $filePath,
        string $engineMode = 'fusion'
    ): OCRResult {
        $this->validateFile($filePath);

        $response = $this->uploadAndProcess('document', $filePath, [
            'engine_mode' => $engineMode
        ]);

        return new OCRResult($response, 'document');
    }

    /**
     * Process multiple files in batch.
     *
     * @param array $filePaths Array of file paths
     * @param string $engineMode OCR engine mode
     * @return array Batch processing result
     * @throws OCRException On error
     */
    public function processBatch(
        array $filePaths,
        string $engineMode = 'fusion'
    ): array {
        // Validate all files
        $validFiles = [];
        foreach ($filePaths as $path) {
            try {
                $this->validateFile($path);
                $validFiles[] = $path;
            } catch (OCRValidationException $e) {
                // Skip invalid files
            }
        }

        if (empty($validFiles)) {
            return [
                'success' => false,
                'total_documents' => count($filePaths),
                'successful' => 0,
                'failed' => count($filePaths),
                'results' => []
            ];
        }

        $response = $this->uploadBatch($validFiles, $engineMode);
        return $response;
    }

    /**
     * Get service health status.
     *
     * @return HealthStatus Health status
     */
    public function getHealth(): HealthStatus
    {
        try {
            $response = $this->request('GET', 'health', [], 10);
            return new HealthStatus($response);
        } catch (\Exception $e) {
            return new HealthStatus([
                'status' => 'unreachable',
                'version' => 'unknown',
                'uptime_seconds' => 0,
                'components' => [],
                'timestamp' => date('c')
            ]);
        }
    }

    /**
     * Quick health check.
     *
     * @return bool True if service is available
     */
    public function isHealthy(): bool
    {
        return $this->getHealth()->isAvailable();
    }

    /**
     * Get Prometheus metrics.
     *
     * @return string Prometheus format metrics
     */
    public function getMetrics(): string
    {
        try {
            $ch = curl_init($this->getUrl('metrics'));
            curl_setopt_array($ch, [
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_TIMEOUT => 10,
                CURLOPT_HTTPHEADER => $this->getHeaders()
            ]);

            $response = curl_exec($ch);
            $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
            curl_close($ch);

            return $httpCode === 200 ? $response : '';
        } catch (\Exception $e) {
            return '';
        }
    }

    // =========================================================================
    // Private Methods
    // =========================================================================

    /**
     * Validate file exists and has supported extension.
     *
     * @param string $filePath File path to validate
     * @throws OCRValidationException If file is invalid
     */
    private function validateFile(string $filePath): void
    {
        if (!file_exists($filePath)) {
            throw new OCRValidationException("File not found: {$filePath}");
        }

        if (!is_readable($filePath)) {
            throw new OCRValidationException("File not readable: {$filePath}");
        }

        $extension = strtolower(pathinfo($filePath, PATHINFO_EXTENSION));
        if (!in_array($extension, self::SUPPORTED_EXTENSIONS)) {
            throw new OCRValidationException(
                "Unsupported file type: .{$extension}. " .
                "Supported: " . implode(', ', self::SUPPORTED_EXTENSIONS)
            );
        }
    }

    /**
     * Upload file and process.
     *
     * @param string $endpoint API endpoint
     * @param string $filePath File to upload
     * @param array $data Additional form data
     * @return array API response
     * @throws OCRException On error
     */
    private function uploadAndProcess(
        string $endpoint,
        string $filePath,
        array $data = []
    ): array {
        $ch = curl_init($this->getUrl($endpoint));

        $postData = $data;
        $postData['file'] = new \CURLFile(
            $filePath,
            mime_content_type($filePath) ?: 'application/octet-stream',
            basename($filePath)
        );

        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => $postData,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => $this->timeout,
            CURLOPT_HTTPHEADER => $this->getHeaders(),
            CURLOPT_SSL_VERIFYPEER => $this->verifySsl
        ]);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error = curl_error($ch);
        curl_close($ch);

        if ($error) {
            throw new OCRConnectionException("Connection failed: {$error}");
        }

        return $this->handleResponse($response, $httpCode);
    }

    /**
     * Upload multiple files for batch processing.
     *
     * @param array $filePaths Files to upload
     * @param string $engineMode OCR engine mode
     * @return array API response
     * @throws OCRException On error
     */
    private function uploadBatch(array $filePaths, string $engineMode): array
    {
        $ch = curl_init($this->getUrl('batch'));

        $postData = ['engine_mode' => $engineMode];
        foreach ($filePaths as $i => $filePath) {
            $postData["files[{$i}]"] = new \CURLFile(
                $filePath,
                mime_content_type($filePath) ?: 'application/octet-stream',
                basename($filePath)
            );
        }

        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => $postData,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => $this->timeout * count($filePaths),
            CURLOPT_HTTPHEADER => $this->getHeaders(),
            CURLOPT_SSL_VERIFYPEER => $this->verifySsl
        ]);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error = curl_error($ch);
        curl_close($ch);

        if ($error) {
            throw new OCRConnectionException("Connection failed: {$error}");
        }

        return $this->handleResponse($response, $httpCode);
    }

    /**
     * Make HTTP request.
     *
     * @param string $method HTTP method
     * @param string $endpoint API endpoint
     * @param array $data Request data
     * @param int|null $timeout Custom timeout
     * @return array API response
     * @throws OCRException On error
     */
    private function request(
        string $method,
        string $endpoint,
        array $data = [],
        ?int $timeout = null
    ): array {
        $ch = curl_init($this->getUrl($endpoint));

        $options = [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => $timeout ?? $this->timeout,
            CURLOPT_HTTPHEADER => $this->getHeaders(),
            CURLOPT_SSL_VERIFYPEER => $this->verifySsl
        ];

        if ($method === 'POST') {
            $options[CURLOPT_POST] = true;
            $options[CURLOPT_POSTFIELDS] = json_encode($data);
            $options[CURLOPT_HTTPHEADER][] = 'Content-Type: application/json';
        }

        curl_setopt_array($ch, $options);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error = curl_error($ch);
        curl_close($ch);

        if ($error) {
            throw new OCRConnectionException("Connection failed: {$error}");
        }

        return $this->handleResponse($response, $httpCode);
    }

    /**
     * Handle API response.
     *
     * @param string $response Raw response
     * @param int $httpCode HTTP status code
     * @return array Decoded response
     * @throws OCRException On error
     */
    private function handleResponse(string $response, int $httpCode): array
    {
        $data = json_decode($response, true);

        if ($httpCode === 200) {
            return $data ?? [];
        }

        $errorMessage = $data['error']['message'] ?? 'Unknown error';

        switch ($httpCode) {
            case 401:
                throw new OCRAuthenticationException("Authentication failed: {$errorMessage}");
            case 429:
                throw new OCRRateLimitException("Rate limit exceeded: {$errorMessage}");
            case 400:
                throw new OCRValidationException("Validation error: {$errorMessage}");
            default:
                if ($httpCode >= 500) {
                    throw new OCRProcessingException("Server error: {$errorMessage}");
                }
                throw new OCRException("Request failed ({$httpCode}): {$errorMessage}");
        }
    }

    /**
     * Build full URL for endpoint.
     *
     * @param string $endpoint Endpoint path
     * @return string Full URL
     */
    private function getUrl(string $endpoint): string
    {
        return $this->baseUrl . '/api/v2/ocr/' . ltrim($endpoint, '/');
    }

    /**
     * Get request headers.
     *
     * @return array Headers
     */
    private function getHeaders(): array
    {
        return [
            "Authorization: Bearer {$this->apiKey}",
            "User-Agent: ArabicOCRClient-PHP/2.0.0"
        ];
    }
}

// =========================================================================
// Factory Function
// =========================================================================

/**
 * Create OCR client from environment or parameters.
 *
 * Environment variables:
 * - OCR_SERVICE_URL: Base URL
 * - OCR_API_KEY: API key
 *
 * @param string|null $baseUrl Base URL (overrides env)
 * @param string|null $apiKey API key (overrides env)
 * @return ArabicOCRClient
 * @throws \InvalidArgumentException If API key is missing
 */
function createClient(?string $baseUrl = null, ?string $apiKey = null): ArabicOCRClient
{
    $url = $baseUrl ?? getenv('OCR_SERVICE_URL') ?: 'http://localhost:8000';
    $key = $apiKey ?? getenv('OCR_API_KEY') ?: '';

    if (empty($key)) {
        throw new \InvalidArgumentException(
            'API key required. Set OCR_API_KEY environment variable or pass apiKey parameter.'
        );
    }

    return new ArabicOCRClient($url, $key);
}
