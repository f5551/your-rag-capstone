from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path
from typing import Any

import pymupdf
import pytesseract
from dotenv import load_dotenv
from PIL import Image
from pypdf import PdfReader


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

TESSERACT_CMD = os.getenv("TESSERACT_CMD")

if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


# ============================================================
# QUALITY SETTINGS
# ============================================================

MIN_TEXT_LENGTH = 20

GOOD_SCORE = 70
SUSPICIOUS_SCORE = 45

LOW_WHITESPACE_THRESHOLD = 0.055

LONG_TOKEN_THRESHOLD = 45
VERY_LONG_TOKEN_THRESHOLD = 80

SINGLE_CHAR_LINES_THRESHOLD = 0.25
HARD_SINGLE_CHAR_LINES_THRESHOLD = 0.50

UNEXPECTED_SCRIPT_THRESHOLD = 0.08
SEVERE_UNEXPECTED_SCRIPT_THRESHOLD = 0.20
HARD_UNEXPECTED_SCRIPT_THRESHOLD = 0.50

REPLACEMENT_CHAR_THRESHOLD = 0.01


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text: str) -> str:
    """
    Conservative cleaning.

    Does not aggressively modify punctuation, ISO clause
    numbers, document structure, or corrupted words.
    """

    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = text.replace("\u200b", "")
    text = text.replace("\ufeff", "")

    lines = [
        re.sub(r"[ \t]{2,}", " ", line.rstrip())
        for line in text.split("\n")
    ]

    text = "\n".join(lines)
    text = re.sub(r"\n{4,}", "\n\n\n", text)

    return text.strip()


# ============================================================
# SCRIPT DETECTION
# ============================================================

def _detect_script(char: str) -> str:
    if not char.isalpha():
        return "non_letter"

    name = unicodedata.name(char, "")

    if "LATIN" in name:
        return "latin"

    if "ARABIC" in name:
        return "arabic"

    if "CYRILLIC" in name:
        return "cyrillic"

    if any(
        marker in name
        for marker in (
            "CJK",
            "HIRAGANA",
            "KATAKANA",
            "HANGUL",
            "IDEOGRAPH",
        )
    ):
        return "cjk"

    if "GREEK" in name:
        return "greek"

    return "other"


def _script_metrics(
    text: str,
    expected_language: str = "eng",
) -> dict[str, Any]:

    letters = [char for char in text if char.isalpha()]

    if not letters:
        return {
            "letters": 0,
            "latin_ratio": 0.0,
            "arabic_ratio": 0.0,
            "cyrillic_ratio": 0.0,
            "cjk_ratio": 0.0,
            "greek_ratio": 0.0,
            "other_script_ratio": 0.0,
            "unexpected_script_ratio": 0.0,
        }

    counts = {
        "latin": 0,
        "arabic": 0,
        "cyrillic": 0,
        "cjk": 0,
        "greek": 0,
        "other": 0,
    }

    for char in letters:
        script = _detect_script(char)

        if script in counts:
            counts[script] += 1

    total = len(letters)

    ratios = {
        key: value / total
        for key, value in counts.items()
    }

    language = (expected_language or "eng").lower()

    if language.startswith("en"):
        expected_scripts = {"latin"}

    elif language.startswith("ar"):
        expected_scripts = {"arabic"}

    elif language in {"eng+ara", "ara+eng", "en+ar", "ar+en"}:
        expected_scripts = {"latin", "arabic"}

    else:
        # Unknown language: do not aggressively reject scripts.
        expected_scripts = set(counts.keys())

    expected_count = sum(
        counts.get(script, 0)
        for script in expected_scripts
    )

    unexpected_ratio = 1.0 - (expected_count / total)

    return {
        "letters": total,
        "latin_ratio": round(ratios["latin"], 4),
        "arabic_ratio": round(ratios["arabic"], 4),
        "cyrillic_ratio": round(ratios["cyrillic"], 4),
        "cjk_ratio": round(ratios["cjk"], 4),
        "greek_ratio": round(ratios["greek"], 4),
        "other_script_ratio": round(ratios["other"], 4),
        "unexpected_script_ratio": round(unexpected_ratio, 4),
    }


# ============================================================
# QUALITY METRICS
# ============================================================

def _single_char_line_ratio(
    text: str,
) -> tuple[float, int, int]:

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        return 0.0, 0, 0

    single_char_lines = sum(
        1
        for line in lines
        if len(re.sub(r"\s+", "", line)) == 1
        and re.sub(r"\s+", "", line).isalpha()
    )

    ratio = single_char_lines / len(lines)

    return ratio, single_char_lines, len(lines)


