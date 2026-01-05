"""
Fuzzy string matching utilities for Arabic OCR post-processing.

This module provides fuzzy matching functions using RapidFuzz library.
Fuzzy matching is essential for matching OCR output with character-level
errors against known field dictionaries.

Uses RapidFuzz for performance. Falls back to simple implementation
if RapidFuzz is not installed.
"""

from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

# Try to import rapidfuzz, fall back to basic implementation if not available
try:
    from rapidfuzz import fuzz, process
    from rapidfuzz.distance import Levenshtein
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False

from .arabic_utils import normalize_arabic, similarity_ratio as basic_similarity


@dataclass
class FuzzyMatch:
    """Result of a fuzzy match operation."""
    text: str
    match: str
    score: float
    index: Optional[int] = None

    def __bool__(self) -> bool:
        """Match is truthy if score is above 0."""
        return self.score > 0


def fuzzy_ratio(s1: str, s2: str, normalize: bool = True) -> float:
    """
    Calculate fuzzy similarity ratio between two strings.

    Uses RapidFuzz's ratio for accurate similarity scoring.
    Optionally normalizes Arabic text before comparison.

    Args:
        s1: First string
        s2: Second string
        normalize: Whether to normalize Arabic text first

    Returns:
        Similarity score (0-100)

    Example:
        >>> fuzzy_ratio("فاتورة", "فانورة")
        85.7  # approximately
    """
    if not s1 or not s2:
        return 0.0

    if normalize:
        s1 = normalize_arabic(s1)
        s2 = normalize_arabic(s2)

    if RAPIDFUZZ_AVAILABLE:
        return fuzz.ratio(s1, s2)
    else:
        return basic_similarity(s1, s2) * 100


def fuzzy_partial_ratio(s1: str, s2: str, normalize: bool = True) -> float:
    """
    Calculate partial fuzzy similarity ratio.

    Useful when one string might be a substring of the other.
    For example, matching "فاتورة" against "فاتورة ضريبية".

    Args:
        s1: First string
        s2: Second string
        normalize: Whether to normalize Arabic text first

    Returns:
        Partial similarity score (0-100)

    Example:
        >>> fuzzy_partial_ratio("فاتورة", "فاتورة ضريبية")
        100.0
    """
    if not s1 or not s2:
        return 0.0

    if normalize:
        s1 = normalize_arabic(s1)
        s2 = normalize_arabic(s2)

    if RAPIDFUZZ_AVAILABLE:
        return fuzz.partial_ratio(s1, s2)
    else:
        # Basic implementation: check if shorter string is similar to any substring
        shorter, longer = (s1, s2) if len(s1) <= len(s2) else (s2, s1)
        if shorter in longer:
            return 100.0

        best_score = 0.0
        for i in range(len(longer) - len(shorter) + 1):
            substring = longer[i:i + len(shorter)]
            score = basic_similarity(shorter, substring) * 100
            best_score = max(best_score, score)

        return best_score


def fuzzy_token_sort_ratio(s1: str, s2: str, normalize: bool = True) -> float:
    """
    Calculate token sort ratio.

    Sorts tokens alphabetically before comparison. Useful when
    word order might differ but content is the same.

    Args:
        s1: First string
        s2: Second string
        normalize: Whether to normalize Arabic text first

    Returns:
        Token sort ratio (0-100)

    Example:
        >>> fuzzy_token_sort_ratio("شركة فضاء", "فضاء شركة")
        100.0
    """
    if not s1 or not s2:
        return 0.0

    if normalize:
        s1 = normalize_arabic(s1)
        s2 = normalize_arabic(s2)

    if RAPIDFUZZ_AVAILABLE:
        return fuzz.token_sort_ratio(s1, s2)
    else:
        # Sort tokens and compare
        tokens1 = ' '.join(sorted(s1.split()))
        tokens2 = ' '.join(sorted(s2.split()))
        return basic_similarity(tokens1, tokens2) * 100


