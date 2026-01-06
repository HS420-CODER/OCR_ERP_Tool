"""
ERP Arabic OCR Microservice - Confidence-Weighted Fusion Engine
================================================================
Implements multi-engine result fusion with Arabic-aware algorithms.
"""

import re
import logging
from typing import List, Dict, Set, Tuple, Optional
from collections import Counter, defaultdict
from dataclasses import dataclass

from . import (
    OCRResult,
    FusionResult,
    FusionStrategy,
    OCREngine
)

logger = logging.getLogger(__name__)


# Arabic vocabulary for validation (common invoice/document words)
ARABIC_VOCABULARY = {
    # Invoice terms
    'فاتورة', 'رقم', 'تاريخ', 'المبلغ', 'الاجمالي', 'الضريبة',
    'الرقم', 'الضريبي', 'اسم', 'العميل', 'المورد', 'البائع',
    'الكمية', 'السعر', 'الوحدة', 'الخصم', 'الصافي',
    # Common words
    'شركة', 'مؤسسة', 'التجارية', 'المحدودة', 'السعودية',
    'المملكة', 'العربية', 'الرياض', 'جدة', 'مكة', 'الدمام',
    # Document terms
    'صفحة', 'من', 'الى', 'عقد', 'اتفاقية', 'ملحق',
    'توقيع', 'ختم', 'مستند', 'وثيقة', 'بيان',
    # Numbers and units
    'ريال', 'دولار', 'درهم', 'دينار',
    # Dates
    'يناير', 'فبراير', 'مارس', 'ابريل', 'مايو', 'يونيو',
    'يوليو', 'اغسطس', 'سبتمبر', 'اكتوبر', 'نوفمبر', 'ديسمبر',
    # Status
    'مدفوع', 'غير', 'مستحق', 'معلق', 'ملغي', 'مؤكد',
}

# Extended vocabulary with common variations
ARABIC_VOCABULARY_EXTENDED = ARABIC_VOCABULARY | {
    'الفاتورة', 'المبيعات', 'المشتريات', 'الحساب', 'البنك',
    'التحويل', 'الدفع', 'السداد', 'الرصيد', 'المتبقي',
    'الوصف', 'البند', 'المواصفات', 'الملاحظات',
}


