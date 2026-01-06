# OCR Tool Output Analysis

**Test Image:** `examples/Screenshot 2026-01-06 104028.png`
**Analysis Date:** 2026-01-06
**Engine:** PaddleOCR PP-OCRv5 (Arabic)
**Processing Time:** ~21 seconds

---

## Raw OCR Output

### Extracted Text Blocks (41 total)

| # | Text | Confidence | Issue |
|---|------|------------|-------|
| 1 | demo_faten2 | 99.91% | OK |
| 2 | فاتورة شراء | 97.27% | OK |
| 3 | demo_faten2 | 99.91% | OK (duplicate) |
| 4 | مصنع اغذية الخليج للتموين | 93.56% | OK |
| 5 | الرقمالمرجعي | 85.59% | MERGED (missing space, missing value) |
| 6 | التاريخ:03/01/2026 12:30 | 93.93% | OK |
| 7 | المعرض | 99.72% | OK |
| 8 | Address, City | 99.94% | OK |
| 9 | الدمام المنطقة الشرقية | 95.76% | OK |
| 10 | الجالةتم الاستلام | 87.10% | MERGED + SPELLING (الحالة) |
| 11 | Saudi Arabia | 99.61% | OK |
| 12 | حالة الدفع آجل | 88.34% | OK |
| 13 | الهاتف134 | 87.45% | TRUNCATED (missing digits) |
| 14 | الرقمالضريبيالهاتف94 | 80.41% | MERGED + TRUNCATED |
| 15 | البريد الإلكتروني | 92.47% | OK |
| 16 | smartlives@smartlives.wsالبريد الإلكتروني | 93.87% | MERGED |
| 17 | المجموع | 99.67% | OK |
| 18 | الضرية | 96.44% | SPELLING (missing ب) |
| 19 | تكلفة الوحدة | 99.46% | OK |
| 20 | الكمية | 93.35% | OK |
| 21 | الوصف | 99.01% | OK |
| 22 | 60.72 | 99.98% | OK |
| 23 | (15) 7.92 | 99.55% | OK |
| 24 | 3.37 | 99.97% | OK |
| 25 | 18.00 | 99.93% | OK |
| 26 | برونتو كوكيز بقطع الشوكولاتةج | 79.55% | TRUNCATED (missing 40جم, trailing ج) |
| 27 | 51.06 | 99.91% | OK |
| 28 | (15) 6.66 | 98.29% | OK |
| 29 | 4.26 | 99.70% | OK |
| 30 | 12.00 | 99.92% | OK |
| 31 | 6287003972716 - خواتم | 98.77% | OK |
| 32 | 11.78 | 96.09% | DIGIT LOSS (should be 111.78) |
| 33 | 14.58 | 99.99% | OK |
| 34 | المجموع | 95.73% | OK |
| 35 | 11.78 | 99.45% | DIGIT LOSS (should be 111.78) |
| 36 | إجماليالمبلغ | 93.36% | MERGED |
| 37 | .00 | 98.56% | DIGIT LOSS (should be 0.00) |
| 38 | (A) مدفوع | 89.50% | GARBLED (SAR misread as A) |
| 39 | 1.78 | 99.91% | DIGIT LOSS (should be 111.78) |
| 40 | الرصيد | 93.19% | OK |
| 41 | Icaبl هuner : طةwlوu شاء | 68.71% | COMPLETELY GARBLED |

---

## Missing Data

### Not Detected

| Data Type | Expected Value | Notes |
|-----------|----------------|-------|
| Reference Number | PO/0544 | Not detected at all |
| Tax Number | 300050201500003 | Not detected |
| Phone 1 | 594807689 | Only "134" detected |
| Phone 2 | 012345678 | Only "94" detected |
| Item 1 Barcode | 6281102740016 | Not detected |
| Item 1 Weight | 40جم | Not detected |
| Row Numbers | 1, 2 | Not detected |
| SAR Labels | (SAR) | Misread as (A) |
| Footer Creator | تم الإنشاء بواسطة : ouner ابوعلى | Garbled |
| Footer Date | التاريخ : 03/01/2026 12:30 | Not detected |

---

## Issue Categories

### 1. Word Merging (No Spaces)

| OCR Output | Expected | Cause |
|------------|----------|-------|
| الرقمالمرجعي | الرقم المرجعي | Arabic words merged |
| الجالةتم الاستلام | الحالة: تم الاستلام | Merged + colon missing |
| الرقمالضريبيالهاتف | الرقم الضريبي الهاتف | Multiple words merged |
| إجماليالمبلغ | إجمالي المبلغ | Words merged |
| smartlives@smartlives.wsالبريد | ... البريد | Email merged with label |

### 2. Leading Digit Loss

| OCR Output | Expected | Lost Digits |
|------------|----------|-------------|
| 11.78 | 111.78 | Leading "1" |
| .00 | 0.00 | Leading "0" |
| 1.78 | 111.78 | Leading "11" |
| 134 | 594807689 | Most digits lost |
| 94 | 012345678 | Most digits lost |

### 3. Spelling Errors

| OCR Output | Expected | Error Type |
|------------|----------|------------|
| الضرية | الضريبة | Missing ب |
| الجالة | الحالة | Wrong letter ج→ح |

### 4. Garbled Text (Low Confidence)

| OCR Output | Expected | Confidence |
|------------|----------|------------|
| Icaبl هuner : طةwlوu شاء | تم الإنشاء بواسطة : ouner ابوعلى | 68.71% |
| (A) مدفوع | (SAR) مدفوع | 89.50% |

---

## Full Text Reconstruction

### Current Output (Unstructured)

```
demo_faten2
فاتورة شراء
demo_faten2
مصنع اغذية الخليج للتموين
الرقمالمرجعي
التاريخ:03/01/2026 12:30
المعرض
Address, City
الدمام المنطقة الشرقية
الجالةتم الاستلام
Saudi Arabia
حالة الدفع آجل
الهاتف134
الرقمالضريبيالهاتف94
البريد الإلكتروني
smartlives@smartlives.wsالبريد الإلكتروني
المجموع
الضرية
تكلفة الوحدة
الكمية
الوصف
60.72
(15) 7.92
3.37
18.00
برونتو كوكيز بقطع الشوكولاتةج
51.06
(15) 6.66
4.26
12.00
6287003972716 - خواتم
11.78
14.58
المجموع
11.78
إجماليالمبلغ
.00
(A) مدفوع
1.78
الرصيد
Icaبl هuner : طةwlوu شاء
```

---

## Quality Metrics

| Metric | Score | Notes |
|--------|-------|-------|
| Text Detection Rate | 41/~55 blocks | ~75% |
| Number Accuracy | 70% | Critical digit loss |
| Arabic Word Accuracy | 60% | Many merged/misspelled |
| English Text Accuracy | 95% | Good |
| Structure Recognition | 20% | No table structure |
| Overall Quality | 55% | Significant issues |

---

## Root Causes

### 1. Detection Resolution
- `text_det_limit_side_len=1280` insufficient for small text
- Numbers in corners/edges missed

### 2. RTL Processing
- Arabic text blocks not properly separated
- Word boundaries not detected

### 3. Confidence Threshold
- `text_rec_score_thresh=0.25` allows garbled text through
- Should filter blocks below 0.7 for critical fields

### 4. No Post-processing
- No digit restoration
- No word separation
- No spelling correction
- No structure analysis
