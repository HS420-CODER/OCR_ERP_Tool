"""
Template Learning System - Stage 6, Step 6.2

Learn invoice templates from processed documents to improve
extraction accuracy over time.

Features:
- Auto-detect recurring patterns in invoices
- Store field locations for known vendors
- Apply learned templates to new documents
- Continuous improvement through feedback

This module enables the OCR system to learn from successfully
processed documents and apply that knowledge to improve
future extractions.
"""

import os
import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class FieldInfo:
    """Information about a field's location and characteristics."""
    field_name: str
    field_type: str  # 'text', 'number', 'date', 'currency'
    expected_region: List[float] = field(default_factory=list)  # [x1, y1, x2, y2] normalized
    label_patterns: List[str] = field(default_factory=list)  # Regex patterns for label
    value_patterns: List[str] = field(default_factory=list)  # Regex patterns for value
    relative_position: str = ""  # 'header', 'body', 'footer'
    occurrence_count: int = 0
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FieldInfo':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class InvoiceTemplate:
    """Template for a specific invoice format/vendor."""
    template_id: str
    vendor_tax_number: str = ""
    vendor_name: str = ""
    document_type: str = "invoice"
    fields: Dict[str, FieldInfo] = field(default_factory=dict)
    layout_signature: str = ""  # Hash of layout characteristics
    sample_count: int = 0
    last_updated: str = ""
    confidence_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "template_id": self.template_id,
            "vendor_tax_number": self.vendor_tax_number,
            "vendor_name": self.vendor_name,
            "document_type": self.document_type,
            "fields": {k: v.to_dict() for k, v in self.fields.items()},
            "layout_signature": self.layout_signature,
            "sample_count": self.sample_count,
            "last_updated": self.last_updated,
            "confidence_score": self.confidence_score,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InvoiceTemplate':
        """Create from dictionary."""
        fields = {}
        for k, v in data.get("fields", {}).items():
            fields[k] = FieldInfo.from_dict(v)

        return cls(
            template_id=data.get("template_id", ""),
            vendor_tax_number=data.get("vendor_tax_number", ""),
            vendor_name=data.get("vendor_name", ""),
            document_type=data.get("document_type", "invoice"),
            fields=fields,
            layout_signature=data.get("layout_signature", ""),
            sample_count=data.get("sample_count", 0),
            last_updated=data.get("last_updated", ""),
            confidence_score=data.get("confidence_score", 0.0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class TemplateMatch:
    """Result of template matching."""
    template: Optional[InvoiceTemplate]
    match_score: float
    matched_fields: List[str] = field(default_factory=list)
    hints: Dict[str, Any] = field(default_factory=dict)
    confidence_boost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "template_id": self.template.template_id if self.template else None,
            "match_score": self.match_score,
            "matched_fields": self.matched_fields,
            "hints": self.hints,
            "confidence_boost": self.confidence_boost,
        }


class TemplateLearner:
    """
    Learn invoice templates from processed documents.

    Features:
    - Auto-detect recurring patterns
    - Store field locations for known vendors
    - Improve extraction accuracy over time
    - Apply learned templates to new documents

    Usage:
        learner = TemplateLearner("data/templates")

        # Learn from processed document
        learner.learn_from_document(invoice_data, layout, ocr_result)

        # Apply template to new document
        hints = learner.apply_template(ocr_result, tax_number)
    """

    # Minimum samples needed for a template to be considered reliable
    MIN_SAMPLES_FOR_CONFIDENCE = 3

    # Maximum number of templates to store
    MAX_TEMPLATES = 1000

    # Field importance for template matching
    FIELD_WEIGHTS = {
        "vendor.tax_number": 1.0,
        "invoice.reference_number": 0.8,
        "totals.total": 0.9,
        "line_items": 0.7,
        "invoice.date": 0.6,
    }

    def __init__(
        self,
        templates_dir: str = "data/templates",
        auto_save: bool = True
    ):
        """
        Initialize the template learner.

        Args:
            templates_dir: Directory to store templates
            auto_save: Automatically save templates after learning
        """
        self.templates_dir = Path(templates_dir)
        self.auto_save = auto_save
        self.templates: Dict[str, InvoiceTemplate] = {}
        self._modified = False

        # Create directory if needed
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # Load existing templates
        self._load_templates()

    def _load_templates(self):
        """Load templates from disk."""
        templates_file = self.templates_dir / "templates.json"

        if templates_file.exists():
            try:
                with open(templates_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for template_id, template_data in data.items():
                    self.templates[template_id] = InvoiceTemplate.from_dict(template_data)

                logger.info(f"Loaded {len(self.templates)} templates from {templates_file}")

            except Exception as e:
                logger.error(f"Failed to load templates: {e}")

    def _save_templates(self):
        """Save templates to disk."""
        templates_file = self.templates_dir / "templates.json"

        try:
            data = {k: v.to_dict() for k, v in self.templates.items()}

            with open(templates_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"Saved {len(self.templates)} templates to {templates_file}")
            self._modified = False

        except Exception as e:
            logger.error(f"Failed to save templates: {e}")

    def learn_from_document(
        self,
        invoice_data: Dict[str, Any],
        layout: Optional[Any] = None,
        ocr_result: Optional[Any] = None,
        page_width: int = 0,
        page_height: int = 0
    ) -> Optional[str]:
        """
        Learn template from processed document.

        Args:
            invoice_data: Extracted invoice data
            layout: Optional DocumentLayout from layout analysis
            ocr_result: Optional OCR result with text blocks
            page_width: Page width for normalization
            page_height: Page height for normalization

        Returns:
            Template ID if learning successful, None otherwise
        """
        # Generate template key from vendor tax number
        vendor = invoice_data.get("vendor", {})
        tax_number = vendor.get("tax_number", "")

        if not tax_number:
            logger.debug("Cannot learn template without vendor tax number")
            return None

        # Generate template ID
        template_id = self._generate_template_id(tax_number)

        # Get or create template
        if template_id in self.templates:
            template = self.templates[template_id]
            self._update_template(template, invoice_data, layout, page_width, page_height)
        else:
            template = self._create_template(
                template_id, invoice_data, layout, page_width, page_height
            )
            self.templates[template_id] = template

        self._modified = True

        # Auto-save if enabled
        if self.auto_save:
            self._save_templates()

        return template_id

    def _generate_template_id(self, tax_number: str) -> str:
        """Generate template ID from tax number."""
        # Use hash for shorter ID
        hash_obj = hashlib.md5(tax_number.encode())
        return f"template_{hash_obj.hexdigest()[:12]}"

    def _create_template(
        self,
        template_id: str,
        invoice_data: Dict[str, Any],
        layout: Optional[Any],
        page_width: int,
        page_height: int
    ) -> InvoiceTemplate:
        """Create new template from document."""
        vendor = invoice_data.get("vendor", {})

        template = InvoiceTemplate(
            template_id=template_id,
            vendor_tax_number=vendor.get("tax_number", ""),
            vendor_name=vendor.get("name", vendor.get("name_ar", "")),
            document_type=invoice_data.get("document_type", "invoice"),
            sample_count=1,
            last_updated=datetime.now().isoformat(),
        )

        # Extract field information
        template.fields = self._extract_field_info(
            invoice_data, layout, page_width, page_height
        )

        # Generate layout signature
        template.layout_signature = self._generate_layout_signature(layout)

        # Calculate initial confidence
        template.confidence_score = 0.5  # Low confidence for single sample

        logger.info(f"Created new template {template_id} for vendor {template.vendor_name}")

        return template

    def _update_template(
        self,
        template: InvoiceTemplate,
        invoice_data: Dict[str, Any],
        layout: Optional[Any],
        page_width: int,
        page_height: int
    ):
        """Update existing template with new document."""
        # Extract new field info
        new_fields = self._extract_field_info(
            invoice_data, layout, page_width, page_height
        )

        # Merge with existing fields
        for field_name, field_info in new_fields.items():
            if field_name in template.fields:
                existing = template.fields[field_name]

                # Average the regions
                if field_info.expected_region and existing.expected_region:
                    existing.expected_region = self._average_regions(
                        existing.expected_region,
                        field_info.expected_region,
                        existing.occurrence_count
                    )

                # Merge patterns
                existing.label_patterns = list(set(
                    existing.label_patterns + field_info.label_patterns
                ))
                existing.value_patterns = list(set(
                    existing.value_patterns + field_info.value_patterns
                ))

                existing.occurrence_count += 1

                # Update confidence
                existing.confidence = min(0.95, 0.5 + 0.1 * existing.occurrence_count)

            else:
                template.fields[field_name] = field_info

        # Update template metadata
        template.sample_count += 1
        template.last_updated = datetime.now().isoformat()

        # Update confidence based on sample count
        template.confidence_score = min(
            0.95,
            0.5 + 0.15 * min(template.sample_count, self.MIN_SAMPLES_FOR_CONFIDENCE)
        )

        logger.debug(f"Updated template {template.template_id} (samples: {template.sample_count})")

    def _extract_field_info(
        self,
        invoice_data: Dict[str, Any],
        layout: Optional[Any],
        page_width: int,
        page_height: int
    ) -> Dict[str, FieldInfo]:
        """Extract field information from invoice data."""
        fields = {}

        # Define field mappings
        field_mappings = [
            ("vendor.tax_number", "vendor", "tax_number", "text"),
            ("vendor.name", "vendor", "name", "text"),
            ("invoice.reference_number", "invoice", "reference_number", "text"),
            ("invoice.date", "invoice", "date", "date"),
            ("totals.total", "totals", "total", "currency"),
            ("totals.subtotal", "totals", "subtotal", "currency"),
            ("totals.tax_amount", "totals", "tax_amount", "currency"),
        ]

        for field_path, section, key, field_type in field_mappings:
            section_data = invoice_data.get(section, {})
            value = section_data.get(key)

            if value:
                fields[field_path] = FieldInfo(
                    field_name=field_path,
                    field_type=field_type,
                    occurrence_count=1,
                    confidence=0.5,
                )

                # Try to determine relative position
                if "vendor" in field_path or "invoice" in field_path:
                    fields[field_path].relative_position = "header"
                elif "totals" in field_path:
                    fields[field_path].relative_position = "footer"
                else:
                    fields[field_path].relative_position = "body"

        # Handle line items
        if "line_items" in invoice_data and invoice_data["line_items"]:
            fields["line_items"] = FieldInfo(
                field_name="line_items",
                field_type="table",
                relative_position="body",
                occurrence_count=len(invoice_data["line_items"]),
                confidence=0.6,
            )

        return fields

    def _average_regions(
        self,
        region1: List[float],
        region2: List[float],
        weight1: int
    ) -> List[float]:
        """Average two regions with weighting."""
        if len(region1) != 4 or len(region2) != 4:
            return region1 or region2

        # Weighted average (existing region has more weight)
        total_weight = weight1 + 1
        return [
            (r1 * weight1 + r2) / total_weight
            for r1, r2 in zip(region1, region2)
        ]

    def _generate_layout_signature(self, layout: Optional[Any]) -> str:
        """Generate a signature representing the document layout."""
        if not layout:
            return ""

        # Create signature from layout characteristics
        sig_parts = []

        if hasattr(layout, 'zones'):
            zone_types = sorted([z.zone_type for z in layout.zones if hasattr(z, 'zone_type')])
            sig_parts.append(f"zones:{','.join(str(z) for z in zone_types)}")

        if hasattr(layout, 'num_columns'):
            sig_parts.append(f"cols:{layout.num_columns}")

        if hasattr(layout, 'header_zone'):
            sig_parts.append(f"header:{1 if layout.header_zone else 0}")

        if sig_parts:
            sig_str = "|".join(sig_parts)
            return hashlib.md5(sig_str.encode()).hexdigest()[:8]

        return ""

    def find_matching_template(
        self,
        invoice_data: Dict[str, Any],
        ocr_result: Optional[Any] = None
    ) -> TemplateMatch:
        """
        Find matching template for document.

        Args:
            invoice_data: Extracted (possibly partial) invoice data
            ocr_result: OCR result for additional matching

        Returns:
            TemplateMatch with best matching template
        """
        vendor = invoice_data.get("vendor", {})
        tax_number = vendor.get("tax_number", "")

        # Try exact match by tax number
        if tax_number:
            template_id = self._generate_template_id(tax_number)
            if template_id in self.templates:
                template = self.templates[template_id]
                return TemplateMatch(
                    template=template,
                    match_score=1.0,
                    matched_fields=list(template.fields.keys()),
                    hints=self._generate_hints(template),
                    confidence_boost=template.confidence_score * 0.1,
                )

        # Try fuzzy matching by vendor name or other fields
        best_match = None
        best_score = 0.0

        vendor_name = vendor.get("name", vendor.get("name_ar", ""))

        for template in self.templates.values():
            score = self._calculate_match_score(invoice_data, template, vendor_name)
            if score > best_score:
                best_score = score
                best_match = template

        if best_match and best_score > 0.5:
            return TemplateMatch(
                template=best_match,
                match_score=best_score,
                matched_fields=[f for f in best_match.fields.keys()
                               if f in self._get_present_fields(invoice_data)],
                hints=self._generate_hints(best_match),
                confidence_boost=best_score * best_match.confidence_score * 0.05,
            )

        return TemplateMatch(
            template=None,
            match_score=0.0,
        )

    def _calculate_match_score(
        self,
        invoice_data: Dict[str, Any],
        template: InvoiceTemplate,
        vendor_name: str
    ) -> float:
        """Calculate match score between invoice and template."""
        score = 0.0

        # Vendor name similarity
        if vendor_name and template.vendor_name:
            name_similarity = self._string_similarity(vendor_name, template.vendor_name)
            score += name_similarity * 0.4

        # Field presence matching
        present_fields = self._get_present_fields(invoice_data)
        template_fields = set(template.fields.keys())

        if template_fields:
            field_overlap = len(present_fields & template_fields) / len(template_fields)
            score += field_overlap * 0.4

        # Document type matching
        if invoice_data.get("document_type") == template.document_type:
            score += 0.2

        return min(1.0, score)

    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity (simple implementation)."""
        if not s1 or not s2:
            return 0.0

        # Use character overlap for simple similarity
        set1 = set(s1)
        set2 = set(s2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    def _get_present_fields(self, invoice_data: Dict[str, Any]) -> set:
        """Get set of present field paths in invoice data."""
        fields = set()

        for section, keys in [
            ("vendor", ["name", "tax_number"]),
            ("invoice", ["reference_number", "date"]),
            ("totals", ["total", "subtotal", "tax_amount"]),
        ]:
            section_data = invoice_data.get(section, {})
            for key in keys:
                if section_data.get(key):
                    fields.add(f"{section}.{key}")

        if invoice_data.get("line_items"):
            fields.add("line_items")

        return fields

    def _generate_hints(self, template: InvoiceTemplate) -> Dict[str, Any]:
        """Generate extraction hints from template."""
        hints = {}

        for field_name, field_info in template.fields.items():
            hints[field_name] = {
                "expected_region": field_info.expected_region,
                "relative_position": field_info.relative_position,
                "field_type": field_info.field_type,
                "confidence": field_info.confidence,
            }

        return hints

    def apply_template(
        self,
        ocr_result: Any,
        template_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Apply learned template to improve extraction.

        Args:
            ocr_result: Raw OCR result
            template_key: Template identifier (e.g., vendor tax number)

        Returns:
            Template-guided extraction hints, or None if no template
        """
        template_id = self._generate_template_id(template_key)

        if template_id not in self.templates:
            return None

        template = self.templates[template_id]
        hints = {}

        # Use template to guide field extraction
        for field_name, field_info in template.fields.items():
            region = field_info.expected_region

            if region and hasattr(ocr_result, 'pages') and ocr_result.pages:
                # Find text blocks in expected region
                matching_blocks = self._find_blocks_in_region(
                    ocr_result.pages[0].text_blocks,
                    region
                )

                if matching_blocks:
                    hints[field_name] = {
                        "region": region,
                        "candidates": [b.text for b in matching_blocks[:5]],
                        "confidence_boost": 0.1,
                    }

        return hints if hints else None

    def _find_blocks_in_region(
        self,
        text_blocks: List[Any],
        region: List[float]
    ) -> List[Any]:
        """Find text blocks within a normalized region."""
        if not region or len(region) != 4:
            return []

        matching = []
        x1, y1, x2, y2 = region

        for block in text_blocks:
            if not hasattr(block, 'bbox') or not block.bbox:
                continue

            # Get block center (assuming bbox is [x1, y1, x2, y2] or polygon)
            bbox = block.bbox
            if isinstance(bbox[0], (list, tuple)):
                # Polygon format
                bx = sum(p[0] for p in bbox) / len(bbox)
                by = sum(p[1] for p in bbox) / len(bbox)
            else:
                # Simple bbox
                bx = (bbox[0] + bbox[2]) / 2 if len(bbox) >= 4 else bbox[0]
                by = (bbox[1] + bbox[3]) / 2 if len(bbox) >= 4 else bbox[1]

            # Check if center is in region (using normalized coordinates)
            if x1 <= bx <= x2 and y1 <= by <= y2:
                matching.append(block)

        return matching

    def get_template_stats(self) -> Dict[str, Any]:
        """Get statistics about stored templates."""
        if not self.templates:
            return {"count": 0}

        sample_counts = [t.sample_count for t in self.templates.values()]
        confidences = [t.confidence_score for t in self.templates.values()]

        return {
            "count": len(self.templates),
            "total_samples": sum(sample_counts),
            "avg_samples_per_template": sum(sample_counts) / len(sample_counts),
            "avg_confidence": sum(confidences) / len(confidences),
            "reliable_templates": sum(
                1 for t in self.templates.values()
                if t.sample_count >= self.MIN_SAMPLES_FOR_CONFIDENCE
            ),
        }

    def export_templates(self, output_path: str):
        """Export templates to file."""
        data = {k: v.to_dict() for k, v in self.templates.items()}

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Exported {len(self.templates)} templates to {output_path}")

    def import_templates(self, input_path: str, merge: bool = True):
        """Import templates from file."""
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        imported = 0
        for template_id, template_data in data.items():
            if merge and template_id in self.templates:
                # Merge with existing
                existing = self.templates[template_id]
                imported_template = InvoiceTemplate.from_dict(template_data)

                if imported_template.sample_count > existing.sample_count:
                    self.templates[template_id] = imported_template
                    imported += 1
            else:
                self.templates[template_id] = InvoiceTemplate.from_dict(template_data)
                imported += 1

        self._modified = True

        if self.auto_save:
            self._save_templates()

        logger.info(f"Imported {imported} templates from {input_path}")

    def clear_templates(self):
        """Clear all stored templates."""
        self.templates.clear()
        self._modified = True

        if self.auto_save:
            self._save_templates()

        logger.info("Cleared all templates")

    def remove_template(self, template_id: str) -> bool:
        """Remove a specific template."""
        if template_id in self.templates:
            del self.templates[template_id]
            self._modified = True

            if self.auto_save:
                self._save_templates()

            return True
        return False
