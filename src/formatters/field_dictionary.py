"""
Bilingual field dictionary for Arabic-English document processing.

Provides comprehensive mappings for:
- Invoice fields (فاتورة)
- Company information
- Customer information
- Payment and summary fields
- Common Arabic terms

Based on Claude Code reference output: examples/Skysoft-Fatoora.md
"""

from typing import Dict, Tuple, Optional, List


# =============================================================================
# INVOICE FIELDS - Complete Arabic-English Dictionary
# =============================================================================

INVOICE_FIELDS: Dict[str, str] = {
    # === Document Type ===
    "فاتورة": "Invoice",
    "فاتورة ضريبية": "Tax Invoice",
    "فاتورة مبيعات": "Sales Invoice",
    "مبيعات": "Sales",
    "مشتريات": "Purchases",
    "عرض سعر": "Quotation",
    "أمر شراء": "Purchase Order",

    # === Company Information ===
    "شركة": "Company",
    "شركة فضاء البرمجيات": "Skysoft Co.",
    "لتقنية المعلومات": "For Information Technology",
    "للحلول المالية والادارية": "For Financial and Administrative Solutions",
    "المركز الرئيسي": "Main Center",
    "سكاي سوفت": "Skysoft",
    "الفرع": "Branch",

    # === Contact Information ===
    "هاتف": "Phone",
    "تلفون": "Phone",
    "التلفون": "Phone",
    "جوال": "Mobile",
    "فاكس": "Fax",
    "بريد": "Email",
    "البريد الإلكتروني": "Email",
    "العنوان": "Address",
    "المدينة": "City",
    "الدولة": "Country",
    "الرمز البريدي": "Postal Code",

    # === Invoice Header Fields ===
    "التاريخ": "Date",
    "تاريخ": "Date",
    "الموافق": "Hijri Date",
    "التاريخ الهجري": "Hijri Date",
    "الوقت": "Time",
    "الرقم": "Number",
    "رقم": "Number",
    "رقم الفاتورة": "Invoice Number",
    "النوع": "Type",
    "المرجع": "Reference",
    "مرجع": "Reference",
    "العملة": "Currency",
    "المندوب": "Representative",
    "مندوب المبيعات": "Sales Representative",
    "الصفحة": "Page",
    "من": "of",

    # === Tax Information ===
    "الرقم الضريبي": "Tax Number",
    "برقم ضريبي": "Tax Number",
    "رقم ضريبي": "Tax Number",
    "السجل التجاري": "Commercial Registration",
    "رقم السجل": "Registration Number",

    # === Customer Information ===
    "العميل": "Customer",
    "عميل": "Customer",
    "اسم العميل": "Customer Name",
    "الرصيد": "Balance",
    "رصيد": "Balance",
    "السائق": "Driver",
    "الوجهة": "Destination",
    "محلي": "Local",
    "دولي": "International",

    # === Invoice Items Table Headers ===
    "م": "No.",
    "رقم": "No.",
    "ر.الصنف": "Item Code",
    "رمز الصنف": "Item Code",
    "كود": "Code",
    "البيان": "Description",
    "الوصف": "Description",
    "الصنف": "Item",
    "المنتج": "Product",
    "الخدمة": "Service",
    "الكمية": "Quantity",
    "كمية": "Quantity",
    "الوحدة": "Unit",
    "وحدة": "Unit",
    "السعر": "Price",
    "سعر الوحدة": "Unit Price",
    "الصافي": "Net",
    "صافي": "Net",
    "المبلغ": "Amount",
    "الإجمالي": "Total",

    # === Units ===
    "عام": "General",
    "قطعة": "Piece",
    "علبة": "Box",
    "كرتون": "Carton",
    "كيلو": "Kilogram",
    "متر": "Meter",
    "لتر": "Liter",

    # === Tax Fields ===
    "ضريبة": "Tax",
    "ضريبة قيمة مضافة": "VAT",
    "ضريبة القيمة المضافة": "VAT",
    "ض.ق.م": "VAT",
    "الصافي+الضريبة": "Net + Tax",
    "شامل الضريبة": "Including Tax",
    "قبل الضريبة": "Before Tax",

    # === Summary Section ===
    "الاجمالي": "Total",
    "إجمالي": "Total",
    "المجموع": "Subtotal",
    "الاضافات": "Additions",
    "إضافات": "Additions",
    "الاجمالي الكلي": "Grand Total",
    "الخصم": "Discount",
    "خصم": "Discount",
    "نسبة الخصم": "Discount Rate",
    "الصافي شامل ض.ق": "Net including VAT",
    "صافي شامل الضريبة": "Net including VAT",
    "اجمالي ضريبة القيمة المضافة": "Total VAT",
    "إجمالي الكمية": "Total Quantity",
    "ملخص": "Summary",

    # === Amount in Words ===
    "فقط": "Only",
    "الف": "Thousand",
    "الفان": "Two Thousand",
    "ألف": "Thousand",
    "مائة": "Hundred",
    "مئة": "Hundred",
    "وثلاثمائة": "Three Hundred",
    "ريال": "Riyal",
    "ريالا": "Riyals",
    "ريالات": "Riyals",
    "لاغير": "Only",
    "لا غير": "Only",
    "سعودي": "Saudi",

    # === Payment Terms ===
    "البائع": "Seller",
    "المستلم": "Receiver",
    "المشتري": "Buyer",
    "آجل": "Credit",
    "نقدي": "Cash",
    "نقد": "Cash",
    "شيك": "Check",
    "تحويل": "Transfer",
    "بطاقة": "Card",

    # === Additional Info ===
    "الاستحقاق": "Due Date",
    "تاريخ الاستحقاق": "Due Date",
    "المستخدم": "User",
    "رقم النسخة": "Copy No.",
    "ملاحظات": "Notes",
    "ملاحظة": "Note",
    "شروط": "Terms",
    "الشروط والأحكام": "Terms and Conditions",

    # === Common Terms ===
    "صيانة": "Maintenance",
    "نظام": "System",
    "الخوارزمي": "Al-Khawarizmi",
    "صيانة نظام الخوارزمي": "Al-Khawarizmi System Maintenance",
    "برنامج": "Software",
    "تركيب": "Installation",
    "تدريب": "Training",
    "دعم فني": "Technical Support",
    "اشتراك": "Subscription",
    "تجديد": "Renewal",
    "ترخيص": "License",

    # === Status ===
    "مدفوع": "Paid",
    "غير مدفوع": "Unpaid",
    "جزئي": "Partial",
    "ملغي": "Cancelled",
    "معلق": "Pending",

    # === Signatures ===
    "التوقيع": "Signature",
    "توقيع البائع": "Seller Signature",
    "توقيع المستلم": "Receiver Signature",
    "الختم": "Stamp",
}

