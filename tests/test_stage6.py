"""
Stage 6 Tests - Advanced Features
(ARABIC_OCR_ENHANCEMENT_IMPLEMENTATION_PLAN.md)

Tests for:
- MLArabicEnhancer (ML-based OCR enhancement with rule fallback)
- TemplateLearner (Invoice template learning)
- PaddleEngine Stage 6 integration
"""

import pytest
import os
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


class TestMLArabicEnhancer:
    """Test the MLArabicEnhancer for ML/rule-based text enhancement."""

    @pytest.fixture
    def enhancer(self):
        """Create MLArabicEnhancer instance."""
        from src.ml.arabic_ocr_enhancer import MLArabicEnhancer, EnhancementMode
        return MLArabicEnhancer(
            mode=EnhancementMode.RULE_ONLY,
            context="invoice"
        )

    def test_enhancer_initialization(self, enhancer):
        """Test enhancer initializes correctly."""
        assert enhancer.context == "invoice"
        assert enhancer._model_available is False

    def test_word_corrections(self, enhancer):
        """Test word-level OCR corrections."""
        # Common OCR errors
        test_cases = [
            ("الضرية", "الضريبة"),
            ("الفانورة", "الفاتورة"),
            ("المجووع", "المجموع"),
            ("الاجمالى", "الإجمالي"),
            ("الكويه", "الكمية"),
            ("السهر", "السعر"),
        ]

        for wrong, expected in test_cases:
            result = enhancer.enhance(wrong)
            assert expected in result.enhanced_text, f"Expected '{expected}' in '{result.enhanced_text}'"

    def test_arabic_numeral_conversion(self, enhancer):
        """Test Arabic-Indic to Western numeral conversion."""
        result = enhancer.enhance("المجموع ١٢٣٤٥")

        assert "12345" in result.enhanced_text
        assert any(c['type'] == 'numeral' for c in result.corrections)

    def test_persian_numeral_conversion(self, enhancer):
        """Test Persian/Urdu numeral conversion."""
        result = enhancer.enhance("الرقم ۱۲۳")

        assert "123" in result.enhanced_text

    def test_enhancement_result_structure(self, enhancer):
        """Test EnhancementResult structure."""
        result = enhancer.enhance("الفانورة الضرية")

        assert hasattr(result, 'original_text')
        assert hasattr(result, 'enhanced_text')
        assert hasattr(result, 'mode_used')
        assert hasattr(result, 'corrections')
        assert hasattr(result, 'entities')
        assert hasattr(result, 'confidence')

    def test_enhancement_result_to_dict(self, enhancer):
        """Test EnhancementResult serialization."""
        result = enhancer.enhance("الفانورة")

        result_dict = result.to_dict()

        assert 'original' in result_dict
        assert 'enhanced' in result_dict
        assert 'mode' in result_dict
        assert 'corrections' in result_dict

    def test_entity_extraction(self, enhancer):
        """Test named entity extraction."""
        text = "الرقم الضريبي 300123456789012 التاريخ 2024-01-15"
        result = enhancer.enhance(text)

        # Should extract tax number and date
        entity_types = [e['type'] for e in result.entities]
        assert 'TAX_NUMBER' in entity_types or 'DATE' in entity_types

    def test_phone_entity_extraction(self, enhancer):
        """Test phone number entity extraction."""
        text = "هاتف 0501234567"
        result = enhancer.enhance(text)

        phone_entities = [e for e in result.entities if e['type'] == 'PHONE']
        assert len(phone_entities) > 0

    def test_invoice_number_extraction(self, enhancer):
        """Test invoice number entity extraction."""
        text = "فاتورة INV-2024-001"
        result = enhancer.enhance(text)

        inv_entities = [e for e in result.entities if e['type'] == 'INVOICE_NUMBER']
        assert len(inv_entities) > 0

    def test_structure_detection(self, enhancer):
        """Test document structure detection."""
        text = """
        فاتورة ضريبية
        المورد: شركة أ ب ج
        الرقم الضريبي: 300123456789012
        البنود والأصناف
        المجموع: 1000 ريال
        """

        sections = enhancer.detect_structure(text)

        assert 'header' in sections or 'vendor_section' in sections

    def test_batch_enhance(self, enhancer):
        """Test batch text enhancement."""
        texts = ["الفانورة", "الضرية", "المجووع"]

        results = enhancer.batch_enhance(texts)

        assert len(results) == 3
        assert all(hasattr(r, 'enhanced_text') for r in results)

    def test_ml_with_fallback_mode(self):
        """Test ML_WITH_FALLBACK mode falls back to rules."""
        from src.ml.arabic_ocr_enhancer import MLArabicEnhancer, EnhancementMode

        enhancer = MLArabicEnhancer(
            mode=EnhancementMode.ML_WITH_FALLBACK,
            context="invoice"
        )

        result = enhancer.enhance("الفانورة")

        assert result.mode_used == "rule"  # Should fall back
        assert "الفاتورة" in result.enhanced_text

    def test_spacing_fixes(self, enhancer):
        """Test spacing issue corrections."""
        text = "المجموع  100  ريال"  # Extra spaces
        result = enhancer.enhance(text)

        # Should not have double spaces
        assert "  " not in result.enhanced_text

    def test_confidence_calculation(self, enhancer):
        """Test confidence score calculation."""
        result = enhancer.enhance("الفانورة الضرية")

        assert 0.0 <= result.confidence <= 1.0

    def test_no_changes_needed(self, enhancer):
        """Test text that needs no correction."""
        text = "فاتورة ضريبية"  # Correct text
        result = enhancer.enhance(text)

        assert result.enhanced_text == text
        assert result.confidence >= 0.9


