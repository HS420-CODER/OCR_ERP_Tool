"""
Unit tests for formatters (Phase 1.5).
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.formatters.field_dictionary import (
    INVOICE_FIELDS,
    INVOICE_FIELDS_EN_AR,
    get_english,
    get_arabic,
    get_bilingual,
    is_arabic_text,
    is_bilingual_text,
    extract_field_value,
)
from src.formatters.document_analyzer import (
    DocumentType,
    DocumentAnalyzer,
    DocumentStructure,
    LayoutRegionType,
)
from src.formatters.output_formatter import StructuredOutputFormatter
from src.models import ReadResult, PageResult, TextBlock


class TestFieldDictionary:
    """Tests for field dictionary."""

    def test_invoice_fields_exist(self):
        """Test that key invoice fields exist."""
        assert "فاتورة" in INVOICE_FIELDS
        assert "فاتورة ضريبية" in INVOICE_FIELDS
        assert "التاريخ" in INVOICE_FIELDS
        assert "الاجمالي" in INVOICE_FIELDS
        assert "العميل" in INVOICE_FIELDS

    def test_invoice_fields_translations(self):
        """Test that translations are correct."""
        assert INVOICE_FIELDS["فاتورة"] == "Invoice"
        assert INVOICE_FIELDS["فاتورة ضريبية"] == "Tax Invoice"
        assert INVOICE_FIELDS["التاريخ"] == "Date"
        assert INVOICE_FIELDS["العميل"] == "Customer"

    def test_reverse_mapping(self):
        """Test English to Arabic reverse mapping."""
        assert "Invoice" in INVOICE_FIELDS_EN_AR
        assert INVOICE_FIELDS_EN_AR["Invoice"] == "فاتورة"
        # Note: "Date" maps to "تاريخ" (without ال), "التاريخ" maps to "Date"
        assert "Date" in INVOICE_FIELDS_EN_AR

    def test_get_english(self):
        """Test Arabic to English translation."""
        assert get_english("فاتورة") == "Invoice"
        assert get_english("التاريخ") == "Date"
        assert get_english("unknown") == "unknown"  # Returns original if not found

    def test_get_arabic(self):
        """Test English to Arabic translation."""
        assert get_arabic("Invoice") == "فاتورة"
        # Note: get_arabic returns the first matching Arabic term for "Date"
        arabic_date = get_arabic("Date")
        assert arabic_date != ""  # Should find a match
        assert get_arabic("unknown") == ""  # Returns empty if not found

    def test_get_bilingual_arabic_source(self):
        """Test bilingual output with Arabic source."""
        en, ar = get_bilingual("فاتورة", source_lang="ar")
        assert en == "Invoice"
        assert ar == "فاتورة"

    def test_get_bilingual_english_source(self):
        """Test bilingual output with English source."""
        en, ar = get_bilingual("Invoice", source_lang="en")
        assert en == "Invoice"
        assert ar == "فاتورة"

    def test_get_bilingual_auto_detect(self):
        """Test bilingual with auto language detection."""
        en, ar = get_bilingual("فاتورة")  # Arabic text
        assert en == "Invoice"
        assert ar == "فاتورة"

    def test_is_arabic_text(self):
        """Test Arabic text detection."""
        assert is_arabic_text("فاتورة ضريبية") == True
        assert is_arabic_text("Invoice") == False
        assert is_arabic_text("فاتورة Invoice") == True  # Mixed
        assert is_arabic_text("") == False

    def test_is_bilingual_text(self):
        """Test bilingual text detection."""
        assert is_bilingual_text("فاتورة ضريبية") == False  # Arabic only
        assert is_bilingual_text("Invoice") == False  # English only
        assert is_bilingual_text("فاتورة Invoice") == True  # Both


class TestDocumentAnalyzer:
    """Tests for DocumentAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        return DocumentAnalyzer()

    def test_detect_tax_invoice(self, analyzer):
        """Test tax invoice detection."""
        text = "فاتورة ضريبية\nالتاريخ: 2022-12-21\nالاجمالي: 2300"

        # Create mock ReadResult
        result = ReadResult(
            success=True,
            file_path="/test/invoice.png",
            file_type="image",
            engine_used="paddle",
            full_text=text
        )

        structure = analyzer.analyze(result)

        assert structure.document_type == DocumentType.TAX_INVOICE
        assert structure.is_bilingual == False
        assert structure.language == "ar"

    def test_detect_regular_invoice(self, analyzer):
        """Test regular invoice detection."""
        text = "فاتورة\nالبيان\nالكمية\nالسعر\nالاجمالي\nالصافي"

        result = ReadResult(
            success=True,
            file_path="/test/invoice.png",
            file_type="image",
            engine_used="paddle",
            full_text=text
        )

        structure = analyzer.analyze(result)

        assert structure.document_type == DocumentType.INVOICE

    def test_detect_bilingual_document(self, analyzer):
        """Test bilingual document detection."""
        text = "Tax Invoice فاتورة ضريبية\nDate التاريخ: 2022-12-21\nTotal الاجمالي: 2300"

        result = ReadResult(
            success=True,
            file_path="/test/invoice.png",
            file_type="image",
            engine_used="paddle",
            full_text=text
        )

        structure = analyzer.analyze(result)

        assert structure.is_bilingual == True
        assert structure.language == "bilingual"

    def test_extract_key_values(self, analyzer):
        """Test key-value pair extraction."""
        text = "التاريخ: 2022-12-21\nالوقت: 17:33:34\nالرقم: 220130"

        result = ReadResult(
            success=True,
            file_path="/test/invoice.png",
            file_type="image",
            engine_used="paddle",
            full_text=text
        )

        structure = analyzer.analyze(result)

        assert "التاريخ" in structure.key_value_pairs
        assert structure.key_value_pairs["التاريخ"] == "2022-12-21"

    def test_title_extraction(self, analyzer):
        """Test document title extraction."""
        text = "فاتورة ضريبية"

        result = ReadResult(
            success=True,
            file_path="/test/invoice.png",
            file_type="image",
            engine_used="paddle",
            full_text=text
        )

        structure = analyzer.analyze(result)

        assert "Tax Invoice" in structure.title
        assert "فاتورة ضريبية" in structure.title


