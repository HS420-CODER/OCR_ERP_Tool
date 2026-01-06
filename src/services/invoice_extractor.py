"""
ERP Arabic OCR Microservice - Invoice Field Extractor
======================================================
Extracts structured fields from Arabic invoice OCR text.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Pattern
from dataclasses import dataclass

from . import InvoiceField, LineItem, InvoiceData, BoundingBox, TextBlock

logger = logging.getLogger(__name__)


# Field patterns for Arabic invoices
FIELD_PATTERNS = {
    # Tax/VAT Number - الرقم الضريبي
    'tax_number': {
        'patterns': [
            r'(?:الرقم\s*الضريبي|رقم\s*ضريبي|الضريبي|VAT\s*(?:No|Number|#)?|Tax\s*(?:ID|Number|No))\s*[:\-]?\s*(\d{15})',
            r'(?:الرقم\s*الضريبي|رقم\s*ضريبي)\s*[:\-]?\s*(\d+)',
            r'(\d{15})\s*(?:الرقم\s*الضريبي)',
        ],
        'name_ar': 'الرقم الضريبي',
        'name_en': 'tax_number',
        'validator': '_validate_saudi_vat'
    },

    # Invoice Number - رقم الفاتورة
    'invoice_number': {
        'patterns': [
            r'(?:رقم\s*الفاتورة|فاتورة\s*رقم|Invoice\s*(?:No|Number|#)?)\s*[:\-]?\s*([A-Za-z0-9\-\/]+)',
            r'(?:الفاتورة|فاتورة)\s*[#:\-]?\s*(\d+)',
        ],
        'name_ar': 'رقم الفاتورة',
        'name_en': 'invoice_number',
        'validator': None
    },

    # Date - التاريخ
    'date': {
        'patterns': [
            r'(?:التاريخ|تاريخ|Date)\s*[:\-]?\s*(\d{1,4}[\-\/\.]\d{1,2}[\-\/\.]\d{2,4})',
            r'(\d{1,2}[\-\/\.]\d{1,2}[\-\/\.]\d{2,4})\s*(?:التاريخ|هـ|م)',
        ],
        'name_ar': 'التاريخ',
        'name_en': 'date',
        'validator': '_validate_date'
    },

    # Total Amount - الاجمالي
    'total': {
        'patterns': [
            r'(?:الاجمالي|المجموع\s*الكلي|الإجمالي|Grand\s*Total|Total)\s*[:\-]?\s*([\d,\.]+)\s*(?:ريال|SAR|SR)?',
            r'(?:الاجمالي|الإجمالي)\s*(?:شامل\s*الضريبة)?\s*[:\-]?\s*([\d,\.]+)',
            r'([\d,\.]+)\s*(?:ريال|SAR)?\s*(?:الاجمالي|المجموع)',
        ],
        'name_ar': 'الاجمالي',
        'name_en': 'total',
        'validator': '_validate_amount'
    },

    # Subtotal - المجموع
    'subtotal': {
        'patterns': [
            r'(?:المجموع|الاجمالي\s*قبل\s*الضريبة|Subtotal)\s*[:\-]?\s*([\d,\.]+)',
            r'(?:المجموع\s*الفرعي)\s*[:\-]?\s*([\d,\.]+)',
        ],
        'name_ar': 'المجموع',
        'name_en': 'subtotal',
        'validator': '_validate_amount'
    },

    # Tax Amount - قيمة الضريبة
    'tax_amount': {
        'patterns': [
            r'(?:قيمة\s*الضريبة|ضريبة\s*القيمة\s*المضافة|VAT|Tax)\s*[:\-]?\s*([\d,\.]+)',
            r'(?:الضريبة|ض\.?ق\.?م)\s*[:\-]?\s*([\d,\.]+)',
            r'(\d+(?:[\.,]\d+)?)\s*%?\s*(?:ضريبة)',
        ],
        'name_ar': 'قيمة الضريبة',
        'name_en': 'tax_amount',
        'validator': '_validate_amount'
    },

    # Vendor Name - اسم المورد
    'vendor_name': {
        'patterns': [
            r'(?:اسم\s*المورد|المورد|البائع|Vendor|Seller|From)\s*[:\-]?\s*([^\n\d]+)',
            r'(?:شركة|مؤسسة)\s+([^\n\d]+?)(?:\s*-|،|,|\n)',
        ],
        'name_ar': 'اسم المورد',
        'name_en': 'vendor_name',
        'validator': None
    },

    # Customer Name - اسم العميل
    'customer_name': {
        'patterns': [
            r'(?:اسم\s*العميل|العميل|المشتري|Customer|Buyer|Bill\s*To)\s*[:\-]?\s*([^\n\d]+)',
        ],
        'name_ar': 'اسم العميل',
        'name_en': 'customer_name',
        'validator': None
    },
}

# Line item patterns
LINE_ITEM_PATTERNS = [
    # Pattern: Description | Quantity | Unit Price | Total
    r'([^\d\n]+?)\s+(\d+(?:[\.,]\d+)?)\s+([\d,\.]+)\s+([\d,\.]+)',
    # Pattern: # | Description | Qty | Price | Total
    r'\d+\s+([^\d\n]+?)\s+(\d+(?:[\.,]\d+)?)\s+([\d,\.]+)\s+([\d,\.]+)',
]


class InvoiceFieldExtractor:
    """
    Extract structured fields from Arabic invoice OCR text.

    Supports:
    - Saudi Arabian invoice formats
    - Bilingual (Arabic/English) invoices
    - Common field extraction (tax number, invoice number, dates, amounts)
    - Line item extraction
    - Field validation
    """

    def __init__(self):
        """Initialize field extractor."""
        # Compile patterns
        self._compiled_patterns = {}
        for field_name, field_config in FIELD_PATTERNS.items():
            self._compiled_patterns[field_name] = [
                re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                for pattern in field_config['patterns']
            ]

        self._line_item_patterns = [
            re.compile(pattern, re.MULTILINE)
            for pattern in LINE_ITEM_PATTERNS
        ]

    def extract_fields(
        self,
        text: str,
        blocks: Optional[List[TextBlock]] = None
    ) -> InvoiceData:
        """
        Extract all fields from invoice text.

        Args:
            text: OCR text from invoice
            blocks: Optional text blocks with positions

        Returns:
            InvoiceData with extracted fields
        """
        invoice_data = InvoiceData()

        # Extract each field type
        invoice_data.tax_number = self._extract_tax_number(text, blocks)
        invoice_data.invoice_number = self._extract_invoice_number(text, blocks)
        invoice_data.date = self._extract_date(text, blocks)
        invoice_data.total = self._extract_total(text, blocks)
        invoice_data.subtotal = self._extract_subtotal(text, blocks)
        invoice_data.tax_amount = self._extract_tax_amount(text, blocks)
        invoice_data.vendor_name = self._extract_vendor_name(text, blocks)
        invoice_data.customer_name = self._extract_customer_name(text, blocks)

        # Extract line items
        invoice_data.line_items = self._extract_line_items(text)

        return invoice_data

    def _extract_field(
        self,
        text: str,
        field_name: str,
        blocks: Optional[List[TextBlock]] = None
    ) -> Optional[InvoiceField]:
        """
        Extract a specific field from text.

        Args:
            text: OCR text
            field_name: Field to extract
            blocks: Optional text blocks

        Returns:
            InvoiceField if found, None otherwise
        """
        if field_name not in self._compiled_patterns:
            return None

        field_config = FIELD_PATTERNS[field_name]
        patterns = self._compiled_patterns[field_name]

        for pattern in patterns:
            match = pattern.search(text)
            if match:
                value = match.group(1).strip()

                # Run validator if configured
                validated = True
                validation_msg = ""
                validator_name = field_config.get('validator')

                if validator_name and hasattr(self, validator_name):
                    validator = getattr(self, validator_name)
                    validated, validation_msg = validator(value)

                # Find bbox if blocks provided
                bbox = self._find_bbox_for_value(value, blocks) if blocks else None

                return InvoiceField(
                    field_name=field_config['name_en'],
                    field_name_ar=field_config['name_ar'],
                    value=value,
                    confidence=0.9 if validated else 0.6,
                    bbox=bbox,
                    validated=validated,
                    validation_message=validation_msg
                )

        return None

    def _extract_tax_number(
        self,
        text: str,
        blocks: Optional[List[TextBlock]] = None
    ) -> Optional[InvoiceField]:
        """Extract tax/VAT number."""
        return self._extract_field(text, 'tax_number', blocks)

    def _extract_invoice_number(
        self,
        text: str,
        blocks: Optional[List[TextBlock]] = None
    ) -> Optional[InvoiceField]:
        """Extract invoice number."""
        return self._extract_field(text, 'invoice_number', blocks)

    def _extract_date(
        self,
        text: str,
        blocks: Optional[List[TextBlock]] = None
    ) -> Optional[InvoiceField]:
        """Extract date."""
        return self._extract_field(text, 'date', blocks)

    def _extract_total(
        self,
        text: str,
        blocks: Optional[List[TextBlock]] = None
    ) -> Optional[InvoiceField]:
        """Extract total amount."""
        return self._extract_field(text, 'total', blocks)

    def _extract_subtotal(
        self,
        text: str,
        blocks: Optional[List[TextBlock]] = None
    ) -> Optional[InvoiceField]:
        """Extract subtotal."""
        return self._extract_field(text, 'subtotal', blocks)

    def _extract_tax_amount(
        self,
        text: str,
        blocks: Optional[List[TextBlock]] = None
    ) -> Optional[InvoiceField]:
        """Extract tax amount."""
        return self._extract_field(text, 'tax_amount', blocks)

    def _extract_vendor_name(
        self,
        text: str,
        blocks: Optional[List[TextBlock]] = None
    ) -> Optional[InvoiceField]:
        """Extract vendor name."""
        return self._extract_field(text, 'vendor_name', blocks)

    def _extract_customer_name(
        self,
        text: str,
        blocks: Optional[List[TextBlock]] = None
    ) -> Optional[InvoiceField]:
        """Extract customer name."""
        return self._extract_field(text, 'customer_name', blocks)

    def _extract_line_items(self, text: str) -> List[LineItem]:
        """
        Extract line items from invoice.

        Args:
            text: OCR text

        Returns:
            List of LineItem objects
        """
        items = []

        for pattern in self._line_item_patterns:
            matches = pattern.findall(text)
            for match in matches:
                try:
                    if len(match) >= 4:
                        description = match[0].strip()
                        quantity = self._parse_number(match[1])
                        unit_price = self._parse_number(match[2])
                        total = self._parse_number(match[3])

                        # Skip if description is too short or looks like a header
                        if len(description) < 2:
                            continue
                        if any(kw in description.lower() for kw in ['الوصف', 'description', 'item', 'البند']):
                            continue

                        items.append(LineItem(
                            description=description,
                            quantity=quantity,
                            unit_price=unit_price,
                            total=total,
                            confidence=0.8
                        ))
                except (ValueError, IndexError):
                    continue

        return items

    def _validate_saudi_vat(self, value: str) -> Tuple[bool, str]:
        """
        Validate Saudi VAT number.

        Saudi VAT numbers:
        - 15 digits
        - Start with 3

        Args:
            value: VAT number to validate

        Returns:
            Tuple of (is_valid, message)
        """
        # Clean value
        cleaned = re.sub(r'\D', '', value)

        if len(cleaned) != 15:
            return False, f"VAT number must be 15 digits (got {len(cleaned)})"

        if not cleaned.startswith('3'):
            return False, "Saudi VAT number must start with 3"

        return True, "Valid Saudi VAT number"

    def _validate_date(self, value: str) -> Tuple[bool, str]:
        """
        Validate date format.

        Args:
            value: Date string

        Returns:
            Tuple of (is_valid, message)
        """
        # Check common date patterns
        date_patterns = [
            r'^\d{4}[\-\/\.]\d{1,2}[\-\/\.]\d{1,2}$',  # YYYY-MM-DD
            r'^\d{1,2}[\-\/\.]\d{1,2}[\-\/\.]\d{4}$',  # DD-MM-YYYY
            r'^\d{1,2}[\-\/\.]\d{1,2}[\-\/\.]\d{2}$',  # DD-MM-YY
        ]

        for pattern in date_patterns:
            if re.match(pattern, value):
                return True, "Valid date format"

        return False, "Invalid date format"

    def _validate_amount(self, value: str) -> Tuple[bool, str]:
        """
        Validate amount/currency value.

        Args:
            value: Amount string

        Returns:
            Tuple of (is_valid, message)
        """
        try:
            amount = self._parse_number(value)
            if amount >= 0:
                return True, f"Valid amount: {amount}"
            return False, "Amount cannot be negative"
        except ValueError:
            return False, "Invalid number format"

    def _parse_number(self, value: str) -> float:
        """
        Parse number from string.

        Handles:
        - Comma as thousands separator
        - Arabic/English numerals

        Args:
            value: Number string

        Returns:
            Parsed float value
        """
        # Remove thousand separators
        cleaned = value.replace(',', '')

        # Convert Arabic numerals to English
        arabic_to_english = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
        cleaned = cleaned.translate(arabic_to_english)

        # Parse
        return float(cleaned)

    def _find_bbox_for_value(
        self,
        value: str,
        blocks: List[TextBlock]
    ) -> Optional[BoundingBox]:
        """
        Find bounding box for a value in text blocks.

        Args:
            value: Value to find
            blocks: Text blocks with positions

        Returns:
            BoundingBox if found
        """
        for block in blocks:
            if value in block.text:
                return block.bbox
        return None


# Export
__all__ = ["InvoiceFieldExtractor", "FIELD_PATTERNS"]