class FusionEngine:
    """
    Confidence-weighted fusion engine for multi-engine OCR results.

    Strategies:
    1. Confidence-Weighted: Σ(word × confidence) / Σ(confidence)
    2. Majority Voting: Democratic word selection
    3. Dictionary-Validated: Prefer words in Arabic vocabulary
    4. Best Confidence: Select result with highest overall confidence

    Features:
    - Arabic-aware tokenization
    - Vocabulary validation bonus
    - Conflict resolution for disagreements
    """

    def __init__(
        self,
        vocabulary: Optional[Set[str]] = None,
        confidence_threshold: float = 0.7
    ):
        """
        Initialize fusion engine.

        Args:
            vocabulary: Arabic vocabulary for validation
            confidence_threshold: Minimum confidence for fusion
        """
        self.vocabulary = vocabulary or ARABIC_VOCABULARY_EXTENDED
        self.confidence_threshold = confidence_threshold

    def fuse_results(
        self,
        results: List[OCRResult],
        strategy: FusionStrategy = FusionStrategy.CONFIDENCE_WEIGHTED
    ) -> FusionResult:
        """
        Fuse multiple OCR results into a single output.

        Args:
            results: List of OCR results from different engines
            strategy: Fusion strategy to use

        Returns:
            FusionResult with fused text
        """
        if not results:
            return FusionResult(
                fused_text="",
                confidence=0.0,
                strategy=strategy,
                individual_results=[]
            )

        if len(results) == 1:
            return FusionResult(
                fused_text=results[0].text,
                confidence=results[0].confidence,
                strategy=strategy,
                individual_results=results
            )

        # Select fusion method based on strategy
        if strategy == FusionStrategy.CONFIDENCE_WEIGHTED:
            fused_text, confidence, word_sources = self._confidence_weighted_fusion(results)
        elif strategy == FusionStrategy.MAJORITY_VOTING:
            fused_text, confidence, word_sources = self._majority_voting_fusion(results)
        elif strategy == FusionStrategy.DICTIONARY_VALIDATED:
            fused_text, confidence, word_sources = self._dictionary_validated_fusion(results)
        elif strategy == FusionStrategy.BEST_CONFIDENCE:
            best = max(results, key=lambda r: r.confidence)
            fused_text = best.text
            confidence = best.confidence
            word_sources = {w: best.engine.value for w in fused_text.split()}
        else:
            fused_text, confidence, word_sources = self._confidence_weighted_fusion(results)

        # Calculate improvement score
        best_single = max(r.confidence for r in results)
        improvement = confidence - best_single

        return FusionResult(
            fused_text=fused_text,
            confidence=confidence,
            strategy=strategy,
            individual_results=results,
            improvement_score=improvement,
            word_sources=word_sources
        )

    def _confidence_weighted_fusion(
        self,
        results: List[OCRResult]
    ) -> Tuple[str, float, Dict[str, str]]:
        """
        Confidence-weighted word fusion.

        For each word position, select word with highest weighted score:
        score = confidence × vocabulary_bonus

        Args:
            results: OCR results to fuse

        Returns:
            Tuple of (fused_text, confidence, word_sources)
        """
        # Tokenize all results
        tokenized_results = [
            (self._tokenize_arabic(r.text), r.confidence, r.engine)
            for r in results
        ]

        # Find maximum number of tokens
        max_tokens = max(len(tokens) for tokens, _, _ in tokenized_results)

        if max_tokens == 0:
            return "", 0.0, {}

        # Fuse word by word
        fused_words = []
        word_sources = {}
        total_confidence = 0.0

        for i in range(max_tokens):
            candidates = []

            for tokens, base_confidence, engine in tokenized_results:
                if i < len(tokens):
                    word = tokens[i]
                    vocab_bonus = self._calculate_vocabulary_bonus(word)
                    score = base_confidence * vocab_bonus
                    candidates.append((word, score, engine))

            if candidates:
                # Select word with highest score
                best_word, best_score, best_engine = max(
                    candidates, key=lambda x: x[1]
                )
                fused_words.append(best_word)
                word_sources[best_word] = best_engine.value
                total_confidence += best_score

        fused_text = " ".join(fused_words)
        avg_confidence = total_confidence / len(fused_words) if fused_words else 0.0

        return fused_text, avg_confidence, word_sources

    def _majority_voting_fusion(
        self,
        results: List[OCRResult]
    ) -> Tuple[str, float, Dict[str, str]]:
        """
        Majority voting word fusion.

        For each word position, select the most common word.

        Args:
            results: OCR results to fuse

        Returns:
            Tuple of (fused_text, confidence, word_sources)
        """
        tokenized_results = [
            (self._tokenize_arabic(r.text), r.confidence, r.engine)
            for r in results
        ]

        max_tokens = max(len(tokens) for tokens, _, _ in tokenized_results)

        if max_tokens == 0:
            return "", 0.0, {}

        fused_words = []
        word_sources = {}
        confidences = []

        for i in range(max_tokens):
            word_votes = Counter()
            word_engines = {}

            for tokens, confidence, engine in tokenized_results:
                if i < len(tokens):
                    word = tokens[i]
                    word_votes[word] += 1
                    word_engines[word] = engine

            if word_votes:
                # Get most common word
                best_word, vote_count = word_votes.most_common(1)[0]
                fused_words.append(best_word)
                word_sources[best_word] = word_engines[best_word].value
                # Confidence based on vote ratio
                confidences.append(vote_count / len(results))

        fused_text = " ".join(fused_words)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return fused_text, avg_confidence, word_sources

    def _dictionary_validated_fusion(
        self,
        results: List[OCRResult]
    ) -> Tuple[str, float, Dict[str, str]]:
        """
        Dictionary-validated word fusion.

        Prefer words that appear in the Arabic vocabulary.

        Args:
            results: OCR results to fuse

        Returns:
            Tuple of (fused_text, confidence, word_sources)
        """
        tokenized_results = [
            (self._tokenize_arabic(r.text), r.confidence, r.engine)
            for r in results
        ]

        max_tokens = max(len(tokens) for tokens, _, _ in tokenized_results)

        if max_tokens == 0:
            return "", 0.0, {}

        fused_words = []
        word_sources = {}
        confidences = []

        for i in range(max_tokens):
            candidates = []

            for tokens, base_confidence, engine in tokenized_results:
                if i < len(tokens):
                    word = tokens[i]
                    # Strong bonus for dictionary words
                    in_vocab = self._normalize_for_vocab(word) in self.vocabulary
                    score = base_confidence * (2.0 if in_vocab else 1.0)
                    candidates.append((word, score, engine, in_vocab))

            if candidates:
                # Prefer dictionary words
                vocab_candidates = [c for c in candidates if c[3]]
                if vocab_candidates:
                    best_word, best_score, best_engine, _ = max(
                        vocab_candidates, key=lambda x: x[1]
                    )
                else:
                    best_word, best_score, best_engine, _ = max(
                        candidates, key=lambda x: x[1]
                    )

                fused_words.append(best_word)
                word_sources[best_word] = best_engine.value
                confidences.append(best_score / 2.0)  # Normalize back

        fused_text = " ".join(fused_words)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return fused_text, avg_confidence, word_sources

    def _tokenize_arabic(self, text: str) -> List[str]:
        """
        Arabic-aware tokenization.

        Handles:
        - Arabic word boundaries
        - Punctuation separation
        - Number preservation
        - Mixed Arabic/English

        Args:
            text: Text to tokenize

        Returns:
            List of tokens
        """
        if not text:
            return []

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text.strip())

        # Split on whitespace while preserving punctuation
        tokens = []
        current_token = ""

        for char in text:
            if char.isspace():
                if current_token:
                    tokens.append(current_token)
                    current_token = ""
            elif char in '.,،؛:!?()[]{}«»"\'':
                if current_token:
                    tokens.append(current_token)
                    current_token = ""
                # Optionally include punctuation as separate token
                # tokens.append(char)
            else:
                current_token += char

        if current_token:
            tokens.append(current_token)

        return tokens

    def _calculate_vocabulary_bonus(self, word: str) -> float:
        """
        Calculate vocabulary bonus for a word.

        Args:
            word: Word to check

        Returns:
            Bonus multiplier (1.0-1.5)
        """
        normalized = self._normalize_for_vocab(word)

        # Exact match in vocabulary
        if normalized in self.vocabulary:
            return 1.5

        # Partial match (word contains vocabulary word)
        for vocab_word in self.vocabulary:
            if vocab_word in normalized or normalized in vocab_word:
                return 1.2

        # Check if it looks like a valid Arabic word
        if self._is_valid_arabic_word(word):
            return 1.1

        return 1.0

    def _normalize_for_vocab(self, word: str) -> str:
        """
        Normalize word for vocabulary lookup.

        Removes:
        - Diacritics
        - Leading/trailing punctuation
        - Kashida

        Args:
            word: Word to normalize

        Returns:
            Normalized word
        """
        # Remove diacritics
        diacritics = '\u064B\u064C\u064D\u064E\u064F\u0650\u0651\u0652'
        result = ''.join(c for c in word if c not in diacritics)

        # Remove kashida
        result = result.replace('\u0640', '')

        # Strip punctuation
        result = result.strip('.,،؛:!?()[]{}«»"\'')

        return result

    def _is_valid_arabic_word(self, word: str) -> bool:
        """
        Check if word appears to be valid Arabic.

        Args:
            word: Word to check

        Returns:
            True if word looks like valid Arabic
        """
        if not word:
            return False

        # Count Arabic characters
        arabic_count = sum(1 for c in word if '\u0600' <= c <= '\u06FF')

        # Minimum length and Arabic ratio
        if len(word) >= 2 and arabic_count / len(word) > 0.8:
            return True

        return False

    def resolve_conflicts(
        self,
        results: List[OCRResult],
        position: int
    ) -> Tuple[str, float, str]:
        """
        Resolve word conflicts at a specific position.

        Uses multiple signals:
        1. Confidence scores
        2. Vocabulary validation
        3. Character-level agreement

        Args:
            results: OCR results
            position: Word position to resolve

        Returns:
            Tuple of (best_word, confidence, source_engine)
        """
        candidates = []

        for result in results:
            tokens = self._tokenize_arabic(result.text)
            if position < len(tokens):
                word = tokens[position]
                candidates.append((
                    word,
                    result.confidence,
                    result.engine,
                    self._calculate_vocabulary_bonus(word)
                ))

        if not candidates:
            return "", 0.0, ""

        # Score each candidate
        scored = []
        for word, confidence, engine, vocab_bonus in candidates:
            # Base score from confidence
            score = confidence * vocab_bonus

            # Bonus for agreement with other candidates
            for other_word, _, _, _ in candidates:
                if other_word == word:
                    score += 0.1
                elif self._words_similar(word, other_word):
                    score += 0.05

            scored.append((word, score, engine))

        # Return best
        best_word, best_score, best_engine = max(scored, key=lambda x: x[1])
        return best_word, min(best_score, 1.0), best_engine.value

    def _words_similar(self, word1: str, word2: str) -> bool:
        """
        Check if two words are similar (fuzzy match).

        Args:
            word1: First word
            word2: Second word

        Returns:
            True if words are similar
        """
        if word1 == word2:
            return True

        # Normalize both
        n1 = self._normalize_for_vocab(word1)
        n2 = self._normalize_for_vocab(word2)

        if n1 == n2:
            return True

        # Simple edit distance check
        if len(n1) > 2 and len(n2) > 2:
            # Check if one is substring of other
            if n1 in n2 or n2 in n1:
                return True

            # Check character overlap
            common = sum(1 for c in n1 if c in n2)
            ratio = common / max(len(n1), len(n2))
            return ratio > 0.7

        return False


# Export
__all__ = ["FusionEngine", "ARABIC_VOCABULARY", "ARABIC_VOCABULARY_EXTENDED"]