def fuzzy_token_set_ratio(s1: str, s2: str, normalize: bool = True) -> float:
    """
    Calculate token set ratio.

    Compares sets of tokens, ignoring duplicates and order.
    Best for matching fields where exact phrasing varies.

    Args:
        s1: First string
        s2: Second string
        normalize: Whether to normalize Arabic text first

    Returns:
        Token set ratio (0-100)

    Example:
        >>> fuzzy_token_set_ratio("فاتورة ضريبية مبسطة", "فاتورة مبسطة")
        100.0
    """
    if not s1 or not s2:
        return 0.0

    if normalize:
        s1 = normalize_arabic(s1)
        s2 = normalize_arabic(s2)

    if RAPIDFUZZ_AVAILABLE:
        return fuzz.token_set_ratio(s1, s2)
    else:
        # Simple set-based comparison
        set1 = set(s1.split())
        set2 = set(s2.split())

        if not set1 or not set2:
            return 0.0

        intersection = set1 & set2
        union = set1 | set2

        return (len(intersection) / len(union)) * 100


def fuzzy_best_match(query: str,
                     candidates: List[str],
                     threshold: int = 70,
                     normalize: bool = True,
                     limit: int = 1) -> Optional[FuzzyMatch]:
    """
    Find the best fuzzy match for a query from a list of candidates.

    Args:
        query: String to match
        candidates: List of candidate strings to match against
        threshold: Minimum score to consider a match (0-100)
        normalize: Whether to normalize Arabic text
        limit: Maximum number of results (default 1 for best match only)

    Returns:
        FuzzyMatch object or None if no match above threshold

    Example:
        >>> fuzzy_best_match("فانورة", ["فاتورة", "رقم", "تاريخ"])
        FuzzyMatch(text='فانورة', match='فاتورة', score=85.7, index=0)
    """
    if not query or not candidates:
        return None

    query_normalized = normalize_arabic(query) if normalize else query
    candidates_normalized = [normalize_arabic(c) if normalize else c for c in candidates]

    if RAPIDFUZZ_AVAILABLE:
        results = process.extractOne(
            query_normalized,
            candidates_normalized,
            score_cutoff=threshold
        )

        if results:
            match_text, score, idx = results
            return FuzzyMatch(
                text=query,
                match=candidates[idx],  # Return original, not normalized
                score=score,
                index=idx
            )
    else:
        best_score = 0.0
        best_idx = -1

        for idx, candidate in enumerate(candidates_normalized):
            score = basic_similarity(query_normalized, candidate) * 100
            if score > best_score:
                best_score = score
                best_idx = idx

        if best_score >= threshold and best_idx >= 0:
            return FuzzyMatch(
                text=query,
                match=candidates[best_idx],
                score=best_score,
                index=best_idx
            )

    return None