class TestTemplateLearner:
    """Test the TemplateLearner for invoice template learning."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for templates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def learner(self, temp_dir):
        """Create TemplateLearner instance."""
        from src.learning.template_learner import TemplateLearner
        return TemplateLearner(
            templates_dir=temp_dir,
            auto_save=False
        )

    @pytest.fixture
    def sample_invoice(self):
        """Sample invoice data for testing."""
        return {
            'vendor': {
                'name': 'Test Vendor',
                'name_ar': 'مورد اختبار',
                'tax_number': '300123456789012',
            },
            'invoice': {
                'reference_number': 'INV-2024-001',
                'date': '2024-01-15',
            },
            'line_items': [
                {'description': 'Item 1', 'quantity': 1, 'unit_price': 100}
            ],
            'totals': {
                'subtotal': 100,
                'tax_amount': 15,
                'total': 115,
            }
        }

    def test_learner_initialization(self, learner):
        """Test learner initializes correctly."""
        assert learner.templates == {}
        assert learner.auto_save is False

    def test_learn_from_document(self, learner, sample_invoice):
        """Test learning from processed document."""
        template_id = learner.learn_from_document(sample_invoice)

        assert template_id is not None
        assert template_id in learner.templates

    def test_template_fields_extraction(self, learner, sample_invoice):
        """Test field extraction during learning."""
        template_id = learner.learn_from_document(sample_invoice)
        template = learner.templates[template_id]

        assert 'vendor.tax_number' in template.fields
        assert 'invoice.reference_number' in template.fields
        assert 'totals.total' in template.fields

    def test_template_update(self, learner, sample_invoice):
        """Test template update with new document."""
        # Learn first time
        template_id = learner.learn_from_document(sample_invoice)
        template1 = learner.templates[template_id]
        assert template1.sample_count == 1

        # Learn second time
        learner.learn_from_document(sample_invoice)
        template2 = learner.templates[template_id]
        assert template2.sample_count == 2

    def test_find_matching_template(self, learner, sample_invoice):
        """Test finding matching template."""
        learner.learn_from_document(sample_invoice)

        match = learner.find_matching_template(sample_invoice)

        assert match.template is not None
        assert match.match_score == 1.0  # Exact tax number match

    def test_no_template_match(self, learner):
        """Test when no template matches."""
        invoice = {
            'vendor': {'name': 'Unknown Vendor'},
            'totals': {'total': 100}
        }

        match = learner.find_matching_template(invoice)

        assert match.template is None or match.match_score < 0.5

    def test_generate_hints(self, learner, sample_invoice):
        """Test hint generation from template."""
        learner.learn_from_document(sample_invoice)

        match = learner.find_matching_template(sample_invoice)

        assert match.hints is not None
        assert len(match.hints) > 0

    def test_template_stats(self, learner, sample_invoice):
        """Test template statistics."""
        learner.learn_from_document(sample_invoice)

        stats = learner.get_template_stats()

        assert stats['count'] == 1
        assert stats['total_samples'] == 1

    def test_save_and_load_templates(self, temp_dir):
        """Test template persistence."""
        from src.learning.template_learner import TemplateLearner

        # Create and save
        learner1 = TemplateLearner(templates_dir=temp_dir, auto_save=True)
        learner1.learn_from_document({
            'vendor': {'tax_number': '300123456789012', 'name': 'Test'},
            'totals': {'total': 100}
        })

        # Create new learner and load
        learner2 = TemplateLearner(templates_dir=temp_dir, auto_save=False)

        assert len(learner2.templates) == 1

    def test_export_templates(self, learner, sample_invoice, temp_dir):
        """Test template export."""
        learner.learn_from_document(sample_invoice)

        export_path = os.path.join(temp_dir, "export.json")
        learner.export_templates(export_path)

        assert os.path.exists(export_path)

        with open(export_path, 'r') as f:
            data = json.load(f)
            assert len(data) == 1

    def test_import_templates(self, temp_dir, sample_invoice):
        """Test template import."""
        from src.learning.template_learner import TemplateLearner

        # Create and export
        learner1 = TemplateLearner(templates_dir=temp_dir, auto_save=False)
        learner1.learn_from_document(sample_invoice)
        export_path = os.path.join(temp_dir, "export.json")
        learner1.export_templates(export_path)

        # Import to new learner
        import_dir = os.path.join(temp_dir, "import")
        os.makedirs(import_dir)
        learner2 = TemplateLearner(templates_dir=import_dir, auto_save=False)
        learner2.import_templates(export_path)

        assert len(learner2.templates) == 1

    def test_clear_templates(self, learner, sample_invoice):
        """Test clearing all templates."""
        learner.learn_from_document(sample_invoice)
        assert len(learner.templates) == 1

        learner.clear_templates()
        assert len(learner.templates) == 0

    def test_remove_template(self, learner, sample_invoice):
        """Test removing specific template."""
        template_id = learner.learn_from_document(sample_invoice)

        result = learner.remove_template(template_id)

        assert result is True
        assert template_id not in learner.templates

    def test_template_confidence_increases(self, learner, sample_invoice):
        """Test that confidence increases with more samples."""
        learner.learn_from_document(sample_invoice)
        template_id = list(learner.templates.keys())[0]
        conf1 = learner.templates[template_id].confidence_score

        # Add more samples
        for _ in range(3):
            learner.learn_from_document(sample_invoice)

        conf2 = learner.templates[template_id].confidence_score
        assert conf2 > conf1

    def test_no_learning_without_tax_number(self, learner):
        """Test that learning requires tax number."""
        invoice = {
            'vendor': {'name': 'Unknown Vendor'},
            'totals': {'total': 100}
        }

        template_id = learner.learn_from_document(invoice)

        assert template_id is None


class TestPaddleEngineStage6Integration:
    """Test Stage 6 integration in PaddleEngine."""

    @pytest.fixture
    def engine(self):
        """Create PaddleEngine instance for testing."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine.__new__(PaddleEngine)
        engine._lang = 'ar'
        engine._use_gpu = False
        engine._use_angle_cls = True
        engine._use_server_model = False
        engine._ocr_engines = {}
        engine._available = None
        return engine

    def test_get_ml_enhancer_lazy_loading(self, engine):
        """Test lazy loading of MLArabicEnhancer."""
        enhancer = engine._get_ml_enhancer()

        assert enhancer is not None
        assert hasattr(enhancer, 'enhance')

    def test_get_template_learner_lazy_loading(self, engine):
        """Test lazy loading of TemplateLearner."""
        learner = engine._get_template_learner()

        assert learner is not None
        assert hasattr(learner, 'learn_from_document')

    def test_enhance_text_with_ml_method(self, engine):
        """Test enhance_text_with_ml method."""
        result = engine.enhance_text_with_ml("الفانورة")

        assert result is not None
        assert hasattr(result, 'enhanced_text')
        assert "الفاتورة" in result.enhanced_text

    def test_learn_template_method(self, engine):
        """Test learn_template method."""
        invoice_data = {
            'vendor': {'tax_number': '300123456789999', 'name': 'Test'},
            'totals': {'total': 100}
        }

        template_id = engine.learn_template(invoice_data)

        assert template_id is not None

    def test_get_template_hints_method(self, engine):
        """Test get_template_hints method."""
        invoice_data = {
            'vendor': {'tax_number': '300123456789999', 'name': 'Test'},
            'totals': {'total': 100}
        }

        # Learn first
        engine.learn_template(invoice_data)

        # Get hints
        hints = engine.get_template_hints(invoice_data)

        assert hints is not None
        assert 'template_id' in hints

    def test_get_template_stats_method(self, engine):
        """Test get_template_stats method."""
        stats = engine.get_template_stats()

        assert 'count' in stats
        assert 'available' in stats


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_enhance_with_ml_function(self):
        """Test enhance_with_ml convenience function."""
        from src.ml.arabic_ocr_enhancer import enhance_with_ml

        result = enhance_with_ml("الفانورة")

        assert result is not None
        assert "الفاتورة" in result.enhanced_text


