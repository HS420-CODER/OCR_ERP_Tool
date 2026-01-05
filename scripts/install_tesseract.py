#!/usr/bin/env python3
"""
Tesseract OCR Installation Helper Script.

This script helps with:
1. Installing Tesseract OCR on Windows
2. Installing language packs (English and Arabic)
3. Verifying the installation

Usage:
    python scripts/install_tesseract.py --check       # Check installation status
    python scripts/install_tesseract.py --install     # Install Tesseract (Windows)
    python scripts/install_tesseract.py --lang ar     # Install Arabic language pack
    python scripts/install_tesseract.py --lang en     # Install English language pack
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
import tempfile
from pathlib import Path


# Tesseract download URLs and paths
TESSERACT_WINDOWS_URL = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe"
TESSERACT_WINDOWS_PATHS = [
    r"C:\Program Files\Tesseract-OCR",
    r"C:\Program Files (x86)\Tesseract-OCR",
    r"C:\Tesseract-OCR",
]

# Language data URLs (from tessdata_best for higher accuracy)
TESSDATA_URLS = {
    "eng": "https://github.com/tesseract-ocr/tessdata_best/raw/main/eng.traineddata",
    "ara": "https://github.com/tesseract-ocr/tessdata_best/raw/main/ara.traineddata",
    "osd": "https://github.com/tesseract-ocr/tessdata_best/raw/main/osd.traineddata",
}


def find_tesseract() -> str:
    """Find Tesseract installation path."""
    # Check PATH first
    tesseract_path = shutil.which("tesseract")
    if tesseract_path:
        return os.path.dirname(tesseract_path)

    # Check common Windows paths
    if platform.system() == "Windows":
        for path in TESSERACT_WINDOWS_PATHS:
            exe_path = os.path.join(path, "tesseract.exe")
            if os.path.exists(exe_path):
                return path

    return ""


def get_tessdata_path() -> str:
    """Get the tessdata directory path."""
    tesseract_dir = find_tesseract()
    if tesseract_dir:
        tessdata = os.path.join(tesseract_dir, "tessdata")
        if os.path.exists(tessdata):
            return tessdata
    return ""


def check_installation():
    """Check Tesseract installation status."""
    print("=" * 60)
    print("Tesseract OCR Installation Check")
    print("=" * 60)

    tesseract_dir = find_tesseract()
    if tesseract_dir:
        print(f"\n[OK] Tesseract found at: {tesseract_dir}")

        # Get version
        try:
            exe_path = os.path.join(tesseract_dir, "tesseract.exe") if platform.system() == "Windows" else "tesseract"
            result = subprocess.run([exe_path, "--version"], capture_output=True, text=True)
            version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown"
            print(f"     Version: {version_line}")
        except Exception as e:
            print(f"     Could not get version: {e}")
    else:
        print("\n[NOT FOUND] Tesseract is not installed")
        print("     Run: python scripts/install_tesseract.py --install")
        return False

    # Check tessdata directory
    tessdata = get_tessdata_path()
    if tessdata:
        print(f"\n[OK] Tessdata directory: {tessdata}")

        # List installed languages
        installed_langs = []
        for file in os.listdir(tessdata):
            if file.endswith(".traineddata"):
                lang = file.replace(".traineddata", "")
                installed_langs.append(lang)

        print(f"\nInstalled languages ({len(installed_langs)}):")
        for lang in sorted(installed_langs):
            print(f"     - {lang}")

        # Check for required languages
        required = ["eng", "ara"]
        missing = [lang for lang in required if lang not in installed_langs]
        if missing:
            print(f"\n[WARNING] Missing required languages: {missing}")
            for lang in missing:
                short = "en" if lang == "eng" else "ar"
                print(f"     Install with: python scripts/install_tesseract.py --lang {short}")
        else:
            print(f"\n[OK] All required languages installed")
    else:
        print("\n[NOT FOUND] Tessdata directory not found")
        return False

    # Check pytesseract
    print("\n" + "-" * 60)
    print("Python Package Check")
    print("-" * 60)

    try:
        import pytesseract
        print(f"\n[OK] pytesseract is installed")

        # Try to get tesseract version through pytesseract
        try:
            version = pytesseract.get_tesseract_version()
            print(f"     pytesseract can access Tesseract: v{version}")
        except Exception as e:
            print(f"     [WARNING] pytesseract cannot access Tesseract: {e}")
    except ImportError:
        print("\n[NOT FOUND] pytesseract is not installed")
        print("     Install with: pip install pytesseract")
        return False

    print("\n" + "=" * 60)
    print("Installation check complete!")
    print("=" * 60)

    return True


def download_file(url: str, dest: str, desc: str = ""):
    """Download a file with progress indication."""
    print(f"Downloading {desc or url}...")

    def progress_hook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100, downloaded * 100 / total_size)
            bar_len = 40
            filled = int(bar_len * percent / 100)
            bar = '=' * filled + '-' * (bar_len - filled)
            print(f'\r[{bar}] {percent:.1f}%', end='', flush=True)

    urllib.request.urlretrieve(url, dest, progress_hook)
    print()  # New line after progress


def install_tesseract_windows():
    """Install Tesseract on Windows."""
    print("=" * 60)
    print("Tesseract OCR Installation (Windows)")
    print("=" * 60)

    # Check if already installed
    if find_tesseract():
        print("\n[INFO] Tesseract is already installed")
        check_installation()
        return True

    print("\nDownloading Tesseract installer...")
    print(f"URL: {TESSERACT_WINDOWS_URL}")

    # Download installer
    with tempfile.TemporaryDirectory() as tmp_dir:
        installer_path = os.path.join(tmp_dir, "tesseract-installer.exe")
        download_file(TESSERACT_WINDOWS_URL, installer_path, "Tesseract installer")

        print(f"\nInstaller downloaded to: {installer_path}")
        print("\n" + "-" * 60)
        print("IMPORTANT: Manual steps required")
        print("-" * 60)
        print("""
