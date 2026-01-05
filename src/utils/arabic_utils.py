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
