"""
Embedding layer for QISO RAG system.

Provider:
    Cohere

Model:
    embed-multilingual-v3.0

Document input type:
    search_document

Query input type:
    search_query
"""

import os
import time
from copy import deepcopy
from typing import Any

import cohere
from cohere.errors import TooManyRequestsError
from dotenv import load_dotenv


# --------------------------------------------------
# Configuration
# --------------------------------------------------

EMBEDDING_MODEL = "embed-multilingual-v3.0"

DEFAULT_BATCH_SIZE = 90

# Delay between batches to respect Cohere trial limits
REQUEST_DELAY_SECONDS = 10

# Retry settings
MAX_RETRIES = 5
RATE_LIMIT_WAIT_SECONDS = 60


# --------------------------------------------------
# Cohere client
# --------------------------------------------------

def get_cohere_client():

    load_dotenv()

    api_key = os.getenv("COHERE_API_KEY")

    if not api_key:
        raise ValueError(
            "COHERE_API_KEY was not found in .env"
        )

    return cohere.Client(api_key)


# --------------------------------------------------
# Embed document chunks
# --------------------------------------------------

def embed_chunks(
    chunks: list[dict[str, Any]],
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> list[dict[str, Any]]:

    if not isinstance(chunks, list):
        raise TypeError(
            "chunks must be a list."
        )

    if not chunks:
        return []

    if batch_size <= 0:
        raise ValueError(
            "batch_size must be greater than 0."
        )

    if batch_size > 96:
        raise ValueError(
            "Cohere batch_size cannot exceed 96 texts."
        )

    client = get_cohere_client()

    embedded_chunks = []

    total_chunks = len(chunks)

    print("\n" + "=" * 60)
    print("COHERE EMBEDDING")
    print("=" * 60)

    print(f"Model:             {EMBEDDING_MODEL}")
    print(f"Chunks received:   {total_chunks}")
    print(f"Batch size:        {batch_size}")
    print(
        f"Delay per batch:   "
        f"{REQUEST_DELAY_SECONDS} seconds"
    )

    for start in range(
        0,
        total_chunks,
        batch_size,
    ):

        end = min(
            start + batch_size,
            total_chunks,
        )

        batch = chunks[start:end]

        texts = [
            chunk["text"]
            for chunk in batch
        ]

        # ------------------------------------------
        # Retry loop
        # ------------------------------------------

        response = None

        for attempt in range(
            1,
            MAX_RETRIES + 1,
        ):

            try:

                response = client.embed(
                    texts=texts,
                    model=EMBEDDING_MODEL,
                    input_type="search_document",
                )

                break

            except TooManyRequestsError:

                if attempt == MAX_RETRIES:
                    raise

                print(
                    "\nCohere rate limit reached."
                )

                print(
                    f"Waiting "
                    f"{RATE_LIMIT_WAIT_SECONDS} seconds..."
                )

                time.sleep(
                    RATE_LIMIT_WAIT_SECONDS
                )

        if response is None:
            raise RuntimeError(
                "Cohere embedding failed."
            )

        vectors = response.embeddings

        if len(vectors) != len(batch):
            raise RuntimeError(
                "Embedding count does not match chunk count."
            )

        # ------------------------------------------
        # Build records
        # ------------------------------------------

        for chunk, vector in zip(
            batch,
            vectors,
        ):

            record = {
                "text": chunk["text"],
                "metadata": deepcopy(
                    chunk["metadata"]
                ),
                "embedding": vector,
            }

            record["metadata"][
                "embedding_model"
            ] = EMBEDDING_MODEL

            record["metadata"][
                "embedding_dimensions"
            ] = len(vector)

            embedded_chunks.append(
                record
            )

        print(
            f"Embedded:          "
            f"{end}/{total_chunks}"
        )

        # ------------------------------------------
        # Respect trial rate limit
        # ------------------------------------------

        if end < total_chunks:

            time.sleep(
                REQUEST_DELAY_SECONDS
            )

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    print("\nEmbedding Summary")

    print(
        f"Embedded chunks:   "
        f"{len(embedded_chunks)}"
    )

    if embedded_chunks:

        print(
            f"Vector dimensions: "
            f"{len(embedded_chunks[0]['embedding'])}"
        )

    return embedded_chunks


# --------------------------------------------------
# Embed search query
# --------------------------------------------------

def embed_query(
    query: str,
) -> list[float]:

    if not isinstance(query, str):
        raise TypeError(
            "query must be a string."
        )

    if not query.strip():
        raise ValueError(
            "query cannot be empty."
        )

    client = get_cohere_client()

    response = client.embed(
        texts=[query],
        model=EMBEDDING_MODEL,
        input_type="search_query",
    )

    return response.embeddings[0]