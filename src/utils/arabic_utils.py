"""
Arabic text processing utilities for OCR post-processing.

This module provides functions to normalize Arabic text, which is critical
for matching OCR output against field dictionaries when character-level
errors are present.

Unicode ranges used:
- Arabic diacritics (tashkeel): U+064B to U+0652
- Kashida (tatweel): U+0640
- Arabic letters: U+0600 to U+06FF
"""

import re
import unicodedata
from typing import Optional


# Arabic diacritical marks (tashkeel) - Unicode range
ARABIC_DIACRITICS = (
    '\u064B'  # FATHATAN
    '\u064C'  # DAMMATAN
    '\u064D'  # KASRATAN
    '\u064E'  # FATHA
    '\u064F'  # DAMMA
    '\u0650'  # KASRA
    '\u0651'  # SHADDA
    '\u0652'  # SUKUN
    '\u0653'  # MADDAH ABOVE
    '\u0654'  # HAMZA ABOVE
    '\u0655'  # HAMZA BELOW
    '\u0656'  # SUBSCRIPT ALEF
    '\u0657'  # INVERTED DAMMA
    '\u0658'  # MARK NOON GHUNNA
    '\u0659'  # ZWARAKAY
    '\u065A'  # VOWEL SIGN SMALL V ABOVE
    '\u065B'  # VOWEL SIGN INVERTED SMALL V ABOVE
    '\u065C'  # VOWEL SIGN DOT BELOW
    '\u065D'  # REVERSED DAMMA
    '\u065E'  # FATHA WITH TWO DOTS
    '\u065F'  # WAVY HAMZA BELOW
    '\u0670'  # SUPERSCRIPT ALEF
)

# Kashida (tatweel) - Arabic elongation character
KASHIDA = '\u0640'

# Alef variations mapping to plain Alef
ALEF_VARIATIONS = {
    '\u0622': '\u0627',  # ALEF WITH MADDA ABOVE -> ALEF
    '\u0623': '\u0627',  # ALEF WITH HAMZA ABOVE -> ALEF
    '\u0625': '\u0627',  # ALEF WITH HAMZA BELOW -> ALEF
    '\u0671': '\u0627',  # ALEF WASLA -> ALEF
    '\u0672': '\u0627',  # ALEF WITH WAVY HAMZA ABOVE -> ALEF
    '\u0673': '\u0627',  # ALEF WITH WAVY HAMZA BELOW -> ALEF
    '\u0675': '\u0627',  # HIGH HAMZA ALEF -> ALEF
}

# Yaa variations (Alef Maksura -> Yaa)
YAA_VARIATIONS = {
    '\u0649': '\u064A',  # ALEF MAKSURA -> YAA
    '\u06CC': '\u064A',  # FARSI YEH -> YAA
}

# Taa Marbuta to Haa (optional, context-dependent)
TAA_MARBUTA = '\u0629'
HAA = '\u0647'

# Compile regex patterns for performance
DIACRITICS_PATTERN = re.compile(f'[{"".join(ARABIC_DIACRITICS)}]')
KASHIDA_PATTERN = re.compile(KASHIDA)
ALEF_PATTERN = re.compile(f'[{"".join(ALEF_VARIATIONS.keys())}]')
YAA_PATTERN = re.compile(f'[{"".join(YAA_VARIATIONS.keys())}]')
WHITESPACE_PATTERN = re.compile(r'\s+')


def remove_diacritics(text: str) -> str:
    """
    Remove Arabic diacritical marks (tashkeel) from text.

    Diacritics include: fatha, damma, kasra, shadda, sukun, tanween, etc.
    These marks indicate vowels and pronunciation but are often omitted
    in modern Arabic writing and can cause matching issues.

    Args:
        text: Arabic text potentially containing diacritics

    Returns:
        Text with diacritics removed

    Example:
        >>> remove_diacritics("مُحَمَّد")
        'محمد'
    """
    if not text:
        return text
    return DIACRITICS_PATTERN.sub('', text)


def remove_kashida(text: str) -> str:
    """
    Remove kashida (tatweel) characters from text.

    Kashida is an elongation character used for justification in Arabic text.
    It should be removed for text matching purposes.

    Args:
        text: Arabic text potentially containing kashida

    Returns:
        Text with kashida removed

    Example:
        >>> remove_kashida("الـــعربيـــة")
        'العربية'
    """
    if not text:
        return text
    return KASHIDA_PATTERN.sub('', text)


def normalize_alef(text: str) -> str:
    """
    Normalize all Alef variations to plain Alef.

    Arabic has several Alef forms (with hamza above/below, with madda, wasla).
    OCR often confuses these, so normalizing improves matching.

    Normalizations:
        - آ (Alef with Madda) -> ا
        - أ (Alef with Hamza Above) -> ا
        - إ (Alef with Hamza Below) -> ا
        - ٱ (Alef Wasla) -> ا

    Args:
        text: Arabic text with potential Alef variations

    Returns:
        Text with normalized Alef characters

    Example:
        >>> normalize_alef("أحمد إبراهيم آمن")
        'احمد ابراهيم امن'
    """
    if not text:
        return text

    def replace_alef(match):
        return ALEF_VARIATIONS.get(match.group(), match.group())

    return ALEF_PATTERN.sub(replace_alef, text)


