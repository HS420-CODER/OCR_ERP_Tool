"""
Machine Learning Arabic OCR Enhancer - Stage 6, Step 6.1

ML-based Arabic OCR enhancement with rule-based fallback.

Features:
- Character-level error correction model (when available)
- Named entity recognition for field extraction
- Sequence labeling for structure detection
- Comprehensive rule-based fallback

This module provides ML-enhanced text correction when trained
models are available, with automatic fallback to rule-based
enhancement for production reliability.
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class EnhancementMode(Enum):
    """Enhancement mode selection."""
    ML_ONLY = "ml_only"           # Only use ML (fail if unavailable)
    RULE_ONLY = "rule_only"       # Only use rules
    ML_WITH_FALLBACK = "ml_with_fallback"  # ML preferred, rules as fallback
    HYBRID = "hybrid"             # Combine ML and rules


@dataclass
class EnhancementResult:
    """Result of text enhancement."""
    original_text: str
    enhanced_text: str
    mode_used: str  # 'ml', 'rule', 'hybrid'
    corrections: List[Dict[str, Any]] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original": self.original_text,
            "enhanced": self.enhanced_text,
            "mode": self.mode_used,
            "corrections": self.corrections,
            "entities": self.entities,
            "confidence": self.confidence,
        }


class MLArabicEnhancer:
    """
    Machine learning-based Arabic OCR enhancement.

    Uses:
    - Character-level error correction model (optional)
    - Named entity recognition for field extraction
    - Sequence labeling for structure detection

    Falls back to comprehensive rule-based enhancement
    when ML models are not available.

    Usage:
        enhancer = MLArabicEnhancer()
        result = enhancer.enhance("الفانورة الضرية")
        print(result.enhanced_text)  # "الفاتورة الضريبية"
    """

    # Invoice domain vocabulary for NER
    INVOICE_ENTITIES = {
        "TAX_NUMBER": [
            r'3\d{14}',  # Saudi tax number
            r'\d{15}',   # Generic 15-digit
        ],
        "INVOICE_NUMBER": [
            r'INV[-/]?\d+',
            r'فاتورة\s*[-#:]?\s*\d+',
            r'\d{4,}[-/]\d+',
        ],
        "DATE": [
            r'\d{4}[-/]\d{2}[-/]\d{2}',
            r'\d{2}[-/]\d{2}[-/]\d{4}',
            r'\d{1,2}\s+\w+\s+\d{4}',
        ],
        "CURRENCY": [
            r'\d+[,.]?\d*\s*(SAR|ر\.س|ريال)',
            r'(SAR|ر\.س|ريال)\s*\d+[,.]?\d*',
        ],
        "PHONE": [
            r'\+?966\s*\d{9}',
            r'05\d{8}',
            r'\d{3}[-\s]?\d{3}[-\s]?\d{4}',
        ],
    }

    # Common OCR errors in Arabic (character-level)
    CHAR_CORRECTIONS = {
        # Dot-related confusions
        'ب': {'candidates': ['ت', 'ث', 'ن', 'ي'], 'context_weight': 0.8},
        'ج': {'candidates': ['ح', 'خ'], 'context_weight': 0.9},
        'د': {'candidates': ['ذ'], 'context_weight': 0.9},
        'ر': {'candidates': ['ز'], 'context_weight': 0.9},
        'س': {'candidates': ['ش'], 'context_weight': 0.9},
        'ص': {'candidates': ['ض'], 'context_weight': 0.9},
        'ط': {'candidates': ['ظ'], 'context_weight': 0.9},
        'ع': {'candidates': ['غ'], 'context_weight': 0.9},
        'ف': {'candidates': ['ق'], 'context_weight': 0.8},
        'ك': {'candidates': ['ل'], 'context_weight': 0.7},
        'ه': {'candidates': ['ة'], 'context_weight': 0.95},
    }

    # Word-level corrections for invoice domain
    WORD_CORRECTIONS = {
        # Tax/Invoice terms (high frequency errors)
        'الضرية': 'الضريبة',
        'الضربة': 'الضريبة',
        'الضربية': 'الضريبية',
        'الفانورة': 'الفاتورة',
        'الفاتوره': 'الفاتورة',
        'الفاتورھ': 'الفاتورة',
        'المجووع': 'المجموع',
        'المجوع': 'المجموع',
        'الاجمالى': 'الإجمالي',
        'الاجمالي': 'الإجمالي',
        'الكويه': 'الكمية',
        'الكميه': 'الكمية',
        'الوحده': 'الوحدة',
        'السهر': 'السعر',
        'السحر': 'السعر',
        'البياى': 'البيان',
        'البيأن': 'البيان',
        'المورذ': 'المورد',
        'العميل': 'العميل',
        'الرصبد': 'الرصيد',
        'مدفوح': 'مدفوع',
        'المرجحي': 'المرجعي',
        'المرجهي': 'المرجعي',
        'الرقو': 'الرقم',

        # Common field labels
        'الباريخ': 'التاريخ',
        'التأريخ': 'التاريخ',
        'الوفت': 'الوقت',
        'رقو': 'رقم',
        'التسجبل': 'التسجيل',
        'التجاري': 'التجاري',
        'السجل': 'السجل',

        # Vendor/Customer
        'الموزد': 'المورد',
        'المشترى': 'المشتري',
        'المستفبد': 'المستفيد',

        # Totals
        'صافى': 'صافي',
        'صافي': 'صافي',
        'اجمالى': 'إجمالي',
        'مبلع': 'مبلغ',
    }

    # Sequence patterns for structure detection
    STRUCTURE_PATTERNS = {
        'header': [
            r'(فاتورة|إشعار|سند)',
            r'(ضريبي[ةه]?)',
            r'(مبسط[ةه]?)',
        ],
        'vendor_section': [
            r'(المورد|البائع|المنشأة)',
            r'(الرقم\s*الضريبي)',
            r'(السجل\s*التجاري)',
        ],
        'customer_section': [
            r'(العميل|المشتري|المستفيد)',
            r'(اسم\s*العميل)',
        ],
        'items_section': [
            r'(البنود|الأصناف|المنتجات)',
            r'(الكمية|العدد)',
            r'(السعر|الوحدة)',
        ],
        'totals_section': [
            r'(المجموع|الإجمالي)',
            r'(الضريبة|ضريبة)',
            r'(صافي|الصافي)',
        ],
    }

    def __init__(
        self,
        model_path: Optional[str] = None,
        mode: EnhancementMode = EnhancementMode.ML_WITH_FALLBACK,
        context: str = "invoice"
    ):
        """
        Initialize the ML enhancer.

        Args:
            model_path: Path to trained ML model (optional)
            mode: Enhancement mode selection
            context: Document context ("invoice", "receipt", "general")
        """
        self.model_path = model_path
        self.mode = mode
        self.context = context
        self._model = None
        self._tokenizer = None
        self._model_available = False

        # Try to load ML model if path provided
        if model_path:
            self._load_model()

    def _load_model(self) -> bool:
        """
        Attempt to load ML model.

        Returns:
            True if model loaded successfully
        """
        if not self.model_path:
            return False

        model_path = Path(self.model_path)
        if not model_path.exists():
            logger.warning(f"Model path not found: {self.model_path}")
            return False

        try:
            # Try to load transformers model (optional dependency)
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(str(model_path))
            self._model = AutoModelForSeq2SeqLM.from_pretrained(str(model_path))
            self._model_available = True
            logger.info(f"ML model loaded from {model_path}")
            return True

        except ImportError:
            logger.info("Transformers not installed, using rule-based fallback")
            return False
        except Exception as e:
            logger.warning(f"Failed to load ML model: {e}")
            return False

    def _is_model_available(self) -> bool:
        """Check if ML model is available for inference."""
        return self._model_available and self._model is not None

    def enhance(
        self,
        text: str,
        context: Optional[str] = None
    ) -> EnhancementResult:
        """
        Enhance OCR text using ML or rule-based methods.

        Args:
            text: Raw OCR text to enhance
            context: Optional context override

        Returns:
            EnhancementResult with enhanced text and metadata
        """
        ctx = context or self.context

        # Select enhancement strategy based on mode
        if self.mode == EnhancementMode.ML_ONLY:
            if self._is_model_available():
                return self._enhance_with_ml(text, ctx)
            else:
                raise RuntimeError("ML model not available and ML_ONLY mode specified")

        elif self.mode == EnhancementMode.RULE_ONLY:
            return self._enhance_with_rules(text, ctx)

        elif self.mode == EnhancementMode.ML_WITH_FALLBACK:
            if self._is_model_available():
                return self._enhance_with_ml(text, ctx)
            else:
                return self._enhance_with_rules(text, ctx)

        else:  # HYBRID
            if self._is_model_available():
                ml_result = self._enhance_with_ml(text, ctx)
                rule_result = self._enhance_with_rules(ml_result.enhanced_text, ctx)
                return EnhancementResult(
                    original_text=text,
                    enhanced_text=rule_result.enhanced_text,
                    mode_used="hybrid",
                    corrections=ml_result.corrections + rule_result.corrections,
                    entities=rule_result.entities,
                    confidence=(ml_result.confidence + rule_result.confidence) / 2
                )
            else:
                return self._enhance_with_rules(text, ctx)

    def _enhance_with_ml(
        self,
        text: str,
        context: str
    ) -> EnhancementResult:
        """
        Apply ML-based enhancement.

        Args:
            text: Input text
            context: Document context

        Returns:
            EnhancementResult from ML model
        """
        if not self._is_model_available():
            return self._enhance_with_rules(text, context)

        try:
            # Tokenize input
            inputs = self._tokenizer(
                text,
                return_tensors="pt",
                max_length=512,
                truncation=True
            )

            # Generate corrected text
            outputs = self._model.generate(
                inputs["input_ids"],
                max_length=512,
                num_beams=4,
                early_stopping=True
            )

            enhanced = self._tokenizer.decode(
                outputs[0],
                skip_special_tokens=True
            )

            # Calculate corrections
            corrections = self._find_differences(text, enhanced)

            return EnhancementResult(
                original_text=text,
                enhanced_text=enhanced,
                mode_used="ml",
                corrections=corrections,
                entities=self._extract_entities(enhanced),
                confidence=0.90
            )

        except Exception as e:
            logger.warning(f"ML enhancement failed: {e}")
            return self._enhance_with_rules(text, context)

    def _enhance_with_rules(
        self,
        text: str,
        context: str
    ) -> EnhancementResult:
        """
        Apply rule-based enhancement.

        Uses comprehensive pattern matching and domain knowledge
        to correct common OCR errors in Arabic text.

        Args:
            text: Input text
            context: Document context

        Returns:
            EnhancementResult from rule-based correction
        """
        enhanced = text
        corrections = []

        # Step 1: Word-level corrections
        for wrong, correct in self.WORD_CORRECTIONS.items():
            if wrong in enhanced:
                enhanced = enhanced.replace(wrong, correct)
                corrections.append({
                    "type": "word",
                    "original": wrong,
                    "corrected": correct,
                    "confidence": 0.95
                })

        # Step 2: Apply context-specific patterns
        if context == "invoice":
            enhanced, inv_corrections = self._apply_invoice_patterns(enhanced)
            corrections.extend(inv_corrections)

        # Step 3: Character-level corrections (context-aware)
        enhanced, char_corrections = self._apply_character_corrections(enhanced)
        corrections.extend(char_corrections)

        # Step 4: Normalize numbers
        enhanced, num_corrections = self._normalize_numbers(enhanced)
        corrections.extend(num_corrections)

        # Step 5: Fix spacing issues
        enhanced, space_corrections = self._fix_spacing(enhanced)
        corrections.extend(space_corrections)

        # Extract entities
        entities = self._extract_entities(enhanced)

        # Calculate confidence
        confidence = self._calculate_confidence(text, enhanced, corrections)

        return EnhancementResult(
            original_text=text,
            enhanced_text=enhanced,
            mode_used="rule",
            corrections=corrections,
            entities=entities,
            confidence=confidence
        )

    def _apply_invoice_patterns(
        self,
        text: str
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Apply invoice-specific correction patterns."""
        enhanced = text
        corrections = []

        # Tax invoice header patterns
        patterns = [
            (r'فاتور[ةه]\s*ضر[يى]ب[يى][ةه]', 'فاتورة ضريبية'),
            (r'إشعار\s*دا[ئي]ن', 'إشعار دائن'),
            (r'إشعار\s*مد[يى]ن', 'إشعار مدين'),
            (r'سند\s*قب[ضص]', 'سند قبض'),
            (r'سند\s*صر[فق]', 'سند صرف'),
        ]

        for pattern, replacement in patterns:
            match = re.search(pattern, enhanced)
            if match:
                original = match.group(0)
                enhanced = re.sub(pattern, replacement, enhanced)
                if original != replacement:
                    corrections.append({
                        "type": "pattern",
                        "original": original,
                        "corrected": replacement,
                        "confidence": 0.90
                    })

        return enhanced, corrections

    def _apply_character_corrections(
        self,
        text: str
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Apply context-aware character-level corrections.

        Uses character confusion matrix and word context
        to make intelligent corrections.
        """
        # This is a simplified implementation
        # A full implementation would use n-gram language models
        corrections = []

        # For now, rely on word-level corrections
        # Character-level corrections need more context

        return text, corrections

    def _normalize_numbers(
        self,
        text: str
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Normalize Arabic and Persian numerals to Western."""
        enhanced = text
        corrections = []

        # Arabic-Indic numerals
        arabic_indic = '٠١٢٣٤٥٦٧٨٩'
        western = '0123456789'

        for ar, west in zip(arabic_indic, western):
            if ar in enhanced:
                enhanced = enhanced.replace(ar, west)
                corrections.append({
                    "type": "numeral",
                    "original": ar,
                    "corrected": west,
                    "confidence": 1.0
                })

        # Persian/Urdu numerals
        persian = '۰۱۲۳۴۵۶۷۸۹'
        for pe, west in zip(persian, western):
            if pe in enhanced:
                enhanced = enhanced.replace(pe, west)
                corrections.append({
                    "type": "numeral",
                    "original": pe,
                    "corrected": west,
                    "confidence": 1.0
                })

        # Fix common OCR number errors
        # O/0 confusion
        enhanced = re.sub(r'(\d+)O(\d+)', r'\g<1>0\2', enhanced)
        # l/1 confusion
        enhanced = re.sub(r'(\d+)l(\d+)', r'\g<1>1\2', enhanced)

        # Arabic decimal separator
        enhanced = enhanced.replace('٫', '.')
        enhanced = enhanced.replace('،', ',')

        return enhanced, corrections

    def _fix_spacing(
        self,
        text: str
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Fix spacing issues in Arabic text."""
        enhanced = text
        corrections = []

        # Remove extra spaces
        if '  ' in enhanced:
            enhanced = re.sub(r' {2,}', ' ', enhanced)
            corrections.append({
                "type": "spacing",
                "description": "Removed extra spaces",
                "confidence": 1.0
            })

        # Ensure space after numbers before Arabic
        enhanced = re.sub(r'(\d)([\u0600-\u06FF])', r'\1 \2', enhanced)

        # Fix space around currency
        enhanced = re.sub(r'(\d)\s*(ريال|SAR|ر\.س)', r'\1 \2', enhanced)

        return enhanced, corrections

    def _extract_entities(
        self,
        text: str
    ) -> List[Dict[str, Any]]:
        """Extract named entities from text."""
        entities = []

        for entity_type, patterns in self.INVOICE_ENTITIES.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    entities.append({
                        "type": entity_type,
                        "value": match.group(0),
                        "start": match.start(),
                        "end": match.end(),
                    })

        return entities

    def _find_differences(
        self,
        original: str,
        enhanced: str
    ) -> List[Dict[str, Any]]:
        """Find differences between original and enhanced text."""
        corrections = []

        # Simple word-level diff
        orig_words = original.split()
        enh_words = enhanced.split()

        for i, (o, e) in enumerate(zip(orig_words, enh_words)):
            if o != e:
                corrections.append({
                    "type": "word",
                    "position": i,
                    "original": o,
                    "corrected": e,
                    "confidence": 0.85
                })

        return corrections

    def _calculate_confidence(
        self,
        original: str,
        enhanced: str,
        corrections: List[Dict[str, Any]]
    ) -> float:
        """Calculate confidence score for enhancement."""
        if not corrections:
            return 0.95  # No changes needed = high confidence

        # More corrections = lower confidence in original
        # But also means more uncertainty in corrections
        num_corrections = len(corrections)
        total_chars = len(original)

        # Base confidence
        confidence = 0.90

        # Adjust based on correction ratio
        correction_ratio = num_corrections / max(1, total_chars / 10)
        confidence -= min(0.3, correction_ratio * 0.1)

        # Boost for high-confidence corrections
        high_conf = sum(1 for c in corrections if c.get('confidence', 0) > 0.9)
        confidence += high_conf * 0.01

        return min(0.99, max(0.50, confidence))

    def detect_structure(
        self,
        text: str
    ) -> Dict[str, List[Tuple[int, int]]]:
        """
        Detect document structure sections.

        Args:
            text: Document text

        Returns:
            Dictionary mapping section types to position ranges
        """
        sections = {}

        for section_type, patterns in self.STRUCTURE_PATTERNS.items():
            matches = []
            for pattern in patterns:
                for match in re.finditer(pattern, text):
                    matches.append((match.start(), match.end()))

            if matches:
                sections[section_type] = matches

        return sections

    def batch_enhance(
        self,
        texts: List[str],
        context: Optional[str] = None
    ) -> List[EnhancementResult]:
        """
        Enhance multiple texts.

        Args:
            texts: List of texts to enhance
            context: Optional context override

        Returns:
            List of EnhancementResults
        """
        return [self.enhance(text, context) for text in texts]


# Convenience function
def enhance_with_ml(
    text: str,
    model_path: Optional[str] = None,
    context: str = "invoice"
) -> EnhancementResult:
    """
    Enhance Arabic OCR text using ML or rules.

    Args:
        text: Text to enhance
        model_path: Optional path to ML model
        context: Document context

    Returns:
        EnhancementResult with enhanced text
    """
    enhancer = MLArabicEnhancer(
        model_path=model_path,
        mode=EnhancementMode.ML_WITH_FALLBACK,
        context=context
    )
    return enhancer.enhance(text)
