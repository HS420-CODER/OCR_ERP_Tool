#!/bin/bash
# ==============================================================================
# ERP Arabic OCR Microservice - Health Check Script
# ==============================================================================
#
# This script checks the health of the OCR microservice.
# Designed for use with monitoring systems (Nagios, Prometheus, cron).
#
# Exit codes:
#   0 - Service is healthy
#   1 - Service is degraded (some components unavailable)
#   2 - Service is unhealthy or unreachable
#
# Usage:
#   ./health_check.sh                    # Check localhost:8000
#   ./health_check.sh http://ocr.local   # Check specific URL
#   ./health_check.sh --verbose          # Verbose output
#   ./health_check.sh --json             # Output raw JSON
#
# Cron example (check every 5 minutes):
#   */5 * * * * /path/to/health_check.sh >> /var/log/ocr-health.log 2>&1
#
# ==============================================================================

set -euo pipefail

# Configuration
DEFAULT_URL="http://127.0.0.1:8000"
HEALTH_ENDPOINT="/api/v2/ocr/health"
TIMEOUT=10
VERBOSE=false
JSON_OUTPUT=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ==============================================================================
# Functions
# ==============================================================================

usage() {
    echo "Usage: $0 [OPTIONS] [URL]"
    echo ""
    echo "Options:"
    echo "  -v, --verbose    Verbose output"
    echo "  -j, --json       Output raw JSON response"
    echo "  -t, --timeout N  Request timeout in seconds (default: 10)"
    echo "  -h, --help       Show this help message"
    echo ""
    echo "Arguments:"
    echo "  URL              Base URL of the OCR service (default: http://127.0.0.1:8000)"
    echo ""
    echo "Exit codes:"
    echo "  0 - Healthy"
    echo "  1 - Degraded"
    echo "  2 - Unhealthy/Unreachable"
}

log_info() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${GREEN}[INFO]${NC} $1"
    fi
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    if ! command -v curl &> /dev/null; then
        log_error "curl is required but not installed"
        exit 2
    fi

    if ! command -v jq &> /dev/null; then
        log_warn "jq not installed - JSON parsing will be limited"
        HAS_JQ=false
    else
        HAS_JQ=true
    fi
}

# ==============================================================================
# Parse Arguments
# ==============================================================================

BASE_URL="$DEFAULT_URL"

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -j|--json)
            JSON_OUTPUT=true
            shift
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            log_error "Unknown option: $1"
            usage
            exit 2
            ;;
        *)
            BASE_URL="$1"
            shift
            ;;
    esac
done

# ==============================================================================
# Main Health Check
# ==============================================================================

check_dependencies

HEALTH_URL="${BASE_URL}${HEALTH_ENDPOINT}"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

log_info "Checking health at: $HEALTH_URL"
log_info "Timestamp: $TIMESTAMP"

# Make health check request
HTTP_RESPONSE=$(curl --silent --write-out "HTTPSTATUS:%{http_code}" \
    --connect-timeout "$TIMEOUT" \
    --max-time "$TIMEOUT" \
    "$HEALTH_URL" 2>/dev/null) || {
    log_error "Failed to connect to $HEALTH_URL"
    echo "CRITICAL: OCR service unreachable at $BASE_URL"
    exit 2
}

# Extract body and status code
HTTP_BODY=$(echo "$HTTP_RESPONSE" | sed -e 's/HTTPSTATUS\:.*//g')
HTTP_STATUS=$(echo "$HTTP_RESPONSE" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')

log_info "HTTP Status: $HTTP_STATUS"

# Output raw JSON if requested
if [ "$JSON_OUTPUT" = true ]; then
    echo "$HTTP_BODY"
    if [ "$HTTP_STATUS" -eq 200 ]; then
        exit 0
    else
        exit 2
    fi
fi

# Check HTTP status
if [ "$HTTP_STATUS" -ne 200 ]; then
    log_error "Health endpoint returned HTTP $HTTP_STATUS"
    echo "CRITICAL: OCR service returned HTTP $HTTP_STATUS"
    exit 2
fi

# Parse JSON response
if [ "$HAS_JQ" = true ]; then
    STATUS=$(echo "$HTTP_BODY" | jq -r '.status // "unknown"')
    VERSION=$(echo "$HTTP_BODY" | jq -r '.version // "unknown"')
    UPTIME=$(echo "$HTTP_BODY" | jq -r '.uptime_seconds // 0')

    # Check component statuses
    PADDLE_STATUS=$(echo "$HTTP_BODY" | jq -r '.components.paddle_ocr.status // "unknown"')
    EASYOCR_STATUS=$(echo "$HTTP_BODY" | jq -r '.components.easyocr.status // "unknown"')
    LLM_STATUS=$(echo "$HTTP_BODY" | jq -r '.components.llm.status // "unknown"')

    log_info "Service Status: $STATUS"
    log_info "Version: $VERSION"
    log_info "Uptime: ${UPTIME}s"
    log_info "PaddleOCR: $PADDLE_STATUS"
    log_info "EasyOCR: $EASYOCR_STATUS"
    log_info "LLM: $LLM_STATUS"

    # Determine exit code based on status
    case "$STATUS" in
        "healthy")
            echo "OK: OCR service is healthy (v$VERSION, uptime: ${UPTIME}s)"
            echo "  PaddleOCR: $PADDLE_STATUS, EasyOCR: $EASYOCR_STATUS"
            exit 0
            ;;
        "degraded")
            echo "WARNING: OCR service is degraded (v$VERSION)"
            echo "  PaddleOCR: $PADDLE_STATUS, EasyOCR: $EASYOCR_STATUS, LLM: $LLM_STATUS"
            exit 1
            ;;
        *)
            echo "CRITICAL: OCR service status is $STATUS"
            exit 2
            ;;
    esac
else
    # Simple check without jq
    if echo "$HTTP_BODY" | grep -q '"status":\s*"healthy"'; then
        echo "OK: OCR service is healthy"
        exit 0
    elif echo "$HTTP_BODY" | grep -q '"status":\s*"degraded"'; then
        echo "WARNING: OCR service is degraded"
        exit 1
    else
        echo "CRITICAL: OCR service health check failed"
        exit 2
    fi
fi
