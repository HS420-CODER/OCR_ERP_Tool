"""
Document formatting and structure analysis.

Components:
- DocumentAnalyzer: Analyzes document structure and type
- StructuredOutputFormatter: Formats output as bilingual markdown
- field_dictionary: Arabic-English field translations
"""

from .field_dictionary import (
    INVOICE_FIELDS,
    INVOICE_FIELDS_EN_AR,
    SECTION_HEADERS,
    get_english,
    get_arabic,
    get_bilingual,
    is_arabic_text,
    is_bilingual_text,
)

from .document_analyzer import (
    DocumentType,
    LayoutRegionType,
    LayoutRegion,
    DetectedTable,
    DocumentStructure,
    DocumentAnalyzer,
)

from .output_formatter import StructuredOutputFormatter

__all__ = [
    # Field dictionary
    "INVOICE_FIELDS",
    "INVOICE_FIELDS_EN_AR",
    "SECTION_HEADERS",
    "get_english",
    "get_arabic",
    "get_bilingual",
    "is_arabic_text",
    "is_bilingual_text",
    # Document analyzer
    "DocumentType",
    "LayoutRegionType",
    "LayoutRegion",
    "DetectedTable",
    "DocumentStructure",
    "DocumentAnalyzer",
    # Output formatter
    "StructuredOutputFormatter",
]
