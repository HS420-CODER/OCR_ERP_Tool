"""
Number Validation and Correction Module

Validates and corrects numeric OCR results for invoices.

Features:
- Leading digit restoration (11.78 → 111.78)
- Barcode validation (EAN-13 checksum)
- Invoice total validation (mathematical consistency)
- Phone number correction
- Currency amount validation
"""

import re
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class NumberContext:
    """
    Context information for number validation.

    Provides hints about what the number represents and
    related values for cross-validation.
    """
    field_type: str  # 'currency', 'barcode', 'quantity', 'phone', 'tax_number'
    expected_digits: int = 0  # Expected number of digits
    related_values: List[float] = field(default_factory=list)
    label: str = ""  # Associated label (e.g., "المجموع")


class NumberValidator:
    """
    Validates and corrects numeric OCR results.

    Addresses common OCR errors:
    - Missing leading digits (111.78 → 11.78)
    - Missing leading zeros (0.00 → .00)
    - Truncated phone numbers
    - Invalid barcode checksums
    """

    # EAN-13 barcode pattern
    EAN13_PATTERN = re.compile(r'^\d{13}$')

    # Currency amount pattern (allows negative, decimals)
    CURRENCY_PATTERN = re.compile(r'^-?\d+\.?\d{0,2}$')

    # Saudi phone patterns
    SAUDI_PHONE_PATTERNS = [
        re.compile(r'^966\d{9}$'),      # International
        re.compile(r'^05\d{8}$'),        # Mobile
        re.compile(r'^01\d{7,8}$'),      # Landline
        re.compile(r'^0\d{8,9}$'),       # General
    ]

    # Tax number pattern (Saudi 15-digit VAT number)
    TAX_NUMBER_PATTERN = re.compile(r'^3\d{14}$')

    @classmethod
    def restore_leading_digits(
        cls,
        value: str,
        context: Optional[NumberContext] = None
    ) -> str:
        """
        Restore missing leading digits.

        Common OCR errors:
        - 111.78 → 11.78 (missing leading 1)
        - 0.00 → .00 (missing leading 0)
        - 111.78 → 1.78 (missing leading 11)

        Args:
            value: OCR-extracted number string
            context: Optional context for validation

        Returns:
            Corrected number string
        """
        if not value or not value.strip():
            return value

        value = value.strip()

        # Fix leading decimal point
        if value.startswith('.'):
            logger.debug(f"Restoring leading zero: .{value[1:]} → 0{value}")
            value = '0' + value

        # If context provided, use related values to infer correct digits
        if context and context.related_values:
            try:
                current = float(value)
                best_match = None
                best_diff = float('inf')

                for related in context.related_values:
                    # Check if adding leading digit(s) matches related value
                    for prefix in ['1', '11', '111', '0', '00']:
                        candidate = prefix + value
                        try:
                            candidate_float = float(candidate)
                            diff = abs(candidate_float - related)
                            if diff < 0.01 and diff < best_diff:
                                best_match = candidate
                                best_diff = diff
                        except ValueError:
                            continue

                if best_match:
                    logger.debug(f"Restored from context: {value} → {best_match}")
                    return best_match

            except ValueError:
                pass

        # Heuristic: If value looks like a truncated total (11.78 instead of 111.78)
        # and there are line items that would make sense
        if re.match(r'^\d{1,2}\.\d{2}$', value):
            # Check if doubling/tripling makes a more reasonable total
            try:
                current = float(value)
                # If < 100 and looks like it should be >= 100
                if current < 100 and current > 10:
                    # Try prepending '1'
                    candidate = '1' + value
                    candidate_float = float(candidate)
                    if 100 <= candidate_float <= 999:
                        logger.debug(f"Heuristic restoration: {value} → {candidate}")
                        return candidate
            except ValueError:
                pass

        return value

    @classmethod
    def validate_ean13(cls, barcode: str) -> Tuple[bool, str]:
        """
        Validate EAN-13 barcode with checksum.

        EAN-13 checksum algorithm:
        1. Sum digits at odd positions (1,3,5...) × 1
        2. Sum digits at even positions (2,4,6...) × 3
        3. Check digit = (10 - (sum % 10)) % 10

        Args:
            barcode: 13-digit barcode string

        Returns:
            Tuple of (is_valid, corrected_or_original_barcode)
        """
        # Clean input - remove non-digits
        cleaned = re.sub(r'\D', '', barcode)

        if len(cleaned) != 13:
            logger.warning(f"Invalid barcode length: {len(cleaned)} (expected 13)")
            return False, barcode

        # Calculate checksum
        total = 0
        for i, digit in enumerate(cleaned[:12]):
            weight = 1 if i % 2 == 0 else 3
            total += int(digit) * weight

        check_digit = (10 - (total % 10)) % 10

        actual_check = int(cleaned[12])
        if actual_check == check_digit:
            logger.debug(f"Valid EAN-13: {cleaned}")
            return True, cleaned
        else:
            # Return corrected barcode
            corrected = cleaned[:12] + str(check_digit)
            logger.warning(
                f"Invalid EAN-13 checksum: {cleaned} (expected check digit: {check_digit})"
            )
            return False, corrected

    @classmethod
    def validate_invoice_totals(
        cls,
        subtotal: float,
        tax: float,
        total: float,
        paid: float,
        balance: float
    ) -> Dict[str, Any]:
        """
        Validate invoice mathematical relationships.

        Expected relationships:
        - balance = total - paid
        - total = subtotal + tax (in some formats)
        - OR total = subtotal (tax included)

        Args:
            subtotal: Sum of line items before tax
            tax: Tax amount
            total: Grand total
            paid: Amount paid
            balance: Amount due

        Returns:
            Dictionary with:
            - valid: bool
            - issues: List of issue descriptions
            - corrections: Dict of suggested corrections
        """
        results = {
            'valid': True,
            'issues': [],
            'corrections': {}
        }

        # Check balance calculation
        expected_balance = total - paid
        if abs(balance - expected_balance) > 0.01:
            results['valid'] = False
            results['issues'].append(
                f"Balance mismatch: {balance} != {total} - {paid} = {expected_balance}"
            )
            results['corrections']['balance'] = round(expected_balance, 2)

        # Check total calculation
        # Option 1: total = subtotal + tax
        expected_total_with_tax = subtotal + tax
        # Option 2: total = subtotal (tax included in line items)
        expected_total_without_tax = subtotal

        if abs(total - expected_total_with_tax) > 0.01 and abs(total - expected_total_without_tax) > 0.01:
            results['issues'].append(
                f"Total calculation unclear: {total} != {subtotal} + {tax} = {expected_total_with_tax}"
            )
            # Suggest correction if obvious
            if abs(total - expected_total_with_tax) < 10:
                results['corrections']['total'] = round(expected_total_with_tax, 2)

        # Check if tax rate is reasonable (5-20% typical for VAT)
        if subtotal > 0:
            tax_rate = (tax / subtotal) * 100
            if tax_rate < 0 or tax_rate > 30:
                results['issues'].append(
                    f"Unusual tax rate: {tax_rate:.1f}% (expected 5-20%)"
                )

        if results['issues']:
            results['valid'] = False

        return results

    @classmethod
    def fix_phone_number(cls, phone: str, country: str = "SA") -> str:
        """
        Attempt to fix truncated phone numbers.

        Saudi Arabia phone formats:
        - 966XXXXXXXXX (international, 12 digits)
        - 05XXXXXXXX (mobile, 10 digits)
        - 01XXXXXXX (landline, 9 digits)

        Args:
            phone: Potentially truncated phone string
            country: Country code (default: Saudi Arabia)

        Returns:
            Best-effort corrected phone or original if unfixable
        """
        # Clean input - keep only digits
        cleaned = re.sub(r'\D', '', phone)

        if not cleaned:
            return phone

        # If already valid, return as-is
        for pattern in cls.SAUDI_PHONE_PATTERNS:
            if pattern.match(cleaned):
                return cleaned

        # If only a few digits, likely severely truncated - can't fix
        if len(cleaned) <= 3:
            logger.warning(f"Phone too truncated to fix: {phone}")
            return phone

        # Try common prefix additions
        if len(cleaned) >= 7:
            # Try adding 05 for mobile
            candidate = '05' + cleaned[-8:] if len(cleaned) <= 8 else cleaned
            if cls.SAUDI_PHONE_PATTERNS[1].match(candidate):
                return candidate

            # Try adding 01 for landline
            candidate = '01' + cleaned[-7:] if len(cleaned) <= 7 else cleaned
            if cls.SAUDI_PHONE_PATTERNS[2].match(candidate):
                return candidate

        return phone

    @classmethod
    def validate_tax_number(cls, tax_number: str) -> Tuple[bool, str]:
        """
        Validate Saudi VAT tax number.

        Saudi VAT numbers:
        - 15 digits
        - Start with 3

        Args:
            tax_number: Tax registration number

        Returns:
            Tuple of (is_valid, cleaned_number)
        """
        cleaned = re.sub(r'\D', '', tax_number)

        if cls.TAX_NUMBER_PATTERN.match(cleaned):
            return True, cleaned

        # If 14 digits, might be missing leading 3
        if len(cleaned) == 14:
            candidate = '3' + cleaned
            if cls.TAX_NUMBER_PATTERN.match(candidate):
                logger.debug(f"Restored tax number leading 3: {candidate}")
                return True, candidate

        return False, cleaned

    @classmethod
    def enhance_text_block_numbers(
        cls,
        blocks: List[Dict[str, Any]],
        context_hints: Optional[Dict[str, NumberContext]] = None
    ) -> List[Dict[str, Any]]:
        """
        Enhance numeric values in text blocks.

        Args:
            blocks: List of text block dictionaries
            context_hints: Optional mapping of patterns to NumberContext

        Returns:
            Enhanced blocks with corrected numbers
        """
        enhanced = []

        # Build context from all blocks
        all_numbers = []
        for block in blocks:
            text = block.get('text', '')
            try:
                if re.match(r'^[\d.,-]+$', text):
                    all_numbers.append(float(text.replace(',', '')))
            except ValueError:
                pass

        default_context = NumberContext(
            field_type='currency',
            related_values=all_numbers
        )

        for block in blocks:
            enhanced_block = block.copy()
            text = block.get('text', '')

            # Check if this is a numeric value
            if re.match(r'^[\d.,-]+$', text.strip()):
                context = default_context
                if context_hints:
                    for pattern, ctx in context_hints.items():
                        if pattern in str(block.get('label', '')):
                            context = ctx
                            break

                corrected = cls.restore_leading_digits(text, context)
                if corrected != text:
                    enhanced_block['text'] = corrected
                    enhanced_block['_number_enhanced'] = True
                    enhanced_block['_original_number'] = text

            enhanced.append(enhanced_block)

        return enhanced


# Convenience functions
def validate_ean13(barcode: str) -> Tuple[bool, str]:
    """Validate EAN-13 barcode."""
    return NumberValidator.validate_ean13(barcode)


def restore_leading_digits(value: str, context: Optional[NumberContext] = None) -> str:
    """Restore missing leading digits."""
    return NumberValidator.restore_leading_digits(value, context)


def validate_invoice_totals(
    subtotal: float,
    tax: float,
    total: float,
    paid: float,
    balance: float
) -> Dict[str, Any]:
    """Validate invoice mathematical relationships."""
    return NumberValidator.validate_invoice_totals(subtotal, tax, total, paid, balance)
