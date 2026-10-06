"""
QISO BM25 keyword search.

BM25 is built directly from the chunks stored in Chroma,
so lexical and vector retrieval use the same corpus.
"""

import argparse
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi
import snowballstemmer

from .vector_store import (
    DEFAULT_COLLECTION,
    DEFAULT_PERSIST_DIR,
    get_collection,
)


TOKEN_PATTERN = re.compile(
    r"\d+(?:[.:]\d+)*|[^\W\d_]+",
    re.UNICODE,
)

ARABIC_MARKS = re.compile(
    r"[\u0640\u064b-\u065f\u0670]"
)

ENGLISH_STEMMER = snowballstemmer.stemmer(
    "english"
)

STOPWORDS = frozenset(
    """
    a an the is are was were be been being am
    do does did of in on at to for from with by as
    and or this that these those what which who whom
    whose how why when where it its they them their
    we our you your i me my
    """.split()
)


@lru_cache(maxsize=10000)
def stem_english(
    token: str,
) -> str:
    """Stem one English token."""

    return ENGLISH_STEMMER.stemWord(
        token
    )


def tokenize(
    text: str,
) -> list[str]:
    """
    Normalize documents and queries identically.

    Preserves clause and standard references such as:
    9.2
    9001:2015
    """

    if not isinstance(text, str):
        raise TypeError(
            "text must be a string."
        )

    text = unicodedata.normalize(
        "NFKC",
        text,
    ).casefold()

    text = ARABIC_MARKS.sub(
        "",
        text,
    )

    text = "".join(
        (
            str(
                unicodedata.decimal(char)
            )
            if char.isdecimal()
            else char
        )
        for char in text
    )

    tokens = TOKEN_PATTERN.findall(
        text
    )

    return [
        (
            stem_english(token)
            if token.isascii()
            and token.isalpha()
            else token
        )
        for token in tokens
        if token not in STOPWORDS
    ]


