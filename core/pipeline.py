"""
QISO RAG Ingestion Pipeline.

Stages:
1. Inspect docs folder
2. Ingest
3. Chunk
4. Source Sync Decision
5. Embed / Store
6. Delete removed sources
7. Validate corpus sync
"""

from collections import Counter, defaultdict

from .ingest import DOCS_DIR, ingest_pdfs
from .chunker import chunk_documents
from .vector_store import (
    audit_corpus,
    delete_source_chunks,
    get_collection,
    get_source_states,
    replace_source_chunks,
    store_chunks,
)


class Pipeline:

    def ingest(
        self,
        chunk_size: int = 800,
        overlap: int = 120,
        dry_run: bool = False,
        allow_delete_all: bool = False,
    ):
        """
        Run the QISO ingestion pipeline and synchronize Chroma with docs/.

        Source actions:
            ADD       new PDF
            SKIP      unchanged PDF and pipeline version
            REPLACE   PDF content changed
            REPROCESS same PDF, processing version changed
            DELETE    PDF was removed from docs/

        Safety rules:
            - Deletions are based on PDF filenames physically present in docs/,
              not on successful extraction/chunking. A temporarily failed PDF
              therefore does not lose its existing vectors.
            - DELETE actions run only after all ADD/REPLACE/REPROCESS actions
              finish successfully.
            - An unexpectedly empty docs/ folder cannot wipe the whole corpus
              unless allow_delete_all=True is passed explicitly.
            - dry_run=True reports the plan without modifying Chroma.
        """

        # ====================================================
        # 0. INSPECT SOURCE FOLDER BEFORE PROCESSING
        # ====================================================

        if not DOCS_DIR.is_dir():
            raise FileNotFoundError(
                f"QISO docs directory was not found: {DOCS_DIR}"
            )

        pdf_files = sorted(DOCS_DIR.glob("*.pdf"))
        disk_sources = {path.name for path in pdf_files}

        # Read the current Chroma state before ingestion so deletion decisions
        # are based on the pre-run corpus.
        stored_states = get_source_states()
        stored_sources = set(stored_states)

        missing_sources = sorted(stored_sources - disk_sources)

        if not disk_sources and stored_sources and not allow_delete_all:
            raise RuntimeError(
                "docs/ contains no PDF files while Chroma still contains "
                f"{len(stored_sources)} source(s). Refusing to delete the "
                "entire corpus automatically. If this is intentional, call "
                "Pipeline().ingest(allow_delete_all=True)."
            )

        # ====================================================
        # 1. INGEST
        # ====================================================

        docs = ingest_pdfs()

        # ====================================================
        # 2. CHUNK
        # ====================================================

        chunks = (
            chunk_documents(
                docs,
                chunk_size=chunk_size,
                overlap=overlap,
            )
            if docs
            else []
        )

        # ====================================================
        # CHUNKING SUMMARY
        # ====================================================

        lengths = [len(chunk["text"]) for chunk in chunks]
        short_chunks = [length for length in lengths if length < 100]

        print("\n" + "=" * 60)
        print("RAG PIPELINE SUMMARY")
        print("=" * 60)
        print(f"PDF files on disk:  {len(disk_sources)}")
        print(f"Loaded pages:       {len(docs)}")
        print(f"Generated chunks:   {len(chunks)}")
        print(f"Chunk size:         {chunk_size}")
        print(f"Chunk overlap:      {overlap}")

        if lengths:
            print(f"Shortest chunk:     {min(lengths)}")
            print(f"Longest chunk:      {max(lengths)}")
            print(f"Average chunk:      {sum(lengths) / len(lengths):.1f}")
            print(f"Chunks under 100:   {len(short_chunks)}")
        else:
            print("Shortest chunk:     -")
            print("Longest chunk:      -")
            print("Average chunk:      -")
            print("Chunks under 100:   0")

        # ====================================================
        # 3. GROUP CHUNKS BY SOURCE
        # ====================================================

        chunks_by_source = defaultdict(list)

        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            source = metadata.get("source")

            if not source:
                raise ValueError("Chunk is missing metadata.source")

            if source not in disk_sources:
                raise ValueError(
                    f"Chunk source is not present in docs/: {source}"
                )

            if not metadata.get("source_hash"):
                raise ValueError(
                    f"{source}: chunk is missing source_hash"
                )

            if not metadata.get("pipeline_version"):
                raise ValueError(
                    f"{source}: chunk is missing pipeline_version"
                )

            chunks_by_source[source].append(chunk)

        # A PDF may still be physically present but fail extraction. Never
        # classify it as deleted just because it produced no accepted chunks.
        unprocessed_sources = sorted(
            disk_sources - set(chunks_by_source)
        )

        # ====================================================
        # 4. DECIDE SOURCE ACTIONS
        # ====================================================

        actions = {}

        for source, source_chunks in chunks_by_source.items():
            metadata = source_chunks[0]["metadata"]
            new_hash = metadata["source_hash"]
            new_version = metadata["pipeline_version"]
            old_state = stored_states.get(source)

            if old_state is None:
                action = "ADD"
            else:
                old_hash = old_state.get("source_hash")
                old_version = old_state.get("pipeline_version")

                if old_hash == new_hash and old_version == new_version:
                    action = "SKIP"
                elif old_hash == new_hash and old_version != new_version:
                    action = "REPROCESS"
                else:
                    # Also handles legacy records without source_hash/version.
                    action = "REPLACE"

            actions[source] = {
                "action": action,
                "chunks": source_chunks,
            }

        # Sources stored in Chroma but no longer physically present in docs/.
        for source in missing_sources:
            actions[source] = {
                "action": "DELETE",
                "chunks": [],
            }

        action_counts = Counter(
            item["action"] for item in actions.values()
        )

        # ====================================================
        # SOURCE SYNC SUMMARY
        # ====================================================

        print("\n" + "=" * 60)
        print("SOURCE SYNC PLAN")
        print("=" * 60)
        print(f"Sources on disk:     {len(disk_sources)}")
        print(f"Sources in Chroma:   {len(stored_sources)}")
        print(f"ADD:                 {action_counts['ADD']}")
        print(f"SKIP:                {action_counts['SKIP']}")
        print(f"REPLACE:             {action_counts['REPLACE']}")
        print(f"REPROCESS:           {action_counts['REPROCESS']}")
        print(f"DELETE:              {action_counts['DELETE']}")

        if unprocessed_sources:
            print(
                "PRESENT BUT NO CHUNKS: "
                f"{len(unprocessed_sources)}"
            )
            for source in unprocessed_sources:
                status = (
                    "preserving existing Chroma data"
                    if source in stored_sources
                    else "no vectors created"
                )
                print(f"  - {source}: {status}")

        if missing_sources:
            print("Deleted-from-disk sources:")
            for source in missing_sources:
                old_count = len(
                    stored_states[source].get("chunk_ids", set())
                )
                print(f"  - {source}: {old_count} stored chunk(s)")

        if dry_run:
            print("\nDRY RUN: Chroma was not modified.")
            return docs, chunks

        # ====================================================
        # 5. APPLY NON-DESTRUCTIVE ACTIONS FIRST
        # ====================================================

        processed = Counter()

        for source, item in actions.items():
            action = item["action"]
            source_chunks = item["chunks"]

            if action == "DELETE":
                continue

            if action == "SKIP":
                processed["SKIP"] += 1
                continue

            if action == "ADD":
                print(f"\n[ADD] {source}")
                store_chunks(source_chunks)
                processed["ADD"] += 1
                continue

            if action in {"REPLACE", "REPROCESS"}:
                print(f"\n[{action}] {source}")
                replace_source_chunks(
                    source=source,
                    chunks=source_chunks,
                )
                processed[action] += 1
                continue

            raise RuntimeError(
                f"Unsupported source action: {action}"
            )

        # ====================================================
        # 6. DELETE SOURCES REMOVED FROM docs/
        # ====================================================
        # Run this only after all writes above have succeeded. For example, a
        # rename is treated as ADD(new name) followed by DELETE(old name), so a
        # failed embedding cannot destroy the previous source first.

        deleted_chunks = 0

        for source in missing_sources:
            print(f"\n[DELETE] {source}")
            result = delete_source_chunks(source)
            processed["DELETE"] += 1
            deleted_chunks += result["removed"]

        # ====================================================
        # 7. FINAL VALIDATION
        # ====================================================

        collection = get_collection()
        total_vectors = collection.count()
        final_states = get_source_states()

        stale_after_sync = sorted(
            set(final_states) - disk_sources
        )

        if stale_after_sync:
            raise RuntimeError(
                "Source synchronization failed. Chroma still contains "
                "deleted source(s): " + ", ".join(stale_after_sync)
            )

        corpus_audit = audit_corpus()

        print("\n" + "=" * 60)
        print("QISO INGESTION COMPLETE")
        print("=" * 60)
        print(f"Pages:              {len(docs)}")
        print(f"Chunks:             {len(chunks)}")
        print(f"ADD:                {processed['ADD']}")
        print(f"SKIP:               {processed['SKIP']}")
        print(f"REPLACE:            {processed['REPLACE']}")
        print(f"REPROCESS:          {processed['REPROCESS']}")
        print(f"DELETE:             {processed['DELETE']}")
        print(f"Deleted chunks:     {deleted_chunks}")
        print(f"Vectors in Chroma:  {total_vectors}")
        print(f"Corpus audit:       {corpus_audit['status']}")

        if corpus_audit["status"] != "PASS":
            print(
                f"Corpus audit errors: {len(corpus_audit['errors'])}"
            )
            for error in corpus_audit["errors"][:10]:
                print(f"  - {error}")
            if len(corpus_audit["errors"]) > 10:
                print("  - ...")

        return docs, chunks


if __name__ == "__main__":
    Pipeline().ingest()
