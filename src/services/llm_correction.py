"""
ERP Arabic OCR Microservice - LLM Correction Service
=====================================================
Implements LLM-based post-correction for Arabic OCR output.
"""

import time
import logging
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from . import CorrectionResult
from config.settings import get_settings

logger = logging.getLogger(__name__)


# Arabic OCR correction prompt template
ARABIC_OCR_CORRECTION_PROMPT = """أنت مصحح نصوص عربية متخصص في تصحيح مخرجات التعرف الضوئي على الحروف (OCR).

المهمة: صحح النص العربي التالي الذي تم استخراجه من صورة فاتورة/مستند.

قواعد التصحيح:
1. صحح أخطاء الحروف المنقطة (ب، ت، ث، ن، ي، ج، ح، خ، ف، ق)
2. صحح أخطاء "ال" التعريف
3. فصل الكلمات الملتصقة
4. صحح الأخطاء الإملائية الشائعة
5. حافظ على الأرقام والتواريخ كما هي
6. لا تضف كلمات جديدة غير موجودة في النص الأصلي
7. لا تغير المعنى العام للنص

النص الأصلي:
{text}

أعد النص المصحح فقط بدون أي شرح أو تعليق:"""


ENGLISH_OCR_CORRECTION_PROMPT = """You are a specialized OCR text corrector.

Task: Correct the following text extracted from an invoice/document image.

Correction rules:
1. Fix common OCR character confusions (0/O, 1/l/I, etc.)
2. Fix word boundaries and spacing
3. Correct obvious spelling errors
4. Preserve numbers and dates exactly
5. Do not add words not present in the original
6. Maintain the overall meaning

Original text:
{text}

Return only the corrected text without any explanation:"""


BILINGUAL_OCR_CORRECTION_PROMPT = """You are a specialized bilingual (Arabic/English) OCR text corrector.

Task: Correct the following mixed Arabic/English text from an invoice.

Rules:
- Arabic: Fix dotted letter errors (ب،ت،ث،ن،ي), "ال" prefix issues, merged words
- English: Fix OCR character confusions (0/O, 1/l/I)
- Preserve all numbers, dates, and amounts exactly
- Separate merged words
- Do not add new content

Original text:
{text}

Return only the corrected text:"""


@dataclass
class LLMConfig:
    """LLM API configuration."""
    api_url: str
    api_key: str
    model: str
    max_tokens: int
    temperature: float
    timeout: int


