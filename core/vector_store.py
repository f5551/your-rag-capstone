"""
Vector storage layer for QISO RAG system.

Database:
    ChromaDB

Embedding:
    Cohere embed-multilingual-v3.0
"""

from pathlib import Path
from typing import Any

import chromadb

from .embedder import embed_chunks


BASE_DIR = Path(__file__).resolve().parent.parent

DEFAULT_PERSIST_DIR = BASE_DIR / "chroma_db"
DEFAULT_COLLECTION = "qiso_docs"

DEFAULT_EMBED_BATCH_SIZE = 90
DEFAULT_STORE_BATCH_SIZE = 500


def clean_metadata(
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Keep metadata values compatible with Chroma."""

    return {
        key: (
            value
            if isinstance(value, (str, int, float, bool))
            else str(value)
        )
        for key, value in metadata.items()
        if value is not None
    }


def get_collection(
    persist_dir: Path = DEFAULT_PERSIST_DIR,
    collection_name: str = DEFAULT_COLLECTION,
):
    """Open or create the persistent Chroma collection."""

    persist_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    client = chromadb.PersistentClient(
        path=str(persist_dir)
    )

    return client.get_or_create_collection(
        name=collection_name
    )


def get_source_states(
    persist_dir: Path = DEFAULT_PERSIST_DIR,
    collection_name: str = DEFAULT_COLLECTION,
) -> dict[str, dict[str, Any]]:
    """Return the current state of every source stored in Chroma."""

    collection = get_collection(
        persist_dir=persist_dir,
        collection_name=collection_name,
    )

    data = collection.get(
        include=["metadatas"]
    )

    ids = data.get("ids", [])
    metadatas = data.get("metadatas") or []

    states: dict[str, dict[str, Any]] = {}

    for chunk_id, metadata in zip(
        ids,
        metadatas,
    ):
        metadata = metadata or {}

        source = metadata.get("source")

        if not source:
            continue

        if source not in states:
            states[source] = {
                "source_hash": metadata.get(
                    "source_hash"
                ),
                "pipeline_version": metadata.get(
                    "pipeline_version"
                ),
                "chunk_ids": set(),
            }

        states[source]["chunk_ids"].add(
            chunk_id
        )

    return states


def _validate_chunks(
    chunks: list[dict[str, Any]],
) -> None:
    """Validate chunk structure before embedding and storage."""

    if not isinstance(chunks, list):
        raise TypeError(
            "chunks must be a list."
        )

    for chunk in chunks:
        text = chunk.get("text")

        if not isinstance(text, str) or not text.strip():
            raise ValueError(
                "Chunk is missing text."
            )

        metadata = chunk.get(
            "metadata"
        )

        if not isinstance(metadata, dict):
            raise ValueError(
                "Chunk metadata must be a dictionary."
            )

        if not metadata.get("chunk_id"):
            raise ValueError(
                "Chunk is missing metadata.chunk_id"
            )

        if not metadata.get("source"):
            raise ValueError(
                "Chunk is missing metadata.source"
            )


def _upsert_embedded_chunks(
    collection,
    embedded_chunks: list[dict[str, Any]],
) -> None:
    """Store already embedded chunks in batches."""

    for start in range(
        0,
        len(embedded_chunks),
        DEFAULT_STORE_BATCH_SIZE,
    ):
        batch = embedded_chunks[
            start:start + DEFAULT_STORE_BATCH_SIZE
        ]

        collection.upsert(
            ids=[
                item["metadata"]["chunk_id"]
                for item in batch
            ],
            documents=[
                item["text"]
                for item in batch
            ],
            embeddings=[
                item["embedding"]
                for item in batch
            ],
            metadatas=[
                clean_metadata(
                    item["metadata"]
                )
                for item in batch
            ],
        )

        completed = min(
            start + len(batch),
            len(embedded_chunks),
        )

        print(
            f"Stored:            "
            f"{completed}/{len(embedded_chunks)}"
        )


def store_chunks(
    chunks: list[dict[str, Any]],
    persist_dir: Path = DEFAULT_PERSIST_DIR,
    collection_name: str = DEFAULT_COLLECTION,
    embed_batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
) -> int:
    """Embed and store chunks that do not already exist."""

    _validate_chunks(chunks)

    collection = get_collection(
        persist_dir=persist_dir,
        collection_name=collection_name,
    )

    if not chunks:
        print("No chunks to store.")
        return collection.count()

    requested_ids = [
        chunk["metadata"]["chunk_id"]
        for chunk in chunks
    ]

    existing = collection.get(
        ids=requested_ids
    )

    existing_ids = set(
        existing.get("ids", [])
    )

    new_chunks = [
        chunk
        for chunk in chunks
        if chunk["metadata"]["chunk_id"]
        not in existing_ids
    ]

    print("\n" + "=" * 60)
    print("CHROMA VECTOR STORE")
    print("=" * 60)

    print(
        f"Collection:        {collection_name}"
    )
    print(
        f"Persist directory: {persist_dir}"
    )
    print(
        f"Chunks received:   {len(chunks)}"
    )
    print(
        f"Already present:   {len(existing_ids)}"
    )
    print(
        f"New chunks:        {len(new_chunks)}"
    )

    if not new_chunks:
        total = collection.count()

        print(
            "\nNo new chunks need embedding."
        )
        print(
            f"Collection total:  {total}"
        )

        return total

    embedded_chunks = embed_chunks(
        new_chunks,
        batch_size=embed_batch_size,
    )

    if len(embedded_chunks) != len(new_chunks):
        raise RuntimeError(
            "Embedding count does not match chunk count."
        )

    _upsert_embedded_chunks(
        collection,
        embedded_chunks,
    )

    total = collection.count()

    print("\n" + "=" * 60)
    print("VECTOR STORE SUMMARY")
    print("=" * 60)

    print(
        f"New chunks stored: {len(embedded_chunks)}"
    )
    print(
        f"Collection total:  {total}"
    )
    print(
        f"Database path:     {persist_dir}"
    )

    return total


def replace_source_chunks(
    source: str,
    chunks: list[dict[str, Any]],
    persist_dir: Path = DEFAULT_PERSIST_DIR,
    collection_name: str = DEFAULT_COLLECTION,
    embed_batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
) -> int:
    """
    Safely replace all chunks belonging to one source.

    New chunks are embedded and stored before stale old
    chunks are removed.
    """

    if not source:
        raise ValueError(
            "source is required."
        )

    _validate_chunks(chunks)

    if not chunks:
        raise ValueError(
            "Refusing to replace a source with zero chunks."
        )

    invalid_sources = {
        chunk["metadata"]["source"]
        for chunk in chunks
        if chunk["metadata"]["source"] != source
    }

    if invalid_sources:
        raise ValueError(
            "replace_source_chunks received chunks "
            "from another source."
        )

    collection = get_collection(
        persist_dir=persist_dir,
        collection_name=collection_name,
    )

    existing = collection.get(
        where={
            "source": source
        },
        include=["metadatas"],
    )

    old_ids = set(
        existing.get("ids", [])
    )

    new_ids = {
        chunk["metadata"]["chunk_id"]
        for chunk in chunks
    }

    if len(new_ids) != len(chunks):
        raise ValueError(
            "Duplicate chunk IDs found in replacement source."
        )

    print("\n" + "=" * 60)
    print("SOURCE REPLACE")
    print("=" * 60)

    print(
        f"Source:            {source}"
    )
    print(
        f"Old chunks:        {len(old_ids)}"
    )
    print(
        f"New chunks:        {len(new_ids)}"
    )

    embedded_chunks = embed_chunks(
        chunks,
        batch_size=embed_batch_size,
    )

    if len(embedded_chunks) != len(chunks):
        raise RuntimeError(
            "Embedding count does not match chunk count. "
            "Existing source was not deleted."
        )

    _upsert_embedded_chunks(
        collection,
        embedded_chunks,
    )

    stale_ids = list(
        old_ids - new_ids
    )

    if stale_ids:
        collection.delete(
            ids=stale_ids
        )

    total = collection.count()

    print(
        f"Stale removed:     {len(stale_ids)}"
    )
    print(
        f"Collection total:  {total}"
    )

    return total



def delete_source_chunks(
    source: str,
    persist_dir: Path = DEFAULT_PERSIST_DIR,
    collection_name: str = DEFAULT_COLLECTION,
) -> dict[str, int]:
    """Delete every stored chunk for one source and verify removal.

    This operation does not embed anything and is intended for source files
    that were physically removed from docs/. The caller is responsible for
    deciding that the source really is absent from the source-of-truth folder.
    """

    if not isinstance(source, str) or not source.strip():
        raise ValueError("source must be a non-empty filename.")

    source = source.strip()

    collection = get_collection(
        persist_dir=persist_dir,
        collection_name=collection_name,
    )

    existing = collection.get(
        where={"source": source},
        include=[],
    )

    ids = list(existing.get("ids", []))

    print("\n" + "=" * 60)
    print("SOURCE DELETE")
    print("=" * 60)
    print(f"Source:            {source}")
    print(f"Chunks found:      {len(ids)}")

    if ids:
        collection.delete(ids=ids)

    remaining = collection.get(
        where={"source": source},
        include=[],
    )

    remaining_ids = list(
        remaining.get("ids", [])
    )

    if remaining_ids:
        raise RuntimeError(
            f"Failed to delete all chunks for source: {source}"
        )

    total = collection.count()

    print(f"Chunks removed:    {len(ids)}")
    print(f"Collection total:  {total}")

    return {
        "removed": len(ids),
        "total": total,
    }


def audit_corpus(
    persist_dir: Path = DEFAULT_PERSIST_DIR,
    collection_name: str = DEFAULT_COLLECTION,
) -> dict[str, Any]:
    """Inspect structural integrity of the stored Chroma corpus."""

    collection = get_collection(
        persist_dir=persist_dir,
        collection_name=collection_name,
    )

    data = collection.get(
        include=[
            "documents",
            "metadatas",
        ]
    )

    ids = data.get("ids", [])
    documents = data.get("documents") or []
    metadatas = data.get("metadatas") or []

    errors: list[str] = []

    source_hashes: dict[
        str,
        set[str],
    ] = {}

    source_versions: dict[
        str,
        set[str],
    ] = {}

    lengths: list[int] = []

    empty_chunks = 0
    short_chunks = 0
    ocr_chunks = 0

    if len(ids) != len(documents):
        errors.append(
            "Document count does not match ID count."
        )

    if len(ids) != len(metadatas):
        errors.append(
            "Metadata count does not match ID count."
        )

    duplicate_ids = (
        len(ids)
        - len(set(ids))
    )

    if duplicate_ids:
        errors.append(
            f"Duplicate IDs found: {duplicate_ids}"
        )

    for chunk_id, text, metadata in zip(
        ids,
        documents,
        metadatas,
    ):
        metadata = metadata or {}

        if not isinstance(text, str) or not text.strip():
            empty_chunks += 1

            errors.append(
                f"{chunk_id}: empty document"
            )

            continue

        chunk_length = len(text)
        lengths.append(chunk_length)

        if chunk_length < 100:
            short_chunks += 1

        if metadata.get("ocr_used") is True:
            ocr_chunks += 1

        for field in (
            "source",
            "page",
            "chunk_id",
            "source_hash",
            "pipeline_version",
        ):
            if metadata.get(field) in (
                None,
                "",
            ):
                errors.append(
                    f"{chunk_id}: missing {field}"
                )

        if metadata.get("chunk_id") != chunk_id:
            errors.append(
                f"{chunk_id}: chunk_id mismatch"
            )

        page = metadata.get("page")

        if (
            isinstance(page, bool)
            or not isinstance(page, int)
            or page <= 0
        ):
            errors.append(
                f"{chunk_id}: invalid page {page}"
            )

        source = metadata.get("source")
        source_hash = metadata.get(
            "source_hash"
        )
        pipeline_version = metadata.get(
            "pipeline_version"
        )

        if source:
            source_hashes.setdefault(
                source,
                set(),
            )
            source_versions.setdefault(
                source,
                set(),
            )

            if source_hash:
                source_hashes[
                    source
                ].add(
                    source_hash
                )

            if pipeline_version:
                source_versions[
                    source
                ].add(
                    pipeline_version
                )

    for source, hashes in source_hashes.items():
        if len(hashes) != 1:
            errors.append(
                f"{source}: multiple source_hash values"
            )

    for source, versions in source_versions.items():
        if len(versions) != 1:
            errors.append(
                f"{source}: multiple pipeline versions"
            )

    average_chunk = (
        round(
            sum(lengths) / len(lengths),
            1,
        )
        if lengths
        else 0
    )

    return {
        "status": (
            "PASS"
            if not errors
            else "FAIL"
        ),
        "chunks": len(ids),
        "sources": len(source_hashes),
        "duplicate_ids": duplicate_ids,
        "empty_chunks": empty_chunks,
        "short_chunks": short_chunks,
        "ocr_chunks": ocr_chunks,
        "shortest_chunk": (
            min(lengths)
            if lengths
            else 0
        ),
        "longest_chunk": (
            max(lengths)
            if lengths
            else 0
        ),
        "average_chunk": average_chunk,
        "errors": errors,
    }