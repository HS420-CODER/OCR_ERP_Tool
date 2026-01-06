# OCR Enhancement Solution: Claude Code CLI Quality Output

**Version:** 1.0
**Date:** 2026-01-06
**Goal:** Achieve 90%+ similarity with Claude Code CLI vision output

---

## Executive Summary

This document outlines a comprehensive solution to enhance the OCR tool output quality to match Claude Code CLI's multimodal vision capabilities. The solution addresses critical issues including digit loss, word merging, and garbled text through a multi-layered enhancement pipeline.

---

## Problem Analysis

### Current State vs Target

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| Number Accuracy | 70% | 99% | -29% |
| Arabic Word Accuracy | 60% | 95% | -35% |
| Structure Recognition | 20% | 90% | -70% |
| Barcode Detection | 50% | 95% | -45% |
| Overall Similarity | 55% | 90% | -35% |

### Root Causes Identified

1. **Detection Resolution** - 1280px insufficient for small numbers
2. **RTL Processing** - Arabic words not properly separated
3. **No Post-processing** - Raw OCR output without validation
4. **No Structure Analysis** - Missing table/document understanding
5. **Confidence Issues** - Low-confidence text accepted

---

## Solution Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Enhanced OCR Pipeline v2.0                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  INPUT: Image/PDF                                                           │
│     │                                                                       │
│     ▼                                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  STAGE 1: Pre-processing                                             │   │
│  │  ├── Image quality enhancement (contrast, sharpening)                │   │
│  │  ├── Document type detection (invoice, receipt, general)             │   │
│  │  └── Region identification (header, table, footer)                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│     │                                                                       │
│     ▼                                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  STAGE 2: Multi-Pass OCR                                             │   │
│  │  ├── Pass 1: Full document @ 1280px (structure detection)            │   │
│  │  ├── Pass 2: Full document @ 1920px (detail capture)                 │   │
│  │  ├── Pass 3: Number regions @ 2560px (digit precision)               │   │
│  │  └── Result fusion with confidence weighting                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│     │                                                                       │
│     ▼                                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  STAGE 3: Arabic Text Enhancement                                    │   │
│  │  ├── Word separation (merged word dictionary)                        │   │
│  │  ├── Spelling correction (OCR error dictionary)                      │   │
│  │  ├── RTL ordering validation                                         │   │
│  │  └── Diacritics handling                                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│     │                                                                       │
│     ▼                                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  STAGE 4: Number Validation                                          │   │
│  │  ├── Leading digit restoration                                       │   │
│  │  ├── Barcode pattern validation (EAN-13 checksum)                    │   │
│  │  ├── Currency consistency check                                      │   │
│  │  └── Mathematical relationship validation                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│     │                                                                       │
│     ▼                                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  STAGE 5: Structure Analysis                                         │   │
│  │  ├── Table detection and extraction                                  │   │
│  │  ├── Header/footer recognition                                       │   │
│  │  ├── Field mapping (invoice fields → structured data)                │   │
│  │  └── Section classification                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│     │                                                                       │
│     ▼                                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  STAGE 6: Output Generation                                          │   │
│  │  ├── Claude Code-style markdown                                      │   │
│  │  ├── Bilingual tables                                                │   │
│  │  ├── Confidence indicators                                           │   │
│  │  └── Validation report                                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│     │                                                                       │
│     ▼                                                                       │
│  OUTPUT: Structured ReadResult                                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### Stage 1: Fix PaddleOCR Engine (Critical)

**File:** `src/engines/paddle_engine.py`

#### Problem
Current code passes parameters to `predict()` that cause RuntimeError:
```python
# BUGGY CODE (line 263-267)
result = ocr.predict(
    input=processed_image,
    text_det_limit_side_len=ocr_params.get("text_det_limit_side_len", 960),
    text_rec_score_thresh=ocr_params.get("text_rec_score_thresh", 0.5),
)
```

#### Solution
Remove problematic parameters from predict() call:
```python
# FIXED CODE
# Only pass supported parameters
result = ocr.predict(input=processed_image)
```

