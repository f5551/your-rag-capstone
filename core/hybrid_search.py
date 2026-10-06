"""
QISO hybrid retrieval.

Combines:
- Vector search
- BM25 search
- Reciprocal Rank Fusion (RRF)

Run:
    python -m core.hybrid_search "internal audit purpose"
"""

import argparse
from pathlib import Path
from typing import Any

from .bm25_search import BM25Searcher
from .query_translator import translate_query
from .retriever import retrieve
from .vector_store import (
    DEFAULT_COLLECTION,
    DEFAULT_PERSIST_DIR,
)


def positive_integer(
    value: int,
    name: str,
) -> None:
    """Validate a positive integer argument."""

    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
    ):
        raise ValueError(
            f"{name} must be a positive integer."
        )


def fuse_results(
    vector_results: list[dict[str, Any]],
    bm25_results: list[dict[str, Any]],
    top_k: int = 5,
    rrf_k: int = 60,
) -> list[dict[str, Any]]:
    """
    Merge vector and BM25 rankings using Reciprocal Rank Fusion.

    Results are deduplicated by chunk_id.
    Raw vector distance and BM25 score are retained
    for diagnostics only.
    """

    positive_integer(
        top_k,
        "top_k",
    )

    positive_integer(
        rrf_k,
        "rrf_k",
    )

    merged: dict[
        str,
        dict[str, Any],
    ] = {}

    for method, results in (
        ("vector", vector_results),
        ("bm25", bm25_results),
    ):
        seen: set[str] = set()

        for rank, item in enumerate(
            results,
            start=1,
        ):
            chunk_id = item.get(
                "chunk_id"
            )

            if (
                not isinstance(chunk_id, str)
                or not chunk_id
            ):
                raise ValueError(
                    "Search result is missing "
                    "a valid chunk_id."
                )

            if chunk_id in seen:
                continue

            seen.add(
                chunk_id
            )

            if chunk_id not in merged:
                merged[chunk_id] = {
                    "chunk_id": chunk_id,
                    "text": item.get(
                        "text",
                        "",
                    ),
                    "metadata": dict(
                        item.get("metadata")
                        or {}
                    ),
                    "rrf_score": 0.0,
                    "vector_rank": None,
                    "bm25_rank": None,
                    "distance": None,
                    "bm25_score": None,
                }

            record = merged[
                chunk_id
            ]

            record[
                "rrf_score"
            ] += (
                1.0
                / (rrf_k + rank)
            )

            record[
                f"{method}_rank"
            ] = rank

            if method == "vector":
                record[
                    "distance"
                ] = item.get(
                    "distance"
                )
            else:
                record[
                    "bm25_score"
                ] = item.get(
                    "bm25_score"
                )

    ordered = sorted(
        merged.values(),
        key=lambda item: (
            -item["rrf_score"],
            item["chunk_id"],
        ),
    )

    return [
        {
            "rank": rank,
            **item,
        }
        for rank, item in enumerate(
            ordered[:top_k],
            start=1,
        )
    ]