1. The installer will now launch
2. Follow the installation wizard
3. IMPORTANT: Check the boxes for:
   - "Additional language data (download)"
   - Select "Arabic" and "English" languages
4. Use the default installation path (C:\\Program Files\\Tesseract-OCR)
5. After installation, restart your terminal/IDE

Press Enter to launch the installer...""")
        input()

        # Launch installer
        try:
            subprocess.run([installer_path], check=True)
            print("\n[INFO] Installer launched. Complete the installation wizard.")
        except Exception as e:
            print(f"\n[ERROR] Failed to launch installer: {e}")
            print(f"Please run the installer manually: {installer_path}")
            return False

    # Verify installation
    print("\nVerifying installation...")
    if find_tesseract():
        print("[OK] Tesseract installed successfully!")
        check_installation()
        return True
    else:
        print("[WARNING] Tesseract not found after installation")
        print("Please ensure you completed the installation wizard")
        return False


def install_language_pack(lang: str):
    """Install a language pack for Tesseract."""
    # Map short codes to tessdata names
    lang_map = {
        "en": "eng",
        "eng": "eng",
        "english": "eng",
        "ar": "ara",
        "ara": "ara",
        "arabic": "ara",
    }

    tess_lang = lang_map.get(lang.lower())
    if not tess_lang:
        print(f"[ERROR] Unknown language: {lang}")
        print(f"Supported: en (English), ar (Arabic)")
        return False

    if tess_lang not in TESSDATA_URLS:
        print(f"[ERROR] No download URL for language: {tess_lang}")
        return False

    print("=" * 60)
    print(f"Installing Language Pack: {tess_lang}")
    print("=" * 60)

    # Find tessdata directory
    tessdata = get_tessdata_path()
    if not tessdata:
        print("\n[ERROR] Tessdata directory not found")
        print("Please install Tesseract first:")
        print("  python scripts/install_tesseract.py --install")
        return False

    print(f"\nTessdata directory: {tessdata}")

    # Check if already installed
    traineddata_file = os.path.join(tessdata, f"{tess_lang}.traineddata")
    if os.path.exists(traineddata_file):
        print(f"\n[INFO] Language {tess_lang} is already installed")
        return True

    # Download language file
    url = TESSDATA_URLS[tess_lang]
    print(f"\nDownloading from: {url}")

    try:
        download_file(url, traineddata_file, f"{tess_lang}.traineddata")
        print(f"\n[OK] Language {tess_lang} installed successfully!")
        print(f"     File: {traineddata_file}")
        return True
    except Exception as e:
        print(f"\n[ERROR] Failed to download: {e}")
        return False


def install_pytesseract():
    """Install pytesseract Python package."""
    print("Installing pytesseract...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "pytesseract"], check=True)
        print("[OK] pytesseract installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to install pytesseract: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Tesseract OCR Installation Helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --check           Check installation status
  %(prog)s --install         Install Tesseract (Windows only)
  %(prog)s --lang ar         Install Arabic language pack
  %(prog)s --lang en         Install English language pack
  %(prog)s --pip             Install pytesseract Python package
        """
    )

    parser.add_argument("--check", action="store_true", help="Check installation status")
    parser.add_argument("--install", action="store_true", help="Install Tesseract OCR")
    parser.add_argument("--lang", type=str, help="Install language pack (en, ar)")
    parser.add_argument("--pip", action="store_true", help="Install pytesseract package")

    args = parser.parse_args()

    # Default to check if no args
    if not any([args.check, args.install, args.lang, args.pip]):
        args.check = True

    if args.check:
        check_installation()
        return

    if args.install:
        if platform.system() == "Windows":
            install_tesseract_windows()
        else:
            print("Automatic installation is only supported on Windows")
            print("For Linux/Mac, please use your package manager:")
            print("  Ubuntu/Debian: sudo apt install tesseract-ocr tesseract-ocr-ara")
            print("  macOS: brew install tesseract tesseract-lang")
        return

    if args.lang:
        install_language_pack(args.lang)
        return

    if args.pip:
        install_pytesseract()
        return


if __name__ == "__main__":
    main()
