"""
ERP Arabic OCR Microservice - Output Formatter
===============================================
Formats OCR results for API responses and exports.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from . import (
    ProcessingResult,
    OCRResult,
    FusionResult,
    CorrectionResult,
    InvoiceData,
    DocumentType
)

logger = logging.getLogger(__name__)


class OutputFormatter:
    """
    Format OCR processing results for various outputs.

    Supports:
    - JSON API responses
    - Structured invoice data
    - Markdown documentation
    - CSV export
    - Bilingual output (Arabic/English)
    """

    def __init__(self, include_debug: bool = False):
        """
        Initialize output formatter.

        Args:
            include_debug: Include debug information in output
        """
        self.include_debug = include_debug

    def format_invoice_response(
        self,
        result: ProcessingResult,
        include_raw: bool = False
    ) -> Dict[str, Any]:
        """
        Format invoice processing result for API response.

        Args:
            result: Processing result
            include_raw: Include raw OCR output

        Returns:
            Formatted API response dict
        """
        response = {
            "success": result.success,
            "document_type": "invoice",
            "timestamp": result.timestamp,
            "processing_time_ms": result.processing_time_ms,
        }

        # Main text output
        response["text"] = {
            "full_text": result.text,
            "confidence": result.confidence,
            "word_count": len(result.text.split()) if result.text else 0
        }

        # Extracted fields
        if result.invoice_data:
            response["extracted_fields"] = self._format_invoice_fields(result.invoice_data)

        # Engines used
        if result.fusion_result:
            response["engines"] = {
                "mode": "fusion",
                "engines_used": result.fusion_result.engines_used,
                "fusion_strategy": result.fusion_result.strategy.value,
                "improvement_score": result.fusion_result.improvement_score
            }
        elif result.ocr_result:
            response["engines"] = {
                "mode": "single",
                "engine": result.ocr_result.engine.value
            }

        # Corrections applied
        if result.correction_result and result.correction_result.was_modified:
            response["corrections"] = {
                "applied": True,
                "type": result.correction_result.correction_type,
                "count": result.correction_result.correction_count,
                "confidence": result.correction_result.confidence
            }

        # Metadata
        response["metadata"] = {
            "request_id": result.request_id,
            "filename": result.filename,
            "file_size_bytes": result.file_size_bytes,
            "image_dimensions": result.image_dimensions
        }

        # Warnings and errors
        if result.warnings:
            response["warnings"] = result.warnings
        if result.errors:
            response["errors"] = result.errors

        # Raw output (optional)
        if include_raw and result.ocr_result:
            response["raw"] = {
                "text": result.ocr_result.raw_text,
                "blocks": [b.to_dict() for b in result.ocr_result.blocks]
            }

        return response

    def format_document_response(
        self,
        result: ProcessingResult
    ) -> Dict[str, Any]:
        """
        Format general document processing result.

        Args:
            result: Processing result

        Returns:
            Formatted API response dict
        """
        response = {
            "success": result.success,
            "document_type": result.document_type.value,
            "timestamp": result.timestamp,
            "processing_time_ms": result.processing_time_ms,
            "text": result.text,
            "confidence": result.confidence,
            "metadata": {
                "request_id": result.request_id,
                "filename": result.filename,
                "word_count": len(result.text.split()) if result.text else 0
            }
        }

        if result.warnings:
            response["warnings"] = result.warnings
        if result.errors:
            response["errors"] = result.errors

        return response

    def format_batch_response(
        self,
        results: List[ProcessingResult],
        batch_id: str = ""
    ) -> Dict[str, Any]:
        """
        Format batch processing results.

        Args:
            results: List of processing results
            batch_id: Batch identifier

        Returns:
            Formatted batch response dict
        """
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        total_time = sum(r.processing_time_ms for r in results)
        avg_confidence = (
            sum(r.confidence for r in successful) / len(successful)
            if successful else 0.0
        )

        response = {
            "batch_id": batch_id or datetime.utcnow().isoformat(),
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total": len(results),
                "successful": len(successful),
                "failed": len(failed),
                "total_processing_time_ms": total_time,
                "average_confidence": avg_confidence
            },
            "results": []
        }

        for result in results:
            item = {
                "filename": result.filename,
                "success": result.success,
                "confidence": result.confidence,
                "processing_time_ms": result.processing_time_ms
            }

            if result.success:
                item["text_preview"] = result.text[:200] + "..." if len(result.text) > 200 else result.text
                if result.invoice_data:
                    item["invoice_number"] = (
                        result.invoice_data.invoice_number.value
                        if result.invoice_data.invoice_number else None
                    )
            else:
                item["errors"] = result.errors

            response["results"].append(item)

        return response

    def generate_structured_markdown(
        self,
        result: ProcessingResult,
        language: str = "bilingual"
    ) -> str:
        """
        Generate structured markdown output.

        Args:
            result: Processing result
            language: Output language (ar, en, bilingual)

        Returns:
            Markdown formatted string
        """
        lines = []

        # Header
        if language == "ar":
            lines.append("# نتائج التعرف الضوئي على الحروف")
            lines.append("")
            lines.append(f"**التاريخ:** {result.timestamp}")
            lines.append(f"**الثقة:** {result.confidence:.2%}")
        elif language == "en":
            lines.append("# OCR Processing Results")
            lines.append("")
            lines.append(f"**Date:** {result.timestamp}")
            lines.append(f"**Confidence:** {result.confidence:.2%}")
        else:
            lines.append("# OCR Results | نتائج التعرف الضوئي")
            lines.append("")
            lines.append(f"**Date | التاريخ:** {result.timestamp}")
            lines.append(f"**Confidence | الثقة:** {result.confidence:.2%}")

        lines.append("")

        # Extracted Text
        if language == "ar":
            lines.append("## النص المستخرج")
        elif language == "en":
            lines.append("## Extracted Text")
        else:
            lines.append("## Extracted Text | النص المستخرج")

        lines.append("")
        lines.append("```")
        lines.append(result.text)
        lines.append("```")
        lines.append("")

        # Invoice Fields
        if result.invoice_data:
            if language == "ar":
                lines.append("## بيانات الفاتورة")
            elif language == "en":
                lines.append("## Invoice Data")
            else:
                lines.append("## Invoice Data | بيانات الفاتورة")

            lines.append("")
            lines.append("| Field | القيمة | Value |")
            lines.append("|-------|--------|-------|")

            fields = [
                ('tax_number', 'الرقم الضريبي', result.invoice_data.tax_number),
                ('invoice_number', 'رقم الفاتورة', result.invoice_data.invoice_number),
                ('date', 'التاريخ', result.invoice_data.date),
                ('total', 'الاجمالي', result.invoice_data.total),
                ('subtotal', 'المجموع', result.invoice_data.subtotal),
                ('tax_amount', 'قيمة الضريبة', result.invoice_data.tax_amount),
                ('vendor_name', 'اسم المورد', result.invoice_data.vendor_name),
                ('customer_name', 'اسم العميل', result.invoice_data.customer_name),
            ]

            for field_en, field_ar, field_obj in fields:
                if field_obj:
                    value = field_obj.value
                    status = "✓" if field_obj.validated else "?"
                    lines.append(f"| {field_en} | {field_ar} | {value} {status} |")

            lines.append("")

            # Line Items
            if result.invoice_data.line_items:
                if language == "ar":
                    lines.append("### بنود الفاتورة")
                elif language == "en":
                    lines.append("### Line Items")
                else:
                    lines.append("### Line Items | بنود الفاتورة")

                lines.append("")
                lines.append("| Description | Qty | Unit Price | Total |")
                lines.append("|-------------|-----|------------|-------|")

                for item in result.invoice_data.line_items:
                    lines.append(
                        f"| {item.description} | {item.quantity or '-'} | "
                        f"{item.unit_price or '-'} | {item.total or '-'} |"
                    )

                lines.append("")

        # Processing Details
        if self.include_debug:
            lines.append("## Processing Details")
            lines.append("")
            lines.append(f"- Processing Time: {result.processing_time_ms:.0f}ms")
            lines.append(f"- Request ID: {result.request_id}")

            if result.fusion_result:
                lines.append(f"- Engines: {', '.join(result.fusion_result.engines_used)}")
                lines.append(f"- Fusion Strategy: {result.fusion_result.strategy.value}")

            lines.append("")

        return "\n".join(lines)

    def format_csv_export(
        self,
        results: List[ProcessingResult]
    ) -> str:
        """
        Format results as CSV for export.

        Args:
            results: List of processing results

        Returns:
            CSV formatted string
        """
        lines = []

        # Header
        headers = [
            "filename",
            "success",
            "confidence",
            "processing_time_ms",
            "tax_number",
            "invoice_number",
            "date",
            "total",
            "text_preview"
        ]
        lines.append(",".join(headers))

        # Rows
        for result in results:
            row = [
                self._escape_csv(result.filename),
                str(result.success),
                f"{result.confidence:.4f}",
                f"{result.processing_time_ms:.0f}",
            ]

            if result.invoice_data:
                row.append(
                    self._escape_csv(
                        result.invoice_data.tax_number.value
                        if result.invoice_data.tax_number else ""
                    )
                )
                row.append(
                    self._escape_csv(
                        result.invoice_data.invoice_number.value
                        if result.invoice_data.invoice_number else ""
                    )
                )
                row.append(
                    self._escape_csv(
                        result.invoice_data.date.value
                        if result.invoice_data.date else ""
                    )
                )
                row.append(
                    self._escape_csv(
                        result.invoice_data.total.value
                        if result.invoice_data.total else ""
                    )
                )
            else:
                row.extend(["", "", "", ""])

            # Text preview (first 100 chars)
            preview = result.text[:100].replace("\n", " ") if result.text else ""
            row.append(self._escape_csv(preview))

            lines.append(",".join(row))

        return "\n".join(lines)

    def _format_invoice_fields(
        self,
        invoice_data: InvoiceData
    ) -> Dict[str, Any]:
        """
        Format invoice fields for API response.

        Args:
            invoice_data: Invoice data object

        Returns:
            Formatted fields dict
        """
        fields = {}

        field_mapping = [
            ('tax_number', invoice_data.tax_number),
            ('invoice_number', invoice_data.invoice_number),
            ('date', invoice_data.date),
            ('total', invoice_data.total),
            ('subtotal', invoice_data.subtotal),
            ('tax_amount', invoice_data.tax_amount),
            ('vendor_name', invoice_data.vendor_name),
            ('customer_name', invoice_data.customer_name),
        ]

        for field_name, field_obj in field_mapping:
            if field_obj:
                fields[field_name] = {
                    "value": field_obj.value,
                    "confidence": field_obj.confidence,
                    "validated": field_obj.validated,
                    "label_ar": field_obj.field_name_ar
                }
                if field_obj.validation_message:
                    fields[field_name]["validation_message"] = field_obj.validation_message

        # Line items
        if invoice_data.line_items:
            fields["line_items"] = [
                {
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total": item.total,
                    "confidence": item.confidence
                }
                for item in invoice_data.line_items
            ]

        return fields

    def _escape_csv(self, value: str) -> str:
        """
        Escape value for CSV format.

        Args:
            value: Value to escape

        Returns:
            CSV-safe string
        """
        if not value:
            return ""

        # Escape quotes and wrap if contains special chars
        if ',' in value or '"' in value or '\n' in value:
            return '"' + value.replace('"', '""') + '"'

        return value


class APIResponseBuilder:
    """
    Build standardized API responses.

    Provides consistent response format for all endpoints.
    """

    @staticmethod
    def success(
        data: Any,
        message: str = "Success",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build success response.

        Args:
            data: Response data
            message: Success message
            metadata: Optional metadata

        Returns:
            API response dict
        """
        response = {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }

        if metadata:
            response["metadata"] = metadata

        return response

    @staticmethod
    def error(
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 400
    ) -> Dict[str, Any]:
        """
        Build error response.

        Args:
            error_code: Error code
            message: Error message
            details: Optional error details
            status_code: HTTP status code

        Returns:
            API response dict
        """
        response = {
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
                "status_code": status_code
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        if details:
            response["error"]["details"] = details

        return response

    @staticmethod
    def health(
        status: str,
        components: Dict[str, Any],
        version: str = "2.0.0"
    ) -> Dict[str, Any]:
        """
        Build health check response.

        Args:
            status: Overall health status
            components: Component health details
            version: Service version

        Returns:
            Health response dict
        """
        return {
            "status": status,
            "version": version,
            "timestamp": datetime.utcnow().isoformat(),
            "components": components
        }


# Export
__all__ = [
    "OutputFormatter",
    "APIResponseBuilder"
]