Configure parameters at initialization time instead:
```python
# Configure at init
self._ocr_engines[lang] = PaddleOCR(
    lang=lang,
    ocr_version="PP-OCRv5",
    use_doc_orientation_classify=True,
    use_doc_unwarping=True,
    use_textline_orientation=True,
    device="cpu",
)
```

---

### Stage 2: Create Arabic Text Enhancer

**File:** `src/utils/arabic_enhancer.py`

```python
"""
Arabic Text Enhancement Module

Features:
- Merged word separation
- OCR spelling correction
- Invoice-specific patterns
"""

import re
from typing import Dict, List, Tuple

class ArabicTextEnhancer:
    """
    Post-processing enhancement for Arabic OCR results.
    """

    # Common merged words to separate
    MERGED_WORDS: Dict[str, str] = {
        # Invoice fields
        "الرقمالمرجعي": "الرقم المرجعي",
        "الرقمالضريبي": "الرقم الضريبي",
        "إجماليالمبلغ": "إجمالي المبلغ",
        "تكلفةالوحدة": "تكلفة الوحدة",

        # Status fields
        "الجالةتم": "الحالة: تم",
        "الحالةتم": "الحالة: تم",
        "حالةالدفع": "حالة الدفع",

        # Contact fields
        "البريدالإلكتروني": "البريد الإلكتروني",
        "الهاتفالمحمول": "الهاتف المحمول",
    }

    # OCR spelling corrections
    OCR_CORRECTIONS: Dict[str, str] = {
        "الضرية": "الضريبة",
        "الضربة": "الضريبة",
        "الكوية": "الكمية",
        "الجالة": "الحالة",
        "المبلع": "المبلغ",
        "الهانف": "الهاتف",
    }

    # Pattern-based corrections (regex)
    PATTERN_CORRECTIONS: List[Tuple[str, str]] = [
        # Fix merged email addresses
        (r'(\S+@\S+\.\w+)(البريد)', r'\1 البريد'),
        # Fix SAR misread as (A)
        (r'\(A\)', r'(SAR)'),
        (r'\(a\)', r'(SAR)'),
    ]

    @classmethod
    def enhance(cls, text: str) -> str:
        """
        Apply all enhancements to text.

        Args:
            text: Raw OCR text

        Returns:
            Enhanced text
        """
        result = text

        # 1. Apply merged word separation
        for merged, separated in cls.MERGED_WORDS.items():
            result = result.replace(merged, separated)

        # 2. Apply spelling corrections
        for wrong, correct in cls.OCR_CORRECTIONS.items():
            result = result.replace(wrong, correct)

        # 3. Apply pattern-based corrections
        for pattern, replacement in cls.PATTERN_CORRECTIONS:
            result = re.sub(pattern, replacement, result)

        return result

    @classmethod
    def enhance_text_blocks(cls, blocks: List[dict]) -> List[dict]:
        """
        Enhance a list of text blocks.

        Args:
            blocks: List of text block dictionaries

        Returns:
            Enhanced blocks
        """
        enhanced = []
        for block in blocks:
            enhanced_block = block.copy()
            enhanced_block['text'] = cls.enhance(block.get('text', ''))
            enhanced.append(enhanced_block)
        return enhanced
```

---

### Stage 3: Create Number Validator

**File:** `src/validators/number_validator.py`

