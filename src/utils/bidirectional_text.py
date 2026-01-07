"""
Bidirectional Text Handler Module.

Phase 4: Language Processing
Based on ARABIC_OCR_IMPLEMENTATION_PLAN.md v4.0 and Unicode UAX #9

Handles Unicode Bidirectional Algorithm for mixed RTL/LTR text.
Essential for correct rendering of Arabic-English mixed content.

Features:
- Unicode Bidi character classification
- RTL/LTR run detection and segmentation
- Logical to visual order conversion
- Mixed content display ordering
- Number handling in Bidi context
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class BidiClass(Enum):
    """
    Unicode Bidirectional Character Types (UAX #9).

    Reference: https://unicode.org/reports/tr9/
    """
    # Strong types
    L = "L"           # Left-to-Right (Latin letters)
    R = "R"           # Right-to-Left (Hebrew)
    AL = "AL"         # Arabic Letter

    # Weak types
    EN = "EN"         # European Number (0-9)
    ES = "ES"         # European Separator (+ -)
    ET = "ET"         # European Terminator (# $ %)
    AN = "AN"         # Arabic Number (٠-٩)
    CS = "CS"         # Common Separator (, . :)
    NSM = "NSM"       # Non-Spacing Mark (diacritics)
    BN = "BN"         # Boundary Neutral (format controls)

    # Neutral types
    B = "B"           # Paragraph Separator
    S = "S"           # Segment Separator
    WS = "WS"         # Whitespace
    ON = "ON"         # Other Neutral (punctuation)

    # Explicit formatting
    LRE = "LRE"       # Left-to-Right Embedding
    LRO = "LRO"       # Left-to-Right Override
    RLE = "RLE"       # Right-to-Left Embedding
    RLO = "RLO"       # Right-to-Left Override
    PDF = "PDF"       # Pop Directional Format
    LRI = "LRI"       # Left-to-Right Isolate
    RLI = "RLI"       # Right-to-Left Isolate
    FSI = "FSI"       # First Strong Isolate
    PDI = "PDI"       # Pop Directional Isolate


class Direction(Enum):
    """Text direction."""
    LTR = "ltr"       # Left-to-Right
    RTL = "rtl"       # Right-to-Left
    NEUTRAL = "neutral"


@dataclass
class BidiRun:
    """
    A run of text with same direction.

    Attributes:
        text: The text content
        direction: Text direction (ltr or rtl)
        start: Start index in original text
        end: End index in original text
        bidi_classes: Bidi classes of each character
        embedding_level: Bidi embedding level
    """
    text: str
    direction: Direction
    start: int
    end: int
    bidi_classes: List[BidiClass] = field(default_factory=list)
    embedding_level: int = 0

    @property
    def length(self) -> int:
        return len(self.text)

    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "direction": self.direction.value,
            "start": self.start,
            "end": self.end,
            "length": self.length,
            "embedding_level": self.embedding_level,
        }


@dataclass
class BidiParagraph:
    """
    A paragraph with resolved bidirectional text.

    Attributes:
        original: Original text (logical order)
        visual: Text in visual order
        runs: List of directional runs
        base_direction: Paragraph base direction
        is_mixed: Whether paragraph contains both RTL and LTR
    """
    original: str
    visual: str
    runs: List[BidiRun]
    base_direction: Direction
    is_mixed: bool = False

    def to_dict(self) -> Dict:
        return {
            "original": self.original,
            "visual": self.visual,
            "runs": [r.to_dict() for r in self.runs],
            "base_direction": self.base_direction.value,
            "is_mixed": self.is_mixed,
        }


class BidirectionalTextHandler:
    """
    Handle bidirectional text for Arabic-English mixed content.

    Implements a simplified version of Unicode Bidi Algorithm (UAX #9)
    optimized for Arabic-English OCR output.

    Key Features:
    - Character classification by Bidi type
    - Strong character detection for base direction
    - Run segmentation by direction
    - Visual order reordering

    Usage:
        handler = BidirectionalTextHandler()
        result = handler.resolve("Hello مرحبا World")
        print(result.visual)  # Properly ordered for display
    """

    # Arabic Unicode ranges
    ARABIC_RANGES = [
        (0x0600, 0x06FF),   # Arabic
        (0x0750, 0x077F),   # Arabic Supplement
        (0x08A0, 0x08FF),   # Arabic Extended-A
        (0xFB50, 0xFDFF),   # Arabic Presentation Forms-A
        (0xFE70, 0xFEFF),   # Arabic Presentation Forms-B
    ]

    # Hebrew range (for completeness)
    HEBREW_RANGE = (0x0590, 0x05FF)

    # Arabic-Indic digits
    ARABIC_INDIC_DIGITS = (0x0660, 0x0669)
    EXTENDED_ARABIC_INDIC = (0x06F0, 0x06F9)

    def __init__(self, default_direction: Direction = Direction.LTR):
        """
        Initialize the handler.

        Args:
            default_direction: Default base direction for neutral text
        """
        self.default_direction = default_direction

    def get_bidi_class(self, char: str) -> BidiClass:
        """
        Get bidirectional class for a character.

        Args:
            char: Single character

        Returns:
            BidiClass enum value
        """
        if not char:
            return BidiClass.ON

        cp = ord(char)

        # Arabic letters
        for start, end in self.ARABIC_RANGES:
            if start <= cp <= end:
                # Check if it's a digit in Arabic range
                if self.ARABIC_INDIC_DIGITS[0] <= cp <= self.ARABIC_INDIC_DIGITS[1]:
                    return BidiClass.AN
                if self.EXTENDED_ARABIC_INDIC[0] <= cp <= self.EXTENDED_ARABIC_INDIC[1]:
                    return BidiClass.AN
                return BidiClass.AL

        # Hebrew letters
        if self.HEBREW_RANGE[0] <= cp <= self.HEBREW_RANGE[1]:
            return BidiClass.R

        # Latin letters (A-Z, a-z)
        if (0x0041 <= cp <= 0x005A) or (0x0061 <= cp <= 0x007A):
            return BidiClass.L

        # Extended Latin
        if (0x00C0 <= cp <= 0x00FF) or (0x0100 <= cp <= 0x017F):
            return BidiClass.L

        # European digits (0-9)
        if 0x0030 <= cp <= 0x0039:
            return BidiClass.EN

        # European separators
        if char in '+-':
            return BidiClass.ES

        # European terminators
        if char in '#$%':
            return BidiClass.ET

        # Common separators
        if char in ',./:;':
            return BidiClass.CS

        # Whitespace
        if char in ' \t\n\r\u00A0':
            return BidiClass.WS

        # Paragraph separator
        if char in '\u2029':
            return BidiClass.B

        # Segment separator
        if char == '\u001F':
            return BidiClass.S

        # Explicit formatting characters
        if char == '\u202A':
            return BidiClass.LRE
        if char == '\u202B':
            return BidiClass.RLE
        if char == '\u202C':
            return BidiClass.PDF
        if char == '\u202D':
            return BidiClass.LRO
        if char == '\u202E':
            return BidiClass.RLO
        if char == '\u2066':
            return BidiClass.LRI
        if char == '\u2067':
            return BidiClass.RLI
        if char == '\u2068':
            return BidiClass.FSI
        if char == '\u2069':
            return BidiClass.PDI

        # Combining marks (approximate)
        if 0x0300 <= cp <= 0x036F:  # Combining diacritical marks
            return BidiClass.NSM
        if 0x064B <= cp <= 0x0655:  # Arabic diacritics
            return BidiClass.NSM

        # Default to other neutral
        return BidiClass.ON

    def get_character_direction(self, char: str) -> Direction:
        """
        Get the direction of a single character.

        Args:
            char: Single character

        Returns:
            Direction enum value
        """
        bidi_class = self.get_bidi_class(char)

        if bidi_class in (BidiClass.L,):
            return Direction.LTR
        elif bidi_class in (BidiClass.R, BidiClass.AL):
            return Direction.RTL
        else:
            return Direction.NEUTRAL

    def detect_base_direction(self, text: str) -> Direction:
        """
        Detect paragraph base direction from first strong character.

        Args:
            text: Text to analyze

        Returns:
            Base direction (LTR or RTL)
        """
        for char in text:
            bidi_class = self.get_bidi_class(char)
            if bidi_class == BidiClass.L:
                return Direction.LTR
            elif bidi_class in (BidiClass.R, BidiClass.AL):
                return Direction.RTL

        return self.default_direction

    def segment_runs(self, text: str) -> List[BidiRun]:
        """
        Segment text into directional runs.

        Args:
            text: Text to segment

        Returns:
            List of BidiRun objects
        """
        if not text:
            return []

        runs = []
        current_run_chars = []
        current_direction = None
        current_start = 0
        current_classes = []

        for i, char in enumerate(text):
            bidi_class = self.get_bidi_class(char)
            char_dir = self.get_character_direction(char)

            # Determine effective direction
            if char_dir == Direction.NEUTRAL:
                # Neutral characters inherit direction
                effective_dir = current_direction or self.default_direction
            else:
                effective_dir = char_dir

            # Check if we need to start a new run
            if current_direction is None:
                current_direction = effective_dir
            elif effective_dir != Direction.NEUTRAL and effective_dir != current_direction:
                # Save current run
                if current_run_chars:
                    runs.append(BidiRun(
                        text="".join(current_run_chars),
                        direction=current_direction,
                        start=current_start,
                        end=i,
                        bidi_classes=current_classes.copy()
                    ))
                # Start new run
                current_run_chars = []
                current_classes = []
                current_start = i
                current_direction = effective_dir

            current_run_chars.append(char)
            current_classes.append(bidi_class)

        # Don't forget last run
        if current_run_chars:
            runs.append(BidiRun(
                text="".join(current_run_chars),
                direction=current_direction or self.default_direction,
                start=current_start,
                end=len(text),
                bidi_classes=current_classes
            ))

        return runs

    def resolve(self, text: str, base_direction: Optional[Direction] = None) -> BidiParagraph:
        """
        Resolve bidirectional text for display.

        Args:
            text: Input text (logical order)
            base_direction: Force base direction (auto-detect if None)

        Returns:
            BidiParagraph with resolved text
        """
        if not text:
            return BidiParagraph(
                original=text,
                visual=text,
                runs=[],
                base_direction=self.default_direction,
                is_mixed=False
            )

        # Detect or use provided base direction
        if base_direction is None:
            base_direction = self.detect_base_direction(text)

        # Segment into runs
        runs = self.segment_runs(text)

        # Check if mixed
        directions = set(r.direction for r in runs if r.direction != Direction.NEUTRAL)
        is_mixed = len(directions) > 1

        # Reorder runs for visual display
        visual_text = self._reorder_for_display(runs, base_direction)

        return BidiParagraph(
            original=text,
            visual=visual_text,
            runs=runs,
            base_direction=base_direction,
            is_mixed=is_mixed
        )

    def _reorder_for_display(self, runs: List[BidiRun], base_direction: Direction) -> str:
        """
        Reorder runs for visual display.

        Args:
            runs: List of directional runs
            base_direction: Paragraph base direction

        Returns:
            Text in visual order
        """
        if not runs:
            return ""

        # Assign embedding levels
        # Simplified: RTL runs get odd levels, LTR runs get even levels
        for run in runs:
            if run.direction == Direction.RTL:
                run.embedding_level = 1 if base_direction == Direction.LTR else 0
            else:
                run.embedding_level = 0 if base_direction == Direction.LTR else 1

        # For RTL base direction, reverse the order of runs
        if base_direction == Direction.RTL:
            ordered_runs = list(reversed(runs))
        else:
            ordered_runs = runs

        # Build visual text
        visual_parts = []
        for run in ordered_runs:
            if run.direction == Direction.RTL:
                # Reverse RTL runs
                visual_parts.append(run.text[::-1])
            else:
                visual_parts.append(run.text)

        return "".join(visual_parts)

    def get_display_text(self, text: str) -> str:
        """
        Quick method to get display-ready text.

        Args:
            text: Input text (logical order)

        Returns:
            Text in visual order
        """
        result = self.resolve(text)
        return result.visual

    def wrap_rtl(self, text: str) -> str:
        """
        Wrap text with RTL marks for correct display.

        Args:
            text: Arabic or RTL text

        Returns:
            Text wrapped with RLM markers
        """
        RLM = '\u200F'  # Right-to-Left Mark
        return f"{RLM}{text}{RLM}"

    def wrap_ltr(self, text: str) -> str:
        """
        Wrap text with LTR marks for correct display.

        Args:
            text: English or LTR text

        Returns:
            Text wrapped with LRM markers
        """
        LRM = '\u200E'  # Left-to-Right Mark
        return f"{LRM}{text}{LRM}"

    def embed_rtl(self, text: str) -> str:
        """
        Embed RTL text using Unicode embedding controls.

        Args:
            text: Text to embed as RTL

        Returns:
            Text with RLE/PDF markers
        """
        RLE = '\u202B'  # Right-to-Left Embedding
        PDF = '\u202C'  # Pop Directional Format
        return f"{RLE}{text}{PDF}"

    def embed_ltr(self, text: str) -> str:
        """
        Embed LTR text using Unicode embedding controls.

        Args:
            text: Text to embed as LTR

        Returns:
            Text with LRE/PDF markers
        """
        LRE = '\u202A'  # Left-to-Right Embedding
        PDF = '\u202C'  # Pop Directional Format
        return f"{LRE}{text}{PDF}"

    def isolate_rtl(self, text: str) -> str:
        """
        Isolate RTL text using Unicode isolate controls.

        Args:
            text: Text to isolate as RTL

        Returns:
            Text with RLI/PDI markers
        """
        RLI = '\u2067'  # Right-to-Left Isolate
        PDI = '\u2069'  # Pop Directional Isolate
        return f"{RLI}{text}{PDI}"

    def isolate_ltr(self, text: str) -> str:
        """
        Isolate LTR text using Unicode isolate controls.

        Args:
            text: Text to isolate as LTR

        Returns:
            Text with LRI/PDI markers
        """
        LRI = '\u2066'  # Left-to-Right Isolate
        PDI = '\u2069'  # Pop Directional Isolate
        return f"{LRI}{text}{PDI}"

    def format_mixed_text(
        self,
        arabic: str,
        english: str,
        separator: str = " "
    ) -> str:
        """
        Format mixed Arabic-English text for display.

        Args:
            arabic: Arabic text part
            english: English text part
            separator: Separator between parts

        Returns:
            Properly formatted mixed text
        """
        # Wrap each part with appropriate marks
        arabic_wrapped = self.wrap_rtl(arabic)
        english_wrapped = self.wrap_ltr(english)

        return f"{arabic_wrapped}{separator}{english_wrapped}"

    def is_rtl_dominant(self, text: str) -> bool:
        """
        Check if text is predominantly RTL.

        Args:
            text: Text to analyze

        Returns:
            True if more RTL than LTR characters
        """
        rtl_count = 0
        ltr_count = 0

        for char in text:
            direction = self.get_character_direction(char)
            if direction == Direction.RTL:
                rtl_count += 1
            elif direction == Direction.LTR:
                ltr_count += 1

        return rtl_count > ltr_count

    def get_direction_ratio(self, text: str) -> Dict[str, float]:
        """
        Get ratio of RTL/LTR/Neutral characters.

        Args:
            text: Text to analyze

        Returns:
            Dict with direction ratios
        """
        if not text:
            return {"rtl": 0.0, "ltr": 0.0, "neutral": 1.0}

        rtl_count = 0
        ltr_count = 0
        neutral_count = 0

        for char in text:
            direction = self.get_character_direction(char)
            if direction == Direction.RTL:
                rtl_count += 1
            elif direction == Direction.LTR:
                ltr_count += 1
            else:
                neutral_count += 1

        total = len(text)
        return {
            "rtl": rtl_count / total,
            "ltr": ltr_count / total,
            "neutral": neutral_count / total,
        }


# Singleton instance
_handler_instance: Optional[BidirectionalTextHandler] = None


def get_bidi_handler(
    default_direction: Direction = Direction.LTR
) -> BidirectionalTextHandler:
    """Get singleton instance of bidirectional text handler."""
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = BidirectionalTextHandler(default_direction)
    return _handler_instance


def resolve_bidi(text: str) -> BidiParagraph:
    """
    Resolve bidirectional text.

    Args:
        text: Text to resolve

    Returns:
        BidiParagraph with resolved text
    """
    handler = get_bidi_handler()
    return handler.resolve(text)


def get_visual_text(text: str) -> str:
    """
    Get text in visual display order.

    Args:
        text: Text in logical order

    Returns:
        Text in visual order
    """
    handler = get_bidi_handler()
    return handler.get_display_text(text)


def detect_direction(text: str) -> Direction:
    """
    Detect base direction of text.

    Args:
        text: Text to analyze

    Returns:
        Detected direction
    """
    handler = get_bidi_handler()
    return handler.detect_base_direction(text)


def is_rtl(text: str) -> bool:
    """
    Check if text base direction is RTL.

    Args:
        text: Text to check

    Returns:
        True if RTL
    """
    return detect_direction(text) == Direction.RTL


def is_ltr(text: str) -> bool:
    """
    Check if text base direction is LTR.

    Args:
        text: Text to check

    Returns:
        True if LTR
    """
    return detect_direction(text) == Direction.LTR