def _token_metrics(text: str) -> dict[str, Any]:
    tokens = re.findall(r"\S+", text)

    if not tokens:
        return {
            "token_count": 0,
            "average_token_length": 0.0,
            "max_token_length": 0,
            "long_token_count": 0,
            "long_token_ratio": 0.0,
        }

    lengths = [len(token) for token in tokens]

    long_tokens = [
        length
        for length in lengths
        if length >= LONG_TOKEN_THRESHOLD
    ]

    return {
        "token_count": len(tokens),
        "average_token_length": round(
            sum(lengths) / len(lengths),
            2,
        ),
        "max_token_length": max(lengths),
        "long_token_count": len(long_tokens),
        "long_token_ratio": round(
            len(long_tokens) / len(tokens),
            4,
        ),
    }


# ============================================================
# TEXT QUALITY
# ============================================================

def text_quality(
    text: str,
    expected_language: str = "eng",
) -> dict[str, Any]:
    """
    Evaluate extracted text.

    Returns:
        score
        quality: good / suspicious / rejected / empty
        reasons
        metrics
    """

    cleaned = clean_text(text)

    if not cleaned:
        return {
            "score": 0,
            "quality": "empty",
            "reasons": ["empty_text"],
            "metrics": {
                "char_count": 0,
            },
        }

    char_count = len(cleaned)
    alnum_count = sum(char.isalnum() for char in cleaned)
    whitespace_count = sum(char.isspace() for char in cleaned)
    printable_count = sum(
        char.isprintable() or char in "\n\t"
        for char in cleaned
    )
    replacement_count = cleaned.count("\ufffd")

    alnum_ratio = alnum_count / max(char_count, 1)
    whitespace_ratio = whitespace_count / max(char_count, 1)
    printable_ratio = printable_count / max(char_count, 1)
    replacement_ratio = replacement_count / max(char_count, 1)

    token_metrics = _token_metrics(cleaned)

    (
        single_char_ratio,
        single_char_count,
        line_count,
    ) = _single_char_line_ratio(cleaned)

    script_metrics = _script_metrics(
        cleaned,
        expected_language=expected_language,
    )

    metrics = {
        "char_count": char_count,
        "alnum_ratio": round(alnum_ratio, 4),
        "whitespace_ratio": round(whitespace_ratio, 4),
        "printable_ratio": round(printable_ratio, 4),
        "replacement_char_ratio": round(replacement_ratio, 4),

        "line_count": line_count,
        "single_char_line_count": single_char_count,
        "single_char_line_ratio": round(single_char_ratio, 4),

        **token_metrics,
        **script_metrics,
    }

    reasons: list[str] = []
    score = 100
    hard_reject = False

    # --------------------------------------------------------
    # Very short text
    # --------------------------------------------------------

    if char_count < MIN_TEXT_LENGTH or alnum_count < 8:
        score -= 50
        reasons.append("very_short_text")

    # --------------------------------------------------------
    # Printable characters
    # --------------------------------------------------------

    if printable_ratio < 0.95:
        score -= 20
        reasons.append("low_printable_ratio")

    # --------------------------------------------------------
    # Unicode replacement characters
    # --------------------------------------------------------

    if replacement_ratio > REPLACEMENT_CHAR_THRESHOLD:
        score -= 30
        reasons.append("replacement_characters")

    # --------------------------------------------------------
    # Low whitespace
    #
    # Typical glued text:
    # Theorganizationshallestablishimplement...
    # --------------------------------------------------------

    low_whitespace = (
        char_count >= 120
        and whitespace_ratio < LOW_WHITESPACE_THRESHOLD
    )

    if low_whitespace:
        score -= 25
        reasons.append("low_whitespace")

    # --------------------------------------------------------
    # Long tokens
    #
    # A long token alone is not sufficient evidence of
    # corruption because PDFs may contain URLs, identifiers,
    # standards references, or layout artifacts.
    #
    # Long tokens become a stronger signal when combined
    # with abnormally low whitespace.
    # --------------------------------------------------------

    max_token_length = token_metrics["max_token_length"]
    long_token_ratio = token_metrics["long_token_ratio"]

    if max_token_length >= VERY_LONG_TOKEN_THRESHOLD:
        reasons.append("very_long_token")
        score -= 10

        if low_whitespace:
            score -= 20

    elif max_token_length >= LONG_TOKEN_THRESHOLD:
        reasons.append("long_token")
        score -= 5

    if long_token_ratio >= 0.05:
        if (
            "long_token" not in reasons
            and "very_long_token" not in reasons
        ):
            reasons.append("many_long_tokens")

        score -= 5

    # --------------------------------------------------------
    # Single-character line corruption
    # --------------------------------------------------------

    if (
        line_count >= 5
        and single_char_ratio >= SINGLE_CHAR_LINES_THRESHOLD
    ):
        score -= 60
        reasons.append("single_char_lines")

    if (
        line_count >= 5
        and single_char_ratio >= HARD_SINGLE_CHAR_LINES_THRESHOLD
    ):
        hard_reject = True

    # --------------------------------------------------------
    # Unexpected scripts
    # --------------------------------------------------------

    unexpected_ratio = script_metrics[
        "unexpected_script_ratio"
    ]

    if unexpected_ratio >= SEVERE_UNEXPECTED_SCRIPT_THRESHOLD:
        score -= 60
        reasons.append("unexpected_script")

    elif unexpected_ratio >= UNEXPECTED_SCRIPT_THRESHOLD:
        score -= 30
        reasons.append("unexpected_script")

    if unexpected_ratio >= HARD_UNEXPECTED_SCRIPT_THRESHOLD:
        hard_reject = True

    # --------------------------------------------------------
    # Low alphanumeric content
    # --------------------------------------------------------

    if char_count >= 50 and alnum_ratio < 0.30:
        score -= 20
        reasons.append("low_alnum_ratio")

    score = max(0, min(100, score))

    # --------------------------------------------------------
    # Final quality
    # --------------------------------------------------------

    if hard_reject:
        quality = "rejected"

    elif score >= GOOD_SCORE:
        quality = "good"

    elif score >= SUSPICIOUS_SCORE:
        quality = "suspicious"

    else:
        quality = "rejected"

    metrics["hard_reject"] = hard_reject

    return {
        "score": score,
        "quality": quality,
        "reasons": reasons,
        "metrics": metrics,
    }