class TestStructuredOutputFormatter:
    """Tests for StructuredOutputFormatter."""

    @pytest.fixture
    def formatter(self):
        return StructuredOutputFormatter()

    @pytest.fixture
    def sample_invoice_structure(self):
        """Create a sample invoice structure for testing."""
        from src.formatters.document_analyzer import DetectedTable

        return DocumentStructure(
            document_type=DocumentType.TAX_INVOICE,
            language="ar",
            is_bilingual=True,
            title="Tax Invoice (فاتورة ضريبية)",
            key_value_pairs={
                "التاريخ": "2022-12-21",
                "الموافق": "1444-05-27",
                "الوقت": "17:33:34",
                "الرقم": "220130",
                "العميل": "قرطاسية اصل",
                "العنوان": "الشوقية",
                "الاجمالي": "2000.00",
                "الصافي": "2000.00",
                "ضريبة القيمة المضافة": "300.00",
            },
            tables=[
                DetectedTable(
                    headers=["م", "البيان", "الكمية", "السعر", "الصافي"],
                    rows=[
                        ["1", "صيانة نظام الخوارزمي", "1", "2000.00", "2000.00"]
                    ]
                )
            ]
        )

    @pytest.fixture
    def sample_ocr_result(self):
        """Create a sample OCR result for testing."""
        return ReadResult(
            success=True,
            file_path="/test/invoice.png",
            file_type="image",
            engine_used="paddle",
            full_text="فاتورة ضريبية\nالتاريخ: 2022-12-21\nالاجمالي: 2000.00"
        )

    def test_format_invoice_markdown(self, formatter, sample_invoice_structure, sample_ocr_result):
        """Test invoice markdown formatting."""
        output = formatter.format(sample_ocr_result, sample_invoice_structure, "markdown")

        # Check title
        assert "# Tax Invoice (فاتورة ضريبية)" in output

        # Check sections exist
        assert "## Invoice Header" in output or "## Summary" in output

        # Check table headers
        assert "| م |" in output or "| البيان |" in output

    def test_format_has_bilingual_tables(self, formatter, sample_invoice_structure, sample_ocr_result):
        """Test that output has bilingual table structure."""
        output = formatter.format(sample_ocr_result, sample_invoice_structure, "markdown")

        # Should have table separators
        assert "|" in output
        assert "---" in output

    def test_format_json(self, formatter, sample_invoice_structure, sample_ocr_result):
        """Test JSON output format."""
        output = formatter.format(sample_ocr_result, sample_invoice_structure, "json")

        import json
        data = json.loads(output)

        assert data["document_type"] == "tax_invoice"
        assert data["is_bilingual"] == True
        assert "key_value_pairs" in data

    def test_format_text(self, formatter, sample_invoice_structure, sample_ocr_result):
        """Test plain text output format."""
        output = formatter.format(sample_ocr_result, sample_invoice_structure, "text")

        # Should return the full text
        assert "فاتورة ضريبية" in output

    def test_format_generic_document(self, formatter):
        """Test generic document formatting."""
        structure = DocumentStructure(
            document_type=DocumentType.GENERIC,
            language="en",
            is_bilingual=False,
            title="Document"
        )

        result = ReadResult(
            success=True,
            file_path="/test/doc.png",
            file_type="image",
            engine_used="paddle",
            full_text="Some generic content"
        )

        output = formatter.format(result, structure, "markdown")

        assert "# Document" in output