# Reverse mapping (English -> Arabic)
INVOICE_FIELDS_EN_AR: Dict[str, str] = {v: k for k, v in INVOICE_FIELDS.items()}


# =============================================================================
# SECTION HEADERS
# =============================================================================

SECTION_HEADERS: Dict[str, str] = {
    "معلومات الشركة": "Company Information",
    "بيانات الشركة": "Company Information",
    "معلومات العميل": "Customer Information",
    "بيانات العميل": "Customer Information",
    "تفاصيل الفاتورة": "Invoice Details",
    "رأس الفاتورة": "Invoice Header",
    "بنود الفاتورة": "Invoice Items",
    "البنود": "Items",
    "الملخص": "Summary",
    "المجموع": "Totals",
    "التوقيعات": "Signatures",
    "ملاحظات": "Notes",
    "معلومات إضافية": "Additional Information",
}

SECTION_HEADERS_EN_AR: Dict[str, str] = {v: k for k, v in SECTION_HEADERS.items()}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_english(arabic_text: str) -> str:
    """
    Get English translation for Arabic text.

    Args:
        arabic_text: Arabic text to translate

    Returns:
        English translation or original text if not found
    """
    # Try exact match first
    if arabic_text in INVOICE_FIELDS:
        return INVOICE_FIELDS[arabic_text]

    # Try section headers
    if arabic_text in SECTION_HEADERS:
        return SECTION_HEADERS[arabic_text]

    # Try partial match (for compound terms)
    for ar, en in INVOICE_FIELDS.items():
        if ar in arabic_text:
            return en

    return arabic_text


