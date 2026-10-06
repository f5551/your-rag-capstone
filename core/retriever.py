"""QISO vector retrieval baseline. Run: python -m core.retriever"""

import argparse
from pathlib import Path
from typing import Any

import chromadb

from .embedder import EMBEDDING_MODEL, embed_query
from .vector_store import DEFAULT_COLLECTION, DEFAULT_PERSIST_DIR


def retrieve(
    query: str,
    top_k: int = 5,
    persist_dir: Path = DEFAULT_PERSIST_DIR,
    collection_name: str = DEFAULT_COLLECTION,
) -> list[dict[str, Any]]:
    """Return stored chunks, metadata, and raw Chroma distances."""

    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string.")

    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
        raise ValueError("top_k must be a positive integer.")

    persist_dir = Path(persist_dir).resolve()
    database_file = persist_dir / "chroma.sqlite3"

    if not database_file.is_file():
        raise FileNotFoundError(
            f"Chroma database was not found: {persist_dir}"
        )

    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_collection(name=collection_name)

    count = collection.count()
    if count == 0:
        raise ValueError(f"Collection '{collection_name}' is empty.")

    sample = collection.peek(limit=1)
    metadata = (sample.get("metadatas") or [{}])[0] or {}

    stored_model = metadata.get("embedding_model")
    if stored_model and stored_model != EMBEDDING_MODEL:
        raise ValueError(f"Embedding model mismatch: {stored_model}")

    query_vector = embed_query(query.strip())

    dimensions = metadata.get("embedding_dimensions")
    if dimensions is not None and int(dimensions) != len(query_vector):
        raise ValueError(
            "Query and stored embedding dimensions do not match."
        )

    response = collection.query(
        query_embeddings=[query_vector],
        n_results=min(top_k, count),
        include=["documents", "metadatas", "distances"],
    )

    return [
        {
            "rank": index + 1,
            "chunk_id": chunk_id,
            "text": response["documents"][0][index] or "",
            "metadata": response["metadatas"][0][index] or {},
            "distance": response["distances"][0][index],
        }
        for index, chunk_id in enumerate(response["ids"][0])
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search existing QISO chunks."
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Arabic or English question",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
    )

    args = parser.parse_args()
    query = args.query if args.query is not None else input("Question: ")

    results = retrieve(query, top_k=args.top_k)

    print("\n" + "=" * 60)
    print("QISO VECTOR RETRIEVAL")
    print("=" * 60)
    print(f"Query:      {query}")
    print(f"Retrieved:  {len(results)}")

    for item in results:
        metadata = item["metadata"]

        print("\n" + "-" * 60)
        print(f"Rank:       {item['rank']}")
        print(f"Source:     {metadata.get('source', 'Unknown')}")
        print(f"PDF page:   {metadata.get('page', 'Unknown')}")
        print(f"Chunk ID:   {item['chunk_id']}")
        print(f"Distance:   {item['distance']:.6f}")
        print(item["text"])


if __name__ == "__main__":
    main()