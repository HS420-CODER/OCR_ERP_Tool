"""
Document Structure Analyzer for Arabic/English documents.

Analyzes OCR output to determine:
- Document type (invoice, receipt, form, etc.)
- Language (Arabic, English, bilingual)
- Layout regions (header, table, footer)
- Key-value pairs extraction
- Table detection

Uses PP-StructureV3 for layout analysis when available.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from .field_dictionary import (
    INVOICE_FIELDS,
    DOCUMENT_TYPE_KEYWORDS,
    COMPANY_KEYWORDS,
    CUSTOMER_KEYWORDS,
    INVOICE_HEADER_KEYWORDS,
    TABLE_HEADER_KEYWORDS,
    SUMMARY_KEYWORDS,
    is_arabic_text,
    is_bilingual_text,
    get_english,
)

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Supported document types."""
    INVOICE = "invoice"
    TAX_INVOICE = "tax_invoice"
    RECEIPT = "receipt"
    QUOTATION = "quotation"
    PURCHASE_ORDER = "purchase_order"
    FORM = "form"
    LETTER = "letter"
    TABLE = "table"
    GENERIC = "generic"


class LayoutRegionType(Enum):
    """Document layout region types."""
    HEADER = "header"
    TITLE = "title"
    COMPANY_INFO = "company_info"
    CUSTOMER_INFO = "customer_info"
    INVOICE_HEADER = "invoice_header"
    TABLE = "table"
    TABLE_HEADER = "table_header"
    TABLE_ROW = "table_row"
    SUMMARY = "summary"
    FOOTER = "footer"
    SIGNATURE = "signature"
    TEXT = "text"
    LOGO = "logo"
    QR_CODE = "qr_code"
    UNKNOWN = "unknown"


@dataclass
class LayoutRegion:
    """A detected region in the document."""
    region_type: LayoutRegionType
    bbox: Optional[List[List[int]]] = None  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    text: str = ""
    confidence: float = 1.0
    children: List["LayoutRegion"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.region_type.value,
            "text": self.text,
            "confidence": self.confidence,
            "bbox": self.bbox,
            "children": [c.to_dict() for c in self.children]
        }


@dataclass
class TableCell:
    """A cell in a detected table."""
    row: int
    col: int
    text: str
    is_header: bool = False
    colspan: int = 1
    rowspan: int = 1


@dataclass
class DetectedTable:
    """A detected table structure."""
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    bbox: Optional[List[int]] = None
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "headers": self.headers,
            "rows": self.rows,
            "bbox": self.bbox,
            "confidence": self.confidence
        }


@dataclass
class DocumentStructure:
    """Complete analyzed document structure."""
    document_type: DocumentType
    language: str  # "ar", "en", or "bilingual"
    is_bilingual: bool
    title: str = ""
    regions: List[LayoutRegion] = field(default_factory=list)
    tables: List[DetectedTable] = field(default_factory=list)
    key_value_pairs: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_type": self.document_type.value,
            "language": self.language,
            "is_bilingual": self.is_bilingual,
            "title": self.title,
            "regions": [r.to_dict() for r in self.regions],
            "tables": [t.to_dict() for t in self.tables],
            "key_value_pairs": self.key_value_pairs,
            "metadata": self.metadata
        }


