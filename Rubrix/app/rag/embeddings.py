import os
from pathlib import Path
from typing import Iterable, List

import fitz
from sentence_transformers import SentenceTransformer


DEFAULT_EMBEDDING_MODEL = os.getenv("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2")
DEFAULT_CHUNK_SIZE = 900
DEFAULT_CHUNK_OVERLAP = 150
MAX_EMBED_BATCH = 64

_MODEL_CACHE: dict[str, SentenceTransformer] = {}


def _get_model(model_name: str = DEFAULT_EMBEDDING_MODEL) -> SentenceTransformer:
	if model_name in _MODEL_CACHE:
		return _MODEL_CACHE[model_name]
	try:
		model = SentenceTransformer(model_name)
	except Exception as exc:
		raise RuntimeError(
			f"Failed to load sentence-transformer model '{model_name}'."
		) from exc
	_MODEL_CACHE[model_name] = model
	return model


def extract_text_from_pdf(path: Path) -> str:
	if not path.exists():
		raise FileNotFoundError(f"PDF not found: {path}")
	document = fitz.open(path)
	try:
		pages = [page.get_text("text") for page in document]
	finally:
		document.close()
	return "\n".join(pages).strip()


def chunk_text(
	text: str,
	chunk_size: int = DEFAULT_CHUNK_SIZE,
	overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[str]:
	clean = " ".join(text.split())
	if not clean:
		return []
	chunks: List[str] = []
	start = 0
	length = len(clean)
	while start < length:
		end = min(start + chunk_size, length)
		chunk = clean[start:end].strip()
		if chunk:
			chunks.append(chunk)
		if end == length:
			break
		start = max(end - overlap, 0)
	return chunks


def embed_texts(texts: Iterable[str], model: str | None = None) -> List[List[float]]:
	items = [text for text in texts if text]
	if not items:
		return []
	model_name = model or DEFAULT_EMBEDDING_MODEL
	sentence_model = _get_model(model_name)
	embeddings: List[List[float]] = []
	for index in range(0, len(items), MAX_EMBED_BATCH):
		batch = items[index : index + MAX_EMBED_BATCH]
		encoded = sentence_model.encode(batch, convert_to_numpy=True)
		if len(encoded.shape) == 1:
			embeddings.append(encoded.tolist())
		else:
			for row in encoded:
				embeddings.append(row.tolist())
	return embeddings