def normalize_yaa(text: str) -> str:
    """
    Normalize Yaa variations to standard Yaa.

    Alef Maksura (ى) is often confused with Yaa (ي) by OCR.
    Farsi Yeh is also normalized to Arabic Yaa.

    Args:
        text: Arabic text with potential Yaa variations

    Returns:
        Text with normalized Yaa characters

    Example:
        >>> normalize_yaa("على موسى")
        'علي موسي'
    """
    if not text:
        return text

    def replace_yaa(match):
        return YAA_VARIATIONS.get(match.group(), match.group())

    return YAA_PATTERN.sub(replace_yaa, text)


def normalize_taa_marbuta(text: str, to_haa: bool = False) -> str:
    """
    Optionally normalize Taa Marbuta to Haa.

    Taa Marbuta (ة) and Haa (ه) are sometimes confused by OCR.
    This normalization is optional as it can change meaning.

    Args:
        text: Arabic text
        to_haa: If True, convert ة to ه

    Returns:
        Text with optionally normalized Taa Marbuta

    Example:
        >>> normalize_taa_marbuta("فاتورة", to_haa=True)
        'فاتوره'
    """
    if not text or not to_haa:
        return text
    return text.replace(TAA_MARBUTA, HAA)


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text.

    Collapses multiple spaces to single space and strips leading/trailing.

    Args:
        text: Text with potential irregular whitespace

    Returns:
        Text with normalized whitespace
    """
    if not text:
        return text
    return WHITESPACE_PATTERN.sub(' ', text).strip()


def normalize_arabic(text: str,
                     remove_tashkeel: bool = True,
                     remove_tatweel: bool = True,
                     normalize_alef_chars: bool = True,
                     normalize_yaa_chars: bool = True,
                     normalize_taa: bool = False,
                     normalize_spaces: bool = True) -> str:
    """
    Apply full Arabic text normalization pipeline.

    This is the main function that combines all normalization steps.
    Each step can be individually enabled/disabled.

    Args:
        text: Arabic text to normalize
        remove_tashkeel: Remove diacritical marks (default: True)
        remove_tatweel: Remove kashida/elongation (default: True)
        normalize_alef_chars: Normalize Alef variations (default: True)
        normalize_yaa_chars: Normalize Yaa variations (default: True)
        normalize_taa: Normalize Taa Marbuta to Haa (default: False)
        normalize_spaces: Normalize whitespace (default: True)

    Returns:
        Fully normalized Arabic text

    Example:
        >>> normalize_arabic("فَاتُورَة ضَرِيبِيَّة")
        'فاتورة ضريبية'
    """
    if not text:
        return text

    result = text

    if remove_tashkeel:
        result = remove_diacritics(result)

    if remove_tatweel:
        result = remove_kashida(result)

    if normalize_alef_chars:
        result = normalize_alef(result)

    if normalize_yaa_chars:
        result = normalize_yaa(result)

    if normalize_taa:
        result = normalize_taa_marbuta(result, to_haa=True)

    if normalize_spaces:
        result = normalize_whitespace(result)

    return result


def is_arabic(text: str) -> bool:
    """
    Check if text contains Arabic characters.

    Args:
        text: Text to check

    Returns:
        True if text contains Arabic characters

    Example:
        >>> is_arabic("Hello مرحبا")
        True
        >>> is_arabic("Hello World")
        False
    """
    if not text:
        return False

    for char in text:
        if '\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F':
            return True
    return False


def arabic_ratio(text: str) -> float:
    """
    Calculate the ratio of Arabic characters in text.

    Args:
        text: Text to analyze

    Returns:
        Ratio of Arabic characters (0.0 to 1.0)

    Example:
        >>> arabic_ratio("Hello مرحبا")
        0.5  # approximately
    """
    if not text:
        return 0.0

    text_no_spaces = text.replace(' ', '')
    if not text_no_spaces:
        return 0.0

    arabic_count = sum(
        1 for char in text_no_spaces
        if '\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F'
    )

    return arabic_count / len(text_no_spaces)


def extract_arabic_words(text: str) -> list:
    """
    Extract Arabic words from mixed text.

    Args:
        text: Mixed language text

    Returns:
        List of Arabic words

    Example:
        >>> extract_arabic_words("Invoice فاتورة Number رقم")
        ['فاتورة', 'رقم']
    """
    if not text:
        return []

    words = text.split()
    return [word for word in words if is_arabic(word)]


def extract_non_arabic_words(text: str) -> list:
    """
    Extract non-Arabic words from mixed text.

    Args:
        text: Mixed language text

    Returns:
        List of non-Arabic words

    Example:
        >>> extract_non_arabic_words("Invoice فاتورة Number رقم")
        ['Invoice', 'Number']
    """
    if not text:
        return []

    words = text.split()
    return [word for word in words if word and not is_arabic(word)]


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate Levenshtein distance between two strings.

    This is a simple implementation for cases where rapidfuzz is not available.
    For production use with many comparisons, prefer rapidfuzz.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Edit distance between strings

    Example:
        >>> levenshtein_distance("فاتورة", "فانورة")
        1
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)

    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # j+1 instead of j since previous_row and current_row are one character longer
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def similarity_ratio(s1: str, s2: str) -> float:
    """
    Calculate similarity ratio between two strings.

    Returns a value between 0 (completely different) and 1 (identical).
    Uses Levenshtein distance normalized by the longer string length.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Similarity ratio (0.0 to 1.0)

    Example:
        >>> similarity_ratio("فاتورة", "فانورة")
        0.857  # approximately
    """
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    max_len = max(len(s1), len(s2))
    distance = levenshtein_distance(s1, s2)

    return 1.0 - (distance / max_len)


# Common OCR corrections for Arabic text
# Maps truncated/misread words to correct forms
# Based on analysis of PP-OCRv5 Arabic output patterns
ARABIC_OCR_CORRECTIONS = {
    # ============================================
    # Missing first character corrections (ف، ر، ا)
    # ============================================
    'اتورة': 'فاتورة',           # فاتورة (invoice) - missing ف
    'قم': 'رقم',                 # رقم (number) - missing ر
    'مز': 'رمز',                 # رمز (code) - missing ر
    'لبريد': 'البريد',           # البريد (email) - missing ا
    'لرقم': 'الرقم',             # الرقم (the number) - missing ا
    'لتاريخ': 'التاريخ',         # التاريخ (date) - missing ا
    'لاجمالي': 'الاجمالي',       # الاجمالي (total) - missing ا
    'لاجمالى': 'الاجمالي',       # الاجمالي variant
    'لضريبة': 'الضريبة',         # الضريبة (tax) - missing ا
    'لضريبي': 'الضريبي',         # الضريبي (tax adj) - missing ا
    'لعميل': 'العميل',           # العميل (customer) - missing ا
    'لصنف': 'الصنف',             # الصنف (item) - missing ا
    'لكمية': 'الكمية',           # الكمية (quantity) - missing ا
    'لوحدة': 'الوحدة',           # الوحدة (unit) - missing ا
    'لحساب': 'الحساب',           # الحساب (account) - missing ا
    'لبنك': 'البنك',             # البنك (bank) - missing ا
    'لبنكي': 'البنكي',           # البنكي (banking) - missing ا
    'لمجموع': 'المجموع',         # المجموع (sum) - missing ا
    'لفرعي': 'الفرعي',           # الفرعي (subtotal) - missing ا

    # ============================================
    # Character confusion corrections (similar shapes)
    # ============================================
    # ف/ق confusion (very common in Arabic OCR)
    'تقاصيل': 'تفاصيل',          # تفاصيل (details) - ق→ف
    'قاتورة': 'فاتورة',          # فاتورة (invoice) - ق→ف
    'قرعي': 'فرعي',              # فرعي (sub) - ق→ف
    'الدقع': 'الدفع',            # الدفع (payment) - ق→ف
    'مدقوع': 'مدفوع',            # مدفوع (paid) - ق→ف

    # ن/د confusion
    'البدك': 'البنك',            # البنك (bank) - د→ن
    'البدكي': 'البنكي',          # البنكي (banking) - د→ن
    'البكي': 'البنكي',           # البنكي - missing ن
    'التليقون': 'التليفون',      # التليفون (telephone) - ق→ف
    'الهاتق': 'الهاتف',          # الهاتف (phone) - ق→ف

    # ر/ز confusion
    'الضزيبي': 'الضريبي',        # الضريبي (tax) - ز→ر
    'الضزيبة': 'الضريبة',        # الضريبة (tax) - ز→ر

    # ت/ث/ب confusion
    'الثاريخ': 'التاريخ',        # التاريخ (date) - ث→ت
    'ثاريخ': 'تاريخ',            # تاريخ (date) - ث→ت

    # Missing middle characters
    'الفع': 'الدفع',             # الدفع (payment) - missing د
    'حالة الفع': 'حالة الدفع',   # حالة الدفع (payment status)
    'الليفون': 'التليفون',       # التليفون (telephone) - missing ت
    'التيفون': 'التليفون',       # التليفون - missing ل

    # ============================================
    # ى/ي end confusion (very common)
    # ============================================
    'الالكترولى': 'الالكتروني',  # ى vs ي at end
    'الالكترونى': 'الالكتروني',  # ى vs ي at end
    'الضريبى': 'الضريبي',        # ى vs ي at end
    'البنكى': 'البنكي',          # ى vs ي at end
    'الفرعى': 'الفرعي',          # ى vs ي at end
    'الكلى': 'الكلي',            # ى vs ي at end
    'الاجمالى': 'الاجمالي',      # ى vs ي at end

    # ============================================
    # Invoice-specific terms
    # ============================================
    'nvoice': 'Invoice',         # English - missing I
    'ax': 'Tax',                 # English - missing T

    # ============================================
    # Diacritics-affected words (remove and correct)
    # ============================================
    'قَم': 'رقم',                # رقم with diacritics
    'الَليفون': 'التليفون',      # التليفون with diacritics
    'الَليفُون': 'التليفون',     # التليفون with diacritics
    'قَم الَليفُون': 'رقم التليفون',  # Full phrase

    # ============================================
    # Spacing issues
    # ============================================
    'فاتورةالى': 'فاتورة الى',
    'حالةالدفع': 'حالة الدفع',
    'رقمالفاتورة': 'رقم الفاتورة',
    'رقمالضريبي': 'رقم الضريبي',
    'البريدالالكتروني': 'البريد الالكتروني',
    'تفاصيلالبنك': 'تفاصيل البنك',
    'رقمالحساب': 'رقم الحساب',

    # ============================================
    # Complete phrase corrections
    # ============================================
    'اتورة الى': 'فاتورة الى',   # Bill to
    'تقاصيل البدك': 'تفاصيل البنك',  # Bank details
    'تقاصيل البنك': 'تفاصيل البنك',  # Bank details variant
    'رقم الحساب البكي': 'رقم الحساب البنكي',  # Bank account number

    # ============================================
    # Additional OCR corrections from real invoice testing
    # ============================================
    # Tax invoice terms
    'ضرسة': 'ضريبية',            # ضريبية (tax) - س→ي، missing ي
    'ضرسية': 'ضريبية',           # ضريبية variant
    'مببعات': 'مبيعات',          # مبيعات (sales) - ب→ي
    'مبعات': 'مبيعات',           # مبيعات - missing ي
    'الصغحة': 'الصفحة',          # الصفحة (page) - غ→ف
    'الصفجة': 'الصفحة',          # الصفحة variant
    'صفحة': 'صفحة',              # Keep correct

    # Date/time terms
    'الناريح': 'التاريخ',        # التاريخ (date) - ن→ت، ح→خ
    'الناريخ': 'التاريخ',        # التاريخ variant
    'التاريح': 'التاريخ',        # التاريخ - ح→خ
    'الوفت': 'الوقت',            # الوقت (time) - ف→ق
    'الوقث': 'الوقت',            # الوقت variant
    'المواللف': 'الموافق',       # الموافق (corresponding)
    'الموالق': 'الموافق',        # الموافق variant

    # Numbers/codes
    'رفمر': 'رقم',               # رقم (number) - ف→ق
    'رفم': 'رقم',                # رقم - ف→ق
    'الرفم': 'الرقم',            # الرقم - ف→ق
    'برفم': 'برقم',              # برقم (by number)

    # Customer/client terms
    'فرطاسبة': 'قرطاسية',        # قرطاسية (stationery) - ف→ق، ب→ي
    'فرطاسية': 'قرطاسية',        # قرطاسية variant
    'قرطاسبة': 'قرطاسية',        # قرطاسية variant
    'الشوفية': 'الفاتورة',       # الفاتورة (invoice)
    'اللفون': 'التليفون',        # التليفون (telephone)
    'الليفون': 'التليفون',       # التليفون variant
    'التلفون': 'التليفون',       # التليفون variant

    # Financial terms
    'الاستحفاق': 'الاستحقاق',    # الاستحقاق (entitlement) - ف→ق
    'الاستحقاف': 'الاستحقاق',    # الاستحقاق variant
    'الصافلي': 'الصافي',         # الصافي (net) - ل→nothing
    'الصاللي': 'الصافي',         # الصافي variant
    'هاتضرية': 'الضريبة',        # الضريبة (tax)
    'الاحمالي': 'الاجمالي',      # الاجمالي (total) - ح→ج
    'الأحمالي': 'الاجمالي',      # الاجمالي variant
    'احمالي': 'اجمالي',          # اجمالي variant

    # Company/location terms
    'المركر': 'المركز',          # المركز (center) - ر→ز
    'المركذ': 'المركز',          # المركز variant
    'الرنيسى': 'الرئيسي',        # الرئيسي (main) - ن→ئ
    'الرنيسي': 'الرئيسي',        # الرئيسي variant
    'الريسي': 'الرئيسي',         # الرئيسي - missing ئ
    'الريسى': 'الرئيسي',         # الرئيسي variant

    # Unit/quantity terms
    'الكمبة': 'الكمية',          # الكمية (quantity) - ب→ي
    'الكمبه': 'الكمية',          # الكمية variant
    'الوجدة': 'الوحدة',          # الوحدة (unit) - ج→ح
    'الوجده': 'الوحدة',          # الوحدة variant
    'اعم': 'أصل',                # أصل (original) - ع→ص
    'أعم': 'أصل',                # أصل variant
    'احل': 'أصل',                # أصل variant

    # Additional common errors
    'السعر': 'السعر',            # السعر (price) - correct
    'السغر': 'السعر',            # السعر - غ→ع
    'الصنق': 'الصنف',            # الصنف (item) - ق→ف
    'السائق': 'السابق',          # السابق (previous) - ئ→ب
    'الخصم': 'الخصم',            # الخصم (discount) - correct
    'الفيمة': 'القيمة',          # القيمة (value) - ف→ق
    'الفيمه': 'القيمة',          # القيمة variant
    'المضفة': 'المضافة',         # المضافة (added) - missing ا
    'المضافه': 'المضافة',        # المضافة variant
    'الملاحظات': 'الملاحظات',    # الملاحظات (notes) - correct
    'ملاحظات': 'ملاحظات',        # ملاحظات - correct

    # Seller/receiver terms
    'البايع': 'البائع',          # البائع (seller) - ي→ئ
    'البائغ': 'البائع',          # البائع variant
    'المستلم': 'المستلم',        # المستلم (receiver) - correct
    'المسنلم': 'المستلم',        # المستلم variant
}


def fix_ocr_errors(text: str) -> str:
    """
    Fix common OCR errors in Arabic text.

    Applies corrections for:
    - Missing first characters (common with ف, ر, ا)
    - Character confusions (ى vs ي, ف vs ق, ن vs د)
    - Spacing issues
    - Full phrase corrections

    Args:
        text: OCR output text

    Returns:
        Corrected text

    Example:
        >>> fix_ocr_errors("اتورة ضريبية")
        'فاتورة ضريبية'
    """
    if not text:
        return text

    result = text

    # First pass: Apply phrase-level corrections (longer strings first)
    # Sort by length descending to avoid partial replacements
    sorted_corrections = sorted(
        ARABIC_OCR_CORRECTIONS.items(),
        key=lambda x: len(x[0]),
        reverse=True
    )

    for wrong, correct in sorted_corrections:
        # Skip short patterns in phrase pass (handle in word pass)
        if len(wrong) < 4 and ' ' not in wrong:
            continue

        # Direct replacement for phrases
        if wrong in result:
            # Don't replace if correct form already exists
            if correct not in result:
                result = result.replace(wrong, correct)

    # Second pass: Apply word-level corrections
    for wrong, correct in sorted_corrections:
        # Skip phrases (already handled)
        if ' ' in wrong:
            continue

        # Skip if correct form already exists in text
        if correct in result:
            continue

        # Check for standalone wrong word (not part of larger word)
        # Use word boundary detection suitable for Arabic
        pattern = r'(?:^|(?<=\s))' + re.escape(wrong) + r'(?:$|(?=\s))'
        if re.search(pattern, result):
            result = re.sub(pattern, correct, result)

    return result


def apply_fuzzy_arabic_correction(text: str, threshold: float = 0.75) -> str:
    """
    Apply fuzzy matching to correct Arabic words that are close to known terms.

    Uses Levenshtein distance to find and correct words that are similar
    to common Arabic invoice/document terms.

    Args:
        text: OCR output text
        threshold: Minimum similarity ratio (0-1) for correction

    Returns:
        Corrected text
    """
    if not text:
        return text

    # Common Arabic invoice terms with correct spelling
    CORRECT_TERMS = [
        # Invoice terms
        'فاتورة', 'ضريبية', 'مبيعات', 'ضريبة', 'الضريبة', 'الضريبي',
        # Numbers/codes
        'رقم', 'الرقم', 'برقم', 'رمز',
        # Date/time
        'التاريخ', 'تاريخ', 'الوقت', 'الموافق',
        # Totals
        'الاجمالي', 'اجمالي', 'المجموع', 'الفرعي', 'الصافي', 'المبلغ',
        # Contact
        'البريد', 'الالكتروني', 'التليفون', 'الهاتف',
        # Banking
        'الحساب', 'البنك', 'البنكي', 'الدفع', 'مدفوع',
        # Items
        'تفاصيل', 'الصنف', 'الكمية', 'الوحدة', 'السعر', 'الخصم',
        # Customer/Seller
        'العميل', 'البائع', 'المستلم', 'الشركة',
        # Pages
        'الصفحة', 'صفحة', 'من',
        # Tax terms
        'القيمة', 'المضافة', 'الاستحقاق',
        # Company terms
        'المركز', 'الرئيسي', 'قرطاسية',
        # Other
        'طريقة', 'حالة', 'ملاحظات', 'الملاحظات', 'أصل'
    ]

    words = text.split()
    corrected_words = []

    for word in words:
        # Skip non-Arabic words
        if not is_arabic(word):
            corrected_words.append(word)
            continue

        # Skip if word is already correct
        if word in CORRECT_TERMS:
            corrected_words.append(word)
            continue

        # Find best matching correct term
        best_match = None
        best_ratio = 0

        for correct_term in CORRECT_TERMS:
            ratio = similarity_ratio(word, correct_term)
            if ratio > best_ratio and ratio >= threshold:
                best_ratio = ratio
                best_match = correct_term

        if best_match and best_ratio > threshold:
            corrected_words.append(best_match)
        else:
            corrected_words.append(word)

    return ' '.join(corrected_words)


def post_process_arabic_ocr(text: str, normalize: bool = True, use_fuzzy: bool = True) -> str:
    """
    Full post-processing pipeline for Arabic OCR output.

    Applies:
    1. Arabic normalization (diacritics removal for better matching)
    2. Dictionary-based OCR error corrections
    3. Fuzzy matching corrections (optional)
    4. Whitespace normalization

    Args:
        text: Raw OCR output
        normalize: Whether to apply Arabic normalization
        use_fuzzy: Whether to apply fuzzy matching corrections

    Returns:
        Cleaned and corrected text
    """
    if not text:
        return text

    result = text

    # First: Remove diacritics to improve pattern matching
    # This helps catch words like قَم → رقم
    result = remove_diacritics(result)

    # Second: Apply dictionary-based OCR error corrections
    result = fix_ocr_errors(result)

    # Third: Apply fuzzy matching for remaining errors
    if use_fuzzy:
        result = apply_fuzzy_arabic_correction(result, threshold=0.80)

    # Fourth: Apply full normalization if requested
    if normalize:
        result = normalize_arabic(
            result,
            remove_tashkeel=True,
            remove_tatweel=True,
            normalize_alef_chars=False,  # Keep alef variations for readability
            normalize_yaa_chars=False,   # Keep yaa variations
            normalize_taa=False,
            normalize_spaces=True
        )
    else:
        result = normalize_whitespace(result)

    return result


# ============================================================================
# ADVANCED ARABIC WORD RESTORATION SYSTEM
# ============================================================================
# This system handles truncated Arabic words by detecting patterns and
# restoring missing characters based on invoice/document vocabulary.

# Comprehensive Arabic invoice vocabulary with all variations
# Format: (truncated_pattern, correct_form, english_equivalent)
ARABIC_INVOICE_VOCABULARY = [
    # === Header Terms ===
    ('فاتورة', 'فاتورة', 'invoice'),
    ('اتورة', 'فاتورة', 'invoice'),  # Missing ف
    ('قاتورة', 'فاتورة', 'invoice'),  # ق instead of ف

    # === Number/ID Terms ===
    ('رقم', 'رقم', 'number'),
    ('قم', 'رقم', 'number'),  # Missing ر
    ('الرقم', 'الرقم', 'the number'),
    ('لرقم', 'الرقم', 'the number'),  # Missing ا

    # === Tax Terms ===
    ('الضريبي', 'الضريبي', 'tax'),
    ('لضريبي', 'الضريبي', 'tax'),  # Missing ا
    ('ضريبي', 'الضريبي', 'tax'),  # Missing ال
    ('الضريبة', 'الضريبة', 'tax'),
    ('لضريبة', 'الضريبة', 'tax'),

    # === Phone Terms ===
    ('التليفون', 'التليفون', 'telephone'),
    ('لتليفون', 'التليفون', 'telephone'),  # Missing ا
    ('تليفون', 'التليفون', 'telephone'),  # Missing ال
    ('الهاتف', 'الهاتف', 'phone'),
    ('هاتف', 'الهاتف', 'phone'),

    # === Email Terms ===
    ('البريد', 'البريد', 'mail'),
    ('لبريد', 'البريد', 'mail'),  # Missing ا
    ('بريد', 'البريد', 'mail'),
    ('الالكتروني', 'الالكتروني', 'electronic'),
    ('لالكتروني', 'الالكتروني', 'electronic'),
    ('الكتروني', 'الالكتروني', 'electronic'),
    ('الإلكتروني', 'الالكتروني', 'electronic'),

    # === Date Terms ===
    ('التاريخ', 'التاريخ', 'date'),
    ('لتاريخ', 'التاريخ', 'date'),  # Missing ا
    ('تاريخ', 'تاريخ', 'date'),
    ('الاستحقاق', 'الاستحقاق', 'due'),
    ('لاستحقاق', 'الاستحقاق', 'due'),
    ('استحقاق', 'الاستحقاق', 'due'),

    # === Payment Terms ===
    ('الدفع', 'الدفع', 'payment'),
    ('لدفع', 'الدفع', 'payment'),  # Missing ا
    ('دفع', 'الدفع', 'payment'),
    ('مدفوع', 'مدفوع', 'paid'),
    ('دفوع', 'مدفوع', 'paid'),  # Missing م
    ('حالة', 'حالة', 'status'),
    ('طريقة', 'طريقة', 'method'),
    ('ريقة', 'طريقة', 'method'),  # Missing ط

    # === Bank Terms ===
    ('البنك', 'البنك', 'bank'),
    ('لبنك', 'البنك', 'bank'),  # Missing ا
    ('بنك', 'البنك', 'bank'),
    ('البنكي', 'البنكي', 'banking'),
    ('لبنكي', 'البنكي', 'banking'),
    ('بنكي', 'البنكي', 'banking'),
    ('الحساب', 'الحساب', 'account'),
    ('لحساب', 'الحساب', 'account'),
    ('حساب', 'الحساب', 'account'),
    ('تفاصيل', 'تفاصيل', 'details'),
    ('فاصيل', 'تفاصيل', 'details'),  # Missing ت
    ('قاصيل', 'تفاصيل', 'details'),  # ق instead of تف

    # === Item/Product Terms ===
    ('الصنف', 'الصنف', 'item'),
    ('لصنف', 'الصنف', 'item'),
    ('صنف', 'الصنف', 'item'),
    ('الكمية', 'الكمية', 'quantity'),
    ('لكمية', 'الكمية', 'quantity'),
    ('كمية', 'الكمية', 'quantity'),
    ('الوحدة', 'الوحدة', 'unit'),
    ('لوحدة', 'الوحدة', 'unit'),
    ('وحدة', 'الوحدة', 'unit'),
    ('سعر', 'سعر', 'price'),
    ('عر', 'سعر', 'price'),  # Missing س

    # === Total Terms ===
    ('الاجمالي', 'الاجمالي', 'total'),
    ('لاجمالي', 'الاجمالي', 'total'),
    ('اجمالي', 'الاجمالي', 'total'),
    ('المجموع', 'المجموع', 'sum'),
    ('لمجموع', 'المجموع', 'sum'),
    ('مجموع', 'المجموع', 'sum'),
    ('الفرعي', 'الفرعي', 'subtotal'),
    ('لفرعي', 'الفرعي', 'subtotal'),
    ('فرعي', 'الفرعي', 'subtotal'),

    # === Other Common Terms ===
    ('رمز', 'رمز', 'code'),
    ('مز', 'رمز', 'code'),  # Missing ر
    ('العميل', 'العميل', 'customer'),
    ('لعميل', 'العميل', 'customer'),
    ('عميل', 'العميل', 'customer'),
    ('المبلغ', 'المبلغ', 'amount'),
    ('لمبلغ', 'المبلغ', 'amount'),
    ('مبلغ', 'المبلغ', 'amount'),
]

# Build lookup dictionaries for fast access
_TRUNCATED_TO_CORRECT = {item[0]: item[1] for item in ARABIC_INVOICE_VOCABULARY}
_CORRECT_WORDS = set(item[1] for item in ARABIC_INVOICE_VOCABULARY)


def restore_truncated_arabic_word(word: str) -> str:
    """
    Restore a potentially truncated Arabic word to its correct form.

    This function detects common OCR truncation patterns where the first
    character is missing (especially ر، ف، ا، ت، م، س، ط) and restores
    the word based on invoice vocabulary.

    Args:
        word: Arabic word that may be truncated

    Returns:
        Corrected word if match found, otherwise original word

    Example:
        >>> restore_truncated_arabic_word("قم")
        'رقم'
        >>> restore_truncated_arabic_word("لتليفون")
        'التليفون'
    """
    if not word or not is_arabic(word):
        return word

    # First check if it's already correct
    if word in _CORRECT_WORDS:
        return word

    # Check direct lookup
    if word in _TRUNCATED_TO_CORRECT:
        return _TRUNCATED_TO_CORRECT[word]

    # Try prefix restoration patterns
    # Common missing first characters: ا، ر، ف، ت، م، س، ط، ن
    prefixes_to_try = ['ا', 'ر', 'ف', 'ت', 'م', 'س', 'ط', 'ن', 'ال']

    for prefix in prefixes_to_try:
        candidate = prefix + word
        if candidate in _CORRECT_WORDS:
            return candidate
        if candidate in _TRUNCATED_TO_CORRECT:
            return _TRUNCATED_TO_CORRECT[candidate]

    return word


def restore_arabic_text(text: str) -> str:
    """
    Restore truncated Arabic words in a full text string.

    Processes each word and attempts to restore truncated forms
    based on invoice vocabulary patterns.

    Args:
        text: Full text with potentially truncated Arabic words

    Returns:
        Text with restored Arabic words

    Example:
        >>> restore_arabic_text("قم التليفون 1234567890")
        'رقم التليفون 1234567890'
    """
    if not text:
        return text

    words = text.split()
    restored_words = []

    for word in words:
        restored = restore_truncated_arabic_word(word)
        restored_words.append(restored)

    return ' '.join(restored_words)


# ============================================
# Merged word patterns for splitting
# Format: (merged_pattern, split_result)
# ============================================
ARABIC_MERGED_WORD_SPLITS = [
    # Phone/contact merged with numbers
    (r'ماف(\d+)', r'هاتف \1'),           # ماف920002762 → هاتف 920002762
    (r'هاتف(\d+)', r'هاتف \1'),          # هاتف920002762 → هاتف 920002762
    (r'تلفون(\d+)', r'تليفون \1'),       # تلفون920002762 → تليفون 920002762
    (r'فاكس(\d+)', r'فاكس \1'),          # فاكس920002762 → فاكس 920002762

    # Tax number merged
    (r'رقمارسي', r'رقم ضريبي'),          # رقمارسي → رقم ضريبي
    (r'رقمضريبي', r'رقم ضريبي'),         # رقمضريبي → رقم ضريبي
    (r'الرقمالضريبي', r'الرقم الضريبي'), # الرقمالضريبي → الرقم الضريبي

    # Invoice terms merged
    (r'فاتورةضريبية', r'فاتورة ضريبية'), # فاتورةضريبية → فاتورة ضريبية
    (r'ضريبةالقيمة', r'ضريبة القيمة'),   # ضريبةالقيمة → ضريبة القيمة
    (r'القيمةالمضافة', r'القيمة المضافة'), # القيمةالمضافة → القيمة المضافة

    # Common merged patterns
    (r'(\d+)e([ا-ي])', r'\1 \2'),        # 55000eالتليفون → 55000 التليفون
    (r'([ا-ي]+)(\d+)', r'\1 \2'),        # Split Arabic followed by numbers

    # Name patterns
    (r'المندوبصالح', r'المندوب صالح'),   # المندوبصالح → المندوب صالح
    (r'المدوبصالج', r'المندوب صالح'),    # المدوبصالج → المندوب صالح

    # Common prefix merges
    (r'منال(\w+)', r'من ال\1'),          # منالصفحة → من الصفحة
    (r'فيال(\w+)', r'في ال\1'),          # فيالصفحة → في الصفحة
]

# Additional OCR corrections for remaining errors
ARABIC_OCR_CORRECTIONS_EXTENDED = {
    # Specific errors from invoice analysis
    'الحسنلم': 'المستلم',               # الحسنلم → المستلم
    'الحسلنم': 'المستلم',               # variant
    'المسنلم': 'المستلم',               # المسنلم → المستلم
    'الصسنخدم': 'المستخدم',             # الصسنخدم → المستخدم
    'المسنخدم': 'المستخدم',             # variant
    'التخوارزس': 'الخوارزمي',           # التخوارزس → الخوارزمي (name)
    'المدوبصالج': 'المندوب صالح',       # المدوبصالج → المندوب صالح
    'المدوب': 'المندوب',                # المدوب → المندوب

    # More truncated words
    'صن': 'من',                          # صن → من (from)
    'عن': 'من',                          # sometimes confused
    'رفمر': 'رقم',                       # رفمر → رقم
    'رفم': 'رقم',                        # رفم → رقم

    # Financial terms
    'ضرس': 'ضريبي',                      # ضرس → ضريبي
    'ضرسي': 'ضريبي',                     # ضرسي → ضريبي
    'الصرف1': 'الصرف',                   # Remove trailing number
    'الصرف': 'الصرف',                    # Keep correct

    # Company/location
    'تخوا': 'سكاي',                      # تخوا → سكاي (Skysoft)
    'ليويي': 'لتقنية',                   # ليويي → لتقنية
    'المالة': 'المالية',                 # المالة → المالية
    'والارية': 'والادارية',              # والارية → والادارية
    'الارية': 'الادارية',                # الارية → الادارية

    # Amount in words
    'فغط': 'فقط',                        # فغط → فقط
    'الفان': 'الفين',                    # الفان → الفين (two thousand)
    'ولانمانة': 'وثلاثمائة',             # ولانمانة → وثلاثمائة
    'ربالا': 'ريال',                     # ربالا → ريال
    'لاعير': 'لاغير',                    # لاعير → لاغير
    'لاغبر': 'لاغير',                    # variant

    # Page/document terms
    'الصغحة': 'الصفحة',                  # الصغحة → الصفحة
    'صغحة': 'صفحة',                      # صغحة → صفحة

    # Invoice header terms
    'البوع': 'النوع',                    # البوع → النوع
    'عرض': 'عرض',                        # Keep correct
    'المرجع': 'المرجع',                  # Keep correct
    'العوان': 'العنوان',                 # العوان → العنوان
    'العوانين': 'العناوين',              # العوانين → العناوين

    # Time/date
    'الموالق': 'الموافق',                # الموالق → الموافق
    'المواللف': 'الموافق',               # المواللف → الموافق
}


def split_merged_arabic_words(text: str) -> str:
    """
    Split merged Arabic words using pattern matching.

    Handles cases where OCR merges multiple words together,
    especially Arabic words merged with numbers or other Arabic words.

    Args:
        text: Text with potentially merged words

    Returns:
        Text with merged words split apart
    """
    if not text:
        return text

    result = text

    # Apply regex-based splits
    for pattern, replacement in ARABIC_MERGED_WORD_SPLITS:
        result = re.sub(pattern, replacement, result)

    # Split Arabic word + number combinations
    # Pattern: Arabic letters followed by digits with no space
    result = re.sub(r'([ا-ي]+)(\d{3,})', r'\1 \2', result)

    # Split number + Arabic word combinations
    result = re.sub(r'(\d+)([ا-ي]{2,})', r'\1 \2', result)

    return result


def apply_extended_corrections(text: str) -> str:
    """
    Apply extended OCR corrections for remaining errors.

    This handles specific errors found in invoice analysis
    that weren't covered by the base correction dictionary.

    Args:
        text: Text to correct

    Returns:
        Corrected text
    """
    if not text:
        return text

    result = text

    # Sort by length (longest first) to avoid partial replacements
    sorted_corrections = sorted(
        ARABIC_OCR_CORRECTIONS_EXTENDED.items(),
        key=lambda x: len(x[0]),
        reverse=True
    )

    for wrong, correct in sorted_corrections:
        if wrong in result:
            result = result.replace(wrong, correct)

    return result


def restore_arabic_prefixes(text: str) -> str:
    """
    Restore common Arabic prefixes that may have been truncated.

    Common prefixes: ال (the), ب (with), ل (for), و (and), ف (so)

    Args:
        text: Text with potentially truncated prefixes

    Returns:
        Text with restored prefixes
    """
    if not text:
        return text

    # Words that commonly need ال prefix restored
    WORDS_NEEDING_AL_PREFIX = [
        ('صفحة', 'الصفحة'),
        ('تاريخ', 'التاريخ'),
        ('وقت', 'الوقت'),
        ('رقم', 'الرقم'),
        ('مبلغ', 'المبلغ'),
        ('صنف', 'الصنف'),
        ('كمية', 'الكمية'),
        ('وحدة', 'الوحدة'),
        ('سعر', 'السعر'),
        ('صافي', 'الصافي'),
        ('ضريبة', 'الضريبة'),
        ('اجمالي', 'الاجمالي'),
        ('خصم', 'الخصم'),
        ('عميل', 'العميل'),
        ('بائع', 'البائع'),
        ('مستلم', 'المستلم'),
        ('مندوب', 'المندوب'),
        ('عنوان', 'العنوان'),
        ('هاتف', 'الهاتف'),
        ('بريد', 'البريد'),
        ('بنك', 'البنك'),
        ('حساب', 'الحساب'),
    ]

    words = text.split()
    restored = []

    for word in words:
        # Check if word needs ال prefix
        matched = False
        for base, with_prefix in WORDS_NEEDING_AL_PREFIX:
            if word == base:
                restored.append(with_prefix)
                matched = True
                break

        if not matched:
            restored.append(word)

    return ' '.join(restored)


def multi_pass_correction(text: str, passes: int = 3) -> str:
    """
    Apply correction pipeline multiple times for better results.

    Some corrections may reveal new errors that can be fixed
    in subsequent passes.

    Args:
        text: Text to correct
        passes: Number of correction passes (default: 3)

    Returns:
        Fully corrected text
    """
    if not text:
        return text

    result = text

    for _ in range(passes):
        previous = result

        # Apply all correction steps
        result = fix_ocr_errors(result)
        result = apply_extended_corrections(result)
        result = split_merged_arabic_words(result)
        result = restore_truncated_arabic_word(result)

        # If no changes, stop early
        if result == previous:
            break

    return result


def advanced_arabic_ocr_correction(text: str) -> str:
    """
    Apply advanced Arabic OCR correction with word restoration.

    This is a comprehensive correction pipeline that:
    1. Removes diacritics for better matching
    2. Splits merged words
    3. Applies dictionary-based corrections (multi-pass)
    4. Restores truncated words using vocabulary matching
    5. Applies prefix restoration
    6. Applies fuzzy matching for remaining errors
    7. Normalizes whitespace

    Args:
        text: Raw OCR output text

    Returns:
        Fully corrected Arabic text
    """
    if not text:
        return text

    result = text

    # Step 1: Remove diacritics
    result = remove_diacritics(result)

    # Step 2: Split merged words first
    result = split_merged_arabic_words(result)

    # Step 3: Multi-pass correction (dictionary + extended + truncation)
    result = multi_pass_correction(result, passes=3)

    # Step 4: Restore truncated words
    result = restore_arabic_text(result)

    # Step 5: Restore common prefixes
    result = restore_arabic_prefixes(result)

    # Step 6: Apply fuzzy matching for remaining errors
    result = apply_fuzzy_arabic_correction(result, threshold=0.70)

    # Step 7: Final extended corrections pass
    result = apply_extended_corrections(result)

    # Step 8: Normalize whitespace
    result = normalize_whitespace(result)

    return result