class HybridSearcher:
    """Hybrid Vector + BM25 search using RRF."""

    def __init__(
        self,
        persist_dir: Path = DEFAULT_PERSIST_DIR,
        collection_name: str = DEFAULT_COLLECTION,
    ) -> None:

        self.persist_dir = Path(
            persist_dir
        ).resolve()

        self.collection_name = (
            collection_name
        )

        self.bm25 = BM25Searcher(
            persist_dir=self.persist_dir,
            collection_name=self.collection_name,
        )

        sync = (
            self.bm25.sync_report()
        )

        if sync["status"] != "PASS":
            raise RuntimeError(
                "Hybrid search cannot start because "
                "BM25 and Chroma are not synchronized."
            )

        self.last_stats: dict[
            str,
            int,
        ] = {}

        self.last_bm25_query = ""
        self.last_mode = ""

    def search(
        self,
        query: str,
        top_k: int = 5,
        candidate_k: int = 20,
        rrf_k: int = 60,
        translate_bm25: bool = True,
    ) -> list[dict[str, Any]]:
        """Run Vector + BM25 search and fuse results using RRF."""

        if (
            not isinstance(query, str)
            or not query.strip()
        ):
            raise ValueError(
                "query must be a non-empty string."
            )

        for name, value in (
            ("top_k", top_k),
            ("candidate_k", candidate_k),
            ("rrf_k", rrf_k),
        ):
            positive_integer(
                value,
                name,
            )

        if candidate_k < top_k:
            raise ValueError(
                "candidate_k must be greater than "
                "or equal to top_k."
            )

        if not isinstance(
            translate_bm25,
            bool,
        ):
            raise ValueError(
                "translate_bm25 must be a boolean."
            )

        query = query.strip()

        self.last_stats = {}
        self.last_bm25_query = ""
        self.last_mode = ""

        bm25_query = (
            translate_query(query)
            if translate_bm25
            else query
        )

        bm25_results = (
            self.bm25.search(
                bm25_query,
                top_k=candidate_k,
            )
        )

        vector_results = retrieve(
            query,
            top_k=candidate_k,
            persist_dir=self.persist_dir,
            collection_name=self.collection_name,
        )

        corpus_ids = (
            self.bm25.chroma_ids
        )

        for item in (
            vector_results
            + bm25_results
        ):
            chunk_id = item.get(
                "chunk_id"
            )

            if chunk_id not in corpus_ids:
                raise RuntimeError(
                    "Retriever returned a chunk outside "
                    "the synchronized corpus: "
                    f"{chunk_id}"
                )

        results = fuse_results(
            vector_results,
            bm25_results,
            top_k=top_k,
            rrf_k=rrf_k,
        )

        unique_ids = {
            item["chunk_id"]
            for item in (
                vector_results
                + bm25_results
            )
        }

        self.last_stats = {
            "vector_candidates": len(
                vector_results
            ),
            "bm25_candidates": len(
                bm25_results
            ),
            "unique_candidates": len(
                unique_ids
            ),
            "returned": len(
                results
            ),
        }

        self.last_bm25_query = (
            bm25_query
        )

        if (
            vector_results
            and bm25_results
        ):
            self.last_mode = (
                "hybrid"
            )

        elif vector_results:
            self.last_mode = (
                "vector_only"
            )

        elif bm25_results:
            self.last_mode = (
                "bm25_only"
            )

        else:
            self.last_mode = (
                "no_results"
            )

        return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Search QISO using "
            "Vector + BM25 + RRF."
        )
    )

    parser.add_argument(
        "query",
        nargs="?",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--candidate-k",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--rrf-k",
        type=int,
        default=60,
    )

    parser.add_argument(
        "--no-translate",
        action="store_true",
    )

    args = parser.parse_args()

    query = (
        args.query
        if args.query is not None
        else input("Question: ")
    )

    searcher = (
        HybridSearcher()
    )

    results = searcher.search(
        query=query,
        top_k=args.top_k,
        candidate_k=args.candidate_k,
        rrf_k=args.rrf_k,
        translate_bm25=(
            not args.no_translate
        ),
    )

    sync = (
        searcher.bm25.sync_report()
    )

    print(
        "\n"
        + "=" * 60
    )

    print(
        "QISO HYBRID SEARCH"
    )

    print(
        "=" * 60
    )

    print(
        f"Corpus sync:        "
        f"{sync['status']}"
    )

    print(
        f"Corpus chunks:      "
        f"{sync['chroma_chunks']}"
    )

    print(
        f"Query:              "
        f"{query}"
    )

    print(
        f"BM25 query:         "
        f"{searcher.last_bm25_query}"
    )

    print(
        f"Search mode:        "
        f"{searcher.last_mode}"
    )

    for name, count in (
        searcher.last_stats.items()
    ):
        print(
            f"{name + ':':<20}"
            f"{count}"
        )

    for item in results:
        metadata = (
            item["metadata"]
        )

        print(
            "\n"
            + "-" * 60
        )

        print(
            f"Rank:         "
            f"{item['rank']}"
        )

        print(
            f"Source:       "
            f"{metadata.get('source', 'Unknown')}"
        )

        print(
            f"PDF page:     "
            f"{metadata.get('page', 'Unknown')}"
        )

        print(
            f"Chunk ID:     "
            f"{item['chunk_id']}"
        )

        print(
            f"RRF score:    "
            f"{item['rrf_score']:.6f}"
        )

        print(
            f"Vector rank:  "
            f"{item['vector_rank']}"
        )

        print(
            f"BM25 rank:    "
            f"{item['bm25_rank']}"
        )


if __name__ == "__main__":
    main()