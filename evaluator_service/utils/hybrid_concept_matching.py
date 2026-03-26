"""
Hybrid concept matching for RAG research metrics.

Matching is performed on short concept strings using:
1) Exact match (after lower+strip)
2) Substring match
3) Semantic similarity using sentence-transformers embeddings + cosine similarity

The embedding threshold defaults to 0.75.
"""

from __future__ import annotations

from typing import Iterable, Tuple

from evaluator_service.embedding.similarity import cosine_similarity, get_embedding


def normalize(text: str) -> str:
    """Lowercase + trim normalization used for exact/substring checks."""
    return (text or "").lower().strip()


def semantic_similarity(a: str, b: str) -> float:
    """Semantic similarity of two strings via embeddings + cosine similarity."""
    emb_a = get_embedding(a)
    emb_b = get_embedding(b)
    return cosine_similarity(emb_a, emb_b)


def hybrid_match(
    query: str,
    candidate_list: Iterable[str],
    threshold: float = 0.75,
) -> Tuple[bool, str | None]:
    """
    Hybrid match query against a list of candidate strings.

    Returns:
      (True, matching_candidate) if a match is found, else (False, None)
    """
    candidates = [c for c in candidate_list if isinstance(c, str) and (c or "").strip()]
    query_norm = normalize(query)
    if not query_norm or not candidates:
        return False, None

    # 1. Exact match
    for candidate in candidates:
        candidate_norm = normalize(candidate)
        if not candidate_norm:
            continue
        if query_norm == candidate_norm:
            return True, candidate

    # 2. Substring match
    for candidate in candidates:
        candidate_norm = normalize(candidate)
        if not candidate_norm:
            continue
        if query_norm in candidate_norm or candidate_norm in query_norm:
            return True, candidate

    # 3. Semantic match
    best_score = -1.0
    best_candidate: str | None = None

    query_emb = get_embedding(query_norm)
    for candidate in candidates:
        candidate_norm = normalize(candidate)
        if not candidate_norm:
            continue
        score = cosine_similarity(query_emb, get_embedding(candidate_norm))
        if score > best_score:
            best_score = score
            best_candidate = candidate

    if best_score >= threshold:
        return True, best_candidate
    return False, None


def find_best_match(
    query: str,
    candidate_keys: Iterable[str],
    threshold: float = 0.75,
) -> str | None:
    """Find the best-matching candidate key using the shared hybrid matcher."""
    matched, candidate = hybrid_match(query, candidate_keys, threshold)
    return candidate

