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
    get_english_fuzzy,
    get_all_fuzzy_matches,
    categorize_field,
    FUZZY_AVAILABLE,
)

# Import utilities for enhanced analysis
try:
    from ..utils.arabic_utils import normalize_arabic, is_arabic
    from ..utils.fuzzy_match import fuzzy_contains, fuzzy_best_match
    from ..utils.pattern_extractors import extract_all_patterns, extract_to_flat_dict
    ENHANCED_ANALYSIS = True
except ImportError:
    ENHANCED_ANALYSIS = False
    normalize_arabic = lambda x: x

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
        Uses fuzzy matching to handle OCR errors.
        """
        text_lower = text.lower()
        text_normalized = normalize_arabic(text) if ENHANCED_ANALYSIS else text

        # Check for tax invoice (most specific first)
        # Exact match
        if "فاتورة ضريبية" in text or "tax invoice" in text_lower:
            return DocumentType.TAX_INVOICE

        # Fuzzy match for tax invoice (handles OCR errors like "فانورة ضرسة")
        if ENHANCED_ANALYSIS and FUZZY_AVAILABLE:
            if (fuzzy_contains(text_normalized, "فاتورة ضريبية", threshold=70) or
                fuzzy_contains(text_normalized, "فاتورة", threshold=75)):
                # Check if it looks like an invoice with tax info
                tax_indicators = ["ضريب", "tax", "vat", "15%", "الرقم الضريبي"]
                if any(ind in text_lower or ind in text_normalized for ind in tax_indicators):
                    return DocumentType.TAX_INVOICE

        # Check for quotation
        quote_ar = sum(1 for kw in self.QUOTATION_KEYWORDS_AR if kw in text)
        quote_en = sum(1 for kw in self.QUOTATION_KEYWORDS_EN if kw in text_lower)

        # Fuzzy quotation check
        if ENHANCED_ANALYSIS and FUZZY_AVAILABLE and quote_ar == 0:
            for kw in self.QUOTATION_KEYWORDS_AR:
                if fuzzy_contains(text_normalized, kw, threshold=75):
                    quote_ar += 1
                    break

        if quote_ar >= 1 or quote_en >= 1:
            return DocumentType.QUOTATION

        # Check for receipt
        receipt_ar = sum(1 for kw in self.RECEIPT_KEYWORDS_AR if kw in text)
        receipt_en = sum(1 for kw in self.RECEIPT_KEYWORDS_EN if kw in text_lower)

        # Fuzzy receipt check
        if ENHANCED_ANALYSIS and FUZZY_AVAILABLE and receipt_ar == 0:
            for kw in self.RECEIPT_KEYWORDS_AR:
                if fuzzy_contains(text_normalized, kw, threshold=75):
                    receipt_ar += 1
                    break

        if receipt_ar >= 1 or receipt_en >= 1:
            return DocumentType.RECEIPT

        # Check for invoice (with lower threshold due to OCR errors)
        invoice_ar = sum(1 for kw in self.INVOICE_KEYWORDS_AR if kw in text)
        invoice_en = sum(1 for kw in self.INVOICE_KEYWORDS_EN if kw in text_lower)

        # Fuzzy invoice check - more lenient
        if ENHANCED_ANALYSIS and FUZZY_AVAILABLE:
            for kw in self.INVOICE_KEYWORDS_AR:
                if fuzzy_contains(text_normalized, kw, threshold=70):
                    invoice_ar += 0.5  # Partial credit for fuzzy match

        # Lower threshold: 1 match is enough with fuzzy matching
        if invoice_ar >= 1 or invoice_en >= 2:
            return DocumentType.INVOICE

        # Additional check: use pattern extractors to detect invoice-like content
        if ENHANCED_ANALYSIS:
            patterns = extract_to_flat_dict(text)
            # If we have structured data typical of invoices, it's likely an invoice
            invoice_signals = 0
            if 'total_amount' in patterns:
                invoice_signals += 1
            if 'tax_number' in patterns:
                invoice_signals += 1
            if 'date' in patterns:
                invoice_signals += 1
            if 'invoice_number' in patterns:
                invoice_signals += 1

            if invoice_signals >= 2:
                # Has tax number = likely tax invoice
                if 'tax_number' in patterns:
                    return DocumentType.TAX_INVOICE
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

        Uses fuzzy matching to handle OCR errors and extracts full values.
        """
        pairs = {}
        lines = text.split('\n')

        # First, use pattern extractors for structured fields
        if ENHANCED_ANALYSIS:
            patterns = extract_to_flat_dict(text)
            if 'date' in patterns:
                pairs['التاريخ'] = patterns['date']
            if 'total_amount' in patterns:
                pairs['الاجمالي'] = patterns['total_amount']
            if 'tax_number' in patterns:
                pairs['الرقم الضريبي'] = patterns['tax_number']
            if 'phone' in patterns:
                pairs['هاتف'] = patterns['phone']
            if 'invoice_number' in patterns:
                pairs['رقم الفاتورة'] = patterns['invoice_number']
            if 'time' in patterns:
                pairs['الوقت'] = patterns['time']

        # Use fuzzy matching for all fields
        if ENHANCED_ANALYSIS and FUZZY_AVAILABLE:
            fuzzy_matches = get_all_fuzzy_matches(text, threshold=65, limit=30)
            for match in fuzzy_matches:
                arabic_key = match.get('arabic', '')
                english_key = match.get('english', '')
                value = match.get('value', '')

                if english_key and value and english_key not in pairs:
                    # Store with Arabic key for consistency
                    pairs[arabic_key] = value

        # Traditional extraction as fallback
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Try colon separator (: or Arabic semicolon ؛)
            for delim in [':', '؛']:
                if delim in line:
                    parts = line.split(delim, 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        if key and value and key not in pairs:
                            # Try to get the canonical Arabic key via fuzzy match
                            if ENHANCED_ANALYSIS and FUZZY_AVAILABLE:
                                english, score = get_english_fuzzy(key, threshold=70)
                                if score >= 70:
                                    pairs[key] = value
                            else:
                                pairs[key] = value
                    break

            # Try common field patterns for Arabic with fuzzy matching
            if ENHANCED_ANALYSIS and FUZZY_AVAILABLE:
                for field_ar in list(INVOICE_FIELDS.keys())[:50]:  # Top 50 fields
                    if fuzzy_contains(line, field_ar, threshold=70):
                        # Extract full value after field name
                        # Find best match position
                        words = line.split()
                        for i, word in enumerate(words):
                            if fuzzy_contains(word, field_ar, threshold=70) or field_ar in word:
                                # Value is everything after
                                value = ' '.join(words[i+1:]) if i+1 < len(words) else ''
                                value = value.lstrip(':').lstrip('-').strip()
                                if value and field_ar not in pairs:
                                    pairs[field_ar] = value
                                break
                        break
            else:
                # Original logic for fallback
                for field_ar in INVOICE_FIELDS.keys():
                    if field_ar in line:
                        idx = line.find(field_ar)
                        after = line[idx + len(field_ar):].strip()
                        after = after.lstrip(':').lstrip('-').strip()
                        if after and field_ar not in pairs:
                            # Extract full value, not just first word
                            pairs[field_ar] = after
                        break

        return pairs

    def _detect_tables_from_text(self, text: str) -> List[DetectedTable]:
        """
        Detect tables from text patterns.

        Looks for structured text that resembles table data.
        Uses fuzzy matching for header detection with OCR errors.
        """
        tables = []
        lines = text.split('\n')

        # Look for table header indicators
        header_line_idx = -1
        for i, line in enumerate(lines):
            # Check for table header keywords with exact match
            header_count = sum(1 for kw in TABLE_HEADER_KEYWORDS if kw in line)

            # Also try fuzzy matching for headers
            if ENHANCED_ANALYSIS and FUZZY_AVAILABLE and header_count < 2:
                fuzzy_count = 0
                for kw in TABLE_HEADER_KEYWORDS:
                    if fuzzy_contains(line, kw, threshold=70):
                        fuzzy_count += 1
                header_count = max(header_count, fuzzy_count * 0.8)  # Weight fuzzy matches slightly lower

            # Lower threshold: 2 matches is enough (was 3)
            if header_count >= 2:
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
            # Check for summary section (fuzzy)
            elif ENHANCED_ANALYSIS and FUZZY_AVAILABLE:
                is_summary = any(fuzzy_contains(line, kw, threshold=70) for kw in SUMMARY_KEYWORDS)
                if is_summary:
                    break
            elif any(kw in line for kw in SUMMARY_KEYWORDS):
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
        Uses fuzzy matching for region detection with OCR errors.
        """
        regions = []
        lines = text.split('\n')

        def fuzzy_keyword_match(line: str, keywords: List[str]) -> bool:
            """Check if line matches any keyword (exact or fuzzy)."""
            # Exact match first
            if any(kw in line for kw in keywords):
                return True
            # Fuzzy match
            if ENHANCED_ANALYSIS and FUZZY_AVAILABLE:
                for kw in keywords:
                    if fuzzy_contains(line, kw, threshold=70):
                        return True
            return False

        # Detect company info region (first 15 lines)
        company_text = []
        for line in lines[:15]:
            if fuzzy_keyword_match(line, COMPANY_KEYWORDS):
                company_text.append(line)

        if company_text:
            regions.append(LayoutRegion(
                region_type=LayoutRegionType.COMPANY_INFO,
                text='\n'.join(company_text),
                confidence=0.85
            ))

        # Detect customer info region
        customer_text = []
        for line in lines:
            if fuzzy_keyword_match(line, CUSTOMER_KEYWORDS):
                customer_text.append(line)

        if customer_text:
            regions.append(LayoutRegion(
                region_type=LayoutRegionType.CUSTOMER_INFO,
                text='\n'.join(customer_text),
                confidence=0.85
            ))

        # Detect invoice header region
        header_text = []
        for line in lines:
            if fuzzy_keyword_match(line, INVOICE_HEADER_KEYWORDS):
                header_text.append(line)

        if header_text:
            regions.append(LayoutRegion(
                region_type=LayoutRegionType.INVOICE_HEADER,
                text='\n'.join(header_text),
                confidence=0.85
            ))

        # Add table regions
        for table in tables:
            regions.append(LayoutRegion(
                region_type=LayoutRegionType.TABLE,
                text=f"Table with {len(table.headers)} columns, {len(table.rows)} rows",
                confidence=table.confidence
            ))

        # Detect summary region
        summary_text = []
        in_summary = False
        for line in lines:
            if fuzzy_keyword_match(line, SUMMARY_KEYWORDS):
                in_summary = True
            if in_summary:
                summary_text.append(line)
                if len(summary_text) > 10:
                    break

        if summary_text:
            regions.append(LayoutRegion(
                region_type=LayoutRegionType.SUMMARY,
                text='\n'.join(summary_text),
                confidence=0.80
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