class TestIntegration:
    """Integration tests for formatters with read tool."""

    def test_arabic_text_processing(self):
        """Test complete Arabic text processing pipeline."""
        from src.formatters import DocumentAnalyzer, StructuredOutputFormatter

        # Simulate Arabic invoice text
        arabic_text = """
فاتورة ضريبية
شركة فضاء البرمجيات
التاريخ: 2022-12-21
الموافق: 1444-05-27
الرقم: 220130
العميل: قرطاسية اصل
الاجمالي: 2000.00
الصافي: 2000.00
ضريبة القيمة المضافة: 300.00
        """

        result = ReadResult(
            success=True,
            file_path="/test/invoice.png",
            file_type="image",
            engine_used="paddle",
            full_text=arabic_text
        )

        # Analyze
        analyzer = DocumentAnalyzer()
        structure = analyzer.analyze(result)

        assert structure.document_type == DocumentType.TAX_INVOICE
        assert structure.language == "ar"
        assert "التاريخ" in structure.key_value_pairs

        # Format
        formatter = StructuredOutputFormatter()
        output = formatter.format(result, structure, "markdown")

        assert "Tax Invoice" in output
        assert "فاتورة ضريبية" in output


class TestFieldDictionaryCompleteness:
    """Tests for field dictionary completeness based on reference."""

    def test_all_reference_fields_exist(self):
        """Test that all fields from Skysoft-Fatoora.md reference exist."""
        required_fields = [
            # Company info
            "شركة فضاء البرمجيات",
            "لتقنية المعلومات",
            "هاتف",
            "الرقم الضريبي",
            # Invoice header
            "التاريخ",
            "الموافق",
            "الوقت",
            "النوع",
            "المرجع",
            "العملة",
            "المندوب",
            "الصفحة",
            # Customer
            "العميل",
            "العنوان",
            "الرصيد",
            "التلفون",
            # Items
            "البيان",
            "الكمية",
            "الوحدة",
            "السعر",
            "الصافي",
            "ضريبة القيمة المضافة",
            # Summary
            "الاجمالي",
            "الاضافات",
            "الخصم",
            # Payment
            "البائع",
            "المستلم",
            "آجل",
            "نقدي",
        ]

        for field in required_fields:
            assert field in INVOICE_FIELDS, f"Missing field: {field}"
