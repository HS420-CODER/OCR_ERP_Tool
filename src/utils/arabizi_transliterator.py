"""
Arabizi Transliterator Module.

Phase 4: Language Processing
Based on ARABIC_OCR_IMPLEMENTATION_PLAN.md v4.0

Converts Arabizi (Arabic written in Latin script with numbers) to Arabic.
Common in informal digital communication, social media, and chat.

Features:
- Number-to-letter mapping (2=ء, 3=ع, 7=ح, etc.)
- Multi-character pattern handling (sh=ش, kh=خ, etc.)
- Common word dictionary for accurate transliteration
- Confidence scoring for Arabizi detection
- Bidirectional conversion support
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set
import logging

logger = logging.getLogger(__name__)


class TransliterationMode(Enum):
    """Transliteration mode."""
    STRICT = "strict"       # Only known patterns
    LENIENT = "lenient"     # Best-effort for unknown
    PHONETIC = "phonetic"   # Sound-based approximation


@dataclass
class TransliterationResult:
    """
    Result of Arabizi transliteration.

    Attributes:
        original: Original Arabizi text
        arabic: Transliterated Arabic text
        confidence: Confidence in transliteration (0.0-1.0)
        word_mappings: Word-by-word mappings
        unknown_words: Words that couldn't be transliterated
        is_arabizi: Whether input was detected as Arabizi
    """
    original: str
    arabic: str
    confidence: float
    word_mappings: List[Tuple[str, str]] = field(default_factory=list)
    unknown_words: List[str] = field(default_factory=list)
    is_arabizi: bool = False

    def to_dict(self) -> Dict:
        return {
            "original": self.original,
            "arabic": self.arabic,
            "confidence": self.confidence,
            "word_mappings": self.word_mappings,
            "unknown_words": self.unknown_words,
            "is_arabizi": self.is_arabizi,
        }


class ArabiziTransliterator:
    """
    Transliterate Arabizi to Arabic script.

    Arabizi is informal romanization of Arabic using:
    - Numbers for Arabic letters without Latin equivalents
    - Latin letters for similar-sounding Arabic letters

    Number Mappings:
    - 2 = ء (Hamza)
    - 3 = ع (Ain)
    - 3' or gh = غ (Ghain)
    - 5 or kh = خ (Kha)
    - 6 = ط (Ta emphatic)
    - 7 = ح (Ha emphatic)
    - 7' = خ (Kha variant)
    - 8 = ق (Qaf - some dialects)
    - 9 = ص (Sad)
    - 9' = ض (Dad)

    Usage:
        transliterator = ArabiziTransliterator()
        result = transliterator.transliterate("marhaba 7abibi")
        print(result.arabic)  # مرحبا حبيبي
    """

    # Multi-character patterns (checked first, order matters)
    MULTI_CHAR_MAP: Dict[str, str] = {
        # Digraphs
        "sh": "ش",    # Sheen
        "th": "ث",    # Tha
        "kh": "خ",    # Kha
        "dh": "ذ",    # Dhal
        "gh": "غ",    # Ghain
        "ch": "ش",    # Sheen (variant)
        "zh": "ج",    # Jeem (some dialects)

        # Number + apostrophe variants
        "3'": "غ",    # Ghain
        "7'": "خ",    # Kha
        "9'": "ض",    # Dad
        "6'": "ظ",    # Dha

        # Double vowels
        "aa": "ا",    # Alef
        "ee": "ي",    # Ya
        "ii": "ي",    # Ya
        "oo": "و",    # Waw
        "ou": "و",    # Waw
        "uu": "و",    # Waw

        # Common patterns
        "2a": "أ",    # Hamza with Alef
        "2i": "إ",    # Hamza below Alef
        "2u": "أ",    # Hamza with Alef
    }

    # Single character mappings
    SINGLE_CHAR_MAP: Dict[str, str] = {
        # Numbers as Arabic letters
        "2": "ء",     # Hamza
        "3": "ع",     # Ain
        "5": "خ",     # Kha (variant)
        "6": "ط",     # Ta (emphatic)
        "7": "ح",     # Ha (emphatic)
        "8": "ق",     # Qaf (some dialects)
        "9": "ص",     # Sad

        # Latin to Arabic
        "a": "ا",     # Alef
        "b": "ب",     # Ba
        "t": "ت",     # Ta
        "j": "ج",     # Jeem
        "h": "ه",     # Ha (soft)
        "d": "د",     # Dal
        "r": "ر",     # Ra
        "z": "ز",     # Zay
        "s": "س",     # Seen
        "c": "س",     # Seen (variant)
        "f": "ف",     # Fa
        "q": "ق",     # Qaf
        "k": "ك",     # Kaf
        "l": "ل",     # Lam
        "m": "م",     # Meem
        "n": "ن",     # Noon
        "w": "و",     # Waw
        "y": "ي",     # Ya
        "i": "ي",     # Ya (as vowel)
        "e": "ي",     # Ya (as vowel, some dialects)
        "o": "و",     # Waw (as vowel)
        "u": "و",     # Waw (as vowel)
        "v": "ف",     # Fa (foreign words)
        "p": "ب",     # Ba (no P in Arabic)
        "g": "ج",     # Jeem (Egyptian: ج=g)
        "x": "كس",    # Kaf+Seen
        "'": "ع",     # Ain (apostrophe variant)
        "`": "ع",     # Ain (backtick variant)
    }

    # Common Arabizi words dictionary (for accurate transliteration)
    COMMON_WORDS: Dict[str, str] = {
        # Greetings
        "salam": "سلام",
        "ahlan": "أهلاً",
        "marhaba": "مرحبا",
        "sabah": "صباح",
        "masa": "مساء",
        "khair": "خير",
        "shukran": "شكراً",
        "afwan": "عفواً",

        # Common expressions
        "habibi": "حبيبي",
        "habibti": "حبيبتي",
        "yalla": "يلا",
        "khalas": "خلاص",
        "akhi": "أخي",
        "ukhti": "أختي",
        "baba": "بابا",
        "mama": "ماما",

        # Religious expressions
        "inshallah": "إن شاء الله",
        "insha2allah": "إن شاء الله",
        "mashallah": "ما شاء الله",
        "masha2allah": "ما شاء الله",
        "wallah": "والله",
        "wallahi": "والله",
        "bismillah": "بسم الله",
        "alhamdulillah": "الحمد لله",
        "subhanallah": "سبحان الله",
        "astaghfirullah": "أستغفر الله",
        "jazakallah": "جزاك الله",

        # Common words
        "ana": "أنا",
        "inta": "أنت",
        "inti": "أنتِ",
        "huwa": "هو",
        "hiya": "هي",
        "hna": "هنا",
        "hunaka": "هناك",
        "shway": "شوي",
        "kaman": "كمان",
        "bas": "بس",
        "mish": "مش",
        "ma3": "مع",
        "min": "من",
        "ila": "إلى",
        "fi": "في",
        "3ala": "على",
        "la": "لا",
        "na3am": "نعم",
        "aywa": "أيوا",

        # Time
        "yom": "يوم",
        "bokra": "بكرة",
        "ams": "أمس",
        "halla": "هلا",
        "hala2": "هلأ",
        "daba": "دابا",

        # Question words
        "shoo": "شو",
        "shu": "شو",
        "wen": "وين",
        "kef": "كيف",
        "keef": "كيف",
        "lesh": "ليش",
        "laysh": "ليش",
        "kam": "كم",
        "meen": "مين",
        "min": "مين",

        # Invoice/business (for OCR context)
        "fatora": "فاتورة",
        "fatura": "فاتورة",
        "mablagh": "مبلغ",
        "se3r": "سعر",
        "si3r": "سعر",
        "majmoo3": "مجموع",
        "khasm": "خصم",
        "dariba": "ضريبة",
        "daribah": "ضريبة",
    }

    # Arabizi detection patterns
    ARABIZI_NUMBERS = {'2', '3', '5', '6', '7', '8', '9'}

    def __init__(
        self,
        mode: TransliterationMode = TransliterationMode.LENIENT,
        custom_dictionary: Optional[Dict[str, str]] = None,
        detect_threshold: float = 0.05
    ):
        """
        Initialize the transliterator.

        Args:
            mode: Transliteration mode (STRICT, LENIENT, PHONETIC)
            custom_dictionary: Additional word mappings
            detect_threshold: Minimum ratio of Arabizi numbers for detection
        """
        self.mode = mode
        self.detect_threshold = detect_threshold

        # Build combined dictionary
        self.word_dictionary = dict(self.COMMON_WORDS)
        if custom_dictionary:
            self.word_dictionary.update(custom_dictionary)

        # Build sorted multi-char patterns (longest first)
        self._multi_patterns = sorted(
            self.MULTI_CHAR_MAP.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )

        # Compile detection regex
        self._arabizi_number_pattern = re.compile(r'[235679]')
        self._latin_pattern = re.compile(r'[a-zA-Z]')

    def is_arabizi(self, text: str) -> bool:
        """
        Check if text appears to be Arabizi.

        Arabizi typically has:
        - Latin letters mixed with numbers 2,3,5,7,9
        - Number-to-letter ratio between 5-30%

        Args:
            text: Text to check

        Returns:
            True if text appears to be Arabizi
        """
        if not text or len(text) < 3:
            return False

        # Count Arabizi numbers and Latin letters
        arabizi_count = len(self._arabizi_number_pattern.findall(text))
        latin_count = len(self._latin_pattern.findall(text))

        if latin_count < 2:
            return False

        # Calculate ratio
        total = len(text.replace(" ", ""))
        if total == 0:
            return False

        ratio = arabizi_count / total

        # Arabizi typically has 5-30% number usage
        return ratio >= self.detect_threshold and arabizi_count >= 1

    def get_confidence(self, text: str) -> float:
        """
        Get confidence that text is Arabizi.

        Args:
            text: Text to analyze

        Returns:
            Confidence score (0.0-1.0)
        """
        if not text:
            return 0.0

        text_lower = text.lower()
        score = 0.0

        # Check for Arabizi numbers
        arabizi_count = sum(1 for c in text if c in self.ARABIZI_NUMBERS)
        if arabizi_count > 0:
            score += 0.25

        # Check ratio
        total = len(text.replace(" ", ""))
        if total > 0:
            ratio = arabizi_count / total
            if 0.05 <= ratio <= 0.30:
                score += 0.25

        # Check for common Arabizi patterns
        patterns = ['sh', 'kh', 'th', 'gh', 'dh', "3'", "7'"]
        pattern_count = sum(1 for p in patterns if p in text_lower)
        score += min(0.25, pattern_count * 0.08)

        # Check for known words
        words = text_lower.split()
        known_count = sum(1 for w in words if w in self.word_dictionary)
        if words:
            score += min(0.25, (known_count / len(words)) * 0.25)

        return min(1.0, score)

    def transliterate_word(self, word: str) -> Tuple[str, float]:
        """
        Transliterate a single word.

        Args:
            word: Arabizi word

        Returns:
            Tuple of (Arabic text, confidence)
        """
        if not word:
            return "", 0.0

        word_lower = word.lower()

        # Check dictionary first
        if word_lower in self.word_dictionary:
            return self.word_dictionary[word_lower], 1.0

        # Apply pattern-based transliteration
        result = word_lower
        confidence = 0.7  # Base confidence for pattern matching

        # Apply multi-character patterns first
        for pattern, replacement in self._multi_patterns:
            if pattern in result:
                result = result.replace(pattern, replacement)
                confidence = min(confidence + 0.05, 0.95)

        # Apply single-character mappings
        new_result = []
        for char in result:
            if char in self.SINGLE_CHAR_MAP:
                new_result.append(self.SINGLE_CHAR_MAP[char])
            elif char.isspace() or char in '.,;:!?-()[]{}':
                new_result.append(char)
            elif self.mode == TransliterationMode.STRICT:
                # Keep original in strict mode
                new_result.append(char)
                confidence -= 0.1
            else:
                # Try to approximate in lenient mode
                new_result.append(char)
                confidence -= 0.05

        return "".join(new_result), max(0.0, confidence)

    def transliterate(self, text: str) -> TransliterationResult:
        """
        Transliterate Arabizi text to Arabic.

        Args:
            text: Arabizi text

        Returns:
            TransliterationResult with Arabic text and metadata
        """
        if not text:
            return TransliterationResult(
                original=text,
                arabic="",
                confidence=0.0,
                is_arabizi=False
            )

        # Check if text is Arabizi
        is_arabizi = self.is_arabizi(text)

        if not is_arabizi and self.mode == TransliterationMode.STRICT:
            return TransliterationResult(
                original=text,
                arabic=text,
                confidence=0.0,
                is_arabizi=False
            )

        # Split into words
        words = text.split()
        word_mappings = []
        unknown_words = []
        arabic_words = []
        total_confidence = 0.0

        for word in words:
            arabic, conf = self.transliterate_word(word)
            arabic_words.append(arabic)
            word_mappings.append((word, arabic))
            total_confidence += conf

            if conf < 0.5:
                unknown_words.append(word)

        avg_confidence = total_confidence / len(words) if words else 0.0

        return TransliterationResult(
            original=text,
            arabic=" ".join(arabic_words),
            confidence=avg_confidence,
            word_mappings=word_mappings,
            unknown_words=unknown_words,
            is_arabizi=is_arabizi
        )

    def add_word(self, arabizi: str, arabic: str) -> None:
        """
        Add a word to the dictionary.

        Args:
            arabizi: Arabizi word
            arabic: Arabic translation
        """
        self.word_dictionary[arabizi.lower()] = arabic

    def add_words(self, words: Dict[str, str]) -> None:
        """
        Add multiple words to the dictionary.

        Args:
            words: Dictionary of arabizi -> arabic mappings
        """
        for arabizi, arabic in words.items():
            self.add_word(arabizi, arabic)


class ArabicToArabiziConverter:
    """
    Convert Arabic script to Arabizi (reverse transliteration).

    Useful for:
    - Generating training data
    - Testing transliteration accuracy
    - Supporting bidirectional conversion
    """

    # Reverse mapping (Arabic to Latin/Number)
    ARABIC_TO_ARABIZI: Dict[str, str] = {
        # Letters with number representations
        "ء": "2",
        "ع": "3",
        "غ": "3'",
        "خ": "kh",
        "ط": "6",
        "ح": "7",
        "ق": "q",
        "ص": "9",
        "ض": "9'",
        "ظ": "6'",

        # Standard letters
        "ا": "a",
        "أ": "2a",
        "إ": "2i",
        "آ": "2a",
        "ب": "b",
        "ت": "t",
        "ث": "th",
        "ج": "j",
        "ح": "7",
        "د": "d",
        "ذ": "dh",
        "ر": "r",
        "ز": "z",
        "س": "s",
        "ش": "sh",
        "ف": "f",
        "ك": "k",
        "ل": "l",
        "م": "m",
        "ن": "n",
        "ه": "h",
        "و": "w",
        "ي": "y",
        "ى": "a",
        "ة": "a",

        # Diacritics (usually omitted)
        "َ": "a",
        "ُ": "u",
        "ِ": "i",
        "ً": "an",
        "ٌ": "un",
        "ٍ": "in",
        "ّ": "",  # Shadda (double consonant)
        "ْ": "",  # Sukun (no vowel)
    }

    def convert(self, arabic: str) -> str:
        """
        Convert Arabic text to Arabizi.

        Args:
            arabic: Arabic text

        Returns:
            Arabizi transliteration
        """
        result = []
        for char in arabic:
            if char in self.ARABIC_TO_ARABIZI:
                result.append(self.ARABIC_TO_ARABIZI[char])
            elif char.isspace() or char in '.,;:!?-()[]{}0123456789':
                result.append(char)
            else:
                result.append(char)

        return "".join(result)


# Singleton instance
_transliterator_instance: Optional[ArabiziTransliterator] = None


def get_arabizi_transliterator(
    mode: TransliterationMode = TransliterationMode.LENIENT
) -> ArabiziTransliterator:
    """Get singleton instance of Arabizi transliterator."""
    global _transliterator_instance
    if _transliterator_instance is None:
        _transliterator_instance = ArabiziTransliterator(mode=mode)
    return _transliterator_instance


def transliterate_arabizi(text: str) -> str:
    """
    Quick transliteration of Arabizi to Arabic.

    Args:
        text: Arabizi text

    Returns:
        Arabic transliteration
    """
    transliterator = get_arabizi_transliterator()
    result = transliterator.transliterate(text)
    return result.arabic


def is_arabizi(text: str) -> bool:
    """
    Check if text is Arabizi.

    Args:
        text: Text to check

    Returns:
        True if text appears to be Arabizi
    """
    transliterator = get_arabizi_transliterator()
    return transliterator.is_arabizi(text)


def get_arabizi_confidence(text: str) -> float:
    """
    Get confidence that text is Arabizi.

    Args:
        text: Text to analyze

    Returns:
        Confidence score (0.0-1.0)
    """
    transliterator = get_arabizi_transliterator()
    return transliterator.get_confidence(text)
