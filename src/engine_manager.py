"""
Engine Manager for Hybrid Read Tool.

Manages OCR engine lifecycle, selection, and fallback logic.
"""

from typing import Dict, List, Optional, Type
import logging

from .engines.base_engine import (
    BaseEngine,
    EngineCapabilities,
    EngineNotAvailableError,
    LanguageNotSupportedError
)
from .config import ReadToolConfig
from .models import ReadResult

logger = logging.getLogger(__name__)


class EngineManager:
    """
    Manages OCR/Vision engine lifecycle and selection.

    Features:
    - Lazy loading of engines (only initialized when needed)
    - Automatic engine selection based on file type and use case
    - Fallback handling when primary engine fails
    - Engine availability checking
    """

    def __init__(self, config: Optional[ReadToolConfig] = None):
        """
        Initialize the engine manager.

        Args:
            config: Configuration object (uses defaults if None)
        """
        self.config = config or ReadToolConfig()
        self._engines: Dict[str, BaseEngine] = {}
        self._engine_classes: Dict[str, Type[BaseEngine]] = {}
        self._availability_cache: Dict[str, bool] = {}

    def register_engine_class(self, name: str, engine_class: Type[BaseEngine]) -> None:
        """
        Register an engine class for lazy loading.

        Args:
            name: Engine identifier (e.g., "paddle")
            engine_class: Engine class to instantiate
        """
        self._engine_classes[name] = engine_class
        logger.debug(f"Registered engine class: {name}")

    def get_engine(self, name: str) -> BaseEngine:
        """
        Get an engine instance by name (lazy loading).

        Args:
            name: Engine identifier

        Returns:
            Engine instance

        Raises:
            EngineNotAvailableError: If engine is not registered or unavailable
        """
        # Check if already instantiated
        if name in self._engines:
            return self._engines[name]

        # Check if class is registered
        if name not in self._engine_classes:
            raise EngineNotAvailableError(
                f"Engine '{name}' is not registered",
                engine=name,
                code="ENGINE_NOT_REGISTERED"
            )

        # Instantiate engine
        try:
            engine_class = self._engine_classes[name]
            engine = engine_class()
            self._engines[name] = engine
            logger.info(f"Initialized engine: {name}")
            return engine
        except Exception as e:
            raise EngineNotAvailableError(
                f"Failed to initialize engine '{name}': {str(e)}",
                engine=name,
                code="ENGINE_INIT_FAILED"
            )

    def is_available(self, name: str) -> bool:
        """
        Check if an engine is available.

        Args:
            name: Engine identifier

        Returns:
            True if engine is available
        """
        # Check cache first
        if name in self._availability_cache:
            return self._availability_cache[name]

        # Check if registered
        if name not in self._engine_classes:
            self._availability_cache[name] = False
            return False

        try:
            engine = self.get_engine(name)
            available = engine.is_available()
            self._availability_cache[name] = available
            return available
        except Exception:
            self._availability_cache[name] = False
            return False

    def clear_availability_cache(self) -> None:
        """Clear the availability cache (useful after installing new engines)."""
        self._availability_cache.clear()

    def get_available_engines(self) -> List[str]:
        """
        Get list of available engine names.

        Returns:
            List of available engine identifiers
        """
        available = []
        for name in self._engine_classes:
            if self.is_available(name):
                available.append(name)
        return available

    def get_engine_info(self, name: str) -> Dict:
        """
        Get detailed information about an engine.

        Args:
            name: Engine identifier

        Returns:
            Dictionary with engine info
        """
        try:
            engine = self.get_engine(name)
            capabilities = engine.get_capabilities()

            return {
                "name": engine.name,
                "display_name": engine.display_name,
                "available": engine.is_available(),
                "capabilities": {
                    "supports_images": capabilities.supports_images,
                    "supports_pdf": capabilities.supports_pdf,
                    "supports_vision_analysis": capabilities.supports_vision_analysis,
                    "supports_gpu": capabilities.supports_gpu,
                    "supported_languages": capabilities.supported_languages,
                    "max_file_size_mb": capabilities.max_file_size_mb,
                    "supports_tables": capabilities.supports_tables,
                    "supports_structure": capabilities.supports_structure,
                }
            }
        except EngineNotAvailableError:
            return {
                "name": name,
                "display_name": name,
                "available": False,
                "capabilities": {}
            }

    def get_all_engines_info(self) -> List[Dict]:
        """
        Get information about all registered engines.

        Returns:
            List of engine info dictionaries
        """
        return [self.get_engine_info(name) for name in self._engine_classes]

    def select_engine(
        self,
        file_type: str,
        use_case: str = "ocr",
        language: str = "en",
        user_preference: Optional[str] = None
    ) -> str:
        """
        Select the best engine for the given parameters.

        Selection logic:
        1. If user specified a preference and it's available, use it
        2. For vision analysis, require Ollama
        3. For OCR, follow fallback_order from config
        4. Check language support

        Args:
            file_type: Type of file ("image", "pdf", "text")
            use_case: Use case ("ocr", "vision", "analysis")
            language: Language code
            user_preference: User's preferred engine (optional)

        Returns:
            Selected engine name

        Raises:
            EngineNotAvailableError: If no suitable engine is available
        """
        # Handle user preference
        if user_preference and user_preference != "auto":
            if self.is_available(user_preference):
                engine = self.get_engine(user_preference)
                if engine.supports_language(language):
                    return user_preference
                else:
                    logger.warning(
                        f"Engine '{user_preference}' doesn't support language '{language}'"
                    )
            else:
                logger.warning(f"Preferred engine '{user_preference}' is not available")

        # Vision analysis requires Ollama
        if use_case in ("vision", "analysis"):
            if self.is_available("ollama"):
                return "ollama"
            raise EngineNotAvailableError(
                "Ollama is required for vision analysis but is not available",
                engine="ollama",
                code="OLLAMA_REQUIRED"
            )

        # Standard OCR - follow fallback order
        for engine_name in self.config.fallback_order:
            if not self.is_available(engine_name):
                continue

            engine = self.get_engine(engine_name)
            if engine.supports_language(language):
                return engine_name

        # No suitable engine found
        available = self.get_available_engines()
        raise EngineNotAvailableError(
            f"No OCR engine available for language '{language}'. "
            f"Available engines: {available}",
            code="NO_SUITABLE_ENGINE"
        )

    def process_with_fallback(
        self,
        file_path: str,
        file_type: str,
        lang: str,
        options: Optional[Dict] = None,
        user_preference: Optional[str] = None
    ) -> ReadResult:
        """
        Process a file with automatic fallback on failure.

        Args:
            file_path: Path to the file
            file_type: Type of file
            lang: Language code
            options: Processing options
            user_preference: Preferred engine

        Returns:
            ReadResult from successful engine

        Raises:
            EngineNotAvailableError: If all engines fail
        """
        errors = []

        # Determine engine order
        if user_preference and user_preference != "auto":
            engine_order = [user_preference] + [
                e for e in self.config.fallback_order if e != user_preference
            ]
        else:
            engine_order = self.config.fallback_order.copy()

        # Try each engine
        for engine_name in engine_order:
            if not self.is_available(engine_name):
                continue

            engine = self.get_engine(engine_name)

            if not engine.supports_language(lang):
                continue

            try:
                if file_type == "image":
                    result = engine.process_image(file_path, lang, options)
                elif file_type == "pdf":
                    result = engine.process_pdf(file_path, lang, options=options)
                else:
                    result = engine.process_image(file_path, lang, options)

                if result.success:
                    logger.info(f"Successfully processed with engine: {engine_name}")
                    return result
                else:
                    errors.append({
                        "engine": engine_name,
                        "error": result.error or "Unknown error"
                    })

            except Exception as e:
                errors.append({
                    "engine": engine_name,
                    "error": str(e)
                })
                logger.warning(f"Engine {engine_name} failed: {e}")

                if not self.config.fallback_enabled:
                    raise

        # All engines failed
        error_msg = "All OCR engines failed:\n"
        for err in errors:
            error_msg += f"  - {err['engine']}: {err['error']}\n"

        raise EngineNotAvailableError(
            error_msg,
            code="ALL_ENGINES_FAILED"
        )
