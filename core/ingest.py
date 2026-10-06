from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from core.preprocess import load_pdf_smart


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"


# ============================================================
# INGESTION VERSION
# ============================================================

# Increase this value whenever preprocessing / ingestion logic
# changes in a way that requires documents to be processed again.
PIPELINE_VERSION = "2.0"

# ============================================================
# SOURCE HASH
# ============================================================

def calculate_source_hash(
    file_path: Path,
    chunk_size: int = 1024 * 1024,
) -> str:
    """
    Calculate SHA-256 hash from the actual PDF file bytes.

    The hash changes when the source file itself changes.
    """

    sha256 = hashlib.sha256()

    with file_path.open("rb") as file:

        while True:

            block = file.read(chunk_size)

            if not block:
                break

            sha256.update(block)

    return sha256.hexdigest()


# ============================================================
# INGEST PDF FILES
# ============================================================

def ingest_pdfs():
    """
    Run ingestion on all PDF files inside docs/.

    Only accepted pages are returned as documents.

    Blank, rejected, and failed pages are recorded in the
    report but are never passed to chunking or Chroma.
    """

    pdf_files = sorted(
        DOCS_DIR.glob("*.pdf")
    )

    documents = []

    failed_files = []
    failed_pages = []
    rejected_pages = []
    blank_pages = []

    total_pages = 0
    extracted_pages = 0

    pypdf_pages = 0
    pymupdf_pages = 0
    ocr_pages = 0

    pdf_type_stats = {
        "text": 0,
        "mixed": 0,
        "scanned": 0,
        "failed": 0,
        "unknown": 0,
    }

    ingestion_time = datetime.now(
        timezone.utc
    ).isoformat()

    print(
        f"PDF files found: {len(pdf_files)}\n"
    )

    # ========================================================
    # PROCESS EACH PDF
    # ========================================================

    for pdf_path in pdf_files:

        print(
            f"Reading: {pdf_path.name}"
        )

        # ----------------------------------------------------
        # Calculate source identity
        # ----------------------------------------------------

        try:

            source_hash = (
                calculate_source_hash(
                    pdf_path
                )
            )

        except Exception as exc:

            failed_files.append(
                {
                    "source": pdf_path.name,
                    "error": (
                        "SHA-256 failed: "
                        f"{exc}"
                    ),
                }
            )

            print(
                "Status: failed"
            )

            print(
                f"Hash error: {exc}"
            )

            print(
                "-" * 60
            )

            continue

        # ----------------------------------------------------
        # Extract PDF
        # ----------------------------------------------------

        result = load_pdf_smart(
            pdf_path,
            expected_language="eng",
            ocr_language="eng",
        )

        pdf_type = result.get(
            "pdf_type",
            "unknown",
        )

        status = result.get(
            "status",
            "failed",
        )

        pages = result.get(
            "pages",
            [],
        )

        file_total_pages = result.get(
            "total_pages",
            0,
        )

        total_pages += (
            file_total_pages
        )

        # ----------------------------------------------------
        # PDF type statistics
        # ----------------------------------------------------

        if (
            pdf_type
            in pdf_type_stats
        ):

            pdf_type_stats[
                pdf_type
            ] += 1

        else:

            pdf_type_stats[
                "unknown"
            ] += 1

        # ----------------------------------------------------
        # Entire PDF failed before page processing
        # ----------------------------------------------------

        if (
            status == "failed"
            and not pages
        ):

            failed_files.append(
                {
                    "source": (
                        pdf_path.name
                    ),

                    "source_hash": (
                        source_hash
                    ),

                    "error": result.get(
                        "error",
                        "Unknown error",
                    ),
                }
            )

            print(
                "Status: failed"
            )

            print(
                "-" * 60
            )

            continue

        # ----------------------------------------------------
        # File report
        # ----------------------------------------------------

        print(
            f"Type: {pdf_type}"
        )

        print(
            f"Pages: {file_total_pages}"
        )

        print(
            f"Status: {status}"
        )

        print(
            f"SHA-256: {source_hash[:16]}..."
        )

        # ====================================================
        # PROCESS PAGES
        # ====================================================

        for page in pages:

            page_number = page.get(
                "page"
            )

            text = page.get(
                "text",
                "",
            )

            loader = page.get(
                "loader"
            )

            page_status = page.get(
                "status"
            )

            quality = page.get(
                "quality"
            )

            quality_score = page.get(
                "quality_score",
                0,
            )

            quality_reasons = page.get(
                "quality_reasons",
                [],
            )

            ocr_used = page.get(
                "ocr_used",
                False,
            )

            error = page.get(
                "error"
            )

            # ------------------------------------------------
            # BLANK PAGE
            # ------------------------------------------------

            if page_status == "blank":

                blank_pages.append(
                    {
                        "source": (
                            pdf_path.name
                        ),

                        "page": (
                            page_number
                        ),

                        "reason": (
                            quality_reasons
                        ),
                    }
                )

                continue

            # ------------------------------------------------
            # REJECTED PAGE
            # ------------------------------------------------

            if (
                page_status
                == "rejected_low_quality"
            ):

                rejected_pages.append(
                    {
                        "source": (
                            pdf_path.name
                        ),

                        "page": (
                            page_number
                        ),

                        "loader": (
                            loader
                        ),

                        "quality": (
                            quality
                        ),

                        "quality_score": (
                            quality_score
                        ),

                        "reasons": (
                            quality_reasons
                        ),
                    }
                )

                continue

            # ------------------------------------------------
            # EXTRACTION FAILURE
            # ------------------------------------------------

            if (
                page_status
                == "failed_extraction"
            ):

                failed_pages.append(
                    {
                        "source": (
                            pdf_path.name
                        ),

                        "page": (
                            page_number
                        ),

                        "loader": (
                            loader
                        ),

                        "error": (
                            error
                            or
                            "Extraction failed"
                        ),
                    }
                )

                continue

            # ------------------------------------------------
            # SAFETY CHECK
            #
            # Only accepted pages with usable text
            # may enter the corpus.
            # ------------------------------------------------

            if (
                page_status
                != "accepted"
                or not text.strip()
            ):

                failed_pages.append(
                    {
                        "source": (
                            pdf_path.name
                        ),

                        "page": (
                            page_number
                        ),

                        "loader": (
                            loader
                        ),

                        "error": (
                            "Unexpected page state: "
                            f"status={page_status}, "
                            f"quality={quality}"
                        ),
                    }
                )

                continue

            # ------------------------------------------------
            # ACCEPTED PAGE LOADER STATS
            # ------------------------------------------------

            if loader == "pypdf":

                pypdf_pages += 1

            elif loader == "pymupdf":

                pymupdf_pages += 1

            elif loader == "tesseract":

                ocr_pages += 1

            # ------------------------------------------------
            # ACCEPTED DOCUMENT
            # ------------------------------------------------

            extracted_pages += 1

            documents.append(
                {
                    "text": text,

                    "metadata": {
                        # -----------------------------
                        # Source identity
                        # -----------------------------

                        "source": (
                            pdf_path.name
                        ),

                        "source_hash": (
                            source_hash
                        ),

                        "pipeline_version": (
                            PIPELINE_VERSION
                        ),

                        "ingested_at": (
                            ingestion_time
                        ),

                        # -----------------------------
                        # Page identity
                        # -----------------------------

                        "page": (
                            page_number
                        ),

                        # -----------------------------
                        # Extraction metadata
                        # -----------------------------

                        "pdf_type": (
                            pdf_type
                        ),

                        "loader": (
                            loader
                        ),

                        "quality": (
                            quality
                        ),

                        "quality_score": (
                            quality_score
                        ),

                        "ocr_used": (
                            ocr_used
                        ),

                        "extraction_status": (
                            page_status
                        ),
                    },
                }
            )

        print(
            "-" * 60
        )

    # ========================================================
    # FINAL REPORT
    # ========================================================

    print(
        "\n"
        + "=" * 60
    )

    print(
        "Ingestion Summary"
    )

    print(
        "=" * 60
    )

    print(
        f"Pipeline version:   "
        f"{PIPELINE_VERSION}"
    )

    print(
        f"PDF files:          "
        f"{len(pdf_files)}"
    )

    print(
        f"Total pages:        "
        f"{total_pages}"
    )

    print(
        f"Accepted pages:     "
        f"{extracted_pages}"
    )

    print(
        f"Blank pages:        "
        f"{len(blank_pages)}"
    )

    print(
        f"Rejected pages:     "
        f"{len(rejected_pages)}"
    )

    print(
        f"Failed pages:       "
        f"{len(failed_pages)}"
    )

    print(
        f"Failed files:       "
        f"{len(failed_files)}"
    )

    # ========================================================
    # PDF TYPE REPORT
    # ========================================================

    print(
        "\nPDF Type Summary"
    )

    print(
        f"Text PDFs:          "
        f"{pdf_type_stats['text']}"
    )

    print(
        f"Mixed PDFs:         "
        f"{pdf_type_stats['mixed']}"
    )

    print(
        f"Scanned PDFs:       "
        f"{pdf_type_stats['scanned']}"
    )

    print(
        f"Failed PDFs:        "
        f"{pdf_type_stats['failed']}"
    )

    print(
        f"Unknown PDFs:       "
        f"{pdf_type_stats['unknown']}"
    )

    # ========================================================
    # PAGE PROCESSING REPORT
    # ========================================================

    print(
        "\nPage Processing Summary"
    )

    print(
        f"pypdf pages:        "
        f"{pypdf_pages}"
    )

    print(
        f"PyMuPDF pages:      "
        f"{pymupdf_pages}"
    )

    print(
        f"OCR pages:          "
        f"{ocr_pages}"
    )

    print(
        f"Blank pages:        "
        f"{len(blank_pages)}"
    )

    print(
        f"Rejected pages:     "
        f"{len(rejected_pages)}"
    )

    print(
        f"Failed pages:       "
        f"{len(failed_pages)}"
    )

    # ========================================================
    # REJECTED PAGES
    # ========================================================

    if rejected_pages:

        print(
            "\nRejected pages:"
        )

        for item in (
            rejected_pages
        ):

            print(
                f"- {item['source']} | "
                f"Page {item['page']} | "
                f"Loader: {item['loader']} | "
                f"Score: {item['quality_score']} | "
                f"Reasons: {item['reasons']}"
            )

    # ========================================================
    # FAILED PAGES
    # ========================================================

    if failed_pages:

        print(
            "\nFailed pages:"
        )

        for item in (
            failed_pages
        ):

            print(
                f"- {item['source']} | "
                f"Page {item['page']} | "
                f"Loader: {item['loader']} | "
                f"Error: {item['error']}"
            )

    # ========================================================
    # FAILED FILES
    # ========================================================

    if failed_files:

        print(
            "\nFailed files:"
        )

        for item in (
            failed_files
        ):

            print(
                f"- {item['source']} | "
                f"Error: {item['error']}"
            )

    # ========================================================
    # RETURN ACCEPTED DOCUMENTS ONLY
    # ========================================================

    return documents