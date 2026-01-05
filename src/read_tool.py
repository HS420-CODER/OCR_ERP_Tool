"""
Hybrid Read Tool - Main orchestrator class.

Provides Claude Code CLI-like functionality for reading files:
- Text files with line numbers (cat -n format)
- Images via OCR (PaddleOCR/Tesseract)
- PDFs with page-by-page extraction
- Jupyter notebooks (.ipynb)
- Structured bilingual output for Arabic documents

All functionality works offline without API keys.
"""

import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from .models import ReadOptions, ReadResult, PageResult, TextBlock
from .config import ReadToolConfig
from .engine_manager import EngineManager
from .utils.file_utils import (
    get_file_type,
    validate_file_path,
    check_file_size,
    detect_encoding
)

logger = logging.getLogger(__name__)


class HybridReadTool:
    """
    Main Read Tool class - provides Claude Code CLI-like functionality offline.

    Features:
    - Text files: Line numbers, offset/limit, truncation (cat -n format)
    - Images: OCR via PaddleOCR/Tesseract
    - PDFs: Page-by-page OCR extraction
    - Jupyter notebooks: Cell extraction with outputs
    - Vision analysis: Context-aware via Ollama (optional)
    - Structured output: Bilingual markdown for Arabic documents

    Usage:
        reader = HybridReadTool()
        result = reader.read("/path/to/file.png")
        result = reader.read("/path/to/file.txt", offset=100, limit=50)
        result = reader.read("/path/to/doc.pdf", lang="ar")
    """

    # Supported file extensions by category
    TEXT_EXTENSIONS = {
        '.txt', '.md', '.py', '.js', '.ts', '.jsx', '.tsx',
        '.json', '.yaml', '.yml', '.xml', '.html', '.htm',
        '.css', '.scss', '.sql', '.sh', '.bat', '.ps1',
        '.ini', '.cfg', '.conf', '.config', '.log', '.csv',
        '.env', '.c', '.cpp', '.h', '.java', '.go', '.rs',
        '.rb', '.php', '.r', '.swift', '.kt', '.scala'
    }
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.tif'}
    PDF_EXTENSIONS = {'.pdf'}
    NOTEBOOK_EXTENSIONS = {'.ipynb'}

    # Line formatting constants (matches Claude Code CLI)
    MAX_LINE_LENGTH = 2000
    DEFAULT_LINE_LIMIT = 2000

    def __init__(self, config: Optional[ReadToolConfig] = None):
        """
        Initialize the Hybrid Read Tool.

        Args:
            config: Configuration object (uses defaults if None)
        """
        self.config = config or ReadToolConfig()
        self.engine_manager = EngineManager(self.config)
        self._register_engines()

    def _register_engines(self) -> None:
        """Register available OCR engines."""
        # Import and register engines
        # These will be lazy-loaded when needed
        try:
            from .engines.paddle_engine import PaddleEngine
            self.engine_manager.register_engine_class("paddle", PaddleEngine)
        except ImportError:
            logger.warning("PaddleEngine not available")

        try:
            from .engines.tesseract_engine import TesseractEngine
            self.engine_manager.register_engine_class("tesseract", TesseractEngine)
        except ImportError:
            logger.warning("TesseractEngine not available")

        # Ollama Vision engine (Phase 3/6)
        try:
            from .engines.ollama_engine import OllamaEngine
            self.engine_manager.register_engine_class("ollama", OllamaEngine)
        except ImportError:
            logger.warning("OllamaEngine not available")

    def read(
        self,
        file_path: str,
        offset: int = 0,
        limit: int = DEFAULT_LINE_LIMIT,
        lang: str = "en",
        engine: str = "auto",
        prompt: Optional[str] = None,
        output_format: str = "text",
        structured_output: bool = True
    ) -> ReadResult:
        """
        Read a file and extract its contents.

        This is the main entry point for the Read Tool, providing
        Claude Code CLI-like functionality.

        Args:
            file_path: Absolute path to the file
            offset: Line number to start from (for text files, 0-based)
            limit: Maximum lines to read (for text files)
            lang: Language code ("en" or "ar")
            engine: OCR engine ("auto", "paddle", "tesseract", "ollama")
            prompt: Custom prompt for vision analysis
            output_format: Output format ("text", "json", "markdown")
            structured_output: Enable Claude Code-like structured output

        Returns:
            ReadResult with extracted content
        """
        start_time = time.perf_counter()

        # Validate file path
        path = Path(file_path)

        # Must be absolute path
        if not path.is_absolute():
            return ReadResult.error_result(
                file_path,
                f"File path must be absolute: {file_path}"
            )

        # Must exist
        if not path.exists():
            return ReadResult.error_result(
                file_path,
                f"File not found: {file_path}"
            )

        # Cannot be directory
        if path.is_dir():
            return ReadResult.error_result(
                file_path,
                f"Cannot read directory: {file_path}. This tool can only read files, not directories."
            )

        # Check file size
        valid, error = check_file_size(str(path), self.config.max_file_size_mb)
        if not valid:
            return ReadResult.error_result(file_path, error)

        # Determine file type and process accordingly
        suffix = path.suffix.lower()

        try:
            if suffix in self.TEXT_EXTENSIONS or suffix == '':
                result = self._read_text_file(path, offset, limit)
            elif suffix in self.IMAGE_EXTENSIONS:
                result = self._read_image_file(path, lang, engine, prompt, structured_output)
            elif suffix in self.PDF_EXTENSIONS:
                result = self._read_pdf_file(path, lang, engine, structured_output)
            elif suffix in self.NOTEBOOK_EXTENSIONS:
                result = self._read_notebook_file(path)
            else:
                # Try to read as text
                result = self._read_text_file(path, offset, limit)

            # Set processing time
            result.processing_time_ms = (time.perf_counter() - start_time) * 1000

            return result

        except Exception as e:
            logger.exception(f"Error reading file: {file_path}")
            return ReadResult.error_result(file_path, str(e))

    def _read_text_file(
        self,
        path: Path,
        offset: int = 0,
        limit: int = DEFAULT_LINE_LIMIT
    ) -> ReadResult:
        """
        Read text file with line numbers (cat -n format).

        Output format matches Claude Code CLI:
        "     1\tFirst line of content"
        "     2\tSecond line of content"

        Args:
            path: Path to the text file
            offset: Line number to start from (0-based)
            limit: Maximum lines to read

        Returns:
            ReadResult with formatted text
        """
        try:
            # Detect encoding
            encoding = detect_encoding(str(path))

            with open(path, 'r', encoding=encoding, errors='replace') as f:
                lines = f.readlines()
        except Exception as e:
            return ReadResult.error_result(str(path), f"Failed to read file: {e}", "text")

        # Apply offset and limit
        total_lines = len(lines)
        start_line = min(offset, total_lines)
        end_line = min(start_line + limit, total_lines)
        selected_lines = lines[start_line:end_line]

        # Format with line numbers (cat -n style)
        # Format: "     1\tContent" (6 chars for line number + tab)
        formatted_lines = []
        for i, line in enumerate(selected_lines, start=start_line + 1):
            # Remove trailing newline
            line = line.rstrip('\n\r')

            # Truncate long lines
            if len(line) > self.MAX_LINE_LENGTH:
                line = line[:self.MAX_LINE_LENGTH] + "..."

            # Format with line number (right-aligned, 6 chars) + tab + content
            formatted_lines.append(f"{i:>6}\t{line}")

        full_text = '\n'.join(formatted_lines)

        return ReadResult(
            success=True,
            file_path=str(path),
            file_type="text",
            engine_used="native",
            pages=[PageResult(
                page_number=1,
                text_blocks=[],
                full_text=full_text,
            )],
            full_text=full_text,
            processing_time_ms=0,
            language="",
            metadata={
                "total_lines": total_lines,
                "lines_read": len(selected_lines),
                "offset": start_line,
                "limit": limit,
                "encoding": encoding
            }
        )

    def _read_notebook_file(self, path: Path) -> ReadResult:
        """
        Read Jupyter notebook and extract all cells with outputs.

        Mirrors Claude Code CLI notebook reading functionality.

        Args:
            path: Path to the .ipynb file

        Returns:
            ReadResult with formatted notebook content
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                notebook = json.load(f)

            cells = notebook.get('cells', [])
            formatted_parts = []

            for i, cell in enumerate(cells):
                cell_type = cell.get('cell_type', 'unknown')
                source = ''.join(cell.get('source', []))

                # Format cell header
                formatted_parts.append(f"### Cell {i + 1} [{cell_type}]")
                formatted_parts.append("```")
                formatted_parts.append(source)
                formatted_parts.append("```")

                # Include outputs for code cells
                if cell_type == 'code':
                    outputs = cell.get('outputs', [])
                    if outputs:
                        formatted_parts.append("**Output:**")
                        for output in outputs:
                            output_type = output.get('output_type', '')
                            if output_type == 'stream':
                                text = ''.join(output.get('text', []))
                                formatted_parts.append(f"```\n{text}\n```")
                            elif output_type in ('execute_result', 'display_data'):
                                data = output.get('data', {})
                                if 'text/plain' in data:
                                    text = ''.join(data['text/plain'])
                                    formatted_parts.append(f"```\n{text}\n```")
                            elif output_type == 'error':
                                ename = output.get('ename', 'Error')
                                evalue = output.get('evalue', '')
                                formatted_parts.append(f"```\n{ename}: {evalue}\n```")

                formatted_parts.append("")  # Empty line between cells

            full_text = '\n'.join(formatted_parts)

            # Get kernel info
            kernel_name = notebook.get('metadata', {}).get('kernelspec', {}).get('name', 'unknown')
            language_info = notebook.get('metadata', {}).get('language_info', {}).get('name', 'unknown')

            return ReadResult(
                success=True,
                file_path=str(path),
                file_type="notebook",
                engine_used="native",
                pages=[PageResult(
                    page_number=1,
                    text_blocks=[],
                    full_text=full_text,
                )],
                full_text=full_text,
                processing_time_ms=0,
                language=language_info,
                metadata={
                    "total_cells": len(cells),
                    "kernel": kernel_name,
                    "language": language_info,
                    "cell_types": {
                        "code": sum(1 for c in cells if c.get('cell_type') == 'code'),
                        "markdown": sum(1 for c in cells if c.get('cell_type') == 'markdown'),
                        "raw": sum(1 for c in cells if c.get('cell_type') == 'raw'),
                    }
                }
            )

        except json.JSONDecodeError as e:
            return ReadResult.error_result(str(path), f"Invalid notebook format: {e}", "notebook")
        except Exception as e:
            return ReadResult.error_result(str(path), str(e), "notebook")

    def _read_image_file(
        self,
        path: Path,
        lang: str,
        engine: str,
        prompt: Optional[str],
        structured_output: bool
    ) -> ReadResult:
        """
        Read image file using OCR engine.

        Args:
            path: Path to the image file
            lang: Language code
            engine: Engine preference
            prompt: Vision analysis prompt
            structured_output: Enable structured output

        Returns:
            ReadResult with OCR text
        """
        # Select engine
        use_case = "vision" if prompt else "ocr"
        selected_engine = self.engine_manager.select_engine(
            file_type="image",
            use_case=use_case,
            language=lang,
            user_preference=engine if engine != "auto" else None
        )

        engine_instance = self.engine_manager.get_engine(selected_engine)

        # Process with prompt if provided (vision analysis)
        if prompt and engine_instance.get_capabilities().supports_vision_analysis:
            return engine_instance.process_with_prompt(str(path), prompt)

        # Standard OCR
        result = engine_instance.process_image(str(path), lang)

        # Generate structured output for Arabic documents
        if structured_output and lang == "ar" and result.success:
            result = self._add_structured_output(result)

        return result

    def _read_pdf_file(
        self,
        path: Path,
        lang: str,
        engine: str,
        structured_output: bool
    ) -> ReadResult:
        """
        Read PDF file using OCR engine.

        Args:
            path: Path to the PDF file
            lang: Language code
            engine: Engine preference
            structured_output: Enable structured output

        Returns:
            ReadResult with OCR text from all pages
        """
        # Select engine
        selected_engine = self.engine_manager.select_engine(
            file_type="pdf",
            use_case="ocr",
            language=lang,
            user_preference=engine if engine != "auto" else None
        )

        engine_instance = self.engine_manager.get_engine(selected_engine)
        result = engine_instance.process_pdf(str(path), lang)

        # Generate structured output for Arabic documents
        if structured_output and lang == "ar" and result.success:
            result = self._add_structured_output(result)

        return result

    def _add_structured_output(self, result: ReadResult) -> ReadResult:
        """
        Add structured bilingual output for Arabic documents.

        This generates Claude Code-like markdown output with
        bilingual tables and semantic sections.

        Args:
            result: Raw OCR result

        Returns:
            ReadResult with structured_output field populated
        """
        try:
            from .formatters import DocumentAnalyzer, StructuredOutputFormatter

            analyzer = DocumentAnalyzer()
            formatter = StructuredOutputFormatter()

            # Analyze document structure
            structure = analyzer.analyze(result)

            # Generate structured markdown output
            result.structured_output = formatter.format(result, structure, "markdown")

            # Add structure info to metadata
            result.metadata["document_type"] = structure.document_type.value
            result.metadata["is_bilingual"] = structure.is_bilingual
            result.metadata["detected_language"] = structure.language

            logger.info(
                f"Generated structured output: type={structure.document_type.value}, "
                f"bilingual={structure.is_bilingual}"
            )

        except ImportError as e:
            logger.warning(f"Formatters not available: {e}")
        except Exception as e:
            logger.warning(f"Failed to generate structured output: {e}")

        return result

    def get_available_engines(self) -> Dict[str, Any]:
        """
        Get information about available OCR engines.

        Returns:
            Dictionary with engine information
        """
        return {
            "engines": self.engine_manager.get_all_engines_info(),
            "default_engine": self.config.default_engine
        }

    def read_with_options(self, options: ReadOptions) -> ReadResult:
        """
        Read a file using ReadOptions object.

        Args:
            options: ReadOptions with all parameters

        Returns:
            ReadResult with extracted content
        """
        return self.read(
            file_path=options.file_path,
            offset=options.offset,
            limit=options.limit,
            lang=options.lang,
            engine=options.engine,
            prompt=options.prompt,
            output_format=options.output_format,
            structured_output=options.structured_output
        )