def diagnose_page(
    text: str,
    expected_language: str = "eng",
) -> dict[str, Any]:

    return text_quality(
        text,
        expected_language=expected_language,
    )


# ============================================================
# PYMUPDF EXTRACTION
# ============================================================

def extract_page_pymupdf(
    pdf_document: pymupdf.Document,
    page_index: int,
) -> dict[str, Any]:

    try:
        page = pdf_document.load_page(page_index)

        text = page.get_text("text") or ""

        return {
            "text": clean_text(text),
            "success": True,
            "error": None,
        }

    except Exception as exc:
        return {
            "text": "",
            "success": False,
            "error": str(exc),
        }


# ============================================================
# OCR
# ============================================================

def ocr_page(
    pdf_document: pymupdf.Document,
    page_index: int,
    ocr_language: str = "eng",
    dpi: int = 300,
) -> dict[str, Any]:

    try:
        page = pdf_document.load_page(page_index)

        zoom = dpi / 72
        matrix = pymupdf.Matrix(zoom, zoom)

        pix = page.get_pixmap(
            matrix=matrix,
            alpha=False,
        )

        image = Image.frombytes(
            "RGB",
            [pix.width, pix.height],
            pix.samples,
        )

        text = pytesseract.image_to_string(
            image,
            lang=ocr_language,
            config="--psm 6",
        )

        return {
            "text": clean_text(text),
            "success": True,
            "error": None,
        }

    except Exception as exc:
        return {
            "text": "",
            "success": False,
            "error": str(exc),
        }


# ============================================================
# VISUAL BLANK PAGE DETECTION
# ============================================================