def get_arabic(english_text: str) -> str:
    """
    Get Arabic translation for English text.

    Args:
        english_text: English text to translate

    Returns:
        Arabic translation or empty string if not found
    """
    # Try exact match first
    if english_text in INVOICE_FIELDS_EN_AR:
        return INVOICE_FIELDS_EN_AR[english_text]

    # Try section headers
    if english_text in SECTION_HEADERS_EN_AR:
        return SECTION_HEADERS_EN_AR[english_text]

    return ""


def get_bilingual(text: str, source_lang: str = "auto") -> Tuple[str, str]:
    """
    Get bilingual representation of text.

    Args:
        text: The text to translate
        source_lang: Source language ("ar", "en", or "auto" to detect)

    Returns:
        Tuple of (english, arabic) text
    """
    if source_lang == "auto":
        # Detect if text contains Arabic characters
        has_arabic = any('\u0600' <= c <= '\u06FF' for c in text)
        source_lang = "ar" if has_arabic else "en"

    if source_lang == "ar":
        english = get_english(text)
        return (english, text)
    else:
        arabic = get_arabic(text)
        return (text, arabic)


def is_arabic_text(text: str) -> bool:
    """
    Check if text is primarily Arabic.

    Args:
        text: Text to check

    Returns:
        True if text is mostly Arabic
    """
    if not text:
        return False

    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    total_chars = len(text.replace(' ', ''))

    if total_chars == 0:
        return False

    return arabic_chars / total_chars > 0.3


def is_bilingual_text(text: str) -> bool:
    """
    Check if text contains both Arabic and English.

    Args:
        text: Text to check

    Returns:
        True if text contains both languages
    """
    has_arabic = any('\u0600' <= c <= '\u06FF' for c in text)
    has_latin = any('a' <= c.lower() <= 'z' for c in text)
    return has_arabic and has_latin


def extract_field_value(text: str, field_ar: str) -> Optional[str]:
    """
    Extract value for a field from text.

    Looks for patterns like "الحقل: القيمة" or "الحقل القيمة"

    Args:
        text: Text to search in
        field_ar: Arabic field name to look for

    Returns:
        Extracted value or None
    """
    import re

    # Pattern 1: field: value
    pattern1 = rf"{field_ar}\s*[:\-]\s*(.+?)(?:\n|$)"
    match = re.search(pattern1, text)
    if match:
        return match.group(1).strip()

    # Pattern 2: field value (for table cells)
    pattern2 = rf"{field_ar}\s+(\S+)"
    match = re.search(pattern2, text)
    if match:
        return match.group(1).strip()

    return None


def get_all_field_translations() -> List[Tuple[str, str]]:
    """
    Get all field translations as a list of (arabic, english) tuples.

    Returns:
        List of translation pairs
    """
    return [(ar, en) for ar, en in INVOICE_FIELDS.items()]


# =============================================================================
# FIELD CATEGORIES
# =============================================================================

DOCUMENT_TYPE_KEYWORDS = [
    "فاتورة", "فاتورة ضريبية", "عرض سعر", "أمر شراء"
]

COMPANY_KEYWORDS = [
    "شركة", "هاتف", "العنوان", "الرقم الضريبي", "السجل التجاري"
]

CUSTOMER_KEYWORDS = [
    "العميل", "العنوان", "الرصيد", "التلفون"
]

INVOICE_HEADER_KEYWORDS = [
    "التاريخ", "الموافق", "الوقت", "الرقم", "النوع", "المرجع", "المندوب"
]

TABLE_HEADER_KEYWORDS = [
    "م", "البيان", "الكمية", "الوحدة", "السعر", "الصافي", "ضريبة"
]

SUMMARY_KEYWORDS = [
    "الاجمالي", "الاضافات", "الخصم", "الصافي", "ضريبة القيمة المضافة"
]


# =============================================================================
# FUZZY MATCHING SUPPORT
# =============================================================================