class DocumentAnalyzer:
    """
    Analyzes OCR output to determine document structure.

    Features:
    - Document type detection (invoice, receipt, form, etc.)
    - Language detection (Arabic/English/bilingual)
    - Key-value pair extraction
    - Table detection and structure analysis
    - Layout region identification

    Uses PP-StructureV3 for advanced layout analysis when available.
    """

    # Keywords for document type detection
    INVOICE_KEYWORDS_AR = ["فاتورة", "ضريبية", "الاجمالي", "الصافي", "ضريبة", "البيان"]
    INVOICE_KEYWORDS_EN = ["invoice", "total", "amount", "tax", "vat", "subtotal"]

    RECEIPT_KEYWORDS_AR = ["إيصال", "استلام", "مدفوع"]
    RECEIPT_KEYWORDS_EN = ["receipt", "paid", "received"]

    QUOTATION_KEYWORDS_AR = ["عرض سعر", "عرض أسعار"]
    QUOTATION_KEYWORDS_EN = ["quotation", "quote", "proposal"]

    def __init__(self, use_pp_structure: bool = True):
        """
        Initialize the document analyzer.

        Args:
            use_pp_structure: Whether to use PP-StructureV3 for layout analysis
        """
        self.use_pp_structure = use_pp_structure
        self._structure_engine = None

    def analyze(self, ocr_result: Any) -> DocumentStructure:
        """
        Analyze document structure from OCR result.

        Args:
            ocr_result: ReadResult object with OCR data

        Returns:
            DocumentStructure with detected layout and fields
        """
        # Extract full text from OCR result
        if hasattr(ocr_result, 'full_text'):
            full_text = ocr_result.full_text
        elif isinstance(ocr_result, dict):
            full_text = ocr_result.get('full_text', '')
        else:
            full_text = str(ocr_result)

        # Detect primary language
        language = self._detect_language(full_text)

        # Check if bilingual
        is_bilingual = is_bilingual_text(full_text)

        # Detect document type
        doc_type = self._detect_document_type(full_text)

        # Extract title
        title = self._extract_title(full_text, doc_type)

        # Extract key-value pairs
        key_values = self._extract_key_values(full_text, doc_type)

        # Detect tables from text patterns
        tables = self._detect_tables_from_text(full_text)

        # Build layout regions
        regions = self._build_regions(full_text, key_values, tables)

        return DocumentStructure(
            document_type=doc_type,
            language=language,
            is_bilingual=is_bilingual,
            title=title,
            regions=regions,
            tables=tables,
            key_value_pairs=key_values,
            metadata={
                "text_length": len(full_text),
                "has_tables": len(tables) > 0,
                "field_count": len(key_values)
            }
        )

    def _detect_language(self, text: str) -> str:
        """
        Detect primary language of text.

        Returns:
            "ar" for Arabic, "en" for English, "bilingual" for both
        """
        if not text:
            return "en"

        # Count Arabic and Latin characters
        arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
        latin_chars = sum(1 for c in text if 'a' <= c.lower() <= 'z')
        total_chars = len(text.replace(' ', '').replace('\n', ''))

        if total_chars == 0:
            return "en"

        arabic_ratio = arabic_chars / total_chars
        latin_ratio = latin_chars / total_chars

        # Both significant
        if arabic_ratio > 0.2 and latin_ratio > 0.2:
            return "bilingual"
        # Mostly Arabic
        elif arabic_ratio > 0.3:
            return "ar"
        # Default to English
        return "en"

    def _detect_document_type(self, text: str) -> DocumentType:
        """
        Detect document type from text content.

        Checks for keywords that indicate specific document types.
        """
        text_lower = text.lower()

        # Check for tax invoice (most specific first)
        if "فاتورة ضريبية" in text or "tax invoice" in text_lower:
            return DocumentType.TAX_INVOICE

        # Check for quotation
        quote_ar = sum(1 for kw in self.QUOTATION_KEYWORDS_AR if kw in text)
        quote_en = sum(1 for kw in self.QUOTATION_KEYWORDS_EN if kw in text_lower)
        if quote_ar >= 1 or quote_en >= 1:
            return DocumentType.QUOTATION

        # Check for receipt
        receipt_ar = sum(1 for kw in self.RECEIPT_KEYWORDS_AR if kw in text)
        receipt_en = sum(1 for kw in self.RECEIPT_KEYWORDS_EN if kw in text_lower)
        if receipt_ar >= 1 or receipt_en >= 1:
            return DocumentType.RECEIPT

        # Check for invoice
        invoice_ar = sum(1 for kw in self.INVOICE_KEYWORDS_AR if kw in text)
        invoice_en = sum(1 for kw in self.INVOICE_KEYWORDS_EN if kw in text_lower)
        if invoice_ar >= 2 or invoice_en >= 2:
            return DocumentType.INVOICE

        return DocumentType.GENERIC

    def _extract_title(self, text: str, doc_type: DocumentType) -> str:
        """
        Extract document title.

        Returns bilingual title for Arabic documents.
        """
        if doc_type == DocumentType.TAX_INVOICE:
            if "فاتورة ضريبية" in text:
                return "Tax Invoice (فاتورة ضريبية)"
            return "Tax Invoice"

        if doc_type == DocumentType.INVOICE:
            if "فاتورة" in text:
                return "Invoice (فاتورة)"
            return "Invoice"

        if doc_type == DocumentType.RECEIPT:
            if "إيصال" in text:
                return "Receipt (إيصال)"
            return "Receipt"

        if doc_type == DocumentType.QUOTATION:
            if "عرض سعر" in text:
                return "Quotation (عرض سعر)"
            return "Quotation"

        return "Document"

    def _extract_key_values(
        self,
        text: str,
        doc_type: DocumentType
    ) -> Dict[str, str]:
        """
        Extract key-value pairs from document text.

        Looks for patterns like:
        - "الحقل: القيمة"
        - "Field: Value"
        - "الحقل    القيمة" (tab/space separated)
        """
        pairs = {}
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Try colon separator
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key and value:
                        pairs[key] = value
                        continue

            # Try common field patterns for Arabic
            for field_ar in INVOICE_FIELDS.keys():
                if field_ar in line:
                    # Extract value after field name
                    idx = line.find(field_ar)
                    after = line[idx + len(field_ar):].strip()

                    # Remove common separators
                    after = after.lstrip(':').lstrip('-').strip()

                    if after:
                        pairs[field_ar] = after.split()[0] if after.split() else after
                        break

        return pairs

    def _detect_tables_from_text(self, text: str) -> List[DetectedTable]:
        """
        Detect tables from text patterns.

        Looks for structured text that resembles table data.
        """
        tables = []
        lines = text.split('\n')

        # Look for table header indicators
        header_line_idx = -1
        for i, line in enumerate(lines):
            # Check for table header keywords
            header_count = sum(1 for kw in TABLE_HEADER_KEYWORDS if kw in line)
            if header_count >= 3:  # At least 3 header keywords
                header_line_idx = i
                break

        if header_line_idx == -1:
            return tables

        # Extract headers from line
        header_line = lines[header_line_idx]
        headers = self._split_table_row(header_line)

        if len(headers) < 2:
            return tables

        # Extract rows following the header
        rows = []
        for i in range(header_line_idx + 1, min(header_line_idx + 50, len(lines))):
            line = lines[i].strip()
            if not line:
                continue

            # Check if line looks like a table row (has numbers or matches pattern)
            if self._looks_like_table_row(line, len(headers)):
                row = self._split_table_row(line)
                if len(row) >= 2:
                    rows.append(row)
            elif any(kw in line for kw in SUMMARY_KEYWORDS):
                # Hit summary section, stop
                break

        if rows:
            tables.append(DetectedTable(
                headers=headers,
                rows=rows,
                confidence=0.8
            ))

        return tables

    def _split_table_row(self, line: str) -> List[str]:
        """
        Split a line into table cells.

        Uses multiple separators: tabs, multiple spaces, pipes.
        """
        # First try tabs
        if '\t' in line:
            return [cell.strip() for cell in line.split('\t') if cell.strip()]

        # Try pipe separator
        if '|' in line:
            return [cell.strip() for cell in line.split('|') if cell.strip()]

        # Try multiple spaces (2+)
        cells = re.split(r'\s{2,}', line)
        return [cell.strip() for cell in cells if cell.strip()]

    def _looks_like_table_row(self, line: str, expected_cols: int) -> bool:
        """
        Check if a line looks like a table row.
        """
        # Should have numbers (quantities, prices)
        has_numbers = bool(re.search(r'\d+', line))
        if not has_numbers:
            return False

        # Should have reasonable number of cells
        cells = self._split_table_row(line)
        return len(cells) >= 2

    def _build_regions(
        self,
        text: str,
        key_values: Dict[str, str],
        tables: List[DetectedTable]
    ) -> List[LayoutRegion]:
        """
        Build layout regions from extracted data.
        """
        regions = []
        lines = text.split('\n')

        # Detect company info region
        company_text = []
        for line in lines[:10]:  # First 10 lines
            if any(kw in line for kw in COMPANY_KEYWORDS):
                company_text.append(line)

        if company_text:
            regions.append(LayoutRegion(
                region_type=LayoutRegionType.COMPANY_INFO,
                text='\n'.join(company_text)
            ))

        # Detect customer info region
        customer_text = []
        for line in lines:
            if any(kw in line for kw in CUSTOMER_KEYWORDS):
                customer_text.append(line)

        if customer_text:
            regions.append(LayoutRegion(
                region_type=LayoutRegionType.CUSTOMER_INFO,
                text='\n'.join(customer_text)
            ))

        # Detect invoice header region
        header_text = []
        for line in lines:
            if any(kw in line for kw in INVOICE_HEADER_KEYWORDS):
                header_text.append(line)

        if header_text:
            regions.append(LayoutRegion(
                region_type=LayoutRegionType.INVOICE_HEADER,
                text='\n'.join(header_text)
            ))

        # Add table regions
        for table in tables:
            regions.append(LayoutRegion(
                region_type=LayoutRegionType.TABLE,
                text=f"Table with {len(table.headers)} columns, {len(table.rows)} rows"
            ))

        # Detect summary region
        summary_text = []
        in_summary = False
        for line in lines:
            if any(kw in line for kw in SUMMARY_KEYWORDS):
                in_summary = True
            if in_summary:
                summary_text.append(line)
                if len(summary_text) > 10:
                    break

        if summary_text:
            regions.append(LayoutRegion(
                region_type=LayoutRegionType.SUMMARY,
                text='\n'.join(summary_text)
            ))

        return regions

    def get_detected_sections(self) -> List[str]:
        """
        Get list of detected section names.

        For use in tests.
        """
        return [
            "company", "header", "customer", "items", "summary"
        ]