```python
"""
Number Validation and Correction Module

Features:
- Leading digit restoration
- Barcode validation (EAN-13)
- Invoice total validation
- Currency amount consistency
"""

import re
from typing import Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class NumberContext:
    """Context for number validation."""
    field_type: str  # 'currency', 'barcode', 'quantity', 'phone'
    expected_digits: int
    related_values: List[float]


class NumberValidator:
    """
    Validates and corrects numeric OCR results.
    """

    # EAN-13 barcode pattern
    EAN13_PATTERN = re.compile(r'^\d{13}$')

    # Currency amount pattern
    CURRENCY_PATTERN = re.compile(r'^-?\d+\.?\d{0,2}$')

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
        if not value:
            return value

        # Fix leading decimal point
        if value.startswith('.'):
            value = '0' + value

        # If context provided, use related values to infer correct digits
        if context and context.related_values:
            try:
                current = float(value)
                for related in context.related_values:
                    # Check if adding leading digit(s) matches related value
                    for prefix in ['1', '11', '111', '0']:
                        candidate = prefix + value
                        try:
                            if abs(float(candidate) - related) < 0.01:
                                return candidate
                        except ValueError:
                            continue
            except ValueError:
                pass

        return value

    @classmethod
    def validate_ean13(cls, barcode: str) -> Tuple[bool, str]:
        """
        Validate EAN-13 barcode with checksum.

        Args:
            barcode: 13-digit barcode string

        Returns:
            Tuple of (is_valid, corrected_barcode)
        """
        # Clean input
        cleaned = re.sub(r'\D', '', barcode)

        if len(cleaned) != 13:
            return False, barcode

        # Calculate checksum
        total = sum(
            int(d) * (1 if i % 2 == 0 else 3)
            for i, d in enumerate(cleaned[:12])
        )
        check_digit = (10 - (total % 10)) % 10

        if int(cleaned[12]) == check_digit:
            return True, cleaned
        else:
            # Try to correct the checksum
            corrected = cleaned[:12] + str(check_digit)
            return False, corrected

    @classmethod
    def validate_invoice_totals(
        cls,
        subtotal: float,
        tax: float,
        total: float,
        paid: float,
        balance: float
    ) -> dict:
        """
        Validate invoice mathematical relationships.

        Expected:
        - total = subtotal (or subtotal + tax in some formats)
        - balance = total - paid

        Returns:
            Dictionary with validation results and corrections
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
                f"Balance mismatch: {balance} != {total} - {paid}"
            )
            results['corrections']['balance'] = expected_balance

        # Check if subtotal + tax = total (some invoice formats)
        if abs((subtotal + tax) - total) > 0.01:
            # Check if subtotal alone equals total (tax included)
            if abs(subtotal - total) > 0.01:
                results['issues'].append(
                    f"Total calculation unclear: {subtotal} + {tax} != {total}"
                )

        return results

    @classmethod
    def fix_phone_number(cls, phone: str) -> str:
        """
        Attempt to fix truncated phone numbers.

        Common Saudi formats:
        - 9665XXXXXXXX (international)
        - 05XXXXXXXX (mobile)
        - 01XXXXXXX (landline)

        Args:
            phone: Potentially truncated phone string

        Returns:
            Best-effort corrected phone
        """
        # Clean input
        cleaned = re.sub(r'\D', '', phone)

        # If only a few digits, likely truncated
        if len(cleaned) <= 3:
            return phone  # Can't reliably restore

        # Check for common Saudi prefixes
        if len(cleaned) >= 9:
            if cleaned.startswith('9665'):
                return cleaned  # International format
            if cleaned.startswith('05') or cleaned.startswith('01'):
                return cleaned  # Local format

        return phone
```

---

### Stage 4: Integrate Enhancements

**File:** `src/engines/paddle_engine.py` (modifications)

Add post-processing integration:

```python
def _parse_ocr_result(self, result: Any, lang: str = "en") -> Dict[str, Any]:
    """Parse and enhance OCR result."""

    # ... existing parsing code ...

    # Apply Arabic enhancements
    if lang == "ar":
        from ..utils.arabic_enhancer import ArabicTextEnhancer
        from ..validators.number_validator import NumberValidator

        # Enhance text blocks
        raw_blocks = ArabicTextEnhancer.enhance_text_blocks(raw_blocks)

        # Validate and fix numbers
        for block in raw_blocks:
            text = block.get('text', '')
            # Check for currency patterns
            if re.match(r'^[\d.]+$', text):
                block['text'] = NumberValidator.restore_leading_digits(text)

    return {
        'text_blocks': text_blocks,
        'full_text': full_text
    }
```

---

### Stage 5: Create Enhanced Output Formatter

**File:** `src/formatters/claude_formatter.py`

