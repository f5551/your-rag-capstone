from core.ingest import ingest_pdfs


def main():
    docs = ingest_pdfs()

    if docs:
        first = docs[0]

        print("\nFirst ingested page:")
        print(
            f"Source: {first['metadata']['source']}"
        )
        print(
            f"Page:   {first['metadata']['page']}"
        )
        print(
            f"Type:   {first['metadata']['pdf_type']}"
        )
        print(
            f"Loader: {first['metadata']['loader']}"
        )

        print("\nPreview:")
        print(first["text"][:500])


if __name__ == "__main__":
    main()