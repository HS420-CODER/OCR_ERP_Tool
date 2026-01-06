"""
ERP Arabic OCR Microservice - Configuration Settings
=====================================================
Dataclass-based configuration with environment variable loading.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class EngineMode(Enum):
    """OCR engine processing modes."""
    PADDLE_ONLY = "paddle_only"
    EASYOCR_ONLY = "easyocr_only"
    MULTI_ENGINE = "multi_engine"
    FUSION = "fusion"


class FusionStrategy(Enum):
    """Result fusion strategies."""
    CONFIDENCE_WEIGHTED = "confidence_weighted"
    MAJORITY_VOTING = "majority_voting"
    DICTIONARY_VALIDATED = "dictionary_validated"


@dataclass
class OCRSettings:
    """OCR engine configuration."""

    # Engine mode
    engine_mode: EngineMode = field(
        default_factory=lambda: EngineMode(
            os.getenv("OCR_ENGINE_MODE", "fusion")
        )
    )

    # Languages
    languages: List[str] = field(
        default_factory=lambda: os.getenv(
            "OCR_LANGUAGES", "ar,en"
        ).split(",")
    )

    # PaddleOCR settings
    paddle_use_angle_cls: bool = field(
        default_factory=lambda: os.getenv(
            "PADDLE_USE_ANGLE_CLS", "true"
        ).lower() == "true"
    )
    paddle_use_gpu: bool = field(
        default_factory=lambda: os.getenv(
            "PADDLE_USE_GPU", "false"
        ).lower() == "true"
    )
    paddle_det_model_dir: Optional[str] = field(
        default_factory=lambda: os.getenv("PADDLE_DET_MODEL_DIR")
    )
    paddle_rec_model_dir: Optional[str] = field(
        default_factory=lambda: os.getenv("PADDLE_REC_MODEL_DIR")
    )
    paddle_cls_model_dir: Optional[str] = field(
        default_factory=lambda: os.getenv("PADDLE_CLS_MODEL_DIR")
    )

    # EasyOCR settings
    easyocr_gpu: bool = field(
        default_factory=lambda: os.getenv(
            "EASYOCR_GPU", "false"
        ).lower() == "true"
    )
    easyocr_model_storage: Optional[str] = field(
        default_factory=lambda: os.getenv("EASYOCR_MODEL_STORAGE")
    )

    # Fusion settings
    fusion_strategy: FusionStrategy = field(
        default_factory=lambda: FusionStrategy(
            os.getenv("FUSION_STRATEGY", "confidence_weighted")
        )
    )
    fusion_confidence_threshold: float = field(
        default_factory=lambda: float(
            os.getenv("FUSION_CONFIDENCE_THRESHOLD", "0.7")
        )
    )

    # Processing settings
    max_image_size_mb: int = field(
        default_factory=lambda: int(
            os.getenv("MAX_IMAGE_SIZE_MB", "20")
        )
    )
    image_preprocessing: bool = field(
        default_factory=lambda: os.getenv(
            "IMAGE_PREPROCESSING", "true"
        ).lower() == "true"
    )


@dataclass
class LLMSettings:
    """LLM correction service configuration."""

    enabled: bool = field(
        default_factory=lambda: os.getenv(
            "LLM_ENABLED", "true"
        ).lower() == "true"
    )
    api_url: str = field(
        default_factory=lambda: os.getenv(
            "LLM_API_URL", "https://api.openai.com/v1"
        )
    )
    api_key: str = field(
        default_factory=lambda: os.getenv("LLM_API_KEY", "")
    )
    model: str = field(
        default_factory=lambda: os.getenv(
            "LLM_MODEL", "gpt-4o-mini"
        )
    )
    max_tokens: int = field(
        default_factory=lambda: int(
            os.getenv("LLM_MAX_TOKENS", "2048")
        )
    )
    temperature: float = field(
        default_factory=lambda: float(
            os.getenv("LLM_TEMPERATURE", "0.1")
        )
    )
    timeout: int = field(
        default_factory=lambda: int(
            os.getenv("LLM_TIMEOUT", "30")
        )
    )
    retry_attempts: int = field(
        default_factory=lambda: int(
            os.getenv("LLM_RETRY_ATTEMPTS", "3")
        )
    )


@dataclass
class CacheSettings:
    """Redis caching configuration."""

    enabled: bool = field(
        default_factory=lambda: os.getenv(
            "CACHE_ENABLED", "true"
        ).lower() == "true"
    )
    redis_url: str = field(
        default_factory=lambda: os.getenv(
            "REDIS_URL", "redis://localhost:6379/0"
        )
    )
    redis_host: str = field(
        default_factory=lambda: os.getenv(
            "REDIS_HOST", "localhost"
        )
    )
    redis_port: int = field(
        default_factory=lambda: int(
            os.getenv("REDIS_PORT", "6379")
        )
    )
    redis_db: int = field(
        default_factory=lambda: int(
            os.getenv("REDIS_DB", "0")
        )
    )
    redis_password: Optional[str] = field(
        default_factory=lambda: os.getenv("REDIS_PASSWORD")
    )
    ttl_seconds: int = field(
        default_factory=lambda: int(
            os.getenv("CACHE_TTL_SECONDS", "3600")
        )
    )
    max_connections: int = field(
        default_factory=lambda: int(
            os.getenv("REDIS_MAX_CONNECTIONS", "10")
        )
    )


@dataclass
class SecuritySettings:
    """API security configuration."""

    # API Key authentication
    api_keys: List[str] = field(
        default_factory=lambda: [
            k.strip() for k in
            os.getenv("API_KEYS", "").split(",")
            if k.strip()
        ]
    )
    require_api_key: bool = field(
        default_factory=lambda: os.getenv(
            "REQUIRE_API_KEY", "true"
        ).lower() == "true"
    )

    # Rate limiting
    rate_limit_enabled: bool = field(
        default_factory=lambda: os.getenv(
            "RATE_LIMIT_ENABLED", "true"
        ).lower() == "true"
    )
    rate_limit_per_minute: int = field(
        default_factory=lambda: int(
            os.getenv("RATE_LIMIT_PER_MINUTE", "60")
        )
    )
    rate_limit_per_hour: int = field(
        default_factory=lambda: int(
            os.getenv("RATE_LIMIT_PER_HOUR", "1000")
        )
    )

    # File security
    allowed_extensions: List[str] = field(
        default_factory=lambda: os.getenv(
            "ALLOWED_EXTENSIONS", "png,jpg,jpeg,pdf,tiff,bmp"
        ).split(",")
    )
    allowed_mime_types: List[str] = field(
        default_factory=lambda: [
            "image/png", "image/jpeg", "image/tiff",
            "image/bmp", "application/pdf"
        ]
    )
    max_file_size_mb: int = field(
        default_factory=lambda: int(
            os.getenv("MAX_FILE_SIZE_MB", "20")
        )
    )

    # CORS
    cors_origins: List[str] = field(
        default_factory=lambda: os.getenv(
            "CORS_ORIGINS", "*"
        ).split(",")
    )


@dataclass
class ServerSettings:
    """Server configuration."""

    host: str = field(
        default_factory=lambda: os.getenv("SERVER_HOST", "0.0.0.0")
    )
    port: int = field(
        default_factory=lambda: int(
            os.getenv("SERVER_PORT", "5000")
        )
    )
    debug: bool = field(
        default_factory=lambda: os.getenv(
            "DEBUG", "false"
        ).lower() == "true"
    )
    workers: int = field(
        default_factory=lambda: int(
            os.getenv("WORKERS", "4")
        )
    )
    threads: int = field(
        default_factory=lambda: int(
            os.getenv("THREADS", "2")
        )
    )
    timeout: int = field(
        default_factory=lambda: int(
            os.getenv("REQUEST_TIMEOUT", "120")
        )
    )


@dataclass
class MonitoringSettings:
    """Monitoring and logging configuration."""

    # Logging
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )
    log_format: str = field(
        default_factory=lambda: os.getenv(
            "LOG_FORMAT", "json"
        )
    )
    log_file: Optional[str] = field(
        default_factory=lambda: os.getenv("LOG_FILE")
    )

    # Metrics
    metrics_enabled: bool = field(
        default_factory=lambda: os.getenv(
            "METRICS_ENABLED", "true"
        ).lower() == "true"
    )
    metrics_port: int = field(
        default_factory=lambda: int(
            os.getenv("METRICS_PORT", "9090")
        )
    )

    # Health check
    health_check_interval: int = field(
        default_factory=lambda: int(
            os.getenv("HEALTH_CHECK_INTERVAL", "30")
        )
    )


@dataclass
class ResourceSettings:
    """Resource management configuration."""

    max_concurrent_requests: int = field(
        default_factory=lambda: int(
            os.getenv("MAX_CONCURRENT_REQUESTS", "10")
        )
    )
    max_memory_percent: int = field(
        default_factory=lambda: int(
            os.getenv("MAX_MEMORY_PERCENT", "80")
        )
    )
    max_cpu_percent: int = field(
        default_factory=lambda: int(
            os.getenv("MAX_CPU_PERCENT", "90")
        )
    )
    temp_dir: str = field(
        default_factory=lambda: os.getenv(
            "TEMP_DIR", "/tmp/ocr"
        )
    )


@dataclass
class Settings:
    """
    Main application settings container.

    Usage:
        settings = Settings()
        print(settings.ocr.engine_mode)
        print(settings.llm.api_url)
    """

    ocr: OCRSettings = field(default_factory=OCRSettings)
    llm: LLMSettings = field(default_factory=LLMSettings)
    cache: CacheSettings = field(default_factory=CacheSettings)
    security: SecuritySettings = field(default_factory=SecuritySettings)
    server: ServerSettings = field(default_factory=ServerSettings)
    monitoring: MonitoringSettings = field(default_factory=MonitoringSettings)
    resources: ResourceSettings = field(default_factory=ResourceSettings)

    # Application metadata
    app_name: str = "ERP Arabic OCR Microservice"
    app_version: str = field(
        default_factory=lambda: os.getenv("APP_VERSION", "2.0.0")
    )
    environment: str = field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "development")
    )

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    def validate(self) -> List[str]:
        """
        Validate settings and return list of errors.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check LLM API key if enabled
        if self.llm.enabled and not self.llm.api_key:
            errors.append("LLM_API_KEY is required when LLM is enabled")

        # Check API keys in production
        if self.is_production():
            if self.security.require_api_key and not self.security.api_keys:
                errors.append("API_KEYS must be set in production")
            if self.server.debug:
                errors.append("DEBUG must be false in production")

        # Check Redis connection if caching enabled
        if self.cache.enabled:
            if not self.cache.redis_host:
                errors.append("REDIS_HOST is required when caching is enabled")

        return errors


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global settings instance (singleton pattern).

    Returns:
        Settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """
    Reload settings from environment variables.

    Returns:
        New Settings instance
    """
    global _settings
    load_dotenv(override=True)
    _settings = Settings()
    return _settings