```python
"""
Claude Code-style Output Formatter

Generates structured markdown output matching Claude Code CLI quality.
"""

from typing import List, Dict, Any, Optional
from ..models import ReadResult, PageResult


class ClaudeStyleFormatter:
    """
    Formats OCR results to match Claude Code CLI output quality.
    """

    @classmethod
    def format_invoice(cls, result: ReadResult) -> str:
        """
        Format invoice OCR result as Claude Code-style markdown.

        Args:
            result: OCR ReadResult

        Returns:
            Formatted markdown string
        """
        sections = []

        # Header
        sections.append("# Invoice OCR Analysis\n")
        sections.append(f"**File:** `{result.file_path}`\n")
        sections.append(f"**Engine:** {result.engine_used}\n")
        sections.append(f"**Language:** {result.language}\n")
        sections.append(f"**Processing Time:** {result.processing_time_ms:.2f}ms\n")

        # Document Structure
        sections.append("\n## Document Structure\n")

        # Extracted data in tables
        if result.pages:
            for page in result.pages:
                sections.append(cls._format_text_blocks(page.text_blocks))

        # Confidence summary
        sections.append("\n## Confidence Summary\n")
        sections.append(cls._format_confidence_table(result))

        return '\n'.join(sections)

    @classmethod
    def _format_text_blocks(cls, blocks: List) -> str:
        """Format text blocks as markdown table."""
        if not blocks:
            return "*No text blocks detected*\n"

        lines = ["| # | Text | Confidence |",
                 "|---|------|------------|"]

        for i, block in enumerate(blocks, 1):
            text = block.text.replace('|', '\\|')  # Escape pipes
            conf = f"{block.confidence * 100:.1f}%"
            lines.append(f"| {i} | {text} | {conf} |")

        return '\n'.join(lines)

    @classmethod
    def _format_confidence_table(cls, result: ReadResult) -> str:
        """Generate confidence statistics."""
        if not result.pages or not result.pages[0].text_blocks:
            return "*No confidence data*\n"

        blocks = result.pages[0].text_blocks
        confidences = [b.confidence for b in blocks]

        avg = sum(confidences) / len(confidences)
        high = sum(1 for c in confidences if c >= 0.9)
        med = sum(1 for c in confidences if 0.7 <= c < 0.9)
        low = sum(1 for c in confidences if c < 0.7)

        return f"""| Metric | Value |
|--------|-------|
| Total Blocks | {len(blocks)} |
| Average Confidence | {avg*100:.1f}% |
| High (>90%) | {high} |
| Medium (70-90%) | {med} |
| Low (<70%) | {low} |
"""
```

---

## Testing Strategy

### Test Cases

1. **Digit Restoration Test**
   - Input: "11.78" with context [111.78]
   - Expected: "111.78"

2. **Word Separation Test**
   - Input: "الرقمالمرجعي"
   - Expected: "الرقم المرجعي"

3. **Barcode Validation Test**
   - Input: "6281102740016"
   - Expected: Valid EAN-13

4. **Full Invoice Test**
   - Input: `examples/Screenshot 2026-01-06 104028.png`
   - Expected: 90%+ match with Claude Code output

### Success Criteria

| Metric | Current | Target | Test |
|--------|---------|--------|------|
| Number accuracy | 70% | 99% | All totals correct |
| Word separation | 60% | 95% | No merged words |
| Barcode detection | 50% | 95% | Both barcodes found |
| Structure | 20% | 90% | Table reconstructed |

---

## Implementation Order

1. **Phase 1: Bug Fixes** (Priority: Critical)
   - Fix RuntimeError in paddle_engine.py
   - Remove invalid predict() parameters

2. **Phase 2: Enhancement Classes** (Priority: High)
   - Create ArabicTextEnhancer
   - Create NumberValidator

3. **Phase 3: Integration** (Priority: High)
   - Integrate enhancers into paddle_engine.py
   - Update result parsing

4. **Phase 4: Output Formatting** (Priority: Medium)
   - Create ClaudeStyleFormatter
   - Generate markdown output

5. **Phase 5: Testing** (Priority: High)
   - Test with benchmark image
   - Validate improvements

---

## Files to Create/Modify

| File | Action | Priority |
|------|--------|----------|
| `src/engines/paddle_engine.py` | Modify | P0 |
| `src/utils/arabic_enhancer.py` | Create | P1 |
| `src/validators/number_validator.py` | Create | P1 |
| `src/validators/__init__.py` | Create | P1 |
| `src/formatters/claude_formatter.py` | Create | P2 |
| `tests/test_arabic_enhancer.py` | Create | P2 |
| `tests/test_number_validator.py` | Create | P2 |