class LLMCorrectionService:
    """
    LLM-based Arabic OCR correction service.

    Features:
    - OpenAI-compatible API support
    - Arabic-specific correction prompts
    - Batch processing
    - Confidence scoring
    - Fallback handling
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize LLM correction service.

        Args:
            api_url: OpenAI-compatible API URL
            api_key: API key
            model: Model name to use
        """
        settings = get_settings()

        self.config = LLMConfig(
            api_url=api_url or settings.llm.api_url,
            api_key=api_key or settings.llm.api_key,
            model=model or settings.llm.model,
            max_tokens=settings.llm.max_tokens,
            temperature=settings.llm.temperature,
            timeout=settings.llm.timeout
        )

        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize OpenAI client."""
        if not self.config.api_key:
            logger.warning("LLM API key not configured")
            return

        try:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.api_url,
                timeout=self.config.timeout
            )
            logger.info(f"LLM client initialized: {self.config.model}")

        except ImportError:
            logger.warning("OpenAI package not installed")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")

    def correct(
        self,
        text: str,
        language: str = "ar",
        context: Optional[str] = None
    ) -> CorrectionResult:
        """
        Correct OCR text using LLM.

        Args:
            text: OCR text to correct
            language: Language code (ar, en, mixed)
            context: Optional context for correction

        Returns:
            CorrectionResult with corrected text
        """
        start_time = time.time()

        if not text or not text.strip():
            return CorrectionResult(
                original=text,
                corrected=text,
                correction_type="llm",
                processing_time_ms=0
            )

        if self._client is None:
            logger.warning("LLM client not available, returning original text")
            return CorrectionResult(
                original=text,
                corrected=text,
                corrections_made=[{"error": "LLM not available"}],
                confidence=0.0,
                correction_type="llm",
                processing_time_ms=(time.time() - start_time) * 1000
            )

        try:
            # Build prompt
            prompt = self._build_prompt(text, language, context)

            # Call LLM API
            response = self._client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": "You are an expert OCR text corrector."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )

            # Parse response
            corrected_text = self._parse_response(response)

            # Calculate corrections made
            corrections = self._identify_corrections(text, corrected_text)

            # Calculate confidence
            confidence = self._calculate_confidence(text, corrected_text, corrections)

            return CorrectionResult(
                original=text,
                corrected=corrected_text,
                corrections_made=corrections,
                confidence=confidence,
                correction_type="llm",
                processing_time_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            logger.error(f"LLM correction failed: {e}")
            return CorrectionResult(
                original=text,
                corrected=text,
                corrections_made=[{"error": str(e)}],
                confidence=0.0,
                correction_type="llm",
                processing_time_ms=(time.time() - start_time) * 1000
            )

    def correct_batch(
        self,
        texts: List[str],
        language: str = "ar"
    ) -> List[CorrectionResult]:
        """
        Correct multiple texts in batch.

        Args:
            texts: List of texts to correct
            language: Language code

        Returns:
            List of CorrectionResults
        """
        results = []

        for text in texts:
            result = self.correct(text, language)
            results.append(result)

        return results

    def _build_prompt(
        self,
        text: str,
        language: str,
        context: Optional[str] = None
    ) -> str:
        """
        Build correction prompt based on language.

        Args:
            text: Text to correct
            language: Language code
            context: Optional context

        Returns:
            Formatted prompt
        """
        # Select template
        if language == "ar":
            template = ARABIC_OCR_CORRECTION_PROMPT
        elif language == "en":
            template = ENGLISH_OCR_CORRECTION_PROMPT
        else:
            template = BILINGUAL_OCR_CORRECTION_PROMPT

        prompt = template.format(text=text)

        # Add context if provided
        if context:
            prompt = f"Document context: {context}\n\n{prompt}"

        return prompt

    def _parse_response(self, response) -> str:
        """
        Parse LLM response to extract corrected text.

        Args:
            response: OpenAI API response

        Returns:
            Extracted corrected text
        """
        if not response.choices:
            return ""

        content = response.choices[0].message.content

        if not content:
            return ""

        # Clean up response
        # Remove any explanatory text or prefixes
        lines = content.strip().split('\n')

        # Filter out lines that look like explanations
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            # Skip empty lines and explanation markers
            if not line:
                continue
            if line.startswith(('Note:', 'ملاحظة:', 'Explanation:', 'التصحيح:', 'الناتج:')):
                continue
            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def _identify_corrections(
        self,
        original: str,
        corrected: str
    ) -> List[Dict[str, str]]:
        """
        Identify specific corrections made.

        Args:
            original: Original text
            corrected: Corrected text

        Returns:
            List of correction records
        """
        corrections = []

        # Simple word-level diff
        original_words = original.split()
        corrected_words = corrected.split()

        # Use sequence matching for alignment
        from difflib import SequenceMatcher

        matcher = SequenceMatcher(None, original_words, corrected_words)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                orig = ' '.join(original_words[i1:i2])
                corr = ' '.join(corrected_words[j1:j2])
                corrections.append({
                    "type": "replace",
                    "original": orig,
                    "corrected": corr,
                    "position": i1
                })
            elif tag == 'delete':
                orig = ' '.join(original_words[i1:i2])
                corrections.append({
                    "type": "delete",
                    "original": orig,
                    "position": i1
                })
            elif tag == 'insert':
                corr = ' '.join(corrected_words[j1:j2])
                corrections.append({
                    "type": "insert",
                    "corrected": corr,
                    "position": i1
                })

        return corrections

    def _calculate_confidence(
        self,
        original: str,
        corrected: str,
        corrections: List[Dict[str, str]]
    ) -> float:
        """
        Calculate confidence score for corrections.

        Higher confidence when:
        - Fewer changes made
        - Changes are small (1-2 characters)
        - Text structure preserved

        Args:
            original: Original text
            corrected: Corrected text
            corrections: List of corrections made

        Returns:
            Confidence score (0.0-1.0)
        """
        if original == corrected:
            return 1.0

        if not original or not corrected:
            return 0.5

        # Base confidence
        confidence = 0.9

        # Penalize based on number of corrections
        correction_count = len(corrections)
        word_count = len(original.split())

        if word_count > 0:
            correction_ratio = correction_count / word_count
            confidence -= correction_ratio * 0.3

        # Penalize large changes
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, original, corrected).ratio()
        if similarity < 0.8:
            confidence -= (0.8 - similarity) * 0.5

        # Ensure bounds
        return max(0.1, min(1.0, confidence))

    def is_available(self) -> bool:
        """Check if LLM service is available."""
        return self._client is not None

    def get_status(self) -> Dict[str, any]:
        """Get service status."""
        return {
            "available": self.is_available(),
            "model": self.config.model,
            "api_url": self.config.api_url[:50] + "..." if len(self.config.api_url) > 50 else self.config.api_url
        }


class HybridCorrectionService:
    """
    Hybrid correction combining rule-based and LLM correction.

    Strategy:
    1. Apply rule-based Arabic corrections first
    2. Apply LLM correction for remaining errors
    3. Validate LLM changes against rules
    """

    def __init__(self):
        """Initialize hybrid correction service."""
        self.llm_service = LLMCorrectionService()

    def correct(
        self,
        text: str,
        use_llm: bool = True
    ) -> CorrectionResult:
        """
        Apply hybrid correction.

        Args:
            text: Text to correct
            use_llm: Whether to use LLM correction

        Returns:
            CorrectionResult with all corrections
        """
        start_time = time.time()
        all_corrections = []

        # Step 1: Rule-based Arabic correction
        from ..utils.arabic_utils import advanced_arabic_ocr_correction
        rule_corrected = advanced_arabic_ocr_correction(text)

        if rule_corrected != text:
            all_corrections.append({
                "type": "rule_based",
                "stage": 1
            })

        # Step 2: LLM correction (if enabled and available)
        final_text = rule_corrected

        if use_llm and self.llm_service.is_available():
            llm_result = self.llm_service.correct(rule_corrected)

            if llm_result.was_modified:
                # Validate LLM changes
                if self._validate_llm_changes(rule_corrected, llm_result.corrected):
                    final_text = llm_result.corrected
                    all_corrections.extend(llm_result.corrections_made)

        return CorrectionResult(
            original=text,
            corrected=final_text,
            corrections_made=all_corrections,
            confidence=0.95 if final_text != text else 1.0,
            correction_type="hybrid",
            processing_time_ms=(time.time() - start_time) * 1000
        )

    def _validate_llm_changes(
        self,
        original: str,
        corrected: str
    ) -> bool:
        """
        Validate LLM changes are reasonable.

        Rejects changes that:
        - Remove too much content
        - Change numbers/dates
        - Alter meaning significantly

        Args:
            original: Original text
            corrected: LLM-corrected text

        Returns:
            True if changes are valid
        """
        # Check content preservation
        if len(corrected) < len(original) * 0.5:
            logger.warning("LLM removed too much content")
            return False

        # Check numbers preserved
        original_numbers = re.findall(r'\d+', original)
        corrected_numbers = re.findall(r'\d+', corrected)

        if original_numbers != corrected_numbers:
            logger.warning("LLM changed numbers")
            return False

        return True


# Export
__all__ = [
    "LLMCorrectionService",
    "HybridCorrectionService",
    "ARABIC_OCR_CORRECTION_PROMPT",
    "ENGLISH_OCR_CORRECTION_PROMPT",
    "BILINGUAL_OCR_CORRECTION_PROMPT"
]