def is_visually_blank_page(
    pdf_document: pymupdf.Document,
    page_index: int,
    dpi: int = 96,
    white_threshold: int = 245,
    max_ink_ratio: float = 0.0005,
) -> dict[str, Any]:
    """
    Conservatively determine whether a rendered PDF page
    is visually blank.
    """

    try:
        page = pdf_document.load_page(page_index)

        zoom = dpi / 72
        matrix = pymupdf.Matrix(zoom, zoom)

        pix = page.get_pixmap(
            matrix=matrix,
            alpha=False,
        )

        image = Image.frombytes(
            "RGB",
            [pix.width, pix.height],
            pix.samples,
        )

        grayscale = image.convert("L")

        # Downscale for faster analysis.
        max_dimension = 600
        width, height = grayscale.size

        scale = min(
            1.0,
            max_dimension / max(width, height),
        )

        if scale < 1.0:
            grayscale = grayscale.resize(
                (
                    max(1, int(width * scale)),
                    max(1, int(height * scale)),
                )
            )

        pixels = list(grayscale.getdata())

        if not pixels:
            return {
                "is_blank": False,
                "ink_ratio": None,
                "mean_brightness": None,
                "width": pix.width,
                "height": pix.height,
                "error": "no_pixels",
            }

        total_pixels = len(pixels)

        ink_pixels = sum(
            1
            for pixel in pixels
            if pixel < white_threshold
        )

        ink_ratio = ink_pixels / total_pixels
        mean_brightness = sum(pixels) / total_pixels

        return {
            "is_blank": ink_ratio <= max_ink_ratio,
            "ink_ratio": round(ink_ratio, 6),
            "mean_brightness": round(mean_brightness, 2),
            "width": pix.width,
            "height": pix.height,
            "error": None,
        }

    except Exception as exc:
        return {
            "is_blank": False,
            "ink_ratio": None,
            "mean_brightness": None,
            "width": 0,
            "height": 0,
            "error": str(exc),
        }


# ============================================================
# ATTEMPT HELPERS
# ============================================================

def _attempt_record(
    loader: str,
    diagnostic: dict[str, Any],
    error: str | None = None,
) -> dict[str, Any]:

    return {
        "loader": loader,
        "quality": diagnostic.get("quality"),
        "score": diagnostic.get("score", 0),
        "reasons": diagnostic.get("reasons", []),
        "metrics": diagnostic.get("metrics", {}),
        "error": error,
    }


def _best_candidate(
    candidates: list[dict[str, Any]],
) -> dict[str, Any] | None:

    valid = [
        candidate
        for candidate in candidates
        if candidate.get("text")
    ]

    if not valid:
        return None

    return max(
        valid,
        key=lambda candidate: candidate[
            "diagnostic"
        ]["score"],
    )


# ============================================================
# SMART PDF LOADER
# ============================================================

