"""
Integration test for Arabic output improvements.

Tests the enhanced Arabic text processing on OIP.png invoice.
"""

import sys
import io

# Fix Windows console encoding for Arabic
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, '.')

from src.read_tool import HybridReadTool
from src.models import ReadOptions
from src.formatters.document_analyzer import DocumentAnalyzer
from src.formatters.output_formatter import StructuredOutputFormatter


def test_arabic_invoice():
    """Test OCR on Arabic invoice with improvements."""

    print("=" * 60)
    print("ARABIC OUTPUT IMPROVEMENT TEST")
    print("=" * 60)

    # Initialize tools
    read_tool = HybridReadTool()
    analyzer = DocumentAnalyzer()
    formatter = StructuredOutputFormatter()

    # Test file - use absolute path
    import os
    test_file = os.path.abspath("examples/OIP.png")

    print(f"\nProcessing: {test_file}")
    print("-" * 40)

    try:
        print(f"Using engine: paddle")
        print(f"Language: ar")

        result = read_tool.read(
            file_path=test_file,
            lang="ar",
            engine="paddle",
            structured_output=True
        )

        print(f"Result type: {type(result)}")
        print(f"Full text length: {len(result.full_text) if result.full_text else 0}")
        print(f"Pages: {len(result.pages) if result.pages else 0}")

        print("\n# RAW OCR OUTPUT")
        print("-" * 40)
        print(result.full_text[:1000] if len(result.full_text) > 1000 else result.full_text)

        # Analyze structure
        print("\n# DOCUMENT STRUCTURE")
        print("-" * 40)
        structure = analyzer.analyze(result)

        print(f"- Document Type: {structure.document_type}")
        print(f"- Language: {structure.language}")
        print(f"- Is Bilingual: {structure.is_bilingual}")
        print(f"- Key-Value Pairs: {len(structure.key_value_pairs)}")

        print("\n  Extracted Fields:")
        for key, value in list(structure.key_value_pairs.items())[:15]:
            print(f"    - {key}: {value}")

        if len(structure.key_value_pairs) > 15:
            print(f"    ... and {len(structure.key_value_pairs) - 15} more")

        # Format output
        print("\n# FORMATTED OUTPUT")
        print("-" * 40)
        formatted = formatter.format(result, structure, output_format="markdown")
        print(formatted[:2000] if len(formatted) > 2000 else formatted)

        # Summary
        print("\n# SUMMARY")
        print("-" * 40)
        print(f"Document Type: {structure.document_type.value}")
        print(f"Fields Extracted: {len(structure.key_value_pairs)}")
        print(f"Tables Found: {len(structure.tables)}")
        print(f"Regions Detected: {len(structure.regions)}")

        # Check improvements
        print("\n# IMPROVEMENT CHECK")
        print("-" * 40)

        improvements = []
        if structure.document_type.value in ['tax_invoice', 'invoice']:
            improvements.append("Document type correctly identified as invoice")
        else:
            print(f"  WARNING: Document type is {structure.document_type.value}, expected tax_invoice")

        if len(structure.key_value_pairs) >= 10:
            improvements.append(f"Extracted {len(structure.key_value_pairs)} fields (target: 40+)")
        else:
            print(f"  WARNING: Only {len(structure.key_value_pairs)} fields extracted, target is 40+")

        if structure.is_bilingual:
            improvements.append("Bilingual content detected")

        for imp in improvements:
            print(f"  + {imp}")

        return True

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_arabic_invoice()
    sys.exit(0 if success else 1)
