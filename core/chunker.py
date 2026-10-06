"""
Chunking layer for QISO RAG system.

Strategy:
    Recursive Character Chunking

Default settings:
    chunk_size = 800 characters
    chunk_overlap = 120 characters

Additional processing:
    - Conservative PDF noise cleanup
    - Merge short meaningful chunks when possible
"""

import re
from copy import deepcopy
from hashlib import sha256
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter


# --------------------------------------------------
# Configuration
# --------------------------------------------------

DEFAULT_CHUNK_SIZE = 800
DEFAULT_OVERLAP = 120
MIN_CHUNK_CHARS = 100


# Optimized for English technical documents
SEPARATORS = [
    "\n\n",   # paragraphs
    "\n",     # lines
    ". ",     # sentences
    "? ",
    "! ",
    "; ",
    ": ",
    ", ",
    " ",      # words
    "",       # characters - final fallback
]


# --------------------------------------------------
# PDF noise patterns
# --------------------------------------------------

COPYRIGHT_RE = re.compile(
    r"^©\s*ISO\b.*all rights reserved.*$",
    re.IGNORECASE,
)

ISO_DATE_STAMP_RE = re.compile(
    r"^ISO\s+\d{3,6}:\d{4}\s*\d{4}-\d{2}$",
    re.IGNORECASE,
)

ISO_LANGUAGE_HEADER_RE = re.compile(
    r"^ISO\s+\d{3,6}:\d{4}\s*\([a-z]{1,3}\)$",
    re.IGNORECASE,
)

PAGE_NUMBER_RE = re.compile(
    r"^\d{1,4}$"
)

ROMAN_PAGE_RE = re.compile(
    r"^[ivxlcdm]{1,8}$",
    re.IGNORECASE,
)


# --------------------------------------------------
# Create splitter
# --------------------------------------------------

def make_splitter(
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> RecursiveCharacterTextSplitter:

    if not isinstance(chunk_size, int) or chunk_size <= 0:
        raise ValueError(
            "chunk_size must be a positive integer."
        )

    if not isinstance(overlap, int):
        raise ValueError(
            "overlap must be an integer."
        )

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap must satisfy: 0 <= overlap < chunk_size."
        )

    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=SEPARATORS,
        length_function=len,
        is_separator_regex=False,
    )


# --------------------------------------------------
# Detect PDF noise
# --------------------------------------------------

def is_pdf_noise_line(
    line: str,
    is_page_edge: bool = False,
) -> bool:
    """
    Detect obvious PDF header/footer noise.

    The rules are deliberately conservative so that
    useful ISO content is not removed accidentally.
    """

    clean = " ".join(line.split()).strip()

    if not clean:
        return False

    # Example:
    # © ISO 2026 - All rights reserved
    if COPYRIGHT_RE.fullmatch(clean):
        return True

    # Example:
    # ISO 19011:20262026-05
    if ISO_DATE_STAMP_RE.fullmatch(clean):
        return True

    # The following are removed only near the
    # beginning/end of a page.

    if is_page_edge:

        # Example:
        # ISO 19011:2026(en)
        if ISO_LANGUAGE_HEADER_RE.fullmatch(clean):
            return True

        # Example:
        # 12
        if PAGE_NUMBER_RE.fullmatch(clean):
            return True

        # Example:
        # iv
        # vii
        if ROMAN_PAGE_RE.fullmatch(clean):
            return True

    return False


# --------------------------------------------------
# Clean page text
# --------------------------------------------------

def clean_pdf_noise(
    text: str,
) -> tuple[str, int]:
    """
    Remove only obvious PDF header/footer noise.

    Returns:
        cleaned_text
        removed_line_count
    """

    if not isinstance(text, str):
        raise TypeError(
            "text must be a string."
        )

    lines = text.splitlines()

    non_empty_positions = [
        index
        for index, line in enumerate(lines)
        if line.strip()
    ]

    if not non_empty_positions:
        return "", 0

    # First 4 and last 4 non-empty lines are considered
    # page-edge locations.
    edge_positions = set(
        non_empty_positions[:4]
        + non_empty_positions[-4:]
    )

    cleaned_lines = []
    removed_count = 0

    for index, line in enumerate(lines):

        clean = line.strip()

        if not clean:
            cleaned_lines.append("")
            continue

        if is_pdf_noise_line(
            clean,
            is_page_edge=index in edge_positions,
        ):
            removed_count += 1
            continue

        cleaned_lines.append(line)

    cleaned_text = "\n".join(
        cleaned_lines
    )

    # Avoid excessive empty lines after cleanup
    cleaned_text = re.sub(
        r"\n{3,}",
        "\n\n",
        cleaned_text,
    )

    return cleaned_text.strip(), removed_count


# --------------------------------------------------
# Merge short useful chunks
# --------------------------------------------------

def merge_short_chunks(
    chunks: list[str],
    chunk_size: int,
    min_chars: int = MIN_CHUNK_CHARS,
) -> list[str]:
    """
    Merge a short meaningful chunk with the next chunk
    when the combined text remains within chunk_size.

    If merging with the next chunk is not possible,
    try merging with the previous chunk.

    No chunk is deleted merely because it is short.
    """

    parts = [
        chunk.strip()
        for chunk in chunks
        if isinstance(chunk, str)
        and chunk.strip()
    ]

    merged = []
    index = 0

    while index < len(parts):

        current = parts[index]

        # Normal-size chunk
        if len(current) >= min_chars:
            merged.append(current)
            index += 1
            continue

        # ------------------------------------------
        # Try merging with NEXT chunk
        # ------------------------------------------

        if index + 1 < len(parts):

            next_chunk = parts[index + 1]

            candidate = (
                current.rstrip()
                + "\n\n"
                + next_chunk.lstrip()
            )

            if len(candidate) <= chunk_size:

                parts[index + 1] = candidate

                index += 1
                continue

        # ------------------------------------------
        # Try merging with PREVIOUS chunk
        # ------------------------------------------

        if merged:

            previous = merged[-1]

            candidate = (
                previous.rstrip()
                + "\n\n"
                + current.lstrip()
            )

            if len(candidate) <= chunk_size:

                merged[-1] = candidate

                index += 1
                continue

        # Could not merge safely
        merged.append(current)

        index += 1

    return merged


