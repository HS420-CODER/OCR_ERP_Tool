"""
Structured Output Formatter for Claude Code-like output.

Formats OCR results into structured markdown with:
- Bilingual tables (English | Arabic)
- Semantic sections (Company, Header, Items, Summary)
- Invoice-specific templates
- JSON structured output

Based on Claude Code reference: examples/Skysoft-Fatoora.md
"""

import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .document_analyzer import (
    DocumentStructure,
    DocumentType,
    LayoutRegionType,
    DetectedTable
)
from .field_dictionary import (
    INVOICE_FIELDS,
    SECTION_HEADERS,
    get_english,
    get_arabic,
    is_arabic_text,
    get_english_fuzzy,
    FUZZY_AVAILABLE,
)

# Import enhanced utilities
try:
    from ..utils.arabic_utils import normalize_arabic
    from ..utils.fuzzy_match import fuzzy_contains, fuzzy_best_match
    from ..utils.pattern_extractors import extract_to_flat_dict
    ENHANCED_FORMATTING = True
except ImportError:
    ENHANCED_FORMATTING = False
    normalize_arabic = lambda x: x

logger = logging.getLogger(__name__)


class StructuredOutputFormatter:
    """
    Formats OCR results into structured output.

    Produces Claude Code CLI-like output with:
    - Bilingual markdown tables
    - Semantic document sections
    - Invoice-specific formatting
    - JSON structured data

    Example output:
    ```markdown
    # Tax Invoice (فاتورة ضريبية)

    ## Company Information

    | English | Arabic |
    |---------|--------|
    | Skysoft Co. | شركة فضاء البرمجيات |

    ## Invoice Items (البيان)

    | م | البيان | الكمية | السعر |
    |---|--------|--------|-------|
    | 1 | صيانة نظام | 1 | 2,000.00 |
    ```
    """

    def format(
        self,
        ocr_result: Any,
        structure: DocumentStructure,
        output_format: str = "markdown"
    ) -> str:
        """
        Format OCR result into structured output.

        Args:
            ocr_result: ReadResult with OCR data
            structure: Analyzed document structure
            output_format: Output format ("markdown", "json", "text")

        Returns:
            Formatted string output
        """
        if output_format == "markdown":
            return self._format_markdown(ocr_result, structure)
        elif output_format == "json":
            return self._format_json(ocr_result, structure)
        else:
            return self._format_text(ocr_result, structure)

    def _format_markdown(
        self,
        ocr_result: Any,
        structure: DocumentStructure
    ) -> str:
        """
        Format as structured markdown (Claude Code style).
        """
        if structure.document_type in (DocumentType.INVOICE, DocumentType.TAX_INVOICE):
            return self._format_invoice_markdown(ocr_result, structure)
        elif structure.document_type == DocumentType.RECEIPT:
            return self._format_receipt_markdown(ocr_result, structure)
        else:
            return self._format_generic_markdown(ocr_result, structure)

    def _format_invoice_markdown(
        self,
        ocr_result: Any,
        structure: DocumentStructure
    ) -> str:
        """
        Format invoice as structured markdown.

        Produces output matching Claude Code reference.
        """
        lines = []
        kv = structure.key_value_pairs

        # =================================================================
        # TITLE
        # =================================================================
        lines.append(f"# {structure.title}")
        lines.append("")

        # =================================================================
        # COMPANY INFORMATION
        # =================================================================
        company_pairs = self._extract_company_info(kv)
        if company_pairs:
            lines.append("## Company Information")
            lines.append("")
            lines.append("| English | Arabic |")
            lines.append("|---------|--------|")

            for en, ar in company_pairs:
                lines.append(f"| {en} | {ar} |")

            lines.append("")
            lines.append("---")
            lines.append("")

        # =================================================================
        # INVOICE HEADER
        # =================================================================
        header_pairs = self._extract_invoice_header(kv)
        if header_pairs:
            lines.append("## Invoice Header")
            lines.append("")
            lines.append("| Field | Value | الحقل |")
            lines.append("|-------|-------|-------|")

            for en_name, value, ar_name in header_pairs:
                lines.append(f"| {en_name} | {value} | {ar_name} |")

            lines.append("")
            lines.append("---")
            lines.append("")

        # =================================================================
        # CUSTOMER INFORMATION
        # =================================================================
        customer_pairs = self._extract_customer_info(kv)
        if customer_pairs:
            lines.append("## Customer Information (العميل)")
            lines.append("")
            lines.append("| Field | Value |")
            lines.append("|-------|-------|")

            for en_name, ar_name, value in customer_pairs:
                lines.append(f"| {en_name} ({ar_name}) | {value} |")

            lines.append("")
            lines.append("---")
            lines.append("")

        # =================================================================
        # INVOICE ITEMS (TABLE)
        # =================================================================
        if structure.tables:
            lines.append("## Invoice Items (البيان)")
            lines.append("")

            for table in structure.tables:
                lines.extend(self._format_table_markdown(table))

            lines.append("")
            lines.append("---")
            lines.append("")

        # =================================================================
        # SUMMARY
        # =================================================================
        summary_pairs = self._extract_summary(kv)
        if summary_pairs:
            lines.append("## Summary (ملخص)")
            lines.append("")
            lines.append("| Field | Value |")
            lines.append("|-------|-------|")

            for ar_name, en_name, value in summary_pairs:
                lines.append(f"| {ar_name} ({en_name}) | {value} |")

            lines.append("")

        # =================================================================
        # AMOUNT IN WORDS
        # =================================================================
        amount_words = self._extract_amount_in_words(kv, ocr_result)
        if amount_words:
            lines.append("")
            lines.append(f"**{amount_words['arabic']}**")
            if amount_words.get('english'):
                lines.append(f"({amount_words['english']})")
            lines.append("")

        # =================================================================
        # SIGNATURES
        # =================================================================
        lines.append("---")
        lines.append("")
        lines.append("## Signatures")
        lines.append("")
        lines.append("| البائع (Seller) | المستلم (Receiver) |")
        lines.append("|-----------------|-------------------|")
        lines.append("| | |")
        lines.append("")

        # =================================================================
        # ADDITIONAL INFO
        # =================================================================
        additional = self._extract_additional_info(kv)
        if additional:
            lines.append("---")
            lines.append("")
            lines.append("## Additional Info")
            lines.append("")

            for ar_name, en_name, value in additional:
                lines.append(f"- {ar_name} ({en_name}): {value}")

            lines.append("")

        return '\n'.join(lines)

    def _format_table_markdown(self, table: DetectedTable) -> List[str]:
        """
        Format a table as markdown.
        """
        lines = []

        if not table.headers and not table.rows:
            return lines

        headers = table.headers if table.headers else []
        rows = table.rows if table.rows else []

        # Determine column count
        col_count = max(
            len(headers),
            max((len(row) for row in rows), default=0)
        )

        if col_count == 0:
            return lines

        # Header row
        if headers:
            # Pad headers if needed
            padded_headers = headers + [''] * (col_count - len(headers))
            lines.append("| " + " | ".join(padded_headers) + " |")
            lines.append("|" + "|".join(["---"] * col_count) + "|")
        else:
            # Generate generic headers
            lines.append("| " + " | ".join([f"Col {i+1}" for i in range(col_count)]) + " |")
            lines.append("|" + "|".join(["---"] * col_count) + "|")

        # Data rows
        for row in rows:
            # Pad row if needed
            padded_row = list(row) + [''] * (col_count - len(row))
            cells = [str(cell) for cell in padded_row]
            lines.append("| " + " | ".join(cells) + " |")

        return lines

    def _format_receipt_markdown(
        self,
        ocr_result: Any,
        structure: DocumentStructure
    ) -> str:
        """
        Format receipt as structured markdown.
        """
        lines = []

        lines.append(f"# {structure.title}")
        lines.append("")

        # Key-value pairs as simple list
        if structure.key_value_pairs:
            lines.append("## Details")
            lines.append("")

            for key, value in structure.key_value_pairs.items():
                en_key = get_english(key)
                if en_key != key:
                    lines.append(f"- **{en_key}** ({key}): {value}")
                else:
                    lines.append(f"- **{key}**: {value}")

            lines.append("")

        # Tables
        if structure.tables:
            lines.append("## Items")
            lines.append("")

            for table in structure.tables:
                lines.extend(self._format_table_markdown(table))

            lines.append("")

        return '\n'.join(lines)

    def _format_generic_markdown(
        self,
        ocr_result: Any,
        structure: DocumentStructure
    ) -> str:
        """
        Format generic document as markdown.
        """
        lines = []

        # Title
        lang_indicator = structure.language.upper()
        lines.append(f"# Document ({lang_indicator})")
        lines.append("")

        # Content section
        if structure.is_bilingual:
            lines.append("## Content")
            lines.append("")
            lines.append("| English | العربية |")
            lines.append("|---------|---------|")

            # Process key-value pairs
            for key, value in structure.key_value_pairs.items():
                if is_arabic_text(key):
                    en_key = get_english(key)
                    lines.append(f"| {en_key}: {value} | {key}: {value} |")
                else:
                    ar_key = get_arabic(key)
                    lines.append(f"| {key}: {value} | {ar_key}: {value} |")

            lines.append("")
        else:
            # Single language output
            lines.append("## Content")
            lines.append("")

            if hasattr(ocr_result, 'full_text'):
                lines.append(ocr_result.full_text)
            elif structure.key_value_pairs:
                for key, value in structure.key_value_pairs.items():
                    lines.append(f"- **{key}**: {value}")

        # Tables
        if structure.tables:
            lines.append("")
            lines.append("## Tables")
            lines.append("")

            for i, table in enumerate(structure.tables):
                lines.append(f"### Table {i + 1}")
                lines.append("")
                lines.extend(self._format_table_markdown(table))
                lines.append("")

        return '\n'.join(lines)

    def _format_json(
        self,
        ocr_result: Any,
        structure: DocumentStructure
    ) -> str:
        """
        Format as JSON structured output.
        """
        data = structure.to_dict()

        # Add full text if available
        if hasattr(ocr_result, 'full_text'):
            data['full_text'] = ocr_result.full_text

        return json.dumps(data, ensure_ascii=False, indent=2)

    def _format_text(
        self,
        ocr_result: Any,
        structure: DocumentStructure
    ) -> str:
        """
        Format as plain text.
        """
        if hasattr(ocr_result, 'full_text'):
            return ocr_result.full_text
        return ""

    # =========================================================================
    # EXTRACTION HELPERS
    # =========================================================================

    def _fuzzy_key_match(self, kv: Dict[str, str], target_ar: str) -> Optional[str]:
        """
        Find a key in kv dict that fuzzy matches the target Arabic key.

        Returns the value if found, None otherwise.
        """
        # Exact match first
        if target_ar in kv:
            return kv[target_ar]

        # Fuzzy match
        if ENHANCED_FORMATTING and FUZZY_AVAILABLE:
            target_normalized = normalize_arabic(target_ar)
            for key, value in kv.items():
                key_normalized = normalize_arabic(key)
                if fuzzy_contains(key_normalized, target_normalized, threshold=70):
                    return value
                # Also check if target is in key
                if target_normalized in key_normalized or key_normalized in target_normalized:
                    return value

        return None

    def _extract_company_info(
        self,
        kv: Dict[str, str]
    ) -> List[tuple]:
        """
        Extract company information as (english, arabic) pairs.
        Uses fuzzy matching to handle OCR errors.
        """
        pairs = []

        company_fields = [
            ("شركة", "Company"),
            ("شركة فضاء البرمجيات", "Skysoft Co."),
            ("لتقنية المعلومات", "For Information Technology"),
            ("للحلول المالية والادارية", "For Financial and Administrative Solutions"),
            ("هاتف", "Phone"),
            ("الرقم الضريبي", "Tax Number"),
            ("السجل التجاري", "Commercial Registration"),
        ]

        for ar, en in company_fields:
            value = self._fuzzy_key_match(kv, ar)
            if value:
                pairs.append((f"{en}: {value}", f"{ar}: {value}"))
            else:
                # Check if it appears as a value in any key
                for key, val in kv.items():
                    if ar in key or ar in val:
                        pairs.append((en, ar))
                        break
                    # Fuzzy check in values
                    if ENHANCED_FORMATTING and FUZZY_AVAILABLE:
                        if fuzzy_contains(val, ar, threshold=70):
                            pairs.append((en, ar))
                            break

        return pairs

    def _extract_invoice_header(
        self,
        kv: Dict[str, str]
    ) -> List[tuple]:
        """
        Extract invoice header as (english_name, value, arabic_name) tuples.
        Uses fuzzy matching to handle OCR errors.
        """
        pairs = []

        header_fields = [
            ("التاريخ", "Date"),
            ("الموافق", "Hijri Date"),
            ("الوقت", "Time"),
            ("الرقم", "Invoice No."),
            ("رقم الفاتورة", "Invoice No."),
            ("النوع", "Type"),
            ("المرجع", "Reference"),
            ("العملة", "Currency"),
            ("المندوب", "Representative"),
            ("الصفحة", "Page"),
            ("الصرف", "Dispatch"),
        ]

        seen_en = set()  # Avoid duplicate English labels
        for ar, en in header_fields:
            if en in seen_en:
                continue
            value = self._fuzzy_key_match(kv, ar)
            if value:
                pairs.append((en, value, ar))
                seen_en.add(en)

        return pairs

    def _extract_customer_info(
        self,
        kv: Dict[str, str]
    ) -> List[tuple]:
        """
        Extract customer info as (english_name, arabic_name, value) tuples.
        Uses fuzzy matching to handle OCR errors.
        """
        pairs = []

        customer_fields = [
            ("العميل", "Customer"),
            ("العنوان", "Address"),
            ("الرصيد", "Balance"),
            ("الرقم الضريبي", "Tax Number"),
            ("التلفون", "Phone"),
            ("السائق", "Driver"),
            ("الوجهة", "Destination"),
            ("الشوفية", "Delivery"),
        ]

        for ar, en in customer_fields:
            value = self._fuzzy_key_match(kv, ar)
            if value:
                pairs.append((en, ar, value))

        return pairs

    def _extract_summary(
        self,
        kv: Dict[str, str]
    ) -> List[tuple]:
        """
        Extract summary fields as (arabic_name, english_name, value) tuples.
        Uses fuzzy matching to handle OCR errors.
        """
        pairs = []

        summary_fields = [
            ("الاجمالي", "Total"),
            ("الاضافات", "Additions"),
            ("الاجمالي الكلي", "Grand Total"),
            ("الخصم", "Discount"),
            ("الصافي", "Net"),
            ("ضريبة القيمة المضافة", "VAT"),
            ("اجمالي ضريبة القيمة المضافة", "Total VAT"),
            ("الصافي شامل ض.ق", "Net including VAT"),
            ("إجمالي الكمية", "Total Quantity"),
            ("الاستحقاق", "Due"),
        ]

        for ar, en in summary_fields:
            value = self._fuzzy_key_match(kv, ar)
            if value:
                pairs.append((ar, en, value))

        return pairs

    def _extract_amount_in_words(
        self,
        kv: Dict[str, str],
        ocr_result: Any
    ) -> Optional[Dict[str, str]]:
        """
        Extract amount in words (Arabic and English).
        """
        full_text = ""
        if hasattr(ocr_result, 'full_text'):
            full_text = ocr_result.full_text

        # Look for "فقط ... لاغير" pattern
        import re
        pattern = r'فقط\s+(.+?)\s+لاغير'
        match = re.search(pattern, full_text)

        if match:
            arabic_words = f"فقط {match.group(1)} لاغير"
            return {
                "arabic": arabic_words,
                "english": ""  # Would need translation
            }

        return None

    def _extract_additional_info(
        self,
        kv: Dict[str, str]
    ) -> List[tuple]:
        """
        Extract additional info as (arabic_name, english_name, value) tuples.
        """
        pairs = []

        additional_fields = [
            ("الاستحقاق", "Due Date"),
            ("المستخدم", "User"),
            ("رقم النسخة", "Copy No."),
            ("ملاحظات", "Notes"),
        ]

        for ar, en in additional_fields:
            if ar in kv:
                value = kv[ar]
                pairs.append((ar, en, value))

        return pairs