class TestEnhancementModes:
    """Test different enhancement modes."""

    def test_rule_only_mode(self):
        """Test RULE_ONLY mode."""
        from src.ml.arabic_ocr_enhancer import MLArabicEnhancer, EnhancementMode

        enhancer = MLArabicEnhancer(mode=EnhancementMode.RULE_ONLY)
        result = enhancer.enhance("الفانورة")

        assert result.mode_used == "rule"

    def test_ml_only_mode_without_model(self):
        """Test ML_ONLY mode raises error without model."""
        from src.ml.arabic_ocr_enhancer import MLArabicEnhancer, EnhancementMode

        enhancer = MLArabicEnhancer(mode=EnhancementMode.ML_ONLY)

        with pytest.raises(RuntimeError):
            enhancer.enhance("test")

    def test_hybrid_mode(self):
        """Test HYBRID mode (falls back to rules without ML)."""
        from src.ml.arabic_ocr_enhancer import MLArabicEnhancer, EnhancementMode

        enhancer = MLArabicEnhancer(mode=EnhancementMode.HYBRID)
        result = enhancer.enhance("الفانورة")

        # Without ML model, should use rules
        assert "rule" in result.mode_used


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_text_enhancement(self):
        """Test enhancement of empty text."""
        from src.ml.arabic_ocr_enhancer import MLArabicEnhancer

        enhancer = MLArabicEnhancer()
        result = enhancer.enhance("")

        assert result.enhanced_text == ""

    def test_english_text_enhancement(self):
        """Test enhancement of English text."""
        from src.ml.arabic_ocr_enhancer import MLArabicEnhancer

        enhancer = MLArabicEnhancer()
        result = enhancer.enhance("Invoice Total: 100")

        # Should not corrupt English text
        assert "Invoice" in result.enhanced_text

    def test_mixed_content_enhancement(self):
        """Test enhancement of mixed Arabic/English text."""
        from src.ml.arabic_ocr_enhancer import MLArabicEnhancer

        enhancer = MLArabicEnhancer()
        result = enhancer.enhance("الفانورة INV-001")

        assert "الفاتورة" in result.enhanced_text
        assert "INV-001" in result.enhanced_text

    def test_template_learner_with_invalid_data(self):
        """Test template learner with invalid data."""
        from src.learning.template_learner import TemplateLearner
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            learner = TemplateLearner(templates_dir=tmpdir, auto_save=False)

            # Empty data
            result = learner.learn_from_document({})
            assert result is None

    def test_template_matching_partial_data(self):
        """Test template matching with partial invoice data."""
        from src.learning.template_learner import TemplateLearner
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            learner = TemplateLearner(templates_dir=tmpdir, auto_save=False)

            # Learn full template
            learner.learn_from_document({
                'vendor': {'tax_number': '300111111111111', 'name': 'Test Vendor'},
                'invoice': {'reference_number': 'INV-001'},
                'totals': {'total': 100}
            })

            # Match with partial data
            match = learner.find_matching_template({
                'vendor': {'tax_number': '300111111111111'}
            })

            assert match.template is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
