"""
PaddleOCR Tool for ERP Application
Reads text from images and PDFs
"""

import os

# Skip online connectivity check - models are cached locally
os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'
import json
from paddleocr import PaddleOCR
import fitz  # PyMuPDF for PDF handling
from PIL import Image
import cv2
import numpy as np


class ERPOCRTool:
    """OCR Tool for extracting text from images and PDFs for ERP applications."""

    def __init__(self, lang='en', use_textline_orientation=True, use_gpu=False):
        """
        Initialize the OCR engine.

        Args:
            lang: Language for OCR ('en', 'ch', 'fr', 'german', 'korean', 'japan')
            use_textline_orientation: Whether to use textline orientation detection
            use_gpu: Whether to use GPU for processing
        """
        self.ocr = PaddleOCR(
            use_textline_orientation=use_textline_orientation,
            lang=lang,
            device='gpu' if use_gpu else 'cpu'
        )
        self.lang = lang

    def process_image(self, image_path: str) -> dict:
        """
        Extract text from an image file.

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary with extracted text, bounding boxes, and confidence scores
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        result = self.ocr.predict(image_path)

        extracted_data = {
            'file': image_path,
            'type': 'image',
            'pages': []
        }

        # Parse new API result format
        for res in result:
            page_data = self._parse_ocr_result_v3(res)
            extracted_data['pages'].append(page_data)

        if not extracted_data['pages']:
            extracted_data['pages'].append({'text_blocks': [], 'full_text': ''})

        return extracted_data

    def process_pdf(self, pdf_path: str, max_pages: int = None) -> dict:
        """
        Extract text from a PDF file by converting pages to images.

        Args:
            pdf_path: Path to the PDF file
            max_pages: Maximum number of pages to process (None for all)

        Returns:
            Dictionary with extracted text from all pages
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        extracted_data = {
            'file': pdf_path,
            'type': 'pdf',
            'total_pages': 0,
            'processed_pages': 0,
            'pages': []
        }

        # Convert PDF pages to images and process each
        with fitz.open(pdf_path) as pdf:
            total_pages = pdf.page_count
            extracted_data['total_pages'] = total_pages

            if max_pages:
                pages_to_process = min(max_pages, total_pages)
            else:
                pages_to_process = total_pages

            extracted_data['processed_pages'] = pages_to_process

            for page_num in range(pages_to_process):
                page = pdf[page_num]

                # Convert page to image (2x scale for better OCR)
                mat = fitz.Matrix(2, 2)
                pm = page.get_pixmap(matrix=mat, alpha=False)

                # If too large, use 1x scale
                if pm.width > 2000 or pm.height > 2000:
                    pm = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)

                # Convert to numpy array for OCR
                img = Image.frombytes("RGB", [pm.width, pm.height], pm.samples)
                img_array = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

                # Run OCR on the image
                result = self.ocr.predict(img_array)

                page_data = {
                    'page_number': page_num + 1,
                    'text_blocks': [],
                    'full_text': ''
                }

                for res in result:
                    parsed = self._parse_ocr_result_v3(res)
                    page_data['text_blocks'].extend(parsed['text_blocks'])
                    if page_data['full_text']:
                        page_data['full_text'] += '\n' + parsed['full_text']
                    else:
                        page_data['full_text'] = parsed['full_text']

                extracted_data['pages'].append(page_data)

        return extracted_data

    def _parse_ocr_result_v3(self, result) -> dict:
        """Parse OCR v3 result into structured format."""
        text_blocks = []
        full_text_lines = []

        # New API returns OCRResult object (dict-like) with rec_texts, rec_scores, dt_polys
        if hasattr(result, 'keys'):  # Dict-like object
            texts = result.get('rec_texts', []) or []
            scores = result.get('rec_scores', []) or []
            polys = result.get('dt_polys', []) or []

            for i, text in enumerate(texts):
                score = scores[i] if i < len(scores) else 0.0
                bbox = polys[i].tolist() if i < len(polys) and hasattr(polys[i], 'tolist') else []

                text_blocks.append({
                    'text': text,
                    'confidence': round(float(score), 4),
                    'bbox': bbox
                })
                full_text_lines.append(text)
        # Fallback for old format
        elif isinstance(result, list):
            for line in result:
                if isinstance(line, (list, tuple)) and len(line) >= 2:
                    bbox = line[0]
                    text = line[1][0] if isinstance(line[1], (list, tuple)) else line[1]
                    confidence = line[1][1] if isinstance(line[1], (list, tuple)) and len(line[1]) > 1 else 0.0

                    text_blocks.append({
                        'text': text,
                        'confidence': round(float(confidence), 4),
                        'bbox': bbox
                    })
                    full_text_lines.append(text)

        return {
            'text_blocks': text_blocks,
            'full_text': '\n'.join(full_text_lines)
        }

    def _parse_ocr_result(self, result) -> dict:
        """Parse OCR result into structured format (legacy)."""
        text_blocks = []
        full_text_lines = []

        if result:
            for line in result:
                bbox = line[0]
                text = line[1][0]
                confidence = line[1][1]

                text_blocks.append({
                    'text': text,
                    'confidence': round(confidence, 4),
                    'bbox': bbox
                })
                full_text_lines.append(text)

        return {
            'text_blocks': text_blocks,
            'full_text': '\n'.join(full_text_lines)
        }

    def get_text_only(self, file_path: str) -> str:
        """
        Convenience method to get just the extracted text as a string.

        Args:
            file_path: Path to image or PDF file

        Returns:
            Extracted text as a single string
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.pdf':
            result = self.process_pdf(file_path)
        else:
            result = self.process_image(file_path)

        all_text = []
        for page in result['pages']:
            all_text.append(page['full_text'])

        return '\n\n--- Page Break ---\n\n'.join(all_text)

    def save_results_json(self, result: dict, output_path: str):
        """Save OCR results to a JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)


