"""Translate Arabic search queries into English for keyword retrieval only."""

import argparse
import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import cohere
from dotenv import load_dotenv

DEFAULT_TRANSLATION_MODEL = "command-a-translate-08-2025"


def has_arabic(text: str) -> bool:
    return any(char.isalpha() and "ARABIC" in unicodedata.name(char, "")
               for char in text)


def numbers(text: str) -> set[str]:
    text = "".join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in text)
    return set(re.findall(r"\d+(?:[.:]\d+)*", text))


@lru_cache(maxsize=128)
def _translate(query: str, model: str) -> str:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    key = os.getenv("COHERE_API_KEY")
    if not key:
        raise ValueError("COHERE_API_KEY was not found in .env")
    client = cohere.ClientV2(api_key=key, timeout=60)
    response = client.chat(
        model=model,
        messages=[{
            "role": "user",
            "content": (
                "Translate everything that follows into English. "
                "Return only the translation, without answering the question "
                "or adding explanations. Preserve ISO references, versions "
                "and clause numbers exactly (use ASCII digits).\n\n" + query
            ),
        }],
        max_tokens=512,
        temperature=0,
    )
    if response.finish_reason != "COMPLETE":
        raise RuntimeError(f"Search query translation did not complete: {response.finish_reason}")
    translated = "\n".join(
        block.text for block in (response.message.content or [])
        if getattr(block, "type", None) == "text"
    ).strip()
    if not translated or not re.search(r"[a-zA-Z]", translated) or has_arabic(translated):
        raise RuntimeError("Translation did not return a non-empty English query.")
    if numbers(query) != numbers(translated):
        raise RuntimeError("Translation changed or added numeric references.")
    return translated


def translate_query(query: str) -> str:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string.")
    query = query.strip()
    if not has_arabic(query):
        return query
    if len(query) > 2000:
        raise ValueError("Search queries must not exceed 2000 characters.")
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    model = os.getenv("COHERE_TRANSLATION_MODEL", DEFAULT_TRANSLATION_MODEL).strip()
    if not model:
        raise ValueError("COHERE_TRANSLATION_MODEL cannot be empty.")
    return _translate(query, model)


def main() -> None:
    parser = argparse.ArgumentParser(description="Test Arabic query translation.")
    parser.add_argument("query", nargs="?")
    args = parser.parse_args()
    query = args.query if args.query is not None else input("Question: ")
    print(f"Original query: {query}")
    print(f"BM25 query:     {translate_query(query)}")


if __name__ == "__main__":
    main()
