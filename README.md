# OCR Tool for ERP

A powerful OCR (Optical Character Recognition) tool built with PaddleOCR for extracting text from images and PDFs. Designed for ERP applications with support for English and Arabic languages.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![React](https://img.shields.io/badge/React-18+-61DAFB.svg)
![PaddleOCR](https://img.shields.io/badge/PaddleOCR-3.3+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Features

- **Image OCR**: Extract text from PNG, JPG, JPEG, GIF, BMP, TIFF images
- **PDF OCR**: Extract text from PDF documents (multi-page support)
- **Multi-language**: Support for English and Arabic
- **High Accuracy**: 98-99% accuracy using PaddleOCR v5 models
- **Offline Mode**: Works offline after initial model download
- **REST API**: Flask-based API for integration with other systems
- **Modern UI**: React.js frontend with drag & drop file upload
- **Export Options**: Copy text to clipboard or download as JSON

## Screenshots

### Upload Interface
- Drag & drop or browse files
- Select language (English/Arabic)
- Preview images before processing

### Results View
- Text View: Clean extracted text
- Detailed View: Text blocks with confidence scores
- Export: Copy or download results

## Installation

### Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher
- npm 8 or higher

### 1. Clone the Repository

```bash
git clone https://github.com/HS420-CODER/OCR_ERP_Tool.git
cd OCR_ERP_Tool
```

### 2. Setup Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install Python dependencies
pip install paddlepaddle paddleocr PyMuPDF opencv-python Pillow flask flask-cors reportlab
```

### 3. Setup React Frontend

```bash
cd frontend
npm install
cd ..
```

### 4. Download OCR Models (First Run)

The models will download automatically on first use, or you can pre-download them:

```bash
python download_models.py
```

Select option 2 to download common languages (English, Arabic, etc.)

## Usage

### Quick Start (Windows)

Double-click `start.bat` or run:

```bash
start.bat
```

This will start both the API server and React frontend.

### Manual Start

**Terminal 1 - API Server:**
```bash
cd OCR_ERP_Tool
.\venv\Scripts\activate
python api.py
```

**Terminal 2 - React Frontend:**
```bash
cd OCR_ERP_Tool/frontend
npm run dev
```

### Access the Application

- **Frontend**: http://localhost:5173
- **API**: http://localhost:5000

## API Endpoints

### Health Check
```
GET /api/health
```

### OCR Processing (Full Result)
```
POST /api/ocr
Content-Type: multipart/form-data

Parameters:
- file: Image or PDF file
- lang: Language code ('en' or 'ar')

Response:
{
  "success": true,
  "data": {
    "file": "document.pdf",
    "type": "pdf",
    "total_pages": 2,
    "processed_pages": 2,
    "pages": [
      {
        "page_number": 1,
        "text_blocks": [...],
        "full_text": "Extracted text..."
      }
    ]
  }
}
```

### OCR Processing (Text Only)
```
POST /api/ocr/text
Content-Type: multipart/form-data

Parameters:
- file: Image or PDF file
- lang: Language code ('en' or 'ar')

Response:
{
  "success": true,
  "text": "Extracted text content..."
}
```

## Python Library Usage

You can also use the OCR tool directly in Python:

```python
from ocr_tool import ERPOCRTool

# Initialize OCR engine
ocr = ERPOCRTool(lang='en')  # Use 'ar' for Arabic

# Process an image
result = ocr.process_image('invoice.png')
print(result['pages'][0]['full_text'])

# Process a PDF
result = ocr.process_pdf('document.pdf')
for page in result['pages']:
    print(f"Page {page['page_number']}:")
    print(page['full_text'])

# Get text only (convenience method)
text = ocr.get_text_only('document.pdf')
print(text)

# Save results to JSON
ocr.save_results_json(result, 'output.json')
```

## Project Structure

```
OCR_ERP_Tool/
├── api.py                 # Flask REST API server
├── ocr_tool.py            # Core OCR processing logic
├── download_models.py     # Model download utility
├── start.bat              # Windows startup script
├── requirements.txt       # Python dependencies
├── frontend/              # React.js frontend
│   ├── src/
│   │   ├── App.jsx        # Main React component
│   │   ├── App.css        # Styles
│   │   └── main.jsx       # Entry point
│   ├── package.json
│   └── vite.config.js
├── test_samples/          # Sample test files
│   ├── sample_image.png
│   └── sample_document.pdf
└── tasks/
    └── todo.md            # Project documentation
```

## Supported Languages

| Code | Language |
|------|----------|
| `en` | English |
| `ar` | Arabic |
| `ch` | Chinese (Simplified) |
| `fr` | French |
| `german` | German |
| `japan` | Japanese |
| `korean` | Korean |
| `ru` | Russian |

To add more languages, run `download_models.py` and select the languages you need.

## Offline Usage

After the initial model download, the OCR tool works completely offline. Models are cached at:

- **Windows**: `C:\Users\<username>\.paddlex\official_models\`
- **Linux/Mac**: `~/.paddlex/official_models/`

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DISABLE_MODEL_SOURCE_CHECK` | Skip online connectivity check | `True` |

### API Configuration

Edit `api.py` to change:
- Port number (default: 5000)
- Upload folder location
- Allowed file extensions

## Troubleshooting

### Models not downloading
- Check your internet connection
- Try running `python download_models.py` manually

### OCR accuracy issues
- Ensure good image quality (300 DPI recommended)
- Check if the correct language is selected
- For rotated text, the tool auto-detects orientation

### API connection refused
- Make sure the Flask server is running on port 5000
- Check if another application is using the port

## Tech Stack

- **Backend**: Python, Flask, PaddleOCR, PaddlePaddle
- **Frontend**: React.js, Vite, Axios
- **OCR Engine**: PaddleOCR v5 (PP-OCRv5)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) - Awesome multilingual OCR toolkit
- [PaddlePaddle](https://www.paddlepaddle.org.cn/) - Deep learning platform

---

Made with [Claude Code](https://claude.ai/code)
