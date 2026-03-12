"""
Load embedding model (BAAI/bge-large-en-v1.5 locally via sentence-transformers).
Function get_embedding(text)
Function cosine_similarity(vectorA, vectorB)
Function semantic_similarity(textA, textB)
"""

import math
from typing import List
from sentence_transformers import SentenceTransformer

_MODEL_NAME = "BAAI/bge-large-en-v1.5"
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Lazy-load the embedding model (cached for reuse)."""
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def get_embedding(text: str) -> List[float]:
    """
    CLEAN text if needed
    GENERATE embedding vector using BAAI/bge-large-en-v1.5 (local)
    RETURN vector
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("Cannot embed empty text")

    model = _get_model()
    # Model truncates to 512 tokens by default
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


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
