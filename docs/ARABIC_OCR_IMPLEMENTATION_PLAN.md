# Arabic OCR Ultimate Enhancement - Implementation Plan

**Version:** 1.0
**Based On:** ARABIC_OCR_ULTIMATE_ENHANCEMENT.md v5.3
**Created:** 2026-01-07
**Target:** Production-ready bilingual Arabic-English OCR

---

## Executive Summary

This implementation plan provides a comprehensive roadmap to build all components documented in `ARABIC_OCR_ULTIMATE_ENHANCEMENT.md` v5.3. The goal is to create a production-ready bilingual Arabic-English OCR system with multi-engine fusion, character-level correction, and morphological analysis.

### Key Metrics

| Metric | Value |
|--------|-------|
| **Total Components** | 18 major modules |
| **New Code** | ~4,500 lines |
| **New Files** | 13 files |
| **Implementation Phases** | 6 phases |

### Target Benchmarks

| Metric | Arabic | English | Mixed |
|--------|--------|---------|-------|
| **CER** | <0.06 | <0.02 | <0.08 |
| **WER** | <0.16 | <0.04 | <0.12 |
| **Speed** | >5 img/s | >10 img/s | >3 img/s |

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Gap Analysis](#2-gap-analysis)
3. [Phase 1: Foundation](#3-phase-1-foundation)
4. [Phase 2: Core Processing](#4-phase-2-core-processing)
5. [Phase 3: Multi-Engine Fusion](#5-phase-3-multi-engine-fusion)
6. [Phase 4: Language Processing](#6-phase-4-language-processing)
7. [Phase 5: Validation & Scoring](#7-phase-5-validation--scoring)
8. [Phase 6: Production Pipeline](#8-phase-6-production-pipeline)
9. [Data Files Required](#9-data-files-required)
10. [Testing Strategy](#10-testing-strategy)
11. [File Structure](#11-file-structure)
12. [Implementation Order](#12-implementation-order)
13. [Success Criteria](#13-success-criteria)
14. [Risk Mitigation](#14-risk-mitigation)
15. [Appendix A: API Reference](#appendix-a-api-reference)
16. [Appendix B: Configuration Reference](#appendix-b-configuration-reference)

---

## 1. Current State Analysis

### 1.1 Already Implemented Components

The following components are already implemented and should be leveraged:

| Component | File | Lines | Status | Notes |
|-----------|------|-------|--------|-------|
| PaddleOCR Engine | `src/engines/paddle_engine.py` | 1,898 | ✅ Complete | 6-stage pipeline |
| Tesseract Engine | `src/engines/tesseract_engine.py` | 549 | ✅ Complete | Fallback engine |
| Arabic Spell Checker | `src/utils/arabic_spell_checker.py` | 562 | ✅ Complete | Has confusion matrix |
| Arabic Word Separator | `src/utils/arabic_word_separator.py` | 475 | ✅ Complete | Word boundary detection |
| Arabic Number Normalizer | `src/utils/arabic_number_normalizer.py` | 564 | ✅ Complete | Number handling |
| Bilingual Formatter | `src/formatters/bilingual_formatter.py` | 100+ | ✅ Complete | Output formatting |
| Confidence Scorer | `src/validators/confidence_scorer.py` | 100+ | ⚠️ Partial | Needs bilingual support |
| Fusion Engine | `src/services/fusion_engine.py` | 80+ | ⚠️ Partial | Basic fusion only |
| Engine Manager | `src/engine_manager.py` | 334 | ✅ Complete | Engine orchestration |
| Read Tool | `src/read_tool.py` | 534 | ✅ Complete | Main entry point |

### 1.2 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        HybridReadTool                               │
│                      (src/read_tool.py)                             │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        EngineManager                                │
│                    (src/engine_manager.py)                          │
└─────────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ PaddleEngine  │     │TesseractEngine│     │ OllamaEngine  │
│   (Primary)   │     │  (Fallback)   │     │   (Vision)    │
└───────────────┘     └───────────────┘     └───────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Post-Processing Pipeline                          │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐       │
│  │   Spell    │→│   Word     │→│  Number    │→│ Bilingual  │       │
│  │  Checker   │ │ Separator  │ │ Normalizer │ │ Formatter  │       │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Gap Analysis

### 2.1 Components to Implement

| Component | Section in Doc | Priority | Est. Lines | Complexity |
|-----------|----------------|----------|------------|------------|
| ArabicOCRConfig | 8.1 | 🔴 CRITICAL | 100 | Low |
| ArabicConfusionMatrix (standalone) | 3.1 | 🔴 CRITICAL | 200 | Medium |
| ArabicNGramModel | 3.3 | 🔴 CRITICAL | 150 | Medium |
| ArabicBeamCorrector | 3.2 | 🟠 HIGH | 250 | High |
| ArabicMorphologicalAnalyzer | 4.3 | 🟠 HIGH | 300 | High |
| ArabicBPETokenizer | 4.4 | 🟠 HIGH | 200 | Medium |
| OCRFusionEngine (enhanced) | 5.2-5.3 | 🟠 HIGH | 250 | High |
| WordLevelLanguageDetector | 13.3 | 🟡 MEDIUM | 200 | Medium |
| ArabiziTransliterator | - | 🟡 MEDIUM | 150 | Low |
| BidirectionalTextHandler | - | 🟡 MEDIUM | 200 | Medium |
| EnglishOCRValidator | 15.3 | 🟡 MEDIUM | 250 | Medium |
| BilingualConfidenceScorer | - | 🟠 HIGH | 150 | Medium |
| BilingualOCRPipeline | 17.1 | 🟠 HIGH | 300 | High |

### 2.2 Dependency Graph

```
                    ┌─────────────────────┐
                    │  ArabicOCRConfig    │
                    │     (Phase 1)       │
                    └─────────┬───────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ConfusionMatrix│   │ ArabicNGram   │   │ WordLevel     │
│  (Phase 1)    │   │   (Phase 1)   │   │ Detector (P4) │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        └───────────┬───────┘                   │
                    ▼                           │
          ┌───────────────┐                     │
          │ BeamCorrector │                     │
          │   (Phase 2)   │                     │
          └───────┬───────┘                     │
                  │                             │
        ┌─────────┴─────────┐                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  Morphology   │   │ BPETokenizer  │   │   English     │
│  (Phase 2)    │   │   (Phase 2)   │   │ Validator (P5)│
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        └───────────┬───────┴───────────────────┘
                    ▼
          ┌───────────────┐
          │ FusionEngine  │
          │   (Phase 3)   │
          └───────┬───────┘
                  │
                  ▼
          ┌───────────────┐
          │  Bilingual    │
          │Pipeline (P6)  │
          └───────────────┘
```

---

## 3. Phase 1: Foundation

**Duration:** 3-4 days
**Dependencies:** None
**Deliverables:** 3 new files, ~450 lines

### 3.1 Configuration System

**File:** `src/config/arabic_ocr_config.py`

```python
"""
Arabic OCR Configuration System

Provides preset configurations for different accuracy/speed tradeoffs:
- FAST: Single engine, minimal post-processing
- BALANCED: Primary + fallback, standard post-processing
- ACCURATE: Multi-engine fusion, full post-processing
- MAXIMUM: All engines + VLM fallback, exhaustive correction
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

class OCRMode(Enum):
    FAST = "fast"
    BALANCED = "balanced"
    ACCURATE = "accurate"
    MAXIMUM = "maximum"

@dataclass
class ArabicOCRConfig:
    """Main configuration for Arabic OCR pipeline."""

    # Operating mode
    mode: OCRMode = OCRMode.BALANCED

    # Engine settings
    primary_engine: str = "paddle"
    fallback_engine: str = "tesseract"
    enable_easyocr: bool = False
    enable_qari_vlm: bool = False

    # Confidence thresholds
    high_confidence_threshold: float = 0.85
    low_confidence_threshold: float = 0.50
    vlm_trigger_threshold: float = 0.40

    # Correction settings
    beam_width: int = 5
    max_corrections_per_word: int = 3
    enable_morphological_analysis: bool = True
    enable_ngram_scoring: bool = True

    # Engine weights for fusion
    engine_weights: Dict[str, float] = field(default_factory=lambda: {
        'paddle': 1.0,
        'easyocr': 0.8,
        'qari': 1.2,
        'tesseract': 0.6
    })

    # PaddleOCR Arabic-specific settings (from Context7 research)
    paddle_config: Dict[str, any] = field(default_factory=lambda: {
        'text_det_limit_side_len': 1280,  # Default 960, Arabic needs 1280+
        'text_det_unclip_ratio': 1.8,     # Default 1.5, Arabic needs 1.8-2.0
        'text_det_thresh': 0.3,
        'text_det_box_thresh': 0.6,
        'text_rec_score_thresh': 0.5,
    })

# Preset configurations
FAST_CONFIG = ArabicOCRConfig(
    mode=OCRMode.FAST,
    enable_easyocr=False,
    enable_qari_vlm=False,
    beam_width=1,
    max_corrections_per_word=1,
    enable_morphological_analysis=False,
    enable_ngram_scoring=False,
)

BALANCED_CONFIG = ArabicOCRConfig(
    mode=OCRMode.BALANCED,
    enable_easyocr=False,
    enable_qari_vlm=False,
    beam_width=3,
    max_corrections_per_word=2,
)

ACCURATE_CONFIG = ArabicOCRConfig(
    mode=OCRMode.ACCURATE,
    enable_easyocr=True,
    enable_qari_vlm=False,
    beam_width=5,
    max_corrections_per_word=3,
)

MAXIMUM_CONFIG = ArabicOCRConfig(
    mode=OCRMode.MAXIMUM,
    enable_easyocr=True,
    enable_qari_vlm=True,
    beam_width=10,
    max_corrections_per_word=5,
)

def get_config(mode: str) -> ArabicOCRConfig:
    """Get configuration by mode name."""
    configs = {
        'fast': FAST_CONFIG,
        'balanced': BALANCED_CONFIG,
        'accurate': ACCURATE_CONFIG,
        'maximum': MAXIMUM_CONFIG,
    }
    return configs.get(mode.lower(), BALANCED_CONFIG)
```

### 3.2 Arabic Confusion Matrix (Standalone)

**File:** `src/utils/arabic_confusion_matrix.py`

Extract and enhance from existing `arabic_spell_checker.py`:

```python
"""
Arabic OCR Confusion Matrix

Position-aware character confusion probabilities for Arabic OCR correction.
Based on empirical analysis of PaddleOCR and Tesseract output errors.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from enum import Enum

class CharPosition(Enum):
    INITIAL = "initial"
    MEDIAL = "medial"
    FINAL = "final"
    ISOLATED = "isolated"

@dataclass
class ConfusionEntry:
    """Single confusion pair with probability."""
    target: str
    probability: float
    position_bias: Dict[CharPosition, float] = None

# Main confusion matrix - OCR errors with position-aware probabilities
CONFUSION_MATRIX: Dict[str, List[ConfusionEntry]] = {
    # Dotted letters (most common errors)
    'ب': [
        ConfusionEntry('ت', 0.35, {CharPosition.INITIAL: 0.40, CharPosition.MEDIAL: 0.35}),
        ConfusionEntry('ث', 0.25),
        ConfusionEntry('ن', 0.20, {CharPosition.FINAL: 0.30}),
        ConfusionEntry('ي', 0.15, {CharPosition.FINAL: 0.25}),
    ],
    'ت': [
        ConfusionEntry('ب', 0.35),
        ConfusionEntry('ث', 0.30),
        ConfusionEntry('ن', 0.20),
    ],
    'ث': [
        ConfusionEntry('ت', 0.40),
        ConfusionEntry('ب', 0.25),
    ],

    # Similar shapes
    'ج': [
        ConfusionEntry('ح', 0.45),
        ConfusionEntry('خ', 0.35),
    ],
    'ح': [
        ConfusionEntry('ج', 0.40),
        ConfusionEntry('خ', 0.40),
    ],
    'خ': [
        ConfusionEntry('ح', 0.45),
        ConfusionEntry('ج', 0.30),
    ],

    # Alef variations
    'ا': [
        ConfusionEntry('أ', 0.30),
        ConfusionEntry('إ', 0.25),
        ConfusionEntry('آ', 0.20),
        ConfusionEntry('ٱ', 0.15),
    ],
    'أ': [
        ConfusionEntry('ا', 0.40),
        ConfusionEntry('إ', 0.30),
    ],

    # Yaa/Alef Maksura
    'ي': [
        ConfusionEntry('ى', 0.50, {CharPosition.FINAL: 0.70}),
        ConfusionEntry('ئ', 0.25),
    ],
    'ى': [
        ConfusionEntry('ي', 0.55),
        ConfusionEntry('ا', 0.20),
    ],

    # Haa/Taa Marbuta
    'ه': [
        ConfusionEntry('ة', 0.45, {CharPosition.FINAL: 0.60}),
    ],
    'ة': [
        ConfusionEntry('ه', 0.50),
        ConfusionEntry('ت', 0.25),
    ],

    # Raa/Zay
    'ر': [
        ConfusionEntry('ز', 0.40),
    ],
    'ز': [
        ConfusionEntry('ر', 0.45),
    ],

    # Dal/Thal
    'د': [
        ConfusionEntry('ذ', 0.45),
    ],
    'ذ': [
        ConfusionEntry('د', 0.50),
    ],

    # Sad/Dad
    'ص': [
        ConfusionEntry('ض', 0.40),
    ],
    'ض': [
        ConfusionEntry('ص', 0.45),
    ],

    # Taa/Zaa
    'ط': [
        ConfusionEntry('ظ', 0.45),
    ],
    'ظ': [
        ConfusionEntry('ط', 0.50),
    ],

    # Ain/Ghain
    'ع': [
        ConfusionEntry('غ', 0.35),
    ],
    'غ': [
        ConfusionEntry('ع', 0.40),
    ],

    # Faa/Qaf
    'ف': [
        ConfusionEntry('ق', 0.30),
    ],
    'ق': [
        ConfusionEntry('ف', 0.35),
    ],
}

class ArabicConfusionMatrix:
    """Arabic OCR confusion matrix with position-aware candidates."""

    def __init__(self, custom_matrix: Dict = None):
        self.matrix = custom_matrix or CONFUSION_MATRIX

    def get_candidates(
        self,
        char: str,
        position: CharPosition = None,
        min_probability: float = 0.1
    ) -> List[Tuple[str, float]]:
        """
        Get confusion candidates for a character.

        Args:
            char: Source character
            position: Character position in word
            min_probability: Minimum probability threshold

        Returns:
            List of (candidate_char, probability) tuples
        """
        if char not in self.matrix:
            return []

        results = []
        for entry in self.matrix[char]:
            prob = entry.probability

            # Apply position bias if available
            if position and entry.position_bias:
                prob = entry.position_bias.get(position, prob)

            if prob >= min_probability:
                results.append((entry.target, prob))

        return sorted(results, key=lambda x: -x[1])

    def get_confusion_probability(
        self,
        source: str,
        target: str,
        position: CharPosition = None
    ) -> float:
        """Get probability of source being confused with target."""
        if source not in self.matrix:
            return 0.0

        for entry in self.matrix[source]:
            if entry.target == target:
                prob = entry.probability
                if position and entry.position_bias:
                    prob = entry.position_bias.get(position, prob)
                return prob

        return 0.0

    def get_all_confusable_chars(self) -> set:
        """Get all characters that have confusion entries."""
        chars = set(self.matrix.keys())
        for entries in self.matrix.values():
            for entry in entries:
                chars.add(entry.target)
        return chars

    def is_confusable(self, char: str) -> bool:
        """Check if character has confusion candidates."""
        return char in self.matrix
```

### 3.3 Arabic N-Gram Model

**File:** `src/ml/arabic_ngram_model.py`

```python
"""
Arabic N-Gram Language Model

Character and word n-gram scoring for Arabic OCR validation.
Used by beam search corrector to score candidate corrections.
"""

import json
import math
from pathlib import Path
from typing import Dict, Optional

# Common Arabic trigrams with log probabilities
# Source: Extracted from Arabic Wikipedia and news corpus
COMMON_TRIGRAMS: Dict[str, float] = {
    # Most frequent trigrams (normalized log probabilities)
    'ال ': -2.5,   # The (definite article)
    ' ال': -2.6,
    'لال': -3.2,
    'ية ': -3.5,   # -iyya suffix
    'في ': -3.8,   # in
    ' في': -3.9,
    'من ': -4.0,   # from
    ' من': -4.1,
    'ان ': -4.2,
    'ون ': -4.3,
    'ات ': -4.4,
    'ين ': -4.5,
    'لى ': -4.6,   # على
    'على': -4.7,
    'عل ': -4.8,
    ' عل': -4.9,
    'ذا ': -5.0,   # هذا
    'هذا': -5.1,
    'ما ': -5.2,
    ' ما': -5.3,
    'كان': -5.4,
    'قال': -5.5,
    'إلى': -5.6,
    'بين': -5.7,
    'حتى': -5.8,
    'أنه': -5.9,
    'التي': -6.0,
}

# Rare/invalid trigrams (penalty scores)
INVALID_TRIGRAMS: Dict[str, float] = {
    'ءءء': -20.0,
    'ؤؤؤ': -20.0,
    'ئئئ': -20.0,
    'ىىى': -20.0,
    '   ': -15.0,  # Triple space
}


class ArabicNGramModel:
    """Arabic n-gram language model for OCR scoring."""

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize n-gram model.

        Args:
            model_path: Path to custom n-gram JSON file
        """
        self.trigrams = dict(COMMON_TRIGRAMS)
        self.invalid = dict(INVALID_TRIGRAMS)
        self.default_score = -10.0  # Score for unknown trigrams

        if model_path:
            self._load_model(model_path)

    def _load_model(self, path: str) -> None:
        """Load n-gram model from JSON file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.trigrams.update(data.get('trigrams', {}))
                self.invalid.update(data.get('invalid', {}))
        except Exception as e:
            print(f"Warning: Could not load n-gram model: {e}")

    def score_trigram(self, trigram: str) -> float:
        """
        Score a single trigram.

        Args:
            trigram: 3-character string

        Returns:
            Log probability score
        """
        if len(trigram) != 3:
            return self.default_score

        # Check invalid patterns first
        if trigram in self.invalid:
            return self.invalid[trigram]

        # Return known score or default
        return self.trigrams.get(trigram, self.default_score)

    def score_word(self, word: str) -> float:
        """
        Score a word using trigram probabilities.

        Args:
            word: Arabic word to score

        Returns:
            Sum of log probabilities (higher is better)
        """
        if len(word) < 3:
            return 0.0

        # Add word boundary markers
        padded = f" {word} "

        total_score = 0.0
        for i in range(len(padded) - 2):
            trigram = padded[i:i+3]
            total_score += self.score_trigram(trigram)

        # Normalize by length
        return total_score / max(1, len(word))

    def score_text(self, text: str) -> float:
        """
        Score full text using n-gram model.

        Args:
            text: Arabic text to score

        Returns:
            Average normalized score
        """
        words = text.split()
        if not words:
            return 0.0

        scores = [self.score_word(w) for w in words]
        return sum(scores) / len(scores)

    def get_word_perplexity(self, word: str) -> float:
        """
        Calculate perplexity of a word.

        Lower perplexity = more likely to be valid Arabic.

        Args:
            word: Arabic word

        Returns:
            Perplexity score
        """
        score = self.score_word(word)
        # Convert log probability to perplexity
        return math.exp(-score)

    def is_valid_arabic(self, word: str, threshold: float = -8.0) -> bool:
        """
        Check if word appears to be valid Arabic.

        Args:
            word: Word to check
            threshold: Minimum score threshold

        Returns:
            True if word scores above threshold
        """
        return self.score_word(word) > threshold
```

---

## 4. Phase 2: Core Processing

**Duration:** 4-5 days
**Dependencies:** Phase 1 (ConfusionMatrix, NGramModel)
**Deliverables:** 3 new files, ~750 lines

### 4.1 Arabic Beam Corrector

**File:** `src/ml/arabic_beam_corrector.py`

```python
"""
Arabic Beam Search Corrector

Uses confusion matrix and n-gram scoring to find optimal corrections
for OCR output using beam search algorithm.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import heapq

from ..utils.arabic_confusion_matrix import ArabicConfusionMatrix, CharPosition
from .arabic_ngram_model import ArabicNGramModel


@dataclass
class BeamPath:
    """Single path in beam search."""
    text: str
    score: float
    corrections: List[Tuple[int, str, str]] = field(default_factory=list)

    def __lt__(self, other):
        return self.score > other.score  # Higher score = better


@dataclass
class CorrectionResult:
    """Result of beam search correction."""
    original: str
    corrected: str
    confidence: float
    corrections: List[Tuple[int, str, str]]  # (position, from_char, to_char)
    alternatives: List[Tuple[str, float]]


class ArabicBeamCorrector:
    """
    Beam search corrector for Arabic OCR output.

    Algorithm:
    1. Start with original text as initial beam
    2. For each character position:
       - Generate candidates using confusion matrix
       - Score each candidate using n-gram model
       - Keep top-k candidates (beam width)
    3. Return best scoring path
    """

    def __init__(
        self,
        beam_width: int = 5,
        max_corrections_per_word: int = 3,
        min_confidence: float = 0.5,
        confusion_matrix: ArabicConfusionMatrix = None,
        ngram_model: ArabicNGramModel = None
    ):
        self.beam_width = beam_width
        self.max_corrections = max_corrections_per_word
        self.min_confidence = min_confidence
        self.confusion = confusion_matrix or ArabicConfusionMatrix()
        self.ngram = ngram_model or ArabicNGramModel()

    def correct_text(self, text: str) -> CorrectionResult:
        """
        Correct full text using beam search.

        Args:
            text: OCR output text

        Returns:
            CorrectionResult with best correction
        """
        words = text.split()
        corrected_words = []
        all_corrections = []

        for word_idx, word in enumerate(words):
            result = self._correct_word(word, word_idx)
            corrected_words.append(result.corrected)
            all_corrections.extend(result.corrections)

        corrected_text = ' '.join(corrected_words)

        # Calculate overall confidence
        if text == corrected_text:
            confidence = 1.0
        else:
            original_score = self.ngram.score_text(text)
            corrected_score = self.ngram.score_text(corrected_text)
            improvement = corrected_score - original_score
            confidence = min(1.0, max(0.0, 0.5 + improvement * 0.1))

        return CorrectionResult(
            original=text,
            corrected=corrected_text,
            confidence=confidence,
            corrections=all_corrections,
            alternatives=[]
        )

    def _correct_word(self, word: str, word_index: int) -> CorrectionResult:
        """Correct single word using beam search."""
        if len(word) < 2:
            return CorrectionResult(word, word, 1.0, [], [])

        # Initialize beam with original word
        initial_path = BeamPath(word, self.ngram.score_word(word), [])
        beam = [initial_path]

        # Iterate through character positions
        for pos in range(len(word)):
            char = word[pos]
            position = self._get_char_position(word, pos)

            new_beam = []

            for path in beam:
                # Keep current character
                new_beam.append(path)

                # Try substitutions if under correction limit
                if len(path.corrections) < self.max_corrections:
                    candidates = self.confusion.get_candidates(char, position)

                    for candidate_char, prob in candidates:
                        # Create new path with substitution
                        new_text = path.text[:pos] + candidate_char + path.text[pos+1:]
                        new_score = self.ngram.score_word(new_text)
                        new_corrections = path.corrections + [(pos, char, candidate_char)]

                        new_path = BeamPath(new_text, new_score, new_corrections)
                        new_beam.append(new_path)

            # Keep top-k paths
            beam = heapq.nsmallest(self.beam_width, new_beam)

        # Get best path
        best = beam[0]

        # Get alternatives
        alternatives = [(p.text, p.score) for p in beam[1:4]]

        return CorrectionResult(
            original=word,
            corrected=best.text,
            confidence=self._calculate_confidence(word, best),
            corrections=[(word_index * 100 + c[0], c[1], c[2]) for c in best.corrections],
            alternatives=alternatives
        )

    def _get_char_position(self, word: str, pos: int) -> CharPosition:
        """Determine character position in word."""
        if len(word) == 1:
            return CharPosition.ISOLATED
        elif pos == 0:
            return CharPosition.INITIAL
        elif pos == len(word) - 1:
            return CharPosition.FINAL
        else:
            return CharPosition.MEDIAL

    def _calculate_confidence(self, original: str, path: BeamPath) -> float:
        """Calculate confidence score for correction."""
        if original == path.text:
            return 1.0

        original_score = self.ngram.score_word(original)
        improvement = path.score - original_score

        # Base confidence on score improvement
        confidence = min(1.0, max(0.0, 0.5 + improvement * 0.2))

        # Penalize many corrections
        correction_penalty = 0.05 * len(path.corrections)
        confidence = max(0.0, confidence - correction_penalty)

        return confidence
```

### 4.2 Arabic Morphological Analyzer

**File:** `src/utils/arabic_morphology.py`

```python
"""
Arabic Morphological Analyzer

Analyzes Arabic words to extract root, pattern, and affixes.
Used for OCR validation and correction suggestions.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import re


@dataclass
class MorphologicalAnalysis:
    """Result of morphological analysis."""
    word: str
    root: str
    pattern: str
    prefix: str
    suffix: str
    stem: str
    confidence: float


# Common Arabic verb patterns (أوزان)
ARABIC_PATTERNS = [
    ('فعل', 3),      # fa'ala - basic trilateral
    ('فعّل', 3),     # fa''ala - intensive
    ('فاعل', 3),     # faa'ala - reciprocal
    ('أفعل', 3),     # af'ala - causative
    ('تفعّل', 3),    # tafa''ala - reflexive intensive
    ('تفاعل', 3),    # tafaa'ala - reciprocal reflexive
    ('انفعل', 3),    # infa'ala - passive
    ('افتعل', 3),    # ifta'ala - reflexive
    ('افعلّ', 3),    # if'alla - colors/defects
    ('استفعل', 3),   # istaf'ala - requestative
    ('فعلل', 4),     # fa'lala - quadrilateral
    ('تفعلل', 4),    # tafa'lala - quadrilateral reflexive
]

# Common prefixes
COMMON_PREFIXES = [
    ('وال', 'و', 'ال'),  # wa + al
    ('بال', 'ب', 'ال'),  # bi + al
    ('كال', 'ك', 'ال'),  # ka + al
    ('فال', 'ف', 'ال'),  # fa + al
    ('لل', 'ل', 'ال'),   # li + al
    ('ال', '', 'ال'),    # al
    ('و', 'و', ''),      # wa
    ('ب', 'ب', ''),      # bi
    ('ك', 'ك', ''),      # ka
    ('ف', 'ف', ''),      # fa
    ('ل', 'ل', ''),      # li
    ('س', 'س', ''),      # sa (future)
]

# Common suffixes
COMMON_SUFFIXES = [
    ('ات', 'ات'),     # feminine plural
    ('ون', 'ون'),     # masculine plural (nominative)
    ('ين', 'ين'),     # masculine plural (acc/gen)
    ('ان', 'ان'),     # dual nominative
    ('ية', 'ية'),     # nisba adjective
    ('ة', 'ة'),       # ta marbuta
    ('ه', 'ه'),       # possessive his
    ('ها', 'ها'),     # possessive her
    ('هم', 'هم'),     # possessive their
    ('هن', 'هن'),     # possessive their (f)
    ('نا', 'نا'),     # possessive our
    ('ي', 'ي'),       # possessive my
    ('ك', 'ك'),       # possessive your
]


class ArabicMorphologicalAnalyzer:
    """Arabic morphological analyzer for OCR validation."""

    def __init__(self):
        self.patterns = ARABIC_PATTERNS
        self.prefixes = sorted(COMMON_PREFIXES, key=lambda x: -len(x[0]))
        self.suffixes = sorted(COMMON_SUFFIXES, key=lambda x: -len(x[0]))

    def analyze(self, word: str) -> MorphologicalAnalysis:
        """
        Analyze Arabic word morphology.

        Args:
            word: Arabic word to analyze

        Returns:
            MorphologicalAnalysis with extracted components
        """
        # Strip prefixes
        prefix, remainder = self._strip_prefix(word)

        # Strip suffixes
        suffix, stem = self._strip_suffix(remainder)

        # Extract root and pattern
        root, pattern, confidence = self._extract_root(stem)

        return MorphologicalAnalysis(
            word=word,
            root=root,
            pattern=pattern,
            prefix=prefix,
            suffix=suffix,
            stem=stem,
            confidence=confidence
        )

    def _strip_prefix(self, word: str) -> Tuple[str, str]:
        """Remove prefix from word."""
        for prefix_chars, conj, article in self.prefixes:
            if word.startswith(prefix_chars) and len(word) > len(prefix_chars) + 2:
                return prefix_chars, word[len(prefix_chars):]
        return '', word

    def _strip_suffix(self, word: str) -> Tuple[str, str]:
        """Remove suffix from word."""
        for suffix_chars, _ in self.suffixes:
            if word.endswith(suffix_chars) and len(word) > len(suffix_chars) + 2:
                return suffix_chars, word[:-len(suffix_chars)]
        return '', word

    def _extract_root(self, stem: str) -> Tuple[str, str, float]:
        """
        Extract trilateral/quadrilateral root from stem.

        Uses pattern matching to identify root consonants.
        """
        # Remove weak letters and diacritics
        consonants = self._get_consonants(stem)

        if len(consonants) == 3:
            # Trilateral root
            return consonants, 'فعل', 0.8
        elif len(consonants) == 4:
            # Quadrilateral root
            return consonants, 'فعلل', 0.7
        elif len(consonants) > 4:
            # Try to reduce to trilateral
            root = self._reduce_to_trilateral(consonants)
            return root, 'فعل', 0.5
        else:
            # Too short, return as-is
            return stem, '', 0.3

    def _get_consonants(self, text: str) -> str:
        """Extract consonants from Arabic text."""
        weak_letters = 'اوي'  # Alef, Waw, Yaa (weak)
        vowels = '\u064B\u064C\u064D\u064E\u064F\u0650\u0651\u0652'  # Diacritics

        result = []
        for char in text:
            if char not in weak_letters and char not in vowels:
                result.append(char)
        return ''.join(result)

    def _reduce_to_trilateral(self, consonants: str) -> str:
        """Reduce consonant sequence to likely trilateral root."""
        # Common patterns for augmented verbs
        # Remove common augmentation consonants
        augmentation = 'تنام'  # Common prefix/infix consonants

        result = []
        for char in consonants:
            if char not in augmentation or len(result) < 3:
                result.append(char)
            if len(result) == 3:
                break

        return ''.join(result[:3]) if len(result) >= 3 else ''.join(result)

    def reconstruct_word(
        self,
        root: str,
        pattern: str,
        prefix: str = '',
        suffix: str = ''
    ) -> str:
        """Reconstruct word from morphological components."""
        # Basic reconstruction (simplified)
        return prefix + root + suffix

    def is_valid_root(self, root: str) -> bool:
        """Check if root follows Arabic phonological rules."""
        if len(root) < 3:
            return False

        # Check for invalid consonant clusters
        invalid_pairs = [
            ('ء', 'ء'),  # Double hamza
            ('ق', 'ك'),  # Qaf-Kaf
        ]

        for i in range(len(root) - 1):
            pair = (root[i], root[i+1])
            if pair in invalid_pairs:
                return False

        return True
```

### 4.3 Arabic BPE Tokenizer

**File:** `src/ml/arabic_bpe_tokenizer.py`

```python
"""
Arabic BPE (Byte Pair Encoding) Tokenizer

Subword tokenization for Arabic text, useful for:
- Identifying OCR errors in unknown words
- Suggesting corrections based on valid subword units
"""

import json
import pickle
from pathlib import Path
from typing import List, Dict, Optional, Tuple


class ArabicBPETokenizer:
    """
    BPE tokenizer for Arabic OCR validation.

    Uses pre-trained vocabulary to segment Arabic words
    into subword units. Unknown segments may indicate OCR errors.
    """

    def __init__(self, vocab_path: Optional[str] = None):
        """
        Initialize tokenizer.

        Args:
            vocab_path: Path to vocabulary file (.json or .pkl)
        """
        self.vocab: Dict[str, int] = {}
        self.merges: List[Tuple[str, str]] = []
        self.special_tokens = ['[UNK]', '[PAD]', '[CLS]', '[SEP]']

        if vocab_path:
            self._load_vocab(vocab_path)
        else:
            self._initialize_default_vocab()

    def _initialize_default_vocab(self):
        """Initialize with basic Arabic character vocabulary."""
        # Arabic letters
        arabic_chars = 'ابتثجحخدذرزسشصضطظعغفقكلمنهويءآأإؤئة'

        for i, char in enumerate(arabic_chars):
            self.vocab[char] = i

        # Common subword units
        common_units = [
            'ال', 'ون', 'ين', 'ات', 'ية',
            'من', 'في', 'على', 'إلى', 'هذا',
            'كان', 'قال', 'بين', 'حتى', 'أنه',
        ]

        for unit in common_units:
            if unit not in self.vocab:
                self.vocab[unit] = len(self.vocab)

    def _load_vocab(self, path: str) -> None:
        """Load vocabulary from file."""
        path = Path(path)

        try:
            if path.suffix == '.pkl':
                with open(path, 'rb') as f:
                    data = pickle.load(f)
            else:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            self.vocab = data.get('vocab', {})
            self.merges = data.get('merges', [])
        except Exception as e:
            print(f"Warning: Could not load vocab: {e}")
            self._initialize_default_vocab()

    def tokenize(self, word: str) -> List[str]:
        """
        Tokenize word into subword units.

        Args:
            word: Arabic word

        Returns:
            List of subword tokens
        """
        if not word:
            return []

        # Start with character-level tokens
        tokens = list(word)

        # Apply BPE merges
        for merge_a, merge_b in self.merges:
            i = 0
            while i < len(tokens) - 1:
                if tokens[i] == merge_a and tokens[i+1] == merge_b:
                    tokens = tokens[:i] + [merge_a + merge_b] + tokens[i+2:]
                else:
                    i += 1

        return tokens

    def reconstruct(self, tokens: List[str]) -> str:
        """Reconstruct word from tokens."""
        return ''.join(tokens)

    def is_valid_tokenization(self, tokens: List[str]) -> bool:
        """
        Check if all tokens are in vocabulary.

        Returns False if any token is unknown (potential OCR error).
        """
        for token in tokens:
            if token not in self.vocab:
                return False
        return True

    def get_unknown_segments(self, word: str) -> List[str]:
        """
        Get segments that are not in vocabulary.

        These may indicate OCR errors.
        """
        tokens = self.tokenize(word)
        unknown = []

        for token in tokens:
            if token not in self.vocab:
                unknown.append(token)

        return unknown

    def suggest_corrections(self, word: str) -> List[str]:
        """
        Suggest corrections for word with unknown segments.

        Uses edit distance to find similar known tokens.
        """
        unknown = self.get_unknown_segments(word)

        if not unknown:
            return [word]

        suggestions = []

        for unk_token in unknown:
            # Find similar tokens in vocab
            similar = self._find_similar_tokens(unk_token)

            for sim_token in similar[:3]:
                # Replace unknown with similar
                suggestion = word.replace(unk_token, sim_token)
                if suggestion not in suggestions:
                    suggestions.append(suggestion)

        return suggestions[:5]

    def _find_similar_tokens(self, token: str, max_distance: int = 2) -> List[str]:
        """Find vocabulary tokens similar to given token."""
        similar = []

        for vocab_token in self.vocab:
            if abs(len(vocab_token) - len(token)) <= max_distance:
                dist = self._edit_distance(token, vocab_token)
                if dist <= max_distance:
                    similar.append((vocab_token, dist))

        similar.sort(key=lambda x: x[1])
        return [t for t, _ in similar]

    def _edit_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein edit distance."""
        if len(s1) < len(s2):
            return self._edit_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        prev_row = range(len(s2) + 1)

        for i, c1 in enumerate(s1):
            curr_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = prev_row[j + 1] + 1
                deletions = curr_row[j] + 1
                substitutions = prev_row[j] + (c1 != c2)
                curr_row.append(min(insertions, deletions, substitutions))
            prev_row = curr_row

        return prev_row[-1]
```

---

## 5. Phase 3: Multi-Engine Fusion

**Duration:** 3-4 days
**Dependencies:** Phase 2 (BeamCorrector)
**Deliverables:** 1 new file, ~250 lines

### 5.1 Enhanced OCR Fusion Engine

**File:** `src/engines/fusion_ocr_engine.py`

```python
"""
Enhanced OCR Fusion Engine

Multi-engine OCR fusion with:
- Character-level voting
- Weighted engine confidence
- VLM fallback for low-confidence regions
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class FusionStrategy(Enum):
    WEIGHTED_VOTE = "weighted_vote"
    CHARACTER_VOTE = "character_vote"
    CONFIDENCE_SELECT = "confidence_select"
    CASCADE = "cascade"


@dataclass
class WordResult:
    """Single word OCR result."""
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    engine: str


@dataclass
class FusedWord:
    """Result of fusing multiple word results."""
    text: str
    confidence: float
    source_engine: str
    alternatives: List[Tuple[str, float]] = field(default_factory=list)
    fusion_method: str = ""


@dataclass
class FusionResult:
    """Complete fusion result."""
    text: str
    confidence: float
    words: List[FusedWord]
    engines_used: List[str]
    fusion_strategy: FusionStrategy


class OCRFusionEngine:
    """
    Multi-engine OCR fusion.

    Implements the 8-step fusion algorithm from ARABIC_OCR_ULTIMATE_ENHANCEMENT.md:
    1. Detect script via Unicode
    2. Select primary engine
    3. Run primary engine
    4. Check confidence threshold
    5. Run secondary engine if needed
    6. Align results by bounding box (IoU > 0.5)
    7. Character-level voting with weights
    8. VLM fallback if confidence < 0.40
    """

    # Engine weights based on empirical accuracy
    ENGINE_WEIGHTS = {
        'paddle': 1.0,      # PP-OCRv5 - strong Arabic
        'easyocr': 0.8,     # Good Arabic, slower
        'qari': 1.2,        # Best for printed Arabic
        'tesseract': 0.6,   # Fallback
    }

    # Confidence thresholds
    HIGH_CONFIDENCE = 0.85
    LOW_CONFIDENCE = 0.50
    VLM_TRIGGER = 0.40
    IOU_THRESHOLD = 0.5

    def __init__(
        self,
        engine_weights: Dict[str, float] = None,
        iou_threshold: float = 0.5,
        vlm_engine = None
    ):
        self.weights = engine_weights or self.ENGINE_WEIGHTS
        self.iou_threshold = iou_threshold
        self.vlm_engine = vlm_engine

    def fuse(
        self,
        results: List[Dict],
        strategy: FusionStrategy = FusionStrategy.CHARACTER_VOTE
    ) -> FusionResult:
        """
        Fuse multiple OCR results.

        Args:
            results: List of OCR results from different engines
                    Each result: {'words': List[WordResult], 'engine': str}
            strategy: Fusion strategy to use

        Returns:
            FusionResult with fused text and confidence
        """
        if not results:
            return FusionResult("", 0.0, [], [], strategy)

        if len(results) == 1:
            # Single engine, no fusion needed
            return self._single_result(results[0], strategy)

        # Align words by bounding box
        aligned_groups = self._align_results(results)

        # Fuse each word group
        fused_words = []
        for group in aligned_groups:
            if strategy == FusionStrategy.CHARACTER_VOTE:
                fused = self._character_vote(group)
            elif strategy == FusionStrategy.WEIGHTED_VOTE:
                fused = self._weighted_select(group)
            else:
                fused = self._confidence_select(group)

            fused_words.append(fused)

        # Check if VLM fallback needed
        low_conf_words = [w for w in fused_words if w.confidence < self.VLM_TRIGGER]
        if low_conf_words and self.vlm_engine:
            fused_words = self._vlm_fallback(fused_words, low_conf_words)

        # Build final result
        text = ' '.join(w.text for w in fused_words)
        avg_conf = sum(w.confidence for w in fused_words) / max(1, len(fused_words))
        engines = list(set(r['engine'] for r in results))

        return FusionResult(
            text=text,
            confidence=avg_conf,
            words=fused_words,
            engines_used=engines,
            fusion_strategy=strategy
        )

    def _align_results(self, results: List[Dict]) -> List[List[WordResult]]:
        """
        Align word results by bounding box overlap.

        Uses IoU (Intersection over Union) to match words.
        """
        # Flatten all words with engine info
        all_words = []
        for result in results:
            engine = result['engine']
            for word in result.get('words', []):
                if isinstance(word, dict):
                    word = WordResult(**word, engine=engine)
                all_words.append(word)

        if not all_words:
            return []

        # Group by IoU overlap
        groups = []
        used = set()

        for i, word in enumerate(all_words):
            if i in used:
                continue

            group = [word]
            used.add(i)

            for j, other in enumerate(all_words):
                if j in used:
                    continue

                iou = self._calculate_iou(word.bbox, other.bbox)
                if iou >= self.iou_threshold:
                    group.append(other)
                    used.add(j)

            groups.append(group)

        return groups

    def _calculate_iou(
        self,
        bbox1: Tuple[int, int, int, int],
        bbox2: Tuple[int, int, int, int]
    ) -> float:
        """Calculate Intersection over Union of two bounding boxes."""
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])

        if x2 <= x1 or y2 <= y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0

    def _character_vote(self, group: List[WordResult]) -> FusedWord:
        """
        Fuse words using character-level voting.

        Each character position votes based on engine weight.
        """
        if len(group) == 1:
            return FusedWord(
                text=group[0].text,
                confidence=group[0].confidence,
                source_engine=group[0].engine,
                fusion_method="single"
            )

        # Find max length
        max_len = max(len(w.text) for w in group)

        # Vote for each position
        fused_chars = []
        for pos in range(max_len):
            votes = {}

            for word in group:
                if pos < len(word.text):
                    char = word.text[pos]
                    weight = self.weights.get(word.engine, 0.5)
                    votes[char] = votes.get(char, 0) + weight * word.confidence

            if votes:
                best_char = max(votes, key=votes.get)
                fused_chars.append(best_char)

        fused_text = ''.join(fused_chars)

        # Calculate fused confidence
        total_weight = sum(
            self.weights.get(w.engine, 0.5) * w.confidence
            for w in group
        )
        avg_conf = total_weight / len(group)

        # Get alternatives
        alternatives = [
            (w.text, w.confidence)
            for w in sorted(group, key=lambda x: -x.confidence)
            if w.text != fused_text
        ][:3]

        return FusedWord(
            text=fused_text,
            confidence=min(1.0, avg_conf),
            source_engine="fusion",
            alternatives=alternatives,
            fusion_method="character_vote"
        )

    def _weighted_select(self, group: List[WordResult]) -> FusedWord:
        """Select word with highest weighted confidence."""
        best = max(
            group,
            key=lambda w: self.weights.get(w.engine, 0.5) * w.confidence
        )

        return FusedWord(
            text=best.text,
            confidence=best.confidence,
            source_engine=best.engine,
            alternatives=[(w.text, w.confidence) for w in group if w != best][:3],
            fusion_method="weighted_select"
        )

    def _confidence_select(self, group: List[WordResult]) -> FusedWord:
        """Select word with highest raw confidence."""
        best = max(group, key=lambda w: w.confidence)

        return FusedWord(
            text=best.text,
            confidence=best.confidence,
            source_engine=best.engine,
            alternatives=[(w.text, w.confidence) for w in group if w != best][:3],
            fusion_method="confidence_select"
        )

    def _vlm_fallback(
        self,
        fused_words: List[FusedWord],
        low_conf_words: List[FusedWord]
    ) -> List[FusedWord]:
        """Use VLM for low-confidence words."""
        if not self.vlm_engine:
            return fused_words

        logger.info(f"VLM fallback for {len(low_conf_words)} low-confidence words")

        # VLM integration would go here
        # For now, return as-is
        return fused_words

    def _single_result(
        self,
        result: Dict,
        strategy: FusionStrategy
    ) -> FusionResult:
        """Convert single engine result to FusionResult."""
        words = []
        for word in result.get('words', []):
            if isinstance(word, dict):
                words.append(FusedWord(
                    text=word.get('text', ''),
                    confidence=word.get('confidence', 0.5),
                    source_engine=result['engine'],
                    fusion_method="single"
                ))
            else:
                words.append(FusedWord(
                    text=word.text,
                    confidence=word.confidence,
                    source_engine=word.engine,
                    fusion_method="single"
                ))

        text = ' '.join(w.text for w in words)
        avg_conf = sum(w.confidence for w in words) / max(1, len(words))

        return FusionResult(
            text=text,
            confidence=avg_conf,
            words=words,
            engines_used=[result['engine']],
            fusion_strategy=strategy
        )
```

---

## 6. Phase 4: Language Processing

**Duration:** 3-4 days
**Dependencies:** None (can run parallel to Phase 2-3)
**Deliverables:** 3 new files, ~550 lines

### 6.1 Word-Level Language Detector

**File:** `src/utils/word_level_detector.py`

```python
"""
Word-Level Language Detector

Detects language at word level for bilingual Arabic-English documents.
Handles code-switching and mixed-language content.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple
import re


class LanguageTag(Enum):
    ARABIC = "ar"
    ENGLISH = "en"
    MIXED = "mixed"
    NUMERIC = "num"
    PUNCTUATION = "punct"
    UNKNOWN = "unk"


@dataclass
class TaggedWord:
    """Word with language tag."""
    text: str
    language: LanguageTag
    confidence: float
    is_code_switch: bool
    start_pos: int
    end_pos: int


class WordLevelLanguageDetector:
    """
    Detect language at word level.

    Uses Unicode ranges to identify Arabic vs English text.
    Handles mixed content and code-switching points.
    """

    # Unicode ranges
    ARABIC_RANGE = (0x0600, 0x06FF)      # Basic Arabic
    ARABIC_EXT_A = (0x08A0, 0x08FF)      # Arabic Extended-A
    ARABIC_SUPP = (0x0750, 0x077F)       # Arabic Supplement
    ENGLISH_LOWER = (0x0061, 0x007A)     # a-z
    ENGLISH_UPPER = (0x0041, 0x005A)     # A-Z
    DIGITS = (0x0030, 0x0039)            # 0-9
    ARABIC_DIGITS = (0x0660, 0x0669)     # ٠-٩

    def __init__(self):
        pass

    def detect_word_language(self, word: str) -> Tuple[LanguageTag, float]:
        """
        Detect language of a single word.

        Args:
            word: Single word

        Returns:
            (LanguageTag, confidence) tuple
        """
        if not word:
            return LanguageTag.UNKNOWN, 0.0

        arabic_count = 0
        english_count = 0
        digit_count = 0
        other_count = 0

        for char in word:
            code = ord(char)

            if self._in_range(code, self.ARABIC_RANGE) or \
               self._in_range(code, self.ARABIC_EXT_A) or \
               self._in_range(code, self.ARABIC_SUPP):
                arabic_count += 1
            elif self._in_range(code, self.ENGLISH_LOWER) or \
                 self._in_range(code, self.ENGLISH_UPPER):
                english_count += 1
            elif self._in_range(code, self.DIGITS) or \
                 self._in_range(code, self.ARABIC_DIGITS):
                digit_count += 1
            else:
                other_count += 1

        total = len(word)

        # Pure digit
        if digit_count == total:
            return LanguageTag.NUMERIC, 1.0

        # Pure punctuation/other
        if other_count == total:
            return LanguageTag.PUNCTUATION, 1.0

        # Calculate ratios (excluding digits and punctuation)
        text_chars = arabic_count + english_count
        if text_chars == 0:
            return LanguageTag.NUMERIC if digit_count > 0 else LanguageTag.UNKNOWN, 0.5

        arabic_ratio = arabic_count / text_chars
        english_ratio = english_count / text_chars

        # Determine language
        if arabic_ratio > 0.8:
            return LanguageTag.ARABIC, arabic_ratio
        elif english_ratio > 0.8:
            return LanguageTag.ENGLISH, english_ratio
        elif arabic_ratio > 0 and english_ratio > 0:
            return LanguageTag.MIXED, max(arabic_ratio, english_ratio)
        elif arabic_ratio > english_ratio:
            return LanguageTag.ARABIC, arabic_ratio
        else:
            return LanguageTag.ENGLISH, english_ratio

    def _in_range(self, code: int, range_tuple: Tuple[int, int]) -> bool:
        """Check if code point is in range."""
        return range_tuple[0] <= code <= range_tuple[1]

    def tag_text(self, text: str) -> List[TaggedWord]:
        """
        Tag all words in text with language.

        Args:
            text: Full text to tag

        Returns:
            List of TaggedWord objects
        """
        words = self._tokenize(text)
        tagged = []
        prev_lang = None

        for word, start, end in words:
            lang, conf = self.detect_word_language(word)

            # Check for code switch
            is_switch = (
                prev_lang is not None and
                lang != prev_lang and
                lang not in (LanguageTag.NUMERIC, LanguageTag.PUNCTUATION, LanguageTag.UNKNOWN) and
                prev_lang not in (LanguageTag.NUMERIC, LanguageTag.PUNCTUATION, LanguageTag.UNKNOWN)
            )

            tagged.append(TaggedWord(
                text=word,
                language=lang,
                confidence=conf,
                is_code_switch=is_switch,
                start_pos=start,
                end_pos=end
            ))

            if lang not in (LanguageTag.NUMERIC, LanguageTag.PUNCTUATION, LanguageTag.UNKNOWN):
                prev_lang = lang

        return tagged

    def _tokenize(self, text: str) -> List[Tuple[str, int, int]]:
        """Tokenize text into words with positions."""
        words = []
        pattern = r'\S+'

        for match in re.finditer(pattern, text):
            words.append((match.group(), match.start(), match.end()))

        return words

    def find_code_switch_points(self, tagged_words: List[TaggedWord]) -> List[int]:
        """Find positions where language switches."""
        return [i for i, w in enumerate(tagged_words) if w.is_code_switch]

    def get_language_segments(
        self,
        tagged_words: List[TaggedWord]
    ) -> List[Tuple[LanguageTag, List[TaggedWord]]]:
        """
        Group consecutive words by language.

        Returns list of (language, words) segments.
        """
        if not tagged_words:
            return []

        segments = []
        current_lang = tagged_words[0].language
        current_words = [tagged_words[0]]

        for word in tagged_words[1:]:
            if word.language == current_lang or \
               word.language in (LanguageTag.NUMERIC, LanguageTag.PUNCTUATION):
                current_words.append(word)
            else:
                segments.append((current_lang, current_words))
                current_lang = word.language
                current_words = [word]

        if current_words:
            segments.append((current_lang, current_words))

        return segments

    def get_dominant_language(self, text: str) -> Tuple[LanguageTag, float]:
        """Get dominant language of text."""
        tagged = self.tag_text(text)

        arabic = sum(1 for w in tagged if w.language == LanguageTag.ARABIC)
        english = sum(1 for w in tagged if w.language == LanguageTag.ENGLISH)
        total = arabic + english

        if total == 0:
            return LanguageTag.UNKNOWN, 0.0

        if arabic > english:
            return LanguageTag.ARABIC, arabic / total
        else:
            return LanguageTag.ENGLISH, english / total
```

### 6.2 Arabizi Transliterator

**File:** `src/utils/arabizi_transliterator.py`

```python
"""
Arabizi Transliterator

Converts Arabizi (Arabic written in Latin script) to Arabic.
Common in informal digital communication.
"""

from typing import Dict, List, Tuple
import re


class ArabiziTransliterator:
    """
    Transliterate Arabizi to Arabic script.

    Arabizi is informal romanization of Arabic using:
    - Numbers for Arabic letters without Latin equivalents
    - Latin letters for similar-sounding Arabic letters
    """

    # Arabizi to Arabic mapping
    ARABIZI_MAP: Dict[str, str] = {
        # Numbers representing Arabic letters
        '2': 'ء',     # Hamza
        '3': 'ع',     # Ain
        "3'": 'غ',    # Ghain
        '5': 'خ',     # Kha
        '6': 'ط',     # Taa (emphatic)
        '7': 'ح',     # Haa
        '8': 'ق',     # Qaf (some dialects)
        '9': 'ص',     # Sad
        "9'": 'ض',    # Dad

        # Letter mappings (lowercase)
        'a': 'ا',
        'b': 'ب',
        't': 'ت',
        'th': 'ث',
        'j': 'ج',
        'g': 'ج',     # Gulf dialects
        'ch': 'ش',    # Some dialects
        'd': 'د',
        'dh': 'ذ',
        'r': 'ر',
        'z': 'ز',
        's': 'س',
        'sh': 'ش',
        'f': 'ف',
        'q': 'ق',
        'k': 'ك',
        'l': 'ل',
        'm': 'م',
        'n': 'ن',
        'h': 'ه',
        'w': 'و',
        'u': 'و',
        'oo': 'و',
        'y': 'ي',
        'i': 'ي',
        'ee': 'ي',
        'e': 'ي',     # Sometimes
        'o': 'و',     # Sometimes
    }

    # Multi-char patterns (process first)
    MULTI_PATTERNS = [
        ("3'", 'غ'),
        ("9'", 'ض'),
        ('th', 'ث'),
        ('dh', 'ذ'),
        ('sh', 'ش'),
        ('ch', 'ش'),
        ('oo', 'و'),
        ('ee', 'ي'),
    ]

    def __init__(self):
        pass

    def transliterate(self, text: str) -> str:
        """
        Transliterate Arabizi text to Arabic.

        Args:
            text: Arabizi text

        Returns:
            Arabic transliteration
        """
        result = text.lower()

        # Process multi-character patterns first
        for pattern, replacement in self.MULTI_PATTERNS:
            result = result.replace(pattern, replacement)

        # Process single characters
        output = []
        i = 0
        while i < len(result):
            char = result[i]

            if char in self.ARABIZI_MAP:
                output.append(self.ARABIZI_MAP[char])
            elif char.isspace() or char in '.,!?;:-':
                output.append(char)
            else:
                # Keep unknown characters as-is
                output.append(char)

            i += 1

        return ''.join(output)

    def is_arabizi(self, text: str) -> bool:
        """
        Check if text appears to be Arabizi.

        Looks for characteristic patterns like numbers 2,3,5,7,9
        used as letters.
        """
        # Check for Arabizi number patterns
        arabizi_numbers = r'[23579]'

        # Count Arabizi-like patterns
        arabizi_count = len(re.findall(arabizi_numbers, text))

        # Must have some numbers and be mostly Latin
        latin_count = len(re.findall(r'[a-zA-Z]', text))

        if latin_count < 3:
            return False

        # Ratio of Arabizi numbers to total length
        ratio = arabizi_count / len(text) if text else 0

        # Arabizi typically has 5-30% number usage
        return 0.05 < ratio < 0.3 and arabizi_count >= 1

    def get_confidence(self, text: str) -> float:
        """
        Get confidence that text is Arabizi.

        Returns:
            0.0-1.0 confidence score
        """
        if not text:
            return 0.0

        arabizi_chars = sum(1 for c in text if c in '235679')
        latin_chars = sum(1 for c in text if c.isalpha())

        if latin_chars < 3:
            return 0.0

        # Score based on Arabizi pattern presence
        score = 0.0

        # Has characteristic numbers
        if arabizi_chars > 0:
            score += 0.3

        # Ratio is in expected range
        ratio = arabizi_chars / len(text)
        if 0.05 < ratio < 0.3:
            score += 0.3

        # Contains common Arabizi patterns
        common_patterns = ['3', '7', '5', 'sh', 'kh', 'th']
        pattern_count = sum(1 for p in common_patterns if p in text.lower())
        score += min(0.4, pattern_count * 0.1)

        return min(1.0, score)
```

### 6.3 Bidirectional Text Handler

**File:** `src/utils/bidirectional_text.py`

```python
"""
Bidirectional Text Handler

Handles Unicode Bidirectional Algorithm for mixed RTL/LTR text.
Essential for correct rendering of Arabic-English mixed content.
"""

from enum import Enum
from typing import List, Tuple


class BidiClass(Enum):
    """Unicode Bidirectional Character Types."""
    L = "left_to_right"           # Latin letters
    R = "right_to_left"           # Hebrew letters
    AL = "arabic_letter"          # Arabic letters
    EN = "european_number"        # 0-9
    AN = "arabic_number"          # ٠-٩
    ES = "european_separator"     # + -
    ET = "european_terminator"    # # $ %
    CS = "common_separator"       # , . :
    NSM = "nonspacing_mark"       # Diacritics
    BN = "boundary_neutral"       # Format controls
    WS = "whitespace"             # Spaces
    ON = "other_neutral"          # Other punctuation


def get_bidi_class(char: str) -> BidiClass:
    """
    Get bidirectional class for a character.

    Simplified implementation covering main cases.
    """
    code = ord(char)

    # Arabic letters
    if 0x0600 <= code <= 0x06FF or \
       0x0750 <= code <= 0x077F or \
       0x08A0 <= code <= 0x08FF:
        return BidiClass.AL

    # Arabic-Indic digits
    if 0x0660 <= code <= 0x0669:
        return BidiClass.AN

    # Latin letters
    if 0x0041 <= code <= 0x005A or 0x0061 <= code <= 0x007A:
        return BidiClass.L

    # European digits
    if 0x0030 <= code <= 0x0039:
        return BidiClass.EN

    # Whitespace
    if char in ' \t\n\r':
        return BidiClass.WS

    # Common separators
    if char in ',.;:':
        return BidiClass.CS

    # European separators
    if char in '+-':
        return BidiClass.ES

    # Default to other neutral
    return BidiClass.ON


def get_base_direction(text: str) -> str:
    """
    Determine base direction of text.

    Returns 'rtl' if first strong character is Arabic/Hebrew,
    'ltr' otherwise.
    """
    for char in text:
        bidi = get_bidi_class(char)
        if bidi in (BidiClass.AL, BidiClass.R):
            return 'rtl'
        elif bidi == BidiClass.L:
            return 'ltr'

    return 'ltr'  # Default


def reorder_bidi_text(text: str, base_direction: str = None) -> str:
    """
    Reorder bidirectional text for display.

    This is a simplified implementation. For production,
    consider using python-bidi library.

    Args:
        text: Mixed direction text
        base_direction: 'rtl' or 'ltr' (auto-detected if None)

    Returns:
        Reordered text for visual display
    """
    if not text:
        return text

    if base_direction is None:
        base_direction = get_base_direction(text)

    # For simple cases, just handle runs
    runs = _get_directional_runs(text)

    if base_direction == 'rtl':
        # Reverse order of runs, reverse RTL runs
        result = []
        for direction, content in reversed(runs):
            if direction == 'rtl':
                result.append(content)
            else:
                result.append(content)
        return ''.join(result)
    else:
        # Keep LTR order, reverse RTL runs
        result = []
        for direction, content in runs:
            if direction == 'rtl':
                result.append(content[::-1])
            else:
                result.append(content)
        return ''.join(result)


def _get_directional_runs(text: str) -> List[Tuple[str, str]]:
    """
    Split text into directional runs.

    Returns list of (direction, content) tuples.
    """
    runs = []
    current_dir = None
    current_text = []

    for char in text:
        bidi = get_bidi_class(char)

        if bidi in (BidiClass.AL, BidiClass.R, BidiClass.AN):
            char_dir = 'rtl'
        elif bidi in (BidiClass.L, BidiClass.EN):
            char_dir = 'ltr'
        else:
            char_dir = current_dir or 'ltr'

        if char_dir != current_dir and current_text:
            runs.append((current_dir, ''.join(current_text)))
            current_text = []

        current_dir = char_dir
        current_text.append(char)

    if current_text:
        runs.append((current_dir, ''.join(current_text)))

    return runs


def wrap_bidi_text(text: str, direction: str = None) -> str:
    """
    Wrap text with Unicode directional controls.

    Args:
        text: Text to wrap
        direction: 'rtl' or 'ltr'

    Returns:
        Text wrapped with appropriate Unicode marks
    """
    if direction is None:
        direction = get_base_direction(text)

    # Unicode directional controls
    RLE = '\u202B'  # Right-to-Left Embedding
    LRE = '\u202A'  # Left-to-Right Embedding
    PDF = '\u202C'  # Pop Directional Formatting

    if direction == 'rtl':
        return f'{RLE}{text}{PDF}'
    else:
        return f'{LRE}{text}{PDF}'
```

---

## 7. Phase 5: Validation & Scoring

**Duration:** 3-4 days
**Dependencies:** Phase 4 (LanguageDetector)
**Deliverables:** 2 files (1 new, 1 modified), ~400 lines

### 7.1 English OCR Validator

**File:** `src/validators/english_validator.py`

```python
"""
English OCR Validator

Validates English OCR output using:
- Confusion matrix for common OCR errors
- Trigram language model scoring
- Dictionary lookup
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Set
import re


# English OCR confusion matrix
ENGLISH_CONFUSION_MATRIX: Dict[str, List[Tuple[str, float]]] = {
    # Number-letter confusions
    '0': [('O', 0.45), ('o', 0.35), ('Q', 0.10)],
    'O': [('0', 0.40), ('Q', 0.20)],
    '1': [('l', 0.40), ('I', 0.35), ('i', 0.15)],
    'l': [('1', 0.35), ('I', 0.30), ('i', 0.20)],
    'I': [('l', 0.35), ('1', 0.30)],
    '5': [('S', 0.35), ('s', 0.25)],
    'S': [('5', 0.30), ('s', 0.25)],
    '8': [('B', 0.30)],
    'B': [('8', 0.25), ('D', 0.15)],

    # Letter confusions
    'rn': [('m', 0.60)],
    'm': [('rn', 0.40), ('nn', 0.20)],
    'vv': [('w', 0.55)],
    'w': [('vv', 0.35)],
    'cl': [('d', 0.45)],
    'd': [('cl', 0.30)],
    'h': [('b', 0.20), ('n', 0.15)],
    'n': [('h', 0.15), ('ri', 0.20)],
    'e': [('c', 0.15)],
    'c': [('e', 0.15), ('o', 0.10)],
    'g': [('q', 0.20), ('9', 0.15)],
    'q': [('g', 0.20), ('9', 0.10)],
}

# Common English trigrams with frequencies
ENGLISH_TRIGRAMS: Dict[str, float] = {
    'the': 0.0356, 'and': 0.0185, 'ing': 0.0172,
    'ion': 0.0142, 'tio': 0.0134, 'ent': 0.0124,
    'ati': 0.0117, 'for': 0.0116, 'her': 0.0112,
    'ter': 0.0111, 'hat': 0.0108, 'tha': 0.0107,
    'ere': 0.0106, 'ate': 0.0103, 'his': 0.0101,
    'con': 0.0098, 'res': 0.0097, 'ver': 0.0096,
    'all': 0.0094, 'ons': 0.0093, 'nce': 0.0092,
    'men': 0.0089, 'ith': 0.0088, 'ted': 0.0087,
}

# Invalid trigrams (strong OCR error indicators)
INVALID_TRIGRAMS: Set[str] = {
    'aaa', 'bbb', 'ccc', 'ddd', 'eee', 'fff', 'ggg',
    'hhh', 'iii', 'jjj', 'kkk', 'lll', 'mmm', 'nnn',
    'ooo', 'ppp', 'qqq', 'rrr', 'sss', 'ttt', 'uuu',
    'vvv', 'www', 'xxx', 'yyy', 'zzz',
    'qx', 'qz', 'xq', 'zq', 'jx', 'jz',
}


@dataclass
class EnglishValidationResult:
    """Result of English OCR validation."""
    word: str
    is_valid: bool
    confidence: float
    suggested_corrections: List[str]
    trigram_score: float
    has_invalid_trigrams: bool


class EnglishOCRValidator:
    """
    Validate English OCR output.

    Uses trigram scoring and confusion matrix to identify
    and correct OCR errors in English text.
    """

    def __init__(
        self,
        confusion_matrix: Dict = None,
        trigrams: Dict = None,
        invalid_trigrams: Set = None
    ):
        self.confusion = confusion_matrix or ENGLISH_CONFUSION_MATRIX
        self.trigrams = trigrams or ENGLISH_TRIGRAMS
        self.invalid = invalid_trigrams or INVALID_TRIGRAMS

    def validate_word(self, word: str) -> EnglishValidationResult:
        """
        Validate single English word.

        Args:
            word: Word to validate

        Returns:
            EnglishValidationResult
        """
        if not word or len(word) < 2:
            return EnglishValidationResult(
                word=word,
                is_valid=True,
                confidence=1.0,
                suggested_corrections=[],
                trigram_score=0.0,
                has_invalid_trigrams=False
            )

        # Calculate trigram score
        trigram_score = self._calculate_trigram_score(word)

        # Check for invalid trigrams
        has_invalid = self._has_invalid_trigrams(word)

        # Determine validity
        is_valid = trigram_score > -5.0 and not has_invalid

        # Calculate confidence
        confidence = self._calculate_confidence(word, trigram_score, has_invalid)

        # Get corrections if needed
        corrections = []
        if not is_valid or confidence < 0.7:
            corrections = self._get_corrections(word)

        return EnglishValidationResult(
            word=word,
            is_valid=is_valid,
            confidence=confidence,
            suggested_corrections=corrections,
            trigram_score=trigram_score,
            has_invalid_trigrams=has_invalid
        )

    def validate_text(self, text: str) -> Tuple[str, float]:
        """
        Validate and correct full text.

        Args:
            text: English text to validate

        Returns:
            (corrected_text, confidence) tuple
        """
        words = text.split()
        corrected_words = []
        confidences = []

        for word in words:
            # Preserve punctuation
            prefix = ''
            suffix = ''
            core = word

            # Strip punctuation
            while core and not core[0].isalnum():
                prefix += core[0]
                core = core[1:]
            while core and not core[-1].isalnum():
                suffix = core[-1] + suffix
                core = core[:-1]

            if core:
                result = self.validate_word(core)
                confidences.append(result.confidence)

                if result.suggested_corrections and result.confidence < 0.5:
                    corrected = result.suggested_corrections[0]
                else:
                    corrected = core

                corrected_words.append(prefix + corrected + suffix)
            else:
                corrected_words.append(word)
                confidences.append(1.0)

        avg_confidence = sum(confidences) / max(1, len(confidences))
        return ' '.join(corrected_words), avg_confidence

    def _calculate_trigram_score(self, word: str) -> float:
        """Calculate log probability using trigrams."""
        word_lower = word.lower()

        if len(word_lower) < 3:
            return 0.0

        score = 0.0
        count = 0

        for i in range(len(word_lower) - 2):
            trigram = word_lower[i:i+3]
            if trigram in self.trigrams:
                score += self.trigrams[trigram] * 10  # Scale up
            else:
                score -= 0.5  # Penalty for unknown
            count += 1

        return score / max(1, count)

    def _has_invalid_trigrams(self, word: str) -> bool:
        """Check if word contains invalid trigrams."""
        word_lower = word.lower()

        for i in range(len(word_lower) - 2):
            trigram = word_lower[i:i+3]
            if trigram in self.invalid:
                return True

        # Check 2-char patterns
        for i in range(len(word_lower) - 1):
            bigram = word_lower[i:i+2]
            if bigram in self.invalid:
                return True

        return False

    def _calculate_confidence(
        self,
        word: str,
        trigram_score: float,
        has_invalid: bool
    ) -> float:
        """Calculate overall confidence score."""
        if has_invalid:
            return 0.2

        # Base confidence from trigram score
        if trigram_score > 0:
            confidence = min(1.0, 0.5 + trigram_score * 0.1)
        else:
            confidence = max(0.2, 0.5 + trigram_score * 0.05)

        return confidence

    def _get_corrections(self, word: str) -> List[str]:
        """Get suggested corrections for word."""
        corrections = []

        # Try confusion matrix substitutions
        for i, char in enumerate(word):
            if char in self.confusion:
                for replacement, prob in self.confusion[char]:
                    if prob > 0.2:
                        corrected = word[:i] + replacement + word[i+1:]
                        corrections.append(corrected)

        # Try multi-char substitutions
        for pattern, replacements in self.confusion.items():
            if len(pattern) > 1 and pattern in word:
                for replacement, prob in replacements:
                    if prob > 0.3:
                        corrected = word.replace(pattern, replacement)
                        corrections.append(corrected)

        return list(set(corrections))[:5]
```

### 7.2 Enhanced Confidence Scorer (Modify Existing)

**File:** `src/validators/confidence_scorer.py` (modifications)

Add the following class and methods to the existing file:

```python
"""
Add to existing confidence_scorer.py
"""

from ..utils.word_level_detector import WordLevelLanguageDetector, LanguageTag


class BilingualConfidenceScorer:
    """
    Confidence scorer for bilingual Arabic-English OCR.

    Combines language-specific scoring methods for
    accurate confidence calculation on mixed content.
    """

    def __init__(self):
        self.language_detector = WordLevelLanguageDetector()
        self.arabic_scorer = None  # Use existing
        self.english_scorer = None  # Use EnglishOCRValidator

    def score(
        self,
        text: str,
        language_hint: str = None,
        engine_confidence: float = 0.0
    ) -> float:
        """
        Score text confidence with language awareness.

        Args:
            text: OCR output text
            language_hint: Expected language ('ar', 'en', or None for auto)
            engine_confidence: Raw engine confidence

        Returns:
            Combined confidence score (0.0-1.0)
        """
        if not text:
            return 0.0

        # Detect language if not hinted
        if language_hint:
            dominant = LanguageTag(language_hint)
        else:
            dominant, _ = self.language_detector.get_dominant_language(text)

        # Score based on dominant language
        if dominant == LanguageTag.ARABIC:
            lang_score = self._score_arabic(text)
        elif dominant == LanguageTag.ENGLISH:
            lang_score = self._score_english(text)
        else:
            lang_score = self._score_mixed(text)

        # Combine with engine confidence
        if engine_confidence > 0:
            combined = 0.6 * lang_score + 0.4 * engine_confidence
        else:
            combined = lang_score

        return min(1.0, max(0.0, combined))

    def _score_arabic(self, text: str) -> float:
        """Score Arabic text confidence."""
        # Use existing Arabic scoring if available
        if self.arabic_scorer:
            return self.arabic_scorer.score(text)

        # Fallback: basic Arabic character ratio
        arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
        return arabic_chars / max(1, len(text))

    def _score_english(self, text: str) -> float:
        """Score English text confidence."""
        if self.english_scorer:
            _, confidence = self.english_scorer.validate_text(text)
            return confidence

        # Fallback: basic English character ratio
        english_chars = sum(1 for c in text if c.isascii() and c.isalpha())
        return english_chars / max(1, len(text))

    def _score_mixed(self, text: str) -> float:
        """Score mixed language text."""
        tagged = self.language_detector.tag_text(text)

        # Score each segment
        scores = []
        for word in tagged:
            if word.language == LanguageTag.ARABIC:
                scores.append(self._score_arabic(word.text))
            elif word.language == LanguageTag.ENGLISH:
                scores.append(self._score_english(word.text))
            else:
                scores.append(word.confidence)

        return sum(scores) / max(1, len(scores))
```

---

## 8. Phase 6: Production Pipeline

**Duration:** 4-5 days
**Dependencies:** All previous phases
**Deliverables:** 1 new file + modifications, ~400 lines

### 8.1 Bilingual OCR Pipeline

**File:** `src/engines/bilingual_ocr_pipeline.py`

```python
"""
Bilingual OCR Pipeline

Production-ready 6-stage pipeline for Arabic-English OCR:
1. Initial OCR
2. Language Detection
3. Engine Selection
4. Reprocessing (if needed)
5. Post-Processing
6. Confidence Calculation
"""

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from pathlib import Path

from ..config.arabic_ocr_config import ArabicOCRConfig, BALANCED_CONFIG
from ..utils.word_level_detector import WordLevelLanguageDetector, LanguageTag
from ..validators.confidence_scorer import BilingualConfidenceScorer
from ..ml.arabic_beam_corrector import ArabicBeamCorrector
from .fusion_ocr_engine import OCRFusionEngine, FusionStrategy

logger = logging.getLogger(__name__)


@dataclass
class PipelineStageResult:
    """Result from a pipeline stage."""
    stage_name: str
    success: bool
    data: Any
    processing_time_ms: float


@dataclass
class BilingualOCRResult:
    """Final pipeline result."""
    text: str
    confidence: float
    language: LanguageTag
    stages: List[PipelineStageResult]
    metadata: Dict[str, Any]


class BilingualOCRPipeline:
    """
    6-stage bilingual OCR pipeline.

    Stages:
    1. Initial OCR - Run primary engine
    2. Language Detection - Detect AR/EN/Mixed
    3. Engine Selection - Choose best engine for detected language
    4. Reprocessing - Re-run with optimal engine if needed
    5. Post-Processing - Apply corrections and formatting
    6. Confidence Calculation - Final confidence scoring
    """

    def __init__(
        self,
        config: ArabicOCRConfig = None,
        engine_manager = None
    ):
        self.config = config or BALANCED_CONFIG
        self.engine_manager = engine_manager

        # Initialize components
        self.language_detector = WordLevelLanguageDetector()
        self.confidence_scorer = BilingualConfidenceScorer()
        self.fusion_engine = OCRFusionEngine()

        if self.config.enable_ngram_scoring:
            from ..ml.arabic_ngram_model import ArabicNGramModel
            from ..utils.arabic_confusion_matrix import ArabicConfusionMatrix
            self.beam_corrector = ArabicBeamCorrector(
                beam_width=self.config.beam_width,
                max_corrections_per_word=self.config.max_corrections_per_word
            )
        else:
            self.beam_corrector = None

    def process(
        self,
        image_path: str,
        language_hint: str = None
    ) -> BilingualOCRResult:
        """
        Process image through 6-stage pipeline.

        Args:
            image_path: Path to image file
            language_hint: Expected language ('ar', 'en', None for auto)

        Returns:
            BilingualOCRResult with processed text
        """
        import time
        stages = []

        # Validate input
        path = Path(image_path)
        if not path.exists():
            return BilingualOCRResult(
                text="",
                confidence=0.0,
                language=LanguageTag.UNKNOWN,
                stages=[],
                metadata={"error": f"File not found: {image_path}"}
            )

        # Stage 1: Initial OCR
        start = time.perf_counter()
        raw_result = self._stage1_initial_ocr(image_path)
        stages.append(PipelineStageResult(
            "initial_ocr",
            raw_result is not None,
            raw_result,
            (time.perf_counter() - start) * 1000
        ))

        if not raw_result:
            return self._error_result("Initial OCR failed", stages)

        # Stage 2: Language Detection
        start = time.perf_counter()
        language = self._stage2_language_detection(raw_result, language_hint)
        stages.append(PipelineStageResult(
            "language_detection",
            True,
            language,
            (time.perf_counter() - start) * 1000
        ))

        # Stage 3: Engine Selection
        start = time.perf_counter()
        optimal_engine = self._stage3_engine_selection(language)
        stages.append(PipelineStageResult(
            "engine_selection",
            True,
            optimal_engine,
            (time.perf_counter() - start) * 1000
        ))

        # Stage 4: Reprocessing (if needed)
        start = time.perf_counter()
        processed = self._stage4_reprocess(
            image_path, raw_result, optimal_engine, language
        )
        stages.append(PipelineStageResult(
            "reprocess",
            processed is not None,
            processed,
            (time.perf_counter() - start) * 1000
        ))

        # Stage 5: Post-Processing
        start = time.perf_counter()
        corrected = self._stage5_post_process(processed, language)
        stages.append(PipelineStageResult(
            "post_process",
            True,
            corrected,
            (time.perf_counter() - start) * 1000
        ))

        # Stage 6: Confidence Calculation
        start = time.perf_counter()
        final_confidence = self._stage6_confidence(corrected, language)
        stages.append(PipelineStageResult(
            "confidence",
            True,
            final_confidence,
            (time.perf_counter() - start) * 1000
        ))

        # Build metadata
        metadata = {
            "pipeline_version": "1.0",
            "config_mode": self.config.mode.value,
            "total_stages": len(stages),
            "total_time_ms": sum(s.processing_time_ms for s in stages),
        }

        return BilingualOCRResult(
            text=corrected,
            confidence=final_confidence,
            language=language,
            stages=stages,
            metadata=metadata
        )

    def _stage1_initial_ocr(self, image_path: str) -> Optional[Dict]:
        """Stage 1: Run primary OCR engine."""
        if not self.engine_manager:
            logger.warning("No engine manager, returning mock result")
            return {"text": "", "confidence": 0.0, "words": []}

        try:
            engine = self.engine_manager.get_engine(self.config.primary_engine)
            result = engine.process_image(image_path, "ar")
            return {
                "text": result.full_text,
                "confidence": result.metadata.get("average_confidence", 0.5),
                "words": result.pages[0].text_blocks if result.pages else []
            }
        except Exception as e:
            logger.error(f"Stage 1 error: {e}")
            return None

    def _stage2_language_detection(
        self,
        raw_result: Dict,
        language_hint: str
    ) -> LanguageTag:
        """Stage 2: Detect dominant language."""
        if language_hint:
            return LanguageTag(language_hint)

        text = raw_result.get("text", "")
        dominant, _ = self.language_detector.get_dominant_language(text)
        return dominant

    def _stage3_engine_selection(self, language: LanguageTag) -> str:
        """Stage 3: Select optimal engine for language."""
        if language == LanguageTag.ARABIC:
            # Prefer PaddleOCR for Arabic
            return "paddle"
        elif language == LanguageTag.ENGLISH:
            # Tesseract often better for pure English
            return "tesseract" if self.config.fallback_engine == "tesseract" else "paddle"
        else:
            # Mixed content - use fusion
            return "fusion"

    def _stage4_reprocess(
        self,
        image_path: str,
        raw_result: Dict,
        optimal_engine: str,
        language: LanguageTag
    ) -> str:
        """Stage 4: Reprocess with optimal engine if needed."""
        # If already using optimal engine, return raw result
        if optimal_engine == self.config.primary_engine:
            return raw_result.get("text", "")

        # Check if confidence is good enough
        if raw_result.get("confidence", 0) > self.config.high_confidence_threshold:
            return raw_result.get("text", "")

        # Reprocess with optimal engine
        if optimal_engine == "fusion" and self.config.enable_easyocr:
            # Run multiple engines and fuse
            results = [raw_result]

            if self.engine_manager and self.config.fallback_engine:
                try:
                    engine = self.engine_manager.get_engine(self.config.fallback_engine)
                    fallback_result = engine.process_image(
                        image_path,
                        "ar" if language == LanguageTag.ARABIC else "en"
                    )
                    results.append({
                        "text": fallback_result.full_text,
                        "engine": self.config.fallback_engine,
                        "words": []
                    })
                except Exception as e:
                    logger.warning(f"Fallback engine failed: {e}")

            if len(results) > 1:
                fused = self.fusion_engine.fuse(results, FusionStrategy.CHARACTER_VOTE)
                return fused.text

        return raw_result.get("text", "")

    def _stage5_post_process(self, text: str, language: LanguageTag) -> str:
        """Stage 5: Apply post-processing corrections."""
        if not text:
            return text

        # Apply beam search correction for Arabic
        if language == LanguageTag.ARABIC and self.beam_corrector:
            result = self.beam_corrector.correct_text(text)
            return result.corrected

        # Basic cleanup for all languages
        text = ' '.join(text.split())  # Normalize whitespace

        return text

    def _stage6_confidence(self, text: str, language: LanguageTag) -> float:
        """Stage 6: Calculate final confidence score."""
        lang_code = language.value if language != LanguageTag.UNKNOWN else None
        return self.confidence_scorer.score(text, lang_code)

    def _error_result(
        self,
        message: str,
        stages: List[PipelineStageResult]
    ) -> BilingualOCRResult:
        """Create error result."""
        return BilingualOCRResult(
            text="",
            confidence=0.0,
            language=LanguageTag.UNKNOWN,
            stages=stages,
            metadata={"error": message}
        )
```

### 8.2 Integration with Read Tool

**File:** `src/read_tool.py` (modifications)

Add the following integration points:

```python
# Add to imports at top of file
from .config.arabic_ocr_config import ArabicOCRConfig, get_config

# Add to HybridReadTool.__init__
def __init__(self, config: Optional[ReadToolConfig] = None, ocr_config: Optional[ArabicOCRConfig] = None):
    self.config = config or ReadToolConfig()
    self.ocr_config = ocr_config  # NEW: Arabic OCR config
    self.engine_manager = EngineManager(self.config)
    self._register_engines()

    # Initialize bilingual pipeline if config provided
    self._bilingual_pipeline = None
    if self.ocr_config:
        self._init_bilingual_pipeline()

def _init_bilingual_pipeline(self):
    """Initialize bilingual OCR pipeline."""
    try:
        from .engines.bilingual_ocr_pipeline import BilingualOCRPipeline
        self._bilingual_pipeline = BilingualOCRPipeline(
            config=self.ocr_config,
            engine_manager=self.engine_manager
        )
    except ImportError:
        logger.warning("BilingualOCRPipeline not available")

# Modify _read_image_file to optionally use bilingual pipeline
def _read_image_file(
    self,
    path: Path,
    lang: str,
    engine: str,
    prompt: Optional[str],
    structured_output: bool,
    use_bilingual_pipeline: bool = False  # NEW parameter
) -> ReadResult:
    """Read image file using OCR engine."""

    # Use bilingual pipeline if available and requested
    if use_bilingual_pipeline and self._bilingual_pipeline:
        result = self._bilingual_pipeline.process(str(path), lang)
        # Convert to ReadResult format
        return ReadResult(
            success=True,
            file_path=str(path),
            file_type="image",
            engine_used="bilingual_pipeline",
            pages=[PageResult(
                page_number=1,
                text_blocks=[],
                full_text=result.text,
            )],
            full_text=result.text,
            processing_time_ms=result.metadata.get("total_time_ms", 0),
            language=result.language.value,
            metadata={
                "confidence": result.confidence,
                "pipeline_stages": len(result.stages),
                **result.metadata
            }
        )

    # ... rest of existing implementation
```

---

## 9. Data Files Required

### 9.1 Data File Specifications

| File | Location | Size | Format | Priority | Source |
|------|----------|------|--------|----------|--------|
| `arabic_ngrams.json` | `models/` | ~50MB | JSON | CRITICAL | Build from corpus |
| `arabic_bpe_vocab.pkl` | `models/` | ~2MB | Pickle | HIGH | HuggingFace |
| `arabic_dictionary.txt` | `data/` | ~5MB | Text | HIGH | Word list |
| `english_trigrams.json` | `models/` | ~10MB | JSON | MEDIUM | Build from corpus |
| `invoice_vocabulary.txt` | `data/` | ~100KB | Text | Complete | Existing |

### 9.2 Data Generation Scripts

```python
# scripts/generate_ngrams.py
"""Generate Arabic n-gram model from text corpus."""

import json
from collections import Counter
from pathlib import Path

def generate_arabic_ngrams(corpus_path: str, output_path: str):
    """Generate trigram frequencies from corpus."""
    trigrams = Counter()

    with open(corpus_path, 'r', encoding='utf-8') as f:
        for line in f:
            text = line.strip().lower()
            for i in range(len(text) - 2):
                trigrams[text[i:i+3]] += 1

    # Convert to log probabilities
    total = sum(trigrams.values())
    ngram_model = {
        trigram: math.log(count / total)
        for trigram, count in trigrams.most_common(100000)
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({'trigrams': ngram_model}, f, ensure_ascii=False)

if __name__ == '__main__':
    generate_arabic_ngrams(
        'data/arabic_corpus.txt',
        'models/arabic_ngrams.json'
    )
```

---

## 10. Testing Strategy

### 10.1 Unit Tests

```
tests/
├── test_config.py              # Configuration tests
├── test_confusion_matrix.py    # Confusion matrix tests
├── test_ngram_model.py         # N-gram model tests
├── test_beam_corrector.py      # Beam corrector tests
├── test_morphology.py          # Morphology analyzer tests
├── test_bpe_tokenizer.py       # BPE tokenizer tests
├── test_fusion_engine.py       # Fusion engine tests
├── test_language_detector.py   # Language detector tests
├── test_arabizi.py             # Arabizi transliterator tests
├── test_bidi.py                # Bidirectional text tests
├── test_english_validator.py   # English validator tests
├── test_confidence_scorer.py   # Confidence scorer tests
└── test_bilingual_pipeline.py  # Pipeline integration tests
```

### 10.2 Sample Test Cases

```python
# tests/test_confusion_matrix.py
import pytest
from src.utils.arabic_confusion_matrix import ArabicConfusionMatrix, CharPosition

class TestArabicConfusionMatrix:
    def setup_method(self):
        self.matrix = ArabicConfusionMatrix()

    def test_get_candidates_basic(self):
        """Test getting confusion candidates."""
        candidates = self.matrix.get_candidates('ب')
        assert len(candidates) > 0
        assert any(c[0] == 'ت' for c in candidates)

    def test_position_aware_candidates(self):
        """Test position-aware probabilities."""
        initial = self.matrix.get_candidates('ب', CharPosition.INITIAL)
        final = self.matrix.get_candidates('ب', CharPosition.FINAL)
        # Probabilities should differ by position
        assert initial != final

    def test_confusable_chars(self):
        """Test confusable character set."""
        chars = self.matrix.get_all_confusable_chars()
        assert 'ب' in chars
        assert 'ت' in chars
        assert 'ث' in chars
```

### 10.3 Integration Tests

```python
# tests/test_bilingual_pipeline.py
import pytest
from src.engines.bilingual_ocr_pipeline import BilingualOCRPipeline
from src.config.arabic_ocr_config import BALANCED_CONFIG

class TestBilingualPipeline:
    def setup_method(self):
        self.pipeline = BilingualOCRPipeline(config=BALANCED_CONFIG)

    def test_arabic_document(self, sample_arabic_image):
        """Test processing Arabic document."""
        result = self.pipeline.process(sample_arabic_image, 'ar')
        assert result.confidence > 0.5
        assert result.language.value == 'ar'

    def test_english_document(self, sample_english_image):
        """Test processing English document."""
        result = self.pipeline.process(sample_english_image, 'en')
        assert result.confidence > 0.5
        assert result.language.value == 'en'

    def test_mixed_document(self, sample_mixed_image):
        """Test processing mixed Arabic-English document."""
        result = self.pipeline.process(sample_mixed_image)
        assert result.confidence > 0.3
        assert len(result.stages) == 6
```

### 10.4 Benchmark Tests

```python
# tests/benchmark_accuracy.py
"""Benchmark OCR accuracy against test dataset."""

import json
from pathlib import Path
from src.engines.bilingual_ocr_pipeline import BilingualOCRPipeline

def calculate_cer(reference: str, hypothesis: str) -> float:
    """Calculate Character Error Rate."""
    import editdistance
    return editdistance.eval(reference, hypothesis) / max(1, len(reference))

def calculate_wer(reference: str, hypothesis: str) -> float:
    """Calculate Word Error Rate."""
    import editdistance
    ref_words = reference.split()
    hyp_words = hypothesis.split()
    return editdistance.eval(ref_words, hyp_words) / max(1, len(ref_words))

def run_benchmark(test_dir: str):
    """Run benchmark on test dataset."""
    pipeline = BilingualOCRPipeline()
    results = []

    test_path = Path(test_dir)
    for image_path in test_path.glob('*.png'):
        gt_path = image_path.with_suffix('.txt')
        if not gt_path.exists():
            continue

        # Get ground truth
        with open(gt_path, 'r', encoding='utf-8') as f:
            ground_truth = f.read().strip()

        # Run OCR
        result = pipeline.process(str(image_path))

        # Calculate metrics
        cer = calculate_cer(ground_truth, result.text)
        wer = calculate_wer(ground_truth, result.text)

        results.append({
            'image': image_path.name,
            'cer': cer,
            'wer': wer,
            'confidence': result.confidence
        })

    # Calculate averages
    avg_cer = sum(r['cer'] for r in results) / len(results)
    avg_wer = sum(r['wer'] for r in results) / len(results)

    print(f"Average CER: {avg_cer:.4f}")
    print(f"Average WER: {avg_wer:.4f}")

    return results
```

---

## 11. File Structure

### 11.1 New Files to Create

```
src/
├── config/
│   ├── __init__.py                   # NEW
│   └── arabic_ocr_config.py          # NEW - Configuration system
├── engines/
│   ├── fusion_ocr_engine.py          # NEW - Multi-engine fusion
│   └── bilingual_ocr_pipeline.py     # NEW - Production pipeline
├── ml/
│   ├── __init__.py                   # NEW
│   ├── arabic_ngram_model.py         # NEW - N-gram language model
│   ├── arabic_beam_corrector.py      # NEW - Beam search correction
│   └── arabic_bpe_tokenizer.py       # NEW - BPE tokenization
├── utils/
│   ├── arabic_confusion_matrix.py    # NEW - Standalone confusion matrix
│   ├── arabic_morphology.py          # NEW - Morphological analyzer
│   ├── word_level_detector.py        # NEW - Word-level language detection
│   ├── arabizi_transliterator.py     # NEW - Arabizi to Arabic
│   └── bidirectional_text.py         # NEW - Unicode Bidi Algorithm
├── validators/
│   └── english_validator.py          # NEW - English OCR validation
└── read_tool.py                      # MODIFY - Integration

models/
├── arabic_ngrams.json                # NEW - N-gram data
├── arabic_bpe_vocab.pkl              # NEW - BPE vocabulary
└── english_trigrams.json             # NEW - English trigrams

scripts/
├── generate_ngrams.py                # NEW - N-gram generation
└── prepare_bpe.py                    # NEW - BPE preparation

tests/
├── test_config.py                    # NEW
├── test_confusion_matrix.py          # NEW
├── test_ngram_model.py               # NEW
├── test_beam_corrector.py            # NEW
├── test_morphology.py                # NEW
├── test_bpe_tokenizer.py             # NEW
├── test_fusion_engine.py             # NEW
├── test_language_detector.py         # NEW
├── test_arabizi.py                   # NEW
├── test_bidi.py                      # NEW
├── test_english_validator.py         # NEW
├── test_confidence_scorer.py         # NEW
├── test_bilingual_pipeline.py        # NEW
└── benchmark_accuracy.py             # NEW
```

### 11.2 Files to Modify

| File | Modification |
|------|--------------|
| `src/read_tool.py` | Add bilingual pipeline integration |
| `src/validators/confidence_scorer.py` | Add BilingualConfidenceScorer |
| `src/__init__.py` | Export new modules |
| `requirements.txt` | Add new dependencies |

---

## 12. Implementation Order

### 12.1 Execution Timeline

| Phase | Components | Dependencies | Est. Days |
|-------|------------|--------------|-----------|
| **1** | Config, ConfusionMatrix, NGram | None | 3-4 |
| **2** | BeamCorrector, Morphology, BPE | Phase 1 | 4-5 |
| **3** | FusionEngine | Phase 2 | 3-4 |
| **4** | LanguageDetector, Arabizi, Bidi | None | 3-4 |
| **5** | EnglishValidator, ConfidenceScorer | Phase 4 | 3-4 |
| **6** | BilingualPipeline, Integration | All | 4-5 |

**Total:** 20-26 days

### 12.2 Parallel Execution Opportunities

- Phase 4 can run in parallel with Phases 2-3
- Unit tests can be written alongside implementation
- Data file generation can run independently

---

## 13. Success Criteria

### 13.1 Accuracy Metrics

| Metric | Arabic | English | Mixed | Target |
|--------|--------|---------|-------|--------|
| **CER** | <0.06 | <0.02 | <0.08 | ✓ |
| **WER** | <0.16 | <0.04 | <0.12 | ✓ |

### 13.2 Performance Metrics

| Metric | Value | Target |
|--------|-------|--------|
| Arabic images/sec | >5 | ✓ |
| English images/sec | >10 | ✓ |
| Mixed images/sec | >3 | ✓ |

### 13.3 Quality Criteria

| Criterion | Target |
|-----------|--------|
| Test coverage | >90% |
| Code documentation | All public APIs |
| Integration tests passing | 100% |
| Benchmark tests passing | All metrics met |

---

## 14. Risk Mitigation

### 14.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| N-gram model data unavailable | HIGH | LOW | Use existing arabic_spell_checker patterns as fallback |
| BPE vocabulary training time | MEDIUM | MEDIUM | Use pre-built Arabic BPE from HuggingFace |
| Qari-OCR integration issues | MEDIUM | MEDIUM | VLM fallback is optional, pipeline works without it |
| Performance bottlenecks | HIGH | LOW | Implement caching, lazy loading (already in codebase) |
| Memory constraints | MEDIUM | LOW | Use model quantization, batch processing |

### 14.2 Dependency Risks

| Dependency | Risk | Mitigation |
|------------|------|------------|
| PaddleOCR | Version updates may break | Pin version in requirements |
| EasyOCR | Optional, may not install | Make optional with fallback |
| Python-bidi | May have bugs | Use simplified implementation |

---

## Appendix A: API Reference

### A.1 Configuration API

```python
# Get configuration by mode
from src.config.arabic_ocr_config import get_config, ArabicOCRConfig

config = get_config("accurate")  # Returns ACCURATE_CONFIG

# Custom configuration
custom = ArabicOCRConfig(
    mode=OCRMode.BALANCED,
    beam_width=7,
    enable_easyocr=True
)
```

### A.2 Pipeline API

```python
# Process image
from src.engines.bilingual_ocr_pipeline import BilingualOCRPipeline

pipeline = BilingualOCRPipeline(config)
result = pipeline.process("image.png", language_hint="ar")

print(result.text)
print(result.confidence)
print(result.language)
```

### A.3 Fusion API

```python
# Fuse multiple OCR results
from src.engines.fusion_ocr_engine import OCRFusionEngine, FusionStrategy

fusion = OCRFusionEngine()
result = fusion.fuse(
    [paddle_result, easyocr_result],
    strategy=FusionStrategy.CHARACTER_VOTE
)
```

---

## Appendix B: Configuration Reference

### B.1 OCR Modes

| Mode | Use Case | Engines | Correction |
|------|----------|---------|------------|
| FAST | Real-time | Single | Minimal |
| BALANCED | General | Primary + Fallback | Standard |
| ACCURATE | Quality | Multi-engine | Full |
| MAXIMUM | Archival | All + VLM | Exhaustive |

### B.2 PaddleOCR Arabic Parameters

```python
paddle_config = {
    'text_det_limit_side_len': 1280,    # Image max dimension
    'text_det_unclip_ratio': 1.8,       # Text box expansion
    'text_det_thresh': 0.3,              # Detection threshold
    'text_det_box_thresh': 0.6,          # Box confidence threshold
    'text_rec_score_thresh': 0.5,        # Recognition threshold
}
```

### B.3 Engine Weights

```python
ENGINE_WEIGHTS = {
    'paddle': 1.0,      # PP-OCRv5 - strong Arabic
    'easyocr': 0.8,     # Good Arabic, slower
    'qari': 1.2,        # Best for printed Arabic
    'tesseract': 0.6,   # Fallback
}
```

---

**Document Version:** 1.0
**Last Updated:** 2026-01-07
**Author:** Claude Code Implementation Team