# Import fuzzy matching utilities (optional - falls back gracefully)
try:
    from ..utils.arabic_utils import normalize_arabic, is_arabic, similarity_ratio
    from ..utils.fuzzy_match import (
        fuzzy_best_match, fuzzy_field_match as _fuzzy_field_match,
        fuzzy_contains, FuzzyMatch
    )
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
    normalize_arabic = lambda x: x
    is_arabic = lambda x: any('\u0600' <= c <= '\u06FF' for c in x)


def get_english_fuzzy(arabic_text: str,
                      threshold: int = 70,
                      normalize: bool = True) -> Tuple[str, float]:
    """
    Get English translation for Arabic text using fuzzy matching.

    This function handles OCR errors by using fuzzy string matching
    to find the best matching field even when characters are corrupted.

    Args:
        arabic_text: Arabic text to translate (may contain OCR errors)
        threshold: Minimum similarity score (0-100) for a match
        normalize: Whether to normalize Arabic text before matching

    Returns:
        Tuple of (english_translation, confidence_score)
        If no match found, returns (original_text, 0.0)

    Example:
        >>> get_english_fuzzy("فانورة")  # OCR error for فاتورة
        ('Invoice', 85.7)
    """
    if not arabic_text:
        return arabic_text, 0.0

    # Try exact match first (fastest)
    if arabic_text in INVOICE_FIELDS:
        return INVOICE_FIELDS[arabic_text], 100.0

    if arabic_text in SECTION_HEADERS:
        return SECTION_HEADERS[arabic_text], 100.0

    # Normalize and try again
    if normalize:
        normalized = normalize_arabic(arabic_text)
        if normalized in INVOICE_FIELDS:
            return INVOICE_FIELDS[normalized], 98.0
        if normalized in SECTION_HEADERS:
            return SECTION_HEADERS[normalized], 98.0

    # Use fuzzy matching if available
    if FUZZY_AVAILABLE:
        # Combine all fields for matching
        all_fields = {**INVOICE_FIELDS, **SECTION_HEADERS}
        keys = list(all_fields.keys())

        match = fuzzy_best_match(arabic_text, keys, threshold=threshold, normalize=normalize)
        if match:
            return all_fields[match.match], match.score

    # Fallback: partial substring match (original behavior)
    if normalize:
        arabic_text = normalize_arabic(arabic_text)

    for ar, en in INVOICE_FIELDS.items():
        ar_normalized = normalize_arabic(ar) if normalize else ar
        if ar_normalized in arabic_text or arabic_text in ar_normalized:
            return en, 75.0

    return arabic_text, 0.0


def fuzzy_field_lookup(text: str,
                       threshold: int = 70) -> Optional[Tuple[str, str, float]]:
    """
    Look up a field using fuzzy matching.

    Args:
        text: Text to look up (Arabic)
        threshold: Minimum match score

    Returns:
        Tuple of (arabic_field, english_translation, score) or None

    Example:
        >>> fuzzy_field_lookup("العملي")  # OCR error for العميل
        ('العميل', 'Customer', 80.5)
    """
    if not text or not FUZZY_AVAILABLE:
        return None

    all_fields = {**INVOICE_FIELDS, **SECTION_HEADERS}
    arabic_key, english_value, score = _fuzzy_field_match(
        text, all_fields, threshold=threshold
    )

    if arabic_key:
        return arabic_key, english_value, score

    return None


