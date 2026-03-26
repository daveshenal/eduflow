"""
Embedding similarity utilities used by evaluator metrics.

This module uses `sentence-transformers` and caches both:
- the SentenceTransformer model (loaded once per process)
- embeddings (so repeated concept comparisons don't re-encode)
"""

import math
from typing import List
from sentence_transformers import SentenceTransformer

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_model: SentenceTransformer | None = None
_embedding_cache: dict[str, List[float]] = {}


def _normalize(text: str) -> str:
    """Normalization used for embedding cache keys and semantic matching."""
    return (text or "").lower().strip()


def _get_model() -> SentenceTransformer:
    """Lazy-load the embedding model (cached for reuse)."""
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def get_embedding(text: str) -> List[float]:
    """
    Generate (or fetch from cache) an embedding vector for the given text.
    """
    key = _normalize(text)
    if not key:
        raise ValueError("Cannot embed empty text")

    cached = _embedding_cache.get(key)
    if cached is not None:
        return cached

    model = _get_model()
    # Model truncates to 512 tokens by default.
    embedding = model.encode(key, convert_to_numpy=True)
    vector = embedding.tolist()
    _embedding_cache[key] = vector
    return vector


def cosine_similarity(vector_a: List[float], vector_b: List[float]) -> float:
    """
    dot_product = sum(A_i * B_i)
    magnitude_A = sqrt(sum(A_i^2))
    magnitude_B = sqrt(sum(B_i^2))
    similarity = dot_product / (magnitude_A * magnitude_B)
    RETURN similarity
    """
    if len(vector_a) != len(vector_b):
        raise ValueError("Vectors must have same dimension")

    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    magnitude_a = math.sqrt(sum(a * a for a in vector_a))
    magnitude_b = math.sqrt(sum(b * b for b in vector_b))

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


def semantic_similarity(text_a: str, text_b: str) -> float:
    """
    Get embeddings for both texts and return cosine similarity.
    """
    emb_a = get_embedding(text_a)
    emb_b = get_embedding(text_b)
    return cosine_similarity(emb_a, emb_b)
