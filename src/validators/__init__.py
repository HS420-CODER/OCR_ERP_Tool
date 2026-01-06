"""
Validators package for OCR result validation and correction.

Provides validation and correction utilities for:
- Numeric values (currency, quantities)
- Barcodes (EAN-13, UPC)
- Phone numbers
- Invoice mathematical relationships
"""

from .number_validator import (
    NumberValidator,
    NumberContext,
    validate_ean13,
    restore_leading_digits,
    validate_invoice_totals,
)

__all__ = [
    'NumberValidator',
    'NumberContext',
    'validate_ean13',
    'restore_leading_digits',
    'validate_invoice_totals',
]