def fuzzy_match_all(query: str,
                    candidates: List[str],
                    threshold: int = 70,
                    normalize: bool = True,
                    limit: int = 5) -> List[FuzzyMatch]:
    """
    Find all fuzzy matches above threshold, sorted by score.

    Args:
        query: String to match
        candidates: List of candidate strings
        threshold: Minimum score (0-100)
        normalize: Whether to normalize Arabic text
        limit: Maximum number of results

    Returns:
        List of FuzzyMatch objects sorted by score (descending)

    Example:
        >>> fuzzy_match_all("فاتور", ["فاتورة", "فوترة", "تور"], threshold=60)
        [FuzzyMatch(...), FuzzyMatch(...)]
    """
    if not query or not candidates:
        return []

    query_normalized = normalize_arabic(query) if normalize else query
    candidates_normalized = [normalize_arabic(c) if normalize else c for c in candidates]

    matches = []

    if RAPIDFUZZ_AVAILABLE:
        results = process.extract(
            query_normalized,
            candidates_normalized,
            limit=limit,
            score_cutoff=threshold
        )

        for match_text, score, idx in results:
            matches.append(FuzzyMatch(
                text=query,
                match=candidates[idx],
                score=score,
                index=idx
            ))
    else:
        scored = []
        for idx, candidate in enumerate(candidates_normalized):
            score = basic_similarity(query_normalized, candidate) * 100
            if score >= threshold:
                scored.append((idx, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        for idx, score in scored[:limit]:
            matches.append(FuzzyMatch(
                text=query,
                match=candidates[idx],
                score=score,
                index=idx
            ))

    return matches


def fuzzy_contains(text: str, keyword: str, threshold: int = 75, normalize: bool = True) -> bool:
    """
    Check if text fuzzy-contains a keyword.

    Uses partial ratio to check if keyword appears approximately in text.

    Args:
        text: Text to search in
        keyword: Keyword to search for
        threshold: Minimum partial ratio to consider as "contains"
        normalize: Whether to normalize Arabic text

    Returns:
        True if keyword fuzzy-matches part of text

    Example:
        >>> fuzzy_contains("فانورة ضريبية", "فاتورة", threshold=75)
        True
    """
    if not text or not keyword:
        return False

    score = fuzzy_partial_ratio(keyword, text, normalize=normalize)
    return score >= threshold


def fuzzy_field_match(text: str,
                      field_dict: Dict[str, str],
                      threshold: int = 70,
                      normalize: bool = True) -> Tuple[Optional[str], Optional[str], float]:
    """
    Match text against a field dictionary using fuzzy matching.

    Args:
        text: Text to match (typically Arabic field name from OCR)
        field_dict: Dictionary mapping Arabic fields to English translations
        threshold: Minimum score for match
        normalize: Whether to normalize Arabic text

    Returns:
        Tuple of (arabic_key, english_value, score) or (None, None, 0) if no match

    Example:
        >>> field_dict = {"فاتورة": "Invoice", "رقم": "Number"}
        >>> fuzzy_field_match("فانورة", field_dict, threshold=70)
        ("فاتورة", "Invoice", 85.7)
    """
    if not text or not field_dict:
        return None, None, 0.0

    keys = list(field_dict.keys())
    match = fuzzy_best_match(text, keys, threshold=threshold, normalize=normalize)

    if match:
        arabic_key = match.match
        english_value = field_dict[arabic_key]
        return arabic_key, english_value, match.score

    return None, None, 0.0


def fuzzy_extract_key_value(line: str,
                            field_dict: Dict[str, str],
                            threshold: int = 70,
                            normalize: bool = True) -> Optional[Dict[str, Any]]:
    """
    Extract key-value pair from a line using fuzzy field matching.

    Handles various delimiter patterns (colon, space, etc.) and extracts
    the value following a fuzzy-matched field name.

    Args:
        line: Line of text containing potential key-value pair
        field_dict: Dictionary of known field names
        threshold: Minimum fuzzy score
        normalize: Whether to normalize Arabic text

    Returns:
        Dict with arabic_key, english_key, value, score, or None

    Example:
        >>> field_dict = {"الرقم": "Number", "التاريخ": "Date"}
        >>> fuzzy_extract_key_value("الرقم: 12345", field_dict)
        {'arabic_key': 'الرقم', 'english_key': 'Number', 'value': '12345', 'score': 100.0}
    """
    if not line or not field_dict:
        return None

    # Common delimiters
    delimiters = [':', '؛', '،', '-', '=']

    # Try each delimiter
    for delim in delimiters:
        if delim in line:
            parts = line.split(delim, 1)
            if len(parts) == 2:
                potential_key = parts[0].strip()
                value = parts[1].strip()

                arabic_key, english_key, score = fuzzy_field_match(
                    potential_key, field_dict, threshold=threshold, normalize=normalize
                )

                if arabic_key:
                    return {
                        'arabic_key': arabic_key,
                        'english_key': english_key,
                        'value': value,
                        'score': score
                    }

    # No delimiter found - try matching whole words
    words = line.split()
    for i, word in enumerate(words):
        arabic_key, english_key, score = fuzzy_field_match(
            word, field_dict, threshold=threshold, normalize=normalize
        )

        if arabic_key and score >= threshold:
            # Value is rest of the line after the matched word
            value = ' '.join(words[i + 1:]) if i + 1 < len(words) else ''
            return {
                'arabic_key': arabic_key,
                'english_key': english_key,
                'value': value,
                'score': score
            }

    return None