def load_pdf_smart(
    pdf_path: str | Path,
    expected_language: str = "eng",
    ocr_language: str = "eng",
    page_numbers: list[int] | None = None,
    force_ocr: bool = False,
) -> dict[str, Any]:
    """
    Extraction pipeline:

        pypdf
          ↓
        quality gate
          ↓
        PyMuPDF fallback
          ↓
        compare candidates
          ↓
        OCR when native extraction is not good
          ↓
        final quality gate

    Only GOOD text is exposed to ingestion.
    """

    pdf_path = Path(pdf_path)

    result = {
        "pages": [],
        "pdf_type": "unknown",
        "total_pages": 0,
        "processed_pages": 0,
        "status": "failed",

        "stats": {
            "accepted_pages": 0,
            "blank_pages": 0,
            "rejected_pages": 0,
            "failed_pages": 0,

            "pypdf_pages": 0,
            "pymupdf_pages": 0,
            "ocr_pages": 0,

            "fallback_pages": 0,
        },

        "error": None,
    }

    # ========================================================
    # OPEN PDF
    # ========================================================

    try:
        pymupdf_document = pymupdf.open(
            str(pdf_path)
        )

    except Exception as exc:
        result["error"] = (
            f"PyMuPDF open failed: {exc}"
        )

        return result

    result["total_pages"] = len(
        pymupdf_document
    )

    # ========================================================
    # OPEN PYPDF
    # ========================================================

    pdf_reader = None
    pypdf_open_error = None

    try:
        pdf_reader = PdfReader(
            str(pdf_path)
        )

    except Exception as exc:
        pypdf_open_error = str(exc)

    # ========================================================
    # PAGE SELECTION
    # ========================================================

    if page_numbers is None:
        selected_pages = list(
            range(
                result["total_pages"]
            )
        )

    else:
        selected_pages = [
            page_number - 1
            for page_number in page_numbers
            if 0
            <= page_number - 1
            < result["total_pages"]
        ]

    # ========================================================
    # PROCESS PAGES
    # ========================================================

    for page_index in selected_pages:

        page_number = page_index + 1

        attempts: list[
            dict[str, Any]
        ] = []

        candidates: list[
            dict[str, Any]
        ] = []

        # ----------------------------------------------------
        # 1. PYPDF
        # ----------------------------------------------------

        pypdf_text = ""
        pypdf_error = None

        if pdf_reader is not None:
            try:
                pypdf_text = (
                    pdf_reader.pages[
                        page_index
                    ].extract_text()
                    or ""
                )

                pypdf_text = clean_text(
                    pypdf_text
                )

            except Exception as exc:
                pypdf_error = str(exc)

        else:
            pypdf_error = (
                pypdf_open_error
            )

        pypdf_diagnostic = diagnose_page(
            pypdf_text,
            expected_language=expected_language,
        )

        attempts.append(
            _attempt_record(
                "pypdf",
                pypdf_diagnostic,
                pypdf_error,
            )
        )

        if pypdf_text:
            candidates.append(
                {
                    "loader": "pypdf",
                    "text": pypdf_text,
                    "diagnostic": pypdf_diagnostic,
                    "ocr_used": False,
                }
            )

        # ----------------------------------------------------
        # 2. PYMUPDF FALLBACK
        # ----------------------------------------------------

        need_pymupdf = (
            force_ocr
            or pypdf_diagnostic[
                "quality"
            ] != "good"
        )

        if need_pymupdf:
            pymupdf_result = (
                extract_page_pymupdf(
                    pymupdf_document,
                    page_index,
                )
            )

            pymupdf_text = (
                pymupdf_result["text"]
            )

            pymupdf_diagnostic = (
                diagnose_page(
                    pymupdf_text,
                    expected_language=expected_language,
                )
            )

            attempts.append(
                _attempt_record(
                    "pymupdf",
                    pymupdf_diagnostic,
                    pymupdf_result[
                        "error"
                    ],
                )
            )

            if pymupdf_text:
                candidates.append(
                    {
                        "loader": "pymupdf",
                        "text": pymupdf_text,
                        "diagnostic": pymupdf_diagnostic,
                        "ocr_used": False,
                    }
                )

        # ----------------------------------------------------
        # BEST NATIVE CANDIDATE
        # ----------------------------------------------------

        best_native = _best_candidate(
            candidates
        )

        native_good = (
            best_native is not None
            and best_native[
                "diagnostic"
            ]["quality"] == "good"
        )

        # ----------------------------------------------------
        # 3. OCR FALLBACK
        # ----------------------------------------------------

        need_ocr = (
            force_ocr
            or not native_good
        )

        if need_ocr:
            ocr_result = ocr_page(
                pymupdf_document,
                page_index,
                ocr_language=ocr_language,
            )

            ocr_text = (
                ocr_result["text"]
            )

            ocr_diagnostic = (
                diagnose_page(
                    ocr_text,
                    expected_language=expected_language,
                )
            )

            attempts.append(
                _attempt_record(
                    "tesseract",
                    ocr_diagnostic,
                    ocr_result["error"],
                )
            )

            if ocr_text:
                candidates.append(
                    {
                        "loader": "tesseract",
                        "text": ocr_text,
                        "diagnostic": ocr_diagnostic,
                        "ocr_used": True,
                    }
                )

        # ----------------------------------------------------
        # BEST CANDIDATE
        # ----------------------------------------------------

        best = _best_candidate(
            candidates
        )

        has_good_candidate = any(
            candidate[
                "diagnostic"
            ]["quality"] == "good"
            for candidate in candidates
        )

        # ----------------------------------------------------
        # VISUAL BLANK CHECK
        # ----------------------------------------------------

        visual_blank_result = None

        if not has_good_candidate:
            visual_blank_result = (
                is_visually_blank_page(
                    pymupdf_document,
                    page_index,
                )
            )

            if visual_blank_result[
                "is_blank"
            ]:
                result[
                    "stats"
                ][
                    "blank_pages"
                ] += 1

                result["pages"].append(
                    {
                        "page": page_number,
                        "text": "",
                        "loader": None,
                        "status": "blank",
                        "quality": "empty",
                        "quality_score": 0,

                        "quality_reasons": [
                            "visually_blank_page"
                        ],

                        "quality_metrics": {
                            "ink_ratio": (
                                visual_blank_result[
                                    "ink_ratio"
                                ]
                            ),

                            "mean_brightness": (
                                visual_blank_result[
                                    "mean_brightness"
                                ]
                            ),
                        },

                        "ocr_used": False,
                        "attempts": attempts,
                        "error": None,
                    }
                )

                continue

        # ----------------------------------------------------
        # NOTHING EXTRACTED
        # ----------------------------------------------------

        if best is None:
            errors = [
                attempt["error"]
                for attempt in attempts
                if attempt.get("error")
            ]

            if errors:
                error = "; ".join(
                    errors
                )

            elif (
                visual_blank_result
                and visual_blank_result.get(
                    "error"
                )
            ):
                error = (
                    "Visual blank-page check failed: "
                    f"{visual_blank_result['error']}"
                )

            else:
                error = (
                    "No text extracted from a "
                    "visually non-blank page"
                )

            result[
                "stats"
            ][
                "failed_pages"
            ] += 1

            result["pages"].append(
                {
                    "page": page_number,
                    "text": "",
                    "loader": None,

                    "status": (
                        "failed_extraction"
                    ),

                    "quality": "empty",
                    "quality_score": 0,

                    "quality_reasons": [
                        "failed_extraction"
                    ],

                    "quality_metrics": (
                        {
                            "ink_ratio": (
                                visual_blank_result.get(
                                    "ink_ratio"
                                )
                            ),

                            "mean_brightness": (
                                visual_blank_result.get(
                                    "mean_brightness"
                                )
                            ),
                        }
                        if visual_blank_result
                        else {}
                    ),

                    "ocr_used": False,
                    "attempts": attempts,
                    "error": error,
                }
            )

            continue

        # ----------------------------------------------------
        # BEST RESULT EXISTS
        # ----------------------------------------------------

        diagnostic = best[
            "diagnostic"
        ]

        quality = diagnostic[
            "quality"
        ]

        # ----------------------------------------------------
        # GOOD → ACCEPT
        # ----------------------------------------------------

        if quality == "good":
            status = "accepted"

            result[
                "stats"
            ][
                "accepted_pages"
            ] += 1

            if best["loader"] == "pypdf":
                result[
                    "stats"
                ][
                    "pypdf_pages"
                ] += 1

            elif best[
                "loader"
            ] == "pymupdf":
                result[
                    "stats"
                ][
                    "pymupdf_pages"
                ] += 1

                result[
                    "stats"
                ][
                    "fallback_pages"
                ] += 1

            elif best[
                "loader"
            ] == "tesseract":
                result[
                    "stats"
                ][
                    "ocr_pages"
                ] += 1

                result[
                    "stats"
                ][
                    "fallback_pages"
                ] += 1

            final_text = best[
                "text"
            ]

        # ----------------------------------------------------
        # SUSPICIOUS / REJECTED
        # ----------------------------------------------------

        else:
            status = (
                "rejected_low_quality"
            )

            result[
                "stats"
            ][
                "rejected_pages"
            ] += 1

            # Never expose low-quality text
            # to chunking or Chroma.
            final_text = ""

        result["pages"].append(
            {
                "page": page_number,
                "text": final_text,
                "loader": best["loader"],
                "status": status,
                "quality": quality,

                "quality_score": (
                    diagnostic["score"]
                ),

                "quality_reasons": (
                    diagnostic["reasons"]
                ),

                "quality_metrics": (
                    diagnostic["metrics"]
                ),

                "ocr_used": best[
                    "ocr_used"
                ],

                "attempts": attempts,
                "error": None,
            }
        )

    # ========================================================
    # CLOSE PDF
    # ========================================================

    pymupdf_document.close()

    result[
        "processed_pages"
    ] = len(
        selected_pages
    )

    # ========================================================
    # PDF TYPE
    # ========================================================

    accepted_pages = [
        page
        for page in result["pages"]
        if page["status"] == "accepted"
    ]

    if accepted_pages:
        native_count = sum(
            1
            for page in accepted_pages
            if not page["ocr_used"]
        )

        ocr_count = sum(
            1
            for page in accepted_pages
            if page["ocr_used"]
        )

        if native_count > 0 and ocr_count == 0:
            result["pdf_type"] = "text"

        elif native_count == 0 and ocr_count > 0:
            result["pdf_type"] = "scanned"

        elif native_count > 0 and ocr_count > 0:
            result["pdf_type"] = "mixed"

    # ========================================================
    # FILE STATUS
    # ========================================================

    accepted_count = result[
        "stats"
    ][
        "accepted_pages"
    ]

    rejected_count = result[
        "stats"
    ][
        "rejected_pages"
    ]

    failed_count = result[
        "stats"
    ][
        "failed_pages"
    ]

    if accepted_count == 0:
        result["status"] = "failed"

    elif rejected_count > 0 or failed_count > 0:
        result["status"] = "partial"

    else:
        result["status"] = "success"

    return result