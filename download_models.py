"""
PaddleOCR Model Downloader
Downloads OCR models for offline use
"""

import os
os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'

from paddleocr import PaddleOCR

# All supported languages with their codes
SUPPORTED_LANGUAGES = {
    # Most Common
    'en': 'English',
    'ch': 'Chinese (Simplified)',
    'chinese_cht': 'Chinese (Traditional)',
    'ar': 'Arabic',

    # European
    'fr': 'French',
    'german': 'German',
    'it': 'Italian',
    'es': 'Spanish',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'uk': 'Ukrainian',
    'be': 'Belarusian',
    'bg': 'Bulgarian',
    'pl': 'Polish',
    'cs': 'Czech',
    'sk': 'Slovak',
    'sl': 'Slovenian',
    'hr': 'Croatian',
    'rs_cyrillic': 'Serbian (Cyrillic)',
    'rs_latin': 'Serbian (Latin)',
    'hu': 'Hungarian',
    'ro': 'Romanian',
    'nl': 'Dutch',
    'da': 'Danish',
    'no': 'Norwegian',
    'sv': 'Swedish',
    'fi': 'Finnish',
    'et': 'Estonian',
    'lv': 'Latvian',
    'lt': 'Lithuanian',

    # Asian
    'japan': 'Japanese',
    'korean': 'Korean',
    'vi': 'Vietnamese',
    'th': 'Thai',
    'ta': 'Tamil',
    'te': 'Telugu',
    'ka': 'Kannada',
    'mr': 'Marathi',
    'ne': 'Nepali',
    'hi': 'Hindi',
    'fa': 'Persian/Farsi',
    'ur': 'Urdu',
    'sa': 'Sanskrit',
    'bn': 'Bengali',
    'pu': 'Punjabi',
    'ug': 'Uyghur',
    'mn': 'Mongolian',

    # Other
    'tr': 'Turkish',
    'ga': 'Irish',
    'cy': 'Welsh',
    'latin': 'Latin',
    'devanagari': 'Devanagari',
}


def download_model(lang_code, lang_name):
    """Download model for a specific language."""
    print(f"\n{'='*60}")
    print(f"Downloading: {lang_name} ({lang_code})")
    print('='*60)
    try:
        ocr = PaddleOCR(lang=lang_code)
        # Run a dummy prediction to ensure model is fully loaded
        print(f"SUCCESS: {lang_name} model downloaded!")
        return True
    except Exception as e:
        print(f"FAILED: {lang_name} - {str(e)[:100]}")
        return False


def show_menu():
    """Show interactive menu."""
    print("\n" + "="*60)
    print("PaddleOCR Model Downloader")
    print("="*60)
    print("\nAvailable Languages:\n")

    # Group by category
    categories = {
        'Common': ['en', 'ch', 'chinese_cht', 'ar'],
        'European': ['fr', 'german', 'it', 'es', 'pt', 'ru', 'nl', 'pl'],
        'Asian': ['japan', 'korean', 'vi', 'th', 'hi', 'ta', 'fa', 'ur'],
        'Nordic': ['da', 'no', 'sv', 'fi'],
    }

    for category, codes in categories.items():
        print(f"\n{category}:")
        for code in codes:
            if code in SUPPORTED_LANGUAGES:
                print(f"  {code:15} - {SUPPORTED_LANGUAGES[code]}")

    print(f"\n  ... and {len(SUPPORTED_LANGUAGES) - 24} more languages")
    print("\nOptions:")
    print("  1. Download specific language(s)")
    print("  2. Download common languages (en, ch, ar, fr, german)")
    print("  3. Download ALL languages")
    print("  4. List all supported languages")
    print("  5. Exit")

    return input("\nEnter choice (1-5): ").strip()


def main():
    while True:
        choice = show_menu()

        if choice == '1':
            print("\nEnter language codes separated by comma")
            print("Example: en,ch,fr,german,ar")
            codes = input("Language codes: ").strip().split(',')
            codes = [c.strip() for c in codes if c.strip()]

            for code in codes:
                if code in SUPPORTED_LANGUAGES:
                    download_model(code, SUPPORTED_LANGUAGES[code])
                else:
                    print(f"Unknown language code: {code}")

        elif choice == '2':
            common = ['en', 'ch', 'ar', 'fr', 'german']
            print(f"\nDownloading common languages: {common}")
            for code in common:
                download_model(code, SUPPORTED_LANGUAGES[code])

        elif choice == '3':
            print(f"\nDownloading ALL {len(SUPPORTED_LANGUAGES)} languages...")
            print("This may take a while and use significant disk space (~5GB)")
            confirm = input("Continue? (y/n): ").strip().lower()
            if confirm == 'y':
                for code, name in SUPPORTED_LANGUAGES.items():
                    download_model(code, name)

        elif choice == '4':
            print("\n" + "="*60)
            print("All Supported Languages")
            print("="*60)
            for code, name in sorted(SUPPORTED_LANGUAGES.items(), key=lambda x: x[1]):
                print(f"  {code:15} - {name}")

        elif choice == '5':
            print("\nGoodbye!")
            break
        else:
            print("Invalid choice. Please enter 1-5.")


if __name__ == '__main__':
    main()
