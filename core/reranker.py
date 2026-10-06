"""Cohere multilingual reranking following book section 7.4.

Run: python -X utf8 -m core.reranker
"""

import argparse
import math
import os
from pathlib import Path
from typing import Any

import cohere
from dotenv import load_dotenv

from .hybrid_search import HybridSearcher, positive_integer

DEFAULT_RERANK_MODEL = "rerank-multilingual-v3.0"


class Reranker:
    def __init__(self, model: str | None = None) -> None:
        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
        self.model = model or os.getenv("COHERE_RERANK_MODEL", DEFAULT_RERANK_MODEL)
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("Rerank model cannot be empty.")
        self.client = None

    def rerank(
        self, query: str, candidates: list[dict[str, Any]], top_n: int = 5,
    ) -> list[dict[str, Any]]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string.")
        positive_integer(top_n, "top_n")
        if not isinstance(candidates, list):
            raise TypeError("candidates must be a list.")
        unique = []
        seen = set()
        for item in candidates:
            chunk_id = item.get("chunk_id")
            if not isinstance(chunk_id, str) or not chunk_id:
                raise ValueError("Candidate is missing chunk_id.")
            if not isinstance(item.get("text"), str) or not item["text"].strip():
                raise ValueError(f"Candidate {chunk_id} has no text.")
            if chunk_id not in seen:
                unique.append(item)
                seen.add(chunk_id)
        if not unique:
            return []
        if self.client is None:
            key = os.getenv("COHERE_API_KEY")
            if not key:
                raise ValueError("COHERE_API_KEY was not found in .env")
            self.client = cohere.ClientV2(api_key=key, timeout=60)
        response = self.client.rerank(
            model=self.model.strip(),
            query=query.strip(),
            documents=[item["text"] for item in unique],
            top_n=min(top_n, len(unique)),
        )
        if len(response.results) != min(top_n, len(unique)):
            raise RuntimeError("Rerank returned an unexpected number of results.")
        results = []
        indices = set()
        for match in response.results:
            index = match.index
            if not isinstance(index, int) or not 0 <= index < len(unique) or index in indices:
                raise RuntimeError("Rerank returned an invalid or repeated document index.")
            indices.add(index)
            score = float(match.relevance_score)
            if not math.isfinite(score):
                raise RuntimeError("Rerank returned a non-finite relevance score.")
            original = unique[index]
            results.append({
                **original,
                "metadata": dict(original.get("metadata") or {}),
                "hybrid_rank": original.get("rank"),
                "rank": len(results) + 1,
                "rerank_score": score,
            })
        return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Hybrid retrieval then Cohere rerank.")
    parser.add_argument("query", nargs="?")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--model", help="Optional explicit Cohere rerank model")
    args = parser.parse_args()
    positive_integer(args.top_k, "top_k")
    positive_integer(args.candidate_k, "candidate_k")
    if args.candidate_k < args.top_k:
        parser.error("--candidate-k must be >= --top-k")
    query = args.query if args.query is not None else input("Question: ")
    searcher = HybridSearcher()
    candidates = searcher.search(query, top_k=args.candidate_k, candidate_k=args.candidate_k)
    reranker = Reranker(args.model)
    results = reranker.rerank(query, candidates, args.top_k)
    print("\nQISO HYBRID + RERANK")
    print(f"Model:       {reranker.model}")
    print(f"Query:       {query}")
    print(f"BM25 query:  {searcher.last_bm25_query}")
    print(f"Search mode: {searcher.last_mode}")
    print(f"Candidates:  {len(candidates)}")
    print(f"Returned:    {len(results)}")
    for item in results:
        metadata = item["metadata"]
        print("\n" + "-" * 60)
        print(f"Rank:        {item['rank']}")
        print(f"Hybrid rank: {item['hybrid_rank']}")
        print(f"Source:      {metadata.get('source', 'Unknown')}")
        print(f"PDF page:    {metadata.get('page', 'Unknown')}")
        print(f"Chunk ID:    {item['chunk_id']}")
        print(f"Rerank score:{item['rerank_score']:.6f}")
        print(item["text"])


if __name__ == "__main__":
    main()