class BM25Searcher:
    """BM25 search over the current Chroma corpus."""

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

        database_file = (
            self.persist_dir
            / "chroma.sqlite3"
        )

        if not database_file.is_file():
            raise FileNotFoundError(
                "Chroma database was not found: "
                f"{self.persist_dir}"
            )

        self.collection = get_collection(
            persist_dir=self.persist_dir,
            collection_name=self.collection_name,
        )

        self.records: list[
            dict[str, Any]
        ] = []

        self.index = None

        self.stored_count = 0
        self.indexed_count = 0

        self.chroma_ids: set[str] = set()
        self.bm25_ids: set[str] = set()
        self.missing_ids: set[str] = set()
        self.extra_ids: set[str] = set()

        self.refresh()

    def refresh(
        self,
    ) -> None:
        """Rebuild BM25 directly from Chroma."""

        data = self.collection.get(
            include=[
                "documents",
                "metadatas",
            ]
        )

        ids = data.get(
            "ids",
            [],
        )

        documents = data.get(
            "documents"
        )

        metadatas = data.get(
            "metadatas"
        )

        if not ids:
            raise ValueError(
                "The Chroma collection is empty."
            )

        if (
            documents is None
            or len(documents) != len(ids)
        ):
            raise ValueError(
                "Stored documents are missing "
                "or incomplete."
            )

        if metadatas is None:
            metadatas = [
                {}
                for _ in ids
            ]

        if len(metadatas) != len(ids):
            raise ValueError(
                "Stored metadata count does not "
                "match chunk IDs."
            )

        records: list[
            dict[str, Any]
        ] = []

        corpus: list[
            list[str]
        ] = []

        for chunk_id, text, metadata in zip(
            ids,
            documents,
            metadatas,
        ):
            if (
                not isinstance(text, str)
                or not text.strip()
            ):
                raise ValueError(
                    "Invalid document for chunk: "
                    f"{chunk_id}"
                )

            tokens = tokenize(
                text
            )

            if not tokens:
                raise ValueError(
                    "Chunk cannot be indexed by BM25: "
                    f"{chunk_id}"
                )

            records.append(
                {
                    "chunk_id": chunk_id,
                    "text": text,
                    "metadata": metadata or {},
                }
            )

            corpus.append(
                tokens
            )

        self.records = records

        self.index = BM25Okapi(
            corpus
        )

        self.stored_count = len(
            ids
        )

        self.indexed_count = len(
            records
        )

        self.chroma_ids = set(
            ids
        )

        self.bm25_ids = {
            record["chunk_id"]
            for record in records
        }

        self.missing_ids = (
            self.chroma_ids
            - self.bm25_ids
        )

        self.extra_ids = (
            self.bm25_ids
            - self.chroma_ids
        )

        if (
            self.missing_ids
            or self.extra_ids
        ):
            raise RuntimeError(
                "BM25 and Chroma chunk IDs "
                "are not synchronized."
            )

    def sync_report(
        self,
    ) -> dict[str, Any]:
        """Return synchronization status between BM25 and Chroma."""

        return {
            "chroma_chunks": len(
                self.chroma_ids
            ),
            "bm25_chunks": len(
                self.bm25_ids
            ),
            "matching_ids": len(
                self.chroma_ids
                & self.bm25_ids
            ),
            "missing_ids": len(
                self.missing_ids
            ),
            "extra_ids": len(
                self.extra_ids
            ),
            "status": (
                "PASS"
                if not self.missing_ids
                and not self.extra_ids
                else "FAIL"
            ),
        }

    def search(
        self,
        query: str,
        top_k: int = 5,
        source: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search the BM25 index."""

        if (
            not isinstance(query, str)
            or not query.strip()
        ):
            raise ValueError(
                "query must be a non-empty string."
            )

        if (
            isinstance(top_k, bool)
            or not isinstance(top_k, int)
            or top_k <= 0
        ):
            raise ValueError(
                "top_k must be a positive integer."
            )

        if source is not None:
            if (
                not isinstance(source, str)
                or not source.strip()
            ):
                raise ValueError(
                    "source must be a non-empty filename."
                )

            source = source.strip()

        tokens = tokenize(
            query
        )

        if not tokens:
            return []

        scores = self.index.get_scores(
            tokens
        )

        candidates = [
            index
            for index, frequencies
            in enumerate(
                self.index.doc_freqs
            )
            if any(
                token in frequencies
                for token in tokens
            )
            and (
                source is None
                or self.records[
                    index
                ]["metadata"].get(
                    "source"
                ) == source
            )
        ]

        candidates.sort(
            key=lambda index: (
                -float(
                    scores[index]
                ),
                self.records[
                    index
                ]["chunk_id"],
            )
        )

        return [
            {
                "rank": rank,
                **self.records[index],
                "bm25_score": float(
                    scores[index]
                ),
            }
            for rank, index
            in enumerate(
                candidates[:top_k],
                start=1,
            )
        ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Search QISO with BM25."
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
        "--source",
    )

    args = parser.parse_args()

    query = (
        args.query
        if args.query is not None
        else input("Question: ")
    )

    searcher = (
        BM25Searcher()
    )

    results = searcher.search(
        query,
        top_k=args.top_k,
        source=args.source,
    )

    sync = (
        searcher.sync_report()
    )

    print(
        "\n"
        + "=" * 60
    )
    print(
        "CHROMA / BM25 SYNC"
    )
    print(
        "=" * 60
    )

    print(
        f"Chroma chunks:     "
        f"{sync['chroma_chunks']}"
    )

    print(
        f"BM25 chunks:       "
        f"{sync['bm25_chunks']}"
    )

    print(
        f"Matching IDs:      "
        f"{sync['matching_ids']}"
    )

    print(
        f"Missing IDs:       "
        f"{sync['missing_ids']}"
    )

    print(
        f"Extra IDs:         "
        f"{sync['extra_ids']}"
    )

    print(
        f"Status:            "
        f"{sync['status']}"
    )

    print(
        "\n"
        + "=" * 60
    )
    print(
        "QISO BM25 SEARCH"
    )
    print(
        "=" * 60
    )

    print(
        f"Query:             "
        f"{query}"
    )

    print(
        f"Retrieved:         "
        f"{len(results)}"
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
            f"Rank:      "
            f"{item['rank']}"
        )

        print(
            f"Source:    "
            f"{metadata.get('source', 'Unknown')}"
        )

        print(
            f"PDF page:  "
            f"{metadata.get('page', 'Unknown')}"
        )

        print(
            f"Chunk ID:  "
            f"{item['chunk_id']}"
        )

        print(
            f"BM25:      "
            f"{item['bm25_score']:.6f}"
        )


if __name__ == "__main__":
    main()