def main():
    """Test the OCR tool with sample files."""
    print("=" * 60)
    print("PaddleOCR Tool for ERP - Test Suite")
    print("=" * 60)

    # Initialize OCR
    print("\n[1] Initializing OCR engine...")
    ocr_tool = ERPOCRTool(lang='en')
    print("    OCR engine initialized successfully!")

    # Create test output directory
    os.makedirs('output', exist_ok=True)

    # Test with sample image if exists
    test_images = [
        'test_samples/sample_image.png',
        'test_samples/sample_image.jpg',
        'PaddleOCR/doc/imgs_en/img_12.jpg'  # From cloned repo
    ]

    for img_path in test_images:
        if os.path.exists(img_path):
            print(f"\n[2] Testing image OCR with: {img_path}")
            try:
                result = ocr_tool.process_image(img_path)
                print(f"    Found {len(result['pages'][0]['text_blocks'])} text blocks")
                print(f"    Extracted text:\n    {'-'*40}")
                for block in result['pages'][0]['text_blocks'][:5]:
                    print(f"    [{block['confidence']:.2%}] {block['text']}")
                if len(result['pages'][0]['text_blocks']) > 5:
                    print(f"    ... and {len(result['pages'][0]['text_blocks'])-5} more blocks")
                break
            except Exception as e:
                print(f"    Error: {e}")
    else:
        print("\n[2] No sample images found. Creating a test image...")
        create_test_image()
        if os.path.exists('test_samples/sample_image.png'):
            result = ocr_tool.process_image('test_samples/sample_image.png')
            print(f"    Found {len(result['pages'][0]['text_blocks'])} text blocks")
            print(f"    Extracted text:")
            for block in result['pages'][0]['text_blocks']:
                print(f"    [{block['confidence']:.2%}] {block['text']}")

    # Test with sample PDF if exists
    test_pdfs = [
        'test_samples/sample.pdf',
        'test_samples/sample_document.pdf'
    ]

    for pdf_path in test_pdfs:
        if os.path.exists(pdf_path):
            print(f"\n[3] Testing PDF OCR with: {pdf_path}")
            try:
                result = ocr_tool.process_pdf(pdf_path, max_pages=2)
                print(f"    Processed {result['processed_pages']} of {result['total_pages']} pages")
                for page in result['pages']:
                    print(f"    Page {page['page_number']}: {len(page['text_blocks'])} text blocks")
                ocr_tool.save_results_json(result, 'output/pdf_result.json')
                print("    Results saved to output/pdf_result.json")
                break
            except Exception as e:
                print(f"    Error: {e}")
    else:
        print("\n[3] No sample PDFs found. Place a PDF in test_samples/ to test.")

    print("\n" + "=" * 60)
    print("OCR Tool is ready for use!")
    print("=" * 60)
    print("\nUsage example:")
    print('    from ocr_tool import ERPOCRTool')
    print('    ocr = ERPOCRTool(lang="en")')
    print('    result = ocr.process_image("invoice.png")')
    print('    text = ocr.get_text_only("document.pdf")')


def create_test_image():
    """Create a simple test image with text."""
    os.makedirs('test_samples', exist_ok=True)

    # Create a white image with text
    img = np.ones((200, 600, 3), dtype=np.uint8) * 255

    # Add text
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, 'PaddleOCR Test Image', (50, 60), font, 1, (0, 0, 0), 2)
    cv2.putText(img, 'Invoice #12345', (50, 100), font, 0.8, (0, 0, 0), 2)
    cv2.putText(img, 'Total: $1,234.56', (50, 140), font, 0.8, (0, 0, 0), 2)
    cv2.putText(img, 'Date: 2025-01-05', (50, 180), font, 0.8, (0, 0, 0), 2)

    cv2.imwrite('test_samples/sample_image.png', img)
    print("    Created test_samples/sample_image.png")


if __name__ == '__main__':
    main()
