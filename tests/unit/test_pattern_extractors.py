"""
Tests for pattern-based field extraction.
"""

import pytest
from src.utils.pattern_extractors import (
    extract_dates,
    extract_amounts,
    extract_phone_numbers,
    extract_tax_numbers,
    extract_invoice_numbers,
    extract_times,
    extract_percentages,
    extract_all_patterns,
    extract_to_flat_dict,
    identify_invoice_sections,
    ExtractedField,
)


class TestExtractDates:
    """Tests for date extraction."""

    def test_iso_date(self):
        """Extract ISO format date (YYYY-MM-DD)."""
        dates = extract_dates("Date: 2024-12-21")
        assert len(dates) >= 1
        assert "2024-12-21" in [d.value for d in dates]

    def test_iso_date_with_slash(self):
        """Extract ISO format date with slash."""
        dates = extract_dates("Date: 2024/12/21")
        assert len(dates) >= 1

    def test_dmy_date(self):
        """Extract DMY format date."""
        dates = extract_dates("Date: 21-12-2024")
        assert len(dates) >= 1

    def test_multiple_dates(self):
        """Extract multiple dates."""
        text = "Start: 2024-01-01 End: 2024-12-31"
        dates = extract_dates(text)
        assert len(dates) >= 2

    def test_no_dates(self):
        """Handle text without dates."""
        dates = extract_dates("No dates here")
        assert len(dates) == 0


class TestExtractAmounts:
    """Tests for amount extraction."""

    def test_simple_amount(self):
        """Extract simple decimal amount."""
        amounts = extract_amounts("Total: 1234.56")
        assert len(amounts) >= 1
        assert any(a.value == "1234.56" for a in amounts)

    def test_amount_with_thousands(self):
        """Extract amount with thousands separator."""
        amounts = extract_amounts("Total: 1,234.56 SAR")
        assert len(amounts) >= 1

    def test_amount_with_currency(self):
        """Extract amount with currency."""
        amounts = extract_amounts("المبلغ: 2,300.00 ريال")
        assert len(amounts) >= 1

    def test_multiple_amounts(self):
        """Extract multiple amounts."""
        text = "Subtotal: 100.00 Tax: 15.00 Total: 115.00"
        amounts = extract_amounts(text)
        assert len(amounts) >= 3

    def test_no_amounts(self):
        """Handle text without amounts."""
        amounts = extract_amounts("No amounts here")
        assert len(amounts) == 0


class TestExtractPhoneNumbers:
    """Tests for phone number extraction."""

    def test_saudi_920_number(self):
        """Extract Saudi 920 customer service number."""
        phones = extract_phone_numbers("Call 920002762")
        assert len(phones) >= 1
        assert any(p.value == "920002762" for p in phones)

    def test_saudi_9200_number(self):
        """Extract Saudi 9200 number."""
        phones = extract_phone_numbers("Phone: 920012345")
        assert len(phones) >= 1

    def test_toll_free_number(self):
        """Extract toll-free number."""
        phones = extract_phone_numbers("Toll free: 8001234567")
        assert len(phones) >= 1

    def test_no_phone_numbers(self):
        """Handle text without phone numbers."""
        phones = extract_phone_numbers("No phones here")
        assert len(phones) == 0


class TestExtractTaxNumbers:
    """Tests for tax number extraction."""

    def test_15_digit_tax_number(self):
        """Extract 15-digit tax number."""
        tax_numbers = extract_tax_numbers("Tax Number 311297284200003")
        assert len(tax_numbers) >= 1
        assert any(t.value == "311297284200003" for t in tax_numbers)

    def test_no_tax_numbers(self):
        """Handle text without tax numbers."""
        tax_numbers = extract_tax_numbers("No tax numbers 12345")
        # 5 digits shouldn't match
        assert all(len(t.value) == 15 for t in tax_numbers)