def extract_field_value_fuzzy(text: str,
                              field_ar: str,
                              threshold: int = 70) -> Optional[Tuple[str, float]]:
    """
    Extract value for a field using fuzzy matching.

    Handles OCR errors in both the field name and searches for the
    best match in the text.

    Args:
        text: Full text to search in
        field_ar: Arabic field name to look for (may contain OCR errors)
        threshold: Minimum fuzzy match score

    Returns:
        Tuple of (extracted_value, confidence_score) or None

    Example:
        >>> extract_field_value_fuzzy("العملي: قرطاسية اصل", "العميل")
        ('قرطاسية اصل', 85.0)
    """
    import re

    if not text or not field_ar:
        return None

    # Normalize for comparison
    normalized_text = normalize_arabic(text)
    normalized_field = normalize_arabic(field_ar)

    # Split text into lines for line-by-line matching
    lines = text.split('\n')

    for line in lines:
        line_normalized = normalize_arabic(line)

        # Check if field is (fuzzy) present in line
        if FUZZY_AVAILABLE and fuzzy_contains(line_normalized, normalized_field, threshold):
            # Extract value after the field name
            # Try colon separator first
            for delim in [':', '؛', '،', '-']:
                if delim in line:
                    parts = line.split(delim, 1)
                    if len(parts) == 2:
                        potential_field = normalize_arabic(parts[0].strip())
                        # Verify this is actually our field
                        if FUZZY_AVAILABLE:
                            match = fuzzy_best_match(
                                potential_field,
                                [normalized_field],
                                threshold=threshold
                            )
                            if match:
                                return parts[1].strip(), match.score

            # No delimiter - try to extract value by position
            words = line.split()
            for i, word in enumerate(words):
                word_normalized = normalize_arabic(word)
                if FUZZY_AVAILABLE:
                    match = fuzzy_best_match(
                        word_normalized,
                        [normalized_field],
                        threshold=threshold
                    )
                    if match and i + 1 < len(words):
                        # Value is everything after the matched field
                        value = ' '.join(words[i + 1:])
                        return value, match.score

    # Fallback to exact match
    result = extract_field_value(text, field_ar)
    if result:
        return result, 100.0

    return None


def get_all_fuzzy_matches(text: str,
                          threshold: int = 65,
                          limit: int = 20) -> List[Dict]:
    """
    Find all field matches in text using fuzzy matching.

    Useful for extracting multiple key-value pairs from OCR output.

    Args:
        text: Text to search (typically full OCR output)
        threshold: Minimum match score
        limit: Maximum number of matches to return

    Returns:
        List of dicts with keys: arabic_field, english_field, value, score

    Example:
        >>> get_all_fuzzy_matches("التاريخ 2024-12-21\\nالعملي قرطاسية")
        [
            {'arabic': 'التاريخ', 'english': 'Date', 'value': '2024-12-21', 'score': 100},
            {'arabic': 'العميل', 'english': 'Customer', 'value': 'قرطاسية', 'score': 85}
        ]
    """
    results = []
    seen_fields = set()

    all_fields = {**INVOICE_FIELDS, **SECTION_HEADERS}

    lines = text.split('\n')

    for line in lines:
        if not line.strip():
            continue

        # Try to extract key-value from this line
        for delim in [':', '؛', '،', ' ']:
            if delim in line:
                parts = line.split(delim, 1)
                if len(parts) == 2:
                    potential_key = parts[0].strip()
                    value = parts[1].strip()

                    if not potential_key or len(potential_key) > 50:
                        continue

                    # Fuzzy match against known fields
                    english, score = get_english_fuzzy(potential_key, threshold=threshold)

                    if score >= threshold and english not in seen_fields:
                        seen_fields.add(english)
                        results.append({
                            'arabic': potential_key,
                            'english': english,
                            'value': value,
                            'score': score
                        })

                        if len(results) >= limit:
                            return results
                    break

    return results


def categorize_field(arabic_text: str, threshold: int = 70) -> Optional[str]:
    """
    Categorize an Arabic field into its section using fuzzy matching.

    Args:
        arabic_text: Arabic field name

    Returns:
        Category name: 'document_type', 'company', 'customer',
        'invoice_header', 'table_header', 'summary', or None
    """
    categories = {
        'document_type': DOCUMENT_TYPE_KEYWORDS,
        'company': COMPANY_KEYWORDS,
        'customer': CUSTOMER_KEYWORDS,
        'invoice_header': INVOICE_HEADER_KEYWORDS,
        'table_header': TABLE_HEADER_KEYWORDS,
        'summary': SUMMARY_KEYWORDS,
    }

    if not FUZZY_AVAILABLE:
        # Exact match fallback
        for category, keywords in categories.items():
            if any(kw in arabic_text for kw in keywords):
                return category
        return None

    best_category = None
    best_score = threshold

    for category, keywords in categories.items():
        match = fuzzy_best_match(arabic_text, keywords, threshold=threshold)
        if match and match.score > best_score:
            best_score = match.score
            best_category = category

    return best_category
