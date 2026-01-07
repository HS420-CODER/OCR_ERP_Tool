"""
Batch OCR Processor - Parallel processing for multiple images.

Uses process-level isolation due to PaddleOCR thread-safety constraints.
Integrates with ResourceManager for concurrency control.

Part of Phase 7: Performance & Quality implementation.
"""

import asyncio
import logging
import multiprocessing as mp
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed, Future
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Tuple, Union

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    """Result from batch OCR processing."""

    results: List[Dict[str, Any]] = field(default_factory=list)
    total_images: int = 0
    successful: int = 0
    failed: int = 0
    total_time_ms: float = 0.0
    avg_time_per_image_ms: float = 0.0
    errors: List[Tuple[str, str]] = field(default_factory=list)
    processing_stats: Dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_images == 0:
            return 0.0
        return self.successful / self.total_images

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total_images': self.total_images,
            'successful': self.successful,
            'failed': self.failed,
            'success_rate': round(self.success_rate, 4),
            'total_time_ms': round(self.total_time_ms, 2),
            'avg_time_per_image_ms': round(self.avg_time_per_image_ms, 2),
            'errors': self.errors,
            'processing_stats': self.processing_stats
        }


def _process_single_image(args: Tuple[str, str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process a single image in a separate process.

    This function runs in a child process to ensure process-level isolation
    for PaddleOCR (which is not thread-safe).

    Args:
        args: Tuple of (image_path, mode, options)

    Returns:
        Dict with 'success', 'path', 'result' or 'error'
    """
    image_path, mode, options = args
    start_time = time.time()

    try:
        # Import inside process to avoid serialization issues
        from ..engines.bilingual_ocr_pipeline import (
            BilingualOCRPipeline,
            OCRMode,
            PipelineConfig
        )

        # Map mode string to OCRMode enum
        mode_map = {
            'bilingual': OCRMode.BILINGUAL,
            'arabic': OCRMode.ARABIC_ONLY,
            'english': OCRMode.ENGLISH_ONLY,
            'auto': OCRMode.AUTO_DETECT
        }
        ocr_mode = mode_map.get(mode.lower(), OCRMode.BILINGUAL)

        # Create pipeline with options
        config = PipelineConfig(
            mode=ocr_mode,
            enable_reprocessing=options.get('enable_reprocessing', True),
            enable_post_processing=options.get('enable_post_processing', True),
            high_confidence_threshold=options.get('high_confidence', 0.85),
            reprocess_threshold=options.get('reprocess_threshold', 0.70)
        )

        pipeline = BilingualOCRPipeline(config=config)

        # Process image
        result = pipeline.process_image(image_path)

        elapsed_ms = (time.time() - start_time) * 1000

        return {
            'success': result.success,
            'path': image_path,
            'result': {
                'full_text': result.full_text,
                'confidence': result.overall_confidence,
                'primary_language': result.primary_language.value if result.primary_language else 'unknown',
                'is_bilingual': result.is_bilingual,
                'corrections_made': result.corrections_made,
                'stages_executed': result.stages_executed,
                'processing_time_ms': elapsed_ms
            },
            'error': None
        }

    except ImportError as e:
        # Fallback to basic PaddleEngine if pipeline not available
        try:
            from ..engines.paddle_engine import PaddleEngine

            engine = PaddleEngine()
            result = engine.process(image_path, languages=['ar', 'en'])

            elapsed_ms = (time.time() - start_time) * 1000

            return {
                'success': True,
                'path': image_path,
                'result': {
                    'full_text': result.get('full_text', ''),
                    'confidence': result.get('confidence', 0.0),
                    'primary_language': 'unknown',
                    'is_bilingual': False,
                    'corrections_made': 0,
                    'stages_executed': ['basic_ocr'],
                    'processing_time_ms': elapsed_ms
                },
                'error': None
            }
        except Exception as fallback_error:
            elapsed_ms = (time.time() - start_time) * 1000
            return {
                'success': False,
                'path': image_path,
                'result': None,
                'error': f"Pipeline error: {e}, Fallback error: {fallback_error}"
            }

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(f"Error processing {image_path}: {e}")
        return {
            'success': False,
            'path': image_path,
            'result': None,
            'error': str(e)
        }


class BatchOCRProcessor:
    """
    Parallel OCR processing with process-level isolation.

    Uses ProcessPoolExecutor because PaddleOCR is not thread-safe
    (uses internal `_ocr_lock`). Each image is processed in its own
    process to avoid conflicts.

    Usage:
        processor = BatchOCRProcessor(max_workers=3)
        result = processor.process_batch(image_paths)

        # Or async
        result = await processor.process_batch_async(image_paths)
    """

    # Default configuration
    DEFAULT_MAX_WORKERS = 3
    DEFAULT_TIMEOUT_SECONDS = 120
    DEFAULT_MODE = "bilingual"

    def __init__(
        self,
        max_workers: Optional[int] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        use_gpu: bool = False
    ):
        """
        Initialize batch processor.

        Args:
            max_workers: Maximum parallel processes (default: min(3, cpu_count))
            timeout_seconds: Timeout per image (default: 120)
            use_gpu: Enable GPU acceleration if available
        """
        # Limit workers to prevent resource exhaustion
        cpu_count = mp.cpu_count()
        if max_workers is None:
            self.max_workers = min(self.DEFAULT_MAX_WORKERS, cpu_count)
        else:
            self.max_workers = min(max_workers, cpu_count)

        self.timeout_seconds = timeout_seconds
        self.use_gpu = use_gpu

        # Executor created per batch to ensure clean process state
        self._executor: Optional[ProcessPoolExecutor] = None

        logger.info(f"BatchOCRProcessor initialized: "
                   f"max_workers={self.max_workers}, "
                   f"timeout={self.timeout_seconds}s")

    def process_batch(
        self,
        image_paths: List[str],
        mode: str = DEFAULT_MODE,
        language_hint: Optional[str] = None,
        callback: Optional[Callable[[str, Dict], None]] = None,
        **options
    ) -> BatchResult:
        """
        Process batch of images with progress tracking.

        Args:
            image_paths: List of image file paths
            mode: OCR mode ('bilingual', 'arabic', 'english', 'auto')
            language_hint: Optional language hint for processing
            callback: Optional callback(path, result) for progress updates
            **options: Additional options passed to pipeline

        Returns:
            BatchResult with all processing results
        """
        start_time = time.time()

        # Validate paths
        valid_paths = []
        invalid_paths = []
        for path in image_paths:
            if os.path.exists(path):
                valid_paths.append(path)
            else:
                invalid_paths.append((path, "File not found"))

        if not valid_paths:
            return BatchResult(
                total_images=len(image_paths),
                errors=invalid_paths,
                total_time_ms=(time.time() - start_time) * 1000
            )

        # Prepare arguments for each image
        args_list = [(path, mode, options) for path in valid_paths]

        results = []
        errors = list(invalid_paths)
        successful = 0
        failed = len(invalid_paths)

        # Process with ProcessPoolExecutor
        try:
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_path = {
                    executor.submit(_process_single_image, args): args[0]
                    for args in args_list
                }

                # Collect results as they complete
                for future in as_completed(
                    future_to_path,
                    timeout=self.timeout_seconds * len(valid_paths)
                ):
                    path = future_to_path[future]
                    try:
                        result = future.result(timeout=self.timeout_seconds)

                        if result['success']:
                            results.append(result)
                            successful += 1
                        else:
                            errors.append((path, result.get('error', 'Unknown error')))
                            failed += 1

                        # Progress callback
                        if callback:
                            try:
                                callback(path, result)
                            except Exception as cb_error:
                                logger.warning(f"Callback error for {path}: {cb_error}")

                    except TimeoutError:
                        errors.append((path, f"Timeout after {self.timeout_seconds}s"))
                        failed += 1
                    except Exception as e:
                        errors.append((path, str(e)))
                        failed += 1

        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            # Mark remaining as failed
            processed_paths = set(r['path'] for r in results) | set(e[0] for e in errors)
            for path in valid_paths:
                if path not in processed_paths:
                    errors.append((path, f"Batch error: {e}"))
                    failed += 1

        # Calculate statistics
        total_time_ms = (time.time() - start_time) * 1000
        avg_time = total_time_ms / len(image_paths) if image_paths else 0

        return BatchResult(
            results=results,
            total_images=len(image_paths),
            successful=successful,
            failed=failed,
            total_time_ms=total_time_ms,
            avg_time_per_image_ms=avg_time,
            errors=errors,
            processing_stats={
                'max_workers': self.max_workers,
                'mode': mode,
                'gpu_enabled': self.use_gpu,
                'valid_paths': len(valid_paths),
                'invalid_paths': len(invalid_paths)
            }
        )

    async def process_batch_async(
        self,
        image_paths: List[str],
        mode: str = DEFAULT_MODE,
        callback: Optional[Callable[[str, Dict], None]] = None,
        **options
    ) -> BatchResult:
        """
        Async batch processing with callback.

        Args:
            image_paths: List of image file paths
            mode: OCR mode ('bilingual', 'arabic', 'english', 'auto')
            callback: Optional callback(path, result) for progress updates
            **options: Additional options passed to pipeline

        Returns:
            BatchResult with all processing results
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.process_batch(image_paths, mode, callback=callback, **options)
        )

    def process_directory(
        self,
        directory: str,
        pattern: str = "*.png",
        mode: str = DEFAULT_MODE,
        recursive: bool = False,
        **options
    ) -> BatchResult:
        """
        Process all images in a directory.

        Args:
            directory: Directory path
            pattern: Glob pattern for image files (default: *.png)
            mode: OCR mode
            recursive: Search recursively
            **options: Additional options

        Returns:
            BatchResult with all processing results
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            return BatchResult(errors=[(directory, "Directory not found")])

        # Find matching files
        if recursive:
            image_paths = [str(p) for p in dir_path.rglob(pattern)]
        else:
            image_paths = [str(p) for p in dir_path.glob(pattern)]

        # Also include common image extensions
        for ext in ['*.jpg', '*.jpeg', '*.tiff', '*.bmp']:
            if ext != pattern:
                if recursive:
                    image_paths.extend(str(p) for p in dir_path.rglob(ext))
                else:
                    image_paths.extend(str(p) for p in dir_path.glob(ext))

        # Remove duplicates while preserving order
        seen = set()
        unique_paths = []
        for p in image_paths:
            if p not in seen:
                seen.add(p)
                unique_paths.append(p)

        logger.info(f"Found {len(unique_paths)} images in {directory}")

        return self.process_batch(unique_paths, mode, **options)


# Module-level singleton
_processor_instance: Optional[BatchOCRProcessor] = None


def get_batch_processor(
    max_workers: Optional[int] = None,
    **kwargs
) -> BatchOCRProcessor:
    """
    Get batch processor instance.

    Args:
        max_workers: Optional worker count override
        **kwargs: Additional processor options

    Returns:
        BatchOCRProcessor instance
    """
    global _processor_instance
    if _processor_instance is None or max_workers is not None:
        _processor_instance = BatchOCRProcessor(max_workers=max_workers, **kwargs)
    return _processor_instance


def process_batch(
    image_paths: List[str],
    mode: str = "bilingual",
    max_workers: Optional[int] = None,
    **options
) -> BatchResult:
    """
    Convenience function for batch processing.

    Args:
        image_paths: List of image file paths
        mode: OCR mode
        max_workers: Optional worker count
        **options: Additional options

    Returns:
        BatchResult
    """
    processor = get_batch_processor(max_workers=max_workers)
    return processor.process_batch(image_paths, mode, **options)


async def process_batch_async(
    image_paths: List[str],
    mode: str = "bilingual",
    max_workers: Optional[int] = None,
    **options
) -> BatchResult:
    """
    Convenience function for async batch processing.

    Args:
        image_paths: List of image file paths
        mode: OCR mode
        max_workers: Optional worker count
        **options: Additional options

    Returns:
        BatchResult
    """
    processor = get_batch_processor(max_workers=max_workers)
    return await processor.process_batch_async(image_paths, mode, **options)
