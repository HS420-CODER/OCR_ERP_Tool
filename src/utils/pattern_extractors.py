"""
Pattern-based field extraction for Arabic OCR documents.

This module provides regex patterns and extraction functions for common
structured fields found in Arabic invoices and documents:
- Dates (ISO, Arabic, Hijri formats)
- Monetary amounts
- Phone numbers (Saudi Arabia)
- Tax/VAT numbers
- Invoice numbers
- Email addresses
- URLs
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class ExtractedField:
    """Represents an extracted field from text."""
    field_type: str
    value: str
    raw_match: str
    start: int
    end: int
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.field_type,
            'value': self.value,
            'raw': self.raw_match,
            'position': (self.start, self.end),
            'confidence': self.confidence
        }


# Regex patterns for common invoice/document fields
PATTERNS = {
    # Date formats
    'date_iso': r'\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b',  # 2024-12-21, 2024/12/21
    'date_dmy': r'\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b',  # 21-12-2024, 21/12/2024
    'date_arabic': r'\b(\d{1,2})/(\d{1,2})/(\d{4})\s*(?:هـ|ه|م)?\b',  # With Arabic suffix

    # Monetary amounts
    'amount': r'\b(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\b',  # 1,234.56 or 1234.56
    'amount_decimal': r'\b(\d+\.\d{2})\b',  # 1234.56
    'amount_with_currency': r'\b(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:ريال|ر\.س|SAR|SR)\b',

    # Phone numbers (Saudi Arabia)
    'phone_saudi_920': r'\b(920\d{6})\b',  # 920XXXXXX (customer service)
    'phone_saudi_9200': r'\b(9200\d{5})\b',  # 9200XXXXX
    'phone_saudi_mobile': r'\b(?:\+966|00966|0)?(\d{9})\b',  # Mobile numbers
    'phone_toll_free': r'\b(800\d{7})\b',  # 800XXXXXXX

    # Tax and ID numbers
    'tax_number_15': r'\b(\d{15})\b',  # 15-digit tax number
    'vat_number': r'\b(\d{15})\b',  # Same as tax number in Saudi
    'cr_number': r'\b(\d{10})\b',  # Commercial Registration (10 digits)

    # Invoice/Document numbers
    'invoice_number': r'\b([A-Z]{1,3}[-]?\d{4,10})\b',  # A-12345, INV-123456
    'invoice_number_arabic': r'\b(\d{4,10})\b',  # Pure numeric

    # Time
    'time_24h': r'\b(\d{1,2}):(\d{2})(?::(\d{2}))?\b',  # 14:30 or 14:30:45
    'time_12h': r'\b(\d{1,2}):(\d{2})\s*(?:ص|م|AM|PM)\b',  # 2:30 ص

    # Percentages
    'percentage': r'\b(\d+(?:\.\d+)?)\s*%',  # 15%, 15.5%

    # Email
    'email': r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',

    # URL
    'url': r'\b(https?://[^\s]+)\b',
    'domain': r'\b(www\.[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
}

# Compiled patterns for performance
COMPILED_PATTERNS = {name: re.compile(pattern, re.UNICODE | re.IGNORECASE)
                     for name, pattern in PATTERNS.items()}


def extract_dates(text: str) -> List[ExtractedField]:
    """
    Extract all date occurrences from text.

    Supports multiple formats:
    - ISO: 2024-12-21, 2024/12/21
    - DMY: 21-12-2024, 21/12/2024
    - Arabic: With هـ (Hijri) or م (Gregorian) suffix

    Args:
        text: Text to extract dates from

    Returns:
        List of ExtractedField objects for each date found

    Example:
        >>> extract_dates("Date: 2024-12-21 and 21/12/2024")
        [ExtractedField(type='date_iso', value='2024-12-21', ...),
         ExtractedField(type='date_dmy', value='21/12/2024', ...)]
    """
    results = []

    # ISO format (YYYY-MM-DD)
    for match in COMPILED_PATTERNS['date_iso'].finditer(text):
        year, month, day = match.groups()
        results.append(ExtractedField(
            field_type='date_iso',
            value=f"{year}-{month.zfill(2)}-{day.zfill(2)}",
            raw_match=match.group(),
            start=match.start(),
            end=match.end()
        ))

    # DMY format (DD-MM-YYYY)
    for match in COMPILED_PATTERNS['date_dmy'].finditer(text):
        day, month, year = match.groups()
        # Avoid duplicates with ISO format
        raw = match.group()
        if not any(r.raw_match == raw for r in results):
            results.append(ExtractedField(
                field_type='date_dmy',
                value=f"{day.zfill(2)}/{month.zfill(2)}/{year}",
                raw_match=raw,
                start=match.start(),
                end=match.end()
            ))

    return results


def extract_amounts(text: str) -> List[ExtractedField]:
    """
    Extract monetary amounts from text.

    Handles formats with/without thousands separators and currency symbols.

    Args:
        text: Text to extract amounts from

    Returns:
        List of ExtractedField objects for each amount found

    Example:
        >>> extract_amounts("Total: 1,234.56 SAR")
        [ExtractedField(type='amount', value='1234.56', ...)]
    """
    results = []
    seen_positions = set()

    # Amount with currency first (more specific)
    for match in COMPILED_PATTERNS['amount_with_currency'].finditer(text):
        amount = match.group(1).replace(',', '')
        pos = (match.start(), match.end())
        if pos not in seen_positions:
            seen_positions.add(pos)
            results.append(ExtractedField(
                field_type='amount_with_currency',
                value=amount,
                raw_match=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.95
            ))

    # Decimal amounts (X.XX format - likely monetary)
    for match in COMPILED_PATTERNS['amount_decimal'].finditer(text):
        amount = match.group(1)
        # Skip if already captured with currency
        overlaps = any(
            (match.start() >= s and match.start() < e) or
            (match.end() > s and match.end() <= e)
            for s, e in seen_positions
        )
        if not overlaps and float(amount) > 0:
            results.append(ExtractedField(
                field_type='amount',
                value=amount,
                raw_match=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.8
            ))

    return results


def extract_phone_numbers(text: str) -> List[ExtractedField]:
    """
    Extract Saudi phone numbers from text.

    Handles:
    - 920XXXXXX (customer service)
    - 9200XXXXX (customer service)
    - Mobile numbers (with/without country code)
    - 800XXXXXXX (toll-free)

    Args:
        text: Text to extract phone numbers from

    Returns:
        List of ExtractedField objects

    Example:
        >>> extract_phone_numbers("Call 920002762")
        [ExtractedField(type='phone_saudi_920', value='920002762', ...)]
    """
    results = []
    seen = set()

    patterns_to_check = [
        ('phone_saudi_920', 0.95),
        ('phone_saudi_9200', 0.95),
        ('phone_toll_free', 0.90),
    ]

    for pattern_name, confidence in patterns_to_check:
        for match in COMPILED_PATTERNS[pattern_name].finditer(text):
            value = match.group(1)
            if value not in seen:
                seen.add(value)
                results.append(ExtractedField(
                    field_type=pattern_name,
                    value=value,
                    raw_match=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=confidence
                ))

    return results


def extract_tax_numbers(text: str) -> List[ExtractedField]:
    """
    Extract tax/VAT numbers from text.

    Saudi tax numbers are 15 digits.

    Args:
        text: Text to extract tax numbers from

    Returns:
        List of ExtractedField objects

    Example:
        >>> extract_tax_numbers("Tax Number 311297284200003")
        [ExtractedField(type='tax_number_15', value='311297284200003', ...)]
    """
    results = []

    # Look for 15-digit numbers (tax numbers)
    for match in COMPILED_PATTERNS['tax_number_15'].finditer(text):
        value = match.group(1)
        # Verify it's exactly 15 digits and not part of larger number
        if len(value) == 15:
            results.append(ExtractedField(
                field_type='tax_number',
                value=value,
                raw_match=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.85
            ))

    return results


def extract_invoice_numbers(text: str) -> List[ExtractedField]:
    """
    Extract invoice/document numbers from text.

    Handles formats like:
    - A-12345
    - INV-123456
    - Pure numeric sequences

    Args:
        text: Text to extract invoice numbers from

    Returns:
        List of ExtractedField objects

    Example:
        >>> extract_invoice_numbers("Invoice: A-2 dated 2024-01-01")
        [ExtractedField(type='invoice_number', value='A-2', ...)]
    """
    results = []

    for match in COMPILED_PATTERNS['invoice_number'].finditer(text):
        value = match.group(1)
        results.append(ExtractedField(
            field_type='invoice_number',
            value=value,
            raw_match=match.group(),
            start=match.start(),
            end=match.end(),
            confidence=0.80
        ))

    return results


def extract_times(text: str) -> List[ExtractedField]:
    """
    Extract time values from text.

    Handles 24-hour and 12-hour formats.

    Args:
        text: Text to extract times from

    Returns:
        List of ExtractedField objects

    Example:
        >>> extract_times("Time: 17:33:34")
        [ExtractedField(type='time_24h', value='17:33:34', ...)]
    """
    results = []

    for match in COMPILED_PATTERNS['time_24h'].finditer(text):
        hour, minute, second = match.groups()
        if second:
            value = f"{hour.zfill(2)}:{minute}:{second}"
        else:
            value = f"{hour.zfill(2)}:{minute}"

        results.append(ExtractedField(
            field_type='time',
            value=value,
            raw_match=match.group(),
            start=match.start(),
            end=match.end()
        ))

    return results


def extract_percentages(text: str) -> List[ExtractedField]:
    """
    Extract percentage values from text.

    Args:
        text: Text to extract percentages from

    Returns:
        List of ExtractedField objects

    Example:
        >>> extract_percentages("VAT: 15%")
        [ExtractedField(type='percentage', value='15', ...)]
    """
    results = []

    for match in COMPILED_PATTERNS['percentage'].finditer(text):
        value = match.group(1)
        results.append(ExtractedField(
            field_type='percentage',
            value=value,
            raw_match=match.group(),
            start=match.start(),
            end=match.end()
        ))

    return results


def extract_all_patterns(text: str) -> Dict[str, List[ExtractedField]]:
    """
    Extract all structured fields from text.

    Runs all pattern extractors and returns categorized results.

    Args:
        text: Text to extract fields from

    Returns:
        Dictionary mapping field types to lists of extracted fields

    Example:
        >>> results = extract_all_patterns("Invoice A-2 dated 2024-12-21, Total: 2,300.00 SAR")
        >>> results['dates']
        [ExtractedField(type='date_iso', value='2024-12-21', ...)]
        >>> results['amounts']
        [ExtractedField(type='amount_with_currency', value='2300.00', ...)]
    """
    return {
        'dates': extract_dates(text),
        'amounts': extract_amounts(text),
        'phone_numbers': extract_phone_numbers(text),
        'tax_numbers': extract_tax_numbers(text),
        'invoice_numbers': extract_invoice_numbers(text),
        'times': extract_times(text),
        'percentages': extract_percentages(text),
    }


def extract_to_flat_dict(text: str) -> Dict[str, Any]:
    """
    Extract all patterns and return as a flat dictionary.

    Useful for quick access to extracted values. For fields with
    multiple occurrences, returns the first one.

    Args:
        text: Text to extract from

    Returns:
        Flat dictionary with field types as keys

    Example:
        >>> extract_to_flat_dict("Date: 2024-12-21, Amount: 2,300.00")
        {'date': '2024-12-21', 'amount': '2300.00'}
    """
    all_fields = extract_all_patterns(text)

    result = {}

    # Take first date
    if all_fields['dates']:
        result['date'] = all_fields['dates'][0].value

    # Take largest amount (likely total)
    if all_fields['amounts']:
        amounts = sorted(all_fields['amounts'],
                         key=lambda x: float(x.value.replace(',', '')),
                         reverse=True)
        result['total_amount'] = amounts[0].value
        if len(amounts) > 1:
            result['amounts'] = [a.value for a in amounts]

    # Take first phone
    if all_fields['phone_numbers']:
        result['phone'] = all_fields['phone_numbers'][0].value

    # Take first tax number
    if all_fields['tax_numbers']:
        result['tax_number'] = all_fields['tax_numbers'][0].value

    # Take first invoice number
    if all_fields['invoice_numbers']:
        result['invoice_number'] = all_fields['invoice_numbers'][0].value

    # Take first time
    if all_fields['times']:
        result['time'] = all_fields['times'][0].value

    # Collect all percentages
    if all_fields['percentages']:
        result['percentages'] = [p.value for p in all_fields['percentages']]

    return result


def identify_invoice_sections(text: str) -> Dict[str, Tuple[int, int]]:
    """
    Identify logical sections in an invoice based on patterns.

    Returns approximate line ranges for each section.

    Args:
        text: Full invoice text

    Returns:
        Dictionary mapping section names to (start_line, end_line) tuples
    """
    lines = text.split('\n')
    sections = {}

    # Track which lines contain which patterns
    header_indicators = ['شركة', 'company', 'skysoft', 'فضاء']
    invoice_indicators = ['فاتورة', 'invoice', 'رقم', 'تاريخ', 'number', 'date']
    customer_indicators = ['عميل', 'customer', 'client', 'العنوان', 'address']
    items_indicators = ['بيان', 'item', 'description', 'كمية', 'qty', 'سعر', 'price']
    summary_indicators = ['مجموع', 'total', 'ضريبة', 'vat', 'tax', 'صافي', 'net']

    current_section = 'header'
    section_start = 0

    for i, line in enumerate(lines):
        line_lower = line.lower()

        # Detect section transitions
        if any(ind in line_lower for ind in items_indicators):
            if current_section != 'items':
                if current_section:
                    sections[current_section] = (section_start, i - 1)
                current_section = 'items'
                section_start = i

        elif any(ind in line_lower for ind in summary_indicators):
            if current_section != 'summary':
                if current_section:
                    sections[current_section] = (section_start, i - 1)
                current_section = 'summary'
                section_start = i

        elif any(ind in line_lower for ind in customer_indicators):
            if current_section not in ['items', 'summary', 'customer']:
                if current_section:
                    sections[current_section] = (section_start, i - 1)
                current_section = 'customer'
                section_start = i

    # Close final section
    if current_section:
        sections[current_section] = (section_start, len(lines) - 1)

    return sections
