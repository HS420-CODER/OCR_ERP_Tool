"""
Arabic Text Enhancement Module

Post-processing enhancement for Arabic OCR results.

Features:
- Merged word separation
- OCR spelling correction
- Invoice-specific patterns
- RTL text handling

This module is designed to fix common PaddleOCR errors
for Arabic invoice documents.
"""

import re
from typing import Dict, List, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class ArabicTextEnhancer:
    """
    Post-processing enhancement for Arabic OCR results.

    Addresses common issues:
    - Words merged without spaces (الرقمالمرجعي → الرقم المرجعي)
    - OCR spelling errors (الضرية → الضريبة)
    - Pattern-based corrections (email merged with labels)
    """

    # Common merged words to separate
    # Maps merged form to separated form
    MERGED_WORDS: Dict[str, str] = {
        # Invoice header fields
        "الرقمالمرجعي": "الرقم المرجعي",
        "الرقمالضريبي": "الرقم الضريبي",
        "الرقمالموحد": "الرقم الموحد",
        "رقمالفاتورة": "رقم الفاتورة",

        # Invoice totals
        "إجماليالمبلغ": "إجمالي المبلغ",
        "اجماليالمبلغ": "إجمالي المبلغ",
        "مجموعالفاتورة": "مجموع الفاتورة",
        "صافيالمبلغ": "صافي المبلغ",

        # Table headers
        "تكلفةالوحدة": "تكلفة الوحدة",
        "سعرالوحدة": "سعر الوحدة",
        "وصفالمنتج": "وصف المنتج",

        # Status fields
        "الجالةتم": "الحالة: تم",
        "الحالةتم": "الحالة: تم",
        "حالةالدفع": "حالة الدفع",
        "حالةالطلب": "حالة الطلب",
        "تمالاستلام": "تم الاستلام",

        # Contact fields
        "البريدالإلكتروني": "البريد الإلكتروني",
        "البريدالالكتروني": "البريد الإلكتروني",
        "الهاتفالمحمول": "الهاتف المحمول",
        "رقمالهاتف": "رقم الهاتف",
        "رقمالجوال": "رقم الجوال",

        # Company info
        "اسمالشركة": "اسم الشركة",
        "عنوانالشركة": "عنوان الشركة",
        "سجلتجاري": "سجل تجاري",

        # Date/Time
        "تاريخالفاتورة": "تاريخ الفاتورة",
        "تاريخالاستحقاق": "تاريخ الاستحقاق",
    }

    # OCR spelling corrections
    # Maps common OCR errors to correct spelling
    OCR_CORRECTIONS: Dict[str, str] = {
        # Missing letters
        "الضرية": "الضريبة",
        "الضربة": "الضريبة",
        "الكوية": "الكمية",
        "الكميه": "الكمية",

        # Letter substitutions
        "الجالة": "الحالة",
        "الحاله": "الحالة",
        "المبلع": "المبلغ",
        "المبلة": "المبلغ",
        "الهانف": "الهاتف",
        "الهاتق": "الهاتف",

        # Common word errors
        "الاجمالي": "الإجمالي",
        "اجمالي": "إجمالي",
        "الالكتروني": "الإلكتروني",
        "البريب": "البريد",
        "المرجعى": "المرجعي",
        "الضريبى": "الضريبي",

        # Status words
        "الاستلام": "الاستلام",
        "مدفوغ": "مدفوع",
        "اجل": "آجل",
    }

    # Pattern-based corrections (compiled regex)
    PATTERN_CORRECTIONS: List[Tuple[re.Pattern, str]] = [
        # Fix merged email addresses
        (re.compile(r'(\S+@\S+\.\w+)(البريد)'), r'\1 البريد'),
        (re.compile(r'(\S+@\S+\.\w+)(الايميل)'), r'\1 الإيميل'),

        # Fix SAR/currency misread
        (re.compile(r'\(A\)'), r'(SAR)'),
        (re.compile(r'\(a\)'), r'(SAR)'),
        (re.compile(r'\(AR\)'), r'(SAR)'),

        # Fix colon spacing
        (re.compile(r'(\w):(\w)'), r'\1: \2'),

        # Fix date format (add missing colons)
        (re.compile(r'التاريخ(\d{2}/\d{2}/\d{4})'), r'التاريخ: \1'),
    ]

    @classmethod
    def enhance(cls, text: str) -> str:
        """
        Apply all enhancements to text.

        Processing order:
        1. Merged word separation
        2. Spelling corrections
        3. Pattern-based corrections

        Args:
            text: Raw OCR text

        Returns:
            Enhanced text
        """
        if not text:
            return text

        result = text

        # 1. Apply merged word separation
        for merged, separated in cls.MERGED_WORDS.items():
            if merged in result:
                result = result.replace(merged, separated)
                logger.debug(f"Separated: {merged} → {separated}")

        # 2. Apply spelling corrections
        for wrong, correct in cls.OCR_CORRECTIONS.items():
            if wrong in result:
                result = result.replace(wrong, correct)
                logger.debug(f"Corrected: {wrong} → {correct}")

        # 3. Apply pattern-based corrections
        for pattern, replacement in cls.PATTERN_CORRECTIONS:
            if pattern.search(result):
                new_result = pattern.sub(replacement, result)
                if new_result != result:
                    logger.debug(f"Pattern fix applied: {pattern.pattern}")
                    result = new_result

        return result

    @classmethod
    def enhance_text_blocks(cls, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enhance a list of text blocks.

        Args:
            blocks: List of text block dictionaries with 'text' key

        Returns:
            Enhanced blocks with modified 'text' values
        """
        enhanced = []
        for block in blocks:
            enhanced_block = block.copy()
            original_text = block.get('text', '')
            enhanced_text = cls.enhance(original_text)

            if enhanced_text != original_text:
                enhanced_block['text'] = enhanced_text
                enhanced_block['_enhanced'] = True
                enhanced_block['_original'] = original_text

            enhanced.append(enhanced_block)

        return enhanced

    @classmethod
    def detect_merged_words(cls, text: str) -> List[str]:
        """
        Detect potential merged words in text.

        Useful for identifying new merged patterns that
        should be added to MERGED_WORDS dictionary.

        Args:
            text: Text to analyze

        Returns:
            List of potential merged words (long words without spaces)
        """
        # Arabic words typically have 2-10 characters
        # Merged words are often 15+ characters
        potential_merged = []

        # Find Arabic word sequences
        arabic_pattern = re.compile(r'[\u0600-\u06FF]+')
        words = arabic_pattern.findall(text)

        for word in words:
            # Long Arabic words (>12 chars) are likely merged
            if len(word) > 12:
                potential_merged.append(word)

        return potential_merged

    @classmethod
    def split_merged_arabic(cls, text: str) -> str:
        """
        Attempt to split merged Arabic words using heuristics.

        This is a fallback for merged words not in the dictionary.
        Uses common Arabic word patterns to find split points.

        Args:
            text: Text with potential merged words

        Returns:
            Text with attempted splits
        """
        result = text

        # Common Arabic prefixes that indicate word boundaries
        prefixes = ['ال', 'و', 'ب', 'ل', 'ف', 'ك']

        # Common invoice field starts
        field_starts = [
            'رقم', 'تاريخ', 'حالة', 'مجموع', 'صافي',
            'إجمالي', 'ضريبة', 'كمية', 'سعر', 'وصف'
        ]

        # Try to split at field boundaries
        for field in field_starts:
            # Look for field word inside a longer word
            pattern = re.compile(rf'(\w+)({field})')
            if pattern.search(result):
                result = pattern.sub(r'\1 \2', result)

        return result


def enhance_arabic_text(text: str) -> str:
    """
    Convenience function for text enhancement.

    Args:
        text: Raw OCR text

    Returns:
        Enhanced text
    """
    return ArabicTextEnhancer.enhance(text)


def enhance_arabic_blocks(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convenience function for block enhancement.

    Args:
        blocks: List of text blocks

    Returns:
        Enhanced blocks
    """
    return ArabicTextEnhancer.enhance_text_blocks(blocks)
