from pathlib import Path
from typing import Iterable, List

from dotenv import load_dotenv

from app.rag.embeddings import chunk_text, embed_texts, extract_text_from_pdf
from app.rag.vector_store import PineconeVectorStore


def _build_vectors(
    namespace: str,
    source: Path,
    chunks: List[str],
    embeddings: List[List[float]],
) -> Iterable[dict]:
    for index, (chunk, vector) in enumerate(zip(chunks, embeddings)):
        limited_text = chunk[:1500]
        yield {
            "id": f"{namespace}-{source.stem}-{index}",
            "values": vector,
            "metadata": {
                "source": str(source),
                "namespace": namespace,
                "chunk_index": index,
                "text": limited_text,
                "subject": "Electrical Engineering",
                "topic": namespace,
            },
        }


def embed_ee_books(base_path: Path | None = None, index_name: str | None = None) -> None:
    load_dotenv()
    books_root = base_path or Path(__file__).resolve().parents[2] / "Books" / "EE"
    if not books_root.exists():
        raise FileNotFoundError(f"EE books directory not found: {books_root}")

    store: PineconeVectorStore | None = None

    for topic_dir in sorted(path for path in books_root.iterdir() if path.is_dir()):
        namespace = topic_dir.name
        pdf_files = sorted(topic_dir.glob("*.pdf"))
        if not pdf_files:
            continue

        for pdf_path in pdf_files:
            text = extract_text_from_pdf(pdf_path)
            chunks = chunk_text(text)
            if not chunks:
                continue

            embeddings = embed_texts(chunks)
            vectors = list(
                _build_vectors(
                    namespace=namespace,
                    source=pdf_path.relative_to(books_root.parent),
                    chunks=chunks,
                    embeddings=embeddings,
                )
            )
            if not vectors:
                continue

            if store is None:
                vector_dim = len(vectors[0]["values"])
                store = PineconeVectorStore(index_name=index_name, dimension=vector_dim)

            store.upsert(namespace=namespace, vectors=vectors)
            print(
                f"Upserted {len(vectors)} vectors from {pdf_path.name} into namespace '{namespace}'."
            )


if __name__ == "__main__":
    embed_ee_books()