# --------------------------------------------------
# Generate stable chunk ID
# --------------------------------------------------

def make_chunk_id(
    source: str,
    page: Any,
    chunk_index: int,
    text: str,
) -> str:

    raw_id = (
        f"{source}|"
        f"{page}|"
        f"{chunk_index}|"
        f"{text}"
    )

    return sha256(
        raw_id.encode("utf-8")
    ).hexdigest()


# --------------------------------------------------
# Chunk documents
# --------------------------------------------------

def chunk_documents(
    documents: list[dict[str, Any]],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[dict[str, Any]]:

    if not isinstance(documents, list):
        raise TypeError(
            "documents must be a list."
        )

    splitter = make_splitter(
        chunk_size=chunk_size,
        overlap=overlap,
    )

    chunks = []

    for record_number, document in enumerate(
        documents,
        start=1,
    ):

        # ------------------------------------------
        # Validate record
        # ------------------------------------------

        if not isinstance(document, dict):
            raise TypeError(
                f"Record {record_number} "
                f"must be a dictionary."
            )

        text = document.get(
            "text",
            "",
        )

        metadata = document.get(
            "metadata",
            {},
        )

        if not isinstance(text, str):
            raise TypeError(
                f"Record {record_number}: "
                f"text must be a string."
            )

        if not isinstance(metadata, dict):
            raise TypeError(
                f"Record {record_number}: "
                f"metadata must be a dictionary."
            )

        if not text.strip():
            continue

        source = metadata.get(
            "source"
        )

        page = metadata.get(
            "page"
        )

        if source is None:
            raise ValueError(
                f"Record {record_number}: "
                f"missing metadata.source"
            )

        if page is None:
            raise ValueError(
                f"Record {record_number}: "
                f"missing metadata.page"
            )

        # ------------------------------------------
        # Clean PDF noise
        # ------------------------------------------

        cleaned_text, removed_noise_lines = (
            clean_pdf_noise(text)
        )

        if not cleaned_text:
            continue

        # ------------------------------------------
        # Recursive split
        # ------------------------------------------

        page_chunks = splitter.split_text(
            cleaned_text
        )

        # ------------------------------------------
        # Merge short useful chunks
        # ------------------------------------------

        page_chunks = merge_short_chunks(
            page_chunks,
            chunk_size=chunk_size,
        )

        # ------------------------------------------
        # Create final chunk records
        # ------------------------------------------

        for chunk_index, chunk_text in enumerate(
            page_chunks,
            start=1,
        ):

            if not chunk_text.strip():
                continue

            chunk_metadata = deepcopy(
                metadata
            )

            chunk_id = make_chunk_id(
                source=source,
                page=page,
                chunk_index=chunk_index,
                text=chunk_text,
            )

            chunk_metadata.update(
                {
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_index,
                    "char_count": len(chunk_text),
                    "chunk_size": chunk_size,
                    "chunk_overlap": overlap,
                    "noise_lines_removed": removed_noise_lines,
                }
            )

            chunks.append(
                {
                    "text": chunk_text,
                    "metadata": chunk_metadata,
                }
            )

    return chunks


# --------------------------------------------------
# Self-test
# --------------------------------------------------

if __name__ == "__main__":

    sample_documents = [
        {
            "text": """
ISO 19011:20262026-05
ISO 19011:2026(en)

INTRODUCTION

Quality management systems help organizations improve
their processes and consistently meet customer requirements.

ISO 9001 defines requirements for a quality management
system and promotes risk-based thinking and continual improvement.

Internal auditing helps determine whether the management
system conforms to planned arrangements and is effectively implemented.

Corrective actions should address the causes of detected
nonconformities to prevent recurrence.

© ISO 2026 - All rights reserved
iv
""",
            "metadata": {
                "source": "sample_quality_document.pdf",
                "page": 1,
                "loader": "test",
            },
        }
    ]

    result = chunk_documents(
        sample_documents
    )

    print("=" * 60)
    print("CHUNKER SELF TEST")
    print("=" * 60)

    print(
        f"Input pages: "
        f"{len(sample_documents)}"
    )

    print(
        f"Generated chunks: "
        f"{len(result)}"
    )

    if result:

        lengths = [
            len(chunk["text"])
            for chunk in result
        ]

        print(
            f"Shortest chunk: "
            f"{min(lengths)} characters"
        )

        print(
            f"Longest chunk: "
            f"{max(lengths)} characters"
        )

        print(
            f"Noise lines removed: "
            f"{result[0]['metadata']['noise_lines_removed']}"
        )

        print("\nFirst chunk metadata:")
        print(
            result[0]["metadata"]
        )

        print("\nFirst chunk preview:")
        print("-" * 60)

        print(
            result[0]["text"][:700]
        )

        print("-" * 60)

    assert result, (
        "No chunks were generated."
    )

    assert all(
        0 < len(chunk["text"])
        <= DEFAULT_CHUNK_SIZE
        for chunk in result
    )

    assert all(
        "all rights reserved"
        not in chunk["text"].lower()
        for chunk in result
    )

    assert all(
        "ISO 19011:20262026-05"
        not in chunk["text"]
        for chunk in result
    )

    print(
        "\nChunker self-test: PASSED"
    )