class TestExtractInvoiceNumbers:
    """Tests for invoice number extraction."""

    def test_alphanumeric_invoice(self):
        """Extract alphanumeric invoice number."""
        invoices = extract_invoice_numbers("Invoice: A-12345")
        assert len(invoices) >= 1
        assert any("A-12345" in i.value for i in invoices)

    def test_prefix_invoice(self):
        """Extract invoice with prefix."""
        invoices = extract_invoice_numbers("INV-123456")
        assert len(invoices) >= 1

    def test_no_invoice_numbers(self):
        """Handle text without invoice numbers."""
        invoices = extract_invoice_numbers("No invoices")
        assert len(invoices) == 0


class TestExtractTimes:
    """Tests for time extraction."""

    def test_24_hour_time(self):
        """Extract 24-hour format time."""
        times = extract_times("Time: 17:33:34")
        assert len(times) >= 1
        assert any("17:33" in t.value for t in times)

    def test_short_time(self):
        """Extract short time format."""
        times = extract_times("Time: 14:30")
        assert len(times) >= 1

    def test_no_times(self):
        """Handle text without times."""
        times = extract_times("No times here")
        assert len(times) == 0


class TestExtractPercentages:
    """Tests for percentage extraction."""

    def test_integer_percentage(self):
        """Extract integer percentage."""
        percentages = extract_percentages("VAT: 15%")
        assert len(percentages) >= 1
        assert any(p.value == "15" for p in percentages)

    def test_decimal_percentage(self):
        """Extract decimal percentage."""
        percentages = extract_percentages("Rate: 15.5%")
        assert len(percentages) >= 1

    def test_no_percentages(self):
        """Handle text without percentages."""
        percentages = extract_percentages("No percentages")
        assert len(percentages) == 0


class TestExtractAllPatterns:
    """Tests for extract_all_patterns function."""

    def test_extract_all(self):
        """Extract all pattern types."""
        text = """
        Invoice: A-2
        Date: 2024-12-21
        Time: 17:33:34
        Total: 2,300.00 SAR
        VAT: 15%
        Tax Number: 311297284200003
        Phone: 920002762
        """
        results = extract_all_patterns(text)

        assert 'dates' in results
        assert 'amounts' in results
        assert 'phone_numbers' in results
        assert 'tax_numbers' in results
        assert 'invoice_numbers' in results
        assert 'times' in results
        assert 'percentages' in results


class TestExtractToFlatDict:
    """Tests for extract_to_flat_dict function."""

    def test_flat_dict(self):
        """Extract to flat dictionary."""
        text = """
        Date: 2024-12-21
        Total: 2,300.00 SAR
        Phone: 920002762
        """
        result = extract_to_flat_dict(text)

        assert 'date' in result or 'total_amount' in result
        if 'date' in result:
            assert '2024' in result['date']

    def test_empty_text(self):
        """Handle empty text."""
        result = extract_to_flat_dict("")
        assert isinstance(result, dict)


class TestIdentifyInvoiceSections:
    """Tests for invoice section identification."""

    def test_identify_sections(self):
        """Identify invoice sections."""
        text = """
        شركة فضاء البرمجيات
        Company Name

        العميل: قرطاسية اصل
        Customer information

        البيان الكمية السعر
        صيانة 1 2000

        الاجمالي 2300
        Total amount
        """
        sections = identify_invoice_sections(text)

        # Should identify at least some sections
        assert isinstance(sections, dict)


class TestExtractedFieldDataclass:
    """Tests for ExtractedField dataclass."""

    def test_to_dict(self):
        """Test to_dict conversion."""
        field = ExtractedField(
            field_type='date',
            value='2024-12-21',
            raw_match='2024-12-21',
            start=10,
            end=20,
            confidence=0.95
        )
        d = field.to_dict()

        assert d['type'] == 'date'
        assert d['value'] == '2024-12-21'
        assert d['confidence'] == 0.95
        assert d['position'] == (10, 20)
